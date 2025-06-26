# app/schemas.py
from pydantic import BaseModel
from typing import Optional, List

# --- Схемы для пользователей ---
class UserBase(BaseModel):
    """Базовая схема для пользователя, содержащая основные поля."""
    username: str  # Имя пользователя (email)
    full_name: str  # Полное имя пользователя
    role: str  # Роль пользователя (admin, teacher, student)

class UserCreate(UserBase):
    """Схема для создания пользователя, расширяет UserBase с паролем."""
    password: str  # Пароль пользователя (не хэшированный)

class User(UserBase):
    """Схема пользователя с идентификатором для возврата данных."""
    id: int  # Уникальный идентификатор пользователя
    class Config:
        from_attributes = True  # Позволяет создавать экземпляры из ORM-объектов

# --- Схемы для профилей ---
class Student(BaseModel):
    """Схема профиля студента."""
    id: int  # Уникальный идентификатор профиля
    group: str  # Учебная группа студента
    profile: Optional[str] = None  # Дополнительная информация о профиле (опционально)
    user: User  # Связанный пользователь
    class Config:
        from_attributes = True  # Позволяет создавать экземпляры из ORM-объектов

# --- Схемы для тем ---
class TopicBase(BaseModel):
    """Базовая схема для темы курсовой или ВКР."""
    title: str  # Название темы
    description: Optional[str] = None  # Описание темы (опционально)
    work_type: str  # Тип работы (coursework, vkr, vkr/coursework)

class TopicCreate(TopicBase):
    """Схема для создания новой темы, наследуется от TopicBase."""
    pass

class TopicUpdate(BaseModel):
    """Схема для обновления темы, все поля опциональны."""
    title: Optional[str] = None  # Новое название темы (опционально)
    description: Optional[str] = None  # Новое описание темы (опционально)
    work_type: Optional[str] = None  # Новый тип работы (опционально)

class Topic(TopicBase):
    """Схема темы с дополнительными полями для возврата данных."""
    id: int  # Уникальный идентификатор темы
    is_approved: bool  # Флаг утверждения темы
    teacher: User  # Преподаватель, создавший тему
    student: Optional[Student] = None  # Студент, назначенный на тему (опционально)
    class Config:
        from_attributes = True  # Позволяет создавать экземпляры из ORM-объектов
