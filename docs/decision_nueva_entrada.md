## D11 — Bloqueo por intentos fallidos de login (HU-02)

**Decisión:** 5 contraseñas incorrectas dentro de 15 minutos bloquean los intentos de ese email
por 15 minutos. Durante el bloqueo `/login` responde **429** con la cabecera `Retry-After`
(segundos de espera), incluso si la contraseña enviada es la correcta. Un login correcto
borra el contador.

**Reglas:**
- Se cuenta por email, exista o no la cuenta: un email inventado se bloquea igual, así el
  bloqueo no revela qué emails tienen cuenta (misma idea que el mensaje único de 401).
- En la base se guarda solo la huella SHA-256 del email, nunca el texto que escribió quien ataca.
- Los fallos antiguos (más de 15 minutos entre el primero y el siguiente) se olvidan.

**Costo conocido:** como se bloquea por email, alguien podría bloquear a propósito la cuenta
de otra persona (15 minutos cada vez). Se acepta por ahora porque el bloqueo es corto y no
destruye nada. Mejora futura: limitar también por dirección IP y/o aumentar el tiempo
de forma progresiva.

**Pendiente:** limpiar periódicamente los registros viejos de `intentos_login`.
