from typing import Protocol
import re

from waygate_agent_sdk.models import LoadedLiveDocument, RetrievalQuery

WORD_PATTERN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> set[str]:
    return set(WORD_PATTERN.findall(text.lower()))


class DocumentScorer(Protocol):
    def score(
        self,
        document: LoadedLiveDocument,
        request: RetrievalQuery,
        lineage_ids: set[str],
    ) -> dict[str, float]: ...


class LexicalDocumentScorer:
    def score(
        self,
        document: LoadedLiveDocument,
        request: RetrievalQuery,
        lineage_ids: set[str],
    ) -> dict[str, float]:
        metadata = document.metadata
        query_terms = tokenize(request.query)
        title_matches = len(query_terms.intersection(tokenize(metadata.title)))
        tag_matches = len(query_terms.intersection(tokenize(" ".join(metadata.tags))))
        content_matches = len(query_terms.intersection(tokenize(document.content)))
        lineage_matches = len(lineage_ids.intersection(metadata.lineage))

        lexical_score = float((title_matches * 3) + (tag_matches * 2) + content_matches)
        score = lexical_score + float(lineage_matches)
        return {
            "title_matches": float(title_matches),
            "tag_matches": float(tag_matches),
            "content_matches": float(content_matches),
            "lineage_matches": float(lineage_matches),
            "lexical_score": lexical_score,
            "score": score,
        }
