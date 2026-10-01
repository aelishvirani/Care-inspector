import json
from urllib.request import urlopen


CONFIG_URL = (
    "http://127.0.0.1:8000"
    "/api/configuration"
)


def load_configuration() -> dict:
    with urlopen(
        CONFIG_URL,
        timeout=5,
    ) as response:
        return json.load(response)
