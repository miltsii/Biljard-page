import secrets
from flask import Flask
from flask import session
import config
import db
from flask import redirect, render_template, request, session
from werkzeug.security import check_password_hash



app = Flask(__name__)
app.secret_key = config.secret_key

@app.before_request
def before_request():
    if "csrf_token" not in session:
        session["csrf_token"] = config.secret_key

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
    return render_template("index.html")




@app.route("/register", methods=["GET", "POST"])
@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/create", methods=["POST"])
def create():
    username = request.form["username"]
    password1 = request.form["password1"]
    password2 = request.form["password2"]
    if password1 != password2:
        return "VIRHE: salasanat eivät ole samat"
    password_hash = generate_password_hash(password1)

    try:
        sql = "INSERT INTO users (username, password_hash) VALUES (?, ?)"
        db.execute(sql, [username, password_hash])
    except sqlite3.IntegrityError:
        return "VIRHE: tunnus on jo varattu"

    return "Tunnus luotu"

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    
    sql = "SELECT password_hash FROM users WHERE username = ?"
    password_hash = db.query(sql, [username])[0][0]

    if check_password_hash(password_hash, password):
        session["username"] = username
        return redirect("/")
    else:
        return "VIRHE: väärä tunnus tai salasana"

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
