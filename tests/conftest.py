import os
import pytest
from dotenv import load_dotenv
from cocpy import COCClient

load_dotenv()

@pytest.fixture(scope="session")
def token():
    t = os.getenv("COC_TOKEN")
    if not t:
        pytest.skip("COC_TOKEN mancante in .env", allow_module_level=True)
    return t

@pytest.fixture(scope="session")
def client(token):
    return COCClient(token, timeout=20.0, max_retries=2, backoff=0.1)