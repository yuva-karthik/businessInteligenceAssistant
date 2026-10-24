import os
import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

CSV_PATH = Path(
    os.getenv("CSV_PATH", str(BASE_DIR / "data.csv"))
).resolve()

DB_PATH = Path(
    os.getenv("DB_PATH", str(BASE_DIR / "data" / "sales.db"))
).resolve()

EXPECTED_COLUMNS = [
    "Transaction_Id",
    "Order_date",
    "Product",
    "Category",
    "Region",
    "Sales_channel",
    "Quantity",
    "Unit_price",
    "Discount_amount",
    "Status",
]


def connect(db_path=None):
    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row

    return conn


def load_csv(csv_path=None, db_path=None):
    csv_path = Path(csv_path or CSV_PATH)
    db_path = Path(db_path or DB_PATH)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    missing = [
        column
        for column in EXPECTED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"CSV is missing required columns: {', '.join(missing)}"
        )

    df = df[EXPECTED_COLUMNS].copy()

    df["Order_date"] = pd.to_datetime(
        df["Order_date"],
        dayfirst=True,
        errors="coerce",
    )

    for column in [
        "Quantity",
        "Unit_price",
        "Discount_amount",
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df["Status"] = (
        df["Status"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    df["Transaction_Id"] = (
        df["Transaction_Id"]
        .astype("string")
        .str.strip()
    )

    # Keep the first occurrence of each transaction ID.
    df = df.drop_duplicates(
        subset=["Transaction_Id"],
        keep="first",
    )

    def get_exclusion_reason(row):
        if pd.isna(row["Order_date"]):
            return "Invalid or missing order date"

        if pd.isna(row["Quantity"]) or row["Quantity"] < 0:
            return "Missing or negative quantity"

        if pd.isna(row["Unit_price"]) or row["Unit_price"] < 0:
            return "Missing or negative unit price"

        if (
            pd.isna(row["Discount_amount"])
            or row["Discount_amount"] < 0
        ):
            return "Missing or negative discount"

        gross = row["Quantity"] * row["Unit_price"]

        if row["Discount_amount"] > gross:
            return "Discount exceeds gross sales"

        if row["Status"] != "completed":
            return "Status is not Completed"

        return None

    df["exclusion_reason"] = df.apply(
        get_exclusion_reason,
        axis=1,
    )

    df["included"] = df["exclusion_reason"].isna()

    df["gross_revenue"] = (
        df["Quantity"] * df["Unit_price"]
    )

    df["net_revenue"] = (
        df["gross_revenue"] - df["Discount_amount"]
    )

    df["month"] = df["Order_date"].dt.strftime("%Y-%m")

    df["Order_date"] = df["Order_date"].dt.strftime("%Y-%m-%d")

    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        df.to_sql(
            "sales",
            conn,
            if_exists="replace",
            index=False,
        )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sales_month ON sales(month)"
        )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(Product)"
        )

    return {
        "rows_loaded": len(df),
        "rows_included": int(df["included"].sum()),
        "rows_excluded": int((~df["included"]).sum()),
    }