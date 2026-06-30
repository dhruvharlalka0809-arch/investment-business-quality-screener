from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ScreeningWeights:
    growth: float = 0.16
    margin: float = 0.14
    fcf_conversion: float = 0.15
    roic: float = 0.17
    leverage: float = 0.11
    concentration: float = 0.09
    recurring_revenue: float = 0.10
    rule_of_40: float = 0.05
    market_position: float = 0.03


REQUIRED_COLUMNS = {
    "Company",
    "Sector",
    "Revenue",
    "Revenue_Growth",
    "EBITDA_Margin",
    "FCF_Conversion",
    "ROIC",
    "Net_Debt_EBITDA",
    "Customer_Concentration",
    "Recurring_Revenue",
    "Rule_Of_40",
    "Market_Position",
}


def load_company_universe(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def normalize_company_universe(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    output = df.copy()
    numeric_columns = REQUIRED_COLUMNS.difference({"Company", "Sector", "Market_Position"})
    for column in numeric_columns:
        output[column] = pd.to_numeric(output[column], errors="coerce")
    output = output.dropna(subset=["Company", "Revenue"]).reset_index(drop=True)
    return output


def score_company_universe(df: pd.DataFrame, weights: ScreeningWeights) -> pd.DataFrame:
    universe = normalize_company_universe(df)
    output = universe.copy()
    output["Growth_Score"] = score_positive(output["Revenue_Growth"], 0.00, 0.22)
    output["Margin_Score"] = score_positive(output["EBITDA_Margin"], 0.08, 0.26)
    output["FCF_Score"] = score_positive(output["FCF_Conversion"], 0.30, 0.90)
    output["ROIC_Score"] = score_positive(output["ROIC"], 0.06, 0.22)
    output["Leverage_Score"] = score_negative(output["Net_Debt_EBITDA"], 0.0, 3.5)
    output["Concentration_Score"] = score_negative(output["Customer_Concentration"], 0.10, 0.40)
    output["Recurring_Revenue_Score"] = score_positive(output["Recurring_Revenue"], 0.30, 0.90)
    output["Rule_Of_40_Score"] = score_positive(output["Rule_Of_40"], 0.10, 0.45)
    output["Market_Position_Score"] = output["Market_Position"].map(score_market_position).fillna(50.0)
    output["Quality_Score"] = (
        output["Growth_Score"] * weights.growth
        + output["Margin_Score"] * weights.margin
        + output["FCF_Score"] * weights.fcf_conversion
        + output["ROIC_Score"] * weights.roic
        + output["Leverage_Score"] * weights.leverage
        + output["Concentration_Score"] * weights.concentration
        + output["Recurring_Revenue_Score"] * weights.recurring_revenue
        + output["Rule_Of_40_Score"] * weights.rule_of_40
        + output["Market_Position_Score"] * weights.market_position
    )
    output["Risk_Flags"] = output.apply(build_risk_flags, axis=1)
    output["Recommendation"] = output.apply(recommend_company, axis=1)
    return output.sort_values("Quality_Score", ascending=False).reset_index(drop=True)


def build_sector_summary(scored: pd.DataFrame) -> pd.DataFrame:
    grouped = scored.groupby("Sector", as_index=False).agg(
        Companies=("Company", "count"),
        Avg_Quality_Score=("Quality_Score", "mean"),
        Avg_Revenue_Growth=("Revenue_Growth", "mean"),
        Avg_EBITDA_Margin=("EBITDA_Margin", "mean"),
        Avg_ROIC=("ROIC", "mean"),
        Avg_Leverage=("Net_Debt_EBITDA", "mean"),
    )
    return grouped.sort_values("Avg_Quality_Score", ascending=False).reset_index(drop=True)


def build_screening_memo(scored: pd.DataFrame, sector_summary: pd.DataFrame) -> str:
    top = scored.iloc[0]
    watchlist_count = int((scored["Recommendation"] == "Watchlist").sum())
    avoid_count = int((scored["Recommendation"] == "Avoid").sum())
    best_sector = sector_summary.iloc[0]
    return f"""### Investment & Business Quality Screening Memo

**Top-ranked company:** {top.Company} with a quality score of {float(top.Quality_Score):.1f}/100.

**Why it screens well:** {top.Company} combines {float(top.Revenue_Growth):.1%} revenue growth, {float(top.EBITDA_Margin):.1%} EBITDA margin, {float(top.FCF_Conversion):.1%} FCF conversion, and {float(top.ROIC):.1%} ROIC.

**Quality signals:** Rule of 40 is {float(top.Rule_Of_40):.1%}; market position is {top.Market_Position}.

**Best sector:** {best_sector.Sector} has the highest average quality score at {float(best_sector.Avg_Quality_Score):.1f}/100.

**Portfolio screen:** {watchlist_count} companies require watchlist review and {avoid_count} companies screen as avoid candidates.

**Screening interpretation:** Attractive companies combine growth durability, margin quality, cash conversion, capital efficiency, low leverage, low customer concentration, and recurring revenue. Watchlist companies need diligence on one or two weak spots. Avoid candidates show multiple operational or balance-sheet risk flags.
"""


def build_risk_flags(row: pd.Series) -> str:
    flags = []
    if float(row["Net_Debt_EBITDA"]) > 2.5:
        flags.append("High leverage")
    if float(row["Customer_Concentration"]) > 0.30:
        flags.append("Customer concentration")
    if float(row["FCF_Conversion"]) < 0.50:
        flags.append("Weak cash conversion")
    if float(row["ROIC"]) < 0.10:
        flags.append("Low ROIC")
    if float(row["EBITDA_Margin"]) < 0.12:
        flags.append("Thin margin")
    if float(row["Rule_Of_40"]) < 0.30:
        flags.append("Below Rule of 40")
    return ", ".join(flags) if flags else "None"


def recommend_company(row: pd.Series) -> str:
    score = float(row["Quality_Score"])
    flags = str(row["Risk_Flags"])
    flag_count = count_risk_flags(flags)
    if score >= 72 and flag_count == 0:
        return "Attractive"
    if score < 45 or flag_count >= 3:
        return "Avoid"
    return "Watchlist"


def count_risk_flags(flags: str) -> int:
    if flags == "None":
        return 0
    return len([flag for flag in flags.split(",") if flag.strip()])


def score_market_position(position: str) -> float:
    scores = {
        "Leader": 100.0,
        "Challenger": 65.0,
        "Niche": 35.0,
    }
    return scores.get(str(position), 50.0)


def score_positive(series: pd.Series, floor: float, ceiling: float) -> pd.Series:
    return ((series - floor) / (ceiling - floor) * 100).clip(lower=0, upper=100)


def score_negative(series: pd.Series, floor: float, ceiling: float) -> pd.Series:
    return (100 - ((series - floor) / (ceiling - floor) * 100)).clip(lower=0, upper=100)
