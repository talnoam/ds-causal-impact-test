import pandas as pd
import numpy as np
from scipy import stats
from app.data_processing import load_orders, load_shop_metrics, get_daily_revenue

def run_diagnostics(intervention_date: str = "2024-10-27"):
    """
    Runs statistical diagnostics on all potential covariates to determine 
    if they are valid for the CausalImpact model or suffer from endogeneity.
    """
    print(f"Running Covariate Diagnostics for Intervention Date: {intervention_date}\n")
    print("-" * 80)
    
    # 1. Load and merge all data
    orders = load_orders()
    daily_revenue = get_daily_revenue(orders)
    metrics = load_shop_metrics()
    metrics["date"] = pd.to_datetime(metrics["date"])
    
    df = daily_revenue.merge(metrics, on="date", how="inner")
    
    # Add our engineered feature
    df["is_weekend"] = df["date"].dt.dayofweek.isin([5, 6]).astype(int)
    
    # Define periods
    intervention_dt = pd.to_datetime(intervention_date)
    df["is_post_intervention"] = (df["date"] >= intervention_dt).astype(int)
    
    pre_df = df[df["is_post_intervention"] == 0]
    post_df = df[df["is_post_intervention"] == 1]
    
    # Define candidates to test
    candidates = [
        "organic_sessions", 
        "paid_sessions", 
        "email_campaigns_sent", 
        "avg_discount_pct", 
        "returning_customer_pct", 
        "site_conversion_rate",
        "is_weekend"
    ]
    
    results = []
    
    for col in candidates:
        if col not in df.columns:
            continue
            
        # Metric 1: Pre-period Correlation with Revenue (Predictive Power)
        # We want this to be reasonably high (absolute value > 0.1) so it helps the baseline.
        corr_with_revenue = pre_df[col].corr(pre_df["revenue"])
        
        # Metric 2: Post-Intervention Shift (Endogeneity Test)
        # Did the covariate itself jump significantly after the campaign started?
        pre_mean = pre_df[col].mean()
        post_mean = post_df[col].mean()
        
        # Avoid division by zero
        if pre_mean == 0:
            shift_pct = float('inf') if post_mean > 0 else 0.0
        else:
            shift_pct = ((post_mean - pre_mean) / pre_mean) * 100
            
        # Metric 3: Statistical Significance of the Shift (t-test)
        # If p-value < 0.05, the variable was significantly altered post-intervention -> BAD for BSTS.
        t_stat, p_val = stats.ttest_ind(pre_df[col], post_df[col], equal_var=False)
        
        # Decision Logic based on Causal Inference Rules
        is_endogenous = p_val < 0.05 and abs(shift_pct) > 15.0 # Significant shift > 15%
        
        recommendation = "EXCLUDE (Endogenous)" if is_endogenous else "INCLUDE (Valid Proxy)"
        # Special rule for email_campaigns_sent which is the treatment itself
        if col == "email_campaigns_sent":
            recommendation = "EXCLUDE (The Treatment)"
            
        results.append({
            "Covariate": col,
            "Pre-Revenue Corr": f"{corr_with_revenue:.2f}",
            "Pre Mean": f"{pre_mean:.2f}",
            "Post Mean": f"{post_mean:.2f}",
            "Shift %": f"{shift_pct:+.1f}%",
            "Shift P-Value": f"{p_val:.4f}",
            "Recommendation": recommendation
        })
        
    # Format and print the results as a neat table
    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))
    print("-" * 80)
    print("\nCONCLUSION:")
    print("* Covariates with a significant 'Shift P-Value' (<0.05) and large 'Shift %' are contaminated.")
    print("  They absorbed the treatment effect and will cause Covariate Leakage if included.")
    print("* Covariates with stable means (high p-value) and good 'Pre-Revenue Corr' are excellent synthetic controls.")

if __name__ == "__main__":
    run_diagnostics()