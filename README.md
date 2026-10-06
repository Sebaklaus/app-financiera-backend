# App financiera: backend

API en Python con FastAPI. Por ahora tiene dos rutas: `GET /salud` y `POST /distribucion`
(reparto 50/25/15/10 de un monto).

## Cómo está organizado (arquitectura limpia)

Piensa en una cocina: el **dominio** son las recetas (reglas del negocio), los **casos de uso**
son los pedidos que se cocinan, y los **adaptadores** son el mesón por donde entran y salen los
platos (HTTP, base de datos, Fintoc). Las recetas no saben quién hace el pedido; el mesón sí
conoce las recetas, nunca al revés.

```
app/
  dominio/                 reglas puras (distribucion.py)
  casos_de_uso/            qué se puede hacer con las reglas
  adaptadores/api/         rutas HTTP (FastAPI)
  main.py                  arranque de la aplicación
tests/                     pruebas automáticas
docs/decisiones.md         registro de decisiones
```

## Cómo ejecutarlo

Requiere Python 3.12 o superior.

Windows (PowerShell):

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Linux o macOS:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Luego:

```
uvicorn app.main:app --reload     # servidor en http://127.0.0.1:8000
pytest                            # pruebas
ruff check .                      # revisión de estilo
```

Con el servidor andando, abre http://127.0.0.1:8000/docs: FastAPI genera esa página para
probar las rutas desde el navegador.
