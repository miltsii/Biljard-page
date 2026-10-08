
import sqlite3

import config


def get_connection():
    connection = sqlite3.connect(config.DATABASE)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection


def query(sql, params=()):
    connection = get_connection()
    try:
        return connection.execute(sql, params).fetchall()
    finally:
        connection.close()


def execute(sql, params=()):
    connection = get_connection()
    try:
        result = connection.execute(sql, params)
        connection.commit()
        return result.lastrowid
    finally:
        connection.close()


def execute_many(sql, params_list):
    connection = get_connection()
    try:
        connection.executemany(sql, params_list)
        connection.commit()
    finally:
        connection.close()