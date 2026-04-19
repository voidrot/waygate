"""Document visibility values shared across the core data model."""

from enum import StrEnum


class Visibility(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"
