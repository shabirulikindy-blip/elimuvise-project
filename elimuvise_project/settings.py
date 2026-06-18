import os  # Fixed typo: changed 'from hire import os' to 'import os'
from pathlib import Path
from urllib.parse import urlparse
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# Standardized to use decouple's config for environment variables
SECRET_KEY = config('SECRET_KEY', default='elimuvise-secret-key')
DEBUG = config('DEBUG', default=False, cast=bool)

# Process ALLOWED_HOSTS safely
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS.split(',')]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'elimuvise_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'elimuvise_project.wsgi.application'

# Database Parsing Setup
DATABASE_URL = config('DATABASE_URL', default='postgresql://elimuvise_user:elimuvise_pass@localhost:5432/elimuvise')

url = urlparse(DATABASE_URL)
if url.scheme in ('postgresql', 'postgres'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': url.path[1:] if url.path else 'elimuvise',
            'USER': url.username if url.username else 'elimuvise_user',
            'PASSWORD': url.password if url.password else 'elimuvise_pass',
            'HOST': url.hostname if url.hostname else 'localhost',
            'PORT': url.port if url.port else 5432,
        }
    }
else:
    raise RuntimeError('DATABASE_URL must start with postgresql:// or postgres://')

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'dashboard.User'
LOGIN_URL = 'login'

# Session Timeout Configuration
# Admin session expires after 1 minute (60 seconds) of inactivity
SESSION_COOKIE_AGE = 60  # 1 minute for admin
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True  # Reset timeout on every request
ADMIN_SESSION_TIMEOUT = 60  # 1 minute timeout for admin dashboard