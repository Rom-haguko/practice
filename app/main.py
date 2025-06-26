# app/main.py
import io
import os
import secrets
import string
from datetime import date
from typing import Optional, List

import pandas as pd
from fastapi import (Depends, FastAPI, File, Form, HTTPException, Request,
                     Response, UploadFile, status)
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import auth, crud, models, schemas
from .dependencies import get_db

# --- Инициализация приложения ---
# Создаем FastAPI приложение с названием
app = FastAPI(title="Система назначения тем работ")
# Определяем базовые пути для работы с файлами
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
# Подключаем папку static для статических файлов (CSS, JS и т.д.)
app.mount("/static", StaticFiles(directory=os.path.join(PROJECT_ROOT, "static")), name="static")
# Настраиваем Jinja2 для рендеринга HTML-шаблонов
templates = Jinja2Templates(directory=os.path.join(PROJECT_ROOT, "templates"))

# --- Вспомогательные функции ---
def generate_random_password(length=12):
    """Генерирует случайный пароль длиной length из букв, цифр и символов."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for i in range(length))

def get_user_or_redirect(token: str, db: Session):
    """Проверяет токен, возвращает пользователя или перенаправляет на страницу логина."""
    user = auth.get_user_from_token(db, token)
    if not user:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login?error=auth"})
    return user

# =================================================================
# ЭНДПОИНТЫ ДЛЯ ОТОБРАЖЕНИЯ СТРАНИЦ (GET-запросы)
# =================================================================

@app.get("/", response_class=HTMLResponse, tags=["Pages"])
def page_home(request: Request, token: Optional[str] = None, db: Session = Depends(get_db)):
    """Отображает главную страницу, показывая информацию о текущем пользователе, если он авторизован."""
    user = auth.get_user_from_token(db, token) if token else None
    return templates.TemplateResponse("home.html", {"request": request, "current_user": user, "token": token})

@app.get("/login", response_class=HTMLResponse, tags=["Pages"])
def page_login_form(request: Request, error: Optional[str] = None):
    """Отображает форму логина с возможными сообщениями об ошибках."""
    context = {"request": request}
    if error == "1": context["error_message"] = "Неверный логин или пароль."
    if error == "auth": context["error_message"] = "Требуется авторизация. Пожалуйста, войдите."
    return templates.TemplateResponse("login.html", context)

@app.get("/logout", response_class=RedirectResponse, tags=["Pages"])
def page_logout():
    """Обрабатывает выход пользователя, перенаправляя на главную страницу."""
    return RedirectResponse(url="/")

@app.get("/dashboard", response_class=HTMLResponse, tags=["Pages"])
def page_dashboard(request: Request, token: str, db: Session = Depends(get_db)):
    """Отображает панель управления в зависимости от роли пользователя (админ, преподаватель, студент)."""
    user = get_user_or_redirect(token, db)
    # Получаем дедлайн для ВКР из настроек
    deadline_setting = crud.get_setting(db, "vkr_edit_deadline")
    deadline = deadline_setting.setting_value if deadline_setting else "не установлен"
    
    context = {"request": request, "current_user": user, "token": token, "vkr_deadline": deadline}
    
    # Обработка сообщений об ошибках и успехах
    query_params = request.query_params
    if "error" in query_params:
        error_map = { 
            "already_assigned": "Вы уже записаны на другую тему.", 
            "topic_taken": "Эта тема уже занята.", 
            "deadline_passed": "Дедлайн прошел.", 
            "no_topic": "У вас нет темы.", 
            "approved": "Нельзя отписаться от утвержденной темы.", 
            "file_read_error": "Ошибка чтения файла." 
        }
        context["error_message"] = error_map.get(query_params['error'], "Произошла ошибка.")
    if "success" in query_params:
        success_map = { 
            "students_uploaded": "Студенты успешно загружены.", 
            "teachers_uploaded": "Преподаватели успешно загружены.", 
            "deadline_set": "Дедлайн установлен." 
        }
        context["success_message"] = success_map.get(query_params['success'], "Операция выполнена.")

    if user.role == "admin":
        return templates.TemplateResponse("admin_dashboard.html", context)
    
    if user.role == "teacher":
        # Получаем список тем преподавателя
        teacher_topics = crud.get_topics_by_teacher(db, teacher_id=user.id)
        # Проверяем, прошел ли дедлайн для каждой темы
        for topic in teacher_topics:
            topic.deadline_is_passed = crud.is_vkr_deadline_passed(db, topic)
        context["topics"] = teacher_topics
        return templates.TemplateResponse("teacher_dashboard.html", context)
    
    if user.role == "student":
        # Проверяем наличие профиля студента
        if not user.student_profile: 
            return templates.TemplateResponse("error_page.html", context)
        # Получаем все доступные темы и текущую тему студента
        context["all_topics"] = crud.get_all_topics(db)
        context["my_topic"] = crud.get_student_topic(db, student_profile_id=user.student_profile.id)
        return templates.TemplateResponse("student_dashboard.html", context)
    
    return templates.TemplateResponse("error_page.html", context)

@app.get("/topics/create", response_class=HTMLResponse, tags=["Pages"])
def page_create_topic_form(request: Request, token: str, db: Session = Depends(get_db)):
    """Отображает форму для создания новой темы (доступно только преподавателям)."""
    user = get_user_or_redirect(token, db)
    if user.role != 'teacher': 
        raise HTTPException(status_code=403)
    return templates.TemplateResponse("create_topic.html", {"request": request, "current_user": user, "token": token})

@app.get("/teacher/edit-topic/{topic_id}", response_class=HTMLResponse, tags=["Pages"])
def page_edit_topic_form(
    topic_id: int, 
    request: Request, 
    token: str, 
    db: Session = Depends(get_db)
):
    """Отображает форму для редактирования темы, доступно только автору темы."""
    user = get_user_or_redirect(token, db)
    topic = crud.get_topic_by_id(db, topic_id)
    
    # Проверяем права доступа
    if not topic or user.role != 'teacher' or topic.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    context = {
        "request": request,
        "current_user": user,
        "token": token,
        "topic": topic
    }
    return templates.TemplateResponse("edit_topic.html", context)

# =================================================================
# ЭНДПОИНТЫ ДЛЯ ОБРАБОТКИ HTML-ФОРМ (POST-запросы)
# =================================================================

@app.post("/login", response_class=RedirectResponse, tags=["Forms"])
def handle_login_form(username: str = Form(), password: str = Form(), db: Session = Depends(get_db)):
    """Обрабатывает форму логина, создает токен и перенаправляет на dashboard."""
    user = crud.get_user_by_username(db, username)
    if not user or not auth.verify_password(password, user.hashed_password):
        return RedirectResponse(url="/login?error=1", status_code=status.HTTP_302_FOUND)
    access_token = auth.create_access_token(data={"sub": user.username})
    return RedirectResponse(url=f"/dashboard?token={access_token}", status_code=status.HTTP_302_FOUND)

@app.post("/topics/create", response_class=RedirectResponse, tags=["Forms"])
def handle_create_topic(token: str = Form(), title: str = Form(), description: str = Form(""), work_type: str = Form(), db: Session = Depends(get_db)):
    """Создает новую тему для преподавателя после проверки прав и типа работы."""
    user = get_user_or_redirect(token, db)
    if user.role != 'teacher': 
        raise HTTPException(status_code=403)
    VALID_WORK_TYPES = ['coursework', 'vkr', 'vkr/coursework']
    if work_type not in VALID_WORK_TYPES: 
        raise HTTPException(status_code=400)
    topic_data = schemas.TopicCreate(title=title, description=description, work_type=work_type)
    crud.create_teacher_topic(db, topic=topic_data, teacher_id=user.id)
    return RedirectResponse(url=f"/dashboard?token={token}", status_code=status.HTTP_302_FOUND)

@app.post("/student/assign-topic/{topic_id}", response_class=RedirectResponse, tags=["Forms"])
def handle_assign_topic(topic_id: int, token: str = Form(), db: Session = Depends(get_db)):
    """Назначает тему студенту, проверяя доступность темы и наличие у студента других тем."""
    user = get_user_or_redirect(token, db)
    if not user.student_profile: 
        raise HTTPException(status_code=403)
    if crud.get_student_topic(db, student_profile_id=user.student_profile.id):
        return RedirectResponse(url=f"/dashboard?token={token}&error=already_assigned", status_code=status.HTTP_302_FOUND)
    topic = crud.get_topic_by_id(db, topic_id=topic_id)
    if not topic or topic.student_id is not None:
        return RedirectResponse(url=f"/dashboard?token={token}&error=topic_taken", status_code=status.HTTP_302_FOUND)
    crud.assign_topic_to_student(db, topic=topic, student_profile_id=user.student_profile.id)
    return RedirectResponse(url=f"/dashboard?token={token}", status_code=status.HTTP_302_FOUND)

@app.post("/teacher/edit-topic/{topic_id}", response_class=RedirectResponse, tags=["Forms"])
def handle_edit_topic_form(
    topic_id: int,
    token: str = Form(),
    title: str = Form(),
    description: str = Form(""),
    work_type: str = Form(),
    db: Session = Depends(get_db)
):
    """Обрабатывает форму редактирования темы, обновляя данные после проверки прав."""
    user = get_user_or_redirect(token, db)
    topic_to_update = crud.get_topic_by_id(db, topic_id)

    # Проверяем права доступа
    if not topic_to_update or user.role != 'teacher' or topic_to_update.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="Действие запрещено")

    # Проверяем валидность типа работы
    VALID_WORK_TYPES = ['coursework', 'vkr', 'vkr/coursework']
    if work_type not in VALID_WORK_TYPES:
        raise HTTPException(status_code=400, detail="Неверный тип работы.")
        
    # Обновляем тему
    topic_data = schemas.TopicUpdate(
        title=title,
        description=description,
        work_type=work_type
    )
    crud.update_topic(db, topic_to_update=topic_to_update, topic_data=topic_data)
    
    return RedirectResponse(url=f"/dashboard?token={token}", status_code=status.HTTP_302_FOUND)

@app.post("/student/unassign-topic", response_class=RedirectResponse, tags=["Forms"])
def handle_unassign_topic(token: str = Form(), db: Session = Depends(get_db)):
    """Отменяет назначение темы студенту, если она не утверждена и дедлайн не прошел."""
    user = get_user_or_redirect(token, db)
    if not user.student_profile: 
        raise HTTPException(status_code=403)
    topic = crud.get_student_topic(db, student_profile_id=user.student_profile.id)
    if not topic: 
        return RedirectResponse(url=f"/dashboard?token={token}&error=no_topic")
    if topic.is_approved: 
        return RedirectResponse(url=f"/dashboard?token={token}&error=approved")
    if crud.is_vkr_deadline_passed(db, topic): 
        return RedirectResponse(url=f"/dashboard?token={token}&error=deadline_passed")
    crud.unassign_topic_from_student(db, topic=topic)
    return RedirectResponse(url=f"/dashboard?token={token}", status_code=status.HTTP_302_FOUND)

@app.post("/teacher/approve-topic/{topic_id}", response_class=RedirectResponse, tags=["Forms"])
def handle_approve_topic(topic_id: int, token: str = Form(), db: Session = Depends(get_db)):
    """Утверждает назначение темы преподавателем."""
    user = get_user_or_redirect(token, db)
    topic = crud.get_topic_by_id(db, topic_id)
    if not topic or user.role != 'teacher' or topic.teacher_id != user.id: 
        raise HTTPException(status_code=403)
    crud.approve_topic_assignment(db, topic=topic)
    return RedirectResponse(url=f"/dashboard?token={token}", status_code=status.HTTP_302_FOUND)

@app.post("/teacher/unapprove-topic/{topic_id}", response_class=RedirectResponse, tags=["Forms"])
def handle_unapprove_topic(topic_id: int, token: str = Form(), db: Session = Depends(get_db)):
    """Снимает утверждение темы, если дедлайн не прошел."""
    user = get_user_or_redirect(token, db)
    topic = crud.get_topic_by_id(db, topic_id)
    if not topic or user.role != 'teacher' or topic.teacher_id != user.id: 
        raise HTTPException(status_code=403)
    if crud.is_vkr_deadline_passed(db, topic): 
        return RedirectResponse(url=f"/dashboard?token={token}&error=deadline_passed")
    crud.unapprove_topic_assignment(db, topic=topic)
    return RedirectResponse(url=f"/dashboard?token={token}", status_code=status.HTTP_302_FOUND)

@app.post("/teacher/reject-topic/{topic_id}", response_class=RedirectResponse, tags=["Forms"])
def handle_reject_topic(topic_id: int, token: str = Form(), db: Session = Depends(get_db)):
    """Отклоняет назначение темы, если дедлайн не прошел."""
    user = get_user_or_redirect(token, db)
    topic = crud.get_topic_by_id(db, topic_id)
    if not topic or user.role != 'teacher' or topic.teacher_id != user.id: 
        raise HTTPException(status_code=403)
    if crud.is_vkr_deadline_passed(db, topic): 
        return RedirectResponse(url=f"/dashboard?token={token}&error=deadline_passed")
    crud.reject_topic_assignment(db, topic=topic)
    return RedirectResponse(url=f"/dashboard?token={token}", status_code=status.HTTP_302_FOUND)

@app.post("/admin/upload/students", response_class=RedirectResponse, tags=["Forms"])
def handle_upload_students(token: str = Form(), file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Загружает данные студентов из CSV/Excel файла, создает пользователей и профили."""
    user = get_user_or_redirect(token, db)
    if user.role != 'admin': 
        raise HTTPException(status_code=403)
    try:
        df = pd.read_excel(file.file) if file.filename.endswith('.xlsx') else pd.read_csv(file.file)
        required_cols = {'full_name', 'email', 'group'}
        if not required_cols.issubset(df.columns): 
            raise ValueError("Отсутствуют колонки")
    except Exception:
        return RedirectResponse(url=f"/dashboard?token={token}&error=file_read_error", status_code=status.HTTP_302_FOUND)
    
    for _, row in df.iterrows():
        if crud.get_user_by_username(db, username=row['email']): 
            continue
        hashed_password = auth.pwd_context.hash(generate_random_password())
        user_data = schemas.UserBase(username=row['email'], full_name=row['full_name'], role='student')
        new_user = crud.create_user(db, user_data=user_data, hashed_password=hashed_password)
        student_profile = models.Student(user_id=new_user.id, group=row['group'], profile=row.get('profile', ''))
        db.add(student_profile)
        db.commit()
    return RedirectResponse(url=f"/dashboard?token={token}&success=students_uploaded", status_code=status.HTTP_302_FOUND)

@app.post("/admin/upload/teachers", response_class=RedirectResponse, tags=["Forms"])
def handle_upload_teachers(token: str = Form(), file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Загружает данные преподавателей из CSV/Excel файла, создает пользователей и профили."""
    user = get_user_or_redirect(token, db)
    if user.role != 'admin': 
        raise HTTPException(status_code=403)
    try:
        df = pd.read_excel(file.file) if file.filename.endswith('.xlsx') else pd.read_csv(file.file)
        required_cols = {'full_name', 'email', 'position'}
        if not required_cols.issubset(df.columns): 
            raise ValueError("Отсутствуют колонки")
    except Exception:
        return RedirectResponse(url=f"/dashboard?token={token}&error=file_read_error", status_code=status.HTTP_302_FOUND)
    
    for _, row in df.iterrows():
        if crud.get_user_by_username(db, username=row['email']): 
            continue
        hashed_password = auth.pwd_context.hash(generate_random_password())
        user_data = schemas.UserBase(username=row['email'], full_name=row['full_name'], role='teacher')
        new_user = crud.create_user(db, user_data=user_data, hashed_password=hashed_password)
        teacher_profile = models.Teacher(user_id=new_user.id, degree=row.get('degree',''), title=row.get('title', ''), position=row.get('position',''))
        db.add(teacher_profile)
        db.commit()
    return RedirectResponse(url=f"/dashboard?token={token}&success=teachers_uploaded", status_code=status.HTTP_302_FOUND)

@app.post("/admin/settings/vkr-deadline", response_class=RedirectResponse, tags=["Forms"])
def handle_set_vkr_deadline(token: str = Form(), deadline: date = Form(), db: Session = Depends(get_db)):
    """Устанавливает дедлайн для редактирования ВКР."""
    user = get_user_or_redirect(token, db)
    if user.role != 'admin': 
        raise HTTPException(status_code=403)
    crud.set_setting(db, name="vkr_edit_deadline", value=deadline.isoformat())
    return RedirectResponse(url=f"/dashboard?token={token}&success=deadline_set", status_code=status.HTTP_302_FOUND)

# --- Эндпоинты для скачивания файлов ---

@app.get("/admin/report/download", tags=["Downloads"])
def download_report(token: str, db: Session = Depends(get_db)):
    """Генерирует и возвращает Excel-отчет по всем темам."""
    user = get_user_or_redirect(token, db)
    if user.role != 'admin': 
        raise HTTPException(status_code=403)
    all_topics = crud.get_all_topics(db, limit=2000)
    if not all_topics: 
        return Response(content="Нет данных для отчета.", status_code=404)

    report_data = []
    for topic in all_topics:
        student_name = topic.student.user.full_name if topic.student and topic.student.user else ""
        student_status = "Тема закреплена" if topic.student else "Тема свободна"
        teacher_status = "Студент и тема согласованы" if topic.is_approved else "Ожидает согласования"
        if not topic.student: 
            teacher_status = ""
        report_data.append({
            "Тип работы": topic.work_type, 
            "ФИО преподавателя": topic.teacher.full_name,
            "Тема от преподавателя": topic.title, 
            "Описание темы": topic.description or "",
            "ФИО студента": student_name, 
            "Текущий статус для студента": student_status,
            "Статус от преподавателя": teacher_status, 
            "Корректировка темы": ""
        })
    df = pd.DataFrame(report_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Report')
    output.seek(0)
    headers = {'Content-Disposition': 'attachment; filename="coursework_report.xlsx"'}
    return StreamingResponse(output, headers=headers)

@app.get("/admin/reset-passwords/students", tags=["Downloads"])
def download_reset_student_passwords(token: str, db: Session = Depends(get_db)):
    """Сбрасывает пароли студентов и возвращает Excel-файл с новыми учетными данными."""
    user = get_user_or_redirect(token, db)
    if user.role != 'admin': 
        raise HTTPException(status_code=403)
    users_to_reset = crud.get_users_by_role(db, role="student")
    if not users_to_reset: 
        return RedirectResponse(url=f"/dashboard?token={token}&error=no_students_found")

    report_data = []
    for u in users_to_reset:
        new_password = generate_random_password()
        new_hashed_password = auth.pwd_context.hash(new_password)
        crud.change_user_password(db, user=u, new_hashed_password=new_hashed_password)
        report_data.append({"ФИО": u.full_name, "Логин (email)": u.username, "Новый пароль": new_password})
    
    df = pd.DataFrame(report_data)
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    headers = {'Content-Disposition': 'attachment; filename="students_new_credentials.xlsx"'}
    return StreamingResponse(output, headers=headers)

@app.get("/admin/reset-passwords/teachers", tags=["Downloads"])
def download_reset_teacher_passwords(token: str, db: Session = Depends(get_db)):
    """Сбрасывает пароли преподавателей и возвращает Excel-файл с новыми учетными данными."""
    user = get_user_or_redirect(token, db)
    if user.role != 'admin':
        raise HTTPException(status_code=403, detail="Действие доступно только для администраторов")
    users_to_reset = crud.get_users_by_role(db, role="teacher")
    if not users_to_reset:
        return RedirectResponse(url=f"/dashboard?token={token}&error=no_teachers_found")

    report_data = []
    for u in users_to_reset:
        new_password = generate_random_password()
        new_hashed_password = auth.pwd_context.hash(new_password)
        crud.change_user_password(db, user=u, new_hashed_password=new_hashed_password)
        report_data.append({
            "ФИО": u.full_name,
            "Логин (email)": u.username,
            "Новый пароль": new_password
        })
    
    df = pd.DataFrame(report_data)
    output = io.BytesIO()
    df.to_excel(output, index=False, sheet_name='Teacher Credentials')
    output.seek(0)
    headers = {'Content-Disposition': 'attachment; filename="teachers_new_credentials.xlsx"'}
    return StreamingResponse(output, headers=headers)
