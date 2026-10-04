
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
DATABASE = os.environ.get("DATABASE", "database.db")
PAGE_SIZE = 10