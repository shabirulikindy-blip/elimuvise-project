#!/usr/bin/env python
"""
PostgreSQL Database Setup Script for ElimuVISE Django Project
This script sets up the PostgreSQL database and user for the project.
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, shell=False, env=None):
    "Run a shell command and return output"
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, check=False, env=env)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def verify_postgres_admin(postgres_user, postgres_password, postgres_host, postgres_port):
    env = os.environ.copy()
    if postgres_password:
        env['PGPASSWORD'] = postgres_password
    cmd = [
        'psql',
        '-h', postgres_host,
        '-U', postgres_user,
        '-p', postgres_port,
        '-d', 'postgres',
        '-At',
        '-c', "SELECT 1;"
    ]
    return run_command(cmd, env=env)


def setup_postgresql():
    "Set up PostgreSQL database and user"
    
    print("=" * 60)
    print("PostgreSQL Database Setup for ElimuVISE")
    print("=" * 60)
    
    # Check if psql is available
    returncode, stdout, stderr = run_command("psql --version")
    if returncode != 0:
        print("\nERROR: PostgreSQL is not installed or not in PATH")
        print("\nPlease install PostgreSQL first:")
        print("  - Download from: https://www.postgresql.org/download/windows/")
        print("  - Or use: winget install PostgreSQL.PostgreSQL")
        print("\nAfter installation, restart PowerShell and run this script again.")
        sys.exit(1)
    
    print(f"\nOK: PostgreSQL found: {stdout.strip()}")
    
    # Get PostgreSQL credentials
    print("\n" + "-" * 60)
    print("PostgreSQL Credentials")
    print("-" * 60)
    
    postgres_user = input("PostgreSQL admin username (default: postgres): ").strip() or "postgres"
    postgres_host = input("PostgreSQL host (default: localhost): ").strip() or "localhost"
    postgres_port = input("PostgreSQL port (default: 5432): ").strip() or "5432"

    postgres_password = None
    for attempt in range(3):
        postgres_password = input(f"Password for '{postgres_user}' (leave blank if none): ").strip()
        code, _, err = verify_postgres_admin(postgres_user, postgres_password, postgres_host, postgres_port)
        if code == 0:
            print("OK: PostgreSQL admin credentials validated")
            break
        print(f"ERROR: PostgreSQL admin authentication failed on attempt {attempt + 1}:\n{err.strip()}")
        if attempt < 2:
            print("Please verify the PostgreSQL admin password and try again.")
    else:
        print("\nUnable to authenticate to PostgreSQL after 3 attempts.")
        print("Make sure the superuser password for the 'postgres' account is correct.")
        print("You can test it manually with:")
        print("  $env:PGPASSWORD='your-password'; psql -U postgres -h localhost -c \"SELECT 1;\"")
        print("\nIf you have lost the password, reset it by temporarily editing:")
        print("  C:\\Program Files\\PostgreSQL\\18\\data\\pg_hba.conf")
        print("Change the localhost entries from scram-sha-256 to trust, restart PostgreSQL, then run:")
        print("  psql -U postgres -h localhost -c \"ALTER USER postgres WITH PASSWORD 'new-password';\"")
        print("Restore pg_hba.conf to scram-sha-256 and restart PostgreSQL again.")
        return False

    db_name = "elimuvise"
    db_user = "elimuvise_user"
    db_password = input("\nPassword for new database user (default: elimuvise_pass): ").strip() or "elimuvise_pass"

    print("\n" + "-" * 60)
    print("Creating Database and User...")
    print("-" * 60)

    def sql_quote(value: str) -> str:
        return value.replace("'", "''")

    env = os.environ.copy()
    if postgres_password:
        env['PGPASSWORD'] = postgres_password

    def run_psql(sql: str, db: str = 'postgres'):
        cmd = [
            'psql',
            '-h', postgres_host,
            '-U', postgres_user,
            '-p', postgres_port,
            '-d', db,
            '-At',
            '-c', sql,
        ]
        return run_command(cmd, env=env)

    db_exists_code, db_exists_out, db_exists_err = run_psql(
        f"SELECT 1 FROM pg_database WHERE datname = '{sql_quote(db_name)}';"
    )
    if db_exists_code != 0:
        print(f"ERROR: Failed to verify database existence:\n{db_exists_err}")
        return False

    if db_exists_out.strip() != '1':
        create_db_code, _, create_db_err = run_psql(f"CREATE DATABASE {db_name};")
        if create_db_code != 0:
            print(f"ERROR: Failed to create database {db_name}:\n{create_db_err}")
            return False
        print(f"OK: Created database {db_name}")
    else:
        print(f"OK: Database {db_name} already exists")

    user_exists_code, user_exists_out, user_exists_err = run_psql(
        f"SELECT 1 FROM pg_roles WHERE rolname = '{sql_quote(db_user)}';"
    )
    if user_exists_code != 0:
        print(f"ERROR: Failed to verify user existence:\n{user_exists_err}")
        return False

    if user_exists_out.strip() != '1':
        user_sql = f"CREATE USER {db_user} WITH PASSWORD '{sql_quote(db_password)}';"
        user_action = 'Created'
    else:
        user_sql = f"ALTER USER {db_user} WITH PASSWORD '{sql_quote(db_password)}';"
        user_action = 'Updated'

    user_code, _, user_err = run_psql(user_sql)
    if user_code != 0:
        print(f"ERROR: Failed to {user_action.lower()} user {db_user}:\n{user_err}")
        return False
    print(f"OK: {user_action} user {db_user}")

    grant_code, _, grant_err = run_psql(
        f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};"
    )
    if grant_code != 0:
        print(f"ERROR: Failed to grant privileges on {db_name}:\n{grant_err}")
        return False
    print(f"OK: Granted privileges on {db_name} to {db_user}")

    # Run Django migrations
    print("\n" + "-" * 60)
    print("Running Django Migrations...")
    print("-" * 60)
    
    # Set environment variable for Django
    os.environ['DATABASE_URL'] = f"postgresql://{db_user}:{db_password}@{postgres_host}:{postgres_port}/{db_name}"
    
    returncode, stdout, stderr = run_command([sys.executable, "manage.py", "migrate"])
    
    if returncode == 0:
        print("OK: Migrations completed successfully!")
    else:
        print(f"Migration output:\n{stdout}")
        if stderr:
            print(f"Errors:\n{stderr}")

    # Run Django seed_db
    print("\nSeeding database with sample logins...")
    seed_code, seed_stdout, seed_stderr = run_command([sys.executable, "manage.py", "seed_db"])
    if seed_code == 0:
        print("OK: Database seeded successfully!")
    else:
        print(f"Seeding output:\n{seed_stdout}")
        if seed_stderr:
            print(f"Errors:\n{seed_stderr}")

    # Persist database URL for future shell sessions
    env_file = Path('.env')
    env_content = f"DATABASE_URL=postgresql://{db_user}:{db_password}@{postgres_host}:{postgres_port}/{db_name}\n"
    if env_file.exists():
        existing = env_file.read_text()
        if 'DATABASE_URL=' not in existing:
            env_file.write_text(existing + env_content)
        else:
            env_file.write_text('\n'.join(
                [line for line in existing.splitlines() if not line.startswith('DATABASE_URL=')] + [env_content.strip()]) + '\n')
    else:
        env_file.write_text(env_content)
    print(f"\nOK: Persisted PostgreSQL URL to {env_file.resolve()}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print(f"\nDatabase URL for environment variable:")
    print(f"DATABASE_URL=postgresql://{db_user}:{db_password}@{postgres_host}:{postgres_port}/{db_name}")
    print("1. Run the server: python manage.py runserver")
    print("2. Visit: http://127.0.0.1:8000/ and log in using the sample credentials")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = setup_postgresql()
    sys.exit(0 if success else 1)
