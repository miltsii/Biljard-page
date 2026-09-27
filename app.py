import secrets
from flask import Flask, session, g
import db

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

@app.before_request
def before_request():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)

@app.context_processor
def inject():
    return {"csrf_token": session.get("csrf_token", "")}

@app.cli.command("init-db")
def init_db():
    con = db.get_connection()
    with open("schema.sql") as f:
        con.executescript(f.read())
    con.close()
    print("Database initialized.")

@app.route("/")
def index():
    return "Billiards forum - coming soon"
 # lisää importteihin:
from flask import render_template, request, redirect, url_for, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if request.form["csrf_token"] != session["csrf_token"]:
            abort(403)
        username = request.form["username"]
        password = request.form["password"]
        password2 = request.form["password2"]
        if password != password2:
            flash("Passwords do not match")
            return redirect("/register")
        con = db.get_connection()
        try:
            con.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                        [username, generate_password_hash(password)])
            con.commit()
        except Exception:
            flash("Username already taken")
            con.close()
            return redirect("/register")
        con.close()
        flash("Account created, you can now log in")
        return redirect("/login")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["csrf_token"] != session["csrf_token"]:
            abort(403)
        username = request.form["username"]
        password = request.form["password"]
        con = db.get_connection()
        user = con.execute("SELECT * FROM users WHERE username = ?",
                           [username]).fetchone()
        con.close()
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Wrong username or password")
            return redirect("/login")
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect("/")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/")
def index():
    con = db.get_connection()
    posts = con.execute("""SELECT posts.*, users.username, categories.name AS category
                           FROM posts
                           JOIN users ON posts.user_id = users.id
                           LEFT JOIN categories ON posts.category_id = categories.id
                           ORDER BY posts.created_at DESC""").fetchall()
    con.close()
    return render_template("index.html", posts=posts)

@app.route("/new_post", methods=["GET", "POST"])
def new_post():
    if not session.get("user_id"):
        flash("Please log in first")
        return redirect("/login")
    con = db.get_connection()
    if request.method == "POST":
        if request.form["csrf_token"] != session["csrf_token"]:
            abort(403)
        title = request.form["title"]
        content = request.form["content"]
        category_id = request.form.get("category_id") or None
        con.execute("INSERT INTO posts (title, content, user_id, category_id) VALUES (?, ?, ?, ?)",
                    [title, content, session["user_id"], category_id])
        con.commit()
        con.close()
        flash("Post created!")
        return redirect("/")
    categories = con.execute("SELECT * FROM categories ORDER BY name").fetchall()
    con.close()
    return render_template("new_post.html", categories=categories)

@app.route("/post/<int:post_id>")
def show_post(post_id):
    con = db.get_connection()
    post = con.execute("""SELECT posts.*, users.username, categories.name AS category
                          FROM posts
                          JOIN users ON posts.user_id = users.id
                          LEFT JOIN categories ON posts.category_id = categories.id
                          WHERE posts.id = ?""", [post_id]).fetchone()
    if post is None:
        abort(404)
    comments = con.execute("""SELECT comments.*, users.username FROM comments
                              JOIN users ON comments.user_id = users.id
                              WHERE comments.post_id = ?
                              ORDER BY comments.created_at""", [post_id]).fetchall()
    con.close()
    return render_template("post.html", post=post, comments=comments)

@app.route("/post/<int:post_id>/comment", methods=["POST"])
def add_comment(post_id):
    if not session.get("user_id"):
        flash("Please log in first")
        return redirect("/login")
    if request.form["csrf_token"] != session["csrf_token"]:
        abort(403)
    con = db.get_connection()
    post = con.execute("SELECT * FROM posts WHERE id = ?", [post_id]).fetchone()
    if post is None:
        abort(404)
    con.execute("INSERT INTO comments (content, user_id, post_id) VALUES (?, ?, ?)",
                [request.form["content"], session["user_id"], post_id])
    con.commit()
    con.close()
    return redirect("/post/" + str(post_id))

@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
def edit_post(post_id):
    if not session.get("user_id"):
        return redirect("/login")
    con = db.get_connection()
    post = con.execute("SELECT * FROM posts WHERE id = ?", [post_id]).fetchone()
    if post is None:
        abort(404)
    if post["user_id"] != session["user_id"]:
        abort(403)
    if request.method == "POST":
        if request.form["csrf_token"] != session["csrf_token"]:
            abort(403)
        con.execute("UPDATE posts SET title = ?, content = ?, category_id = ? WHERE id = ?",
                    [request.form["title"], request.form["content"],
                     request.form.get("category_id") or None, post_id])
        con.commit()
        con.close()
        flash("Post updated!")
        return redirect("/post/" + str(post_id))
    categories = con.execute("SELECT * FROM categories ORDER BY name").fetchall()
    con.close()
    return render_template("edit_post.html", post=post, categories=categories)

@app.route("/post/<int:post_id>/delete", methods=["POST"])
def delete_post(post_id):
    if not session.get("user_id"):
        return redirect("/login")
    if request.form["csrf_token"] != session["csrf_token"]:
        abort(403)
    con = db.get_connection()
    post = con.execute("SELECT * FROM posts WHERE id = ?", [post_id]).fetchone()
    if post is None:
        abort(404)
    if post["user_id"] != session["user_id"]:
        abort(403)
    con.execute("DELETE FROM comments WHERE post_id = ?", [post_id])
    con.execute("DELETE FROM posts WHERE id = ?", [post_id])
    con.commit()
    con.close()
    flash("Post removed")
    return redirect("/")
@app.route("/search")
def search():
    q = request.args.get("q", "")
    category_id = request.args.get("category_id", "")
    con = db.get_connection()
    categories = con.execute("SELECT * FROM categories ORDER BY name").fetchall()
    sql = """SELECT posts.*, users.username, categories.name AS category
             FROM posts
             JOIN users ON posts.user_id = users.id
             LEFT JOIN categories ON posts.category_id = categories.id
             WHERE (posts.title LIKE ? OR posts.content LIKE ?)"""
    params = ["%" + q + "%", "%" + q + "%"]
    if category_id:
        sql += " AND posts.category_id = ?"
        params.append(category_id)
    sql += " ORDER BY posts.created_at DESC"
    posts = con.execute(sql, params).fetchall()
    con.close()
    return render_template("search.html", posts=posts, q=q,
                           categories=categories, selected=category_id)
