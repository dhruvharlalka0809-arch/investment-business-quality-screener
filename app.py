import pandas as pd
import streamlit as st

from src.quality_model import (
    ScreeningWeights,
    build_screening_memo,
    build_sector_summary,
    load_company_universe,
    score_company_universe,
)


def format_percent_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    output = df.copy()
    for column in columns:
        if column in output.columns:
            output[column] = output[column].map(lambda value: f"{value:.1%}")
    return output


def format_number_columns(df: pd.DataFrame, columns: list[str], suffix: str = "") -> pd.DataFrame:
    output = df.copy()
    for column in columns:
        if column in output.columns:
            output[column] = output[column].map(lambda value: f"{value:,.1f}{suffix}")
    return output


st.set_page_config(
    page_title="Investment & Business Quality Screener",
    page_icon=":mag:",
    layout="wide",
)


@st.cache_data
def load_sample_universe() -> pd.DataFrame:
    return load_company_universe("data/company_universe.csv")


st.title("Investment & Business Quality Screener")
st.caption("Rank companies by growth, margin quality, cash conversion, ROIC, leverage, concentration risk, and recurring revenue.")

with st.sidebar:
    st.header("Screening Weights")
    growth_weight = st.slider("Growth", 0.00, 0.35, 0.18, 0.01)
    margin_weight = st.slider("EBITDA margin", 0.00, 0.35, 0.16, 0.01)
    fcf_weight = st.slider("FCF conversion", 0.00, 0.35, 0.16, 0.01)
    roic_weight = st.slider("ROIC", 0.00, 0.35, 0.18, 0.01)
    leverage_weight = st.slider("Low leverage", 0.00, 0.25, 0.12, 0.01)
    concentration_weight = st.slider("Low concentration", 0.00, 0.25, 0.10, 0.01)
    recurring_weight = st.slider("Recurring revenue", 0.00, 0.25, 0.10, 0.01)
    st.caption("Weights are normalized automatically so the quality score remains on a 0-100 scale.")
    sector_filter = st.multiselect("Sector filter", sorted(load_sample_universe()["Sector"].unique()))
    uploaded_file = st.file_uploader("Upload company universe", type="csv")

raw_weights = {
    "growth": growth_weight,
    "margin": margin_weight,
    "fcf_conversion": fcf_weight,
    "roic": roic_weight,
    "leverage": leverage_weight,
    "concentration": concentration_weight,
    "recurring_revenue": recurring_weight,
}
total_weight = sum(raw_weights.values()) or 1.0
weights = ScreeningWeights(**{key: value / total_weight for key, value in raw_weights.items()})

try:
    universe = pd.read_csv(uploaded_file) if uploaded_file else load_sample_universe()
    if sector_filter:
        universe = universe.loc[universe["Sector"].isin(sector_filter)]
    scored = score_company_universe(universe, weights)
except Exception as exc:
    st.error(f"Could not load company universe: {exc}")
    st.stop()

sector_summary = build_sector_summary(scored)
top_company = scored.iloc[0]
attractive_count = int((scored["Recommendation"] == "Attractive").sum())
watchlist_count = int((scored["Recommendation"] == "Watchlist").sum())
avoid_count = int((scored["Recommendation"] == "Avoid").sum())

hero = st.columns(5)
hero[0].metric("Top Company", str(top_company.Company))
hero[1].metric("Top Score", f"{float(top_company.Quality_Score):.1f}/100")
hero[2].metric("Attractive", attractive_count)
hero[3].metric("Watchlist", watchlist_count)
hero[4].metric("Avoid", avoid_count)

st.divider()

snapshot_tab, company_tab, sector_tab, memo_tab, data_tab = st.tabs(
    ["Screening Snapshot", "Company Scores", "Sector View", "Investment Memo", "Data"]
)

with snapshot_tab:
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Quality Score Ranking")
        ranking_chart = scored[["Company", "Quality_Score"]].set_index("Company")
        st.bar_chart(ranking_chart, use_container_width=True)
    with right:
        st.subheader("Top Candidate Readout")
        st.write(f"**{top_company.Company}** screens as **{top_company.Recommendation}**.")
        st.write(f"Quality score: **{float(top_company.Quality_Score):.1f}/100**")
        st.write(f"Risk flags: **{top_company.Risk_Flags}**")
        st.write(f"Rule of 40: **{float(top_company.Rule_Of_40):.1%}**")

    st.subheader("Recommendation Mix")
    recommendation_mix = scored["Recommendation"].value_counts().rename_axis("Recommendation").reset_index(name="Companies")
    st.bar_chart(recommendation_mix.set_index("Recommendation"), use_container_width=True)

with company_tab:
    st.subheader("Company Scorecard")
    display = scored[
        [
            "Company",
            "Sector",
            "Quality_Score",
            "Recommendation",
            "Revenue_Growth",
            "EBITDA_Margin",
            "FCF_Conversion",
            "ROIC",
            "Net_Debt_EBITDA",
            "Customer_Concentration",
            "Recurring_Revenue",
            "Risk_Flags",
        ]
    ].copy()
    display = format_percent_columns(
        display,
        ["Revenue_Growth", "EBITDA_Margin", "FCF_Conversion", "ROIC", "Customer_Concentration", "Recurring_Revenue"],
    )
    display = format_number_columns(display, ["Quality_Score"], "/100")
    st.dataframe(display, use_container_width=True, hide_index=True)

with sector_tab:
    st.subheader("Sector Quality View")
    sector_display = sector_summary.copy()
    sector_display = format_percent_columns(sector_display, ["Avg_Revenue_Growth", "Avg_EBITDA_Margin", "Avg_ROIC"])
    sector_display = format_number_columns(sector_display, ["Avg_Quality_Score"], "/100")
    sector_display = format_number_columns(sector_display, ["Avg_Leverage"], "x")
    st.dataframe(sector_display, use_container_width=True, hide_index=True)

    st.subheader("Average Quality by Sector")
    st.bar_chart(sector_summary.set_index("Sector")["Avg_Quality_Score"], use_container_width=True)

with memo_tab:
    st.subheader("Investment Screening Memo")
    memo = build_screening_memo(scored, sector_summary)
    st.markdown(memo)
    st.download_button("Download memo", memo, "investment_quality_screening_memo.md", "text/markdown")

with data_tab:
    st.subheader("Source Company Universe")
    st.dataframe(universe, use_container_width=True, hide_index=True)
    st.subheader("Scoring Methodology")
    st.write("Positive factors are scored higher when the metric is stronger: growth, EBITDA margin, FCF conversion, ROIC, and recurring revenue.")
    st.write("Risk factors are scored higher when risk is lower: leverage and customer concentration.")
    st.write("Recommendations combine quality score thresholds with risk-flag count.")
