"""
Ingestion module for RetailIQ.
Handles file reading (CSV and Excel), character encoding fallback, metadata inspection, and DuckDB staging.
"""

from io import BytesIO
from typing import Any

import duckdb
import pandas as pd


def inspect_file(
    file_source: str | BytesIO | bytes,
    filename: str,
    sample_size: int = 200,
) -> dict[str, Any]:
    """
    Inspect an uploaded file or file path and return metadata and a sample preview.
    Supports CSV and Excel (.xlsx, .xls).
    """
    ext = filename.lower().split(".")[-1]
    df_sample: pd.DataFrame | None = None
    total_rows = 0
    encoding_used = "utf-8"

    if ext in ["csv", "txt"]:
        # Try common encodings
        encodings = ["utf-8", "latin1", "iso-8859-1", "cp1252"]
        success = False
        last_err = None
        for enc in encodings:
            try:
                if isinstance(file_source, bytes):
                    bio = BytesIO(file_source)
                    df_sample = pd.read_csv(bio, nrows=sample_size, encoding=enc)
                    bio.seek(0)
                    # Approximate row count or read full for small/medium files
                    df_full = pd.read_csv(bio, encoding=enc)
                    total_rows = len(df_full)
                elif isinstance(file_source, BytesIO):
                    file_source.seek(0)
                    df_sample = pd.read_csv(file_source, nrows=sample_size, encoding=enc)
                    file_source.seek(0)
                    df_full = pd.read_csv(file_source, encoding=enc)
                    total_rows = len(df_full)
                    file_source.seek(0)
                else:
                    df_sample = pd.read_csv(file_source, nrows=sample_size, encoding=enc)
                    with open(file_source, "rb") as f:
                        total_rows = sum(1 for _ in f) - 1
                encoding_used = enc
                success = True
                break
            except Exception as e:
                last_err = e
                continue
        if not success:
            raise ValueError(f"Could not read CSV file with standard encodings: {last_err}")

    elif ext in ["xlsx", "xls"]:
        try:
            if isinstance(file_source, bytes):
                bio = BytesIO(file_source)
                df_full = pd.read_excel(bio)
            elif isinstance(file_source, BytesIO):
                file_source.seek(0)
                df_full = pd.read_excel(file_source)
                file_source.seek(0)
            else:
                df_full = pd.read_excel(file_source)
            total_rows = len(df_full)
            df_sample = df_full.head(sample_size)
        except Exception as e:
            raise ValueError(f"Could not read Excel file: {e}")
    else:
        raise ValueError(f"Unsupported file format: '.{ext}'. Supported formats are CSV and Excel (.xlsx, .xls).")

    columns = list(df_sample.columns)
    column_dtypes = {col: str(dtype) for col, dtype in df_sample.dtypes.items()}

    return {
        "filename": filename,
        "extension": ext,
        "total_rows": total_rows,
        "total_columns": len(columns),
        "columns": columns,
        "column_dtypes": column_dtypes,
        "encoding": encoding_used,
        "sample": df_sample,
    }


def load_full_dataframe(
    file_source: str | BytesIO | bytes,
    filename: str,
    encoding: str = "utf-8",
) -> pd.DataFrame:
    """
    Load the entire dataset into a pandas DataFrame.
    """
    ext = filename.lower().split(".")[-1]
    if ext in ["csv", "txt"]:
        encodings = [encoding, "latin1", "iso-8859-1", "cp1252", "utf-8"]
        for enc in encodings:
            try:
                if isinstance(file_source, bytes):
                    return pd.read_csv(BytesIO(file_source), encoding=enc)
                elif isinstance(file_source, BytesIO):
                    file_source.seek(0)
                    res = pd.read_csv(file_source, encoding=enc)
                    file_source.seek(0)
                    return res
                else:
                    return pd.read_csv(file_source, encoding=enc)
            except Exception:
                continue
        raise ValueError(f"Unable to read CSV '{filename}' with attempted encodings.")
    elif ext in ["xlsx", "xls"]:
        if isinstance(file_source, (bytes, BytesIO)):
            bio = BytesIO(file_source) if isinstance(file_source, bytes) else file_source
            bio.seek(0)
            res = pd.read_excel(bio)
            bio.seek(0)
            return res
        return pd.read_excel(file_source)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def register_duckdb_table(df: pd.DataFrame, table_name: str = "transactions", conn: duckdb.DuckDBPyConnection | None = None) -> duckdb.DuckDBPyConnection:
    """
    Registers a pandas DataFrame as a table in a DuckDB in-memory database for analytical queries.
    """
    if conn is None:
        conn = duckdb.connect(database=":memory:")
    conn.register(table_name, df)
    return conn
