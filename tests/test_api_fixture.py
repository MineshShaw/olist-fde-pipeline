from pathlib import Path

import pytest
from starlette.requests import Request

from data.api import main


def test_fixture_paths_are_anchored_to_module_not_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert Path(main.API_DIR) == Path(main.__file__).resolve().parent
    assert main.payments_data
    assert "order_id" in main.payments_data[0]
    assert "geolocation_zip_code_prefix" in main.geo_data[0]


def test_fixture_loader_fails_clearly_when_file_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "API_DIR", tmp_path)

    with pytest.raises(RuntimeError, match="Unable to load API fixture"):
        main.load_json_as_list("missing.json", "order_id")


@pytest.mark.parametrize(
    "contents,exception,message",
    [
        ("{", RuntimeError, "Unable to load API fixture"),
        ('["not-an-object"]', ValueError, "only JSON objects"),
        ('{"O1": "not-an-object"}', ValueError, "objects or lists"),
    ],
)
def test_fixture_loader_rejects_invalid_json_shapes(
    tmp_path, monkeypatch, contents, exception, message
):
    monkeypatch.setattr(main, "API_DIR", tmp_path)
    (tmp_path / "fixture.json").write_text(contents, encoding="utf-8")

    with pytest.raises(exception, match=message):
        main.load_json_as_list("fixture.json", "order_id")


def test_paginated_fixture_endpoints_expose_extractable_metadata():
    main._request_history.clear()
    request = Request({"type": "http", "client": ("unit-test", 12345)})
    routes = (main.get_payments, main.get_geolocation)
    for route in routes:
        payload = route(request, page=1, page_size=10)

        assert isinstance(payload["data"], list)
        assert isinstance(payload["total_pages"], int)
        assert payload["total_pages"] >= 1
        assert isinstance(payload["total_records"], int)
        assert payload["total_records"] >= 0
