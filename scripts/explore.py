import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

orders = pd.read_csv("data/raw/olist_orders_dataset.csv")
items = pd.read_csv("data/raw/olist_order_items_dataset.csv")
pay = pd.read_csv("data/raw/olist_order_payments_dataset.csv")

print("Shapes:", orders.shape, items.shape, pay.shape)

print("\n--- ORDERS ---")
print(orders.head(2))
print(orders["order_status"].value_counts())

print("\n--- ITEMS ---")
print(items.head(2))

print("\n--- PAYMENTS ---")
print(pay.head(2))
print(pay["payment_type"].value_counts())