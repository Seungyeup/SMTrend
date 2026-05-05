from __future__ import annotations

import os

SQLALCHEMY_DATABASE_URI = os.getenv(
    "SQLALCHEMY_DATABASE_URI",
    "postgresql+psycopg2://superset:superset@superset-db:5432/superset",
)

FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
}

ROW_LIMIT = 10000
