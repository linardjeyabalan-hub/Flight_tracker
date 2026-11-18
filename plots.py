import sqlite3
import webbrowser
import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Load data from SQLite
conn = sqlite3.connect("prices.db")
df = pd.read_sql_query("SELECT * FROM prices", conn)
conn.close()

if df.empty:
    print("No data in prices.db yet.")
    exit()

# Convert run_id (YYYY-MM-DD_HH-MM-SS) into a clean datetime for the X-axis
df["run_time"] = pd.to_datetime(df["run_id"], format="%Y-%m-%d_%H-%M-%S")

# 2. Pivot so each run_id is one row and each option_name is a column
pivot_df = df.pivot_table(
    index="run_time",
    columns="option_name",
    values="price",
    aggfunc="first"
).sort_index()

# Automatically compute the sum of the two One-Way legs
if "IST-CMB" in pivot_df.columns and "CMB-HEL" in pivot_df.columns:
    pivot_df["One-Way Combined (IST-CMB + CMB-HEL)"] = (
        pivot_df["IST-CMB"] + pivot_df["CMB-HEL"]
    )

# 3. Create a 2-panel interactive figure (Top: Total Comparison, Bottom: Individual Legs)
fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.12,
    subplot_titles=(
        "Total Trip Cost Comparison: Combined One-Ways vs. Multi-City (CHF)",
        "Individual One-Way Leg Breakdown (CHF)"
    )
)

# Top Panel: Compare total booking strategies
total_series = [
    "One-Way Combined (IST-CMB + CMB-HEL)",
    "IST-CMB-HEL (Multi-City)"
]
for col in total_series:
    if col in pivot_df.columns:
        fig.add_trace(
            go.Scatter(
                x=pivot_df.index,
                y=pivot_df[col],
                mode="lines+markers",
                name=col,
                hovertemplate="%{y:,.0f} CHF<br>%{x|%Y-%m-%d %H:%M}<extra>" + col + "</extra>"
            ),
            row=1, col=1
        )

# Bottom Panel: Individual One-Way Legs
leg_series = ["IST-CMB", "CMB-HEL"]
for col in leg_series:
    if col in pivot_df.columns:
        fig.add_trace(
            go.Scatter(
                x=pivot_df.index,
                y=pivot_df[col],
                mode="lines+markers",
                name=col,
                hovertemplate="%{y:,.0f} CHF<br>%{x|%Y-%m-%d %H:%M}<extra>" + col + "</extra>"
            ),
            row=2, col=1
        )

fig.update_layout(
    height=750,
    title_text="Flight Price Tracker (2 Adults, 3 Children — TK Flights)",
    hovermode="x unified",
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

fig.update_yaxes(title_text="Total Price (CHF)", row=1, col=1)
fig.update_yaxes(title_text="Leg Price (CHF)", row=2, col=1)

# 4. Save to standalone HTML and open in browser
output_file = os.path.abspath("price_trends.html")
fig.write_html(output_file, include_plotlyjs="cdn")
print(f"Chart saved to {output_file}")
