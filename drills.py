
import config
import db

LIST_SQL = """SELECT d.id, d.title, d.created_at, u.id AS user_id, u.username,
                     (SELECT COUNT(*) FROM attempts a WHERE a.drill_id = d.id) AS attempt_count
              FROM drills d JOIN users u ON u.id = d.user_id """
PAGE_SQL = " ORDER BY d.id DESC LIMIT ? OFFSET ?"


CATEGORY_FILTER = """WHERE ? IS NULL OR EXISTS (SELECT 1 FROM drill_categories dc
                     WHERE dc.drill_id = d.id AND dc.category_id = ?)"""
SEARCH_FILTER = "WHERE d.title LIKE ? ESCAPE '\\' OR d.description LIKE ? ESCAPE '\\'"


def offset_of(page):
    return (page - 1) * config.PAGE_SIZE


def like_pattern(term):
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def get_categories():
    return db.query("SELECT id, name FROM categories ORDER BY name")


def get_drill_categories(drill_id):
    sql = """SELECT c.id, c.name FROM categories c
             JOIN drill_categories dc ON dc.category_id = c.id
             WHERE dc.drill_id = ? ORDER BY c.name"""
    return db.query(sql, [drill_id])


def set_categories(drill_id, category_ids):
    db.execute("DELETE FROM drill_categories WHERE drill_id = ?", [drill_id])
    sql = "INSERT INTO drill_categories (drill_id, category_id) VALUES (?, ?)"
    db.execute_many(sql, [(drill_id, category_id) for category_id in category_ids])


def add_drill(user_id, title, description, category_ids):
    sql = "INSERT INTO drills (user_id, title, description) VALUES (?, ?, ?)"
    drill_id = db.execute(sql, [user_id, title, description])
    set_categories(drill_id, category_ids)
    return drill_id


def get_drill(drill_id):
    sql = """SELECT d.id, d.user_id, d.title, d.description, d.created_at, u.username
             FROM drills d JOIN users u ON u.id = d.user_id WHERE d.id = ?"""
    rows = db.query(sql, [drill_id])
    return rows[0] if rows else None


def update_drill(drill_id, title, description, category_ids):
    sql = "UPDATE drills SET title = ?, description = ? WHERE id = ?"
    db.execute(sql, [title, description, drill_id])
    set_categories(drill_id, category_ids)


def remove_drill(drill_id):
    db.execute("DELETE FROM drills WHERE id = ?", [drill_id])


def count_drills(category_id):
    sql = "SELECT COUNT(*) FROM drills d " + CATEGORY_FILTER
    return db.query(sql, [category_id, category_id])[0][0]


def get_drills(page, category_id):
    sql = LIST_SQL + CATEGORY_FILTER + PAGE_SQL
    return db.query(sql, [category_id, category_id, config.PAGE_SIZE, offset_of(page)])


def count_search(term):
    pattern = like_pattern(term)
    sql = "SELECT COUNT(*) FROM drills d " + SEARCH_FILTER
    return db.query(sql, [pattern, pattern])[0][0]


def search_drills(term, page):
    pattern = like_pattern(term)
    sql = LIST_SQL + SEARCH_FILTER + PAGE_SQL
    return db.query(sql, [pattern, pattern, config.PAGE_SIZE, offset_of(page)])


def count_user_drills(user_id):
    sql = "SELECT COUNT(*) FROM drills WHERE user_id = ?"
    return db.query(sql, [user_id])[0][0]


def get_user_drills(user_id, page):
    sql = LIST_SQL + "WHERE d.user_id = ?" + PAGE_SQL
    return db.query(sql, [user_id, config.PAGE_SIZE, offset_of(page)])