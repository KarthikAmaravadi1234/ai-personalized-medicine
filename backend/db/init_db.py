import backend.models.orm  # noqa: F401  (ensures all models are registered on Base.metadata)
from backend.db.engine import get_engine
from backend.models.orm import Base


def init_db() -> None:
    """Create all tables that do not yet exist.

    Lightweight bootstrap for development. Replace with Alembic migrations
    once the schema starts changing.
    """
    Base.metadata.create_all(bind=get_engine())


if __name__ == "__main__":
    init_db()
    print("Database tables created.")
