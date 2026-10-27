import json
import sqlite3

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = [
    "area_m2", "habitaciones", "banos", "piso", "antiguedad",
    "dist_univ_min_km", "dist_metro_km", "dist_servicios_km",
    "nivel_seguridad", "nivel_ruido", "areas_verdes_score",
    "calidad_servicios", "servicios_comunes", "estrato",
]

connection = sqlite3.connect("vivienda_estudiantil.db")
data = pd.read_sql_query("SELECT * FROM inmuebles", connection)
connection.close()
X = data[FEATURES]
y = data["precio"].astype(float)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("mlp", MLPRegressor(hidden_layer_sizes=(64, 32, 16), max_iter=1500, random_state=42, early_stopping=True)),
])
model = TransformedTargetRegressor(regressor=pipeline, func=np.log1p, inverse_func=np.expm1)
model.fit(X_train, y_train)
prediction = model.predict(X_test)
metrics = {"r2": float(r2_score(y_test, prediction)), "mae": float(mean_absolute_error(y_test, prediction)), "samples": len(data)}
model.fit(X, y)
joblib.dump(model, "modelo_cbnn_vivienda.joblib")
with open("model_card.json", "w", encoding="utf-8") as file:
    json.dump(metrics, file, ensure_ascii=False, indent=2)
print(metrics)
