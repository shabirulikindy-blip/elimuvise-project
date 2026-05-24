import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'exampler-secret-key')
    DATABASE_URL = os.environ.get('DATABASE_URL')

    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL must be set to a PostgreSQL URI like postgresql://user:password@localhost:5432/exampler')
    if not (DATABASE_URL.startswith('postgresql://') or DATABASE_URL.startswith('postgres://')):
        raise RuntimeError('DATABASE_URL must start with postgresql:// or postgres://')

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
