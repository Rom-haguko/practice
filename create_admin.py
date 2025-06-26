# create_admin.py
import getpass
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas, auth
from app.database import Base, engine

# Создаем все таблицы в базе данных (если их еще нет)
print("Проверка и создание таблиц в базе данных...")
Base.metadata.create_all(bind=engine)
print("Таблицы созданы/проверены.")

# Создаем сессию для работы с БД
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def create_admin_user():
    """Интерактивная утилита для создания администратора."""
    print("\n--- Создание учетной записи администратора ---")
  
    username = input("Введите логин (email) для админа: ")
    full_name = input("Введите ФИО админа: ")
    password = getpass.getpass("Введите пароль для админа: ")
    password_confirm = getpass.getpass("Подтвердите пароль: ")
    
    if password != password_confirm:
        print("\n[ОШИБКА] Пароли не совпадают. Попробуйте снова.")
        return

    # Проверяем, не занят ли уже такой username
    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        print(f"\n[ОШИБКА] Пользователь с логином '{username}' уже существует.")
        return

    try:
        # Хешируем пароль
        hashed_password = auth.pwd_context.hash(password)
        
        # Создаем пользователя с ролью 'admin'
        user_data = schemas.UserBase(
            username=username,
            full_name=full_name,
            role='admin'
        )
        
        db_user = models.User(**user_data.dict(), hashed_password=hashed_password)
        
        db.add(db_user)
        db.commit()
        
        print(f"\n[УСПЕХ] Администратор '{full_name}' ({username}) успешно создан!")

    except Exception as e:
        db.rollback() # Откатываем изменения в случае ошибки
        print(f"\n[ОШИБКА] Произошла ошибка при создании пользователя: {e}")
    finally:
        db.close() # Всегда закрываем сессию

if __name__ == "__main__":
    create_admin_user()
