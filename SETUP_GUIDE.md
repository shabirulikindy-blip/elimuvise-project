# Django + PostgreSQL Setup Guide

## Prerequisites

### 1. Install PostgreSQL

#### Option A: Windows Installer (Recommended)
1. Download PostgreSQL from: https://www.postgresql.org/download/windows/
2. Run the installer (version 13 or higher)
3. During installation:
   - Set password for `postgres` user (e.g., `postgres`)
   - Set port to `5432` (default)
   - Remember the password you set
4. PostgreSQL will be installed and started automatically

#### Option B: Using Package Manager
```powershell
# Using Winget
winget install PostgreSQL.PostgreSQL

# Using Scoop
scoop install postgresql
```

---

## Setup Instructions

### 1. After PostgreSQL Installation

Open PowerShell and verify PostgreSQL is running:
```powershell
psql --version
```

### 2. Create the Database

Run the setup script:
```powershell
python setup_postgres.py
```

This script will:
- Create a PostgreSQL database named `elimuvise`
- Create a user with proper permissions
- Create all necessary tables

### 3. Install Python Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Run Django Migrations (Optional - if not done by setup script)

```powershell
python manage.py migrate
```

### 5. Create a Superuser (Admin Account)

```powershell
python manage.py createsuperuser
```

Follow the prompts to create an admin account.

---

## Running the Project

### Start the Django Development Server

```powershell
python manage.py runserver
```

The server will start at: **http://127.0.0.1:8000/**

### Access the Admin Panel

1. Go to: http://127.0.0.1:8000/admin/
2. Login with the superuser credentials you created

---

## Environment Variables (Optional)

If you want to use custom PostgreSQL credentials, create a `.env` file:

```
DATABASE_URL=postgresql://elimuvise_user:elimuvise_pass@localhost:5432/elimuvise
DEBUG=True
SECRET_KEY=your-secret-key-here
```

Then use python-decouple to load it in settings.py (already installed).

---

## Troubleshooting

### "psql is not recognized"
- PostgreSQL is not installed or not in PATH
- Restart PowerShell after installing PostgreSQL
- Or add PostgreSQL to PATH manually

### "Connection refused"
- PostgreSQL service is not running
- Windows: Start it from Services or run: `pg_ctl start`
- Or use PostgreSQL GUI tool to start the server

### "Password authentication failed"
- Check the password used during PostgreSQL installation
- Update the script or environment variables with correct credentials

---

## Project Structure

```
elimuvise/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── elimuvise_project/        # Django project settings
│   ├── settings.py         # Database configuration here
│   ├── urls.py
│   └── wsgi.py
├── dashboard/              # Main Django app
│   ├── models.py           # Database models
│   ├── views.py
│   ├── urls.py
│   └── migrations/
├── templates/              # HTML templates
└── static/                 # CSS, JS files
```

---

## Next Steps

1. Install PostgreSQL
2. Run `python setup_postgres.py`
3. Run `python manage.py runserver`
4. Open http://127.0.0.1:8000/ in your browser

Good to go! 🚀
