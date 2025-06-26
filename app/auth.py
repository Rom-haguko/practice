# app/auth.py
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import config, crud, models

# Инициализация контекста для хэширования паролей с использованием bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет, соответствует ли введенный пароль хэшированному паролю."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    """Создает JWT-токен с временем истечения, основанным на настройках."""
    to_encode = data.copy()
    # Устанавливаем время истечения токена
    expire = datetime.now(timezone.utc) + timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # Кодируем токен с использованием секретного ключа и алгоритма
    return jwt.encode(to_encode, config.settings.SECRET_KEY, algorithm=config.settings.ALGORITHM)

def get_user_from_token(db: Session, token: str) -> Optional[models.User]:
    """Извлекает пользователя из JWT-токена, если токен валиден."""
    if not token:
        return None
    try:
        # Декодируем токен с использованием секретного ключа
        payload = jwt.decode(token, config.settings.SECRET_KEY, algorithms=[config.settings.ALGORITHM])
        # Извлекаем имя пользователя из поля 'sub'
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        # Возвращаем None в случае ошибки декодирования
        return None
    # Получаем пользователя из базы данных по имени пользователя
    return crud.get_user_by_username(db, username=username)
