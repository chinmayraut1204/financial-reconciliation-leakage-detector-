import pandas as pd
import mysql.connector

PASSWORD = "Chinuvish@1204"   # <-- yahan apna MySQL password likho

conn = mysql.connector.connect(host="localhost", port=3306,
                               user="root", password=PASSWORD)
cur = conn.cursor()

cur.execute("CREATE DATABASE IF NOT EXISTS recon_db")
cur.execute("USE recon_db")

# Dobara chalane par purani tables hat jayengi
for t in ["leakage_report", "refunds", "bank_settlements",
          "gateway_transactions", "invoices"]:
    cur.execute(f"DROP TABLE IF EXISTS {t}")

cur.execute("""
CREATE TABLE invoices (
  invoice_id      VARCHAR(40) PRIMARY KEY,
  customer_id     VARCHAR(40) NOT NULL,
  invoice_date    DATE NOT NULL,
  invoice_amount  DECIMAL(12,2) NOT NULL,
  status          VARCHAR(20) NOT NULL
)""")

cur.execute("""
CREATE TABLE gateway_transactions (
  txn_id          VARCHAR(30) PRIMARY KEY,
  invoice_id      VARCHAR(40),
  txn_date        DATETIME NOT NULL,
  txn_amount      DECIMAL(12,2) NOT NULL,
  gateway_fee     DECIMAL(10,2) NOT NULL,
  txn_status      VARCHAR(20) NOT NULL,
  payment_method  VARCHAR(20),
  INDEX idx_gw_invoice (invoice_id)
)""")

cur.execute("""
CREATE TABLE bank_settlements (
  settlement_id    VARCHAR(30) PRIMARY KEY,
  txn_id           VARCHAR(30),
  settlement_date  DATE NOT NULL,
  settled_amount   DECIMAL(12,2) NOT NULL,
  INDEX idx_bank_txn (txn_id)
)""")

cur.execute("""
CREATE TABLE refunds (
  refund_id      VARCHAR(30) PRIMARY KEY,
  txn_id         VARCHAR(30),
  invoice_id     VARCHAR(40),
  refund_date    DATE NOT NULL,
  refund_amount  DECIMAL(12,2) NOT NULL
)""")

cur.execute("""
CREATE TABLE leakage_report (
  leakage_id     INT AUTO_INCREMENT PRIMARY KEY,
  leakage_type   VARCHAR(40) NOT NULL,
  invoice_id     VARCHAR(40),
  txn_id         VARCHAR(30),
  expected_amt   DECIMAL(12,2),
  actual_amt     DECIMAL(12,2),
  leakage_amt    DECIMAL(12,2),
  detected_on    DATE
)""")
conn.commit()
print("Tables ban gayi")

def load(table, csv_path, cols):
    df = pd.read_csv(csv_path)[cols].astype(object)
    df = df.where(df.notna(), None)
    rows = [tuple(r) for r in df.itertuples(index=False, name=None)]
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(['%s'] * len(cols))})"
    for i in range(0, len(rows), 2000):
        cur.executemany(sql, rows[i:i + 2000])
    conn.commit()
    print(f"{table}: {len(rows)} rows load hui")

load("invoices", "data/final/invoices.csv",
     ["invoice_id", "customer_id", "invoice_date", "invoice_amount", "status"])
load("gateway_transactions", "data/final/gateway_transactions.csv",
     ["txn_id", "invoice_id", "txn_date", "txn_amount", "gateway_fee",
      "txn_status", "payment_method"])
load("bank_settlements", "data/final/bank_settlements.csv",
     ["settlement_id", "txn_id", "settlement_date", "settled_amount"])
load("refunds", "data/final/refunds.csv",
     ["refund_id", "txn_id", "invoice_id", "refund_date", "refund_amount"])

cur.close()
conn.close()
print("Sab ho gaya!")