
import sqlite3

import config

with open("schema.sql", encoding="utf-8") as schema_file:
    schema = schema_file.read()

connection = sqlite3.connect(config.DATABASE)
connection.executescript(schema)
connection.commit()
connection.close()
print(f"Database initialized: {config.DATABASE}")