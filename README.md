# SkillHub API

REST API платформи онлайн-курсів (Django + Django REST Framework).

## Стек

- Python 3.12+
- Django / Django REST Framework
- SQLite
- drf-spectacular (OpenAPI / Swagger)
- bcrypt

## Запуск проєкту

1. Створити та активувати віртуальне середовище:
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

2. Встановити залежності:
```powershell
pip install -r requirements.txt
```

3. Налаштувати змінні середовища:
Скопіювати `.env.example` у `.env` та вказати `SECRET_KEY`.

4. Виконати міграції та запустити сервер:
```powershell
python manage.py migrate
python manage.py runserver
```

## Основні маршрути

- `GET /swagger/` — документація Swagger UI
- `GET /health/` — перевірка стану сервера
- `POST /api/auth/register/` — реєстрація користувача
- `POST /api/auth/login/` — вхід користувача
- `GET /api/categories/`, `POST /api/categories/` — категорії курсів
- `GET /api/courses/`, `POST /api/courses/` — список та створення курсів
- `GET /api/courses/{id}/`, `PUT /api/courses/{id}/`, `DELETE /api/courses/{id}/` — деталі, оновлення та видалення курсу
- `POST /api/courses/{id}/cover/`, `GET /api/courses/{id}/cover/`, `DELETE /api/courses/{id}/cover/` — обкладинка курсу
- `GET /api/courses/{id}/enrollments/`, `POST /api/courses/{id}/enrollments/` — записи студентів на курс
- `GET /api/jobs/{job_id}/` — статус фонової задачі

## Тести

```powershell
python manage.py test
```
