import json
from cocpy.client import COCClient
import requests
from requests.models import Response

class DummySession(requests.Session):
    def __init__(self, status=200, payload=None, headers=None):
        super().__init__()
        self._status = status
        self._payload = payload or {}
        self._headers = headers or {}

    def request(self, method, url, **kwargs):
        r = Response()
        r.status_code = self._status
        r._content = json.dumps(self._payload).encode()
        r.headers.update(self._headers)
        return r

def test_tag_encoding():
    c = COCClient("t", session=DummySession())
    encoded = c._encode_tag("#2abc")
    assert encoded == "%232ABC"

def test_get_player_ok():
    sess = DummySession(payload={"name":"Alice","tag":"#2ABC"})
    c = COCClient("t", session=sess)
    assert c.get_player("#2ABC")["name"] == "Alice"