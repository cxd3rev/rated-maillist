from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from email.message import EmailMessage
from collections import defaultdict
from time import time
import sqlite3
import hashlib
import secrets
import base64
import os
import smtplib
from pathlib import Path


# ============================================================
# APP SETUP
# ============================================================

app = FastAPI(title="RATED. API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin
        for origin in [
            "http://127.0.0.1:5500",
            "http://localhost:5500",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "http://127.0.0.1:5501",
            "http://localhost:5501",
            os.environ.get("RATED_ORIGIN", "").strip(),
        ]
        if origin
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATABASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE = BASE_DIR / "data" / "rated.db"


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db()
    cursor = connection.cursor()

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            profile_picture TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --------------------------------------------------------
    # SESSIONS
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE CASCADE
        )
        """
    )

    # --------------------------------------------------------
    # ALBUM RATINGS
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS album_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            album_id INTEGER NOT NULL,
            score REAL NOT NULL,

            UNIQUE(user_id, album_id),

            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE CASCADE
        )
        """
    )

    # --------------------------------------------------------
    # SONG RATINGS
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS song_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            album_id INTEGER NOT NULL,
            song_index INTEGER NOT NULL,
            score REAL NOT NULL,

            UNIQUE(user_id, album_id, song_index),

            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            welcome_sent INTEGER NOT NULL DEFAULT 0,
            launch_sent INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()


init_db()


# ============================================================
# PASSWORD SECURITY
# ============================================================

HASH_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    """
    Creates a secure PBKDF2 password hash.

    The returned value contains:
    algorithm + iterations + salt + hash
    """

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


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Checks a password against the stored password hash.
    """

    try:
        algorithm, iterations, salt_b64, hash_b64 = stored_hash.split("$")

        if algorithm != "pbkdf2_sha256":
            return False

        salt = base64.b64decode(salt_b64)
        original_hash = base64.b64decode(hash_b64)

        new_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )

        return secrets.compare_digest(new_hash, original_hash)

    except Exception:
        return False


# ============================================================
# AUTHENTICATION
# ============================================================

def create_session(user_id: int) -> str:
    """
    Creates a random login token and saves it in the database.
    """

    token = secrets.token_urlsafe(32)

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO sessions (user_id, token)
        VALUES (?, ?)
        """,
        (user_id, token),
    )

    connection.commit()
    connection.close()

    return token


def get_current_user(token: str | None):
    """
    Finds the user belonging to an authentication token.
    """

    if not token:
        return None

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            users.id,
            users.username,
            users.email,
            users.profile_picture,
            users.created_at
        FROM sessions
        JOIN users
            ON users.id = sessions.user_id
        WHERE sessions.token = ?
        """,
        (token,),
    )

    user = cursor.fetchone()

    connection.close()

    return user


def require_user(authorization: str | None):
    """
    Requires a valid Bearer token.
    """

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="You must be logged in.",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication format.",
        )

    token = authorization.replace("Bearer ", "", 1).strip()

    user = get_current_user(token)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session.",
        )

    return user


# ============================================================
# REQUEST MODELS
# ============================================================

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    profile_picture: str | None = None

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Enter a valid email address.")
        return email


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        return value.strip().lower()


class RatingRequest(BaseModel):
    album_id: int
    album_score: float
    song_ratings: dict[str, float]


class WaitlistRequest(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Enter a valid email address.")
        return email


# ============================================================
# BASIC ROUTE
# ============================================================

@app.get("/api")
def api_status():
    return {
        "status": "online",
        "message": "RATED. API is running."
    }


# ============================================================
# REGISTER
# ============================================================

@app.post("/register")
def register(data: RegisterRequest):

    username = data.username.strip()
    email = str(data.email).strip().lower()
    password = data.password

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    if len(username) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username must be at least 3 characters."
        )

    if len(username) > 30:
        raise HTTPException(
            status_code=400,
            detail="Username cannot exceed 30 characters."
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters."
        )

    # --------------------------------------------------------
    # Check existing account
    # --------------------------------------------------------

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM users
        WHERE username = ?
        """,
        (username,),
    )

    existing_username = cursor.fetchone()

    if existing_username:
        connection.close()

        raise HTTPException(
            status_code=400,
            detail="Username is already taken."
        )

    cursor.execute(
        """
        SELECT id
        FROM users
        WHERE email = ?
        """,
        (email,),
    )

    existing_email = cursor.fetchone()

    if existing_email:
        connection.close()

        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists."
        )

    # --------------------------------------------------------
    # Create account
    # --------------------------------------------------------

    password_hash = hash_password(password)

    cursor.execute(
        """
        INSERT INTO users (
            username,
            email,
            password_hash,
            profile_picture
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            username,
            email,
            password_hash,
            data.profile_picture,
        ),
    )

    user_id = cursor.lastrowid

    connection.commit()
    connection.close()

    # --------------------------------------------------------
    # Automatically log user in
    # --------------------------------------------------------

    token = create_session(user_id)

    return {
        "message": "Account created successfully.",
        "token": token,
        "user": {
            "id": user_id,
            "username": username,
            "email": email,
            "profile_picture": data.profile_picture,
        },
    }


# ============================================================
# LOGIN
# ============================================================

@app.post("/login")
def login(data: LoginRequest):

    email = str(data.email).strip().lower()

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email,),
    )

    user = cursor.fetchone()

    connection.close()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password."
        )

    if not verify_password(
        data.password,
        user["password_hash"],
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password."
        )

    # --------------------------------------------------------
    # Create session
    # --------------------------------------------------------

    token = create_session(user["id"])

    return {
        "message": "Login successful.",
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "profile_picture": user["profile_picture"],
        },
    }


# ============================================================
# CURRENT USER
# ============================================================

@app.get("/me")
def me(authorization: str | None = Header(default=None)):

    user = require_user(authorization)

    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "profile_picture": user["profile_picture"],
        "created_at": user["created_at"],
    }


# ============================================================
# LOGOUT
# ============================================================

@app.post("/logout")
def logout(authorization: str | None = Header(default=None)):

    if not authorization:
        return {
            "message": "Already logged out."
        }

    if not authorization.startswith("Bearer "):
        return {
            "message": "Already logged out."
        }

    token = authorization.replace(
        "Bearer ",
        "",
        1,
    ).strip()

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM sessions
        WHERE token = ?
        """,
        (token,),
    )

    connection.commit()
    connection.close()

    return {
        "message": "Logged out successfully."
    }


# ============================================================
# GET USER RATINGS
# ============================================================

@app.get("/ratings")
def get_ratings(
    authorization: str | None = Header(default=None)
):

    user = require_user(authorization)

    connection = get_db()
    cursor = connection.cursor()

    # --------------------------------------------------------
    # Get album ratings
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT
            album_id,
            score
        FROM album_ratings
        WHERE user_id = ?
        """,
        (user["id"],),
    )

    albums = cursor.fetchall()

    # --------------------------------------------------------
    # Get song ratings
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT
            album_id,
            song_index,
            score
        FROM song_ratings
        WHERE user_id = ?
        """,
        (user["id"],),
    )

    songs = cursor.fetchall()

    connection.close()

    # --------------------------------------------------------
    # Build response
    # --------------------------------------------------------

    ratings = {}

    for album in albums:

        album_id = str(album["album_id"])

        ratings[album_id] = {
            "albumScore": album["score"]
        }

    for song in songs:

        album_id = str(song["album_id"])
        song_index = str(song["song_index"])

        if album_id not in ratings:
            ratings[album_id] = {}

        ratings[album_id][song_index] = song["score"]

    return ratings


# ============================================================
# SAVE RATINGS
# ============================================================

@app.post("/ratings")
def save_ratings(
    data: RatingRequest,
    authorization: str | None = Header(default=None),
):

    user = require_user(authorization)

    # --------------------------------------------------------
    # Validate album score
    # --------------------------------------------------------

    if data.album_score < 0 or data.album_score > 10:
        raise HTTPException(
            status_code=400,
            detail="Album score must be between 0 and 10."
        )

    # --------------------------------------------------------
    # Validate song scores
    # --------------------------------------------------------

    for song_index, score in data.song_ratings.items():

        if score < 0 or score > 10:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid score for song {song_index}."
            )

    connection = get_db()
    cursor = connection.cursor()

    # --------------------------------------------------------
    # Save / update album rating
    # --------------------------------------------------------

    cursor.execute(
        """
        INSERT INTO album_ratings (
            user_id,
            album_id,
            score
        )
        VALUES (?, ?, ?)

        ON CONFLICT(user_id, album_id)
        DO UPDATE SET score = excluded.score
        """,
        (
            user["id"],
            data.album_id,
            data.album_score,
        ),
    )

    # --------------------------------------------------------
    # Save / update song ratings
    # --------------------------------------------------------

    for song_index, score in data.song_ratings.items():

        cursor.execute(
            """
            INSERT INTO song_ratings (
                user_id,
                album_id,
                song_index,
                score
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(user_id, album_id, song_index)
            DO UPDATE SET score = excluded.score
            """,
            (
                user["id"],
                data.album_id,
                int(song_index),
                score,
            ),
        )

    connection.commit()
    connection.close()

    return {
        "message": "Ratings saved successfully.",
        "album_id": data.album_id,
        "album_score": data.album_score,
        "song_ratings": data.song_ratings,
    }


# ============================================================
# DELETE ALBUM RATING
# ============================================================

@app.delete("/ratings/{album_id}")
def delete_album_rating(
    album_id: int,
    authorization: str | None = Header(default=None),
):

    user = require_user(authorization)

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM album_ratings
        WHERE user_id = ?
        AND album_id = ?
        """,
        (
            user["id"],
            album_id,
        ),
    )

    cursor.execute(
        """
        DELETE FROM song_ratings
        WHERE user_id = ?
        AND album_id = ?
        """,
        (
            user["id"],
            album_id,
        ),
    )

    connection.commit()
    connection.close()

    return {
        "message": "Album ratings deleted."
    }


# ============================================================
# SERVE FRONTEND
# ============================================================

@app.get("/")
def serve_frontend():

    frontend_file = BASE_DIR / "index.html"

    if frontend_file.exists():
        return FileResponse(frontend_file)

    return {
        "message": "RATED. backend is running.",
        "frontend": "index.html was not found."
    }


@app.get("/waitlist")
@app.get("/waitlist.html")
def serve_waitlist():
    waitlist_file = BASE_DIR / "waitlist.html"
    if waitlist_file.exists():
        return FileResponse(waitlist_file)
    raise HTTPException(status_code=404, detail="Waitlist page not found.")


@app.get("/waitlist.css")
def serve_waitlist_css():
    return FileResponse(BASE_DIR / "css" / "waitlist.css")


@app.get("/waitlist.js")
def serve_waitlist_js():
    return FileResponse(BASE_DIR / "js" / "waitlist.js")


@app.get("/icon.svg")
@app.get("/icon.png")
def serve_icon():
    return FileResponse(BASE_DIR / "assets" / "logo.png")


# ============================================================
# WAITLIST EMAIL
# ============================================================

WAITLIST_HITS = defaultdict(list)


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST", "").strip())


def send_waitlist_email(to_email: str, username: str, kind: str) -> bool:
    host = os.environ.get("SMTP_HOST", "").strip()
    if not host:
        return False

    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    sender = os.environ.get("SMTP_FROM", user or "rated@localhost")
    app_url = os.environ.get(
        "RATED_APP_URL",
        "http://127.0.0.1:8000",
    ).strip()

    if kind == "launch":
        subject = "RATED is live. Your seat is waiting."
        headline = "The list just opened."
        body = (
            f"Hey {username},\n\n"
            "RATED is live. Your waitlist account is ready — "
            "same username, same password, same inbox.\n\n"
            f"Walk in: {app_url}\n\n"
            "Rate the albums. Rank the catalog. Don't blink.\n\n"
            "— RATED."
        )
        html_copy = (
            f"<p>Hey {username},</p>"
            "<p>RATED is live. Your waitlist account is ready — "
            "same username, same password, same inbox.</p>"
            f'<p><a href="{app_url}" style="color:#ff2f92">Open RATED</a></p>'
            "<p>Rate the albums. Rank the catalog. Don't blink.</p>"
        )
    else:
        subject = "You're on the RATED waitlist."
        headline = "You're locked in."
        body = (
            f"Hey {username},\n\n"
            "You're on the RATED waitlist. When the app launches, "
            "this email is how we'll tap you in.\n\n"
            "Keep your username and password. That's your seat.\n\n"
            "— RATED."
        )
        html_copy = (
            f"<p>Hey {username},</p>"
            "<p>You're on the RATED waitlist. When the app launches, "
            "this email is how we'll tap you in.</p>"
            "<p>Keep your username and password. That's your seat.</p>"
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_email
    message.set_content(body)
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


def rate_limit_waitlist(ip: str) -> None:
    now = time()
    recent = [stamp for stamp in WAITLIST_HITS[ip] if now - stamp < 3600]
    if len(recent) >= 8:
        raise HTTPException(
            status_code=429,
            detail="Too many signups from this network. Try again later.",
        )
    recent.append(now)
    WAITLIST_HITS[ip] = recent


# ============================================================
# WAITLIST
# ============================================================

@app.get("/waitlist/count")
def waitlist_count():
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM waitlist")
    total = cursor.fetchone()["total"]
    connection.close()
    return {"count": total}


@app.post("/waitlist")
def join_waitlist(data: WaitlistRequest, request: Request):
    client = request.client.host if request.client else "unknown"
    rate_limit_waitlist(client)

    username = data.username.strip()
    email = str(data.email).strip().lower()
    password = data.password

    if len(username) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username must be at least 3 characters.",
        )

    if len(username) > 30:
        raise HTTPException(
            status_code=400,
            detail="Username cannot exceed 30 characters.",
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters.",
        )

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id FROM waitlist
        WHERE username = ? OR email = ?
        """,
        (username, email),
    )
    existing = cursor.fetchone()

    if existing:
        connection.close()
        raise HTTPException(
            status_code=400,
            detail="You're already on the list.",
        )

    cursor.execute(
        """
        SELECT id FROM users
        WHERE username = ? OR email = ?
        """,
        (username, email),
    )
    taken = cursor.fetchone()

    if taken:
        connection.close()
        raise HTTPException(
            status_code=400,
            detail="That username or email is already taken.",
        )

    password_hash = hash_password(password)

    cursor.execute(
        """
        INSERT INTO waitlist (
            username,
            email,
            password_hash
        )
        VALUES (?, ?, ?)
        """,
        (username, email, password_hash),
    )

    waitlist_id = cursor.lastrowid
    connection.commit()

    welcome_sent = 1 if send_waitlist_email(email, username, "welcome") else 0

    if welcome_sent:
        cursor.execute(
            "UPDATE waitlist SET welcome_sent = 1 WHERE id = ?",
            (waitlist_id,),
        )
        connection.commit()

    connection.close()

    return {
        "ok": True,
        "username": username,
        "email": email,
        "emailSent": bool(welcome_sent),
        "message": "You're locked in.",
    }


@app.post("/waitlist/notify")
def notify_waitlist_launch(x_waitlist_key: str | None = Header(default=None)):
    expected = os.environ.get("WAITLIST_NOTIFY_KEY", "").strip()
    if not expected or x_waitlist_key != expected:
        raise HTTPException(status_code=401, detail="Invalid notify key.")

    connection = get_db()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id, username, email
        FROM waitlist
        WHERE launch_sent = 0
        """
    )
    rows = cursor.fetchall()

    sent = 0
    for row in rows:
        if send_waitlist_email(row["email"], row["username"], "launch"):
            cursor.execute(
                "UPDATE waitlist SET launch_sent = 1 WHERE id = ?",
                (row["id"],),
            )
            sent += 1

    connection.commit()
    connection.close()

    return {"sent": sent, "total": len(rows)}


app.mount("/css", StaticFiles(directory=str(BASE_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(BASE_DIR / "js")), name="js")
app.mount("/assets", StaticFiles(directory=str(BASE_DIR / "assets")), name="assets")


# ============================================================
# STARTUP MESSAGE
# ============================================================

if __name__ == "__main__":
    import uvicorn

    print("")
    print("======================================")
    print("        RATED. BACKEND ONLINE")
    print("======================================")
    print("")
    print("Database:")
    print(DATABASE)
    print("")
    print("Server:")
    print("http://127.0.0.1:8000")
    print("")
    print("Waitlist:")
    print("http://127.0.0.1:8000/waitlist")
    print("")
    print("======================================")
    print("")

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
    )