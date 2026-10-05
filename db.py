
import sqlite3

import config


def get_connection():
    """Open a new database connection."""
    connection = sqlite3.connect(config.DATABASE)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection


def query(sql, params=()):
    """Run a SELECT and return all rows."""
    connection = get_connection()
    try:
        return connection.execute(sql, params).fetchall()
    finally:
        connection.close()


def execute(sql, params=()):
    """Run INSERT, UPDATE or DELETE and return the id of the last inserted row."""
    connection = get_connection()
    try:
        result = connection.execute(sql, params)
        connection.commit()
        return result.lastrowid
    finally:
        connection.close()


def execute_many(sql, params_list):
    """Run the same statement for each parameter tuple in one transaction."""
    connection = get_connection()
    try:
        connection.executemany(sql, params_list)
        connection.commit()
    finally:
        connection.close()