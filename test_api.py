"""Manual smoke check for a running local API fixture (not an offline pytest)."""

import requests

__test__ = False

BASE_URL = "http://127.0.0.1:8000"


def run_smoke_check() -> None:
    for endpoint in ("payments", "geolocation"):
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            params={"page": 1, "page_size": 10},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError(f"{endpoint} response must be a JSON object")
        if not isinstance(payload.get("data"), list):
            raise ValueError(f"{endpoint} response must include a data list")
        if not isinstance(payload.get("total_pages"), int) or payload["total_pages"] < 1:
            raise ValueError(f"{endpoint} response must include positive total_pages metadata")
        if not isinstance(payload.get("total_records"), int) or payload["total_records"] < 0:
            raise ValueError(
                f"{endpoint} response must include non-negative total_records metadata"
            )
        print(
            f"{endpoint}: received {len(payload['data'])} record(s) "
            f"on page 1 of {payload['total_pages']} "
            f"({payload['total_records']} total)"
        )


if __name__ == "__main__":
    run_smoke_check()
