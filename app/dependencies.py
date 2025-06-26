# app/dependencies.py
from .database import SessionLocal

def get_db():
    """Создает сессию базы данных для запроса и закрывает её после завершения."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
