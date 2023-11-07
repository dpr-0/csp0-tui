import time
from datetime import datetime, timedelta, timezone

import jwt
from pytest import fixture


@fixture
def alice_jwt():
    exp = (datetime.now(timezone.utc) + timedelta(seconds=60)).timestamp()
    time.time()
    token = jwt.encode({"exp": exp, "id": "alice"}, key="secret")
    return token


@fixture
def alice_invalid_jwt():
    exp = (datetime.now(timezone.utc) - timedelta(seconds=60)).timestamp()
    time.time()
    token = jwt.encode({"exp": exp, "id": "alice"}, key="secret")
    return token
