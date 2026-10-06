"""Adaptador HTTP: traduce solicitudes web a llamadas a los casos de uso."""

from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.casos_de_uso.calcular_distribucion import calcular_distribucion

router = APIRouter()


class SolicitudDistribucion(BaseModel):
    # strict=True: rechaza "1000" y 1000.5; solo acepta enteros. Tope para evitar abusos.
    monto: Annotated[int, Field(strict=True, gt=0, le=1_000_000_000)]


class RespuestaDistribucion(BaseModel):
    necesidades: int
    inversion: int
    estabilidad: int
    entretenimiento: int
    total: int


@router.get("/salud")
def salud() -> dict[str, str]:
    return {"estado": "ok"}


@router.post("/distribucion", response_model=RespuestaDistribucion)
def post_distribucion(solicitud: SolicitudDistribucion) -> RespuestaDistribucion:
    d = calcular_distribucion(solicitud.monto)
    return RespuestaDistribucion(
        necesidades=d.necesidades,
        inversion=d.inversion,
        estabilidad=d.estabilidad,
        entretenimiento=d.entretenimiento,
        total=d.total,
    )
