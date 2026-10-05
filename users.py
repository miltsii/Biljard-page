
from werkzeug.security import check_password_hash, generate_password_hash

import db


def create_user(username, password):
    """Add a user. Raises sqlite3.IntegrityError if the username is taken."""
    password_hash = generate_password_hash(password)
    sql = "INSERT INTO users (username, password_hash) VALUES (?, ?)"
    db.execute(sql, [username, password_hash])


def check_login(username, password):
    """Return the user id if the credentials are correct, otherwise None."""
    sql = "SELECT id, password_hash FROM users WHERE username = ?"
    rows = db.query(sql, [username])
    if rows and check_password_hash(rows[0]["password_hash"], password):
        return rows[0]["id"]
    return None


def get_user(user_id):
    """Return a user row or None."""
    sql = "SELECT id, username, created_at FROM users WHERE id = ?"
    rows = db.query(sql, [user_id])
    return rows[0] if rows else None


def get_stats(user_id):
    """Return drill count, attempt count and average score of a user."""
    sql = """SELECT (SELECT COUNT(*) FROM drills WHERE user_id = ?) AS drill_count,
                    (SELECT COUNT(*) FROM attempts WHERE user_id = ?) AS attempt_count,
                    (SELECT AVG(score) FROM attempts WHERE user_id = ?) AS average_score"""
    return db.query(sql, [user_id, user_id, user_id])[0]