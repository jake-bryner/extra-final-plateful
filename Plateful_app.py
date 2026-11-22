import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from io import StringIO

st.set_page_config(page_title="Plateful | Production Planner", page_icon="🍽️", layout="wide")

# ---------- Styling ----------
st.markdown("""
<style>
    .block-container {padding-top: 1.8rem; padding-bottom: 2rem;}
    [data-testid="stMetric"] {background: #f4f7f3; padding: 14px 16px; border-radius: 12px;}
    .hero {padding: 1.3rem 1.5rem; border-radius: 16px; background: linear-gradient(110deg,#123b2b,#28734e); color:white;}
    .hero p {color:#e4f1e8; margin-bottom:0;}
    .small-note {color:#64748b; font-size:0.88rem;}
</style>
""", unsafe_allow_html=True)

# ---------- Sample data ----------
DEFAULT_SALES = pd.DataFrame({
    "Date": pd.date_range(end=date.today() - timedelta(days=1), periods=7).date,
    "Portions sold": [62, 68, 73, 70, 86, 91, 78],
})
DEFAULT_INVENTORY = pd.DataFrame({
    "Ingredient": ["Rice", "Pasta", "Lentils", "Tomato sauce"],
    "Available quantity (kg)": [8.0, 6.0, 4.0, 5.0],
    "Kg per portion": [0.10, 0.08, 0.06, 0.05],
    "Cost per kg (CAD)": [0.94, 1.13, 1.48, 0.81],
})
DEFAULT_MENU = pd.DataFrame({
    "Menu item": ["Koshary"],
    "Selling price (CAD)": [0.94],
    "Other cost per portion (CAD)": [0.19],
})

if "sales" not in st.session_state:
    st.session_state.sales = DEFAULT_SALES.copy()
if "inventory" not in st.session_state:
    st.session_state.inventory = DEFAULT_INVENTORY.copy()
if "menu" not in st.session_state:
    st.session_state.menu = DEFAULT_MENU.copy()

def forecast_demand(sales_df, uplift=0):
    """Forecast demand using a transparent weighted average of recent sales."""
    values = pd.to_numeric(sales_df["Portions sold"], errors="coerce").dropna().tail(7)
    if values.empty:
        return 0
    weights = list(range(1, len(values) + 1))
    weighted = sum(v * w for v, w in zip(values.tolist(), weights)) / sum(weights)
    return max(0, round(weighted * (1 + uplift / 100)))

def calculate_inventory_capacity(inventory_df):
    capacities = []
    for _, row in inventory_df.iterrows():
        kg = max(0, float(row["Available quantity (kg)"]))
        per_portion = float(row["Kg per portion"])
        capacities.append(float("inf") if per_portion <= 0 else kg / per_portion)
    return min(capacities) if capacities else 0

def money(value):
    return f"${value:,.2f} CAD"

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 🍽️ Plateful")
    st.caption("Smarter preparation. Less waste.")
    page = st.radio("Workspace", ["Overview", "Sales & forecast", "Inventory", "Scenario planner", "Waste & insights"])
    st.divider()
    st.caption("DEMO WORKSPACE")
    st.caption("Sample figures are editable. Replace them with a vendor's real records before relying on the recommendations.")

# ---------- Shared calculations ----------
sales = st.session_state.sales.copy()
inventory = st.session_state.inventory.copy()
menu = st.session_state.menu.copy()
forecast = forecast_demand(sales)
capacity = calculate_inventory_capacity(inventory)
recommended = min(forecast, int(capacity)) if capacity != float("inf") else forecast
price = float(menu.iloc[0]["Selling price (CAD)"]) if not menu.empty else 0
other_cost = float(menu.iloc[0]["Other cost per portion (CAD)"]) if not menu.empty else 0
ingredient_cost = sum(float(r["Kg per portion"]) * float(r["Cost per kg (CAD)"]) for _, r in inventory.iterrows())
unit_cost = ingredient_cost + other_cost
expected_revenue = recommended * price
expected_cost = recommended * unit_cost
expected_profit = expected_revenue - expected_cost
shortages = inventory[inventory["Available quantity (kg)"] < inventory["Kg per portion"] * recommended] if not inventory.empty else inventory

# ---------- Header ----------
st.markdown("""
<div class="hero">
  <h1 style="margin:0">Plateful</h1>
  <p>Smarter preparation. Less waste.</p>
</div>
""", unsafe_allow_html=True)
st.write("")

if page == "Overview":
    st.subheader("Vendor overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Forecast demand", f"{forecast} portions")
    c2.metric("Recommended prep", f"{recommended} portions")
    c3.metric("Expected revenue", money(expected_revenue))
    c4.metric("Estimated profit", money(expected_profit), delta="before fixed overhead")
    left, right = st.columns([1.5, 1])
    with left:
        st.markdown("### Recent sales")
        chart = px.bar(sales, x="Date", y="Portions sold", color_discrete_sequence=["#28734e"])
        chart.update_layout(margin=dict(l=5, r=5, t=10, b=5), height=310, xaxis_title="", yaxis_title="Portions")
        st.plotly_chart(chart, use_container_width=True)
    with right:
        st.markdown("### Production check")
        st.metric("Ingredient capacity", f"{int(capacity) if capacity != float('inf') else '—'} portions")
        if forecast > capacity:
            st.warning(f"Current stock may support only {int(capacity)} portions. Review the inventory page.")
        else:
            st.success("Current inventory can support the forecast.")
        if len(shortages):
            st.markdown("**Ingredients to review**")
            for ingredient in shortages["Ingredient"].tolist():
                st.write(f"• {ingredient}")
        else:
            st.write("No ingredient shortages against the current recommendation.")
    st.info("This is a planning estimate, not a guaranteed demand prediction. Check local conditions and use your own sales records.")

elif page == "Sales & forecast":
    st.subheader("Sales history and demand forecast")
    st.write("Edit the sample sales below or paste in your own recent daily totals.")
    edited = st.data_editor(st.session_state.sales, num_rows="dynamic", use_container_width=True, key="sales_editor")
    if st.button("Save sales history", type="primary"):
        edited = edited.copy()
        edited["Portions sold"] = pd.to_numeric(edited["Portions sold"], errors="coerce").fillna(0).clip(lower=0)
        st.session_state.sales = edited
        st.success("Sales history updated.")
        st.rerun()
    st.divider()
    st.markdown("### Forecast method")
    st.write("LastPlate uses a weighted average of up to the seven most recent entries. More recent days receive more weight.")
    st.metric("Current estimated demand", f"{forecast} portions")
    st.caption("For a real business, add more history and account for holidays, weather, events, and weekday patterns before treating a forecast as reliable.")

elif page == "Inventory":
    st.subheader("Ingredient inventory")
    st.write("Enter stock on hand, the quantity needed for one portion, and the purchase cost per kilogram.")
    edited = st.data_editor(st.session_state.inventory, num_rows="dynamic", use_container_width=True, key="inventory_editor")
    if st.button("Save inventory", type="primary"):
        edited = edited.copy()
        for col in ["Available quantity (kg)", "Kg per portion", "Cost per kg (CAD)"]:
            edited[col] = pd.to_numeric(edited[col], errors="coerce").fillna(0).clip(lower=0)
        st.session_state.inventory = edited
        st.success("Inventory updated.")
        st.rerun()
    st.divider()
    st.markdown("### Stock required for the current recommendation")
    required = st.session_state.inventory.copy()
    required["Required for forecast (kg)"] = required["Kg per portion"] * recommended
    required["Surplus / shortage (kg)"] = required["Available quantity (kg)"] - required["Required for forecast (kg)"]
    st.dataframe(required, use_container_width=True, hide_index=True)
    st.caption("The demo assumes the listed ingredient quantities apply to one menu item.")

elif page == "Scenario planner":
    st.subheader("What-if scenario planner")
    st.write("Test how a change in expected demand affects preparation, stock, revenue, and estimated costs.")
    uplift = st.slider("Demand change", min_value=-50, max_value=100, value=20, step=5, format="%d%%")
    scenario_demand = forecast_demand(st.session_state.sales, uplift)
    scenario_prep = min(scenario_demand, int(capacity)) if capacity != float("inf") else scenario_demand
    s1, s2, s3 = st.columns(3)
    s1.metric("Scenario demand", f"{scenario_demand} portions")
    s2.metric("Can prepare now", f"{scenario_prep} portions", delta=f"{scenario_prep - recommended} vs. baseline")
    s3.metric("Estimated revenue", money(scenario_prep * price))
    st.markdown("### Scenario economics")
    st.write(f"Estimated ingredient and other variable cost: **{money(scenario_prep * unit_cost)}**")
    st.write(f"Estimated contribution after listed variable costs: **{money(scenario_prep * (price - unit_cost))}**")
    if scenario_prep < scenario_demand:
        st.warning(f"Potential stock gap: {scenario_demand - scenario_prep} portions. Review inventory or adjust the prep target.")
    else:
        st.success("Current stock covers this scenario's estimated demand.")
    st.caption("The slider changes the forecast for demonstration. It does not predict that demand will actually change.")

elif page == "Waste & insights":
    st.subheader("Waste and cost insights")
    st.write("Record estimated unsold portions to see their potential cost. These figures are manually entered, not sensor measurements.")
    unsold = st.number_input("Unsold portions from the last service", min_value=0, max_value=10000, value=8, step=1)
    waste_cost = unsold * unit_cost
    a, b, c = st.columns(3)
    a.metric("Unsold portions", f"{unsold}")
    b.metric("Estimated variable cost tied up", money(waste_cost))
    c.metric("Potential revenue not earned", money(unsold * price))
    st.divider()
    st.markdown("### Simple operating insight")
    if unsold == 0:
        st.success("No unsold portions were entered. Keep recording daily results to improve planning.")
    elif unsold <= max(1, round(forecast * 0.05)):
        st.success("Unsold portions are relatively low compared with the current forecast.")
    else:
        st.warning("Review the next prep estimate and compare it with actual sales. Avoid cutting production too sharply after one unusual day.")
    st.caption("This page estimates the cost of unsold portions using the entered per-portion cost. It is not an audited accounting report.")

# ---------- Exports ----------
st.divider()
st.markdown("#### Export your demo data")
export_col1, export_col2 = st.columns(2)
with export_col1:
    csv = st.session_state.sales.to_csv(index=False).encode("utf-8")
    st.download_button("Download sales CSV", data=csv, file_name="plateful_sales.csv", mime="text/csv")
with export_col2:
    csv = st.session_state.inventory.to_csv(index=False).encode("utf-8")
    st.download_button("Download inventory CSV", data=csv, file_name="plateful_inventory.csv", mime="text/csv")

st.caption("Plateful prototype • Streamlit + Python + Plotly • Demo data is stored in the current app session only.")
