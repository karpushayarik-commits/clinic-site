import os, re, sqlite3
from datetime import date
from functools import wraps
from flask import Flask, g, render_template, request, redirect, url_for, session, flash, abort

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
DB = os.path.join(app.root_path, "clinic.db")
STATIC_BUILD = os.environ.get("STATIC_BUILD") == "1"
ADMIN_USER = "admin"
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")
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
    ("Олена Коваленко", "Терапевт", 14, "Лікар вищої категорії. Веде пацієнтів з хронічними захворюваннями."),
    ("Андрій Мельник", "Кардіолог", 18, "Кандидат медичних наук. Спеціалізується на гіпертонії."),
    ("Ірина Шевченко", "Невролог", 11, "Працює з болем у спині та мігренями."),
    ("Максим Бондаренко", "Педіатр", 9, "Приймає дітей від народження, проводить вакцинацію."),
]


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def init_db():
    c = sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS services(id INTEGER PRIMARY KEY, name TEXT, description TEXT, price INTEGER);
    CREATE TABLE IF NOT EXISTS doctors(id INTEGER PRIMARY KEY, name TEXT, speciality TEXT, experience INTEGER, bio TEXT);
    CREATE TABLE IF NOT EXISTS appointments(
        id INTEGER PRIMARY KEY, name TEXT, phone TEXT, doctor_id INTEGER, visit_date TEXT,
        comment TEXT, status TEXT DEFAULT 'нова', created TEXT DEFAULT CURRENT_TIMESTAMP);
    """)
    if not c.execute("SELECT COUNT(*) FROM services").fetchone()[0]:
        c.executemany("INSERT INTO services(name,description,price) VALUES (?,?,?)", SERVICES)
        c.executemany("INSERT INTO doctors(name,speciality,experience,bio) VALUES (?,?,?,?)", DOCTORS)
    c.commit()
    c.close()


@app.context_processor
def inject():
    return dict(clinic=CLINIC, static_build=STATIC_BUILD)


def validate(form):
    errors = {}
    if len(form.get("name", "").strip()) < 2:
        errors["name"] = "Введіть ім'я (мінімум 2 літери)"
    if not re.fullmatch(r"\+?[0-9 ()\-]{10,16}", form.get("phone", "").strip()):
        errors["phone"] = "Введіть телефон, наприклад +380501234567"
    if not form.get("doctor_id", "").isdigit():
        errors["doctor_id"] = "Оберіть лікаря"
    d = form.get("visit_date", "")
    if not d or d < date.today().isoformat():
        errors["visit_date"] = "Оберіть дату не раніше сьогодні"
    return errors


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrapper


@app.route("/")
def index():
    return render_template("index.html", services=db().execute("SELECT * FROM services").fetchall(),
                           doctors=db().execute("SELECT * FROM doctors").fetchall())


@app.route("/services/")
def services():
    return render_template("services.html", services=db().execute("SELECT * FROM services").fetchall())


@app.route("/doctors/")
def doctors():
    return render_template("doctors.html", doctors=db().execute("SELECT * FROM doctors").fetchall())


@app.route("/appointment/", methods=["GET", "POST"])
def appointment():
    docs = db().execute("SELECT id, name, speciality FROM doctors").fetchall()
    errors, form = {}, {}
    if request.method == "POST":
        form = request.form
        errors = validate(form)
        if not errors:
            db().execute("INSERT INTO appointments(name,phone,doctor_id,visit_date,comment) VALUES (?,?,?,?,?)",
                         (form["name"].strip(), form["phone"].strip(), int(form["doctor_id"]),
                          form["visit_date"], form.get("comment", "").strip()))
            db().commit()
            flash("Заявку прийнято. Ми зателефонуємо протягом години.")
            return redirect(url_for("appointment"))
    return render_template("appointment.html", doctors=docs, errors=errors, form=form)


@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("user") == ADMIN_USER and request.form.get("password") == ADMIN_PASS:
            session["admin"] = True
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
    return render_template("admin.html", rows=rows)


@app.route("/admin/done/<int:aid>", methods=["POST"])
@login_required
def done(aid):
    db().execute("UPDATE appointments SET status='оброблена' WHERE id=?", (aid,))
    db().commit()
    return redirect(url_for("admin"))


@app.route("/admin/delete/<int:aid>", methods=["POST"])
@login_required
def delete(aid):
    db().execute("DELETE FROM appointments WHERE id=?", (aid,))
    db().commit()
    return redirect(url_for("admin"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)
