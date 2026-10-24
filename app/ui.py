
import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")

st.set_page_config(
    page_title="RSG BI Assistant",
    page_icon="📊",
    layout="wide",
)

# Session state stores messages for display only.
if "messages" not in st.session_state:
    st.session_state.messages = []

if "clear_chat" not in st.session_state:
    st.session_state.clear_chat = False

if st.session_state.clear_chat:
    st.session_state.messages = []
    st.session_state.clear_chat = False

# Sidebar
with st.sidebar:
    st.title("📊 RSG BI")
    st.caption("Sales Intelligence Assistant")
    st.divider()

    st.subheader("Dataset overview")

    try:
        response = requests.get(
            f"{API_URL}/api/summary",
            timeout=(5, 15),
        )
        response.raise_for_status()
        summary = response.json()

        st.metric(
            "Net revenue",
            f"{summary['total_revenue']:,.2f}",
        )
        st.metric(
            "Included transactions",
            summary["included_transactions"],
        )
        st.metric(
            "Excluded transactions",
            summary["excluded_transactions"],
        )

    except requests.RequestException:
        st.warning("Could not load dataset metrics.")

    st.divider()
    st.subheader("Try asking")

    examples = [
        "What is the total revenue?",
        "Which product has the highest revenue?",
        "Show the monthly revenue trend.",
        "Which region has the highest revenue?",
        "What percentage increase was there from January to February 2026?",
        "Show the data quality report.",
    ]

    for example in examples:
        if st.button(example, use_container_width=True):
            st.session_state.pending_question = example

    st.divider()

    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.clear_chat = True
        st.rerun()

# Main chat area
st.title("Business Intelligence Assistant")
st.caption(
    "Ask questions about sales, revenue, products, regions, and trends."
)

# Render previous messages. These are visual history only.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message.get("details"):
            with st.expander("Analysis details"):
                st.json(message["details"])

# Handle example-question clicks.
pending_question = st.session_state.pop("pending_question", None)

question = st.chat_input("Ask a question about your sales data...")

if pending_question:
    question = pending_question

if question and question.strip():
    question = question.strip()

    # Show and store the user's message.
    st.session_state.messages.append({
        "role": "user",
        "content": question,
    })

    with st.chat_message("user"):
        st.markdown(question)

    # Call the Flask agent.
    with st.chat_message("assistant"):
        with st.spinner("Analyzing your sales data..."):
            try:
                response = requests.post(
                    f"{API_URL}/api/ask",
                    json={"question": question},
                    timeout=(5, 300),
                )

                response.raise_for_status()
                result = response.json()

                answer = result.get(
                    "answer",
                    "The API did not return an answer.",
                )

                st.markdown(answer)

                details = {
                    key: value
                    for key, value in result.items()
                    if key != "answer"
                }

                with st.expander("Analysis details"):
                    st.json(details)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "details": details,
                })

            except requests.Timeout:
                answer = (
                    "The request took too long. Please try again, "
                    "or check the Flask and Ollama logs."
                )

                st.error(answer)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                })

            except requests.RequestException as exc:
                answer = f"Could not reach the Flask API: {exc}"

                st.error(answer)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                })
