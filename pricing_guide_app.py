import streamlit as st
import pandas as pd
import altair as alt
from PIL import Image, ImageDraw

st.set_page_config(page_title="CATS Pricing Guide", layout="wide")

FILE_PATH = "CAA Pricing Guide DC PA 01012025 to 02282026 Cleaned.xlsx"
SHEET_NAME = "Worksheet"

import base64

def make_svg_thumbnail_data_uri():
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" width="120" height="72" viewBox="0 0 120 72">
      <rect width="120" height="72" fill="#f2f2f2" stroke="#c8c8c8"/>
      <rect x="8" y="8" width="104" height="56" rx="6" fill="#e9e9e9" stroke="#d0d0d0"/>
      <text x="60" y="30" font-size="11" text-anchor="middle" fill="#666" font-family="Arial">No Image</text>
      <text x="60" y="47" font-size="10" text-anchor="middle" fill="#888" font-family="Arial">Vehicle</text>
    </svg>
    """
    encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"

def normalize_trim_value(val):
    if pd.isna(val) or str(val).strip() == "" or str(val).strip().lower() == "none":
        return "Base"
    return str(val)

def reset_all_filters():
    # Main filter widgets
    st.session_state["filter_vin"] = ""
    st.session_state["filter_location"] = []
    st.session_state["filter_year"] = []
    st.session_state["filter_make"] = []
    st.session_state["filter_model"] = []
    st.session_state["filter_trim"] = []
    st.session_state["filter_status"] = []

    # Range fields
    st.session_state["filter_mileage_start"] = 0
    st.session_state["filter_mileage_end"] = 999999

    if "Sold Price" in df.columns and df["Sold Price"].notna().any():
        st.session_state["filter_price_start"] = int(df["Sold Price"].min())
        st.session_state["filter_price_end"] = int(df["Sold Price"].max())

    if "Date Sold" in df.columns and df["Date Sold"].notna().any():
        st.session_state["filter_date"] = (
            df["Date Sold"].min().date(),
            df["Date Sold"].max().date()
        )

    # Viewer / selection state
    st.session_state["show_viewer"] = False
    st.session_state["viewer_index"] = 0
    st.session_state["last_selected_row"] = ()

    # Reset dependency tracking
    for key in [
        "previous_filter_year",
        "previous_filter_make",
        "previous_filter_model",
        "previous_filter_trim",
        "last_filter_state",
    ]:
        if key in st.session_state:
            del st.session_state[key]

@st.cache_data
def load_data():
    df = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME)
    df.columns = df.columns.str.strip()

    numeric_cols = [
        "Sold Price",
        "B Price Wholesale",
        "B Price Trade-In",
        "B Price Retail",
        "Mileage",
        "Year",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "Date Sold" in df.columns:
        df["Date Sold"] = pd.to_datetime(df["Date Sold"], errors="coerce")

    if "Trim" in df.columns:
        df["Trim"] = df["Trim"].apply(normalize_trim_value)

    if "Stock Number" in df.columns:
        stock = df["Stock Number"].where(df["Stock Number"].notna(), "").astype(str).str.strip()
        df["Stock Number"] = stock
        first_char = stock.str[0].str.upper()
        df["Location"] = first_char.map({
            "D": "DC",
            "P": "PA",
            "N": "NH",
        }).fillna("Other")
    else:
        df["Location"] = "Unknown"

    return df

def format_date_mmddyyyy(series):
    return series.dt.strftime("%m/%d/%Y").fillna("")

def safe_sorted_options(series, col_name=None):
    vals = [x for x in series.dropna().unique()]

    if col_name == "Year":
        vals = [str(int(x)) for x in vals if pd.notna(x)]
        return sorted(vals, key=lambda x: int(x), reverse=True)

    return sorted(vals, key=lambda x: str(x).strip().lower())

def format_currency(x):
    return f"${x:,.0f}" if pd.notna(x) else "N/A"

def format_number(x):
    return f"{x:,.0f}" if pd.notna(x) else "N/A"

def get_vin_decode_values(vin_text):
    """
    Placeholder for future VIN decoder integration.
    Return a dict like:
    {
        "Year": 2022,
        "Make": "Toyota",
        "Model": "Camry",
        "Trim": "SE"
    }
    """
    return {}

def get_period_subset(data, days):
    if "Date Sold" not in data.columns or data["Date Sold"].dropna().empty:
        return data.iloc[0:0].copy()

    max_date = data["Date Sold"].max()
    start_date = max_date - pd.Timedelta(days=days)
    return data[data["Date Sold"] >= start_date].copy()

def historical_summary(data):
    periods = {
        "Past 30 Days": 30,
        "Past 3 Months": 90,
        "Past 6 Months": 180,
        "Past 12 Months": 365,
    }

    rows = []
    for label, days in periods.items():
        subset = get_period_subset(data, days)
        rows.append({
            "Period": label,
            "Number of Vehicles": len(subset),
            "Average Sold Price": subset["Sold Price"].mean() if "Sold Price" in subset.columns else None,
            "Average B Price Wholesale": subset["B Price Wholesale"].mean() if "B Price Wholesale" in subset.columns else None,
            "Average B Price Trade-In": subset["B Price Trade-In"].mean() if "B Price Trade-In" in subset.columns else None,
            "Average B Price Retail": subset["B Price Retail"].mean() if "B Price Retail" in subset.columns else None,
        })

    return pd.DataFrame(rows)

def make_placeholder_thumbnail(row, width=360, height=220):
    img = Image.new("RGB", (width, height), color=(242, 242, 242))
    draw = ImageDraw.Draw(img)

    year = "" if pd.isna(row.get("Year")) else str(int(row.get("Year")))
    make = "" if pd.isna(row.get("Make")) else str(row.get("Make"))
    model = "" if pd.isna(row.get("Model")) else str(row.get("Model"))
    stock = "" if pd.isna(row.get("Stock Number")) else str(row.get("Stock Number"))
    location = "" if pd.isna(row.get("Location")) else str(row.get("Location"))

    draw.rectangle([0, 0, width - 1, height - 1], outline=(180, 180, 180), width=2)
    draw.text((16, 20), "No Vehicle Image", fill=(70, 70, 70))
    draw.text((16, 70), f"{year} {make}".strip()[:30], fill=(20, 20, 20))
    draw.text((16, 105), model[:30], fill=(20, 20, 20))
    draw.text((16, 140), f"Stock: {stock}"[:30], fill=(20, 20, 20))
    draw.text((16, 175), f"Location: {location}"[:30], fill=(20, 20, 20))

    return img

def row_to_display_dict(row):
    out = {}
    for col, val in row.items():
        if pd.isna(val):
            out[col] = ""
        elif col == "Date Sold" and isinstance(val, pd.Timestamp):
            out[col] = val.strftime("%m/%d/%Y")
        elif col in ["Sold Price", "B Price Wholesale", "B Price Trade-In", "B Price Retail"]:
            out[col] = f"${int(round(val)):,}"
        elif col == "Year":
            out[col] = f"{int(val)}"
        elif isinstance(val, (int, float)) and col != "Trim":
            out[col] = f"{int(round(val)):,}"
        else:
            out[col] = str(val)
    return out

def extract_check_engine_light(text):
    if pd.isna(text):
        return None

    text = str(text).strip()
    if not text:
        return None

    upper_text = text.upper()
    marker = "CHECK ENGINE LIGHT:"

    if marker in upper_text:
        start_idx = upper_text.find(marker)
        return text[start_idx + len(marker):].strip(" -:;,")

    return None

def clean_text_value(text):
    if pd.isna(text):
        return ""

    text = str(text).strip()
    if text.lower() == "none":
        return ""

    return text

def remove_check_engine_from_condition_report(text):
    text = clean_text_value(text)
    if not text:
        return ""

    upper_text = text.upper()
    marker = "CHECK ENGINE LIGHT:"
    if marker in upper_text:
        idx = upper_text.find(marker)
        return text[:idx].strip(" -:;,")
    return text

def render_text_section(title, value):
    value = clean_text_value(value)
    if not value:
        return

    st.markdown(f"**{title}:**")
    st.write(value)

df = load_data()

if "viewer_index" not in st.session_state:
    st.session_state.viewer_index = 0

if "show_viewer" not in st.session_state:
    st.session_state.show_viewer = False

DEPENDENCY_KEYS = {
    "filter_year": ["filter_make", "filter_model", "filter_trim", "filter_status"],
    "filter_make": ["filter_model", "filter_trim", "filter_status"],
    "filter_model": ["filter_trim", "filter_status"],
    "filter_trim": ["filter_status"],
}

def reset_downstream_filters(changed_key):
    for key in DEPENDENCY_KEYS.get(changed_key, []):
        if key in st.session_state:
            st.session_state[key] = []

def handle_filter_change(changed_key):
    current_value = tuple(st.session_state.get(changed_key, []))
    previous_key = f"previous_{changed_key}"

    if previous_key not in st.session_state:
        st.session_state[previous_key] = current_value
    elif st.session_state[previous_key] != current_value:
        reset_downstream_filters(changed_key)
        st.session_state[previous_key] = current_value
        st.session_state.show_viewer = False

@st.dialog("Vehicle Viewer", width="large")
def show_vehicle_popup():
    if len(filtered_df) == 0:
        st.info("No vehicles match the selected filters.")
        st.session_state.show_viewer = False
        return

    idx = max(0, min(st.session_state.viewer_index, len(filtered_df) - 1))
    st.session_state.viewer_index = idx

    current_row = filtered_df.iloc[st.session_state.viewer_index]
    current_display = row_to_display_dict(current_row)

    left, middle, right = st.columns([1.05, 0.9, 1.05])

    with left:
        st.image(make_placeholder_thumbnail(current_row), use_container_width=True)

        nav_left, nav_mid, nav_right = st.columns([1, 1, 1])

        with nav_left:
            if st.button("◀", key="popup_prev_arrow", use_container_width=True):
                if st.session_state.viewer_index > 0:
                    st.session_state.viewer_index -= 1
                    st.rerun()

        with nav_mid:
            st.markdown(
                f"<div style='text-align:center; padding-top:8px; font-weight:600;'>"
                f"{st.session_state.viewer_index + 1} / {len(filtered_df):,}"
                f"</div>",
                unsafe_allow_html=True
            )

        with nav_right:
            if st.button("▶", key="popup_next_arrow", use_container_width=True):
                if st.session_state.viewer_index < len(filtered_df) - 1:
                    st.session_state.viewer_index += 1
                    st.rerun()

    with middle:
        info_fields = [
            "VIN", "Stock Number", "Year", "Make", "Model", "Trim",
            "Mileage", "Vehicle Status", "Sold Price", "B Price Wholesale",
            "B Price Trade-In", "B Price Retail", "Location"
        ]

        info_rows = []
        for field in info_fields:
            if field in current_display:
                info_rows.append({"Field": field, "Value": current_display[field]})

        st.dataframe(
            pd.DataFrame(info_rows),
            use_container_width=True,
            hide_index=True
        )

    with right:
        condition_report_raw = current_row.get("Condition Report")
        condition_report_clean = remove_check_engine_from_condition_report(condition_report_raw)
        check_engine_light = extract_check_engine_light(condition_report_raw)

        render_text_section("Condition Notes", condition_report_clean)
        render_text_section("Carfax Notes", current_row.get("Carfax notes"))
        render_text_section("Title Announcements", current_row.get("Title Announcements"))
        render_text_section("Auction Announcements", current_row.get("Auction Announcements"))
        render_text_section("Check Engine Light", check_engine_light)

st.title("CATS Pricing Guide")

st.subheader("Filters")

top_btn_col1, top_btn_col2 = st.columns([1, 6])
with top_btn_col1:
    if st.button("Reset Filters", use_container_width=True):
        reset_all_filters()
        st.rerun()

vin_input = st.text_input("VIN", value="", key="filter_vin").strip().upper()

base_df = df.copy()

c1, c2, c3, c4, c5, c6 = st.columns(6)

with c1:
    location_options = safe_sorted_options(base_df["Location"], "Location") if "Location" in base_df.columns else []
    selected_locations = st.multiselect("Location", location_options, key="filter_location")

df_after_location = base_df.copy()
if selected_locations:
    df_after_location = df_after_location[df_after_location["Location"].isin(selected_locations)]

with c2:
    year_options = safe_sorted_options(df_after_location["Year"], "Year") if "Year" in df_after_location.columns else []
    selected_years = st.multiselect("Year", year_options, key="filter_year")
    handle_filter_change("filter_year")

df_after_year = df_after_location.copy()
if selected_years:
    selected_years_numeric = [pd.to_numeric(x, errors="coerce") for x in selected_years]
    df_after_year = df_after_year[df_after_year["Year"].isin(selected_years_numeric)]

with c3:
    make_options = safe_sorted_options(df_after_year["Make"], "Make") if "Make" in df_after_year.columns else []
    selected_makes = st.multiselect("Make", make_options, key="filter_make")
    handle_filter_change("filter_make")

df_after_make = df_after_year.copy()
if selected_makes:
    df_after_make = df_after_make[df_after_make["Make"].isin(selected_makes)]

with c4:
    model_options = safe_sorted_options(df_after_make["Model"], "Model") if "Model" in df_after_make.columns else []
    selected_models = st.multiselect("Model", model_options, key="filter_model")
    handle_filter_change("filter_model")

df_after_model = df_after_make.copy()
if selected_models:
    df_after_model = df_after_model[df_after_model["Model"].isin(selected_models)]

with c5:
    trim_options = safe_sorted_options(df_after_model["Trim"], "Trim") if "Trim" in df_after_model.columns else []
    selected_trims = st.multiselect("Trim", trim_options, key="filter_trim")
    handle_filter_change("filter_trim")

df_after_trim = df_after_model.copy()
if selected_trims:
    df_after_trim = df_after_trim[df_after_trim["Trim"].isin(selected_trims)]

with c6:
    status_options = safe_sorted_options(df_after_trim["Vehicle Status"], "Vehicle Status") if "Vehicle Status" in df_after_trim.columns else []
    selected_statuses = st.multiselect("Vehicle Status", status_options, key="filter_status")

g1, g2, g3 = st.columns(3)

with g1:
    mileage_col1, mileage_col2 = st.columns(2)
    with mileage_col1:
        mileage_start = st.number_input(
            "Mileage From",
            min_value=0,
            max_value=99999999,
            value=0,
            step=1000,
            key="filter_mileage_start"
        )
    with mileage_col2:
        mileage_end = st.number_input(
            "Mileage To",
            min_value=0,
            max_value=99999999,
            value=999999,
            step=1000,
            key="filter_mileage_end"
        )

with g2:
    if "Sold Price" in df.columns and df["Sold Price"].notna().any():
        min_price = int(df["Sold Price"].min())
        max_price = int(df["Sold Price"].max())

        price_col1, price_col2 = st.columns(2)
        with price_col1:
            sold_price_start = st.number_input(
                "Sold Price From",
                min_value=min_price,
                max_value=max_price,
                value=min_price,
                step=100,
                key="filter_price_start"
            )
        with price_col2:
            sold_price_end = st.number_input(
                "Sold Price To",
                min_value=min_price,
                max_value=max_price,
                value=max_price,
                step=100,
                key="filter_price_end"
            )
    else:
        sold_price_start = None
        sold_price_end = None
        min_price = 0
        max_price = 0

with g3:
    if "Date Sold" in df.columns and df["Date Sold"].notna().any():
        min_date = df["Date Sold"].min().date()
        max_date = df["Date Sold"].max().date()
        date_range = st.date_input(
            "Date Sold Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            format="MM/DD/YYYY",
            key="filter_date"
        )
    else:
        date_range = None

vin_decoded = get_vin_decode_values(vin_input) if vin_input else {}

filtered_df = df.copy()

if vin_decoded:
    if vin_decoded.get("Year") is not None and "Year" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Year"] == vin_decoded["Year"]]

    if vin_decoded.get("Make") and "Make" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Make"] == vin_decoded["Make"]]

    if vin_decoded.get("Model") and "Model" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Model"] == vin_decoded["Model"]]

    if vin_decoded.get("Trim") and "Trim" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Trim"] == normalize_trim_value(vin_decoded["Trim"])]

if selected_locations:
    filtered_df = filtered_df[filtered_df["Location"].isin(selected_locations)]

if selected_years:
    selected_years_numeric = [pd.to_numeric(x, errors="coerce") for x in selected_years]
    filtered_df = filtered_df[filtered_df["Year"].isin(selected_years_numeric)]

if selected_makes:
    filtered_df = filtered_df[filtered_df["Make"].isin(selected_makes)]

if selected_models:
    filtered_df = filtered_df[filtered_df["Model"].isin(selected_models)]

if selected_trims:
    selected_trims_normalized = [normalize_trim_value(x) for x in selected_trims]
    filtered_df = filtered_df[filtered_df["Trim"].isin(selected_trims_normalized)]

if selected_statuses:
    filtered_df = filtered_df[filtered_df["Vehicle Status"].isin(selected_statuses)]

range_error = False

if mileage_start > mileage_end:
    st.error("Mileage From cannot be greater than Mileage To.")
    range_error = True

if sold_price_start is not None and sold_price_end is not None and sold_price_start > sold_price_end:
    st.error("Sold Price From cannot be greater than Sold Price To.")
    range_error = True

if not range_error:
    if "Mileage" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["Mileage"].isna() |
            (filtered_df["Mileage"] < 0) |
            (filtered_df["Mileage"] > 99999999) |
            filtered_df["Mileage"].between(mileage_start, mileage_end, inclusive="both")
        ]

    if sold_price_start is not None and sold_price_end is not None and "Sold Price" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["Sold Price"].isna() |
            filtered_df["Sold Price"].between(sold_price_start, sold_price_end, inclusive="both")
        ]

if date_range and isinstance(date_range, tuple) and len(date_range) == 2 and "Date Sold" in filtered_df.columns:
    start_date, end_date = date_range
    filtered_df = filtered_df[
        filtered_df["Date Sold"].isna() |
        (
            (filtered_df["Date Sold"].dt.date >= start_date) &
            (filtered_df["Date Sold"].dt.date <= end_date)
        )
    ]

current_filter_state = {
    "location": tuple(st.session_state.get("filter_location", [])),
    "year": tuple(st.session_state.get("filter_year", [])),
    "make": tuple(st.session_state.get("filter_make", [])),
    "model": tuple(st.session_state.get("filter_model", [])),
    "trim": tuple(st.session_state.get("filter_trim", [])),
    "status": tuple(st.session_state.get("filter_status", [])),
    "vin": st.session_state.get("filter_vin", ""),
    "mileage_start": st.session_state.get("filter_mileage_start", 0),
    "mileage_end": st.session_state.get("filter_mileage_end", 999999),
    "price_start": st.session_state.get("filter_price_start", min_price) if "Sold Price" in df.columns and df["Sold Price"].notna().any() else None,
    "price_end": st.session_state.get("filter_price_end", max_price) if "Sold Price" in df.columns and df["Sold Price"].notna().any() else None,
    "date": tuple(st.session_state.get("filter_date", (min_date, max_date))) if "Date Sold" in df.columns and df["Date Sold"].notna().any() else (),
}

if "last_filter_state" not in st.session_state:
    st.session_state.last_filter_state = current_filter_state
else:
    if st.session_state.last_filter_state != current_filter_state:
        st.session_state.show_viewer = False
        st.session_state.last_filter_state = current_filter_state

sample_count = len(filtered_df)
avg_sold_price = filtered_df["Sold Price"].mean() if "Sold Price" in filtered_df.columns else None
avg_b_price = filtered_df["B Price Wholesale"].mean() if "B Price Wholesale" in filtered_df.columns else None
avg_b_price_trade_in = filtered_df["B Price Trade-In"].mean() if "B Price Trade-In" in filtered_df.columns else None
avg_b_price_retail = filtered_df["B Price Retail"].mean() if "B Price Retail" in filtered_df.columns else None
avg_mileage = filtered_df["Mileage"].mean() if "Mileage" in filtered_df.columns else None

highest_sold_price = filtered_df["Sold Price"].max() if "Sold Price" in filtered_df.columns and filtered_df["Sold Price"].notna().any() else None
lowest_sold_price = filtered_df["Sold Price"].min() if "Sold Price" in filtered_df.columns and filtered_df["Sold Price"].notna().any() else None

m1, m2, m3, m4 = st.columns(4)
m1.metric("Number of Samples", f"{sample_count:,}")
m2.metric("Average Sold Price", format_currency(avg_sold_price))
m3.metric("Average B Price Wholesale", format_currency(avg_b_price))
m4.metric("Average Mileage", format_number(avg_mileage))

m5, m6, m7, m8 = st.columns(4)
m5.metric("Average B Price Trade-In (not real data)", format_currency(avg_b_price_trade_in))
m6.metric("Average B Price Retail (not real data)", format_currency(avg_b_price_retail))
m7.metric("Highest Sold Price", format_currency(highest_sold_price))
m8.metric("Lowest Sold Price", format_currency(lowest_sold_price))

st.subheader("Historical Average")

hist_df = historical_summary(filtered_df)
hist_display = hist_df.copy()

hist_display["Number of Vehicles"] = hist_display["Number of Vehicles"].apply(lambda x: f"{int(x):,}")
hist_display["Average Sold Price"] = hist_display["Average Sold Price"].apply(format_currency)
hist_display["Average B Price Wholesale"] = hist_display["Average B Price Wholesale"].apply(format_currency)
hist_display["Average B Price Trade-In"] = hist_display["Average B Price Trade-In"].apply(format_currency)
hist_display["Average B Price Retail"] = hist_display["Average B Price Retail"].apply(format_currency)

hist_display = hist_display.set_index("Period").T.reset_index()
hist_display = hist_display.rename(columns={"index": "Metric"})

st.dataframe(hist_display, use_container_width=True, hide_index=True)

st.subheader("Vehicles by Sold Price Range")

chart_df = filtered_df[filtered_df["Sold Price"].notna()].copy()

if not chart_df.empty:
    bucket_size = 500
    chart_df["bucket_start"] = (chart_df["Sold Price"] // bucket_size) * bucket_size

    bucket_counts = (
        chart_df.groupby("bucket_start", as_index=False)
        .size()
        .rename(columns={"size": "Number of Vehicles"})
        .sort_values("bucket_start")
    )

    bucket_counts["bucket_end"] = bucket_counts["bucket_start"] + bucket_size
    bucket_counts["Sold Price Range"] = bucket_counts.apply(
        lambda r: f"${int(r['bucket_start']):,}-${int(r['bucket_end'] - 1):,}",
        axis=1
    )

    chart = (
        alt.Chart(bucket_counts)
        .mark_bar()
        .encode(
            x=alt.X("bucket_start:Q", title="Sold Price", axis=alt.Axis(format="$,.0f")),
            x2="bucket_end:Q",
            y=alt.Y("Number of Vehicles:Q", title="Number of Vehicles"),
            tooltip=[
                alt.Tooltip("Sold Price Range:N"),
                alt.Tooltip("Number of Vehicles:Q", format=",")
            ],
        )
        .properties(height=400)
    )

    st.altair_chart(chart, use_container_width=True)
else:
    st.info("No sold price data available for the chart.")

st.subheader("Search Results")

display_df = filtered_df.reset_index(drop=True).copy()

thumbnail_uri = make_svg_thumbnail_data_uri()
display_df.insert(0, "Thumbnail", thumbnail_uri)

if "Date Sold" in display_df.columns:
    display_df["Date Sold"] = format_date_mmddyyyy(display_df["Date Sold"])

for col in display_df.columns:
    if col in ["Sold Price", "B Price Wholesale", "B Price Trade-In", "B Price Retail"]:
        if pd.api.types.is_numeric_dtype(display_df[col]):
            display_df[col] = display_df[col].apply(lambda x: f"${int(x):,}" if pd.notna(x) else "")
    elif col == "Year":
        if pd.api.types.is_numeric_dtype(display_df[col]):
            display_df[col] = display_df[col].apply(lambda x: f"{int(x)}" if pd.notna(x) else "")
    elif col not in ["Trim", "Thumbnail"]:
        if pd.api.types.is_numeric_dtype(display_df[col]):
            display_df[col] = display_df[col].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "")

event = st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "Thumbnail": st.column_config.ImageColumn("Image", width="small"),
        "Carfax notes": st.column_config.TextColumn("Carfax notes", width="medium", max_chars=80),
        "Condition Report": st.column_config.TextColumn("Condition Report", width="large", max_chars=120),
        "Title Announcements": st.column_config.TextColumn("Title Announcements", width="medium", max_chars=60),
        "Auction Announcements": st.column_config.TextColumn("Auction Announcements", width="medium", max_chars=60),
    },
    column_order=["Thumbnail"] + [c for c in display_df.columns if c != "Thumbnail"]
)

selected_rows = event.selection.rows if event and event.selection else []

current_selected_row = tuple(selected_rows)

if "last_selected_row" not in st.session_state:
    st.session_state.last_selected_row = ()

if current_selected_row and current_selected_row != st.session_state.last_selected_row:
    st.session_state.viewer_index = selected_rows[0]
    st.session_state.show_viewer = True

st.session_state.last_selected_row = current_selected_row

if st.session_state.show_viewer:
    show_vehicle_popup()
