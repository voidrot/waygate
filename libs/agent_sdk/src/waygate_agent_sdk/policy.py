from typing import Protocol

from waygate_core.schemas import FrontMatterDocument

from waygate_agent_sdk.models import RetrievalScope


class VisibilityPolicy(Protocol):
    def allows(self, metadata: FrontMatterDocument, scope: RetrievalScope) -> bool: ...


class DefaultVisibilityPolicy:
    def allows(self, metadata: FrontMatterDocument, scope: RetrievalScope) -> bool:
        return str(metadata.visibility) in {
            str(item) for item in scope.allowed_visibilities
        }
