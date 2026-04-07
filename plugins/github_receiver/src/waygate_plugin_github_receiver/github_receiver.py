import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, List
from uuid import uuid4

from waygate_core.plugin_base import IngestionPlugin
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
            except (OSError, json.JSONDecodeError):
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
        sender = payload.get("sender") or {}
        pull_request = payload.get("pull_request") or {}
        issue = payload.get("issue") or {}
        comment = payload.get("comment") or {}
        head_commit = payload.get("head_commit") or {}

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
            or self._string(pull_request, "html_url")
            or self._string(issue, "html_url")
            or self._string(head_commit, "url")
            or self._string(repository, "html_url")
        )
        source_id = (
            self._string(payload, "delivery_id")
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
            head_commit=head_commit,
        )
        timestamp = self._timestamp_from_payload(
            payload, pull_request, issue, comment, head_commit
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
        head_commit: dict[str, Any],
    ) -> str:
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
        head_commit: dict[str, Any],
    ) -> datetime:
        value = (
            self._string(comment, "updated_at")
            or self._string(comment, "created_at")
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
        except (TypeError, ValueError):
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

    async def listen(
        self, on_data_callback: Callable[[List[RawDocument]], Awaitable[None]]
    ) -> None:
        raise NotImplementedError("GitHub stream listener stub is not implemented yet")
