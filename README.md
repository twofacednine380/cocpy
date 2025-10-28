# cocpy

Unofficial Python client for the Clash of Clans API.

## Install
```bash
pip install cocpy
```

## Usage
```python
from cocpy import COCClient

client = COCClient("YOUR_JWT_TOKEN")
player = client.get_player("#2ABC")
print(player["name"])

ver = client.verify_player_token("#2ABC", "one-time-token")
print(ver["status"])
```