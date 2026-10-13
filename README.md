# Сайт приватної клініки «Верес»

Flask + Jinja2 + SQLite. Дизайн у Figma, публікація на GitHub Pages.

## Запуск локально (повна версія з БД і адмінкою)
```bash
python -m venv venv
venv\Scripts\activate        # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python app.py                # http://127.0.0.1:5000
```
Адмінка: `/login/`, логін `admin`, пароль `admin123` (змінюється змінною `ADMIN_PASS`).

## Що реалізовано (за планом курсу)
- Шаблонізація Jinja2: `base.html` + сторінки (Лекція №3, Практична №2)
- Форма запису, GET/POST, валідація, сесії, вхід/вихід (Лекція №4, Практична №3)
- SQLite: послуги й лікарі виводяться з БД (Лекція №5)
- CRUD заявок в адмінці: перегляд, додавання через форму, зміна статусу, видалення (Лекція №6, Практична №4)

## Публікація на GitHub Pages
GitHub Pages не запускає Python, тому `freeze.py` (Frozen-Flask) збирає сайт у статичні HTML у `build/`.
У статичній версії форма запису зберігає заявки в `localStorage` браузера, адмінки там немає.

1. Створіть репозиторій на GitHub і виконайте:
   ```bash
   git init && git add . && git commit -m "Clinic website"
   git branch -M main
   git remote add origin https://github.com/<ваш-логін>/<репозиторій>.git
   git push -u origin main
   ```
2. У репозиторії: **Settings → Pages → Source: GitHub Actions**.
3. Після пушу workflow `.github/workflows/pages.yml` збере й опублікує сайт:
   `https://<ваш-логін>.github.io/<репозиторій>/`

Перевірка збірки локально: `python freeze.py`, потім відкрийте `build/index.html`.

## Дизайн
Опис макета, стилів і компонентів: [design/figma-spec.md](design/figma-spec.md).
