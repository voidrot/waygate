import hashlib
import hmac
import json
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, List
from uuid import uuid4

from waygate_core.plugin_base import IngestionPlugin, WebhookVerificationError
from waygate_core.schemas import RawDocument
from waygate_plugin_github_receiver.metadata import GitHubSourceMetadata


class GitHubReceiver(IngestionPlugin):
    @property
    def plugin_name(self) -> str:
        return "github_receiver"

    def poll(self, since_timestamp=None) -> List[RawDocument]:
        # TODO: implement process to get repo files as a snapshot
        export_path = os.getenv("GITHUB_EXPORT_PATH")
        if not export_path:
            return []

        root = Path(export_path)
        if not root.exists():
            return []

        documents: list[RawDocument] = []
        for snapshot_file in sorted(root.glob("*.json")):
            mtime = datetime.fromtimestamp(snapshot_file.stat().st_mtime, tz=UTC)
            if since_timestamp and mtime <= since_timestamp:
                continue

            try:
                snapshot = json.loads(snapshot_file.read_text(encoding="utf-8"))
            except OSError, json.JSONDecodeError:
                continue

            documents.extend(
                self._documents_from_snapshot(
                    snapshot=snapshot, fallback_timestamp=mtime
                )
            )

        return documents

    def handle_webhook(self, payload: dict) -> List[RawDocument]:
        if not payload:
            raise ValueError("Webhook body cannot be empty")

        repository = payload.get("repository") or {}
        pull_request = payload.get("pull_request") or {}
        issue = payload.get("issue") or {}
        comment = payload.get("comment") or {}
        review = payload.get("review") or {}
        head_commit = payload.get("head_commit") or {}
        raw_commits = payload.get("commits")
        commits: list[Any] = raw_commits if isinstance(raw_commits, list) else []

        repo_name = self._string(repository, "full_name")
        branch = self._branch_from_ref(self._string(payload, "ref"))
        commit_sha = (
            self._string(payload, "after")
            or self._string(head_commit, "id")
            or self._string(pull_request, "head", "sha")
        )
        owner = self._string(repository, "owner", "login")

        source_url = (
            self._string(comment, "html_url")
            or self._string(review, "html_url")
            or self._string(pull_request, "html_url")
            or self._string(issue, "html_url")
            or self._string(head_commit, "url")
            or self._string(repository, "html_url")
        )
        source_id = (
            self._string(payload, "delivery_id")
            or self._string(review, "id")
            or self._string(comment, "id")
            or self._string(pull_request, "id")
            or self._string(issue, "id")
            or self._string(payload, "after")
            or str(uuid4())
        )

        content = self._content_from_payload(
            payload=payload,
            pull_request=pull_request,
            issue=issue,
            comment=comment,
            review=review,
            head_commit=head_commit,
            commits=commits,
        )
        timestamp = self._timestamp_from_payload(
            payload, pull_request, issue, comment, review, head_commit
        )

        tags = ["github"]
        event = self._string(payload, "event")
        action = self._string(payload, "action")
        if event:
            tags.append(event)
        if action:
            tags.append(action)

        metadata = GitHubSourceMetadata(
            repo_name=repo_name,
            branch=branch,
            commit_sha=commit_sha,
            owner=owner,
        )

        return [
            RawDocument(
                source_type="github",
                source_id=source_id,
                timestamp=timestamp,
                content=content,
                tags=tags,
                source_url=source_url,
                source_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                source_metadata=metadata,
            )
        ]

    def verify_webhook_request(
        self,
        headers: Mapping[str, str],
        body: bytes,
    ) -> None:
        secret = os.getenv("GITHUB_WEBHOOK_SECRET")
        if not secret:
            raise WebhookVerificationError("GitHub webhook secret is not configured")

        signature = headers.get("x-hub-signature-256")
        if not signature:
            raise WebhookVerificationError("Missing GitHub signature header")

        expected = (
            "sha256="
            + hmac.new(
                secret.encode("utf-8"),
                body,
                hashlib.sha256,
            ).hexdigest()
        )
        if not hmac.compare_digest(signature, expected):
            raise WebhookVerificationError("Invalid GitHub webhook signature")

    def prepare_webhook_payload(
        self,
        payload: Any,
        headers: Mapping[str, str],
    ) -> Any:
        if not isinstance(payload, dict):
            return payload

        enriched = dict(payload)
        if "event" not in enriched:
            event_name = headers.get("x-github-event")
            if event_name:
                enriched["event"] = event_name
        if "delivery_id" not in enriched:
            delivery_id = headers.get("x-github-delivery")
            if delivery_id:
                enriched["delivery_id"] = delivery_id
        return enriched

    def _documents_from_snapshot(
        self, *, snapshot: Any, fallback_timestamp: datetime
    ) -> list[RawDocument]:
        if not isinstance(snapshot, dict):
            return []

        repository = snapshot.get("repository") or {}
        repo_name = self._string(repository, "full_name")
        owner = self._string(repository, "owner", "login")
        branch = self._branch_from_ref(
            self._string(snapshot, "ref")
            or self._string(snapshot, "branch")
            or self._string(snapshot, "default_branch")
        )
        commit_sha = self._string(snapshot, "after") or self._string(
            snapshot, "commit_sha"
        )

        files = snapshot.get("files")
        if not isinstance(files, list):
            return []

        tech_stack = sorted(
            {
                str(item.get("language")).lower()
                for item in files
                if isinstance(item, dict) and item.get("language")
            }
        )

        docs: list[RawDocument] = []
        for item in files:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if content is None:
                continue
            if not isinstance(content, str):
                content = json.dumps(content, sort_keys=True)

            path = (
                self._string(item, "path")
                or self._string(item, "filename")
                or "unknown"
            )
            source_id = (
                self._string(item, "sha")
                or self._string(item, "id")
                or f"{commit_sha or 'snapshot'}:{path}"
            )
            source_url = (
                self._string(item, "html_url")
                or self._string(item, "url")
                or self._build_blob_url(repository, branch, path)
            )

            metadata = GitHubSourceMetadata(
                repo_name=repo_name,
                branch=branch,
                commit_sha=commit_sha,
                owner=owner,
                tech_stack=tech_stack,
                token_count=len(content.split()),
            )

            docs.append(
                RawDocument(
                    source_type="github",
                    source_id=source_id,
                    timestamp=fallback_timestamp,
                    content=content,
                    tags=[tag for tag in ["github", "snapshot", branch] if tag],
                    source_url=source_url,
                    source_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    source_metadata=metadata,
                )
            )

        return docs

    def _content_from_payload(
        self,
        *,
        payload: dict[str, Any],
        pull_request: dict[str, Any],
        issue: dict[str, Any],
        comment: dict[str, Any],
        review: dict[str, Any],
        head_commit: dict[str, Any],
        commits: list[Any],
    ) -> str:
        push_summary = self._build_push_summary(
            payload=payload,
            repository=self._as_dict(payload.get("repository")),
            commits=commits,
        )
        if push_summary:
            return push_summary

        review_summary = self._build_review_summary(
            payload=payload,
            pull_request=pull_request,
            review=review,
        )
        if review_summary:
            return review_summary

        issue_summary = self._build_issue_summary(payload=payload, issue=issue)
        if issue_summary:
            return issue_summary

        comment_body = self._string(comment, "body")
        if comment_body:
            return comment_body

        pr_text = "\n\n".join(
            value
            for value in [
                self._string(pull_request, "title"),
                self._string(pull_request, "body"),
            ]
            if value
        )
        if pr_text:
            return pr_text

        issue_text = "\n\n".join(
            value
            for value in [
                self._string(issue, "title"),
                self._string(issue, "body"),
            ]
            if value
        )
        if issue_text:
            return issue_text

        head_message = self._string(head_commit, "message")
        if head_message:
            return head_message

        return json.dumps(payload, sort_keys=True)

    def _timestamp_from_payload(
        self,
        payload: dict[str, Any],
        pull_request: dict[str, Any],
        issue: dict[str, Any],
        comment: dict[str, Any],
        review: dict[str, Any],
        head_commit: dict[str, Any],
    ) -> datetime:
        value = (
            self._string(comment, "updated_at")
            or self._string(comment, "created_at")
            or self._string(review, "submitted_at")
            or self._string(review, "updated_at")
            or self._string(review, "created_at")
            or self._string(pull_request, "updated_at")
            or self._string(pull_request, "created_at")
            or self._string(issue, "updated_at")
            or self._string(issue, "created_at")
            or self._string(head_commit, "timestamp")
            or self._string(payload, "timestamp")
        )

        if value is None:
            return datetime.now(UTC)

        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except TypeError, ValueError:
            return datetime.now(UTC)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed

    def _build_blob_url(
        self, repository: dict[str, Any], branch: str | None, path: str
    ) -> str | None:
        html_url = self._string(repository, "html_url")
        if not html_url or not branch:
            return None
        return f"{html_url}/blob/{branch}/{path}"

    def _branch_from_ref(self, ref: str | None) -> str | None:
        if not ref:
            return None
        prefix = "refs/heads/"
        if ref.startswith(prefix):
            return ref[len(prefix) :]
        return ref

    def _string(self, payload: dict[str, Any], *keys: str) -> str | None:
        current: Any = payload
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        if current is None:
            return None
        return str(current)

    def _as_dict(self, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _build_issue_summary(
        self,
        *,
        payload: dict[str, Any],
        issue: dict[str, Any],
    ) -> str | None:
        if self._string(payload, "event") != "issues":
            return None

        title = self._string(issue, "title") or "Untitled issue"
        number = self._string(issue, "number")
        action = self._string(payload, "action") or "updated"
        raw_labels = issue.get("labels")
        labels: list[Any] = raw_labels if isinstance(raw_labels, list) else []
        label_names = [
            str(item.get("name"))
            for item in labels
            if isinstance(item, dict) and item.get("name")
        ]
        raw_assignees = issue.get("assignees")
        assignees: list[Any] = raw_assignees if isinstance(raw_assignees, list) else []
        assignee_names = [
            str(item.get("login"))
            for item in assignees
            if isinstance(item, dict) and item.get("login")
        ]
        body = self._string(issue, "body") or ""

        lines = [f"GitHub issue {number or '?'} {action}: {title}"]
        if label_names:
            lines.append(f"Labels: {', '.join(label_names)}")
        if assignee_names:
            lines.append(f"Assignees: {', '.join(assignee_names)}")
        if body:
            lines.append("")
            lines.append(body)
        return "\n".join(lines)

    def _build_review_summary(
        self,
        *,
        payload: dict[str, Any],
        pull_request: dict[str, Any],
        review: dict[str, Any],
    ) -> str | None:
        event_name = self._string(payload, "event")
        if event_name not in {"pull_request_review", "pull_request_review_comment"}:
            return None

        pr_title = self._string(pull_request, "title") or "Untitled pull request"
        pr_number = self._string(pull_request, "number")
        action = self._string(payload, "action") or "updated"
        state = self._string(review, "state")
        body = self._string(review, "body")
        if event_name == "pull_request_review_comment" and not body:
            comment = self._as_dict(payload.get("comment"))
            body = self._string(comment, "body")

        lines = [f"GitHub PR review for #{pr_number or '?'} {action}: {pr_title}"]
        if state:
            lines.append(f"Review state: {state}")
        if body:
            lines.append("")
            lines.append(body)
        return "\n".join(lines)

    def _build_push_summary(
        self,
        *,
        payload: dict[str, Any],
        repository: dict[str, Any],
        commits: list[Any],
    ) -> str | None:
        if self._string(payload, "event") != "push":
            return None

        repo_name = self._string(repository, "full_name") or "unknown repository"
        ref = self._branch_from_ref(self._string(payload, "ref")) or "unknown"
        commit_dicts = [item for item in commits if isinstance(item, dict)]

        lines = [
            f"GitHub push to {repo_name} on {ref}",
            f"Commit count: {len(commit_dicts)}",
        ]
        changed_files: set[str] = set()
        if commit_dicts:
            lines.append("")
            lines.append("Commits:")
        for commit in commit_dicts:
            commit_id = self._string(commit, "id") or "unknown"
            message = self._string(commit, "message") or "(no message)"
            lines.append(f"- {commit_id[:7]} {message}")
            for key in ("added", "modified", "removed"):
                values = commit.get(key)
                if isinstance(values, list):
                    changed_files.update(str(item) for item in values if item)

        if changed_files:
            lines.append("")
            lines.append("Changed files:")
            lines.extend(f"- {path}" for path in sorted(changed_files))
        return "\n".join(lines)

    async def listen(
        self, on_data_callback: Callable[[List[RawDocument]], Awaitable[None]]
    ) -> None:
        raise NotImplementedError("GitHub stream listener stub is not implemented yet")
