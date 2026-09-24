from fastapi import FastAPI, HTTPException
import json
import os

app = FastAPI(title="Olist FDE Mock API")

API_DIR = "./data/api"

# Load JSON data into memory at startup for fast retrieval
def load_json(filename):
    filepath = os.path.join(API_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return {}

payments_data = load_json("payments.json")
geo_data = load_json("geolocation.json")

@app.get("/payments/{order_id}")
def get_payment(order_id: str):
    if order_id in payments_data:
        return {"order_id": order_id, "payments": payments_data[order_id]}
    raise HTTPException(status_code=404, detail="Order payment not found")

@app.get("/geolocation/{zip_code_prefix}")
def get_geolocation(zip_code_prefix: str):
    if zip_code_prefix in geo_data:
        return {"zip_code_prefix": zip_code_prefix, "geo": geo_data[zip_code_prefix]}
    raise HTTPException(status_code=404, detail="Geolocation not found")