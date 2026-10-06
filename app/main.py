from fastapi import FastAPI

from app.adaptadores.api.rutas import router

app = FastAPI(title="App financiera API", version="0.1.0")
app.include_router(router)
