import json
import os
from urllib.request import Request, urlopen


CONFIG_URL = os.getenv(
    "CARE_INSPECTOR_CONFIG_URL",
    "http://127.0.0.1:8000/api/collector/configuration",
)


def load_configuration() -> dict:
    key = os.getenv("CARE_INSPECTOR_COLLECTOR_KEY", "")

    if len(key) < 32:
        raise RuntimeError(
            "Collector machine key is missing or too short"
        )

    request = Request(
        CONFIG_URL,
        headers={"X-Collector-Key": key},
    )

    with urlopen(request, timeout=5) as response:
        return json.load(response)
