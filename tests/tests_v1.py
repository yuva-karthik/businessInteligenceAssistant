import pandas as pd
import pytest

from app.api import create_app


@pytest.fixture
def client(tmp_path):
    csv_path = tmp_path / "sales.csv"
    db_path = tmp_path / "sales.db"

    df = pd.DataFrame([
        [
            "T1", "03-01-2026", "Mouse", "Accessories",
            "North", "Online", 2, 100, 0, "Completed"
        ],
        [
            "T2", "05-01-2026", "Keyboard", "Accessories",
            "South", "Retail", 1, 300, 0, "Completed"
        ],
        [
            "T3", "08-02-2026", "Mouse", "Accessories",
            "North", "Online", 1, 100, 0, "Completed"
        ],
        [
            "T4", "09-02-2026", "Monitor", "Electronics",
            "West", "Retail", 1, 200, 0, "Returned"
        ],
    ], columns=[
        "Transaction_Id",
        "Order_date",
        "Product",
        "Category",
        "Region",
        "Sales_channel",
        "Quantity",
        "Unit_price",
        "Discount_amount",
        "Status",
    ])

    df.to_csv(csv_path, index=False)

    app = create_app({
        "TESTING": True,
        "CSV_PATH": str(csv_path),
        "DB_PATH": str(db_path),
    })

    return app.test_client()


def test_health(client):
    assert client.get("/health").status_code == 200


def test_summary(client):
    result = client.get("/api/summary").get_json()

    assert result["total_revenue"] == 600.0
    assert result["included_transactions"] == 3
    assert result["excluded_transactions"] == 1


def test_total_revenue(client):
    response = client.post(
        "/api/ask",
        json={"question": "What is the total revenue?"},
    )

    result = response.get_json()

    assert result["intent"] == "total_revenue"
    assert result["value"] == 600.0


def test_top_product(client):
    response = client.post(
        "/api/ask",
        json={"question": "Which product has the highest revenue?"},
    )

    assert response.get_json()["product"] == "Keyboard"


def test_monthly_trend(client):
    response = client.post(
        "/api/ask",
        json={"question": "Show monthly revenue trend"},
    )

    result = response.get_json()

    assert result["data"] == [
        {"month": "2026-01", "revenue": 500.0},
        {"month": "2026-02", "revenue": 100.0},
    ]


def test_top_region(client):
    response = client.post(
        "/api/ask",
        json={"question": "Which region has the highest sales?"},
    )

    assert response.get_json()["region"] == "South"


def test_month_comparison(client):
    response = client.post(
        "/api/ask",
        json={
            "question": (
                "Compare revenue between 2026-01 and 2026-02"
            )
        },
    )

    assert response.get_json()["difference"] == -400.0


def test_data_quality(client):
    response = client.post(
        "/api/ask",
        json={"question": "Show data quality report"},
    )

    result = response.get_json()

    assert result["included"] == 3
    assert result["excluded"] == 1


def test_invalid_requests(client):
    assert client.post("/api/ask", json={}).status_code == 400

    assert client.post(
        "/api/ask",
        json={"question": " "},
    ).status_code == 400


def test_unsupported_question(client):
    response = client.post(
        "/api/ask",
        json={"question": "What is the weather?"},
    )

    assert response.get_json()["intent"] == "unknown"