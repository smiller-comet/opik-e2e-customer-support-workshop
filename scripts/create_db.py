"""
Create SQLite database from JSON data files.
Run this script to initialize the database before running the app.
"""

import json
import sqlite3
from pathlib import Path

import pandas as pd

# Get paths - script is in scripts/, data is at project root
script_dir = Path(__file__).parent
project_root = script_dir.parent
data_dir = project_root / "data"

# 1. Define the database name
DB_NAME = data_dir / "ohm_sweet_ohm.db"

# 2. Start fresh: Delete old DB if it exists
if DB_NAME.exists():
    DB_NAME.unlink()
    print("🗑️  Deleted existing database")

# Ensure data directory exists
data_dir.mkdir(exist_ok=True)

conn = sqlite3.connect(str(DB_NAME))
print(f"🔨 Creating new database: {DB_NAME}...")


# ==========================================
# HELPER FUNCTION TO LOAD JSON FILES
# ==========================================
def load_json_file(filename: str) -> list:
    """Loads a JSON file from the data directory"""
    filepath = data_dir / filename
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: Could not find file {filepath}")
        return []


# Load the data from your files
print("   ... Loading JSON files from disk")
orders_data = load_json_file("orders.json")
products_data = load_json_file("products.json")
stores_data = load_json_file("stores.json")
promotions_data = load_json_file("promotions.json")

# ==========================================
# TABLE 1: PRODUCTS
# ==========================================
print("   ... Processing products")
pd.DataFrame(products_data).to_sql("products", conn, index=False, if_exists="replace")

# ==========================================
# TABLE 2 & 3: STORES & INVENTORY (Flattening)
# ==========================================
print("   ... Processing stores")
store_rows = []
inventory_rows = []

for store in stores_data:
    store_rows.append({"store_id": store["store_id"], "name": store["name"], "address": store["address"], "phone": store["phone"]})
    # Flatten the inventory dictionary (nested JSON)
    for pid, qty in store["inventory"].items():
        inventory_rows.append({"store_id": store["store_id"], "product_id": pid, "stock_level": qty})

pd.DataFrame(store_rows).to_sql("stores", conn, index=False, if_exists="replace")
pd.DataFrame(inventory_rows).to_sql("store_inventory", conn, index=False, if_exists="replace")

# ==========================================
# TABLE 4 & 5: ORDERS & ORDER ITEMS (Flattening)
# ==========================================
print("   ... Processing orders")
order_rows = []
order_items_rows = []

for order in orders_data:
    order_rows.append(
        {
            "order_id": order["order_id"],
            "customer_name": order["customer_name"],
            "customer_email": order["customer_email"],
            "status": order["status"],
            "days_since_order": order["days_since_order"],
            "current_location": order["current_location"],
        }
    )
    # Flatten the items list (nested JSON)
    for item in order["items"]:
        order_items_rows.append(
            {"order_id": order["order_id"], "product_id": item["product_id"], "quantity": item["quantity"], "unit_price": item["price"]}
        )

pd.DataFrame(order_rows).to_sql("orders", conn, index=False, if_exists="replace")
pd.DataFrame(order_items_rows).to_sql("order_items", conn, index=False, if_exists="replace")

# ==========================================
# TABLE 6: PROMOTIONS
# ==========================================
print("   ... Processing promotions")
df_promos = pd.DataFrame(promotions_data)

# Convert list columns (like 'product_ids') to strings to avoid SQL errors
# Some rows might not have 'product_ids', so we handle missing values
if "product_ids" in df_promos.columns:
    df_promos["product_ids"] = df_promos["product_ids"].apply(lambda x: str(x) if isinstance(x, list) else x)

df_promos.to_sql("promotions", conn, index=False, if_exists="replace")

# Finalize
conn.close()
print(f"✅ Success! Database '{DB_NAME}' created with 6 tables.")
