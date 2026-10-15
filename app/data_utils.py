"""Data loading and cleaning for the Retail Sales dashboard.

Same cleaning rules as the notebook (Section 7), packaged as functions so the
Streamlit app can rebuild the cleaned data from the raw file or from an upload.
"""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_PATH = PROJECT_DIR / "data" / "original_dataset.csv"

REQUIRED = ["Order Date", "Category", "Sales", "Quantity", "Discount", "Profit"]

COLUMN_ALIASES = {
    "orderid": "Order ID", "orderdate": "Order Date", "shipdate": "Ship Date",
    "shipmode": "Ship Mode", "customerid": "Customer ID", "customername": "Customer Name",
    "segment": "Segment", "customersegment": "Segment", "region": "Region",
    "productid": "Product ID", "productname": "Product Name",
    "category": "Category", "productcategory": "Category",
    "subcategory": "Sub-Category", "productsubcategory": "Sub-Category",
    "sales": "Sales", "profit": "Profit", "discount": "Discount",
    "quantity": "Quantity", "qty": "Quantity", "orderquantity": "Quantity",
}

# All month-first (US style); the Superstore file mixes '4/15/2017' and '11-08-2016'
DATE_FORMATS = ["%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%m/%d/%y"]


def read_raw(source: str | Path | bytes) -> pd.DataFrame:
    """Read a CSV (trying common encodings) or Excel file from a path or raw bytes."""
    name = str(source).lower() if not isinstance(source, bytes) else ""
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(source)
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            if isinstance(source, bytes):
                return pd.read_csv(io.BytesIO(source), encoding=encoding)
            return pd.read_csv(source, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not decode the CSV file.")


def _normalize_key(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def _parse_dates(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    text = series.astype("string").str.strip()
    result = None
    for fmt in DATE_FORMATS:
        attempt = pd.to_datetime(text, format=fmt, errors="coerce")
        result = attempt if result is None else result.fillna(attempt)
    return result


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Return the cleaned DataFrame and a list of plain-English cleaning notes."""
    df = raw.copy()
    df.columns = df.columns.str.strip()
    notes: list[str] = []

    rename = {}
    for col in df.columns:
        standard = COLUMN_ALIASES.get(_normalize_key(col))
        if standard and standard != col and standard not in df.columns:
            rename[col] = standard
    df = df.rename(columns=rename)

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Required columns missing: {missing}")

    for col in ["Ship Mode", "Segment", "Region", "Category", "Sub-Category",
                "Product Name", "Customer Name"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    if "Sub-Category" in df.columns:
        usual = df.groupby("Sub-Category")["Category"].agg(lambda s: s.mode().iloc[0])
        expected = df["Sub-Category"].map(usual)
        wrong = df["Category"].notna() & expected.notna() & (df["Category"] != expected)
        if wrong.any():
            df.loc[wrong, "Category"] = expected[wrong]
            notes.append(f"Fixed {int(wrong.sum())} inconsistent Category label(s) using Sub-Category")

    dash_dates = 0
    if not pd.api.types.is_datetime64_any_dtype(df["Order Date"]):
        dash_dates = int(df["Order Date"].astype("string").str.contains("-").sum())
    df["Order Date"] = _parse_dates(df["Order Date"])
    if "Ship Date" in df.columns:
        df["Ship Date"] = _parse_dates(df["Ship Date"])
        df["Ship Days"] = (df["Ship Date"] - df["Order Date"]).dt.days
    if dash_dates:
        check = ""
        if "Ship Days" in df.columns:
            early = int((df["Ship Days"] < 0).sum())
            check = (" - verified: no order ships before it is placed" if early == 0
                     else f" - warning: {early} orders ship before their order date, check the date format")
        notes.append(f"Parsed {dash_dates:,} order dates written like '11-08-2016' as month-first{check}")

    for col in ["Sales", "Quantity", "Discount", "Profit"]:
        if not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = pd.to_numeric(df[col].astype("string").str.replace(r"[$,%\s]", "", regex=True),
                                    errors="coerce")
        df[col] = df[col].replace([np.inf, -np.inf], np.nan)
    if df["Discount"].max() > 1:
        df["Discount"] = df["Discount"] / 100
        notes.append("Converted Discount from percent to fraction")

    dups = int(df.duplicated().sum())
    df = df.drop_duplicates()
    if dups:
        notes.append(f"Removed {dups} exact duplicate row(s)")

    bad = df[REQUIRED].isna().any(axis=1)
    if bad.any():
        notes.append(f"Dropped {int(bad.sum())} row(s) missing essential values")
    df = df.loc[~bad].copy()
    if df.empty:
        raise ValueError("No usable rows after cleaning.")

    df["Year"] = df["Order Date"].dt.year
    df["Month"] = df["Order Date"].dt.month
    df["Year-Month"] = df["Order Date"].dt.to_period("M").dt.to_timestamp()
    df["Profit Margin (%)"] = np.where(df["Sales"] != 0, df["Profit"] / df["Sales"] * 100, np.nan)
    df["Is Loss"] = df["Profit"] < 0
    df["Discount Band"] = pd.cut(df["Discount"], bins=[-0.001, 0, 0.2, 0.4, 1.0],
                                 labels=["0%", "1-20%", "21-40%", "Above 40%"])
    notes.append(f"{len(df):,} clean rows, orders from {df['Order Date'].min():%d %b %Y} "
                 f"to {df['Order Date'].max():%d %b %Y}")
    return df, notes


def discount_cap_whatif(df: pd.DataFrame, cap: float) -> pd.DataFrame:
    """Re-price every transaction whose discount is above `cap` down to `cap`.

    Superstore records Sales after discount. Cost is recovered as Sales - Profit,
    list price as Sales / (1 - discount). The scenario keeps quantity the same,
    which is an assumption: in reality fewer customers might buy at a higher price.
    """
    out = df[["Sales", "Profit", "Discount"]].copy()
    affected = (out["Discount"] > cap) & (out["Discount"] < 1)
    cost = out["Sales"] - out["Profit"]
    list_price_total = out["Sales"] / (1 - out["Discount"].where(out["Discount"] < 1, 0))
    new_sales = np.where(affected, list_price_total * (1 - cap), out["Sales"])
    out["New Sales"] = new_sales
    out["New Profit"] = new_sales - cost
    out["Affected"] = affected
    return out
