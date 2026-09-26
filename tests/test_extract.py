import pytest
import pandas as pd
import sqlite3
import requests
from unittest.mock import patch, MagicMock
from src.extract import DataExtractor, ExtractionError

@pytest.fixture
def extractor():
    """Fixture to provide a configured DataExtractor instance."""
    return DataExtractor(data_dir="mock_data", api_url="http://mock-api.local")

@patch("src.extract.pd.read_csv")
def test_extract_csv_success(mock_read_csv, extractor):
    mock_df = pd.DataFrame({"order_id": ["A1", "B2"], "status": ["delivered", "shipped"]})
    mock_read_csv.return_value = mock_df
    
    result = extractor.extract_csv("raw/mock_orders.csv")
    
    mock_read_csv.assert_called_once()
    assert len(result) == 2
    assert "order_id" in result.columns

@patch("src.extract.pd.read_csv", side_effect=FileNotFoundError("File missing"))
def test_extract_csv_failure(mock_read_csv, extractor):
    with pytest.raises(ExtractionError, match="CSV Extraction failed"):
        extractor.extract_csv("raw/missing.csv")

@patch("src.extract.sqlite3.connect")
@patch("src.extract.pd.read_sql_query")
def test_extract_sqlite_success(mock_read_sql, mock_connect, extractor):
    mock_df = pd.DataFrame({"item_id": [1, 2], "price": [10.5, 20.0]})
    mock_read_sql.return_value = mock_df
    
    # Mock the context manager for sqlite3.connect
    mock_conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn

    result = extractor.extract_sqlite("SELECT * FROM items", "raw/mock.db")
    
    mock_connect.assert_called_once()
    mock_read_sql.assert_called_once_with("SELECT * FROM items", mock_conn)
    assert len(result) == 2

@patch("src.extract.requests.get")
def test_extract_api_pagination_success(mock_get, extractor):
    # Mock a 2-page API response
    def mock_api_response(url, timeout):
        mock_resp = MagicMock()
        if "page=1" in url:
            mock_resp.json.return_value = {
                "data": [{"payment_id": "P1"}],
                "total_pages": 2,
                "current_page": 1
            }
        else:
            mock_resp.json.return_value = {
                "data": [{"payment_id": "P2"}],
                "total_pages": 2,
                "current_page": 2
            }
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    mock_get.side_effect = mock_api_response
    
    result = extractor.extract_api("/payments")
    
    assert mock_get.call_count == 2
    assert len(result) == 2
    assert result.iloc[0]["payment_id"] == "P1"

@patch("src.extract.requests.get")
def test_extract_api_http_error(mock_get, extractor):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
    mock_get.return_value = mock_response
    
    with pytest.raises(ExtractionError, match="API Extraction failed"):
        # The script will attempt page 1 and fail immediately
        extractor.extract_api("/bad_endpoint")


def test_run_all_extracts_every_transformed_dataset(extractor):
    from unittest.mock import call

    frame = pd.DataFrame({"value": [1]})
    sqlite_extract = MagicMock(side_effect=[frame] * 5)
    extractor.extract_csv = MagicMock(return_value=frame)
    extractor.extract_sqlite = sqlite_extract
    extractor.extract_api = MagicMock(return_value=frame)

    result = extractor.run_all()

    assert set(result) == {
        "orders",
        "reviews",
        "items",
        "customers",
        "sellers",
        "products",
        "category_translation",
        "payments",
        "geolocation",
    }
    assert sqlite_extract.call_args_list == [
        call(),
        call("SELECT * FROM customers", filename="raw/ecommerce.db"),
        call("SELECT * FROM sellers", filename="raw/ecommerce.db"),
        call("SELECT * FROM products", filename="raw/ecommerce.db"),
        call("SELECT * FROM category_translation", filename="raw/ecommerce.db"),
    ]


@patch("src.extract.time.sleep")
@patch("src.extract.requests.get")
def test_extract_api_retries_rate_limit(mock_get, mock_sleep):
    logger = MagicMock()
    extractor = DataExtractor(data_dir="mock_data", api_url="http://mock-api.local", logger=logger)
    rate_limited = MagicMock(status_code=429, headers={"Retry-After": "0"})
    rate_limited.raise_for_status.side_effect = requests.exceptions.HTTPError("429 Too Many Requests")
    success = MagicMock(status_code=200, headers={})
    success.json.return_value = {
        "data": [{"payment_id": "P1"}],
        "total_pages": 1,
        "total_records": 1,
    }
    mock_get.side_effect = [rate_limited, success]

    result = extractor.extract_api("/payments")

    assert len(result) == 1
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(0.0)
    assert any("retry 1/3" in call.args[0] for call in logger.warn.call_args_list)