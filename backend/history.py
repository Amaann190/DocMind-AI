"""Local conversation storage. Never store credentials or original uploads here."""
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "react-history.sqlite3"


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("""CREATE TABLE IF NOT EXISTS conversations (
        owner TEXT NOT NULL, id TEXT NOT NULL, title TEXT NOT NULL,
        payload TEXT NOT NULL, updated REAL NOT NULL, PRIMARY KEY (owner, id))""")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def listing(owner, query=""):
    with connect() as db:
        return [dict(row) for row in db.execute(
            """SELECT id, title, updated, json_array_length(payload, '$.messages') > 0 AS started
               FROM conversations WHERE owner=? AND instr(lower(title || payload), lower(?)) > 0
               ORDER BY updated DESC""", (owner, query))]


def read(owner, conversation_id):
    with connect() as db:
        row = db.execute("SELECT * FROM conversations WHERE owner=? AND id=?", (owner, conversation_id)).fetchone()
    return {**dict(row), "payload": json.loads(row["payload"])} if row else None


def save(owner, conversation_id, title, payload):
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO conversations VALUES (?, ?, ?, ?, ?)",
                   (owner, conversation_id, title, json.dumps(payload), time.time()))


def delete(owner, conversation_id=None):
    with connect() as db:
        if conversation_id is None:
            db.execute("DELETE FROM conversations WHERE owner=?", (owner,))
        else:
            db.execute("DELETE FROM conversations WHERE owner=? AND id=?", (owner, conversation_id))
