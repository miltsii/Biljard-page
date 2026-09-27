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
