"""Збирає статичну версію сайту в build/ для GitHub Pages."""
import os
os.environ["STATIC_BUILD"] = "1"
import sqlite3
from flask_frozen import Freezer
from app import app, DB

app.config["FREEZER_DESTINATION"] = "build"
app.config["FREEZER_RELATIVE_URLS"] = True
freezer = Freezer(app, with_no_argument_rules=False, log_url_for=False)


@freezer.register_generator
def pages():
    yield "index", {}
    yield "appointment", {}
    for (did,) in sqlite3.connect(DB).execute("SELECT id FROM doctors"):
        yield "doctor", {"did": did}


if __name__ == "__main__":
    freezer.freeze()
    open("build/.nojekyll", "w").close()
    print("Готово: build/")
