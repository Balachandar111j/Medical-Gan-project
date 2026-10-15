"""Retail Sales and Customer Purchasing Analysis - interactive dashboard.

Run from the project folder:
    streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_utils import RAW_PATH, clean, discount_cap_whatif, read_raw

# ---------------------------------------------------------------- page setup
st.set_page_config(page_title="Retail Sales Analysis", page_icon="📊", layout="wide")

BLUE, ORANGE, AQUA, RED, INK_2 = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#52514e"
SLOTS = [BLUE, ORANGE, AQUA, "#eda100", "#e87ba4", "#008300", "#6250d6", RED]
DIVERGING = [[0.0, RED], [0.5, "#f0efec"], [1.0, BLUE]]
FX_RATE = 83.0
STATE_CODES = {
    "Alabama": "AL", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL",
    "Georgia": "GA", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
    "Alaska": "AK", "Hawaii": "HI",
}


def inr(value: float) -> float:
    return value * FX_RATE


def money(value: float, decimals: int = 0) -> str:
    value = inr(value)
    sign = "-" if value < 0 else ""
    return f"{sign}₹{abs(value):,.{decimals}f}"


def money_compact(value: float) -> str:
    """₹2,297,201 -> '₹2.30M' so large KPI values fit their tile."""
    value = inr(value)
    if abs(value) >= 1_000_000:
        return f"{'-' if value < 0 else ''}₹{abs(value) / 1_000_000:,.2f}M"
    return money(value)


def style(fig: go.Figure, height: int = 380) -> go.Figure:
    """Apply one consistent look to every Plotly chart."""
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=50, b=10),
                      legend_title_text="", hoverlabel=dict(font_size=12),
                      font=dict(size=13), title_font=dict(size=16))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.15)")
    return fig


def has(df: pd.DataFrame, col: str) -> bool:
    return col in df.columns


# ---------------------------------------------------------------- data
@st.cache_data(show_spinner="Cleaning the Superstore dataset...")
def load_default():
    return clean(read_raw(RAW_PATH))


@st.cache_data(show_spinner="Cleaning your file...")
def load_uploaded(file_bytes: bytes, file_name: str):
    if file_name.lower().endswith((".xlsx", ".xls")):
        import io
        raw = pd.read_excel(io.BytesIO(file_bytes))
    else:
        raw = read_raw(file_bytes)
    return clean(raw)


st.sidebar.title("📊 Retail Sales Analysis")
source = st.sidebar.radio("Data source", ["Sample Superstore (included)", "Upload my own file"])
try:
    if source == "Upload my own file":
        uploaded = st.sidebar.file_uploader("Superstore-style CSV or Excel", type=["csv", "xlsx", "xls"])
        if uploaded is None:
            st.info("Upload a CSV or Excel file in the sidebar, or switch back to the included dataset.")
            st.stop()
        data, cleaning_notes = load_uploaded(uploaded.getvalue(), uploaded.name)
    else:
        if not RAW_PATH.exists():
            st.error(f"Dataset not found at {RAW_PATH}. Put the Superstore CSV there or upload a file.")
            st.stop()
        data, cleaning_notes = load_default()
except ValueError as error:
    st.error(f"Could not use this file: {error}")
    st.stop()

# ---------------------------------------------------------------- filters
st.sidebar.header("Filters")
min_date, max_date = data["Order Date"].min().date(), data["Order Date"].max().date()
date_range = st.sidebar.date_input("Order date range", (min_date, max_date),
                                   min_value=min_date, max_value=max_date)
start, end = (date_range if isinstance(date_range, (tuple, list)) and len(date_range) == 2
              else (min_date, max_date))


def multiselect(label: str, column: str) -> list:
    if not has(data, column):
        return []
    options = sorted(data[column].dropna().unique().tolist())
    return st.sidebar.multiselect(label, options, placeholder="All")


regions = multiselect("Region", "Region")
segments = multiselect("Customer segment", "Segment")
categories = multiselect("Category", "Category")
subcats = multiselect("Sub-Category", "Sub-Category")
disc_lo, disc_hi = st.sidebar.slider("Discount range", 0.0, 1.0, (0.0, 1.0), 0.05, format="%.2f")

mask = data["Order Date"].dt.date.between(start, end) & data["Discount"].between(disc_lo, disc_hi)
for column, chosen in [("Region", regions), ("Segment", segments),
                       ("Category", categories), ("Sub-Category", subcats)]:
    if chosen:
        mask &= data[column].isin(chosen)
df = data.loc[mask].copy()

st.sidebar.caption(f"Showing **{len(df):,}** of {len(data):,} transactions")
if df.empty:
    st.warning("No transactions match these filters. Widen the filters in the sidebar.")
    st.stop()

CATEGORY_ORDER = sorted(data["Category"].unique())
CAT_COLORS = {c: SLOTS[i] for i, c in enumerate(CATEGORY_ORDER[:8])}

# ---------------------------------------------------------------- header + KPIs
st.title("Retail Sales and Customer Purchasing Analysis")
st.caption("Exploratory Data Analysis dashboard · Sample Superstore (fictional US retailer) · "
           "use the sidebar to filter every chart")

total_sales, total_profit = df["Sales"].sum(), df["Profit"].sum()
orders = df["Order ID"].nunique() if has(df, "Order ID") else None
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total sales", money_compact(total_sales), help=money(total_sales, 2))
k2.metric("Total profit", money_compact(total_profit), help=money(total_profit, 2))
k3.metric("Profit margin", f"{total_profit / total_sales * 100:.1f}%" if total_sales else "n/a",
          help="Total profit ÷ total sales × 100")
k4.metric("Orders", f"{orders:,}" if orders else f"{len(df):,} rows")
k5.metric("Avg order value", money(total_sales / orders) if orders else money(df["Sales"].mean()),
          help="Total sales ÷ unique orders")
k6.metric("Loss-making rows", f"{df['Is Loss'].mean() * 100:.1f}%", help="Share of transactions with profit < 0")

tabs = st.tabs(["📈 Overview", "📦 Products", "🗺️ Regions & Segments", "🏷️ Discounts & What-if",
                "🔬 EDA (Units 3-5)", "📄 Data"])

# ================================================================ OVERVIEW
with tabs[0]:
    monthly = df.groupby("Year-Month").agg(Sales=("Sales", "sum"), Profit=("Profit", "sum")).reset_index()
    monthly["3-month average"] = monthly["Sales"].rolling(3, min_periods=1).mean()

    left, right = st.columns([3, 2])
    fig = px.line(monthly, x="Year-Month", y=["Sales", "3-month average"], markers=True,
                  title="Monthly sales trend", color_discrete_sequence=[BLUE, ORANGE])
    fig.update_traces(selector=dict(name="3-month average"), line_dash="dash", marker_size=0)
    if len(monthly) > 1:
        peak = monthly.loc[monthly["Sales"].idxmax()]
        fig.add_annotation(x=peak["Year-Month"], y=peak["Sales"], text=f"Peak {peak['Year-Month']:%b %Y}",
                           showarrow=True, arrowhead=2, ay=-35)
    fig.update_yaxes(title="Sales (INR)", tickprefix="₹")
    fig.update_xaxes(title="")
    left.plotly_chart(style(fig), width="stretch")

    monthly["Result"] = np.where(monthly["Profit"] >= 0, "Profit", "Loss")
    fig = px.bar(monthly, x="Year-Month", y="Profit", color="Result", title="Monthly profit",
                 color_discrete_map={"Profit": BLUE, "Loss": RED})
    fig.update_yaxes(title="Profit (INR)", tickprefix="₹")
    fig.update_xaxes(title="")
    right.plotly_chart(style(fig), width="stretch")

    st.subheader("Key insights for the current filters")
    cat = df.groupby("Category").agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
    cat["Margin"] = cat["Profit"] / cat["Sales"] * 100
    insights = [
        f"**{cat['Sales'].idxmax()}** has the highest sales ({money(cat['Sales'].max())}); "
        f"**{cat['Margin'].idxmin()}** has the lowest margin ({cat['Margin'].min():.1f}%).",
    ]
    if has(df, "Sub-Category"):
        sub = df.groupby("Sub-Category")["Profit"].sum()
        losers = sub[sub < 0].sort_values()
        insights.append(
            f"Loss-making sub-categories: **{', '.join(losers.index)}** (total {money(losers.sum())})."
            if len(losers) else "No sub-category is loss-making overall for these filters.")
    if has(df, "Region"):
        reg = df.groupby("Region").agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
        reg["Margin"] = reg["Profit"] / reg["Sales"] * 100
        insights.append(f"Best region margin: **{reg['Margin'].idxmax()}** ({reg['Margin'].max():.1f}%); "
                        f"weakest: **{reg['Margin'].idxmin()}** ({reg['Margin'].min():.1f}%).")
    heavy = df[df["Discount"] > 0.2]
    if len(heavy):
        insights.append(f"Transactions with discount above 20%: **{len(heavy):,}** rows, combined profit "
                        f"**{money(heavy['Profit'].sum())}**.")
    for line in insights:
        st.markdown(f"- {line}")

# ================================================================ PRODUCTS
with tabs[1]:
    cat_long = cat.reset_index().melt(id_vars="Category", value_vars=["Sales", "Profit"],
                                      var_name="Measure", value_name="INR")
    left, right = st.columns(2)
    fig = px.bar(cat_long, x="Category", y="INR", color="Measure", barmode="group",
                 title="Sales and profit by category", color_discrete_map={"Sales": BLUE, "Profit": ORANGE},
                 text_auto=".3s")
    fig.update_yaxes(tickprefix="₹")
    left.plotly_chart(style(fig), width="stretch")

    if has(df, "Sub-Category"):
        sub_df = (df.groupby("Sub-Category").agg(Profit=("Profit", "sum"), Sales=("Sales", "sum"),
                                                 Avg_discount=("Discount", "mean"))
                    .sort_values("Profit").reset_index())
        sub_df["Result"] = np.where(sub_df["Profit"] >= 0, "Profit", "Loss")
        fig = px.bar(sub_df, x="Profit", y="Sub-Category", orientation="h", color="Result",
                     color_discrete_map={"Profit": BLUE, "Loss": RED}, title="Profit by sub-category",
                     hover_data={"Sales": ":₹,.0f", "Avg_discount": ":.0%", "Result": False})
        fig.update_xaxes(tickprefix="₹", showgrid=True, gridcolor="rgba(128,128,128,0.15)")
        right.plotly_chart(style(fig, 460), width="stretch")

    if has(df, "Product Name"):
        top_n = st.slider("Number of products to list", 5, 25, 10)
        prod = (df.groupby(["Product Name", "Category"])
                  .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"), Units=("Quantity", "sum"),
                       Avg_discount=("Discount", "mean"))
                  .reset_index())
        money_cols = {"Sales": st.column_config.NumberColumn(format="₹#,##0.00"),
                      "Profit": st.column_config.NumberColumn(format="₹#,##0.00"),
                      "Avg_discount": st.column_config.NumberColumn("Avg discount", format="percent")}
        c1, c2 = st.columns(2)
        c1.markdown(f"**Top {top_n} products by sales**")
        c1.dataframe(prod.nlargest(top_n, "Sales"), hide_index=True, column_config=money_cols, width="stretch")
        c2.markdown(f"**{top_n} products with the largest losses**")
        c2.dataframe(prod.nsmallest(top_n, "Profit"), hide_index=True, column_config=money_cols,
                     width="stretch")
        losing = prod[prod["Profit"] < 0]
        st.caption(f"{len(losing):,} of {len(prod):,} products lose money overall "
                   f"(combined {money(losing['Profit'].sum())}).")

# ================================================================ REGIONS & SEGMENTS
with tabs[2]:
    if has(df, "Region"):
        left, right = st.columns(2)
        heat = df.pivot_table(index="Region", columns="Category", values="Profit", aggfunc="sum").round(0)
        fig = px.imshow(heat, text_auto=",.0f", color_continuous_scale=DIVERGING, color_continuous_midpoint=0,
                        aspect="auto", title="Profit by region and category (red = loss)")
        fig.update_coloraxes(colorbar_title="INR")
        left.plotly_chart(style(fig), width="stretch")

        reg_df = reg.reset_index().sort_values("Sales", ascending=False)
        reg_df["Label"] = reg_df["Margin"].map(lambda m: f"margin {m:.1f}%")
        fig = px.bar(reg_df, x="Region", y="Sales", text="Label",
                     title="Sales by region", color_discrete_sequence=[BLUE],
                     hover_data={"Profit": ":₹,.0f", "Margin": ":.1f", "Label": False})
        fig.update_yaxes(tickprefix="₹")
        right.plotly_chart(style(fig), width="stretch")

    if has(df, "State"):
        state = df.groupby("State").agg(Sales=("Sales", "sum"), Profit=("Profit", "sum")).reset_index()
        state["Code"] = state["State"].map(STATE_CODES)
        state["Margin %"] = state["Profit"] / state["Sales"] * 100
        state = state.dropna(subset=["Code"])
        if len(state):
            limit = state["Profit"].abs().max()
            fig = px.choropleth(state, locations="Code", locationmode="USA-states", scope="usa",
                                color="Profit", color_continuous_scale=DIVERGING, range_color=(-limit, limit),
                                hover_name="State", hover_data={"Code": False, "Sales": ":₹,.0f",
                                                                "Profit": ":₹,.0f", "Margin %": ":.1f"},
                                title="Profit by state (red = loss-making state)")
            st.plotly_chart(style(fig, 450), width="stretch")
            worst = state.nsmallest(10, "Profit").sort_values("Profit", ascending=False)
            fig = px.bar(worst, x="Profit", y="State", orientation="h", color_discrete_sequence=[RED],
                         title="10 states with the lowest total profit (works offline)",
                         hover_data={"Sales": ":₹,.0f", "Margin %": ":.1f"})
            fig.update_xaxes(tickprefix="₹", showgrid=True, gridcolor="rgba(128,128,128,0.15)")
            st.plotly_chart(style(fig), width="stretch")

    if has(df, "Segment"):
        seg = df.groupby("Segment").agg(Sales=("Sales", "sum"), Profit=("Profit", "sum")).reset_index()
        seg_long = seg.melt(id_vars="Segment", var_name="Measure", value_name="INR")
        fig = px.bar(seg_long, x="Segment", y="INR", color="Measure", barmode="group", text_auto=".3s",
                     title="Sales and profit by customer segment",
                     color_discrete_map={"Sales": BLUE, "Profit": ORANGE})
        fig.update_yaxes(tickprefix="₹")
        st.plotly_chart(style(fig), width="stretch")

# ================================================================ DISCOUNTS & WHAT-IF
with tabs[3]:
    band = (df.groupby("Discount Band", observed=True)
              .agg(Transactions=("Sales", "size"), Sales=("Sales", "sum"), Profit=("Profit", "sum"),
                   Loss_rows=("Is Loss", "mean")).reset_index())
    band["Margin %"] = band["Profit"] / band["Sales"] * 100
    band["Loss rows %"] = band["Loss_rows"] * 100
    band["Result"] = np.where(band["Margin %"] >= 0, "Profit", "Loss")
    band["Discount Band"] = band["Discount Band"].astype(str)

    left, right = st.columns(2)
    fig = px.bar(band, x="Discount Band", y="Margin %", color="Result", text_auto=".1f",
                 category_orders={"Discount Band": ["0%", "1-20%", "21-40%", "Above 40%"]},
                 color_discrete_map={"Profit": BLUE, "Loss": RED}, title="Overall profit margin by discount band",
                 hover_data={"Transactions": ":,", "Loss rows %": ":.1f", "Result": False})
    fig.update_yaxes(ticksuffix="%")
    fig.update_xaxes(type="category")      # stop Plotly reading '0%' as the number 0
    left.plotly_chart(style(fig), width="stretch")

    sample = df.sample(min(3000, len(df)), random_state=42).copy()
    rng = np.random.default_rng(42)
    sample["Discount (jittered)"] = sample["Discount"] + rng.uniform(-0.01, 0.01, len(sample))
    fig = px.scatter(sample, x="Discount (jittered)", y="Profit", color="Category", opacity=0.5,
                     title="Discount vs profit per transaction",
                     color_discrete_map=CAT_COLORS, category_orders={"Category": CATEGORY_ORDER},
                     hover_data={c: True for c in ["Product Name", "Sales", "Discount"] if has(df, c)}
                     | {"Discount (jittered)": False})
    fig.update_xaxes(title="Discount", tickformat=".0%")
    fig.add_hline(y=0, line_color=RED, line_width=1)
    fig.update_yaxes(tickprefix="₹")
    right.plotly_chart(style(fig), width="stretch")

    st.subheader("What-if: cap discounts")
    st.markdown(
        "- Every transaction with a discount above the cap is re-priced at the cap.\n"
        "- **Assumption:** customers still buy the same quantity. In reality some might not, so treat the result "
        "as an upper estimate, not a forecast.")
    cap = st.slider("Maximum discount allowed", 0.0, 0.8, 0.2, 0.05, format="%.2f")
    sim = discount_cap_whatif(df, cap)
    affected = sim["Affected"]
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Transactions re-priced ({affected.mean() * 100:.1f}% of rows)", f"{int(affected.sum()):,}")
    c2.metric("Profit today", money(sim["Profit"].sum()))
    gain = sim["New Profit"].sum() - sim["Profit"].sum()
    c3.metric("Profit with the cap", money(sim["New Profit"].sum()), f"{money(gain)} if volume holds")
    by_cat = (pd.concat([df[["Category"]], sim], axis=1).groupby("Category")[["Profit", "New Profit"]].sum()
                .reset_index().melt(id_vars="Category", var_name="Scenario", value_name="INR"))
    by_cat["Scenario"] = by_cat["Scenario"].replace({"Profit": "Today", "New Profit": f"Cap at {cap:.0%}"})
    fig = px.bar(by_cat, x="Category", y="INR", color="Scenario", barmode="group", text_auto=".3s",
                 title="Profit today vs with the discount cap", color_discrete_sequence=[INK_2, BLUE])
    fig.update_yaxes(tickprefix="₹")
    st.plotly_chart(style(fig), width="stretch")

# ================================================================ EDA
with tabs[4]:
    st.markdown("Explore one variable (Unit 3), pairs of variables (Unit 4) and all of them together (Unit 5).")
    variable = st.selectbox("Variable", ["Sales", "Profit", "Quantity", "Discount", "Profit Margin (%)"])
    series = df[variable].dropna()
    q1, q3 = series.quantile([0.25, 0.75])
    iqr = q3 - q1
    outliers = ((series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)).sum()

    stats_cols = st.columns(7)
    for col, (label, value) in zip(stats_cols, [
            ("Mean", series.mean()), ("Median", series.median()), ("Std dev", series.std()),
            ("Q1 (25%)", q1), ("Q3 (75%)", q3), ("Skewness", series.skew())]):
        col.metric(label, f"{value:,.2f}")
    stats_cols[6].metric(f"IQR outliers ({outliers / len(series):.1%})", f"{outliers:,}",
                         help="Values beyond Q1 - 1.5×IQR or Q3 + 1.5×IQR")

    left, right = st.columns(2)
    log_scale = left.checkbox("Log scale (useful for skewed Sales)", value=False,
                              disabled=bool((series <= 0).any()))
    fig = px.histogram(df, x=variable, nbins=60, color_discrete_sequence=[BLUE], log_x=log_scale,
                       title=f"Distribution of {variable}")
    fig.add_vline(x=series.median(), line_dash="dash", line_color=INK_2, annotation_text="median")
    left.plotly_chart(style(fig), width="stretch")
    fig = px.box(df, x="Category", y=variable, color="Category", color_discrete_map=CAT_COLORS, log_y=log_scale,
                 category_orders={"Category": CATEGORY_ORDER}, title=f"{variable} by category (box plot)")
    fig.update_layout(showlegend=False)
    right.plotly_chart(style(fig), width="stretch")

    method = st.radio("Correlation method", ["pearson", "spearman"], horizontal=True,
                      format_func=lambda m: m.title())
    corr = df[["Sales", "Profit", "Quantity", "Discount"]].corr(method=method).round(2)
    left, right = st.columns([1, 1])
    fig = px.imshow(corr, text_auto=".2f", zmin=-1, zmax=1, color_continuous_scale=DIVERGING,
                    title=f"{method.title()} correlation heatmap")
    left.plotly_chart(style(fig), width="stretch")
    right.markdown(
        f"- **Discount vs Profit:** {corr.loc['Discount', 'Profit']:+.2f}\n"
        f"- **Sales vs Profit:** {corr.loc['Sales', 'Profit']:+.2f}\n"
        f"- **Sales vs Quantity:** {corr.loc['Sales', 'Quantity']:+.2f}\n"
        "- Pearson measures straight-line association; Spearman uses ranks, so it is robust to outliers.\n"
        "- Correlation shows association, **not** cause and effect.")

# ================================================================ DATA
with tabs[5]:
    st.markdown("**Cleaning summary**")
    for note in cleaning_notes:
        st.markdown(f"- {note}")
    show_cols = [c for c in ["Order ID", "Order Date", "Ship Date", "Customer Name", "Segment", "Region",
                             "State", "Category", "Sub-Category", "Product Name", "Sales", "Quantity",
                             "Discount", "Profit", "Profit Margin (%)"] if has(df, c)]
    st.dataframe(df[show_cols], hide_index=True, width="stretch", height=420,
                 column_config={"Order Date": st.column_config.DateColumn(format="YYYY-MM-DD"),
                                "Ship Date": st.column_config.DateColumn(format="YYYY-MM-DD"),
                                "Sales": st.column_config.NumberColumn(format="₹#,##0.00"),
                                "Profit": st.column_config.NumberColumn(format="₹#,##0.00"),
                                "Discount": st.column_config.NumberColumn(format="percent"),
                                "Profit Margin (%)": st.column_config.NumberColumn(format="%.1f")})
    st.download_button("Download filtered data (CSV)", df[show_cols].to_csv(index=False).encode("utf-8"),
                       file_name="filtered_superstore.csv", mime="text/csv")

st.caption("Data: Sample Superstore (fictional, 2014–2017). Findings describe this sample, not a real retailer.")
