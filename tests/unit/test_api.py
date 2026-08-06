"""Offline API tests: health and auth fail-closed. No GCP required."""
import os

from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


def test_health_open():
    r = client.get("/health")
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
