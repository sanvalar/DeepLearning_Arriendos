import math

import app as app_module


def test_haversine_same_point_is_zero():
    assert app_module.haversine_km(6.2672, -75.5683, 6.2672, -75.5683) == 0


def test_haversine_medellin_distance_is_reasonable():
    distance = app_module.haversine_km(6.2672, -75.5683, 6.2442, -75.5900)
    assert 3 < distance < 4


def test_api_rejects_invalid_university():
    client = app_module.create_app().test_client()
    response = client.get("/api/recommendations?university=NOEXISTE")
    assert response.status_code == 400


def test_api_rejects_invalid_budget():
    client = app_module.create_app().test_client()
    response = client.get("/api/recommendations?budget=-1")
    assert response.status_code == 400


def test_api_returns_database_recommendations():
    client = app_module.create_app().test_client()
    response = client.get("/api/recommendations?university=UdeA&budget=1300000")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] > 0
    assert payload["results"] == sorted(payload["results"], key=lambda item: item["score"], reverse=True)
    assert all(item["precio"] <= 1300000 for item in payload["results"])
