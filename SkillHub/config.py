import os
from django.core.exceptions import ImproperlyConfigured


class AppOptions:
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
    DEBUG = os.getenv("DEBUG", "True" if ENVIRONMENT == "development" else "False").lower() in ("true", "1")
    SECRET_KEY = os.getenv("SECRET_KEY", "django-stage-1-secret-key-demo")

    MAX_FILE_SIZE_BY_ENV = {
        "development": 10,
        "staging": 7,
        "production": 5,
    }
    DEFAULT_MAX_MB = MAX_FILE_SIZE_BY_ENV.get(ENVIRONMENT, 5)
    MAX_FILE_SIZE_MB = int(os.getenv("FILE_STORAGE_MAX_SIZE_MB", str(DEFAULT_MAX_MB)))

    OPENAPI_TITLE = os.getenv("OPENAPI_TITLE", "SkillHub API")
    OPENAPI_VERSION = os.getenv("OPENAPI_VERSION", "v1")
    OPENAPI_DESCRIPTION = os.getenv("OPENAPI_DESCRIPTION", "Платформа онлайн-навчання")

    @classmethod
    def validate(cls):
        if not cls.SECRET_KEY:
            raise ImproperlyConfigured("SECRET_KEY is required.")
        if cls.ENVIRONMENT == "production" and "demo" in cls.SECRET_KEY:
            raise ImproperlyConfigured("Insecure demo SECRET_KEY is not allowed in production.")
        if cls.MAX_FILE_SIZE_MB <= 0 or cls.MAX_FILE_SIZE_MB > 100:
            raise ImproperlyConfigured("FILE_STORAGE_MAX_SIZE_MB must be between 1 and 100.")
