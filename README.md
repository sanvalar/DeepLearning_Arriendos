# HabitaEdu / DeepLearning_Arriendos

## Ejecutar localmente

```powershell
py -m pip install -r requirements.txt
py app.py
```

Abrir http://127.0.0.1:5000. La API expone `/api/universities` y `/api/recommendations`.

## Pruebas

```powershell
py -m pytest -q test_app.py
```

El backend consulta los inmuebles de SQLite, aplica el modelo cuando está disponible y calcula el ranking con cercanía, valor estimado y seguridad. Los enlaces y fechas de disponibilidad deben validarse antes de usarlos en producción.