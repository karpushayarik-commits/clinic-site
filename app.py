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
    ("Олена Коваленко", "Терапевт", 14, "Лікар вищої категорії. Веде пацієнтів з хронічними захворюваннями.",
     "Дніпровський державний медичний університет, 2010", "Пн, Ср, Пт 8:00–14:00"),
    ("Андрій Мельник", "Кардіолог", 18, "Кандидат медичних наук. Спеціалізується на гіпертонії.",
     "Національний медичний університет ім. О. Богомольця, 2006", "Вт, Чт 10:00–18:00"),
    ("Ірина Шевченко", "Невролог", 11, "Працює з болем у спині та мігренями.",
     "Запорізький державний медичний університет, 2013", "Пн–Пт 14:00–20:00"),
    ("Максим Бондаренко", "Педіатр", 9, "Приймає дітей від народження, проводить вакцинацію.",
     "Дніпровський державний медичний університет, 2015", "Пн–Сб 9:00–15:00"),
]
DOCTOR_FIELDS = ("name", "speciality", "experience", "bio", "education", "schedule")


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
    CREATE TABLE IF NOT EXISTS doctors(id INTEGER PRIMARY KEY, name TEXT, speciality TEXT, experience INTEGER,
        bio TEXT, education TEXT DEFAULT '', schedule TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS appointments(
        id INTEGER PRIMARY KEY, name TEXT, phone TEXT, doctor_id INTEGER, visit_date TEXT,
        comment TEXT, status TEXT DEFAULT 'нова', created TEXT DEFAULT CURRENT_TIMESTAMP);
    """)
    cols = [r[1] for r in c.execute("PRAGMA table_info(doctors)")]
    for col in ("education", "schedule"):  # оновлення старої бази
        if col not in cols:
            c.execute(f"ALTER TABLE doctors ADD COLUMN {col} TEXT DEFAULT ''")
    if not c.execute("SELECT COUNT(*) FROM services").fetchone()[0]:
        c.executemany("INSERT INTO services(name,description,price) VALUES (?,?,?)", SERVICES)
    if not c.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]:
        c.executemany("INSERT INTO doctors(name,speciality,experience,bio,education,schedule) VALUES (?,?,?,?,?,?)",
                      DOCTORS)
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


def validate_doctor(form):
    errors = {}
    if len(form.get("name", "").strip()) < 3:
        errors["name"] = "Введіть ПІБ лікаря"
    if len(form.get("speciality", "").strip()) < 3:
        errors["speciality"] = "Вкажіть спеціальність"
    if not form.get("experience", "").strip().isdigit():
        errors["experience"] = "Стаж: ціле число років"
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


@app.route("/doctors/<int:did>/")
def doctor(did):
    d = db().execute("SELECT * FROM doctors WHERE id=?", (did,)).fetchone()
    if not d:
        abort(404)
    return render_template("doctor.html", d=d)


@app.route("/appointment/", methods=["GET", "POST"])
def appointment():
    docs = db().execute("SELECT id, name, speciality FROM doctors").fetchall()
    errors, form = {}, {"doctor_id": request.args.get("doctor", "")}
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
    docs = db().execute("SELECT * FROM doctors ORDER BY id").fetchall()
    return render_template("admin.html", rows=rows, doctors=docs)


@app.route("/admin/doctor/new/", methods=["GET", "POST"], defaults={"did": None})
@app.route("/admin/doctor/<int:did>/", methods=["GET", "POST"])
@login_required
def doctor_edit(did):
    d = None
    if did is not None:
        d = db().execute("SELECT * FROM doctors WHERE id=?", (did,)).fetchone()
        if not d:
            abort(404)
    form, errors = (dict(d) if d else {}), {}
    if request.method == "POST":
        form = request.form
        errors = validate_doctor(form)
        if not errors:
            vals = [form.get(k, "").strip() for k in DOCTOR_FIELDS]
            vals[2] = int(vals[2])
            if d:
                db().execute("UPDATE doctors SET " + ", ".join(f"{k}=?" for k in DOCTOR_FIELDS) + " WHERE id=?",
                             (*vals, did))
                flash("Дані лікаря оновлено")
            else:
                db().execute(f"INSERT INTO doctors({','.join(DOCTOR_FIELDS)}) VALUES (?,?,?,?,?,?)", vals)
                flash("Лікаря додано")
            db().commit()
            return redirect(url_for("admin"))
    return render_template("doctor_form.html", d=d, form=form, errors=errors)


@app.route("/admin/doctor/<int:did>/delete", methods=["POST"])
@login_required
def doctor_delete(did):
    db().execute("DELETE FROM doctors WHERE id=?", (did,))
    db().commit()
    flash("Лікаря видалено")
    return redirect(url_for("admin"))


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
