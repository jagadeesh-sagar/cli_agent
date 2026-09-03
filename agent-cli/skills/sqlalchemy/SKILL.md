---
name: sqlalchemy
description: SQLAlchemy ORM models, relationships, queries, migrations with Alembic. Use when defining database models or writing queries.
---

# SQLAlchemy ORM

## Model Definition
```python
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id:         Mapped[int]   = mapped_column(primary_key=True)
    email:      Mapped[str]   = mapped_column(String(255), unique=True, index=True)
    name:       Mapped[str]   = mapped_column(String(100))
    created_at: Mapped[DateTime] = mapped_column(server_default=func.now())

    orders:     Mapped[list["Order"]] = relationship(back_populates="user")

class Order(Base):
    __tablename__ = "orders"

    id:      Mapped[int]   = mapped_column(primary_key=True)
    total:   Mapped[float] = mapped_column(Float, nullable=False)
    user_id: Mapped[int]   = mapped_column(ForeignKey("users.id"))

    user:    Mapped["User"] = relationship(back_populates="orders")
```

## Queries (2.0 style)
```python
from sqlalchemy import select

# fetch one
user = db.scalar(select(User).where(User.email == "x@y.com"))

# fetch many
users = db.scalars(select(User).order_by(User.name)).all()

# filter + join
orders = db.scalars(
    select(Order).join(User).where(User.email == "x@y.com")
).all()

# count
from sqlalchemy import func
count = db.scalar(select(func.count()).select_from(User))
```

## CRUD Pattern
```python
def create_user(db, email: str, name: str) -> User:
    user = User(email=email, name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def delete_user(db, user_id: int) -> None:
    user = db.get(User, user_id)
    if user:
        db.delete(user)
        db.commit()
```

## Alembic Migrations
```bash
# Setup (once)
alembic init alembic
# Edit alembic.ini: sqlalchemy.url = sqlite:///./app.db
# Edit alembic/env.py: target_metadata = Base.metadata

# Workflow
alembic revision --autogenerate -m "add orders table"
alembic upgrade head
alembic downgrade -1     # rollback one step
alembic history          # see all revisions
```

## Rules
- Use `Mapped[]` type annotations (SQLAlchemy 2.0) — not `Column()`
- Always `db.refresh(obj)` after commit to get DB-generated fields
- Use `db.get(Model, pk)` for primary key lookups — faster than `select`
- Load relationships explicitly with `.options(selectinload(User.orders))`
- Never use `db.query()` — that's the legacy 1.x API
