# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Staff can register and unregister students after signing in
- Students and visitors can view activities and participant lists without signing in

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Create a staff account. The password is stored as a salted hash in a local
   `src/admins.json` file, which is ignored by Git:

   ```
   python src/manage_admins.py teacher
   ```

3. Configure the signing secret and start the application. Generate a secret
   with `python -c "import secrets; print(secrets.token_hex(32))"`. Set
   `ADMIN_SESSION_SECRET` to the generated value. For local HTTP development,
   set `ADMIN_COOKIE_SECURE=false`; keep it `true` when serving over HTTPS.

   ```
   uvicorn src.app:app --reload
   ```

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc
   - Activities website: http://localhost:8000/

## Staff Access

The activity list and participant names/emails remain visible without an account.
The API requires a signed, HTTP-only staff session cookie to register or
unregister students. Staff accounts are stored locally in `src/admins.json`;
use `python src/manage_admins.py USERNAME` to add an account or update its
password. Do not commit this file or share the session secret. Sessions expire
after eight hours.

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| GET    | `/auth/session`                                                   | Check whether the current browser has a valid staff session          |
| POST   | `/auth/login`                                                     | Sign in as staff; sets an HTTP-only session cookie                   |
| POST   | `/auth/logout`                                                    | Sign out and clear the session cookie                                |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Register a student (staff session required)                         |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (staff session required)                    |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity and registration data is stored in memory and resets when the server
restarts. Staff accounts are stored separately in the local, Git-ignored
`src/admins.json` file.
