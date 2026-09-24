import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_endpoints():
    print("Loading test keys from local files...")
    with open("./data/api/payments.json", "r") as f:
        sample_order_id = next(iter(json.load(f).keys()))
        
    with open("./data/api/geolocation.json", "r") as f:
        sample_zip = next(iter(json.load(f).keys()))

    print(f"\n--- Testing Payments API ---")
    print(f"Requesting Order ID: {sample_order_id}")
    res_payments = requests.get(f"{BASE_URL}/payments/{sample_order_id}")
    print(f"Status Code: {res_payments.status_code}")
    print("Response JSON:")
    print(json.dumps(res_payments.json(), indent=2))

    print(f"\n--- Testing Geolocation API ---")
    print(f"Requesting Zip Code Prefix: {sample_zip}")
    res_geo = requests.get(f"{BASE_URL}/geolocation/{sample_zip}")
    print(f"Status Code: {res_geo.status_code}")
    print("Response JSON:")
    print(json.dumps(res_geo.json(), indent=2))

if __name__ == "__main__":
    test_endpoints()