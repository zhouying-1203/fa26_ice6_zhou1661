"""Tests for story_polisher. Gemini is mocked, so they need no credentials and no network."""
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def fake_story():
    return main.GeminiStory(
        story="As a volunteer, I want a shift list, so that I know when to show up.",
        acceptance_criteria=["The list shows each shift.", "Shifts are sorted by time.", "Past shifts are hidden."],
        open_questions=["Can volunteers swap shifts?"],
    )


def test_health_returns_ok():
    # Arrange
    # (nothing to set up)

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_polish_falls_back_when_no_project(monkeypatch):
    # Arrange
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    # Act
    response = client.post("/polish", json={"idea": "let people filter shows by venue"})

    # Assert
    assert response.status_code == 200
    assert response.json()["source"] == "fallback"


def test_polish_returns_gemini_story(monkeypatch):
    # Arrange
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-project")
    monkeypatch.setattr(main, "call_gemini", lambda idea: fake_story())

    # Act
    response = client.post("/polish", json={"idea": "a shift list for volunteers"})

    # Assert
    body = response.json()
    assert response.status_code == 200
    assert body["source"] == "gemini"
    assert body["story"].startswith("As a volunteer")
    assert 3 <= len(body["acceptance_criteria"]) <= 5


def test_polish_rejects_empty_idea():
    # Arrange
    payload = {"idea": ""}

    # Act
    response = client.post("/polish", json=payload)

    # Assert
    assert response.status_code == 422


def test_polish_rejects_whitespace_idea():
    # Arrange
    payload = {"idea": "   \n\t "}

    # Act
    response = client.post("/polish", json=payload)

    # Assert
    assert response.status_code == 422


def test_polish_rejects_long_idea():
    # Arrange
    payload = {"idea": "x" * (main.MAX_IDEA_CHARS + 1)}

    # Act
    response = client.post("/polish", json=payload)

    # Assert
    assert response.status_code == 422


def test_polish_returns_502_when_gemini_fails(monkeypatch):
    # Arrange
    def broken(idea):
        raise RuntimeError("secret internal detail: 403 permission denied on projects/xyz")

    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-project")
    monkeypatch.setattr(main, "call_gemini", broken)

    # Act
    response = client.post("/polish", json={"idea": "anything"})

    # Assert
    assert response.status_code == 502
    assert "secret" not in response.text
