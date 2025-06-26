# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Класс для хранения настроек приложения, загружаемых из переменных окружения или значений по умолчанию."""
    # Секретный ключ для подписи JWT-токенов
    # ВАЖНО: В реальном приложении этот ключ должен быть сгенерирован
    # командой `openssl rand -hex 32` и храниться в .env файле
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    # Алгоритм шифрования для JWT-токенов
    ALGORITHM: str = "HS256"
    # Время жизни токена в минутах
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

# Создаем экземпляр настроек для использования в приложении
settings = Settings()
