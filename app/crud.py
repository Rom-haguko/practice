# app/crud.py
from sqlalchemy.orm import Session, joinedload
from datetime import date
from . import models, schemas

# --- CRUD операции для пользователей ---
def get_user_by_username(db: Session, username: str):
    """Возвращает пользователя по его имени (email) из базы данных."""
    return db.query(models.User).filter(models.User.username == username).first()

def get_users_by_role(db: Session, role: str):
    """Возвращает список пользователей с указанной ролью."""
    return db.query(models.User).filter(models.User.role == role).all()

def create_user(db: Session, user_data: schemas.UserBase, hashed_password: str):
    """Создает нового пользователя в базе данных с хэшированным паролем."""
    db_user = models.User(**user_data.dict(), hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- CRUD операции для тем ---
def get_topic_by_id(db: Session, topic_id: int):
    """Возвращает тему по её идентификатору."""
    return db.query(models.Topic).filter(models.Topic.id == topic_id).first()

def get_all_topics(db: Session, skip: int = 0, limit: int = 100):
    """Возвращает список всех тем с данными о преподавателе и студенте."""
    return db.query(models.Topic).options(
        joinedload(models.Topic.teacher),
        joinedload(models.Topic.student).joinedload(models.Student.user)
    ).offset(skip).limit(limit).all()

def get_topics_by_teacher(db: Session, teacher_id: int):
    """Возвращает список тем, созданных указанным преподавателем."""
    return db.query(models.Topic).filter(models.Topic.teacher_id == teacher_id).all()

def get_student_topic(db: Session, student_profile_id: int):
    """Возвращает тему, назначенную указанному студенту."""
    return db.query(models.Topic).filter(models.Topic.student_id == student_profile_id).first()

def create_teacher_topic(db: Session, topic: schemas.TopicCreate, teacher_id: int):
    """Создает новую тему для преподавателя."""
    db_topic = models.Topic(**topic.dict(), teacher_id=teacher_id)
    db.add(db_topic)
    db.commit()
    db.refresh(db_topic)
    return db_topic

def assign_topic_to_student(db: Session, topic: models.Topic, student_profile_id: int):
    """Назначает тему студенту, обновляя поле student_id."""
    topic.student_id = student_profile_id
    db.commit()
    db.refresh(topic)
    return topic

def unassign_topic_from_student(db: Session, topic: models.Topic):
    """Снимает назначение темы со студента и сбрасывает статус утверждения."""
    topic.student_id = None
    topic.is_approved = False
    db.commit()
    db.refresh(topic)
    return topic

def approve_topic_assignment(db: Session, topic: models.Topic):
    """Утверждает назначение темы преподавателем."""
    topic.is_approved = True
    db.commit()
    db.refresh(topic)
    return topic

def reject_topic_assignment(db: Session, topic: models.Topic):
    """Отклоняет назначение темы, сбрасывая студента и статус утверждения."""
    topic.student_id = None
    topic.is_approved = False
    db.commit()
    db.refresh(topic)
    return topic

# --- CRUD операции для системных настроек и дедлайнов ---
def get_setting(db: Session, name: str):
    """Возвращает системную настройку по её имени."""
    return db.query(models.SystemSettings).filter(models.SystemSettings.setting_name == name).first()

def set_setting(db: Session, name: str, value: str):
    """Устанавливает или обновляет значение системной настройки."""
    setting = get_setting(db, name)
    if setting:
        setting.setting_value = value
    else:
        db.add(models.SystemSettings(setting_name=name, setting_value=value))
    db.commit()
    return setting

def is_vkr_deadline_passed(db: Session, topic: models.Topic) -> bool:
    """Проверяет, истек ли дедлайн для редактирования ВКР."""
    if topic.work_type != 'vkr':
        return False
    setting = get_setting(db, name="vkr_edit_deadline")
    if setting and setting.setting_value:
        try:
            return date.today() > date.fromisoformat(setting.setting_value)
        except (ValueError, TypeError):
            return False
    return False

def change_user_password(db: Session, user: models.User, new_hashed_password: str):
    """Обновляет хэшированный пароль для указанного пользователя."""
    user.hashed_password = new_hashed_password
    db.add(user)
    db.commit()
    return True

def update_topic(db: Session, topic_to_update: models.Topic, topic_data: schemas.TopicUpdate):
    """Обновляет данные темы на основе переданной Pydantic-схемы."""
    # Получаем данные из схемы, игнорируя неустановленные поля
    update_data = topic_data.dict(exclude_unset=True)
    # Обновляем атрибуты темы
    for key, value in update_data.items():
        setattr(topic_to_update, key, value)
    db.add(topic_to_update)
    db.commit()
    db.refresh(topic_to_update)
    return topic_to_update
