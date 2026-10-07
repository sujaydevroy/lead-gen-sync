from __future__ import annotations

from sqlalchemy import select

from app.core.database import get_session_factory
from app.models import Communication, User


def stats(client):
    return client.get("/api/v1/communications/stats").json()


def test_history_shape_and_filters(auth_client):
    page = auth_client.get("/api/v1/communications", params={"dealerId": "DLR-1006"}).json()
    assert page["total"] >= 2
    item = page["items"][0]
    assert set(item) >= {
        "id",
        "dealerId",
        "dealerName",
        "type",
        "direction",
        "sender",
        "recipient",
        "subject",
        "body",
        "status",
        "createdAt",
        "attachments",
    }
    assert item["dealerId"] == "DLR-1006"
    dates = [i["createdAt"] for i in page["items"]]
    assert dates == sorted(dates, reverse=True)

    meetings = auth_client.get("/api/v1/communications", params=[("types", "Meeting")]).json()
    assert meetings["total"] >= 3 and {i["type"] for i in meetings["items"]} == {"Meeting"}
    inbound = auth_client.get("/api/v1/communications", params={"direction": "inbound"}).json()
    assert {i["direction"] for i in inbound["items"]} == {"inbound"}
    found = auth_client.get("/api/v1/communications", params={"search": "warranty"}).json()
    assert [i["subject"] for i in found["items"]] == ["Warranty claim acknowledgement"]
    assert len(auth_client.get("/api/v1/communications/recent", params={"limit": 3}).json()) == 3


def test_send_message_validation_and_csrf(auth_client):
    url = "/api/v1/dealers/DLR-1047/messages"
    short = auth_client.post(url, data={"subject": "Hi", "message": "Long enough message body"})
    assert short.status_code == 422 and short.json()["message"] == "Subject must be at least 3 characters."
    brief = auth_client.post(url, data={"subject": "Q4 availability", "message": "too short"})
    assert brief.json()["message"] == "Message must be at least 10 characters."

    csrf = auth_client.headers.pop("X-CSRF-Token")
    try:
        blocked = auth_client.post(url, data={"subject": "Q4 availability", "message": "Please confirm quantities."})
        assert blocked.status_code == 403 and blocked.json()["message"] == "Missing or invalid CSRF token."
    finally:
        auth_client.headers["X-CSRF-Token"] = csrf


def test_send_message_with_attachment_updates_history(auth_client):
    before = stats(auth_client)
    content = b"sku,price\nMCB-32A,410\n"
    response = auth_client.post(
        "/api/v1/dealers/DLR-1047/messages",
        data={"subject": "  Q4 Product Availability ", "message": "Please confirm your Q4 forecast quantities."},
        files={"attachment": ("price list.csv", content, "text/csv")},
    )
    assert response.status_code == 201, response.text
    sent = response.json()
    assert sent["subject"] == "Q4 Product Availability" and sent["status"] == "Sent" and sent["type"] == "Message"
    assert sent["sender"] == "John Smith"
    assert sent["recipient"] == "Khalid Al Dhaheri (Al Ain Electro Services) <khalid@alain-electro.example>"
    assert sent["attachments"][0]["name"] == "price list.csv" and sent["attachments"][0]["size"] == len(content)

    download = auth_client.get(sent["attachments"][0]["url"])
    assert download.status_code == 200 and download.content == b"sku,price\nMCB-32A,410\n"

    history = auth_client.get("/api/v1/communications", params={"dealerId": "DLR-1047"}).json()
    assert history["items"][0]["id"] == sent["id"]
    after = stats(auth_client)
    assert after["sent"] == before["sent"] + 1 and after["total"] == before["total"] + 1

    # Audit columns are filled with the authenticated user.
    with get_session_factory()() as db:
        row = db.get(Communication, int(sent["id"].removeprefix("COM-")))
        john = db.scalar(select(User).where(User.email == "john.smith@abc.com"))
        assert row.created_by == john.id and row.modified_by == john.id and row.is_active


def test_rejects_disallowed_attachment(auth_client):
    response = auth_client.post(
        "/api/v1/dealers/DLR-1047/messages",
        data={"subject": "Installer", "message": "Please run the attached installer."},
        files={"attachment": ("setup.exe", b"MZ...", "application/octet-stream")},
    )
    assert response.status_code == 422 and "not allowed" in response.json()["message"]


def test_log_interaction(auth_client):
    response = auth_client.post(
        "/api/v1/dealers/DLR-1001/interactions", json={"type": "Call", "subject": "Call to +91 98371 41116"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "Call" and body["status"] == "Initiated" and body["body"] == "Call started to +91 98371 41116"
    invalid = auth_client.post("/api/v1/dealers/DLR-1001/interactions", json={"type": "Fax", "subject": "x"})
    assert invalid.status_code == 422
