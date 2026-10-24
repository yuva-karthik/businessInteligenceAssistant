import re

from app import analytics


MONTH_NAMES = {
    "january": "01", "jan": "01",
    "february": "02", "feb": "02",
    "march": "03", "mar": "03",
    "april": "04", "apr": "04",
    "may": "05",
    "june": "06", "jun": "06",
    "july": "07", "jul": "07",
    "august": "08", "aug": "08",
    "september": "09", "sep": "09",
    "october": "10", "oct": "10",
    "november": "11", "nov": "11",
    "december": "12", "dec": "12",
}


def extract_months(question):
    q = question.lower()
    found = []

    # Examples: 2026-01 and 2026/01
    for year, month in re.findall(
        r"\b(20\d{2})[-/](0?[1-9]|1[0-2])\b",
        q,
    ):
        found.append(f"{year}-{int(month):02d}")

    # Examples: March 2026 and January 2026
    for name, month_number in MONTH_NAMES.items():
        years = re.findall(
            rf"\b{name}\s+(20\d{{2}})\b",
            q,
        )

        for year in years:
            found.append(f"{year}-{month_number}")

    return list(dict.fromkeys(found))


def answer_question(question, db_path=None):
    q = " ".join(question.lower().strip().split())

    if not q:
        return {
            "intent": "unknown",
            "answer": "Please enter a question.",
        }

    # Data quality questions
    if re.search(
        r"\b(data quality|data cleaning|excluded rows|"
        r"invalid rows|missing values|cleaning report)\b",
        q,
    ):
        return analytics.data_quality(db_path)

    # Month-to-month comparisons
    if re.search(
        r"\b(compare|comparison|change|difference|increase|"
        r"decrease|month.to.month|month over month|mom)\b",
        q,
    ):
        months = extract_months(q)

        if len(months) >= 2:
            return analytics.compare_months(
                months[0],
                months[1],
                db_path,
            )

        return {
            "intent": "revenue_comparison",
            "answer": (
                "Please specify two months, for example: "
                "'Compare revenue between 2026-01 and 2026-02'."
            ),
        }

    # Top region
    if (
        re.search(r"\b(top|highest|best|leading)\b", q)
        and re.search(r"\b(region|area|territory)\b", q)
    ):
        return analytics.top_region(db_path)

    # Top product
    if (
        re.search(r"\b(top|highest|best|leading|most)\b", q)
        and re.search(r"\b(product|item|sku)\b", q)
    ):
        return analytics.top_product(db_path)

    # Monthly revenue trend
    if (
        re.search(r"\b(monthly|month|trend|over time|by month)\b", q)
        and re.search(r"\b(revenue|sales|trend|month)\b", q)
    ):
        return analytics.monthly_trend(db_path)

    # Total revenue
    if (
        re.search(
            r"\b(total|overall|sum|how much|revenue|sales)\b",
            q,
        )
        and re.search(
            r"\b(revenue|sales|earned|generate|generated|"
            r"income|turnover|total)\b",
            q,
        )
    ):
        return analytics.total_revenue(db_path)

    return {
        "intent": "unknown",
        "answer": (
            "I can answer questions about total revenue, top product, "
            "monthly revenue trend, highest-revenue region, comparing "
            "two months, and data quality. Try one of those."
        ),
    }