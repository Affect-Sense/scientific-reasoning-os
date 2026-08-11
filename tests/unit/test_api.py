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


def test_welcome_without_session_renders_waiting_page():
    r = client.get("/welcome")
    assert r.status_code == 200 and "Preparando tu acceso" in r.text


def test_ui_english_chrome(monkeypatch):
    monkeypatch.setenv("API_KEY", "k")
    r = client.get("/ui?k=k&lang=en")
    assert r.status_code == 200
    assert "Your workspace" in r.text and "Powered by Gemini 2.5 Flash" in r.text
    assert "invent literature" in r.text


def test_ui_spanish_default_unchanged(monkeypatch):
    monkeypatch.setenv("API_KEY", "k")
    r = client.get("/ui?k=k")
    assert r.status_code == 200
    assert "Tu espacio de trabajo" in r.text and "No inventa literatura" in r.text


def test_should_retry_codes():
    from google.genai import errors as ge
    from src.services.gemini_client import should_retry

    class Fake(ge.APIError):
        def __init__(self, code):
            self.code = code
            Exception.__init__(self, f"code {code}")

    assert should_retry(Fake(429)) and should_retry(Fake(503))
    assert not should_retry(Fake(400))
    assert not should_retry(ValueError("x"))


def test_submit_saturation_preserves_text(monkeypatch):
    monkeypatch.setenv("API_KEY", "k")
    from src.application import rq_lifecycle
    from src.services.gemini_client import GeminiUnavailableError

    def boom(**kwargs):
        raise GeminiUnavailableError("still 429")

    monkeypatch.setattr(rq_lifecycle, "submit", boom)
    import src.api.app as appmod
    from src.services.firestore_repository import FirestoreRepository
    monkeypatch.setattr(appmod, "resolve_actor", lambda k="": ("genaro", "proj_lak2027"))
    monkeypatch.setattr(FirestoreRepository, "__init__", lambda self, *a, **kw: None)
    monkeypatch.setattr(FirestoreRepository, "ensure_project", lambda self, *a, **kw: "proj_lak2027")
    r = client.post(
        "/ui/questions?k=k&lang=en",
        data={"text": "Does X affect Y in Z populations?", "language": "en"},
    )
    assert r.status_code == 503
    assert "Does X affect Y in Z populations?" in r.text
    assert "NOT lost" in r.text
