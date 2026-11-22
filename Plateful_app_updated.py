import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from pathlib import Path
from datetime import date

# ============================================================
# PLATEFUL | BAKERY DATA ANALYSIS
# Keep this file in the same folder as the six supplied data files.
# ============================================================

st.set_page_config(
    page_title="Plateful | Production Planner",
    page_icon="🍽️",
    layout="wide"
)

DATA_DIR = Path(__file__).resolve().parent

# ---------- Styling: preserves the original Plateful design ----------
st.markdown("""
<style>
    .block-container {padding-top: 1.8rem; padding-bottom: 2rem;}
    [data-testid="stMetric"] {background: #f4f7f3; padding: 14px 16px; border-radius: 12px;}
    .hero {padding: 1.3rem 1.5rem; border-radius: 16px; background: linear-gradient(110deg,#123b2b,#28734e); color:white;}
    .hero p {color:#e4f1e8; margin-bottom:0;}
    .small-note {color:#64748b; font-size:0.88rem;}
</style>
""", unsafe_allow_html=True)


# ---------- Helpers ----------
def find_file(filename):
    """Find a data file beside this script, ignoring capitalization."""
    target = filename.lower()
    for path in DATA_DIR.iterdir():
        if path.is_file() and path.name.lower() == target:
            return path
    return None


def read_csv_optional(filename):
    path = find_file(filename)
    if path is None:
        return None
    # utf-8-sig handles CSVs saved by Excel with a byte-order mark.
    return pd.read_csv(path, encoding="utf-8-sig")


def read_workbook():
    path = find_file("lastplate_bakery_data.xlsx")
    if path is None:
        return {}
    try:
        return pd.read_excel(path, sheet_name=None)
    except Exception as exc:
        st.warning(f"Could not read the Excel workbook: {exc}")
        return {}


def clean_columns(df):
    if df is None:
        return None
    result = df.copy()
    result.columns = [str(c).strip() for c in result.columns]
    return result


def choose_data(csv_name, workbook_sheets, sheet_name):
    """Prefer the standalone CSV; use a matching workbook sheet if absent."""
    frame = read_csv_optional(csv_name)
    if frame is not None:
        return clean_columns(frame)
    for key, value in workbook_sheets.items():
        if key.strip().lower() == sheet_name.lower():
            return clean_columns(value)
    return None


def rename_known_columns(df, mapping):
    """Rename source columns to the canonical names used by the app."""
    if df is None:
        return None
    lookup = {str(c).strip().lower(): c for c in df.columns}
    rename = {}
    for canonical, aliases in mapping.items():
        for alias in aliases:
            if alias.lower() in lookup:
                rename[lookup[alias.lower()]] = canonical
                break
    return df.rename(columns=rename)


def to_number(series, default=0):
    return pd.to_numeric(series, errors="coerce").fillna(default)


def money(value):
    return f"${value:,.2f} CAD"


def safe_sum(frame, column):
    return float(to_number(frame[column]).sum()) if column in frame.columns else 0.0


def format_date_column(series):
    return pd.to_datetime(series, errors="coerce")


# ---------- Load all supplied data ----------
workbook = read_workbook()

sales_raw = choose_data("daily_sales.csv", workbook, "Daily_Sales")
ingredients_raw = choose_data("ingredients.csv", workbook, "Ingredients")
menu_raw = choose_data("menu_items.csv", workbook, "Menu")
recipes_raw = choose_data("recipes.csv", workbook, "Recipes")
answer_raw = read_csv_optional("simulation_answer_key.csv")

if sales_raw is None or ingredients_raw is None or menu_raw is None or recipes_raw is None:
    missing = []
    for filename, frame in [
        ("daily_sales.csv", sales_raw),
        ("ingredients.csv", ingredients_raw),
        ("menu_items.csv", menu_raw),
        ("recipes.csv", recipes_raw),
    ]:
        if frame is None:
            missing.append(filename)
    st.error(
        "Plateful could not find these required data files: "
        + ", ".join(missing)
        + ". Put them in the same folder as Plateful_app.py, or make sure "
          "the Excel workbook contains the corresponding sheets."
    )
    st.stop()

# Standardize the source columns. The aliases accommodate the column names
# described in the supplied dataset documentation.
sales = rename_known_columns(sales_raw, {
    "date": ["date"],
    "food_item": ["food_item", "food item", "menu item"],
    "portions_prepared": ["portions_prepared", "portions prepared"],
    "portions_sold": ["portions_sold", "portions sold"],
    "portions_unsold": ["portions_unsold", "portions unsold"],
    "sold_out": ["sold_out", "sold out"],
    "selling_price_cad": ["selling_price_cad", "selling price cad"],
    "revenue_cad": ["revenue_cad", "revenue cad"],
    "promotion": ["promotion"],
    "special_event": ["special_event", "special event"],
    "holiday": ["holiday"],
    "weather": ["weather"],
    "temp_c": ["temp_c", "temperature_c", "temperature"],
    "day_of_week": ["day_of_week", "day of week"],
    "unsold_discarded": ["unsold_discarded", "unsold discarded"],
    "unsold_donated": ["unsold_donated", "unsold donated"],
    "unsold_reused": ["unsold_reused", "unsold reused"],
    "waste_reason": ["waste_reason", "waste reason"],
    "unsold_cost_cad": ["unsold_cost_cad", "unsold cost cad"],
})

ingredients = rename_known_columns(ingredients_raw, {
    "ingredient": ["ingredient"],
    "unit": ["unit"],
    "current_stock": ["current_stock", "current stock"],
    "reorder_level": ["reorder_level", "reorder level"],
    "cost_per_unit_cad": ["cost_per_unit_cad", "cost per unit cad"],
    "supplier": ["supplier"],
    "lead_time_days": ["lead_time_days", "lead time days"],
    "shelf_life_days": ["shelf_life_days", "shelf life days"],
    "expiration_date": ["expiration_date", "expiration date", "expiry_date"],
    "price_basis": ["price_basis", "price basis"],
})

menu = rename_known_columns(menu_raw, {
    "food_item": ["food_item", "food item", "menu item"],
    "category": ["category"],
    "selling_price_cad": ["selling_price_cad", "selling price cad"],
    "ingredient_cost_per_portion_cad": ["ingredient_cost_per_portion_cad", "ingredient cost per portion cad"],
    "other_variable_cost_cad": ["other_variable_cost_cad", "other variable cost cad"],
    "total_variable_cost_cad": ["total_variable_cost_cad", "total variable cost cad"],
    "ingredient_cost_pct_of_price": ["ingredient_cost_pct_of_price", "ingredient cost pct of price"],
    "batch_size": ["batch_size", "batch size"],
    "shelf_life_days": ["shelf_life_days", "shelf life days"],
})

recipes = rename_known_columns(recipes_raw, {
    "food_item": ["food_item", "food item", "menu item"],
    "ingredient": ["ingredient"],
    "quantity_per_portion": ["quantity_per_portion", "quantity per portion"],
    "unit": ["unit"],
    "readable_amount": ["readable_amount", "readable amount"],
})

# Required columns and numeric/date cleanup.
required_columns = {
    "sales": ["date", "food_item", "portions_prepared", "portions_sold"],
    "ingredients": ["ingredient", "unit", "current_stock", "cost_per_unit_cad"],
    "menu": ["food_item", "selling_price_cad"],
    "recipes": ["food_item", "ingredient", "quantity_per_portion", "unit"],
}
for label, frame, required in [
    ("daily sales", sales, required_columns["sales"]),
    ("ingredients", ingredients, required_columns["ingredients"]),
    ("menu items", menu, required_columns["menu"]),
    ("recipes", recipes, required_columns["recipes"]),
]:
    absent = [col for col in required if col not in frame.columns]
    if absent:
        st.error(f"The {label} data is missing required column(s): {', '.join(absent)}.")
        st.stop()

sales["date"] = format_date_column(sales["date"])
sales = sales.dropna(subset=["date", "food_item"]).copy()
for col in [
    "portions_prepared", "portions_sold", "portions_unsold",
    "selling_price_cad", "revenue_cad", "temp_c",
    "unsold_discarded", "unsold_donated", "unsold_reused", "unsold_cost_cad"
]:
    if col in sales.columns:
        sales[col] = to_number(sales[col])

sales["food_item"] = sales["food_item"].astype(str).str.strip()
ingredients["ingredient"] = ingredients["ingredient"].astype(str).str.strip()
menu["food_item"] = menu["food_item"].astype(str).str.strip()
recipes["food_item"] = recipes["food_item"].astype(str).str.strip()
recipes["ingredient"] = recipes["ingredient"].astype(str).str.strip()

for col in ["current_stock", "reorder_level", "cost_per_unit_cad", "lead_time_days", "shelf_life_days"]:
    if col in ingredients.columns:
        ingredients[col] = to_number(ingredients[col])
for col in [
    "selling_price_cad", "ingredient_cost_per_portion_cad",
    "other_variable_cost_cad", "total_variable_cost_cad",
    "batch_size", "shelf_life_days"
]:
    if col in menu.columns:
        menu[col] = to_number(menu[col])
recipes["quantity_per_portion"] = to_number(recipes["quantity_per_portion"])

# If unsold quantity is missing, derive it from prepared minus sold.
if "portions_unsold" not in sales.columns:
    sales["portions_unsold"] = (
        sales["portions_prepared"] - sales["portions_sold"]
    ).clip(lower=0)
else:
    missing_unsold = sales["portions_unsold"].isna()
    sales.loc[missing_unsold, "portions_unsold"] = (
        sales.loc[missing_unsold, "portions_prepared"]
        - sales.loc[missing_unsold, "portions_sold"]
    ).clip(lower=0)

# Revenue fallback if source data does not contain it.
if "revenue_cad" not in sales.columns:
    price_map = menu.set_index("food_item")["selling_price_cad"].to_dict()
    sales["revenue_cad"] = sales.apply(
        lambda r: r["portions_sold"] * price_map.get(r["food_item"], 0), axis=1
    )

# Answer key is deliberately kept separate from the forecasting inputs.
if answer_raw is not None:
    answer = rename_known_columns(answer_raw, {
        "date": ["date"],
        "food_item": ["food_item", "food item"],
        "simulated_true_demand": ["simulated_true_demand", "simulated true demand"],
    })
    if all(c in answer.columns for c in ["date", "food_item", "simulated_true_demand"]):
        answer["date"] = format_date_column(answer["date"])
        answer["food_item"] = answer["food_item"].astype(str).str.strip()
        answer["simulated_true_demand"] = to_number(answer["simulated_true_demand"])
        answer = answer.dropna(subset=["date", "food_item"])
    else:
        answer = None
else:
    answer = None


# ---------- Derived calculations ----------
products = sorted(menu["food_item"].dropna().unique().tolist())
ingredients_list = sorted(ingredients["ingredient"].dropna().unique().tolist())

menu_lookup = menu.drop_duplicates("food_item").set_index("food_item").to_dict("index")
ingredient_lookup = ingredients.drop_duplicates("ingredient").set_index("ingredient").to_dict("index")


def product_history(product):
    return sales[sales["food_item"] == product].sort_values("date").copy()


def forecast_product(product, days=7):
    """Weighted average of recent observed sales; never reads the answer key."""
    history = product_history(product)
    if history.empty:
        return 0
    values = history["portions_sold"].tail(days).astype(float).tolist()
    if not values:
        return 0
    weights = np.arange(1, len(values) + 1, dtype=float)
    estimate = float(np.average(values, weights=weights))
    # Sold-out days are censored observations: actual demand may have been higher.
    # We flag them for the user rather than pretending observed sales equal demand.
    return max(0, int(round(estimate)))


def calculate_requirements(production_plan):
    """Aggregate ingredient needs across every product in the production plan."""
    plan = {str(k): max(0, float(v)) for k, v in production_plan.items()}
    needs = {}
    for _, recipe_row in recipes.iterrows():
        product = recipe_row["food_item"]
        ingredient = recipe_row["ingredient"]
        portions = plan.get(product, 0)
        needs[ingredient] = needs.get(ingredient, 0.0) + (
            portions * float(recipe_row["quantity_per_portion"])
        )
    return needs


def get_plan_inventory_table(production_plan):
    needs = calculate_requirements(production_plan)
    rows = []
    for _, row in ingredients.iterrows():
        name = row["ingredient"]
        required = needs.get(name, 0.0)
        stock = float(row["current_stock"])
        rows.append({
            "Ingredient": name,
            "Unit": row["unit"],
            "Current stock": stock,
            "Required": required,
            "Surplus / shortage": stock - required,
            "Cost per unit (CAD)": float(row["cost_per_unit_cad"]),
        })
    return pd.DataFrame(rows)


def estimate_plan_economics(production_plan):
    revenue = 0.0
    variable_cost = 0.0
    for product, quantity in production_plan.items():
        details = menu_lookup.get(product, {})
        revenue += quantity * float(details.get("selling_price_cad", 0) or 0)
        variable_cost += quantity * float(details.get("total_variable_cost_cad", 0) or 0)
    return revenue, variable_cost, revenue - variable_cost


# Default product-level forecasts and prep plan.
baseline_forecasts = {p: forecast_product(p) for p in products}
baseline_plan = baseline_forecasts.copy()
baseline_revenue, baseline_cost, baseline_contribution = estimate_plan_economics(baseline_plan)
baseline_inventory = get_plan_inventory_table(baseline_plan)
baseline_shortages = baseline_inventory[baseline_inventory["Surplus / shortage"] < 0]


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 🍽️ Plateful")
    st.caption("Smarter preparation. Less waste.")
    page = st.radio(
        "Workspace",
        ["Overview", "Sales & forecast", "Inventory", "Scenario planner", "Waste & insights"]
    )
    st.divider()
    st.caption("LASTPLATE BAKERY DATA")
    st.caption("Simulated dataset • CAD • 2026")
    st.caption(f"{len(products)} products • {len(ingredients)} ingredients")


# ---------- Header ----------
st.markdown("""
<div class="hero">
  <h1 style="margin:0">Plateful</h1>
  <p>Smarter preparation. Less waste.</p>
</div>
""", unsafe_allow_html=True)
st.write("")


# ============================================================
# OVERVIEW
# ============================================================
if page == "Overview":
    st.subheader("Bakery overview")

    total_sold = safe_sum(sales, "portions_sold")
    total_revenue = safe_sum(sales, "revenue_cad")
    total_unsold = safe_sum(sales, "portions_unsold")
    total_waste_cost = safe_sum(sales, "unsold_cost_cad")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portions sold", f"{total_sold:,.0f}")
    c2.metric("Historical revenue", money(total_revenue))
    c3.metric("Unsold portions", f"{total_unsold:,.0f}")
    c4.metric("Recorded waste cost", money(total_waste_cost))

    left, right = st.columns([1.5, 1])
    with left:
        st.markdown("### Daily sales")
        daily = sales.groupby("date", as_index=False).agg(
            portions_sold=("portions_sold", "sum")
        )
        chart = px.line(
            daily, x="date", y="portions_sold",
            color_discrete_sequence=["#28734e"], markers=True
        )
        chart.update_layout(
            margin=dict(l=5, r=5, t=10, b=5), height=310,
            xaxis_title="", yaxis_title="Portions sold"
        )
        st.plotly_chart(chart, use_container_width=True)

    with right:
        st.markdown("### Product performance")
        product_totals = sales.groupby("food_item", as_index=False).agg(
            portions_sold=("portions_sold", "sum"),
            revenue_cad=("revenue_cad", "sum")
        ).sort_values("revenue_cad", ascending=False)
        st.dataframe(
            product_totals.rename(columns={
                "food_item": "Product",
                "portions_sold": "Portions sold",
                "revenue_cad": "Revenue (CAD)"
            }),
            use_container_width=True, hide_index=True
        )

    st.markdown("### Production check")
    a, b, c = st.columns(3)
    a.metric("Forecast portions", f"{sum(baseline_forecasts.values()):,.0f}")
    a.caption("Sum of product-level forecasts")
    b.metric("Estimated contribution", money(baseline_contribution))
    b.caption("Before fixed overhead")
    c.metric("Ingredient shortages", f"{len(baseline_shortages)}")
    c.caption("Against the baseline production plan")

    if len(baseline_shortages):
        st.warning(
            "The baseline forecast exceeds current stock for: "
            + ", ".join(baseline_shortages["Ingredient"].tolist())
            + ". Review the Inventory or Scenario planner page."
        )
    else:
        st.success("Current stock covers the baseline forecast according to the recipe data.")

    st.info(
        "This dataset is simulated, not actual bakery operating data. "
        "Forecasts use recorded sales only; sold-out days can understate customer demand."
    )


# ============================================================
# SALES & FORECAST
# ============================================================
elif page == "Sales & forecast":
    st.subheader("Sales history and demand forecast")

    selected_product = st.selectbox("Choose a product", ["All products"] + products)

    if selected_product == "All products":
        view = sales.copy()
        forecast_total = sum(baseline_forecasts.values())
        st.metric("Combined estimated daily demand", f"{forecast_total} portions")
        product_daily = view.groupby("date", as_index=False).agg(
            portions_sold=("portions_sold", "sum")
        )
        chart = px.line(
            product_daily, x="date", y="portions_sold",
            markers=True, color_discrete_sequence=["#28734e"]
        )
        chart.update_layout(height=320, xaxis_title="", yaxis_title="Portions sold")
        st.plotly_chart(chart, use_container_width=True)
    else:
        view = product_history(selected_product)
        estimate = baseline_forecasts[selected_product]
        st.metric("Estimated demand for next service", f"{estimate} portions")

        chart = px.line(
            view, x="date", y="portions_sold",
            markers=True, color_discrete_sequence=["#28734e"]
        )
        if "portions_prepared" in view.columns:
            chart.add_scatter(
                x=view["date"], y=view["portions_prepared"],
                mode="lines", name="Prepared", line=dict(dash="dash")
            )
        chart.update_layout(height=320, xaxis_title="", yaxis_title="Portions")
        st.plotly_chart(chart, use_container_width=True)

        sold_out_days = 0
        if "sold_out" in view.columns:
            sold_out_days = int(view["sold_out"].astype(str).str.lower().isin(["true", "1", "yes"]).sum())
        elif "portions_prepared" in view.columns:
            sold_out_days = int((view["portions_sold"] >= view["portions_prepared"]).sum())
        st.caption(
            f"{len(view)} recorded days • {sold_out_days} possible sold-out days. "
            "Sales on sold-out days may be lower than true demand."
        )

    st.divider()
    st.markdown("### Forecast method")
    st.write(
        "The baseline forecast is a weighted average of up to seven recent daily sales observations. "
        "Recent observations receive more weight. The answer key is not used to generate this forecast."
    )

    # Answer-key evaluation, if the full answer-key CSV is available.
    st.markdown("### Forecast evaluation against simulated true demand")
    if answer is not None:
        evaluation = sales.merge(
            answer[["date", "food_item", "simulated_true_demand"]],
            on=["date", "food_item"], how="inner"
        )
        if not evaluation.empty:
            # One-step-ahead forecast for each product/day using only earlier sales.
            evaluation = evaluation.sort_values(["food_item", "date"]).copy()
            predicted = []
            for product, group in evaluation.groupby("food_item", sort=False):
                history = product_history(product).sort_values("date")
                for current_date in group["date"]:
                    earlier = history[history["date"] < current_date]["portions_sold"].tail(7)
                    if earlier.empty:
                        predicted.append(np.nan)
                    else:
                        vals = earlier.astype(float).tolist()
                        weights = np.arange(1, len(vals) + 1, dtype=float)
                        predicted.append(float(np.average(vals, weights=weights)))
            evaluation["forecast"] = predicted
            scored = evaluation.dropna(subset=["forecast"]).copy()
            if not scored.empty:
                scored["absolute_error"] = (
                    scored["forecast"] - scored["simulated_true_demand"]
                ).abs()
                scored["signed_error"] = (
                    scored["forecast"] - scored["simulated_true_demand"]
                )
                m1, m2, m3 = st.columns(3)
                m1.metric("Evaluated days", f"{len(scored):,}")
                m2.metric("Mean absolute error", f"{scored['absolute_error'].mean():.1f} portions")
                m3.metric("Mean forecast bias", f"{scored['signed_error'].mean():+.1f} portions")
                st.caption(
                    "Positive forecast bias means the model overestimated demand on average; "
                    "negative bias means it underestimated demand."
                )
                if selected_product != "All products":
                    scored = scored[scored["food_item"] == selected_product]
                if not scored.empty:
                    evaluation_chart = px.scatter(
                        scored, x="simulated_true_demand", y="forecast",
                        color="food_item", hover_data=["date"],
                        labels={
                            "simulated_true_demand": "Simulated true demand",
                            "forecast": "Forecast"
                        }
                    )
                    evaluation_chart.update_layout(height=320)
                    st.plotly_chart(evaluation_chart, use_container_width=True)
                st.dataframe(
                    scored[["date", "food_item", "forecast", "simulated_true_demand", "absolute_error"]]
                    .rename(columns={
                        "date": "Date", "food_item": "Product",
                        "forecast": "Forecast", "simulated_true_demand": "True demand",
                        "absolute_error": "Absolute error"
                    }),
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("There is not enough earlier sales history to score the answer-key dates.")
        else:
            st.info(
                "The answer key was found, but its dates/products did not match the sales file. "
                "Check that both files use the same date format and product names."
            )
    else:
        st.info(
            "No usable simulation_answer_key.csv was found. Forecasting still works, "
            "but forecast accuracy evaluation requires that file with date, food_item, "
            "and simulated_true_demand columns."
        )

    st.divider()
    st.markdown("### Historical sales records")
    display_columns = [
        c for c in [
            "date", "food_item", "portions_prepared", "portions_sold",
            "portions_unsold", "sold_out", "revenue_cad", "weather",
            "promotion", "special_event", "holiday"
        ] if c in sales.columns
    ]
    st.dataframe(
        sales[display_columns].sort_values("date", ascending=False),
        use_container_width=True, hide_index=True
    )


# ============================================================
# INVENTORY
# ============================================================
elif page == "Inventory":
    st.subheader("Ingredient inventory")
    st.write("Stock and purchasing information from the supplied ingredients dataset.")

    inventory_view = ingredients.copy()
    inventory_view["Stock status"] = np.where(
        inventory_view["current_stock"] < inventory_view.get("reorder_level", 0),
        "Below reorder level", "At / above reorder level"
    )
    if "expiration_date" in inventory_view.columns:
        inventory_view["expiration_date"] = pd.to_datetime(
            inventory_view["expiration_date"], errors="coerce"
        )

    i1, i2, i3 = st.columns(3)
    i1.metric("Ingredients tracked", f"{len(ingredients)}")
    i2.metric(
        "Below reorder level",
        f"{int((inventory_view['Stock status'] == 'Below reorder level').sum())}"
    )
    i3.metric(
        "Estimated stock value",
        money((ingredients["current_stock"] * ingredients["cost_per_unit_cad"]).sum())
    )

    st.markdown("### Current stock")
    display_inventory = inventory_view.rename(columns={
        "ingredient": "Ingredient",
        "unit": "Unit",
        "current_stock": "Current stock",
        "reorder_level": "Reorder level",
        "cost_per_unit_cad": "Cost per unit (CAD)",
        "supplier": "Supplier",
        "lead_time_days": "Lead time (days)",
        "shelf_life_days": "Shelf life (days)",
        "expiration_date": "Expiration date",
        "price_basis": "Price basis",
    })
    st.dataframe(display_inventory, use_container_width=True, hide_index=True)

    low_stock = inventory_view[inventory_view["Stock status"] == "Below reorder level"]
    if not low_stock.empty:
        st.warning(
            "Reorder review recommended: "
            + ", ".join(low_stock["ingredient"].tolist())
        )
    else:
        st.success("All listed ingredients are at or above their reorder levels.")

    if "expiration_date" in inventory_view.columns:
        today = pd.Timestamp(date.today())
        soon = inventory_view[
            inventory_view["expiration_date"].notna()
            & (inventory_view["expiration_date"] <= today + pd.Timedelta(days=14))
        ]
        if not soon.empty:
            st.markdown("### Expiring within 14 days or already expired")
            st.dataframe(
                soon[["ingredient", "expiration_date", "current_stock", "unit"]],
                use_container_width=True, hide_index=True
            )

    st.divider()
    st.markdown("### Ingredient requirements for baseline forecasts")
    baseline_requirements = get_plan_inventory_table(baseline_plan)
    st.dataframe(baseline_requirements, use_container_width=True, hide_index=True)
    st.caption(
        "Requirements are calculated by multiplying each product's forecast portions "
        "by its recipe quantities, then summing shared ingredients across all products."
    )


# ============================================================
# SCENARIO PLANNER
# ============================================================
elif page == "Scenario planner":
    st.subheader("What-if scenario planner")
    st.write(
        "Adjust the production quantity for each product. Plateful will aggregate "
        "the ingredient requirements across the entire bakery."
    )

    uplift = st.slider(
        "Demand adjustment applied to baseline forecasts",
        min_value=-50, max_value=100, value=0, step=5, format="%d%%"
    )

    suggested = {
        product: max(0, int(round(baseline_forecasts[product] * (1 + uplift / 100))))
        for product in products
    }

    st.markdown("### Production plan")
    production_plan = {}
    cols = st.columns(2)
    for index, product in enumerate(products):
        details = menu_lookup.get(product, {})
        batch = max(1, int(details.get("batch_size", 1) or 1))
        with cols[index % 2]:
            production_plan[product] = st.number_input(
                f"{product} (portions)",
                min_value=0, max_value=10000,
                value=min(10000, suggested[product]),
                step=batch,
                key=f"production_{product}"
            )

    revenue, variable_cost, contribution = estimate_plan_economics(production_plan)
    requirements = get_plan_inventory_table(production_plan)
    shortages = requirements[requirements["Surplus / shortage"] < -1e-9]

    s1, s2, s3 = st.columns(3)
    s1.metric("Planned portions", f"{sum(production_plan.values()):,}")
    s2.metric("Estimated revenue", money(revenue))
    s3.metric("Estimated contribution", money(contribution), delta="before fixed overhead")

    st.markdown("### Ingredient requirements")
    st.dataframe(requirements, use_container_width=True, hide_index=True)

    if not shortages.empty:
        st.warning(
            "This plan exceeds available stock for: "
            + ", ".join(shortages["Ingredient"].tolist())
            + ". Reduce production or plan a purchase."
        )
    else:
        st.success("Current stock covers the selected production plan.")

    st.markdown("### Product-level economics")
    economics_rows = []
    for product, quantity in production_plan.items():
        details = menu_lookup.get(product, {})
        price = float(details.get("selling_price_cad", 0) or 0)
        unit_cost = float(details.get("total_variable_cost_cad", 0) or 0)
        economics_rows.append({
            "Product": product,
            "Planned portions": quantity,
            "Selling price (CAD)": price,
            "Variable cost / portion (CAD)": unit_cost,
            "Revenue (CAD)": quantity * price,
            "Contribution (CAD)": quantity * (price - unit_cost),
        })
    st.dataframe(pd.DataFrame(economics_rows), use_container_width=True, hide_index=True)
    st.caption(
        "Product costs use the menu dataset's listed variable costs. Labour, rent, "
        "utilities, and other fixed overhead are not included in the dataset."
    )


# ============================================================
# WASTE & INSIGHTS
# ============================================================
elif page == "Waste & insights":
    st.subheader("Waste and operating insights")
    st.write("Explore unsold portions, their disposition, and potential cost.")

    total_unsold = safe_sum(sales, "portions_unsold")
    discarded = safe_sum(sales, "unsold_discarded")
    donated = safe_sum(sales, "unsold_donated")
    reused = safe_sum(sales, "unsold_reused")
    waste_cost = safe_sum(sales, "unsold_cost_cad")

    a, b, c, d = st.columns(4)
    a.metric("Unsold portions", f"{total_unsold:,.0f}")
    b.metric("Discarded", f"{discarded:,.0f}")
    c.metric("Donated", f"{donated:,.0f}")
    d.metric("Reused", f"{reused:,.0f}")

    w1, w2 = st.columns(2)
    with w1:
        st.markdown("### Unsold portions by disposition")
        disposition = pd.DataFrame({
            "Disposition": ["Discarded", "Donated", "Reused"],
            "Portions": [discarded, donated, reused]
        })
        disposition = disposition[disposition["Portions"] > 0]
        if not disposition.empty:
            fig = px.pie(
                disposition, names="Disposition", values="Portions",
                color_discrete_sequence=["#28734e", "#83b89a", "#c8dfcf"]
            )
            fig.update_layout(height=300, margin=dict(l=5, r=5, t=10, b=5))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No disposition data is available.")
    with w2:
        st.markdown("### Waste by product")
        waste_by_product = sales.groupby("food_item", as_index=False).agg(
            portions_unsold=("portions_unsold", "sum"),
            unsold_cost_cad=("unsold_cost_cad", "sum")
        ) if "unsold_cost_cad" in sales.columns else sales.groupby(
            "food_item", as_index=False
        ).agg(portions_unsold=("portions_unsold", "sum"))
        fig = px.bar(
            waste_by_product, x="food_item", y="portions_unsold",
            color_discrete_sequence=["#28734e"]
        )
        fig.update_layout(height=300, xaxis_title="", yaxis_title="Unsold portions")
        st.plotly_chart(fig, use_container_width=True)

    st.metric("Recorded cost of unsold portions", money(waste_cost))

    st.divider()
    st.markdown("### Waste over time")
    waste_daily = sales.groupby("date", as_index=False).agg(
        portions_unsold=("portions_unsold", "sum")
    )
    fig = px.line(
        waste_daily, x="date", y="portions_unsold",
        markers=True, color_discrete_sequence=["#28734e"]
    )
    fig.update_layout(height=300, xaxis_title="", yaxis_title="Unsold portions")
    st.plotly_chart(fig, use_container_width=True)

    if "weather" in sales.columns:
        st.markdown("### Unsold portions by weather")
        weather_waste = sales.groupby("weather", as_index=False).agg(
            average_unsold=("portions_unsold", "mean"),
            records=("portions_unsold", "size")
        ).sort_values("average_unsold", ascending=False)
        st.dataframe(
            weather_waste.rename(columns={
                "weather": "Weather",
                "average_unsold": "Average unsold portions",
                "records": "Records"
            }),
            use_container_width=True, hide_index=True
        )

    st.caption(
        "Waste cost is taken from the supplied dataset where available. "
        "Discarded, donated, and reused portions are different outcomes and should not "
        "automatically be treated as identical financial losses."
    )


# ---------- Exports ----------
st.divider()
st.markdown("#### Export bakery data")
export_col1, export_col2, export_col3 = st.columns(3)

with export_col1:
    st.download_button(
        "Download sales CSV",
        data=sales.to_csv(index=False).encode("utf-8"),
        file_name="plateful_sales.csv",
        mime="text/csv"
    )
with export_col2:
    st.download_button(
        "Download inventory CSV",
        data=ingredients.to_csv(index=False).encode("utf-8"),
        file_name="plateful_inventory.csv",
        mime="text/csv"
    )
with export_col3:
    st.download_button(
        "Download menu CSV",
        data=menu.to_csv(index=False).encode("utf-8"),
        file_name="plateful_menu.csv",
        mime="text/csv"
    )

st.caption(
    "Plateful prototype • Streamlit + Python + Plotly • "
    "Data loaded locally from the files beside this app."
)
