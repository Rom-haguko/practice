# list_users.py
import sys
from sqlalchemy.orm import sessionmaker
from prettytable import PrettyTable

sys.path.append('.')

# --- Импорты из нашего FastAPI приложения ---
from app import models
from app.database import engine

# Создаем сессию для работы с БД
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def show_all_users():
    """
    Выводит всех пользователей из базы данных в виде красивой таблицы.
    """
    print("\n--- Список всех пользователей в базе данных ---")
    
    try:
        # Получаем всех пользователей из таблицы User
        all_users = db.query(models.User).all()

        if not all_users:
            print("\n[ИНФО] База данных пользователей пуста.")
            return

        # Создаем таблицу для красивого вывода
        # Для этого нужно установить библиотеку: pip install prettytable
        table = PrettyTable()
        table.field_names = ["ID", "Username (Login)", "Full Name", "Role", "Hashed Password"]
        table.align["Hashed Password"] = "l" # Выравнивание по левому краю для длинного хеша

        for user in all_users:
            table.add_row([
                user.id,
                user.username,
                user.full_name,
                user.role,
                user.hashed_password  # Выводим именно хеш
            ])
        
        print(table)

    except Exception as e:
        print(f"\n[ОШИБКА] Не удалось получить пользователей: {e}")
    finally:
        db.close() # Всегда закрываем сессию

if __name__ == "__main__":
    # Проверка на наличие библиотеки prettytable
    try:
        from prettytable import PrettyTable
    except ImportError:
        print("\n[ПРЕДУПРЕЖДЕНИЕ] Библиотека 'prettytable' не найдена.")
        print("Пожалуйста, установите ее для красивого вывода: pip install prettytable")
        # Тут можно было бы выйти, но давайте сделаем простой вывод для случая без библиотеки
        print("\n--- Простой вывод ---")
        show_all_users() # Попытаемся запустить без таблицы
        sys.exit()

    show_all_users()
