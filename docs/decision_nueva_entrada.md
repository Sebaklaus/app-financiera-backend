## D14 — Migraciones de base de datos con Alembic

**Decisión:** los cambios en las tablas se hacen con migraciones (Alembic), no borrando datos ni
recreando tablas. La carpeta `migraciones/` guarda la historia: cada cambio es un archivo
numerado que sabe aplicarse (`upgrade`) y deshacerse (`downgrade`). La base recuerda en qué
versión está en la tabla `alembic_version`.

**Por qué:** hasta ahora, cada tabla nueva o cambio de columna obligó a borrar datos de prueba.
Con usuarios reales eso es imposible. Las migraciones cambian la estructura conservando los datos
y dejan un registro de cómo evolucionó la base (útil para el informe y para el despliegue).

**Cómo se usa:**
- Base nueva y vacía: `alembic upgrade head`.
- Base que ya tenía las tablas (la de desarrollo actual): una sola vez, `alembic stamp head`.
- Cambio futuro: modificar la tabla en el código, y luego `alembic revision --autogenerate -m "qué cambió"`,
  revisar el archivo generado y aplicar con `alembic upgrade head`.
- `app/infraestructura/modelos.py` lista todas las tablas; una tabla nueva se anota ahí.

**Red de seguridad:** `tests/test_migraciones.py` aplica las migraciones sobre una base temporal y
comprueba que coinciden con las tablas del código. Si alguien cambia una tabla y olvida la migración,
la prueba falla y GitHub Actions lo avisa.

**Pendiente:** ejecutar `alembic upgrade head` como parte del despliegue; revisar a mano las
migraciones autogeneradas (Alembic no detecta todo, por ejemplo cambios de nombre de columna).
