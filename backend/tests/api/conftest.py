# Copyright 2026 Alokin LLC
# SPDX-License-Identifier: FCL-1.0-ALv2
"""Fixtures for API-level run-semantics tests.

The SQLite override MUST be set before any pyspur module is imported —
pyspur.database builds its engine at import time.
"""

import os
import tempfile

os.environ.setdefault(
    "SQLITE_OVERRIDE_DATABASE_URL",
    f"sqlite:///{tempfile.mkdtemp(prefix='pyspur_test_')}/test.db",
)

import pytest
from fastapi.testclient import TestClient

from pyspur.database import engine
from pyspur.models.base_model import BaseModel as Base

# Safety net: never run these tests against a real (postgres) database.
if not engine.url.drivername.startswith("sqlite"):
    raise RuntimeError(
        "tests/api requires a SQLite engine — pyspur.database was imported "
        "before the SQLITE_OVERRIDE_DATABASE_URL override could take effect."
    )


@pytest.fixture()
def client():
    from pyspur.api.api_app import api_app

    Base.metadata.create_all(engine)
    with TestClient(api_app) as c:
        yield c
    Base.metadata.drop_all(engine)
