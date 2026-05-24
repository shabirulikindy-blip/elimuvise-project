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
1. Create a Python environment:
   ```bash
   python -m venv .venv
   ```
2. Activate the environment:
   - Windows PowerShell:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   - Windows cmd:
     ```cmd
     .\.venv\Scripts\activate.bat
     ```
   - macOS / Linux:
     ```bash
     source .venv/bin/activate
     ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` if you want to override defaults:
   ```bash
   copy .env.example .env
   ```
5. Run the app:
   ```bash
   python app.py
   ```
6. Open `http://127.0.0.1:5000` in your browser.

### Notes
- This app requires PostgreSQL and will not start without a valid `DATABASE_URL`.
- Set `DATABASE_URL` to a PostgreSQL URI, for example:
  ```bash
  DATABASE_URL=postgresql://user:password@localhost:5432/exampler
  ```

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
