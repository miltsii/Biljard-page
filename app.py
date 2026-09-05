import secrets
import sqlite3
 
from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
 
app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"  
DATABASE = "database.db"
 

CATEGORIES = ["Pool", "Snooker", "Carom", "Equipment", "Tournaments", "General"]
 
 
def get_db():
    
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

@app.before_request
def make_csrf_token():
        session["csrf_token"] = secrets.token_hex(16)
 
 
def csrf_ok():
    submitted = request.form.get("csrf_token")
    return submitted is not None and submitted == session.get("csrf_token")
 
 
def current_user():
    if "user_id" in session:
        return {"id": session["user_id"], "username": session["username"]}
    return None