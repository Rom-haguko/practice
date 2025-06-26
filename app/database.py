# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL базы данных SQLite, указывающий на файл coursework.db в корне проекта
SQLALCHEMY_DATABASE_URL = "sqlite:///./coursework.db"

# Создаем движок SQLAlchemy для взаимодействия с базой данных
# connect_args={"check_same_thread": False} отключает проверку потоков для SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Создаем фабрику сессий для работы с базой данных
# autocommit=False и autoflush=False обеспечивают явное управление транзакциями
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем базовый класс для моделей SQLAlchemy
# Все модели (например, User, Student, Topic) будут наследоваться от этого класса
Base = declarative_base()
