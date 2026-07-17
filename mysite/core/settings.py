"""
Django settings for core project.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Bug #15 corrigido: carrega variáveis do arquivo mysite/.env
load_dotenv(BASE_DIR / ".env")

# Bug #15 corrigido: SECRET_KEY vem do .env, não mais hardcoded no código-fonte.
# Se não existir no .env, usa um fallback inseguro que deixa claro que precisa ser trocado.
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-TROQUE-ISSO-NO-ENV-nao-use-em-producao"
)

DEBUG = os.getenv("DEBUG", "True") == "True"

<<<<<<< Updated upstream
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "equate-chloride-penny.ngrok-free.dev",
=======
# Bug #15 corrigido: ALLOWED_HOSTS vem do .env — sem URL de ngrok morta hardcoded.
# No .env: ALLOWED_HOSTS=127.0.0.1,localhost,sua-url.ngrok-free.app
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if h.strip()
>>>>>>> Stashed changes
]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rolepermissions",
    "usuarios",
    "oraculo",
    "django_q",
]

ROLEPERMISSIONS_MODULE = "core.roles"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = "static/"
STATICFILES_DIRS = (os.path.join(BASE_DIR, "templates/static"),)
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Messages
from django.contrib.messages import constants

MESSAGES_TAGS = {
    constants.SUCCESS: "bg-green-50 text-green-700",
    constants.ERROR: "bg-red-50 text-red-700",
}

Q_CLUSTER = {
    "name": "ia",
    "workers": 1,
    "timeout": 300,
    "retry": 400,
    "queue_limit": 50,
    "orm": "default",
}

# Bug #6 corrigido: FileBasedCache funciona cross-process (o LocMemCache não funciona
# entre o processo do Django e o worker do django-q, fazendo o buffer do WhatsApp
# desaparecer antes de ser processado).
# A pasta django_cache/ é criada automaticamente pelo Django na primeira execução.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": str(BASE_DIR / "django_cache"),
        "TIMEOUT": 180,
    }
}
