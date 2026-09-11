"""Waitlist accounts, mailing lists, launch mail, and founder promotion."""

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path
import json
import os
import smtplib
from datetime import datetime, timezone


OUTBOX = Path(__file__).resolve().parent / "data" / "mail_outbox.jsonl"


def add_column(cursor, table: str, column: str, spec: str) -> None:
    names = {row[1] for row in cursor.execute(f"PRAGMA table_info({table})")}
    if column not in names:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {spec}")


def init_founder_schema(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            welcome_sent INTEGER NOT NULL DEFAULT 0,
            launch_sent INTEGER NOT NULL DEFAULT 0,
            updates_opt_in INTEGER NOT NULL DEFAULT 1,
            promoted_user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    add_column(cursor, "users", "is_founder", "INTEGER NOT NULL DEFAULT 0")
    add_column(cursor, "waitlist", "welcome_sent", "INTEGER NOT NULL DEFAULT 0")
    add_column(cursor, "waitlist", "launch_sent", "INTEGER NOT NULL DEFAULT 0")
    add_column(cursor, "waitlist", "updates_opt_in", "INTEGER NOT NULL DEFAULT 1")
    add_column(cursor, "waitlist", "promoted_user_id", "INTEGER")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS app_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        "INSERT OR IGNORE INTO app_state (key, value) VALUES ('launched', '0')"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO app_state (key, value) VALUES ('seat_display', '4781')"
    )


SEAT_SEED = 4781
SEAT_RECALIBRATE_AT = 5000


def _state_int(cursor, key: str, default: int) -> int:
    row = cursor.execute(
        "SELECT value FROM app_state WHERE key = ?",
        (key,),
    ).fetchone()
    if not row:
        return default
    try:
        return int(str(row["value"]))
    except (TypeError, ValueError):
        return default


def real_waitlist_count(cursor) -> int:
    return int(
        cursor.execute("SELECT COUNT(*) AS total FROM waitlist").fetchone()["total"]
    )


def displayed_seat_count(cursor) -> dict:
    real = real_waitlist_count(cursor)
    recalibrated = real >= SEAT_RECALIBRATE_AT
    if recalibrated:
        display = real
        cursor.execute(
            """
            INSERT INTO app_state (key, value) VALUES ('seat_display', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (str(display),),
        )
    else:
        display = max(SEAT_SEED, _state_int(cursor, "seat_display", SEAT_SEED))
    return {
        "count": display,
        "real": real,
        "recalibrated": recalibrated,
    }


def bump_seat_display(cursor) -> dict:
    real = real_waitlist_count(cursor)
    if real >= SEAT_RECALIBRATE_AT:
        return displayed_seat_count(cursor)
    current = max(SEAT_SEED, _state_int(cursor, "seat_display", SEAT_SEED))
    nxt = current + 1
    cursor.execute(
        """
        INSERT INTO app_state (key, value) VALUES ('seat_display', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (str(nxt),),
    )
    return {
        "count": nxt,
        "real": real,
        "recalibrated": False,
    }


def is_launched(cursor) -> bool:
    row = cursor.execute(
        "SELECT value FROM app_state WHERE key = 'launched'"
    ).fetchone()
    return bool(row) and str(row["value"]) == "1"


def set_launched(cursor) -> None:
    cursor.execute(
        """
        INSERT INTO app_state (key, value) VALUES ('launched', '1')
        ON CONFLICT(key) DO UPDATE SET value = '1'
        """
    )


def public_user(row) -> dict:
    keys = row.keys()
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "profile_picture": row["profile_picture"] if "profile_picture" in keys else None,
        "is_founder": bool(row["is_founder"]) if "is_founder" in keys else False,
    }


def promote_waitlist_row(cursor, row) -> int:
    if row["promoted_user_id"]:
        return int(row["promoted_user_id"])

    existing = cursor.execute(
        """
        SELECT id FROM users
        WHERE username = ? OR email = ?
        """,
        (row["username"], row["email"]),
    ).fetchone()
    if existing:
        user_id = int(existing["id"])
        cursor.execute(
            "UPDATE users SET is_founder = 1 WHERE id = ?",
            (user_id,),
        )
    else:
        result = cursor.execute(
            """
            INSERT INTO users (
                username,
                email,
                password_hash,
                profile_picture,
                is_founder
            )
            VALUES (?, ?, ?, NULL, 1)
            """,
            (row["username"], row["email"], row["password_hash"]),
        )
        user_id = int(result.lastrowid)

    cursor.execute(
        "UPDATE waitlist SET promoted_user_id = ? WHERE id = ?",
        (user_id, row["id"]),
    )
    return user_id


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST", "").strip())


def app_url() -> str:
    return os.environ.get("RATED_APP_URL", "http://127.0.0.1:8000").strip()


def compose_email(to_email: str, username: str, kind: str) -> tuple[str, str, str, str]:
    url = app_url()
    if kind == "launch":
        subject = "RATED is live. Your seat is waiting."
        headline = "The list just opened."
        text = (
            f"Hey {username},\n\n"
            "RATED is live. Your waitlist account is ready — "
            "same username, same password, same inbox.\n\n"
            "Log in and you'll see a gold star next to your name. "
            "That's for believing in the app before release.\n\n"
            f"Walk in: {url}\n\n"
            "— RATED."
        )
        html_copy = (
            f"<p>Hey {username},</p>"
            "<p>RATED is live. Your waitlist account is ready — "
            "same username, same password, same inbox.</p>"
            "<p>Log in and you'll see a gold star next to your name. "
            "That's for believing in the app before release.</p>"
            f'<p><a href="{url}" style="color:#ff2f92">Open RATED</a></p>'
        )
    elif kind == "updates":
        subject = "RATED update"
        headline = "Something new."
        text = (
            f"Hey {username},\n\n"
            "A quick update from RATED — you're on the product list "
            "because you asked for it.\n\n"
            f"{url}\n\n"
            "— RATED."
        )
        html_copy = (
            f"<p>Hey {username},</p>"
            "<p>A quick update from RATED — you're on the product list "
            "because you asked for it.</p>"
            f'<p><a href="{url}" style="color:#ff2f92">Open RATED</a></p>'
        )
    else:
        subject = "You're on the RATED waitlist."
        headline = "You're locked in."
        text = (
            f"Hey {username},\n\n"
            "You're on the RATED waitlist and mailing list. "
            "When the app launches, this inbox gets the keys.\n\n"
            "Keep your username and password. That's your seat — "
            "and a gold star next to your name when you walk in.\n\n"
            "— RATED."
        )
        html_copy = (
            f"<p>Hey {username},</p>"
            "<p>You're on the RATED waitlist and mailing list. "
            "When the app launches, this inbox gets the keys.</p>"
            "<p>Keep your username and password. That's your seat — "
            "and a gold star next to your name when you walk in.</p>"
        )
    return subject, headline, text, html_copy


def write_outbox(to_email: str, username: str, kind: str, subject: str, text: str) -> None:
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "at": datetime.now(timezone.utc).isoformat(),
        "to": to_email,
        "username": username,
        "kind": kind,
        "subject": subject,
        "text": text,
    }
    with OUTBOX.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def send_waitlist_email(to_email: str, username: str, kind: str) -> bool:
    subject, headline, text, html_copy = compose_email(to_email, username, kind)
    write_outbox(to_email, username, kind, subject, text)

    host = os.environ.get("SMTP_HOST", "").strip()
    if not host:
        return False

    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    sender = os.environ.get("SMTP_FROM", user or "rated@localhost")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_email
    message.set_content(text)
    message.add_alternative(
        f"""
        <html>
          <body style="margin:0;padding:32px;background:#080808;color:#f4f4f4;font-family:Inter,Arial,sans-serif;">
            <div style="max-width:480px;margin:0 auto;">
              <p style="letter-spacing:3px;font-size:11px;color:#ff2f92;font-weight:700;">RATED.</p>
              <h1 style="font-size:28px;letter-spacing:-1px;">{headline}</h1>
              {html_copy}
              <p style="color:#777;font-size:13px;">— RATED.</p>
            </div>
          </body>
        </html>
        """,
        subtype="html",
    )

    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls()
            if user:
                smtp.login(user, password)
            smtp.send_message(message)
        return True
    except Exception as error:
        print("Waitlist email failed:", error)
        return False
