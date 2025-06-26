# app/models.py
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    """Модель пользователя, представляющая таблицу users в базе данных."""
    __tablename__ = "users"

    # Уникальный идентификатор пользователя
    id = Column(Integer, primary_key=True, index=True)
    # Полное имя пользователя
    full_name = Column(String, index=True)
    # Уникальное имя пользователя (email)
    username = Column(String, unique=True, index=True)
    # Хэшированный пароль
    hashed_password = Column(String)
    # Роль пользователя (admin, teacher, student)
    role = Column(String, index=True)
    # Связь с профилем студента (один к одному)
    student_profile = relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    # Связь с профилем преподавателя (один к одному)
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False, cascade="all, delete-orphan")
    # Список тем, созданных пользователем (преподавателем)
    created_topics = relationship("Topic", foreign_keys="[Topic.teacher_id]", back_populates="teacher")

class Student(Base):
    """Модель профиля студента, представляющая таблицу students в базе данных."""
    __tablename__ = "students"

    # Уникальный идентификатор профиля студента
    id = Column(Integer, primary_key=True, index=True)
    # Учебная группа студента
    group = Column(String, index=True)
    # Дополнительная информация о профиле (опционально)
    profile = Column(String, nullable=True)
    # Внешний ключ, связывающий с пользователем
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    # Связь с пользователем (один к одному)
    user = relationship("User", back_populates="student_profile")
    # Связь с темой студента (один к одному)
    topic = relationship("Topic", back_populates="student", uselist=False)

class Teacher(Base):
    """Модель профиля преподавателя, представляющая таблицу teachers в базе данных."""
    __tablename__ = "teachers"

    # Уникальный идентификатор профиля преподавателя
    id = Column(Integer, primary_key=True, index=True)
    # Ученая степень преподавателя (опционально)
    degree = Column(String, nullable=True)
    # Ученое звание преподавателя (опционально)
    title = Column(String, nullable=True)
    # Должность преподавателя
    position = Column(String)
    # Внешний ключ, связывающий с пользователем
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    # Связь с пользователем (один к одному)
    user = relationship("User", back_populates="teacher_profile")

class Topic(Base):
    """Модель темы курсовой или ВКР, представляющая таблицу topics в базе данных."""
    __tablename__ = "topics"

    # Уникальный идентификатор темы
    id = Column(Integer, primary_key=True, index=True)
    # Название темы
    title = Column(String, index=True)
    # Описание темы (опционально)
    description = Column(Text, nullable=True)
    # Тип работы (coursework, vkr, vkr/coursework)
    work_type = Column(String)
    # Флаг утверждения темы преподавателем
    is_approved = Column(Boolean, default=False)
    # Внешний ключ, связывающий с преподавателем (пользователем)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Внешний ключ, связывающий со студентом (опционально)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True, unique=True)
    # Связь с преподавателем
    teacher = relationship("User", foreign_keys=[teacher_id], back_populates="created_topics")
    # Связь со студентом
    student = relationship("Student", back_populates="topic")

class SystemSettings(Base):
    """Модель системных настроек, представляющая таблицу system_settings в базе данных."""
    __tablename__ = "system_settings"

    # Имя настройки (уникальный ключ)
    setting_name = Column(String, primary_key=True, index=True)
    # Значение настройки
    setting_value = Column(String)
