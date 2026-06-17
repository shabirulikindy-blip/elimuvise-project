# ElimuVISE Django + PostgreSQL Project

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** (already installed)
- **PostgreSQL 13+** (needs to be installed)

---

## 📋 Step 1: Install PostgreSQL

### Option A: Windows Installer (Recommended)
1. Download: https://www.postgresql.org/download/windows/
2. Run installer
3. Remember the password you set for the `postgres` user
4. Default settings are fine (Port: 5432)
5. PostgreSQL will start automatically

### Option B: Package Manager
```powershell
# Using Winget
winget install PostgreSQL.PostgreSQL
```

---

## 🔧 Step 2: Setup (Run ONE of these)

### Method 1: Automated Setup (Recommended) - PowerShell
```powershell
powershell -ExecutionPolicy Bypass -File .\run_server.ps1
```
If PowerShell script execution is blocked, run the above command instead of `.
un_server.ps1`.
This will:
- Install Python packages
- Create PostgreSQL database
- Run migrations
- Create admin user
- Start the server

### Method 2: Automated Setup - Command Prompt
```cmd
run_server.bat
```

### Method 3: Manual Setup
```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup PostgreSQL
python setup_postgres.py

# 4. Create superuser
python manage.py createsuperuser

# 5. Start server
python manage.py runserver
```

---

## 🌐 Running the Server

### Start the server:
```powershell
python manage.py runserver
```

### Access the application:
- **Home**: http://127.0.0.1:8000/
- **Admin Panel**: http://127.0.0.1:8000/admin/

### Stop the server:
Press `Ctrl + C`

---

## 📁 Database Configuration

The project uses PostgreSQL with these default settings:
- **Database Name**: `elimuvise`
- **Host**: `localhost`
- **Port**: `5432`
- **User**: `elimuvise_user`
- **Password**: `elimuvise_pass`

To use custom settings, create a `.env` file:
```
DATABASE_URL=postgresql://elimuvise_user:elimuvise_pass@localhost:5432/elimuvise
DEBUG=True
SECRET_KEY=your-secret-key
```

---

## 🐛 Troubleshooting

### "psql is not recognized"
**Solution**: 
- Install PostgreSQL (see Step 1)
- Restart PowerShell after installation
- Verify with: `psql --version`

### "Connection refused" when running migrations
**Solution**:
- PostgreSQL service is not running
- Start PostgreSQL from Windows Services
- Or check if port 5432 is correct

### "Password authentication failed"
**Solution**:
- Check the password used during PostgreSQL installation
- Edit `setup_postgres.py` to use correct password
- Or set `DATABASE_URL` environment variable

### Port 8000 already in use
**Solution**:
```powershell
python manage.py runserver 8001
# Then visit: http://127.0.0.1:8001/
```

---

## 📚 Useful Commands

```powershell
# Create superuser
python manage.py createsuperuser

# Create migrations for model changes
python manage.py makemigrations

# Run pending migrations
python manage.py migrate

# Open Django shell
python manage.py shell

# Collect static files
python manage.py collectstatic

# Check for issues
python manage.py check

# Reset database (deletes all data!)
python manage.py migrate dashboard zero
python manage.py migrate
```

---

## 🏗️ Project Structure

```
elimuvise/
├── manage.py                    # Django management
├── requirements.txt             # Python packages
├── setup_postgres.py           # Database setup script
├── run_server.ps1              # PowerShell startup
├── run_server.bat              # Batch startup
│
├── elimuvise_project/           # Django project config
│   ├── settings.py            # Database & app config
│   ├── urls.py
│   ├── wsgi.py
│
├── dashboard/                  # Main Django app
│   ├── models.py              # Database models (User, Student, Result)
│   ├── views.py               # Page logic
│   ├── urls.py                # Routes
│   └── migrations/            # Database changes
│
├── templates/                  # HTML pages
├── static/                     # CSS, JavaScript
└── instance/                   # Instance-specific files
```

---

## 🔐 Security Notes

- Change `SECRET_KEY` in `.env` for production
- Set `DEBUG=False` in `.env` for production
- Use strong password for PostgreSQL
- Never commit `.env` file to version control

---

## 📞 Support

If you encounter issues:
1. Check the SETUP_GUIDE.md file
2. Verify PostgreSQL is running: `psql --version`
3. Check database connection: `python manage.py dbshell`
4. View Django logs in terminal

---

## ✅ Success!

Once the server is running:
1. Open http://127.0.0.1:8000/
2. Go to admin panel: http://127.0.0.1:8000/admin/
3. Login with your superuser credentials
4. Start using the application!

---

**Version**: 1.0  
**Framework**: Django 5.2+  
**Database**: PostgreSQL 13+  
**Python**: 3.8+
