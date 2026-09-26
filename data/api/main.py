from fastapi import FastAPI, HTTPException, Query, Request
import json
import os
import math
import threading
import time

app = FastAPI(title="Olist FDE Paginated API")

API_DIR = "./data/api"
RATE_LIMIT_REQUESTS = int(os.getenv("OLIST_API_RATE_LIMIT", "5"))
RATE_LIMIT_WINDOW_SECONDS = float(os.getenv("OLIST_API_RATE_WINDOW", "1"))
_request_history = {}
_rate_limit_lock = threading.Lock()


def enforce_rate_limit(request: Request):
    client_key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS

    with _rate_limit_lock:
        recent_requests = [
            timestamp
            for timestamp in _request_history.get(client_key, [])
            if timestamp > window_start
        ]
        if len(recent_requests) >= RATE_LIMIT_REQUESTS:
            retry_after = max(1, math.ceil(recent_requests[0] + RATE_LIMIT_WINDOW_SECONDS - now))
            _request_history[client_key] = recent_requests
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )
        recent_requests.append(now)
        _request_history[client_key] = recent_requests

def load_json_as_list(filename):
    filepath = os.path.join(API_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            data = json.load(f)
            # Normalize to list if the mock data is a dictionary
            if isinstance(data, dict):
                return [{"id": k, **(v if isinstance(v, dict) else {"value": v})} for k, v in data.items()]
            return data
    return []

payments_data = load_json_as_list("payments.json")
geo_data = load_json_as_list("geolocation.json")

def paginate_data(data_list, page: int, page_size: int):
    total_records = len(data_list)
    total_pages = math.ceil(total_records / page_size) if total_records > 0 else 1
    
    if page < 1 or (page > total_pages and total_records > 0):
        raise HTTPException(status_code=404, detail="Page out of bounds")
        
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    return {
        "data": data_list[start_idx:end_idx],
        "total_pages": total_pages,
        "current_page": page,
        "total_records": total_records
    }

@app.get("/payments")
def get_payments(request: Request, page: int = Query(1, ge=1), page_size: int = Query(500, ge=1)):
    enforce_rate_limit(request)
    return paginate_data(payments_data, page, page_size)

@app.get("/geolocation")
def get_geolocation(request: Request, page: int = Query(1, ge=1), page_size: int = Query(500, ge=1)):
    enforce_rate_limit(request)
    return paginate_data(geo_data, page, page_size)