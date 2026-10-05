
import re
import secrets
import sqlite3
from math import ceil

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

import attempts
import config
import drills
import users

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")
PASSWORD_MIN, PASSWORD_MAX = 8, 100
TITLE_MAX, DESCRIPTION_MAX, NOTE_MAX, SEARCH_MAX = 100, 5000, 500, 100



@app.before_request
def check_csrf():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    if request.method == "POST":
        token = request.form.get("csrf_token", "")
        if not secrets.compare_digest(token, session["csrf_token"]):
            abort(403)


@app.context_processor
def add_template_variables():
    return {"csrf_token": session.get("csrf_token", ""),
            "current_user": session.get("username"),
            "current_user_id": session.get("user_id")}


def require_login():
    if "user_id" not in session:
        abort(403)


def require_owner(owner_id):
    if owner_id != session.get("user_id"):
        abort(403)


def get_page():
    return max(request.args.get("page", 1, type=int), 1)


def page_info(total, page):
    page_count = max(ceil(total / config.PAGE_SIZE), 1)
    return min(page, page_count), page_count


def load_drill(drill_id):
    drill = drills.get_drill(drill_id)
    if drill is None:
        abort(404)
    return drill


def load_attempt(attempt_id):
    attempt = attempts.get_attempt(attempt_id)
    if attempt is None:
        abort(404)
    return attempt


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="Pääsy estetty."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="Sivua ei löytynyt."), 404



def validate_drill(form):
    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    errors = []
    if not 1 <= len(title) <= TITLE_MAX:
        errors.append(f"Otsikon pituus on 1–{TITLE_MAX} merkkiä.")
    if not 1 <= len(description) <= DESCRIPTION_MAX:
        errors.append(f"Kuvauksen pituus on 1–{DESCRIPTION_MAX} merkkiä.")

    valid_ids = [row["id"] for row in drills.get_categories()]
    category_ids = set()
    for text in form.getlist("categories"):
        if text.isascii() and text.isdigit() and int(text) in valid_ids:
            category_ids.add(int(text))
        else:
            errors.append("Virheellinen luokka.")
    if not category_ids and not errors:
        errors.append("Valitse vähintään yksi luokka.")
    return title, description, category_ids, errors


def validate_attempt(form):
    score_text = form.get("score", "").strip()
    note = form.get("note", "").strip()
    errors = []
    score = 0
    if score_text.isascii() and score_text.isdigit() and int(score_text) <= 10:
        score = int(score_text)
    else:
        errors.append("Pisteet ovat kokonaisluku väliltä 0–10.")
    if len(note) > NOTE_MAX:
        errors.append(f"Muistiinpano saa olla enintään {NOTE_MAX} merkkiä.")
    return score, note, errors


def validate_registration(username, password, password_again):
    errors = []
    if not USERNAME_PATTERN.match(username):
        errors.append("Käyttäjätunnus on 3–20 merkkiä (kirjaimet, numerot ja alaviiva).")
    if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
        errors.append(f"Salasanan pituus on {PASSWORD_MIN}–{PASSWORD_MAX} merkkiä.")
    if password != password_again:
        errors.append("Salasanat eivät täsmää.")
    return errors



@app.route("/")
def index():
    category_id = request.args.get("category", type=int)
    page, page_count = page_info(drills.count_drills(category_id), get_page())
    return render_template("index.html", drills=drills.get_drills(page, category_id),
                           categories=drills.get_categories(), category_id=category_id,
                           page=page, page_count=page_count)


@app.route("/search")
def search():
    term = request.args.get("q", "").strip()[:SEARCH_MAX]
    results, page, page_count = [], 1, 1
    if term:
        page, page_count = page_info(drills.count_search(term), get_page())
        results = drills.search_drills(term, page)
    return render_template("search.html", term=term, drills=results,
                           page=page, page_count=page_count)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", username="", errors=[])

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    errors = validate_registration(username, password, request.form.get("password2", ""))
    if not errors:
        try:
            users.create_user(username, password)
        except sqlite3.IntegrityError:
            errors.append("Tunnus on jo varattu.")
    if errors:
        return render_template("register.html", username=username, errors=errors), 400
    flash("Tunnus luotu. Voit nyt kirjautua sisään.")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", error=None)

    username = request.form.get("username", "").strip()
    user_id = users.check_login(username, request.form.get("password", ""))
    if user_id is None:
        return render_template("login.html", error="Väärä tunnus tai salasana."), 401
    session.clear()
    session["user_id"] = user_id
    session["username"] = username
    session["csrf_token"] = secrets.token_hex(16)
    return redirect(url_for("index"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/user/<int:user_id>")
def user_page(user_id):
    user = users.get_user(user_id)
    if user is None:
        abort(404)
    page, page_count = page_info(drills.count_user_drills(user_id), get_page())
    return render_template("user.html", user=user, stats=users.get_stats(user_id),
                           drills=drills.get_user_drills(user_id, page),
                           page=page, page_count=page_count)



@app.route("/drill/new", methods=["GET", "POST"])
def new_drill():
    require_login()
    if request.method == "GET":
        return render_template("drill_form.html", heading="Uusi harjoitus", title="",
                               description="", chosen=set(), errors=[],
                               categories=drills.get_categories())

    title, description, category_ids, errors = validate_drill(request.form)
    if errors:
        return render_template("drill_form.html", heading="Uusi harjoitus", title=title,
                               description=description, chosen=category_ids, errors=errors,
                               categories=drills.get_categories()), 400
    drill_id = drills.add_drill(session["user_id"], title, description, category_ids)
    return redirect(url_for("show_drill", drill_id=drill_id))


@app.route("/drill/<int:drill_id>")
def show_drill(drill_id):
    drill = load_drill(drill_id)
    page, page_count = page_info(attempts.count_attempts(drill_id), get_page())
    return render_template("drill.html", drill=drill,
                           categories=drills.get_drill_categories(drill_id),
                           attempt_count=attempts.count_attempts(drill_id),
                           average_score=attempts.get_average_score(drill_id),
                           attempts=attempts.get_attempts(drill_id, page),
                           page=page, page_count=page_count)


@app.route("/drill/<int:drill_id>/edit", methods=["GET", "POST"])
def edit_drill(drill_id):
    require_login()
    drill = load_drill(drill_id)
    require_owner(drill["user_id"])
    if request.method == "GET":
        chosen = {row["id"] for row in drills.get_drill_categories(drill_id)}
        return render_template("drill_form.html", heading="Muokkaa harjoitusta",
                               title=drill["title"], description=drill["description"],
                               chosen=chosen, errors=[], categories=drills.get_categories())

    title, description, category_ids, errors = validate_drill(request.form)
    if errors:
        return render_template("drill_form.html", heading="Muokkaa harjoitusta", title=title,
                               description=description, chosen=category_ids, errors=errors,
                               categories=drills.get_categories()), 400
    drills.update_drill(drill_id, title, description, category_ids)
    return redirect(url_for("show_drill", drill_id=drill_id))


@app.route("/drill/<int:drill_id>/delete", methods=["POST"])
def delete_drill(drill_id):
    require_login()
    require_owner(load_drill(drill_id)["user_id"])
    drills.remove_drill(drill_id)
    flash("Harjoitus poistettu.")
    return redirect(url_for("index"))



@app.route("/drill/<int:drill_id>/attempt", methods=["POST"])
def add_attempt(drill_id):
    require_login()
    load_drill(drill_id)
    score, note, errors = validate_attempt(request.form)
    if errors:
        for error in errors:
            flash(error)
    else:
        attempts.add_attempt(drill_id, session["user_id"], score, note)
    return redirect(url_for("show_drill", drill_id=drill_id))


@app.route("/attempt/<int:attempt_id>/edit", methods=["GET", "POST"])
def edit_attempt(attempt_id):
    require_login()
    attempt = load_attempt(attempt_id)
    require_owner(attempt["user_id"])
    if request.method == "GET":
        return render_template("attempt_form.html", attempt=attempt,
                               score=attempt["score"], note=attempt["note"], errors=[])

    score, note, errors = validate_attempt(request.form)
    if errors:
        return render_template("attempt_form.html", attempt=attempt,
                               score=request.form.get("score", ""), note=note,
                               errors=errors), 400
    attempts.update_attempt(attempt_id, score, note)
    return redirect(url_for("show_drill", drill_id=attempt["drill_id"]))


@app.route("/attempt/<int:attempt_id>/delete", methods=["POST"])
def delete_attempt(attempt_id):
    require_login()
    attempt = load_attempt(attempt_id)
    require_owner(attempt["user_id"])
    attempts.remove_attempt(attempt_id)
    flash("Tulos poistettu.")
    return redirect(url_for("show_drill", drill_id=attempt["drill_id"]))


if __name__ == "__main__":
    app.run(debug=True)