import re

from waygate_core.schemas import FrontMatterDocument


def slugify(text: str) -> str:
    text = text.lower()
    return re.sub(r"[\W_]+", "-", text).strip("-")


def generate_frontmatter(metadata: FrontMatterDocument) -> str:
    frontmatter = "---\n"
    # for key, value in metadata:
    #     frontmatter += f"{key}: {value}\n"
    frontmatter += f"title: {metadata.title}\n"
    frontmatter += f"last_updated: {metadata.last_updated}\n"
    frontmatter += f"status: {metadata.status}\n"
    if metadata.tags:
        frontmatter += "tags:\n"
        for tag in metadata.tags:
            frontmatter += f"  - {tag}\n"
    else:
        frontmatter += "tags: []\n"
    if metadata.sources:
        frontmatter += "sources:\n"
        for source in metadata.sources:
            frontmatter += f"  - {source}\n"
    else:
        frontmatter += "sources: []\n"
    frontmatter += "---\n"
    return frontmatter
