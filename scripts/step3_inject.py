import os
import numpy as np
import pandas as pd

os.makedirs("data/final", exist_ok=True)
rng = np.random.default_rng(42)

inv = pd.read_csv("data/clean/invoices_base.csv")
gw = pd.read_csv("data/clean/gateway_base.csv", parse_dates=["txn_date"])

# ---------- A. Clean bank settlements (T+2 din) ----------
bank = pd.DataFrame({
    "settlement_id": ["STL" + str(i).zfill(6) for i in range(1, len(gw) + 1)],
    "txn_id": gw["txn_id"],
    "settlement_date": gw["txn_date"].dt.normalize() + pd.Timedelta(days=2),
    "settled_amount": (gw["txn_amount"] - gw["gateway_fee"]).round(2),
})

# ---------- B. Clean refunds (300) ----------
ref_idx = rng.choice(gw.index, size=300, replace=False)
refunds = pd.DataFrame({
    "refund_id": ["RFD" + str(i).zfill(5) for i in range(1, 301)],
    "txn_id": gw.loc[ref_idx, "txn_id"].values,
    "invoice_id": gw.loc[ref_idx, "invoice_id"].values,
    "refund_date": gw.loc[ref_idx, "txn_date"].dt.normalize().values
                   + pd.to_timedelta(rng.integers(3, 16, 300), unit="D").values,
    "refund_amount": (gw.loc[ref_idx, "txn_amount"].values
                      * rng.uniform(0.2, 1.0, 300)).round(2),
})

# ---------- C. Galtiyan ke liye rows chunna ----------
ref_set = set(ref_idx.tolist())
pool = [i for i in rng.permutation(gw.index).tolist()
        if i not in ref_set and gw.at[i, "txn_amount"] >= 30]

plan = [("missing_payment", 150), ("amount_mismatch", 150),
        ("duplicate_payment", 100), ("missing_settlement", 150),
        ("fee_overcharge", 100), ("late_settlement", 100)]
groups, pos = {}, 0
for name, n in plan:
    groups[name] = pool[pos:pos + n]
    pos += n

truth = []   # (type, invoice_id, txn_id, refund_id, leakage_amt)
drop_gw, drop_bank = [], []
txn_amt = gw.set_index("txn_id")["txn_amount"].copy()

# 1. missing_payment: invoice hai, gateway mein payment nahi
for i in groups["missing_payment"]:
    truth.append(("missing_payment", gw.at[i, "invoice_id"], None, None,
                  float(gw.at[i, "txn_amount"])))
    drop_gw.append(i)
    drop_bank.append(i)

# 2. amount_mismatch: gateway ne kam paisa liya
for i in groups["amount_mismatch"]:
    old = float(gw.at[i, "txn_amount"])
    new = round(old * rng.uniform(0.80, 0.95), 2)
    fee = round(new * 0.02, 2)
    gw.at[i, "txn_amount"] = new
    gw.at[i, "gateway_fee"] = fee
    bank.at[i, "settled_amount"] = round(new - fee, 2)
    truth.append(("amount_mismatch", gw.at[i, "invoice_id"], gw.at[i, "txn_id"],
                  None, round(old - new, 2)))

# 3. duplicate_payment: same invoice pe 2 baar paisa kata
dups = gw.loc[groups["duplicate_payment"]].copy()
dups["txn_id"] = ["TXN" + str(10000 + k).zfill(6) for k in range(1, len(dups) + 1)]
dups["txn_date"] = dups["txn_date"].values + pd.to_timedelta(
    rng.integers(1, 30, len(dups)), unit="m").values
dup_bank = pd.DataFrame({
    "settlement_id": ["STL" + str(10000 + k).zfill(6) for k in range(1, len(dups) + 1)],
    "txn_id": dups["txn_id"].values,
    "settlement_date": dups["txn_date"].dt.normalize().values + np.timedelta64(2, "D"),
    "settled_amount": (dups["txn_amount"] - dups["gateway_fee"]).round(2).values,
})
for _, r in dups.iterrows():
    truth.append(("duplicate_payment", r["invoice_id"], r["txn_id"], None,
                  float(r["txn_amount"])))

# 4. missing_settlement: gateway mein success, bank mein paisa nahi aaya
for i in groups["missing_settlement"]:
    truth.append(("missing_settlement", gw.at[i, "invoice_id"], gw.at[i, "txn_id"],
                  None, float(bank.at[i, "settled_amount"])))
    drop_bank.append(i)

# 5. fee_overcharge: 2% ki jagah 3-4% fee
for i in groups["fee_overcharge"]:
    amt = float(gw.at[i, "txn_amount"])
    fee = round(amt * rng.uniform(0.03, 0.04), 2)
    gw.at[i, "gateway_fee"] = fee
    bank.at[i, "settled_amount"] = round(amt - fee, 2)
    truth.append(("fee_overcharge", gw.at[i, "invoice_id"], gw.at[i, "txn_id"],
                  None, round(fee - amt * 0.02, 2)))

# 6. late_settlement: T+2 ki jagah 7 se 17 din baad
for i in groups["late_settlement"]:
    extra = int(rng.integers(5, 16))
    bank.at[i, "settlement_date"] = bank.at[i, "settlement_date"] + pd.Timedelta(days=extra)
    truth.append(("late_settlement", gw.at[i, "invoice_id"], gw.at[i, "txn_id"],
                  None, 0.0))

# 7. refund_excess: refund > original payment (50)
for j in range(50):
    amt = float(txn_amt[refunds.at[j, "txn_id"]])
    new = round(amt * rng.uniform(1.1, 1.5), 2)
    refunds.at[j, "refund_amount"] = new
    truth.append(("refund_excess", refunds.at[j, "invoice_id"],
                  refunds.at[j, "txn_id"], refunds.at[j, "refund_id"],
                  round(new - amt, 2)))

# 8. refund_orphan: refund hai par original payment hi nahi (50)
orph = pd.DataFrame({
    "refund_id": ["RFD" + str(i).zfill(5) for i in range(301, 351)],
    "txn_id": ["TXN9" + str(i).zfill(5) for i in range(1, 51)],
    "invoice_id": rng.choice(inv["invoice_id"], 50, replace=False),
    "refund_date": (pd.Timestamp("2018-01-01")
                    + pd.to_timedelta(rng.integers(0, 300, 50), unit="D")),
    "refund_amount": rng.uniform(20, 500, 50).round(2),
})
for _, r in orph.iterrows():
    truth.append(("refund_orphan", r["invoice_id"], r["txn_id"], r["refund_id"],
                  float(r["refund_amount"])))

# ---------- D. Final tables ----------
gw = gw.drop(index=drop_gw)
bank = bank.drop(index=drop_bank)
gw = pd.concat([gw, dups], ignore_index=True)
bank = pd.concat([bank, dup_bank], ignore_index=True)
refunds = pd.concat([refunds, orph], ignore_index=True)

bank["settlement_date"] = pd.to_datetime(bank["settlement_date"]).dt.date
refunds["refund_date"] = pd.to_datetime(refunds["refund_date"]).dt.date

truth_df = pd.DataFrame(truth, columns=["leakage_type", "invoice_id", "txn_id",
                                        "refund_id", "leakage_amt"])

inv.to_csv("data/final/invoices.csv", index=False)
gw.to_csv("data/final/gateway_transactions.csv", index=False)
bank.to_csv("data/final/bank_settlements.csv", index=False)
refunds.to_csv("data/final/refunds.csv", index=False)
truth_df.to_csv("data/final/ground_truth.csv", index=False)

print("invoices:", inv.shape)
print("gateway:", gw.shape)
print("bank:", bank.shape)
print("refunds:", refunds.shape)
print("\nGround truth (injected leakage):")
print(truth_df["leakage_type"].value_counts())
print("Total:", len(truth_df))