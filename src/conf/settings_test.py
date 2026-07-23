from decouple import config

from .settings import *

STATIC_URL = config("STATIC_URL", default="/static/")
STATIC_ROOT = config("STATIC_ROOT", default="staticfiles")

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:", "TEST": {}}
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# Django-Q2: modo síncrono em testes (sem Redis)
Q_CLUSTER = {
    "name": "helper-test",
    "workers": 1,
    "timeout": 60,
    "orm": "default",
    "sync": True,
}
