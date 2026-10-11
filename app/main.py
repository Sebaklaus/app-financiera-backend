from fastapi import FastAPI

from app.adaptadores.api.cors import aplicar_cors
from app.adaptadores.api.rutas import router
from app.adaptadores.api.rutas_auth import router as router_auth
from app.adaptadores.api.rutas_confirmaciones import router as router_confirmaciones
from app.adaptadores.api.rutas_movimientos import router as router_movimientos
from app.adaptadores.api.rutas_usuarios import router as router_usuarios
from app.configuracion import origenes_cors

app = FastAPI(title="App financiera API", version="0.1.0")
aplicar_cors(app, origenes_cors())
app.include_router(router)
app.include_router(router_usuarios)
app.include_router(router_auth)
app.include_router(router_movimientos)
app.include_router(router_confirmaciones)
