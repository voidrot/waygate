from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import concrete model modules here so Alembic autogenerate can see their tables.
# Example:
# from .document import Document
