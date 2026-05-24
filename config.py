import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'exampler-secret-key')
    DATABASE_URL = os.environ.get(
        'DATABASE_URL',
        'postgresql://postgres:password@localhost:5432/exampler'
    )
    if not DATABASE_URL.startswith('postgresql://'):
        raise RuntimeError('DATABASE_URL must be a PostgreSQL URI starting with postgresql://')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
