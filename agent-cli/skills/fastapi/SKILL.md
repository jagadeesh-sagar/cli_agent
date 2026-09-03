---
name: fastapi
description: FastAPI app structure, routing, Pydantic schemas, dependency injection, async patterns. Use when building or reviewing a FastAPI backend.
---

# FastAPI

## Project Structure
```
app/
  main.py          # FastAPI() instance + include_router
  routers/         # one file per domain (users.py, products.py)
  schemas/         # Pydantic request/response models
  models/          # SQLAlchemy ORM models
  deps.py          # shared dependencies (get_db, get_current_user)
  database.py      # engine + SessionLocal + Base
```

## App Setup
```python
from fastapi import FastAPI
from app.routers import users, products

app = FastAPI(title="My API", version="1.0.0")
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(products.router, prefix="/products", tags=["products"])
```

## Router Pattern
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import schemas, models
from app.deps import get_db

router = APIRouter()

@router.get("/", response_model=list[schemas.Product])
def list_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()

@router.get("/{id}", response_model=schemas.Product)
def get_product(id: int, db: Session = Depends(get_db)):
    item = db.query(models.Product).get(id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return item

@router.post("/", response_model=schemas.Product, status_code=status.HTTP_201_CREATED)
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db)):
    item = models.Product(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item
```

## Pydantic Schemas
```python
from pydantic import BaseModel

class ProductBase(BaseModel):
    name: str
    price: float

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    class Config:
        from_attributes = True   # replaces orm_mode in Pydantic v2
```

## Database (SQLAlchemy)
```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

# deps.py
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Auth (JWT)
```python
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user = db.query(User).get(payload["sub"])
    if not user:
        raise HTTPException(status_code=401)
    return user
```

## Rules
- Always use `response_model=` to control serialization
- Never return ORM objects directly — always go through a schema
- Use `status_code=201` for POST, `204` for DELETE
- Run with: `uvicorn app.main:app --reload`
- Generate migration: `alembic revision --autogenerate -m "description"`
