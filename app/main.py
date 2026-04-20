from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

from app.schemas import (
    AnalysisResult,
    AnalyzeRequest,
    AnalyzeResponse,
    DataSummary,
    HealthResponse,
)
from app.data_processing import get_data_summary
from app.causal_analysis import run_analysis, get_result, get_plot

app = FastAPI(
    title="Campaign Impact Analysis",
    description="Analyze the causal impact of marketing campaigns on e-commerce revenue",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", version="0.1.0")


@app.get("/data/summary", response_model=DataSummary)
def data_summary():
    summary = get_data_summary()
    return DataSummary(**summary)


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    try:
        analysis_id = run_analysis(
            intervention_date=request.intervention_date,
            covariates=request.covariates,
            alpha=request.alpha,
        )
        return AnalyzeResponse(
            analysis_id=analysis_id,
            status="completed",
            message="Analysis completed successfully. Use /results/{analysis_id} to retrieve results.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/results/{analysis_id}", response_model=AnalysisResult)
def results(analysis_id: str):
    result = get_result(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return AnalysisResult(**result)


@app.get("/results/{analysis_id}/plot")
def plot(analysis_id: str):
    plot_bytes = get_plot(analysis_id)
    if plot_bytes is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return Response(content=plot_bytes, media_type="image/png")
