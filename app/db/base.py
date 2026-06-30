from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass


# Ensures all models are registered on Base.metadata as soon as
# Base itself is imported anywhere — see app/models/__init__.py.
import app.models  # noqa: E402,F401
