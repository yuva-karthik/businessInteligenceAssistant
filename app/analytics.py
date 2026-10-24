from app.database import connect


def scalar(conn, sql, params=()):
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else None


def summary(db_path=None):
    with connect(db_path) as conn:
        return {
            "total_transactions": scalar(
                conn, "SELECT COUNT(*) FROM sales"
            ),
            "included_transactions": scalar(
                conn,
                "SELECT COUNT(*) FROM sales WHERE included = 1",
            ),
            "excluded_transactions": scalar(
                conn,
                "SELECT COUNT(*) FROM sales WHERE included = 0",
            ),
            "total_revenue": scalar(
                conn,
                """
                SELECT ROUND(COALESCE(SUM(net_revenue), 0), 2)
                FROM sales
                WHERE included = 1
                """,
            ),
        }


def total_revenue(db_path=None):
    with connect(db_path) as conn:
        value = scalar(
            conn,
            """
            SELECT ROUND(COALESCE(SUM(net_revenue), 0), 2)
            FROM sales
            WHERE included = 1
            """,
        )

    return {
        "intent": "total_revenue",
        "answer": f"Total net revenue is {value:,.2f}.",
        "value": value,
    }


def top_product(db_path=None):
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT Product, ROUND(SUM(net_revenue), 2) AS revenue
            FROM sales
            WHERE included = 1
            GROUP BY Product
            ORDER BY revenue DESC, Product ASC
            LIMIT 1
            """
        ).fetchone()

    if not row:
        return {
            "intent": "top_product",
            "answer": "No included sales data was found.",
        }

    return {
        "intent": "top_product",
        "answer": (
            f"{row['Product']} has the highest revenue "
            f"at {row['revenue']:,.2f}."
        ),
        "product": row["Product"],
        "value": row["revenue"],
    }


def monthly_trend(db_path=None):
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT month, ROUND(SUM(net_revenue), 2) AS revenue
            FROM sales
            WHERE included = 1
            GROUP BY month
            ORDER BY month
            """
        ).fetchall()

    data = [
        {
            "month": row["month"],
            "revenue": row["revenue"],
        }
        for row in rows
    ]

    answer = "Monthly net revenue: " + (
        "; ".join(
            f"{item['month']}: {item['revenue']:,.2f}"
            for item in data
        )
        if data
        else "no included sales data found."
    )

    return {
        "intent": "monthly_trend",
        "answer": answer,
        "data": data,
    }


def top_region(db_path=None):
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT Region, ROUND(SUM(net_revenue), 2) AS revenue
            FROM sales
            WHERE included = 1
            GROUP BY Region
            ORDER BY revenue DESC, Region ASC
            LIMIT 1
            """
        ).fetchone()

    if not row:
        return {
            "intent": "top_region",
            "answer": "No included sales data was found.",
        }

    return {
        "intent": "top_region",
        "answer": (
            f"{row['Region']} is the highest-revenue region "
            f"at {row['revenue']:,.2f}."
        ),
        "region": row["Region"],
        "value": row["revenue"],
    }


def compare_months(month_a, month_b, db_path=None):
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT month, ROUND(SUM(net_revenue), 2) AS revenue
            FROM sales
            WHERE included = 1 AND month IN (?, ?)
            GROUP BY month
            """,
            (month_a, month_b),
        ).fetchall()

    values = {
        row["month"]: row["revenue"]
        for row in rows
    }

    revenue_a = values.get(month_a, 0)
    revenue_b = values.get(month_b, 0)

    difference = round(revenue_b - revenue_a, 2)

    if revenue_a == 0:
        percentage = None
        percentage_text = (
            "percentage change is undefined because "
            "the first month's revenue is zero"
        )
    else:
        percentage = round(
            difference / revenue_a * 100,
            2,
        )
        percentage_text = f"{percentage:+.2f}%"

    return {
        "intent": "revenue_comparison",
        "answer": (
            f"Revenue changed from {month_a} ({revenue_a:,.2f}) "
            f"to {month_b} ({revenue_b:,.2f}). "
            f"Difference: {difference:+,.2f}; "
            f"{percentage_text}."
        ),
        "months": [
            {"month": month_a, "revenue": revenue_a},
            {"month": month_b, "revenue": revenue_b},
        ],
        "difference": difference,
        "percentage_change": percentage,
    }


def data_quality(db_path=None):
    with connect(db_path) as conn:
        total = scalar(
            conn, "SELECT COUNT(*) FROM sales"
        ) or 0

        included = scalar(
            conn,
            "SELECT COUNT(*) FROM sales WHERE included = 1",
        ) or 0

        rows = conn.execute(
            """
            SELECT exclusion_reason, COUNT(*) AS count
            FROM sales
            WHERE included = 0
            GROUP BY exclusion_reason
            ORDER BY count DESC, exclusion_reason
            """
        ).fetchall()

    reasons = [
        {
            "reason": row["exclusion_reason"],
            "count": row["count"],
        }
        for row in rows
    ]

    details = "; ".join(
        f"{item['reason']}: {item['count']}"
        for item in reasons
    ) or "none"

    return {
        "intent": "data_quality",
        "answer": (
            f"{included} of {total} transactions are included; "
            f"{total - included} are excluded. "
            f"Exclusion reasons: {details}."
        ),
        "total": total,
        "included": included,
        "excluded": total - included,
        "reasons": reasons,
    }