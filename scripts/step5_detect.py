import pandas as pd
import mysql.connector

PASSWORD = "Chinuvish@1204"   # <-- wahi password jo step4_load.py mein daala tha

conn = mysql.connector.connect(host="localhost", port=3306, user="root",
                               password=PASSWORD, database="recon_db")
cur = conn.cursor()
cur.execute("TRUNCATE TABLE leakage_report")

COLS = "(leakage_type, invoice_id, txn_id, expected_amt, actual_amt, leakage_amt, detected_on)"

queries = {

# 1. Invoice hai, gateway mein payment nahi
"missing_payment": f"""
INSERT INTO leakage_report {COLS}
SELECT 'missing_payment', i.invoice_id, NULL, i.invoice_amount, 0, i.invoice_amount, CURDATE()
FROM invoices i
LEFT JOIN gateway_transactions g ON g.invoice_id = i.invoice_id
WHERE g.txn_id IS NULL
""",

# 2. Invoice amount aur payment amount mein 1 se zyada ka farak
"amount_mismatch": f"""
INSERT INTO leakage_report {COLS}
SELECT 'amount_mismatch', i.invoice_id, g.txn_id, i.invoice_amount, g.txn_amount,
       i.invoice_amount - g.txn_amount, CURDATE()
FROM invoices i
JOIN gateway_transactions g ON g.invoice_id = i.invoice_id
WHERE ABS(i.invoice_amount - g.txn_amount) > 1
""",

# 3. Ek invoice pe 2 ya zyada SUCCESS transactions (pehli chhodke baaki duplicate)
"duplicate_payment": f"""
INSERT INTO leakage_report {COLS}
SELECT 'duplicate_payment', x.invoice_id, x.txn_id, 0, x.txn_amount, x.txn_amount, CURDATE()
FROM (
  SELECT g.invoice_id, g.txn_id, g.txn_amount,
         ROW_NUMBER() OVER (PARTITION BY g.invoice_id ORDER BY g.txn_date, g.txn_id) AS rn
  FROM gateway_transactions g
  WHERE g.txn_status = 'SUCCESS'
) x
WHERE x.rn > 1
""",

# 4. Gateway mein success, bank mein paisa nahi aaya
"missing_settlement": f"""
INSERT INTO leakage_report {COLS}
SELECT 'missing_settlement', g.invoice_id, g.txn_id,
       g.txn_amount - g.gateway_fee, 0, g.txn_amount - g.gateway_fee, CURDATE()
FROM gateway_transactions g
LEFT JOIN bank_settlements b ON b.txn_id = g.txn_id
WHERE g.txn_status = 'SUCCESS' AND b.txn_id IS NULL
""",

# 5. Fee 2.2% se zyada kati
"fee_overcharge": f"""
INSERT INTO leakage_report {COLS}
SELECT 'fee_overcharge', g.invoice_id, g.txn_id,
       ROUND(g.txn_amount * 0.02, 2), g.gateway_fee,
       ROUND(g.gateway_fee - g.txn_amount * 0.02, 2), CURDATE()
FROM gateway_transactions g
WHERE g.gateway_fee > g.txn_amount * 0.022
  AND g.gateway_fee - g.txn_amount * 0.02 > 0.10
""",

# 6. Settlement 4 din se zyada late (T+2 hona chahiye)
"late_settlement": f"""
INSERT INTO leakage_report {COLS}
SELECT 'late_settlement', g.invoice_id, g.txn_id, 2,
       DATEDIFF(b.settlement_date, DATE(g.txn_date)), 0, CURDATE()
FROM gateway_transactions g
JOIN bank_settlements b ON b.txn_id = g.txn_id
WHERE DATEDIFF(b.settlement_date, DATE(g.txn_date)) > 4
""",

# 7. Refund original payment se zyada
"refund_excess": f"""
INSERT INTO leakage_report {COLS}
SELECT 'refund_excess', r.invoice_id, r.txn_id, g.txn_amount, r.refund_amount,
       r.refund_amount - g.txn_amount, CURDATE()
FROM refunds r
JOIN gateway_transactions g ON g.txn_id = r.txn_id
WHERE r.refund_amount > g.txn_amount
""",

# 8. Refund hai par original payment hai hi nahi
"refund_orphan": f"""
INSERT INTO leakage_report {COLS}
SELECT 'refund_orphan', r.invoice_id, r.txn_id, 0, r.refund_amount, r.refund_amount, CURDATE()
FROM refunds r
LEFT JOIN gateway_transactions g ON g.txn_id = r.txn_id
WHERE g.txn_id IS NULL
""",
}

for name, sql in queries.items():
    cur.execute(sql)
    print(f"{name}: {cur.rowcount} cases mile")
conn.commit()

# ---------- Summary ----------
print("\n--- Leakage summary ---")
cur.execute("""SELECT leakage_type, COUNT(*), ROUND(SUM(leakage_amt), 2)
               FROM leakage_report GROUP BY leakage_type ORDER BY 3 DESC""")
for t, n, amt in cur.fetchall():
    print(f"{t:20s} cases={n:4d}   amount={amt}")

# ---------- Ground truth se match ----------
cur.execute("SELECT leakage_type, invoice_id, txn_id FROM leakage_report")
det = pd.DataFrame(cur.fetchall(), columns=["leakage_type", "invoice_id", "txn_id"]).fillna("")
truth = pd.read_csv("data/final/ground_truth.csv")[["leakage_type", "invoice_id", "txn_id"]].fillna("")
det["hit"] = 1
truth["real"] = 1
m = det.merge(truth, on=["leakage_type", "invoice_id", "txn_id"], how="outer").fillna(0)

print("\n--- Detector ki accuracy ---")
print(f"{'type':20s} {'TP':>5s} {'FP':>5s} {'FN':>5s} {'precision':>10s} {'recall':>8s}")
for t, g in m.groupby("leakage_type"):
    tp = int(((g.hit == 1) & (g.real == 1)).sum())
    fp = int(((g.hit == 1) & (g.real == 0)).sum())
    fn = int(((g.hit == 0) & (g.real == 1)).sum())
    p = tp / (tp + fp) if (tp + fp) else 0
    r = tp / (tp + fn) if (tp + fn) else 0
    print(f"{t:20s} {tp:5d} {fp:5d} {fn:5d} {p:10.2%} {r:8.2%}")

cur.close()
conn.close()