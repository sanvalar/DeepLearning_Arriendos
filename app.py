from __future__ import annotations

import json
import math
import os
import sqlite3
from pathlib import Path

import joblib
from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "vivienda_estudiantil.db"
MODEL_PATH = BASE_DIR / "modelo_cbnn_vivienda.joblib"

FEATURES = [
    "area_m2", "habitaciones", "banos", "piso", "antiguedad",
    "dist_univ_min_km", "dist_metro_km", "dist_servicios_km",
    "nivel_seguridad", "nivel_ruido", "areas_verdes_score",
    "calidad_servicios", "servicios_comunes", "estrato",
]

UNIVERSITIES = {
    "USB": (6.2565, -75.5650, "Universidad de San Buenaventura"),
    "UdeA": (6.2672, -75.5683, "Universidad de Antioquia"),
    "UNAL": (6.2625, -75.5775, "Universidad Nacional de Colombia"),
    "EAFIT": (6.2000, -75.5783, "Universidad EAFIT"),
    "UPB": (6.2420, -75.5896, "Universidad Pontificia Bolivariana"),
    "UdeM": (6.2313, -75.6104, "Universidad de Medellín"),
}

app = Flask(__name__, static_folder=None)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(max(0, 1 - value)))


def clean_text(value: object, fallback: str = "Sin información") -> str:
    text = "Sin información" if value is None else str(value).strip()
    if not text or "�" in text:
        replacements = {
            "Fincara�z": "Fincaraíz",
            "medellin": "Medellín",
            "Itag��": "Itagüí",
        }
        for damaged, repaired in replacements.items():
            text = text.replace(damaged, repaired)
        text = text.replace("�", "")
    return text or fallback


def model_prediction(row: dict[str, object]) -> float:
    import pandas as pd

    model = app.extensions["model"]
    features = pd.DataFrame([{feature: row.get(feature) for feature in FEATURES}], columns=FEATURES)
    return max(0.0, float(model.predict(features)[0]))


@app.get("/")
def index():
    return send_from_directory(BASE_DIR, "aplicaci_n_web_comercial.html")


@app.get("/api/universities")
def universities():
    return jsonify([
        {"key": key, "name": name, "lat": lat, "lon": lon}
        for key, (lat, lon, name) in UNIVERSITIES.items()
    ])


@app.get("/api/recommendations")
def recommendations():
    university = request.args.get("university", "UdeA")
    if university not in UNIVERSITIES:
        return jsonify({"error": "Universidad no válida"}), 400

    try:
        budget = float(request.args.get("budget", 1300000))
        weight_proximity = float(request.args.get("proximity", 8))
        weight_value = float(request.args.get("value", 9))
        weight_security = float(request.args.get("security", 7))
    except ValueError:
        return jsonify({"error": "Los filtros deben ser numéricos"}), 400

    if not (650000 <= budget <= 10000000):
        return jsonify({"error": "El presupuesto debe estar entre $650.000 y $10.000.000 COP"}), 400
    weights = (weight_proximity, weight_value, weight_security)
    if min(weights) < 1 or max(weights) > 10:
        return jsonify({"error": "Los pesos deben estar entre 1 y 10"}), 400

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    rows = connection.execute("SELECT * FROM inmuebles WHERE precio IS NOT NULL AND lat IS NOT NULL AND lon IS NOT NULL").fetchall()
    connection.close()

    university_lat, university_lon, university_name = UNIVERSITIES[university]
    results = []
    model_available = app.extensions.get("model") is not None
    for source in rows:
        row = dict(source)
        if float(row["precio"]) > budget:
            continue
        try:
            prediction = model_prediction(row) if model_available else float(row["precio"])
        except Exception as exc:
            app.logger.warning("No fue posible predecir el inmueble %s: %s", row["id"], exc)
            prediction = float(row["precio"])
        distance = haversine_km(university_lat, university_lon, float(row["lat"]), float(row["lon"]))
        ratio = float(row["precio"] / prediction) if prediction > 0 else 1.0

        proximity_score = math.exp(-distance / 3.0)
        value_score = max(0.0, min(1.0, (1.25 - ratio) / 0.5))
        security_score = float(row["nivel_seguridad"] or 0) / 10.0
        total = (
            weight_proximity * proximity_score
            + weight_value * value_score
            + weight_security * security_score
        ) / sum(weights)

        if ratio < 0.92:
            classification, marker_color = "oportunidad", "#00B894"
        elif ratio > 1.10:
            classification, marker_color = "sobreprecio", "#EF4444"
        else:
            classification, marker_color = "precio_justo", "#f59e0b"

        results.append({
            "id": row["id"],
            "barrio": clean_text(row["barrio"]),
            "titulo": clean_text(row["titulo"]),
            "precio": float(row["precio"]),
            "prediction": round(prediction),
            "ratio": round(ratio, 3),
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "seguridad": float(row["nivel_seguridad"] or 0),
            "area_m2": float(row["area_m2"] or 0),
            "habitaciones": int(row["habitaciones"] or 0),
            "distance_km": round(distance, 2),
            "score": round(total * 10, 2),
            "classification": classification,
            "marker_color": marker_color,
            "url": row["url"] or None,
            "source": clean_text(row["fuente"]),
            "coordinate_approximate": bool(row["coord_aprox"]),
        })

    results.sort(key=lambda item: item["score"], reverse=True)
    return jsonify({
        "university": university_name,
        "count": len(results),
        "model_available": model_available,
        "as_of": "2026-10-26",
        "model_card": app.extensions.get("model_card", {}),
        "results": results[:100],
    })


def create_app() -> Flask:
    app.extensions["model"] = None
    app.extensions["model_card"] = {}
    card_path = BASE_DIR / "model_card.json"
    if card_path.exists():
        app.extensions["model_card"] = json.loads(card_path.read_text(encoding="utf-8"))
    if MODEL_PATH.exists():
        try:
            app.extensions["model"] = joblib.load(MODEL_PATH)
        except Exception as exc:
            app.logger.warning("Modelo no disponible: %s", exc)
    return app


if __name__ == "__main__":
    create_app()
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)), debug=False)
