import pandas as pd
import mysql.connector

PASSWORD = "Chinuvish@1204"   # <-- wahi password

conn = mysql.connector.connect(host="localhost", port=3306, user="root",
                               password=PASSWORD, database="recon_db")
cur = conn.cursor()

cur.execute("""
SELECT l.leakage_id, l.leakage_type, l.invoice_id, l.txn_id,
       l.expected_amt, l.actual_amt, l.leakage_amt,
       i.invoice_date, g.payment_method
FROM leakage_report l
LEFT JOIN invoices i ON i.invoice_id = l.invoice_id
LEFT JOIN gateway_transactions g ON g.txn_id = l.txn_id
""")
cols = [c[0] for c in cur.description]
df = pd.DataFrame(cur.fetchall(), columns=cols)
df.to_csv("data/final/leakage_report.csv", index=False)

print("Exported:", df.shape)
print(df.head(3))
cur.close()
conn.close()