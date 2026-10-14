"""
Benchmark data generator script for RetailIQ.
Creates a high-fidelity synthetic benchmark dataset modeled on the UCI Online Retail structure.
Covers 18 months of history with realistic repeat customer patterns, cancellations,
guest checkouts, and varied product portfolios for robust testing and demoing.
"""

import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Fix seed for reproducibility
np.random.seed(42)
random.seed(42)

PRODUCTS = [
    ("85123A", "WHITE HANGING HEART T-LIGHT HOLDER", 2.55),
    ("71053", "WHITE METAL LANTERN", 3.39),
    ("84406B", "CREAM CUPID HEARTS COAT HANGER", 2.75),
    ("84029G", "KNITTED UNION FLAG HOT WATER BOTTLE", 3.39),
    ("84029E", "RED WOOLLY HOTTIE WHITE HEART.", 3.39),
    ("22752", "SET 7 BABUSHKA NESTING BOXES", 7.65),
    ("21730", "GLASS STAR FROSTED T-LIGHT HOLDER", 4.25),
    ("22633", "HAND WARMER UNION JACK", 1.85),
    ("22632", "HAND WARMER RED POLKADOT", 1.85),
    ("84879", "ASSORTED COLOUR BIRD ORNAMENT", 1.69),
    ("22745", "POPPY'S PLAYHOUSE BEDROOM", 2.10),
    ("22748", "POPPY'S PLAYHOUSE KITCHEN", 2.10),
    ("22749", "FELTCRAFT PRINCESS CHARLOTTE DOLL", 3.75),
    ("22310", "IVORY KNITTED MUG COSY", 1.65),
    ("84969", "BOX OF 6 ASSORTED NOTELET & ENVELOPES", 2.55),
    ("20725", "LUNCH BAG RED RETROSPOT", 1.65),
    ("20727", "LUNCH BAG BLACK SKULL.", 1.65),
    ("20728", "LUNCH BAG CARS BLUE", 1.65),
    ("22382", "LUNCH BAG SPACEBOY DESIGN", 1.65),
    ("22383", "LUNCH BAG SUKI DESIGN", 1.65),
    ("22384", "LUNCH BAG PINK POLKADOT", 1.65),
    ("20726", "LUNCH BAG WOODLAND", 1.65),
    ("22386", "JUMBO BAG PINK POLKADOT", 1.95),
    ("85099B", "JUMBO BAG RED RETROSPOT", 1.95),
    ("21931", "JUMBO STORAGE BAG SUKI", 1.95),
    ("85099F", "JUMBO BAG STRAWBERRY", 1.95),
    ("22411", "JUMBO SHOPPER VINTAGE RED PAISLEY", 1.95),
    ("20719", "WOODLAND CHARLOTTE BAG", 0.85),
    ("20712", "JUMBO BAG WOODLAND CHARLOTTE", 1.95),
    ("22385", "JUMBO BAG VINTAGE ALPHABET", 1.95),
]

COUNTRIES = [
    ("United Kingdom", 0.88),
    ("Germany", 0.04),
    ("France", 0.03),
    ("EIRE", 0.02),
    ("Spain", 0.01),
    ("Netherlands", 0.01),
    ("Belgium", 0.005),
    ("Switzerland", 0.005),
]


def generate_benchmark_dataset(
    n_customers: int = 400,
    start_date: datetime = datetime(2023, 1, 1),
    total_days: int = 540,  # ~18 months
    output_csv: str = "data/raw/online_retail_sample.csv",
    output_xlsx: str = "data/raw/online_retail_sample.xlsx",
) -> pd.DataFrame:
    """
    Generates a realistic transaction log with customer lifecycles.
    """
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    records = []
    invoice_seq = 536365

    # Assign customer cohorts and behaviors
    customers = []
    for cid in range(12000, 12000 + n_customers):
        # Customer first acquisition day
        acq_day = np.random.randint(0, int(total_days * 0.65))
        # Lifetime duration (some churn early, some stay long)
        is_churner = np.random.rand() < 0.45
        if is_churner:
            active_span = np.random.randint(15, 120)
        else:
            active_span = np.random.randint(180, total_days - acq_day + 1)

        # Average inter-purchase interval in days
        order_frequency_days = np.random.choice([10, 20, 35, 60, 90], p=[0.10, 0.25, 0.35, 0.20, 0.10])
        # Spend multiplier
        spend_tier = np.random.choice([0.5, 1.0, 2.5, 5.0], p=[0.30, 0.50, 0.15, 0.05])
        # Customer country
        country_names = [c[0] for c in COUNTRIES]
        country_probs = [c[1] for c in COUNTRIES]
        country = np.random.choice(country_names, p=country_probs)

        customers.append({
            "customer_id": cid,
            "acq_day": acq_day,
            "end_day": min(total_days, acq_day + active_span),
            "freq_days": order_frequency_days,
            "spend_tier": spend_tier,
            "country": country,
        })

    # Generate customer transactions
    for cust in customers:
        curr_day = cust["acq_day"] + np.random.randint(0, 5)
        while curr_day < cust["end_day"]:
            inv_no = str(invoice_seq)
            invoice_seq += 1

            # Transaction timestamp
            order_time = start_date + timedelta(
                days=int(curr_day),
                hours=random.randint(8, 19),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59),
            )

            # Basket size: 1 to 10 items
            n_items = np.random.choice([1, 2, 3, 5, 8], p=[0.25, 0.35, 0.20, 0.15, 0.05])
            chosen_prods = random.sample(PRODUCTS, min(n_items, len(PRODUCTS)))

            for sku, desc, base_price in chosen_prods:
                qty = int(max(1, round(np.random.exponential(scale=6) * cust["spend_tier"])))
                # slight price variation
                unit_price = round(base_price * (1.0 + np.random.uniform(-0.05, 0.05)), 2)

                records.append({
                    "InvoiceNo": inv_no,
                    "StockCode": sku,
                    "Description": desc,
                    "Quantity": qty,
                    "InvoiceDate": order_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "UnitPrice": unit_price,
                    "CustomerID": cust["customer_id"],
                    "Country": cust["country"],
                })

            # Random return (cancellation) probability for this order ~5%
            if random.random() < 0.05 and records:
                cancel_inv = f"C{inv_no}"
                cancel_time = order_time + timedelta(days=random.randint(1, 5), hours=random.randint(1, 8))
                ret_prod = random.choice(chosen_prods)
                records.append({
                    "InvoiceNo": cancel_inv,
                    "StockCode": ret_prod[0],
                    "Description": f"Manual Return: {ret_prod[1]}",
                    "Quantity": -random.randint(1, 3),
                    "InvoiceDate": cancel_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "UnitPrice": ret_prod[2],
                    "CustomerID": cust["customer_id"],
                    "Country": cust["country"],
                })

            # Advance to next order date
            curr_day += int(np.random.exponential(scale=cust["freq_days"]) + 3)

    # Add guest checkouts (unregistered walk-in customers: ~15% of total transactions)
    n_guest_orders = int(len(records) * 0.15 / 3)
    for _ in range(n_guest_orders):
        inv_no = str(invoice_seq)
        invoice_seq += 1
        guest_day = random.randint(0, total_days - 1)
        guest_time = start_date + timedelta(
            days=guest_day,
            hours=random.randint(9, 20),
            minutes=random.randint(0, 59),
        )
        chosen_prods = random.sample(PRODUCTS, random.randint(1, 4))
        for sku, desc, base_price in chosen_prods:
            qty = random.randint(1, 6)
            records.append({
                "InvoiceNo": inv_no,
                "StockCode": sku,
                "Description": desc,
                "Quantity": qty,
                "InvoiceDate": guest_time.strftime("%Y-%m-%d %H:%M:%S"),
                "UnitPrice": base_price,
                "CustomerID": np.nan,  # Guest checkout
                "Country": "United Kingdom",
            })

    # Add small edge cases for data quality validation:
    # 1. A few duplicate rows
    if len(records) > 10:
        records.append(records[5].copy())
        records.append(records[12].copy())

    # 2. A few zero-price promotion items
    records.append({
        "InvoiceNo": str(invoice_seq),
        "StockCode": "GIFT01",
        "Description": "FREE GIFT SAMPLE PROMOTION",
        "Quantity": 1,
        "InvoiceDate": (start_date + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"),
        "UnitPrice": 0.0,
        "CustomerID": 12050,
        "Country": "United Kingdom",
    })

    df = pd.DataFrame(records)
    # Sort chronologically
    df["dt_sort"] = pd.to_datetime(df["InvoiceDate"])
    df = df.sort_values(by="dt_sort").drop(columns=["dt_sort"]).reset_index(drop=True)

    # Save CSV
    df.to_csv(output_csv, index=False)
    print(f"Generated benchmark dataset saved to CSV: {output_csv} ({len(df)} rows)")

    # Save Excel (top 5000 rows if larger, to keep Excel file agile)
    excel_slice = df.head(6000)
    excel_slice.to_excel(output_xlsx, index=False)
    print(f"Generated benchmark dataset sample saved to Excel: {output_xlsx} ({len(excel_slice)} rows)")

    return df


if __name__ == "__main__":
    generate_benchmark_dataset()
