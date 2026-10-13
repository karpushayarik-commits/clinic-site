"""Збирає статичну версію сайту в build/ для GitHub Pages."""
import os
os.environ["STATIC_BUILD"] = "1"
from flask_frozen import Freezer
from app import app

app.config["FREEZER_DESTINATION"] = "build"
app.config["FREEZER_RELATIVE_URLS"] = True
freezer = Freezer(app, with_no_argument_rules=False, log_url_for=False)


@freezer.register_generator
def pages():
    for ep in ("index", "services", "doctors", "appointment"):
        yield ep, {}


if __name__ == "__main__":
    freezer.freeze()
    open("build/.nojekyll", "w").close()
    print("Готово: build/")
