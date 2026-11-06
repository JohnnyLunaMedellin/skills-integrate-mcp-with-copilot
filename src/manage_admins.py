"""Create or update local staff accounts for the activities app."""

import getpass
import hashlib
import json
import secrets
import sys
from pathlib import Path


ADMIN_CONFIG_PATH = Path(__file__).with_name("admins.json")
PASSWORD_HASH_ITERATIONS = 600_000
MIN_PASSWORD_LENGTH = 12


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        print("Usage: python src/manage_admins.py USERNAME", file=sys.stderr)
        return 2

    username = sys.argv[1].strip()
    password = getpass.getpass("Password (minimum 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        print("Password must be at least 12 characters long.", file=sys.stderr)
        return 1
    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 1

    try:
        existing = json.loads(ADMIN_CONFIG_PATH.read_text(encoding="utf-8"))
        admins = existing.get("admins")
        if not isinstance(admins, list):
            raise ValueError("The admin account file must contain an 'admins' array.")
    except FileNotFoundError:
        admins = []
    except (OSError, json.JSONDecodeError, AttributeError, ValueError) as error:
        print(f"Unable to read existing admin accounts: {error}", file=sys.stderr)
        return 1

    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    account = {
        "username": username,
        "salt": salt.hex(),
        "password_hash": password_hash.hex(),
    }

    for index, admin in enumerate(admins):
        if isinstance(admin, dict) and admin.get("username") == username:
            admins[index] = account
            break
    else:
        admins.append(account)

    try:
        ADMIN_CONFIG_PATH.write_text(
            json.dumps({"admins": admins}, indent=2) + "\n", encoding="utf-8"
        )
    except OSError as error:
        print(f"Unable to save admin account: {error}", file=sys.stderr)
        return 1

    print(f"Admin account '{username}' saved to {ADMIN_CONFIG_PATH}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
