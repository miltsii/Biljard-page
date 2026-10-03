
import sqlite3

import config

with open("schema.sql", encoding="utf-8") as f:
    schema = f.read()

con = sqlite3.connect(config.DATABASE)
con.executescript(schema)
con.commit()
con.close()
print(f"Tietokanta alustettu: {config.DATABASE}")