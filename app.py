import os, re, sqlite3
from datetime import date
from functools import wraps
from flask import Flask, g, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
DB = os.path.join(app.root_path, "clinic.db")
SCHEMA = os.path.join(app.root_path, "schema.sql")
STATIC_BUILD = os.environ.get("STATIC_BUILD") == "1"
CLINIC = "Верес"

SERVICES = [
    ("Терапевт", "Первинний прийом, діагностика, план лікування", 700),
    ("Кардіолог", "ЕКГ, тиск, обстеження серця", 1100),
    ("Невролог", "Головний біль, біль у спині, запаморочення", 1000),
    ("Педіатр", "Огляд дітей від народження, щеплення", 800),
    ("УЗД", "Органи черевної порожнини, щитоподібна залоза", 900),
    ("Лабораторія", "Загальні та біохімічні аналізи, результат за 1 день", 350),
]
DOCTORS = [
    ("Олена Коваленко", "Терапевт", 14, "Лікар вищої категорії. Веде пацієнтів з хронічними захворюваннями.",
     "Дніпровський державний медичний університет, 2010", "Пн, Ср, Пт 8:00–14:00"),
    ("Андрій Мельник", "Кардіолог", 18, "Кандидат медичних наук. Спеціалізується на гіпертонії.",
     "Національний медичний університет ім. О. Богомольця, 2006", "Вт, Чт 10:00–18:00"),
    ("Ірина Шевченко", "Невролог", 11, "Працює з болем у спині та мігренями.",
     "Запорізький державний медичний університет, 2013", "Пн–Пт 14:00–20:00"),
    ("Максим Бондаренко", "Педіатр", 9, "Приймає дітей від народження, проводить вакцинацію.",
     "Дніпровський державний медичний університет, 2015", "Пн–Сб 9:00–15:00"),
]
DOCTOR_FIELDS = ("name", "service_id", "experience", "bio", "education", "schedule")
DOCTORS_SQL = """SELECT d.*, s.name AS speciality FROM doctors d
                 JOIN services s ON s.id = d.service_id"""


def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def db():
    if "db" not in g:
        g.db = connect()
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def init_db():
    c = connect()
    with open(SCHEMA, encoding="utf-8") as f:
        c.executescript(f.read())
    if not c.execute("SELECT COUNT(*) FROM services").fetchone()[0]:
        c.executemany("INSERT INTO services(name, description, price) VALUES (?, ?, ?)", SERVICES)
    if not c.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]:
        for name, spec, exp, bio, edu, sched in DOCTORS:
            sid = c.execute("SELECT id FROM services WHERE name = ?", (spec,)).fetchone()[0]
            c.execute("""INSERT INTO doctors(name, service_id, experience, bio, education, schedule)
                         VALUES (?, ?, ?, ?, ?, ?)""", (name, sid, exp, bio, edu, sched))
    if not c.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        c.execute("INSERT INTO users(username, password_hash) VALUES (?, ?)",
                  ("admin", generate_password_hash(os.environ.get("ADMIN_PASS", "veres2026"))))
    c.commit()
    c.close()


@app.context_processor
def inject():
    return dict(clinic=CLINIC, static_build=STATIC_BUILD, year=date.today().year)


def validate_appointment(form):
    errors = {}
    if len(form.get("name", "").strip()) < 2:
        errors["name"] = "Введіть ім'я (мінімум 2 літери)"
    if not re.fullmatch(r"\+?[0-9 ()\-]{10,16}", form.get("phone", "").strip()):
        errors["phone"] = "Введіть телефон, наприклад +380501234567"
    did = form.get("doctor_id", "")
    if not did.isdigit() or not db().execute("SELECT 1 FROM doctors WHERE id = ?", (did,)).fetchone():
        errors["doctor_id"] = "Оберіть лікаря"
    d = form.get("visit_date", "")
    if not d or d < date.today().isoformat():
        errors["visit_date"] = "Оберіть дату не раніше сьогодні"
    return errors


def validate_doctor(form):
    errors = {}
    if len(form.get("name", "").strip()) < 3:
        errors["name"] = "Введіть ПІБ лікаря"
    sid = form.get("service_id", "")
    if not sid.isdigit() or not db().execute("SELECT 1 FROM services WHERE id = ?", (sid,)).fetchone():
        errors["service_id"] = "Оберіть спеціальність"
    if not form.get("experience", "").strip().isdigit():
        errors["experience"] = "Стаж: ціле число років"
    return errors


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not session.get("user"):
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrapper


@app.route("/")
def index():
    return render_template("index.html",
                           services=db().execute("SELECT * FROM services ORDER BY id").fetchall(),
                           doctors=db().execute(DOCTORS_SQL + " ORDER BY d.id").fetchall())


@app.route("/doctors/<int:did>/")
def doctor(did):
    d = db().execute(DOCTORS_SQL + " WHERE d.id = ?", (did,)).fetchone()
    if not d:
        abort(404)
    return render_template("doctor.html", d=d)


@app.route("/appointment/", methods=["GET", "POST"])
def appointment():
    docs = db().execute(DOCTORS_SQL + " ORDER BY d.name").fetchall()
    errors, form = {}, {"doctor_id": request.args.get("doctor", "")}
    if request.method == "POST":
        form = request.form
        errors = validate_appointment(form)
        if not errors:
            db().execute("""INSERT INTO appointments(name, phone, doctor_id, visit_date, comment)
                            VALUES (?, ?, ?, ?, ?)""",
                         (form["name"].strip(), form["phone"].strip(), int(form["doctor_id"]),
                          form["visit_date"], form.get("comment", "").strip()))
            db().commit()
            flash("Заявку прийнято. Ми зателефонуємо протягом години.")
            return redirect(url_for("appointment"))
    return render_template("appointment.html", doctors=docs, errors=errors, form=form)


@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = db().execute("SELECT * FROM users WHERE username = ?",
                            (request.form.get("user", "").strip(),)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["user"] = user["username"]
            return redirect(url_for("admin"))
        flash("Невірний логін або пароль")
    return render_template("login.html")


@app.route("/logout/")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/admin/")
@login_required
def admin():
    rows = db().execute("""SELECT a.*, d.name AS doctor FROM appointments a
                           LEFT JOIN doctors d ON d.id = a.doctor_id ORDER BY a.id DESC""").fetchall()
    docs = db().execute(DOCTORS_SQL + " ORDER BY d.id").fetchall()
    return render_template("admin.html", rows=rows, doctors=docs)


@app.route("/admin/doctor/new/", methods=["GET", "POST"], defaults={"did": None})
@app.route("/admin/doctor/<int:did>/", methods=["GET", "POST"])
@login_required
def doctor_edit(did):
    d = None
    if did is not None:
        d = db().execute("SELECT * FROM doctors WHERE id = ?", (did,)).fetchone()
        if not d:
            abort(404)
    form, errors = (dict(d) if d else {}), {}
    if request.method == "POST":
        form = request.form
        errors = validate_doctor(form)
        if not errors:
            vals = [form.get(k, "").strip() for k in DOCTOR_FIELDS]
            vals[1], vals[2] = int(vals[1]), int(vals[2])
            if d:
                db().execute("""UPDATE doctors SET name = ?, service_id = ?, experience = ?, bio = ?,
                                education = ?, schedule = ? WHERE id = ?""", (*vals, did))
                flash("Дані лікаря оновлено")
            else:
                db().execute("""INSERT INTO doctors(name, service_id, experience, bio, education, schedule)
                                VALUES (?, ?, ?, ?, ?, ?)""", vals)
                flash("Лікаря додано")
            db().commit()
            return redirect(url_for("admin"))
    services = db().execute("SELECT id, name FROM services ORDER BY name").fetchall()
    return render_template("doctor_form.html", d=d, form=form, errors=errors, services=services)


@app.route("/admin/doctor/<int:did>/delete", methods=["POST"])
@login_required
def doctor_delete(did):
    db().execute("DELETE FROM doctors WHERE id = ?", (did,))
    db().commit()
    flash("Лікаря видалено")
    return redirect(url_for("admin"))


@app.route("/admin/done/<int:aid>", methods=["POST"])
@login_required
def done(aid):
    db().execute("UPDATE appointments SET status = 'оброблена' WHERE id = ?", (aid,))
    db().commit()
    return redirect(url_for("admin"))


@app.route("/admin/delete/<int:aid>", methods=["POST"])
@login_required
def delete(aid):
    db().execute("DELETE FROM appointments WHERE id = ?", (aid,))
    db().commit()
    flash("Заявку видалено")
    return redirect(url_for("admin"))


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, text="Такої сторінки немає."), 404


@app.errorhandler(500)
def server_error(_):
    return render_template("error.html", code=500, text="Щось пішло не так. Спробуйте пізніше."), 500


init_db()

if __name__ == "__main__":
    app.run(debug=True)
