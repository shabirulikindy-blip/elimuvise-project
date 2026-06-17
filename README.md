# ElimuVISE Academic Dashboard MVP

A Django-based academic dashboard prototype for students, advisors, parents, and school administrators.

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
     If PowerShell script execution is disabled, run:
     ```powershell
     powershell -ExecutionPolicy Bypass -File .\run_server.ps1
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
4. Set `DATABASE_URL` for PostgreSQL if you want custom credentials. Example:
   ```powershell
    $env:DATABASE_URL = 'postgresql://elimuvise_user:elimuvise_pass@localhost:5432/elimuvise'
    ```
    If you do not set it, the project defaults to SQLite, or you can configure a custom PostgreSQL connection string:
    ```bash
    postgresql://elimuvise_user:elimuvise_pass@localhost:5432/elimuvise
   ```
   You can also create a `.env` file in the project root with the same value.
5. Apply database migrations:
   ```bash
   python manage.py migrate
   ```
6. Run the Django development server:
   ```bash
   python manage.py runserver
   ```
7. Open `http://127.0.0.1:8000` in your browser.

### Notes
- The Django app is designed for a PostgreSQL backend using `DATABASE_URL`.
- Set `DATABASE_URL` to a URI like:
  ```bash
  DATABASE_URL=postgresql://user:password@localhost:5432/elimuvise
  ```

## Sample Accounts
- ElimuVISE / project2026 (Admin)
- advisor@example.com / advisor123
- student123 / student123
- parent@example.com / parent123

## Optional PostgreSQL setup
The Django app supports PostgreSQL if you want a production-style database.

1. Install PostgreSQL and create a database named `elimuvise`.
2. Set `DATABASE_URL` to your PostgreSQL connection string before starting the app.

```bash
set DATABASE_URL=postgresql://user:password@localhost:5432/elimuvise
python manage.py migrate
python manage.py runserver
```

Or create a `.env` file with:
```
DATABASE_URL=postgresql://postgres:password@localhost:5432/elimuvise
SECRET_KEY=your-secret-key
```

### PostgreSQL admin password issues
If you see:

```text
FATAL:  password authentication failed for user "postgres"
```

then the `postgres` admin password entered during setup is incorrect.

Steps to recover:
1. Verify the password manually:
   ```powershell
   $env:PGPASSWORD='your-password'; psql -U postgres -h localhost -c "SELECT 1;"
   ```
2. If it still fails, edit `C:\Program Files\PostgreSQL\18\data\pg_hba.conf`.
   - Change `host all all 127.0.0.1/32 scram-sha-256` to `host all all 127.0.0.1/32 trust`
   - Change `host all all ::1/128 scram-sha-256` to `host all all ::1/128 trust`
3. Restart the PostgreSQL service:
   ```powershell
   Restart-Service postgresql-x64-18
   ```
4. Reset the password:
   ```powershell
   psql -U postgres -h localhost -c "ALTER USER postgres WITH PASSWORD 'new-password';"
   ```
5. Restore `pg_hba.conf` to `scram-sha-256` and restart PostgreSQL again.

Then rerun `python setup_postgres.py`.
