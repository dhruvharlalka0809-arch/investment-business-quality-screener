# Investment & Business Quality Screener

A Streamlit dashboard that ranks companies by investment and business quality using growth, margin quality, free cash flow conversion, ROIC, leverage, customer concentration, recurring revenue, and risk flags.

## What It Does

- Scores a company universe on a 0-100 quality scale
- Ranks companies as Attractive, Watchlist, or Avoid
- Identifies risk flags such as high leverage, customer concentration, weak cash conversion, low ROIC, and thin margins
- Summarizes quality by sector
- Lets users adjust screening weights in the sidebar
- Generates an investment screening memo
- Supports CSV upload for custom company universes

## Why This Project Matters

This project bridges finance, investment research, business analysis, and consulting. It shows a practical ability to turn company metrics into a structured screening framework and an executive-ready recommendation.

## Tech Stack

- Python
- Streamlit
- Pandas
- Standard-library tests with `unittest`

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Input Data Format

```csv
Company,Sector,Revenue,Revenue_Growth,EBITDA_Margin,FCF_Conversion,ROIC,Net_Debt_EBITDA,Customer_Concentration,Recurring_Revenue,Rule_Of_40,Market_Position
Atlas Workflow Systems,B2B Software,515,0.115,0.185,0.72,0.142,1.0,0.22,0.82,0.300,Leader
```

## Validate

```bash
python scripts/validate.py
```

## Portfolio Talking Points

- Built a company quality screener for investment, consulting, and business analysis use cases
- Combined growth, profitability, cash conversion, capital efficiency, leverage, concentration, and recurring revenue into a weighted score
- Added risk flags and recommendation logic for Attractive, Watchlist, and Avoid classifications
- Converted screening results into an executive-style investment memo

## Author

Dhruv Harlalka

MBA Finance, Middlesex University Dubai
