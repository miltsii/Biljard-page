
import sqlite3
from flask import Flask, session, redirect, render_template, request, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
import db


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
def close_db(exception):
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
def forbidden(e):
    return render_template("error.html", code=403, message="Pääsy estetty."), 403


@app.errorhandler(404)
def not_found(e):
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



# Rekisteröityminen


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    username = request.form["username"]
    password1 = request.form["password1"]
    password2 = request.form["password2"]

    if password1 != password2:
        return "VIRHE: salasanat eivät ole samat"

    if not username or not password1:
        return "VIRHE: täytä kaikki kentät"

    password_hash = generate_password_hash(password1)

    try:
        db.execute(
            """
            INSERT INTO users (username, password_hash)
            VALUES (?, ?)
            """,
            [username, password_hash]
        )

    except sqlite3.IntegrityError:
        return "VIRHE: käyttäjänimi on jo varattu"

    return redirect("/login")

# Kirjautuminen


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html")

    username = request.form["username"]
    password = request.form["password"]

    con = db.get_connection()

    user = con.execute(
        """
        SELECT id, username, password_hash
        FROM users
        WHERE username = ?
        """,
        [username]
    ).fetchone()

    con.close()

    if user is None:
        return "VIRHE: väärä käyttäjänimi tai salasana"

    if check_password_hash(user["password_hash"], password):

        session["user_id"] = user["id"]
        session["username"] = user["username"]

        return redirect("/")

    return "VIRHE: väärä käyttäjänimi tai salasana"


# Uloskirjautuminen


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

# Uuden julkaisun tekeminen

@app.route("/new_post", methods=["GET", "POST"])
def new_post():

    if not session.get("user_id"):
        flash("Kirjaudu ensin sisään.")
        return redirect("/login")

    con = db.get_connection()

    if request.method == "POST":

        if request.form["csrf_token"] != session["csrf_token"]:
            abort(403)

        title = request.form["title"].strip()
        content = request.form["content"].strip()

        if not title:
            return "Otsikko ei saa olla tyhjä"

        if not content:
            return "Sisältö ei saa olla tyhjä"

        con.execute(
            """
            INSERT INTO posts
            (title, content, user_id, category_id)
            VALUES (?, ?, ?, ?)
            """,
            [
                title,
                content,
                session["user_id"],
                category_id
            ]
        )

        con.commit()
        con.close()

        flash("Julkaisu luotu!")

        return redirect("/")

    categories = con.execute(
        """
        SELECT *
        FROM categories
        ORDER BY name
        """
    ).fetchall()

    con.close()

    return render_template(
        "new_post.html",
        categories=categories
    )


# Yksittäinen julkaisu


@app.route("/post/<int:post_id>")
def show_post(post_id):

    con = db.get_connection()

    post = con.execute(
        """
        SELECT posts.*,
               users.username,
               categories.name AS category
        FROM posts
        JOIN users ON posts.user_id = users.id
        LEFT JOIN categories ON posts.category_id = categories.id
        WHERE posts.id = ?
        """,
        [post_id]
    ).fetchone()

    if post is None:
        con.close()
        abort(404)

    comments = con.execute(
        """
        SELECT comments.*,
               users.username
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.post_id = ?
        ORDER BY comments.created_at
        """,
        [post_id]
    ).fetchall()

    con.close()

    return render_template(
        "post.html",
        post=post,
        comments=comments
    )


# ----------------------------------------
# Kommentin lisääminen
# ----------------------------------------

@app.route("/post/<int:post_id>/comment", methods=["POST"])
def add_comment(post_id):

    if not session.get("user_id"):
        flash("Kirjaudu ensin sisään.")
        return redirect("/login")

    if request.form["csrf_token"] != session["csrf_token"]:
        abort(403)

    con = db.get_connection()

    post = con.execute(
        "SELECT * FROM posts WHERE id = ?",
        [post_id]
    ).fetchone()

    if post is None:
        con.close()
        abort(404)

    content = request.form["content"]

    con.execute(
        """
        INSERT INTO comments
        (content, user_id, post_id)
        VALUES (?, ?, ?)
        """,
        [
            content,
            session["user_id"],
            post_id
        ]
    )

    con.commit()
    con.close()

    return redirect("/post/" + str(post_id))


# Julkaisun muokkaaminen


@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
def edit_post(post_id):

    if not session.get("user_id"):
        return redirect("/login")

    con = db.get_connection()

    post = con.execute(
        "SELECT * FROM posts WHERE id = ?",
        [post_id]
    ).fetchone()

    if post is None:
        con.close()
        abort(404)

    if post["user_id"] != session["user_id"]:
        con.close()
        abort(403)

    if request.method == "POST":

        if request.form["csrf_token"] != session["csrf_token"]:
            con.close()
            abort(403)

        title = request.form["title"]
        content = request.form["content"]
        category_id = request.form.get("category_id") or None

        con.execute(
            """
            UPDATE posts
            SET title = ?,
                content = ?,
                category_id = ?
            WHERE id = ?
            """,
            [
                title,
                content,
                category_id,
                post_id
            ]
        )

        con.commit()
        con.close()

        flash("Julkaisu päivitetty!")

        return redirect("/post/" + str(post_id))

    categories = con.execute(
        """
        SELECT *
        FROM categories
        ORDER BY name
        """
    ).fetchall()

    con.close()

    return render_template(
        "edit_post.html",
        post=post,
        categories=categories
    )


# Julkaisun poistaminen


@app.route("/post/<int:post_id>/delete", methods=["POST"])
def delete_post(post_id):

    if not session.get("user_id"):
        return redirect("/login")

    if request.form["csrf_token"] != session["csrf_token"]:
        abort(403)

    con = db.get_connection()

    post = con.execute(
        "SELECT * FROM posts WHERE id = ?",
        [post_id]
    ).fetchone()

    if post is None:
        con.close()
        abort(404)

    if post["user_id"] != session["user_id"]:
        con.close()
        abort(403)

    con.execute(
        "DELETE FROM comments WHERE post_id = ?",
        [post_id]
    )

    con.execute(
        "DELETE FROM posts WHERE id = ?",
        [post_id]
    )

    con.commit()
    con.close()

    flash("Julkaisu poistettu!")

    return redirect("/")


# Haku


@app.route("/search")
def search():

    q = request.args.get("q", "")
    category_id = request.args.get("category_id", "")

    con = db.get_connection()

    categories = con.execute(
        """
        SELECT *
        FROM categories
        ORDER BY name
        """
    ).fetchall()

    sql = """
        SELECT posts.*,
               users.username,
               categories.name AS category
        FROM posts
        JOIN users ON posts.user_id = users.id
        LEFT JOIN categories ON posts.category_id = categories.id
        WHERE posts.title LIKE ?
           OR posts.content LIKE ?
    """

    params = [
        "%" + q + "%",
        "%" + q + "%"
    ]

    if category_id:
        sql += " AND posts.category_id = ?"
        params.append(category_id)

    sql += " ORDER BY posts.created_at DESC"

    posts = con.execute(
        sql,
        params
    ).fetchall()

    con.close()

    return render_template(
        "search.html",
        posts=posts,
        q=q,
        categories=categories,
        selected=category_id
    )


if __name__ == "__main__":
    app.run(debug=True)

