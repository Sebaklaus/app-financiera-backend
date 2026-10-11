## D19 — Límite por IP y limpieza de datos obsoletos

**Límite por IP:** el bloqueo por email (5 fallos) frena a quien ataca una cuenta; el límite por
IP (30 fallos en 15 minutos → bloqueo de 15 minutos, respuesta 429) frena a quien prueba muchas
cuentas distintas desde un mismo lugar. El tope es más alto porque en las redes móviles chilenas
muchas personas comparten una misma IP. No hay tabla nueva: se reutiliza `intentos_login` con la
clave `sha256("ip:" + dirección)`, así la IP no se guarda en claro.

**IP real detrás de un balanceador:** el encabezado `X-Forwarded-For` lo puede escribir cualquiera;
solo se confía en las entradas que agregaron nuestros propios servidores (al final de la lista).
`PROXIES_CONFIABLES` indica cuántos hay delante de la app (0 por defecto = se usa la IP de la
conexión; en Cloud Run suele ser 1, y con balanceador más Cloud Armor puede ser 2: verificarlo al
desplegar). Si se configura mal, el límite por IP no protege o castiga a todos por igual.

**Limpieza (`python -m herramientas.limpieza`):** borra tokens de refresco y de recuperación
vencidos hace más de 1 día e intentos de login que ya no cuentan. Los tokens de refresco revocados
se conservan hasta que vencen, porque permiten detectar el reuso de un token robado. Se agenda
una vez al día al desplegar (por ejemplo, Cloud Scheduler). Cumple con minimización de datos
(Ley 21.719).

**Pendiente:** extender el límite por IP a `/recuperacion/solicitar` y `/registro`.
