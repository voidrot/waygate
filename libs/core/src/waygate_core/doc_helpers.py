import re
from typing import Any

from waygate_core.schemas import FrontMatterDocument


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


def generate_frontmatter(metadata: FrontMatterDocument) -> str:
    frontmatter = "---\n"
    compiled_at = metadata.last_compiled or metadata.last_updated

    frontmatter += f"doc_id: {metadata.doc_id}\n"
    frontmatter += f"title: {metadata.title}\n"
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
