
import sqlite3
from flask import Flask, session, redirect, render_template, request, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

import re
import secrets
import sqlite3
from functools import wraps
from math import ceil

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
PASSWORD_MIN, PASSWORD_MAX = 8, 100
TITLE_MAX, POST_MAX, COMMENT_MAX, QUERY_MAX = 100, 5000, 1000, 100



def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(config.DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def query(sql, params=()):
    return get_db().execute(sql, params).fetchall()


def query_one(sql, params=()):
    return get_db().execute(sql, params).fetchone()


def execute(sql, params=()):
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    return cur


@app.teardown_appcontext
def close_db(_exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.before_request
def csrf_protect():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    if request.method == "POST":
        submitted = request.form.get("csrf_token", "")
        if not secrets.compare_digest(submitted, session["csrf_token"]):
            abort(403)


@app.context_processor
def inject_globals():
    return {"csrf_token": session.get("csrf_token", ""),
            "current_user": session.get("username"),
            "current_user_id": session.get("user_id")}


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Kirjaudu sisään ensin.")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


def safe_next(target):
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("index")


def get_page():
    page = request.args.get("page", 1, type=int)
    return max(page or 1, 1)


def paginate(total, page):
    pages = max(ceil(total / config.PAGE_SIZE), 1)
    page = min(page, pages)
    return page, pages, (page - 1) * config.PAGE_SIZE


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="Pääsy estetty."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="Sivua ei löytynyt."), 404

#

def validate_post_form(form):
    title = form.get("title", "").strip()
    body = form.get("body", "").strip()
    errors = []
    if not title or len(title) > TITLE_MAX:
        errors.append(f"Otsikon pituus on 1–{TITLE_MAX} merkkiä.")
    if not body or len(body) > POST_MAX:
        errors.append(f"Sisällön pituus on 1–{POST_MAX} merkkiä.")
    valid_ids = {c["id"] for c in query("SELECT id FROM categories")}
    chosen = set()
    for raw in form.getlist("categories"):
        if not raw.isdigit() or int(raw) not in valid_ids:
            errors.append("Virheellinen aihealue.")
            break
        chosen.add(int(raw))
    if not chosen and not errors:
        errors.append("Valitse vähintään yksi aihealue.")
    return title, body, chosen, errors


def validate_comment(form):
    body = form.get("body", "").strip()
    if not body or len(body) > COMMENT_MAX:
        return body, [f"Kommentin pituus on 1–{COMMENT_MAX} merkkiä."]
    return body, []


def validate_credentials(username, password, password2):
    errors = []
    if not USERNAME_RE.match(username):
        errors.append("Käyttäjätunnus on 3–20 merkkiä (kirjaimet, numerot ja alaviiva).")
    if len(password) < PASSWORD_MIN or len(password) > PASSWORD_MAX:
        errors.append(f"Salasanan pituus on {PASSWORD_MIN}–{PASSWORD_MAX} merkkiä.")
    if password != password2:
        errors.append("Salasanat eivät täsmää.")
    return errors


def load_post_or_404(post_id):
    post = query_one(
        "SELECT p.*, u.username FROM posts p JOIN users u ON u.id = p.user_id WHERE p.id = ?",
        (post_id,))
    if post is None:
        abort(404)
    return post


def require_owner(owner_id):
    if owner_id != session.get("user_id"):
        abort(403)


def save_categories(post_id, category_ids):
    execute("DELETE FROM post_categories WHERE post_id = ?", (post_id,))
    get_db().executemany(
        "INSERT INTO post_categories (post_id, category_id) VALUES (?, ?)",
        [(post_id, c) for c in category_ids])
    get_db().commit()


POST_LIST_SQL = """
    SELECT p.id, p.title, p.created_at, u.id AS user_id, u.username,
           (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comment_count
    FROM posts p JOIN users u ON u.id = p.user_id
"""

@app.route("/")
def index():
    categories = query("SELECT * FROM categories ORDER BY name")
    category_id = request.args.get("category", type=int)
    where, params = "", []
    if category_id is not None:
        where = " WHERE EXISTS (SELECT 1 FROM post_categories pc WHERE pc.post_id = p.id AND pc.category_id = ?)"
        params = [category_id]
    total = query_one(f"SELECT COUNT(*) FROM posts p{where}", params)[0]
    page, pages, offset = paginate(total, get_page())
    posts = query(f"{POST_LIST_SQL}{where} ORDER BY p.id DESC LIMIT ? OFFSET ?",
                  params + [config.PAGE_SIZE, offset])
    return render_template("index.html", posts=posts, categories=categories,
                           category_id=category_id, page=page, pages=pages)


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()[:QUERY_MAX]
    posts, page, pages = [], 1, 1
    if q:
        like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        where = " WHERE p.title LIKE ? ESCAPE '\\' OR p.body LIKE ? ESCAPE '\\'"
        total = query_one(f"SELECT COUNT(*) FROM posts p{where}", (like, like))[0]
        page, pages, offset = paginate(total, get_page())
        posts = query(f"{POST_LIST_SQL}{where} ORDER BY p.id DESC LIMIT ? OFFSET ?",
                      (like, like, config.PAGE_SIZE, offset))
    return render_template("search.html", q=q, posts=posts, page=page, pages=pages)



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", username="", errors=[])
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    errors = validate_credentials(username, password, request.form.get("password2", ""))
    if not errors:
        try:
            execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password)))
        except sqlite3.IntegrityError:
            errors.append("Tunnus on jo varattu.")
    if errors:
        return render_template("register.html", username=username, errors=errors), 400
    flash("Tunnus luotu. Voit nyt kirjautua sisään.")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", next=request.args.get("next", ""), error=None)
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    user = query_one("SELECT * FROM users WHERE username = ?", (username,))
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", next=request.form.get("next", ""),
                               error="Väärä tunnus tai salasana."), 401
    session.clear()  # uusi istunto kirjautuessa
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["csrf_token"] = secrets.token_hex(16)
    return redirect(safe_next(request.form.get("next")))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/user/<int:user_id>")
def user_page(user_id):
    user = query_one("SELECT id, username, created_at FROM users WHERE id = ?", (user_id,))
    if user is None:
        abort(404)
    stats = query_one(
        "SELECT (SELECT COUNT(*) FROM posts WHERE user_id = ?) AS posts,"
        "       (SELECT COUNT(*) FROM comments WHERE user_id = ?) AS comments",
        (user_id, user_id))
    total = stats["posts"]
    page, pages, offset = paginate(total, get_page())
    posts = query(f"{POST_LIST_SQL} WHERE p.user_id = ? ORDER BY p.id DESC LIMIT ? OFFSET ?",
                  (user_id, config.PAGE_SIZE, offset))
    return render_template("user.html", user=user, stats=stats, posts=posts,
                           page=page, pages=pages)



@app.route("/post/new", methods=["GET", "POST"])
@login_required
def new_post():
    categories = query("SELECT * FROM categories ORDER BY name")
    if request.method == "GET":
        return render_template("post_form.html", categories=categories, title="", body="",
                               chosen=set(), errors=[], action=url_for("new_post"), heading="Uusi viesti")
    title, body, chosen, errors = validate_post_form(request.form)
    if errors:
        return render_template("post_form.html", categories=categories, title=title, body=body,
                               chosen=chosen, errors=errors, action=url_for("new_post"),
                               heading="Uusi viesti"), 400
    post_id = execute("INSERT INTO posts (user_id, title, body) VALUES (?, ?, ?)",
                      (session["user_id"], title, body)).lastrowid
    save_categories(post_id, chosen)
    return redirect(url_for("show_post", post_id=post_id))


@app.route("/post/<int:post_id>")
def show_post(post_id):
    post = load_post_or_404(post_id)
    categories = query(
        "SELECT c.id, c.name FROM categories c JOIN post_categories pc ON pc.category_id = c.id "
        "WHERE pc.post_id = ? ORDER BY c.name", (post_id,))
    total = query_one("SELECT COUNT(*) FROM comments WHERE post_id = ?", (post_id,))[0]
    page, pages, offset = paginate(total, get_page())
    comments = query(
        "SELECT c.*, u.username FROM comments c JOIN users u ON u.id = c.user_id "
        "WHERE c.post_id = ? ORDER BY c.id LIMIT ? OFFSET ?",
        (post_id, config.PAGE_SIZE, offset))
    return render_template("post.html", post=post, categories=categories, comments=comments,
                           total=total, page=page, pages=pages, errors=[], comment_body="")


@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = load_post_or_404(post_id)
    require_owner(post["user_id"])
    categories = query("SELECT * FROM categories ORDER BY name")
    action = url_for("edit_post", post_id=post_id)
    if request.method == "GET":
        chosen = {r["category_id"] for r in query(
            "SELECT category_id FROM post_categories WHERE post_id = ?", (post_id,))}
        return render_template("post_form.html", categories=categories, title=post["title"],
                               body=post["body"], chosen=chosen, errors=[], action=action,
                               heading="Muokkaa viestiä")
    title, body, chosen, errors = validate_post_form(request.form)
    if errors:
        return render_template("post_form.html", categories=categories, title=title, body=body,
                               chosen=chosen, errors=errors, action=action,
                               heading="Muokkaa viestiä"), 400
    execute("UPDATE posts SET title = ?, body = ? WHERE id = ?", (title, body, post_id))
    save_categories(post_id, chosen)
    return redirect(url_for("show_post", post_id=post_id))


@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = load_post_or_404(post_id)
    require_owner(post["user_id"])
    execute("DELETE FROM posts WHERE id = ?", (post_id,))
    flash("Viesti poistettu.")
    return redirect(url_for("index"))



@app.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
def add_comment(post_id):
    post = load_post_or_404(post_id)
    body, errors = validate_comment(request.form)
    if errors:
        categories = query(
            "SELECT c.id, c.name FROM categories c JOIN post_categories pc ON pc.category_id = c.id "
            "WHERE pc.post_id = ?", (post_id,))
        total = query_one("SELECT COUNT(*) FROM comments WHERE post_id = ?", (post_id,))[0]
        page, pages, offset = paginate(total, 1)
        comments = query(
            "SELECT c.*, u.username FROM comments c JOIN users u ON u.id = c.user_id "
            "WHERE c.post_id = ? ORDER BY c.id LIMIT ? OFFSET ?",
            (post_id, config.PAGE_SIZE, offset))
        return render_template("post.html", post=post, categories=categories, comments=comments,
                               total=total, page=page, pages=pages, errors=errors,
                               comment_body=body), 400
    execute("INSERT INTO comments (post_id, user_id, body) VALUES (?, ?, ?)",
            (post_id, session["user_id"], body))
    total = query_one("SELECT COUNT(*) FROM comments WHERE post_id = ?", (post_id,))[0]
    last_page = max(ceil(total / config.PAGE_SIZE), 1)
    return redirect(url_for("show_post", post_id=post_id, page=last_page) + "#comments")


def load_comment_or_404(comment_id):
    comment = query_one("SELECT * FROM comments WHERE id = ?", (comment_id,))
    if comment is None:
        abort(404)
    return comment


@app.route("/comment/<int:comment_id>/edit", methods=["GET", "POST"])
@login_required
def edit_comment(comment_id):
    comment = load_comment_or_404(comment_id)
    require_owner(comment["user_id"])
    if request.method == "GET":
        return render_template("comment_form.html", comment=comment, body=comment["body"], errors=[])
    body, errors = validate_comment(request.form)
    if errors:
        return render_template("comment_form.html", comment=comment, body=body, errors=errors), 400
    execute("UPDATE comments SET body = ? WHERE id = ?", (body, comment_id))
    return redirect(url_for("show_post", post_id=comment["post_id"]))


@app.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = load_comment_or_404(comment_id)
    require_owner(comment["user_id"])
    execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    flash("Kommentti poistettu.")
    return redirect(url_for("show_post", post_id=comment["post_id"]))


if __name__ == "__main__":
    app.run(debug=True)