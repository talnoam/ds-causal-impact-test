from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    version: str


class DataSummary(BaseModel):
    total_orders: int
    total_revenue: float
    avg_order_value: float
    date_range: dict
    orders_per_day_avg: float
    refund_rate: float
    categories: dict
    daily_revenue_stats: dict


class AnalyzeRequest(BaseModel):
    intervention_date: str = Field(
        ...,
        description="Start date of the campaign (YYYY-MM-DD)",
        examples=["2024-10-27"],
    )
    covariates: Optional[list[str]] = Field(
        default=None,
        description="List of shop metric columns to use as covariates. If omitted, uses defaults.",
    )
    alpha: float = Field(
        default=0.05,
        description="Significance level for the causal impact test",
        ge=0.01,
        le=0.2,
    )


class AnalyzeResponse(BaseModel):
    analysis_id: str
    status: str
    message: str


class CausalImpactSummary(BaseModel):
    average_effect: Optional[float] = None
    cumulative_effect: Optional[float] = None
    average_effect_pct: Optional[float] = None
    p_value: Optional[float] = None
    significant: Optional[bool] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None


class AnalysisResult(BaseModel):
    analysis_id: str
    intervention_date: str
    covariates_used: list[str]
    alpha: float
    pre_period_days: int
    post_period_days: int
    summary: CausalImpactSummary
    report: str
