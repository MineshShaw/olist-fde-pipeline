from fastapi import FastAPI, HTTPException, Query
import json
import os
import math

app = FastAPI(title="Olist FDE Paginated API")

API_DIR = "./data/api"

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
def get_payments(page: int = Query(1, ge=1), page_size: int = Query(500, ge=1)):
    return paginate_data(payments_data, page, page_size)

@app.get("/geolocation")
def get_geolocation(page: int = Query(1, ge=1), page_size: int = Query(500, ge=1)):
    return paginate_data(geo_data, page, page_size)