# Exampler Academic Dashboard MVP

A Flask-based academic dashboard prototype for students, advisors, parents, and school administrators.

## Features
- Student Academic Health dashboard with AI prediction badge, trend chart, study tips, and subject breakdown.
- Advisor Priority portal with class health stats, auto-sorted risk list, student registration, result uploads, and alert sending.
- Parent portal with simplified status, alert feed, attendance tracker, and advisor contact.
- Admin portal for high-level analytics, user management insights, and system logs.
- Role-based login and secure hashed credentials.
- AI advisory engine using rule-based predictions with a Random Forest design scaffold.

## Run locally
1. Install PostgreSQL and create a database named `exampler`.
2. Create a Python environment.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables (see PostgreSQL setup below).
5. Start the server:
   ```bash
   python app.py
   ```
6. Open `http://127.0.0.1:5000`.

## Sample Accounts
- admin@example.com / admin123
- advisor@example.com / advisor123
- student@example.com / student123
- parent@example.com / parent123

## PostgreSQL setup
This app uses PostgreSQL only. Do not use SQLite or any other database backend.

1. Install PostgreSQL and create a database named `exampler`.
2. Set `DATABASE_URL` to your PostgreSQL connection string before starting the app.

```bash
set DATABASE_URL=postgresql://user:password@localhost:5432/exampler
python app.py
```

Or create a `.env` file with:
```
DATABASE_URL=postgresql://postgres:password@localhost:5432/exampler
SECRET_KEY=your-secret-key
```
