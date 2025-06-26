# app/init_db.py

# Импортируем необходимые компоненты из пакета 'app'
from app.database import engine, Base  # Подключение к базе данных и базовый класс SQLAlchemy
from app.models import User, Student, Teacher, Topic  # Импортируем модели для создания таблиц

def create_database():
    """
    Создаёт все таблицы в базе данных на основе определённых моделей.
    """
    print("Начинаем создание таблиц...")  # Информируем о начале процесса
    # Создаёт таблицы в базе данных для всех моделей, унаследованных от Base
    Base.metadata.create_all(bind=engine)
    print("База данных и таблицы успешно созданы!")  # Подтверждаем успешное завершение

if __name__ == "__main__":
    # Выполняется только при прямом запуске файла (например, python init_db.py)
    create_database()
