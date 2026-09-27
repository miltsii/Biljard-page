import sqlite3
from flask import g

def get_connection():
    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con
