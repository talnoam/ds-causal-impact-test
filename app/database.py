import os
import sqlite3

import pandas as pd

DATABASE_PATH = os.environ.get("DATABASE_PATH", "data/shop.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    conn = get_connection()
    try:
        df = pd.read_sql_query(sql, conn, params=params)
        return df
    finally:
        conn.close()
