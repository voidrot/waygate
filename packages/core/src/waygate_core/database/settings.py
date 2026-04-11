import os

database_url = f"postgresql'://{os.getenv('PG_USER', 'postgres')}:{os.getenv('PG_PASSWORD', 'postgres')}@{os.getenv('PG_HOST', 'localhost')}:{os.getenv('PG_PORT', '5432')}/{os.getenv('PG_DB', 'postgres')}"


TORTOISE_ORM = {
    "connections": {
        "default": database_url,
    },
    "apps": {
        "core": {
            "models": ["waygate_core.database.models"],
            "default_connection": "default",
            "migrations": "waygate_core.database.migrations",
        }
    },
}
