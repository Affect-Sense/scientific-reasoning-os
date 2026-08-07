"""Offline API tests: health and auth fail-closed. No GCP required."""
import os

from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


def test_healthz_open():
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_fail_closed_when_unconfigured(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    r = client.post("/questions", json={"text": "x" * 20, "language": "en"})
    assert r.status_code == 503


def test_rejects_bad_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "correct-key")
    r = client.post(
        "/questions",
        headers={"X-API-Key": "wrong"},
        json={"text": "x" * 20, "language": "en"},
    )
    assert r.status_code == 401


def test_validation_rejects_short_text(monkeypatch):
    monkeypatch.setenv("API_KEY", "k")
    r = client.post(
        "/questions", headers={"X-API-Key": "k"}, json={"text": "short", "language": "en"}
    )
    assert r.status_code == 422


def test_ui_requires_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "k")
    assert client.get("/ui").status_code == 401
    assert client.get("/ui?k=wrong").status_code == 401


def test_ui_index_renders(monkeypatch):
    monkeypatch.setenv("API_KEY", "k")
    r = client.get("/ui?k=k")
    assert r.status_code == 200 and "pregunta de investigación" in r.text.lower()


def _stripe_sig(payload: bytes, secret: str) -> str:
    import hmac, hashlib, time
    t = int(time.time())
    signed = f"{t}.".encode() + payload
    v1 = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={t},v1={v1}"


def test_webhook_fail_closed(monkeypatch):
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    r = client.post("/webhooks/stripe", content=b"{}")
    assert r.status_code == 503


def test_webhook_rejects_bad_signature(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    r = client.post(
        "/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t=1,v1=deadbeef"}
    )
    assert r.status_code == 400


def test_webhook_ignores_other_event_types(monkeypatch):
    import json
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    payload = json.dumps({"object": "event", "type": "invoice.paid", "data": {"object": {}}}).encode()
    r = client.post(
        "/webhooks/stripe",
        content=payload,
        headers={"stripe-signature": _stripe_sig(payload, "whsec_test")},
    )
    assert r.status_code == 200 and r.json()["ignored"] == "invoice.paid"
