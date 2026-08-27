import os
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, String, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local_test.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class FoodModel(Base):
    __tablename__ = "foods"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    category = Column(String, default="Ostatní")
    kcalPer100g = Column(Float, nullable=False)
    proteinPer100g = Column(Float, nullable=False)
    carbsPer100g = Column(Float, nullable=False)
    fatPer100g = Column(Float, nullable=False)
    fiberPer100g = Column(Float, default=0.0)
    sugarPer100g = Column(Float, default=0.0)
    saltPer100g = Column(Float, default=0.0)
    sourceTag = Column(String, default="USER_COMMUNITY")

Base.metadata.create_all(bind=engine)

class FoodSchema(BaseModel):
    id: str
    name: str
    category: str
    kcalPer100g: float
    proteinPer100g: float
    carbsPer100g: float
    fatPer100g: float
    fiberPer100g: Optional[float] = 0.0
    sugarPer100g: Optional[float] = 0.0
    saltPer100g: Optional[float] = 0.0
    sourceTag: Optional[str] = "USER_COMMUNITY"

    class Config:
        orm_mode = True

app = FastAPI(title="Kalorické Tabulky API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"status": "ok", "message": "Kaloricke Tabulky API bezi online"}

@app.get("/api/foods/barcode/{barcode}", response_model=FoodSchema)
def get_food_by_barcode(barcode: str, db: Session = Depends(get_db)):
    food = db.query(FoodModel).filter(FoodModel.id == barcode).first()
    if not food:
        raise HTTPException(status_code=404, detail="Potravina s timto EAN nebyla nalezena")
    return food

@app.get("/api/foods/search", response_model=List[FoodSchema])
def search_foods(query: str, db: Session = Depends(get_db)):
    if not query.strip():
        return []
    return db.query(FoodModel).filter(FoodModel.name.ilike(f"%{query}%")).limit(25).all()

@app.post("/api/foods", response_model=FoodSchema, status_code=status.HTTP_201_CREATED)
def create_or_update_food(food: FoodSchema, db: Session = Depends(get_db)):
    existing_food = db.query(FoodModel).filter(FoodModel.id == food.id).first()
    if existing_food:
        for key, value in food.dict().items():
            setattr(existing_food, key, value)
        db.commit()
        db.refresh(existing_food)
        return existing_food

    new_food = FoodModel(**food.dict())
    db.add(new_food)
    db.commit()
    db.refresh(new_food)
    return new_food
