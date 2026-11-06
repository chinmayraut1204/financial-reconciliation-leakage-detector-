# Financial Reconciliation & Leakage Detector

An end-to-end data analytics project that matches invoices, payment gateway transactions and bank settlements to detect revenue leakage automatically.

## Problem
Businesses that accept online payments must match three records: what was billed (invoice), what the customer paid (gateway transaction) and what reached the bank (settlement). Mismatches cause silent revenue loss, and manual checking is slow and error-prone.

## Approach
Olist raw data -> build invoices, gateway transactions, bank settlements and refunds -> inject controlled leakage with a ground-truth file -> load into MySQL -> detect mismatches -> export leakage report -> Power BI dashboard

Because leakage is injected with a known `ground_truth.csv`, detection accuracy can be measured instead of guessed.

## Leakage Types Detected
1. Missing payment - invoice exists, no gateway transaction
2. Amount mismatch - invoice amount differs from amount paid
3. Duplicate - same payment charged or recorded twice
4. Missing settlement - payment captured but never reached the bank
5. Refund leakage - refund issued incorrectly or in excess
6. Fee overcharge - gateway fee above the agreed rate
7. Late settlement - settlement delayed beyond the expected window

## Tech Stack
- Python (Pandas) for data preparation and leakage injection
- MySQL 8.0 for the database
- Power BI for the dashboard (in progress)
- Dataset: Olist Brazilian E-Commerce (real orders and payments) plus injected synthetic leakage

## Data Scale
| Table | Records |
|---|---|
| Invoices | 10,000 |
| Gateway transactions | 9,950 |
| Bank settlements | 9,800 |
| Refunds | 350 |
| Injected leakage cases | 850 |

## Project Structure
- `data/raw/` - Olist source files
- `data/clean/` - cleaned base tables
- `data/final/` - final tables, `ground_truth.csv` and `leakage_report.csv`
- `scripts/step2_base.py` - build base invoice and gateway data
- `scripts/step3_inject.py` - inject 850 leakage cases with ground truth
- `scripts/step4_load.py` - load tables into MySQL (`recon_db`)
- `scripts/step5_detect.py` - detect leakage
- `scripts/step6_export.py` - export leakage report

## Project Status
- [x] Base data preparation (Olist)
- [x] Leakage injection with ground truth
- [x] MySQL schema and data load
- [x] Leakage detection and report export
- [ ] Accuracy validation against ground truth
- [ ] Power BI dashboard

## How to Run
1. Install requirements and set MySQL credentials in a `.env` file
2. Run the scripts in `scripts/` in order: step2, step3, step4, step5, step6

## Author
Chinmay Rajesh Raut | [GitHub](https://github.com/chinmayraut1204)
