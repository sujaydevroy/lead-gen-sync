from __future__ import annotations

from pathlib import Path

from tests.conftest import VIEWER_PASSWORD, login

SAMPLE = Path(__file__).resolve().parents[3] / "sample_sales.xlsx"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def upload(client, content=None, name="sample_sales.xlsx"):
    return client.post("/api/v1/sales/uploads", files={"file": (name, content or SAMPLE.read_bytes(), XLSX)})


def test_upload_returns_redux_shape(auth_client):
    response = upload(auth_client)
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {"uploadId", "uploadedData", "processedData", "fileMetadata"}
    assert len(body["processedData"]) == 30 and len(body["uploadedData"]["rows"]) == 30
    assert body["uploadedData"]["headers"][0] == "CustomerName"
    first = body["processedData"][0]
    assert first == {
        "id": "S-2",
        "rowNumber": 2,
        "customerName": "Al Mansoori Trading LLC",
        "country": "United Arab Emirates",
        "location": "Dubai",
        "year": 2025,
        "month": 1,
        "period": "2025-01",
        "product": "Unmanufactured Tobacco (FCV Leaf)",
        "unit": "MT",
        "quantity": 120.0,
        "amount": 468000.0,
        "currency": "USD",
    }
    meta = body["fileMetadata"]
    assert meta["name"] == "sample_sales.xlsx" and meta["validRows"] == 30 and meta["skippedRows"] == 0

    reopened = auth_client.get(f"/api/v1/sales/uploads/{body['uploadId']}").json()
    assert reopened["processedData"] == body["processedData"]
    assert reopened["uploadedData"]["headers"] == body["uploadedData"]["headers"]
    assert any(u["uploadId"] == body["uploadId"] for u in auth_client.get("/api/v1/sales/uploads").json())


def test_sample_endpoint_and_rejections(auth_client):
    sample = auth_client.post("/api/v1/sales/uploads/sample")
    assert sample.status_code == 201 and sample.json()["fileMetadata"]["name"] == "sample_sales.xlsx (demo data)"
    assert upload(auth_client, b"a,b\n1,2\n", "sales.csv").status_code == 415
    corrupt = upload(auth_client, b"PK\x03\x04 definitely not a workbook", "sales.xlsx")
    assert corrupt.status_code == 422


def test_analytics_and_forecast_match_frontend(auth_client):
    upload_id = upload(auth_client).json()["uploadId"]
    result = auth_client.get("/api/v1/sales/analytics", params={"uploadId": upload_id}).json()
    assert result["hasData"] and result["currency"] == "USD" and result["converted"] is True
    assert round(result["kpis"]["totalSales"]) == 5_159_935 and len(result["monthly"]) == 21
    assert result["kpis"]["topDealer"]["name"] == "Hamburg Tabakkontor GmbH"
    forecast = result["forecast"]
    assert forecast["method"] == "ses" and forecast["params"] == {"alpha": 0.4}
    assert {k: round(v) for k, v in forecast["scenarioTotals"].items()} == {
        "conservative": 485_974,
        "base": 1_663_490,
        "optimistic": 4_340_990,
    }
    assert round(result["growth"]["growth"], 1) == -6.2
    assert len(result["chartRows"]) == 21 + 12

    conservative = auth_client.get("/api/v1/sales/forecast", params={"uploadId": upload_id, "scenario": "conservative"}).json()
    assert round(conservative["total"]) == 485_974

    eur = auth_client.get("/api/v1/sales/analytics", params={"uploadId": upload_id, "currency": "EUR"}).json()
    assert eur["forecast"]["status"] == "insufficient" and eur["total"] is None

    bad = auth_client.get("/api/v1/sales/analytics", params={"uploadId": upload_id, "dateFrom": "2025-13"})
    assert bad.status_code == 422


def test_delete_upload(auth_client):
    upload_id = upload(auth_client).json()["uploadId"]
    assert auth_client.delete(f"/api/v1/sales/uploads/{upload_id}").status_code == 200
    assert auth_client.get(f"/api/v1/sales/uploads/{upload_id}").status_code == 404


def test_exchange_rate_overrides_are_admin_only(client):
    login(client, "vera.viewer@abc.com", VIEWER_PASSWORD)
    rates = client.get("/api/v1/sales/exchange-rates").json()
    assert rates["rates"]["EUR"] == 1.08 and rates["overridden"] == []
    forbidden = client.put("/api/v1/sales/exchange-rates", json={"rates": {"EUR": 1.2}})
    assert forbidden.status_code == 403


def test_exchange_rate_override_changes_analytics(auth_client):
    upload_id = upload(auth_client).json()["uploadId"]
    before = auth_client.get("/api/v1/sales/analytics", params={"uploadId": upload_id}).json()["kpis"]["totalSales"]
    updated = auth_client.put("/api/v1/sales/exchange-rates", json={"rates": {"EUR": 1.2}}).json()
    assert updated["rates"]["EUR"] == 1.2 and updated["overridden"] == ["EUR"]
    after = auth_client.get("/api/v1/sales/analytics", params={"uploadId": upload_id}).json()["kpis"]["totalSales"]
    assert after > before
    assert auth_client.put("/api/v1/sales/exchange-rates", json={"rates": {"XYZ": 2}}).status_code == 422
    reset = auth_client.delete("/api/v1/sales/exchange-rates").json()
    assert reset["rates"]["EUR"] == 1.08 and reset["overridden"] == []
