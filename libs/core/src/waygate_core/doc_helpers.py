import hashlib
import re
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from waygate_core.schemas import FrontMatterDocument, RawDocument


def slugify(text: str) -> str:
    text = text.lower()
    return re.sub(r"[\W_]+", "-", text).strip("-")


def _append_list(frontmatter: str, key: str, values: list[str]) -> str:
    if values:
        frontmatter += f"{key}:\n"
        for value in values:
            frontmatter += f"  - {value}\n"
        return frontmatter
    return frontmatter + f"{key}: []\n"


def _append_mapping(frontmatter: str, key: str, mapping: dict[str, Any] | None) -> str:
    if not mapping:
        return frontmatter + f"{key}: {{}}\n"

    frontmatter += f"{key}:\n"
    for item_key, value in mapping.items():
        if value is None:
            continue
        if isinstance(value, list):
            if value:
                frontmatter += f"  {item_key}:\n"
                for entry in value:
                    frontmatter += f"    - {entry}\n"
            else:
                frontmatter += f"  {item_key}: []\n"
        else:
            frontmatter += f"  {item_key}: {value}\n"
    return frontmatter


def _append_scalar(frontmatter: str, key: str, value: Any) -> str:
    if value is None:
        return frontmatter
    return frontmatter + f"{key}: {value}\n"


def infer_initial_topic(documents: list[RawDocument]) -> str:
    if not documents:
        return "Untitled Document"

    first = documents[0]
    source_label = slugify(first.source_type).replace("-", " ").title() or "Source"
    source_identifier = first.source_id.replace("/", " ").replace("-", " ").strip()
    if len(documents) == 1 and source_identifier:
        return f"{source_label} {source_identifier}".strip()
    return f"{source_label} Batch {len(documents)}"


def extract_markdown_title(markdown: str, fallback: str) -> str:
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            if title:
                return title
            continue
        break
    return fallback


def build_compiled_document_id(lineage: list[str], title: str) -> str:
    seed = "|".join([title.strip().lower(), *sorted(lineage)])
    return str(uuid5(NAMESPACE_URL, seed))


def build_live_document_name(title: str, document_id: str) -> str:
    return f"{slugify(title)}-{document_id.split('-')[0]}.md"


def build_provenance_hash(documents: list[RawDocument]) -> str | None:
    parts = [doc.source_hash or doc.doc_id for doc in documents]
    if not parts:
        return None
    digest = hashlib.sha256()
    for part in sorted(parts):
        digest.update(part.encode("utf-8"))
    return digest.hexdigest()


def raw_document_metadata(document: RawDocument) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "doc_id": document.doc_id,
        "source_type": document.source_type,
        "source_id": document.source_id,
        "timestamp": document.timestamp.isoformat(),
        "tags": document.tags,
        "visibility": str(document.visibility),
    }
    if document.source_url is not None:
        metadata["source_url"] = document.source_url
    if document.source_hash is not None:
        metadata["source_hash"] = document.source_hash
    if document.source_metadata is not None:
        metadata["source_metadata"] = document.source_metadata.model_dump(
            exclude_none=True
        )
    return metadata


def generate_raw_frontmatter(document: RawDocument) -> str:
    frontmatter = "---\n"
    metadata = raw_document_metadata(document)
    frontmatter = _append_scalar(frontmatter, "doc_id", metadata["doc_id"])
    frontmatter = _append_scalar(frontmatter, "source_type", metadata["source_type"])
    frontmatter = _append_scalar(frontmatter, "source_id", metadata["source_id"])
    frontmatter = _append_scalar(frontmatter, "timestamp", metadata["timestamp"])
    frontmatter = _append_list(frontmatter, "tags", metadata["tags"])
    frontmatter = _append_scalar(frontmatter, "visibility", metadata["visibility"])
    frontmatter = _append_scalar(frontmatter, "source_url", metadata.get("source_url"))
    frontmatter = _append_scalar(
        frontmatter, "source_hash", metadata.get("source_hash")
    )
    if "source_metadata" in metadata:
        frontmatter = _append_mapping(
            frontmatter, "source_metadata", metadata["source_metadata"]
        )
    frontmatter += "---\n"
    return frontmatter


def generate_raw_document(document: RawDocument) -> str:
    return f"{generate_raw_frontmatter(document)}\n{document.content}"


def generate_frontmatter(metadata: FrontMatterDocument) -> str:
    frontmatter = "---\n"
    compiled_at = metadata.last_compiled or metadata.last_updated

    frontmatter += f"doc_id: {metadata.doc_id}\n"
    frontmatter += f"title: {metadata.title}\n"
    frontmatter += f"document_type: {metadata.document_type}\n"
    frontmatter += f"source_type: {metadata.source_type}\n"
    if metadata.source_url:
        frontmatter += f"source_url: {metadata.source_url}\n"
    if metadata.source_hash:
        frontmatter += f"source_hash: {metadata.source_hash}\n"
    frontmatter += f"status: {metadata.status}\n"
    frontmatter += f"visibility: {metadata.visibility}\n"
    frontmatter = _append_list(frontmatter, "tags", metadata.tags)
    if compiled_at:
        frontmatter += f"last_compiled: {compiled_at}\n"
    frontmatter = _append_list(frontmatter, "lineage", metadata.lineage)
    frontmatter = _append_list(frontmatter, "sources", metadata.sources)
    if metadata.source_metadata is not None:
        frontmatter = _append_mapping(
            frontmatter,
            "source_metadata",
            metadata.source_metadata.model_dump(exclude_none=True),
        )
    else:
        frontmatter += "source_metadata: {}\n"

    # Preserve this legacy key while transitioning to `last_compiled`.
    if metadata.last_updated:
        frontmatter += f"last_updated: {metadata.last_updated}\n"

    frontmatter += "---\n"
    return frontmatter
