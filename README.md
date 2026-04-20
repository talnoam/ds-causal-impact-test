# Data Science Take-Home: Campaign Impact Analysis

## Scenario

You're a data scientist at an e-commerce analytics company. A Shopify skincare store
ran an **email marketing campaign** starting on **October 27, 2024** and wants to know:
**did the campaign significantly increase daily revenue?**

We've built a prototype service that uses **Bayesian Structural Time Series (CausalImpact)**
to answer this question. The service loads order data and shop metrics from a SQLite
database, aggregates them, and runs a causal impact analysis.

**The problem:** The analysis currently reports that the campaign had **no significant
effect** on revenue. The client is convinced revenue went up. It could be they are wrong,
but they are extremely confident.

Your job: find and fix the issues if there are any, improve the model, and explain your reasoning.

---

## Prerequisites

- **Docker** and **Docker Compose** installed and running
- A tool to make HTTP requests (curl, Postman, httpie, or just use the built-in Swagger UI)

---

## Setup & Running

### Step 1: Start the service

Pick one:

**With live reload** — edits to `app/*.py` restart the server automatically:
```bash
docker compose up --build
```

**With debugger** — set breakpoints in VS Code / Cursor and step through code:
```bash
docker compose -f docker-compose.yml -f docker-compose.debug.yml up --build
# Then in VS Code/Cursor: select "Debug: Attach to Docker" and press F5
```
(No live reload in debug mode — restart the container after code changes.)

Both start the API on **http://localhost:8000**. The SQLite database (`data/shop.db`)
is included in the repo and mounted into the container automatically.

The database contains two tables:

**`orders`** — individual order records (~40k rows across 365 days)
| Column | Type | Description |
|--------|------|-------------|
| order_id | TEXT | e.g. "ORD-10001" |
| user_id | TEXT | e.g. "user_12345" |
| created_at | TEXT | ISO 8601 timestamp |
| amount | REAL | Order amount in USD |
| product_category | TEXT | skincare, supplements, accessories, bundles |
| is_refund | INTEGER | 0 or 1 |

**`shop_metrics`** — daily shop-level metrics (365 rows)
| Column | Type |
|--------|------|
| date | TEXT (YYYY-MM-DD) |
| organic_sessions | INTEGER |
| paid_sessions | INTEGER |
| email_campaigns_sent | INTEGER |
| avg_discount_pct | REAL |
| returning_customer_pct | REAL |
| site_conversion_rate | REAL |

You can inspect the database directly:
```bash
sqlite3 data/shop.db ".tables"
sqlite3 data/shop.db "SELECT COUNT(*) FROM orders;"
sqlite3 data/shop.db "SELECT * FROM orders LIMIT 5;"
sqlite3 data/shop.db "SELECT * FROM shop_metrics LIMIT 5;"
```

### Step 2: Verify it's running

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","version":"0.1.0"}
```

Or open **http://localhost:8000/docs** in your browser for the interactive Swagger UI.

### Step 3: Explore the data

```bash
# Get a summary of the dataset
curl http://localhost:8000/data/summary
```

### Step 4: Run the analysis

```bash
# Run the causal impact analysis
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"intervention_date": "2024-10-27"}'

# The response includes an analysis_id. Use it to get results:
curl http://localhost:8000/results/{analysis_id}

# View the plot — open this URL in your browser:
http://localhost:8000/results/{analysis_id}/plot
```

### Making code changes

The `app/` directory is mounted into the container with live reload enabled.
When you edit files in `app/`, the server restarts automatically — no need to
rebuild the container.

If you need to install additional Python packages, add them to `requirements.txt`
and rebuild:
```bash
docker compose up --build
```

### Alternative: Run locally without Docker

If you prefer to run outside Docker (e.g. for faster iteration), you can run
the service directly:

```bash
docker compose down

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Select "Debug: Local (no Docker)" in VS Code/Cursor and press F5
# Or run manually:
DATABASE_PATH=data/shop.db uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Tasks

### Part 1: Explore & Debug (60–90 minutes)

1. **Run the service** and explore the endpoints. Start with `/data/summary`
   to understand the data, then run `/analyze` with the intervention date provided above.

2. **The analysis reports no significant campaign effect.** This is wrong — there
   IS a real campaign effect in the data. Find and fix the bug(s) that cause
   incorrect results. There are **two distinct bugs** in the codebase.

3. For each bug you find:
   - Describe what the bug is and where it lives (file + line)
   - Explain **why** it leads to incorrect causal impact estimates
   - Implement a fix and explain the improvements made.
   
### Part 2: Improve the Model (30–60 minutes)

4. After fixing the bugs, the model should show a significant effect. But can
   you make it more accurate?
   - Are there **confounding factors** in the post-period that inflate the estimate?
   - Can you add features that capture **seasonality** or other patterns?
   - Which covariates should (and should NOT) be included, and why?

5. Discuss the **limitations** of this analysis approach.

### Format & Tools

Submit your work in whatever format you prefer — modify the code directly, use a
Jupyter notebook, a standalone script, or any combination. There is no required format.

**AI code completion tools (Copilot, Cursor, etc.) are encouraged.** We care about
your reasoning and decisions, not whether you typed every character.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/data/summary` | Dataset summary statistics |
| POST | `/analyze` | Run causal impact analysis |
| GET | `/results/{id}` | Get analysis results |
| GET | `/results/{id}/plot` | Get analysis plot (PNG) |

**POST /analyze** request body:
```json
{
  "intervention_date": "2024-10-27",
  "covariates": ["organic_sessions", "avg_discount_pct"],
  "alpha": 0.05
}
```
- `intervention_date` (required): Start date of the campaign
- `covariates` (optional): List of shop metric columns to include. If omitted, uses defaults.
- `alpha` (optional): Significance level, default 0.05

---

## Project Structure

```
├── README.md              ← You are here
├── Dockerfile             ← Container definition
├── docker-compose.yml     ← Service orchestration
├── requirements.txt       ← Python dependencies
├── data/
│   └── shop.db            ← SQLite database (simulated e-commerce data)
├── app/
│   ├── main.py            ← FastAPI endpoints
│   ├── schemas.py         ← Request/response models
│   ├── database.py        ← Database connection helpers
│   ├── data_processing.py ← Data loading & aggregation
│   └── causal_analysis.py ← CausalImpact analysis logic
└── tests/
    └── test_basic.py      ← Basic smoke tests
```

---

## Evaluation Criteria

- **Debugging skill**: Can you identify non-obvious data and modeling issues?
- **Statistical reasoning**: Do you understand causal inference principles?
- **Code quality**: Are your fixes clean, well-reasoned, and tested?
- **Communication**: Can you explain technical decisions clearly?

---

## Tips

- Look carefully at the data summary statistics. Do the numbers make sense?
- Think about what a "covariate" means in a causal inference model.
- You can query the SQLite database directly to explore the raw data.
- The Swagger UI at `/docs` is the easiest way to interact with the API.

---