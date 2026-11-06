import os
import pandas as pd

os.makedirs("data/clean", exist_ok=True)

orders = pd.read_csv("data/raw/olist_orders_dataset.csv")
items = pd.read_csv("data/raw/olist_order_items_dataset.csv")
pay = pd.read_csv("data/raw/olist_order_payments_dataset.csv")

# 1. Sirf delivered orders
orders = orders[orders["order_status"] == "delivered"]

# 2. Invoice amount = price + freight (order ke hisaab se)
items["amt"] = items["price"] + items["freight_value"]
inv_amt = items.groupby("order_id")["amt"].sum().round(2).rename("invoice_amount")

# 3. Gateway ka paid amount (order ke hisaab se)
paid_amt = pay.groupby("order_id")["payment_value"].sum().round(2).rename("txn_amount")
method = pay.groupby("order_id")["payment_type"].first().rename("payment_method")

# 4. Sab jodo
df = orders.set_index("order_id").join([inv_amt, paid_amt, method], how="inner")

# 5. Sirf wahi orders jahan invoice aur payment match karte hain (clean base)
df = df[(df["invoice_amount"] - df["txn_amount"]).abs() <= 1]

# 6. 10,000 random orders
df = df.sample(n=10000, random_state=42).reset_index()

# 7. invoices table
invoices = pd.DataFrame({
    "invoice_id": df["order_id"],
    "customer_id": df["customer_id"],
    "invoice_date": pd.to_datetime(df["order_purchase_timestamp"]).dt.date,
    "invoice_amount": df["invoice_amount"],
    "status": "PAID",
})

# 8. gateway_transactions table
gateway = pd.DataFrame({
    "txn_id": ["TXN" + str(i).zfill(6) for i in range(1, len(df) + 1)],
    "invoice_id": df["order_id"],
    "txn_date": pd.to_datetime(df["order_purchase_timestamp"]),
    "txn_amount": df["txn_amount"],
    "gateway_fee": (df["txn_amount"] * 0.02).round(2),
    "txn_status": "SUCCESS",
    "payment_method": df["payment_method"],
})

invoices.to_csv("data/clean/invoices_base.csv", index=False)
gateway.to_csv("data/clean/gateway_base.csv", index=False)

print("Invoices:", invoices.shape)
print("Gateway:", gateway.shape)
print(invoices.head(3))
print(gateway.head(3))