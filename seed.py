
import random
import sqlite3

from werkzeug.security import generate_password_hash

import config

USER_COUNT, DRILL_COUNT, ATTEMPT_COUNT = 1000, 100_000, 1_000_000

connection = sqlite3.connect(config.DATABASE)
connection.execute("PRAGMA foreign_keys = ON")
password_hash = generate_password_hash("testitesti")

connection.executemany(
    "INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)",
    [(f"user{i}", password_hash) for i in range(1, USER_COUNT + 1)])
user_ids = [row[0] for row in
            connection.execute("SELECT id FROM users WHERE username LIKE 'user%'")]
category_ids = [row[0] for row in connection.execute("SELECT id FROM categories")]

connection.executemany(
    "INSERT INTO drills (user_id, title, description) VALUES (?, ?, ?)",
    [(random.choice(user_ids), f"Test drill {i}", f"Description of test drill {i}")
     for i in range(1, DRILL_COUNT + 1)])
first_drill_id = connection.execute("SELECT MAX(id) FROM drills").fetchone()[0] - DRILL_COUNT + 1
connection.executemany(
    "INSERT INTO drill_categories (drill_id, category_id) VALUES (?, ?)",
    [(first_drill_id + i, random.choice(category_ids)) for i in range(DRILL_COUNT)])
connection.executemany(
    "INSERT INTO attempts (drill_id, user_id, score, note) VALUES (?, ?, ?, ?)",
    [(first_drill_id + random.randrange(DRILL_COUNT), random.choice(user_ids),
      random.randint(0, 10), f"Note {i}")
     for i in range(ATTEMPT_COUNT)])
connection.commit()
connection.close()
print("Done.")