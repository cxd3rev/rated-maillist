"""
Stdlib waitlist server for when FastAPI is not installed.

  python waitlist_server.py

TikTok link (local): http://127.0.0.1:8000/waitlist

Email (optional):
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
Launch emails later:
  WAITLIST_NOTIFY_KEY=secret
  curl -X POST http://127.0.0.1:8000/waitlist/notify -H "x-waitlist-key: secret"
"""

from __future__ import annotations

from collections import defaultdict
from email.message import EmailMessage
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import time
from urllib.parse import urlparse
import json
import os
import sqlite3
import hashlib
import secrets
import base64
import smtplib

import mailer

BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("RATED_DB", BASE_DIR / "rated.db"))
HASH_ITERATIONS = 100_000
WAITLIST_HITS = defaultdict(list)


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db()
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            profile_picture TEXT,
            is_founder INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    mailer.init_founder_schema(connection)
    connection.commit()
    connection.close()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        HASH_ITERATIONS,
    )
    return (
        f"pbkdf2_sha256$"
        f"{HASH_ITERATIONS}$"
        f"{base64.b64encode(salt).decode('utf-8')}$"
        f"{base64.b64encode(password_hash).decode('utf-8')}"
    )


def send_waitlist_email(to_email: str, username: str, kind: str) -> bool:
    return mailer.send_waitlist_email(to_email, username, kind)


ALLOWED_FILES = {
    "/waitlist.html",
    "/waitlist.css",
    "/waitlist.js",
    "/css/waitlist.css",
    "/js/waitlist.js",
    "/icon.svg",
}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, x-waitlist-key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/waitlist", "/waitlist/", "/"):
            self.path = "/waitlist.html"
            return SimpleHTTPRequestHandler.do_GET(self)
        if path == "/waitlist/count":
            connection = get_db()
            payload = mailer.displayed_seat_count(connection)
            payload["launched"] = mailer.is_launched(connection)
            connection.commit()
            connection.close()
            return self.send_json(payload)
        if (
            path in ALLOWED_FILES
            or path.startswith("/css/")
            or path.startswith("/js/")
            or path.startswith("/assets/")
        ):
            return SimpleHTTPRequestHandler.do_GET(self)
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"

        if path == "/waitlist/notify":
            expected = os.environ.get("WAITLIST_NOTIFY_KEY", "").strip()
            key = self.headers.get("x-waitlist-key", "")
            if not expected or key != expected:
                return self.send_json({"detail": "Invalid notify key."}, 401)
            connection = get_db()
            mailer.set_launched(connection)
            rows = connection.execute("SELECT * FROM waitlist").fetchall()
            sent = 0
            promoted = 0
            for row in rows:
                mailer.promote_waitlist_row(connection, row)
                promoted += 1
                emailed = send_waitlist_email(row["email"], row["username"], "launch")
                connection.execute(
                    "UPDATE waitlist SET launch_sent = 1 WHERE id = ?",
                    (row["id"],),
                )
                if emailed:
                    sent += 1
            connection.commit()
            connection.close()
            return self.send_json(
                {
                    "sent": sent,
                    "promoted": promoted,
                    "total": len(rows),
                    "launched": True,
                }
            )

        if path != "/waitlist":
            self.send_error(404)
            return

        ip = self.client_address[0]
        now = time()
        recent = [stamp for stamp in WAITLIST_HITS[ip] if now - stamp < 3600]
        if len(recent) >= 8:
            return self.send_json(
                {"detail": "Too many signups from this network. Try again later."},
                429,
            )
        recent.append(now)
        WAITLIST_HITS[ip] = recent

        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return self.send_json({"detail": "Invalid request."}, 400)

        username = str(data.get("username", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))

        if len(username) < 3:
            return self.send_json(
                {"detail": "Username must be at least 3 characters."},
                400,
            )
        if len(username) > 30:
            return self.send_json(
                {"detail": "Username cannot exceed 30 characters."},
                400,
            )
        if "@" not in email or "." not in email.split("@")[-1]:
            return self.send_json(
                {"detail": "Enter a valid email address."},
                400,
            )
        if len(password) < 8:
            return self.send_json(
                {"detail": "Password must be at least 8 characters."},
                400,
            )

        connection = get_db()
        existing = connection.execute(
            """
            SELECT id FROM waitlist
            WHERE username = ? OR email = ?
            """,
            (username, email),
        ).fetchone()
        if existing:
            connection.close()
            return self.send_json(
                {"detail": "You're already on the list."},
                400,
            )

        updates = 1 if data.get("updates", True) else 0
        connection.execute(
            """
            INSERT INTO waitlist (username, email, password_hash, updates_opt_in)
            VALUES (?, ?, ?, ?)
            """,
            (username, email, hash_password(password), updates),
        )
        waitlist_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        seats = mailer.bump_seat_display(connection)
        connection.commit()

        welcome_sent = send_waitlist_email(email, username, "welcome")
        if welcome_sent:
            connection.execute(
                "UPDATE waitlist SET welcome_sent = 1 WHERE id = ?",
                (waitlist_id,),
            )
            connection.commit()
        connection.close()

        return self.send_json(
            {
                "ok": True,
                "username": username,
                "email": email,
                "emailSent": bool(welcome_sent),
                "count": seats["count"],
                "recalibrated": seats["recalibrated"],
                "message": "You're locked in.",
            }
        )


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Waitlist: http://127.0.0.1:{port}/waitlist")
    server.serve_forever()
