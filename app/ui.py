import os

import requests
import streamlit as st


API_URL = os.getenv(
    "API_URL",
    "http://127.0.0.1:5000",
)

st.set_page_config(
    page_title="RSG BI Assistant V1",
    layout="wide",
)

st.title(" Mini Business Intelligence Assistant")


with st.sidebar:
    st.subheader("Example questions")

    examples = [
        "What is the total revenue?",
        "Which product has the highest revenue?",
        "Show monthly revenue trend",
        "Which region has the highest sales?",
        "Compare revenue between 2026-01 and 2026-02",
        "Show the data quality report",
    ]

    selected = st.selectbox(
        "Choose an example",
        examples,
    )

    if st.button("Use example"):
        st.session_state["question"] = selected

try:
    response = requests.get(
        f"{API_URL}/api/summary",
        timeout=3,
    )
    response.raise_for_status()

    data = response.json()

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total net revenue",
        f"{data['total_revenue']:,.2f}",
    )

    col2.metric(
        "Included transactions",
        data["included_transactions"],
    )

    col3.metric(
        "Excluded transactions",
        data["excluded_transactions"],
    )

except requests.RequestException:
    st.warning(
        "Flask API is not responding. "
        "Start it using: python -m app.api"
    )

question = st.text_input(
    "Ask a sales question",
    key="question",
    placeholder="e.g. Which product has the highest revenue?",
)

if st.button("Ask", type="primary"):
    if not question.strip():
        st.warning("Enter a question first.")
    else:
        try:
            response = requests.post(
                f"{API_URL}/api/ask",
                json={"question": question},
                timeout=10,
            )

            if response.ok:
                result = response.json()

                st.subheader("Answer")
                st.write(result["answer"])

                if result.get("intent") == "monthly_trend":
                    chart_data = result.get("data", [])

                    if chart_data:
                        st.bar_chart({
                            item["month"]: item["revenue"]
                            for item in chart_data
                        })

                with st.expander("View structured result"):
                    st.json(result)

            else:
                st.error(response.text)

        except requests.RequestException as exc:
            st.error(f"Could not reach Flask API: {exc}")

st.divider()

st.caption(
    "Revenue = quantity × unit price − discount. "
    "Only valid completed transactions are included."
)