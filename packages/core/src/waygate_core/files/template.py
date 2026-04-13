import frontmatter
from waygate_core.schema import RawDocumentFrontmatter
from waygate_core.schema import RawDocument
from jinja2 import Environment, PackageLoader

template_env = Environment(loader=PackageLoader("waygate_core", "templates"))

raw_doc_template = template_env.get_template("raw_document.j2")


def build_raw_document_frontmatter(raw_doc: RawDocument) -> RawDocumentFrontmatter:
    """Build frontmatter from a RawDocument using shared metadata fields."""
    return RawDocumentFrontmatter(
        source_type=raw_doc.source_type,
        source_id=raw_doc.source_id,
        source_hash=raw_doc.source_hash,
        source_uri=raw_doc.source_uri,
        timestamp=raw_doc.timestamp,
        topics=raw_doc.topics or [],
        tags=raw_doc.tags or [],
    )


def _serialize_frontmatter(doc_frontmatter: RawDocumentFrontmatter) -> str:
    """Return YAML frontmatter content without surrounding --- fences."""
    post = frontmatter.Post("", **doc_frontmatter.model_dump(exclude_none=True))
    dumped = frontmatter.dumps(post)

    if dumped.startswith("---"):
        lines = dumped.splitlines()
        if lines and lines[0] == "---":
            for index in range(1, len(lines)):
                if lines[index] == "---":
                    return "\n".join(lines[1:index])

    return ""


def render_raw_document(
    raw_doc: RawDocument, doc_frontmatter: RawDocumentFrontmatter | None = None
) -> str:
    resolved_frontmatter = doc_frontmatter or build_raw_document_frontmatter(raw_doc)
    serialized_frontmatter = _serialize_frontmatter(resolved_frontmatter)

    return raw_doc_template.render(
        frontmatter=serialized_frontmatter, raw_content=raw_doc.content
    )


def render_draft_document(context: dict, content: str, doc_uri: str) -> str:
    template = template_env.get_template("draft_source_text.j2")
    return template.render(context=context, content=content, doc_uri=doc_uri)
