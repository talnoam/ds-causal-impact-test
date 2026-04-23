import pandas as pd

from app.database import query_df


def load_orders() -> pd.DataFrame:
    query = """
        SELECT order_id, user_id, created_at, amount, product_category, is_refund
        FROM orders
        -- Bug fix reference: app/data_processing.py load_orders() WHERE clause
        -- previously used `amount > 0`, which dropped negative refunds and
        -- converted the target from Net Revenue to Gross Revenue.
        -- Using `amount != 0` removes zero-value test orders while preserving
        -- refund transactions, restoring variance structure and business logic
        -- required for valid causal impact inference on net outcomes.
        WHERE amount != 0
    """
    df = query_df(query)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["date"] = df["created_at"].dt.date
    return df


def load_shop_metrics() -> pd.DataFrame:
    query = "SELECT * FROM shop_metrics"
    df = query_df(query)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def get_daily_revenue(orders: pd.DataFrame) -> pd.DataFrame:
    daily = orders.groupby("date").agg(
        revenue=("amount", "sum"),
        order_count=("order_id", "nunique"),
        avg_order_value=("amount", "mean"),
    ).reset_index()
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date").reset_index(drop=True)
    return daily


def build_analysis_dataframe(
    intervention_date: str,
    covariates: list[str],
) -> tuple[pd.DataFrame, str, str]:
    orders = load_orders()
    daily_revenue = get_daily_revenue(orders)

    metrics = load_shop_metrics()
    metrics["date"] = pd.to_datetime(metrics["date"])

    df = daily_revenue.merge(metrics, on="date", how="inner")

    # --- Feature Engineering: Seasonality ---
    # Statistical Rationale: E-commerce revenue exhibits strong day-of-week 
    # seasonality. Explicitly defining weekends allows the BSTS model to 
    # capture cyclical variance that isn't explained by traffic volume alone.
    df["is_weekend"] = df["date"].dt.dayofweek.isin([5, 6]).astype(int)

    intervention_dt = pd.to_datetime(intervention_date)
    pre_start = df["date"].min().strftime("%Y-%m-%d")
    pre_end = (intervention_dt - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    post_start = intervention_dt.strftime("%Y-%m-%d")
    post_end = df["date"].max().strftime("%Y-%m-%d")

    # Ensure we dynamically pull the newly engineered features if requested
    columns = ["date", "revenue"] + [c for c in covariates if c in df.columns]
    df = df[columns].set_index("date")

    pre_period = [pre_start, pre_end]
    post_period = [post_start, post_end]

    return df, pre_period, post_period


def get_data_summary() -> dict:
    orders = load_orders()
    total_orders = orders["order_id"].nunique()
    total_revenue = orders["amount"].sum()
    avg_order_value = orders["amount"].mean()

    refund_count = int(orders["is_refund"].sum())
    purchase_count = int((orders["is_refund"] == 0).sum())
    refund_rate = refund_count / purchase_count if purchase_count > 0 else 0

    date_min = orders["created_at"].min()
    date_max = orders["created_at"].max()
    n_days = (date_max - date_min).days + 1

    categories = orders.groupby("product_category")["amount"].agg(
        ["sum", "count"]
    ).to_dict(orient="index")

    daily_rev = orders.groupby("date")["amount"].sum()

    return {
        "total_orders": total_orders,
        "total_revenue": round(float(total_revenue), 2),
        "avg_order_value": round(float(avg_order_value), 2),
        "date_range": {
            "start": str(date_min.date()),
            "end": str(date_max.date()),
            "days": int(n_days),
        },
        "orders_per_day_avg": round(total_orders / n_days, 1),
        "refund_rate": round(float(refund_rate), 4),
        "categories": {
            k: {"revenue": round(v["sum"], 2), "count": int(v["count"])}
            for k, v in categories.items()
        },
        "daily_revenue_stats": {
            "mean": round(float(daily_rev.mean()), 2),
            "std": round(float(daily_rev.std()), 2),
            "min": round(float(daily_rev.min()), 2),
            "max": round(float(daily_rev.max()), 2),
        },
    }