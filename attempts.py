
import db
import config

def add_attempt(drill_id, user_id, score, note):
    sql = "INSERT INTO attempts (drill_id, user_id, score, note) VALUES (?, ?, ?, ?)"
    db.execute(sql, [drill_id, user_id, score, note])


def get_attempt(attempt_id):
    sql = "SELECT id, drill_id, user_id, score, note FROM attempts WHERE id = ?"
    rows = db.query(sql, [attempt_id])
    return rows[0] if rows else None


def update_attempt(attempt_id, score, note):
    sql = "UPDATE attempts SET score = ?, note = ? WHERE id = ?"
    db.execute(sql, [score, note, attempt_id])


def remove_attempt(attempt_id):
    db.execute("DELETE FROM attempts WHERE id = ?", [attempt_id])


def count_attempts(drill_id):
    sql = "SELECT COUNT(*) FROM attempts WHERE drill_id = ?"
    return db.query(sql, [drill_id])[0][0]


def get_attempts(drill_id, page):
    sql = """SELECT a.id, a.user_id, a.score, a.note, a.created_at, u.username
             FROM attempts a JOIN users u ON u.id = a.user_id
             WHERE a.drill_id = ?
             ORDER BY a.id DESC LIMIT ? OFFSET ?"""
    offset = (page - 1) * config.PAGE_SIZE
    return db.query(sql, [drill_id, config.PAGE_SIZE, offset])


def get_average_score(drill_id):
    sql = "SELECT AVG(score) FROM attempts WHERE drill_id = ?"
    return db.query(sql, [drill_id])[0][0]