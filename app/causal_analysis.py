import io
import re
import uuid
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from causalimpact import CausalImpact
import numpy as np

from app.data_processing import build_analysis_dataframe

# Bug fix reference: app/causal_analysis.py DEFAULT_COVARIATES previously included
# `email_campaigns_sent` and `avg_discount_pct`, both campaign-linked variables
# affected by treatment intensity and timing.
# Including treatment-affected covariates leaks intervention signal into the
# synthetic-control baseline (post-treatment endogeneity), attenuating the
# estimated effect toward zero and increasing false negatives.
# We keep only `organic_sessions`, which is an exogenous demand proxy that is
# not directly manipulated by the email campaign and improves baseline fit by
# capturing non-campaign traffic trend.
DEFAULT_COVARIATES = ["organic_sessions"]
RANDOM_SEED = 42

_results_store: dict[str, dict] = {}


def run_analysis(
    intervention_date: str,
    covariates: Optional[list[str]] = None,
    alpha: float = 0.05,
) -> str:
    if covariates is None:
        covariates = DEFAULT_COVARIATES

    np.random.seed(RANDOM_SEED)
    df, pre_period, post_period = build_analysis_dataframe(
        intervention_date, covariates
    )

    ci = CausalImpact(df, pre_period, post_period, alpha=alpha)

    analysis_id = str(uuid.uuid4())[:8]

    summary_data = _parse_summary(ci.summary())
    report_text = ci.summary(output="report")

    _results_store[analysis_id] = {
        "analysis_id": analysis_id,
        "intervention_date": intervention_date,
        "covariates_used": covariates,
        "alpha": alpha,
        "pre_period_days": len(df.loc[:pre_period[1]]),
        "post_period_days": len(df.loc[post_period[0]:]),
        "summary": summary_data,
        "report": report_text,
        "ci_object": ci,
    }

    return analysis_id


def get_result(analysis_id: str) -> Optional[dict]:
    result = _results_store.get(analysis_id)
    if result is None:
        return None
    return {k: v for k, v in result.items() if k != "ci_object"}


def get_plot(analysis_id: str) -> Optional[bytes]:
    result = _results_store.get(analysis_id)
    if result is None:
        return None

    ci = result["ci_object"]
    fig = ci.plot()

    buf = io.BytesIO()
    if fig is not None:
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    else:
        current_fig = plt.gcf()
        current_fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close("all")

    buf.seek(0)
    return buf.read()


def _parse_summary(summary_text: str) -> dict:
    result = {
        "average_effect": None,
        "cumulative_effect": None,
        "average_effect_pct": None,
        "p_value": None,
        "significant": None,
        "ci_lower": None,
        "ci_upper": None,
    }

    lines = summary_text.strip().split("\n")

    in_absolute_effect = False
    for line in lines:
        lower = line.lower()
        if "absolute effect" in lower:
            in_absolute_effect = True
            nums = re.findall(r"[-+]?\d*\.?\d+", line)
            if nums:
                result["average_effect"] = float(nums[0])
                if len(nums) >= 3:
                    result["cumulative_effect"] = float(nums[2])
        elif "relative effect" in lower:
            in_absolute_effect = False
            nums = re.findall(r"[-+]?\d*\.?\d+", line)
            if nums:
                result["average_effect_pct"] = float(nums[0])
        elif "tail-area" in lower:
            nums = re.findall(r"[-+]?\d*\.?\d+", line)
            if nums:
                result["p_value"] = float(nums[-1])
        elif "95% ci" in lower and in_absolute_effect:
            brackets = re.findall(r"\[([-+]?\d*\.?\d+),\s*([-+]?\d*\.?\d+)\]", line)
            if brackets:
                result["ci_lower"] = float(brackets[0][0])
                result["ci_upper"] = float(brackets[0][1])

    if result["p_value"] is not None:
        result["significant"] = result["p_value"] < 0.05
    else:
        report_lower = summary_text.lower()
        result["significant"] = "statistically significant" in report_lower and "not statistically significant" not in report_lower

    return result
