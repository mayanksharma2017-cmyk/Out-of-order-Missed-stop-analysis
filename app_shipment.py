import streamlit as st
import pandas as pd
import io
import sys

st.set_page_config(page_title="Shipment Milestone & Order Analysis", layout="wide")

st.title("🚚 Shipment Milestone & Order Analysis")
st.caption(f"Running Python version: {sys.version}")

st.markdown(
    "Upload your shipment Excel file (.xlsx) to analyze milestone completion, stop order, and carrier details."
)

uploaded_file = st.file_uploader("📤 Upload Excel file", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, engine="openpyxl")
    except ImportError:
        st.error("⚠️ Missing Excel reader dependency. Please ensure openpyxl is installed.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Failed to read Excel: {e}")
        st.stop()

    df.columns = [col.strip().lower() for col in df.columns]

    required_cols = [
        "shipment id",
        "stop type",
        "stop name",
        "stop country",
        "stop actual arrival time",
        "stop actual departure time",
        "current carrier",
    ]

    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        st.error(f"Missing columns: {', '.join(missing_cols)}")
        st.stop()

    results = []
    for shipment_id, group in df.groupby("shipment id"):
        group = group.sort_values(by="stop actual arrival time", na_position="last").reset_index(drop=True)

        arrival_missing = group["stop actual arrival time"].isna()
        departure_missing = group["stop actual departure time"].isna()
        all_missing = arrival_missing & departure_missing

        if all(all_missing):
            milestone_status = "No milestones received"
        elif any(all_missing):
            milestone_status = "Completed with missing milestones"
        else:
            milestone_status = "Completed with all milestones"

        if milestone_status == "No milestones received":
            out_of_order_status = "Not Applicable"
        else:
            times = group["stop actual arrival time"].dropna().tolist()
            out_of_order = any(times[i] > times[i + 1] for i in range(len(times) - 1))
            out_of_order_status = "Yes" if out_of_order else "No"

        num_stops = len(group)
        others = num_stops - 2 if num_stops > 2 else 0
        intended_order = (
            "Origin → "
            + " → ".join([f"Stop{i+1}" for i in range(others)])
            + " → Destination"
            if others > 0 else "Origin → Destination"
        )

        visited_group = group.dropna(subset=["stop actual arrival time"])
        stop_types = visited_group["stop type"].tolist()

        actual_labels = []
        stop_counter = 1
        for s in stop_types:
            if s.lower() == "origin":
                actual_labels.append("Origin")
            elif s.lower() == "destination":
                actual_labels.append("Destination")
            else:
                actual_labels.append(f"Stop{stop_counter}")
                stop_counter += 1
        exact_order = " → ".join(actual_labels) if actual_labels else "—"

        missed = group.loc[
            group["stop actual arrival time"].isna() | group["stop actual departure time"].isna(),
            "stop name",
        ].tolist()
        missed_stops = ", ".join(map(str, missed)) if missed else "—"

        origin_row = group[group["stop type"].str.upper() == "ORIGIN"].head(1)
        origin_location = origin_row["stop name"].iloc[0] if not origin_row.empty else "—"
        carrier = group["current carrier"].iloc[0]

        results.append({
            "Shipment ID": shipment_id,
            "Origin Location": origin_location,
            "Number of Stops": num_stops,
            "Carrier": carrier,
            "Milestone Status": milestone_status,
            "Out of Order": out_of_order_status,
            "Intended Order": intended_order,
            "Exact Order": exact_order,
            "Missed Stops": missed_stops,
        })

    result_df = pd.DataFrame(results)
    for col in ["Intended Order", "Exact Order"]:
        result_df[col] = result_df[col].astype(str)

    st.subheader("📊 Analysis Results")
    st.dataframe(result_df, use_container_width=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        result_df.to_excel(writer, index=False, sheet_name="Shipment Analysis")
    st.download_button(
        label="📥 Download Analyzed Excel",
        data=output.getvalue(),
        file_name="shipment_analysis_output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
