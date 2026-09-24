import pandas as pd
import sqlite3
import json
import os

SOURCE_DIR = "./data/source_zip/olist"
RAW_DIR = "./data/raw"
API_DIR = "./data/api_mock"

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(API_DIR, exist_ok=True)

# 1. Retain core workflow and support logs as CSVs (2 files)
print("Copying CSVs...")
pd.read_csv(f"{SOURCE_DIR}/olist_orders_dataset.csv").to_csv(f"{RAW_DIR}/orders.csv", index=False)
pd.read_csv(f"{SOURCE_DIR}/olist_order_reviews_dataset.csv").to_csv(f"{RAW_DIR}/reviews.csv", index=False)

# 2. Push relational and master data to the SQLite database (5 files)
print("Building SQLite Database...")
conn = sqlite3.connect(f"{RAW_DIR}/ecommerce.db")

db_files = {
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "category_translation": "product_category_name_translation.csv"
}

for table_name, file_name in db_files.items():
    df = pd.read_csv(f"{SOURCE_DIR}/{file_name}")
    df.to_sql(table_name, conn, if_exists="replace", index=False)

conn.close()

# 3. Transform external services data into JSON format for the mock APIs (2 files)
print("Generating API JSON payloads...")

# Payment Gateway API Mock
payments_df = pd.read_csv(f"{SOURCE_DIR}/olist_order_payments_dataset.csv")
payments_dict = (
    payments_df.groupby("order_id")
    .apply(lambda x: x.to_dict(orient="records"))
    .to_dict()
)
with open(f"{API_DIR}/payments.json", "w") as f:
    json.dump(payments_dict, f, indent=4)

# Geolocation / Postal Service API Mock
# The raw geolocation file contains over 1 million rows with duplicate zip codes. 
# Grouping by prefix compresses it into a distinct, high-performance API lookup dictionary.
geo_df = pd.read_csv(f"{SOURCE_DIR}/olist_geolocation_dataset.csv")
geo_dict = (
    geo_df.groupby("geolocation_zip_code_prefix")
    .agg({
        "geolocation_lat": "mean",
        "geolocation_lng": "mean",
        "geolocation_city": "first",
        "geolocation_state": "first"
    })
    .reset_index()
    .set_index("geolocation_zip_code_prefix")
    .to_dict(orient="index")
)
with open(f"{API_DIR}/geolocation.json", "w") as f:
    json.dump(geo_dict, f, indent=4)

print("All 9 files transformed successfully.")