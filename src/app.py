"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi import Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import base64
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import time

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

logger = logging.getLogger(__name__)
ADMIN_CONFIG_PATH = Path(__file__).with_name("admins.json")
ADMIN_SESSION_COOKIE = "admin_session"
ADMIN_SESSION_MAX_AGE = 8 * 60 * 60
PASSWORD_HASH_ITERATIONS = 600_000


class AdminLogin(BaseModel):
    username: str
    password: str


class AdminConfigurationError(Exception):
    pass


def _session_secret() -> bytes:
    secret = os.getenv("ADMIN_SESSION_SECRET", "")
    if len(secret) < 32:
        raise AdminConfigurationError(
            "ADMIN_SESSION_SECRET must be configured with at least 32 characters."
        )
    return secret.encode("utf-8")


def _load_admins() -> list[dict[str, str]]:
    try:
        content = ADMIN_CONFIG_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise AdminConfigurationError(
            f"Admin account file not found: {ADMIN_CONFIG_PATH}"
        ) from error
    except OSError as error:
        raise AdminConfigurationError("Unable to read the admin account file.") from error

    try:
        admins = json.loads(content).get("admins")
    except (json.JSONDecodeError, AttributeError) as error:
        raise AdminConfigurationError(
            "The admin account file must contain an 'admins' array."
        ) from error

    if not isinstance(admins, list):
        raise AdminConfigurationError(
            "The admin account file must contain an 'admins' array."
        )

    for admin in admins:
        if (
            not isinstance(admin, dict)
            or not isinstance(admin.get("username"), str)
            or not isinstance(admin.get("salt"), str)
            or not isinstance(admin.get("password_hash"), str)
        ):
            raise AdminConfigurationError(
                "Each admin account must have username, salt, and password_hash strings."
            )
    return admins


def _verify_admin_credentials(username: str, password: str) -> bool:
    admins = _load_admins()
    admin = next((entry for entry in admins if entry["username"] == username), None)

    # Perform the same expensive operation for unknown usernames to reduce timing leaks.
    try:
        salt = bytes.fromhex(admin["salt"]) if admin else bytes(16)
        expected_hash = bytes.fromhex(admin["password_hash"]) if admin else bytes(32)
    except ValueError as error:
        raise AdminConfigurationError(
            "Admin salts and password hashes must be hex-encoded."
        ) from error

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return admin is not None and hmac.compare_digest(actual_hash, expected_hash)


def _encode_session(username: str) -> str:
    payload = json.dumps(
        {"sub": username, "exp": int(time.time()) + ADMIN_SESSION_MAX_AGE},
        separators=(",", ":"),
    ).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(
        _session_secret(), encoded_payload.encode("ascii"), hashlib.sha256
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{encoded_payload}.{encoded_signature}"


def _decode_session(token: str | None) -> str | None:
    if not token:
        return None

    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        expected_signature = hmac.new(
            _session_secret(), encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        signature = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )
        if not hmac.compare_digest(signature, expected_signature):
            return None

        payload = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )
        session = json.loads(payload)
        if (
            not isinstance(session, dict)
            or not isinstance(session.get("sub"), str)
            or not isinstance(session.get("exp"), int)
            or session["exp"] <= time.time()
        ):
            return None
        return session["sub"]
    except (AdminConfigurationError, ValueError, TypeError, UnicodeDecodeError):
        return None


def require_admin(request: Request) -> str:
    try:
        _session_secret()
    except AdminConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    username = _decode_session(request.cookies.get(ADMIN_SESSION_COOKIE))
    if username is None:
        raise HTTPException(status_code=401, detail="Staff sign-in required")
    return username


def _cookie_secure() -> bool:
    setting = os.getenv("ADMIN_COOKIE_SECURE", "true").lower()
    if setting not in {"true", "false"}:
        raise AdminConfigurationError("ADMIN_COOKIE_SECURE must be 'true' or 'false'.")
    return setting == "true"


# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/auth/session")
def get_admin_session(request: Request):
    try:
        _session_secret()
    except AdminConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {
        "authenticated": _decode_session(
            request.cookies.get(ADMIN_SESSION_COOKIE)
        )
        is not None
    }


@app.post("/auth/login")
def login_admin(credentials: AdminLogin):
    try:
        _session_secret()
        authenticated = _verify_admin_credentials(credentials.username, credentials.password)
        cookie_secure = _cookie_secure()
    except AdminConfigurationError as error:
        logger.error("Admin authentication is not configured: %s", error)
        raise HTTPException(
            status_code=503, detail="Staff sign-in is not configured."
        ) from error

    if not authenticated:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    result = JSONResponse(content={"message": "Signed in successfully"})
    result.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=_encode_session(credentials.username),
        max_age=ADMIN_SESSION_MAX_AGE,
        httponly=True,
        secure=cookie_secure,
        samesite="strict",
        path="/",
    )
    return result


@app.post("/auth/logout")
def logout_admin():
    result = JSONResponse(content={"message": "Signed out successfully"})
    result.delete_cookie(
        key=ADMIN_SESSION_COOKIE,
        httponly=True,
        secure=_cookie_secure(),
        samesite="strict",
        path="/",
    )
    return result


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str, email: str, _: str = Depends(require_admin)
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str, email: str, _: str = Depends(require_admin)
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
