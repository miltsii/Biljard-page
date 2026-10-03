
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




@app.cli.command("init-db")
def init_db():
    con = db.get_connection()

    with open("schema.sql", encoding="utf-8") as f:
        con.executescript(f.read())

    con.close()

    print("Database initialized.")


# Etusivu


@app.route("/")
def index():
    con = db.get_connection()

    posts = con.execute("""
        SELECT posts.*,
               users.username,
               categories.name AS category
        FROM posts
        JOIN users ON posts.user_id = users.id
        LEFT JOIN categories ON posts.category_id = categories.id
        ORDER BY posts.created_at DESC
    """).fetchall()

    con.close()

    return render_template("index.html", posts=posts)


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

