## D5. Inicio de sesión con tokens JWT firmados con RS256

**Decisión.** El login devuelve un token de acceso JWT firmado con RS256 (par de llaves RSA de 2048 bits), con vida de 15 minutos, como fija el informe. El token solo lleva `sub` (id del usuario), `iss`, `iat` y `exp`. Nada de email ni datos financieros.

**Por qué.** Con RS256 solo quien tiene la llave privada puede fabricar tokens; el resto del sistema verifica con la pública. Al decodificar se fija la lista de algoritmos permitidos (`["RS256"]`) para rechazar tokens "sin firma" (`alg: none`).

**Mensaje único.** Email inexistente y contraseña incorrecta devuelven el mismo 401 con el mismo texto, para no revelar qué emails tienen cuenta.

**Pendiente.** Refresh token con rotación, bloqueo por intentos fallidos y cierre por inactividad. Las llaves viven en `claves/` (fuera de Git) en desarrollo; en producción irán en un gestor de secretos. Mejora futura: igualar el tiempo de respuesta cuando el email no existe (hoy es más rápido que verificar un bcrypt).
