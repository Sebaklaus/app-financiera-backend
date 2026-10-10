# Registro de decisiones

Cada decisión técnica que cambie algo del informe se anota aquí (fecha, qué, por qué).
En la semana 14 sirve para actualizar los diagramas y las tablas.

## 2026-10-04

- **D1. Nombres de las cuatro partes:** necesidades (50 %), inversión (25 %), estabilidad (15 %)
  y entretenimiento (10 %). Falta confirmar si el informe usará «estabilidad» o «estabilidad».
- **D2. Montos en pesos enteros.** El peso chileno no usa decimales en la práctica; así se
  evitan errores de redondeo de `float`.
- **D3. Sobrante del redondeo:** inversión, estabilidad y entretenimiento se redondean hacia abajo y
  los pocos pesos que sobran (menos de 3) se suman a necesidades, de modo que la suma siempre da el monto.
  Falta confirmar con el docente o el equipo que esta regla es la deseada.

## D4. Requisitos mínimos de contraseña (HU-01)

Mínimo 8 caracteres, al menos una letra y al menos un número. Máximo 72 bytes, porque
bcrypt solo considera los primeros 72 y rechazar el exceso es más honesto que ignorarlo.
El email se guarda en minúsculas y sin espacios, para que no existan dos cuentas
"distintas" por una mayúscula. Estos requisitos son una decisión de producto y pueden
cambiar; el informe solo habla de "requisitos mínimos" sin fijarlos.

## D6. Ingresos, gastos y resumen por categoría (HU-28)

**Decisión.** Cada ingreso se reparte con la regla 50/25/15/10 (la función `distribuir` de siempre). El reparto no se guarda: se recalcula desde los ingresos cada vez que se pide el resumen. Los gastos se registran contra una de las cuatro categorías. El resumen muestra, por categoría, lo asignado, lo gastado y lo disponible.

**Por qué.** Guardar solo hechos (ingresos y gastos) y calcular lo derivado evita que los datos se contradigan. Cada ingreso se reparte por separado, así los pesos sobrantes se tratan igual al registrarlo y al resumir.

**Reglas.** Montos enteros en pesos, mayores que cero y hasta 1.000 millones. Fecha no futura. Descripción de 1 a 200 caracteres. Disponible negativo significa que la persona se pasó en esa categoría (no se bloquea el gasto). Todas las rutas exigen token y solo muestran los movimientos de su dueño; la tabla además rechaza montos no positivos.

**Pendiente.** Confirmación del reparto por parte del usuario (25 % y 15 %), edición y borrado de movimientos, resumen por mes, zona horaria del usuario para la fecha por defecto (hoy usa la fecha UTC), y calcular el resumen en SQL cuando haya muchos movimientos.

## D7 — Confirmación del reparto (HU-12 / RNF-06)

**Decisión:** al registrar un ingreso, el sistema solo *propone* el reparto 50/25/15/10.
Necesidades (50 %) y entretenimiento (10 %) se asignan de inmediato; inversión (25 %) y
estabilidad (15 %) quedan como propuestas *pendientes* hasta que la persona las confirme o rechace.

**Por qué:** el informe exige que ninguna parte de ahorro/inversión cuente sin consentimiento
explícito. Así la app no "decide por" el usuario.

**Reglas:**
- Una propuesta solo se decide una vez (confirmar o rechazar); la segunda vez responde 409.
- Rechazar deja el dinero "sin apartar" (se muestra como `rechazado` en el resumen).
- Nadie puede ver ni decidir propuestas ajenas (responde 404, no 403, para no revelar que existen).
- La actualización es atómica (`UPDATE ... WHERE estado='pendiente'`), así dos peticiones
  simultáneas no pueden decidir la misma propuesta.

**Pendiente:** poder revisar una decisión, y editar/borrar movimientos. Cambiar el esquema de la
base a mano no escala: más adelante conviene Alembic (migraciones).

## D8 — Editar y borrar movimientos

**Decisión:** se puede corregir (`PATCH /movimientos/{id}`) y borrar (`DELETE /movimientos/{id}`)
cualquier ingreso o gasto propio. Quien no es dueño recibe 404 (igual que si no existiera).

**Reglas:**
- Se cambia solo lo que se envía (monto, categoría, descripción, fecha); se validan igual que al crear.
- Un ingreso no tiene categoría.
- Gastos: se editan y borran libremente; el resumen se recalcula solo.
- Ingresos: texto y fecha siempre se pueden corregir. El **monto** solo si ninguna propuesta
  (25 % / 15 %) fue decidida; entonces se vuelve a proponer el reparto con el monto nuevo.
  Si ya hay una decisión, responde 409: cambiar el monto movería dinero que la persona ya
  confirmó o rechazó. La salida es borrar el ingreso y registrarlo de nuevo.
- Borrar un ingreso borra también sus propuestas, decididas o no.

**Por qué:** respeta la regla de que nada se aplica sin consentimiento (RNF-06) y evita
que el historial contradiga decisiones ya tomadas.

**Pendiente:** el borrado es definitivo (sin papelera ni historial de cambios). Para
auditoría futura convendría un registro de cambios (ley 21.719: derechos de rectificación y supresión).

## D9 — Sesión con token de refresco y logout (HU-02)

**Decisión:** el login entrega dos tokens. El de **acceso** (JWT, 15 min) abre las rutas; el de
**refresco** (opaco, 30 días) solo sirve para pedir un par nuevo en `POST /refrescar`.
`POST /logout` cierra una sesión y `POST /logout/todas` cierra todas las de la persona.

**Reglas:**
- El token de refresco se guarda en la base solo como huella SHA-256 (tabla `tokens_refresco`);
  si alguien leyera la base, no podría usarlo. SHA-256 y no bcrypt: el token es aleatorio y largo,
  no una contraseña adivinable.
- **Rotación:** cada refresco se usa una sola vez; al renovar se entrega uno nuevo y el viejo se revoca.
- **Detección de robo:** si llega un token ya usado, se cierran todas las sesiones de esa persona.
  La revocación es atómica (`UPDATE ... WHERE revocado_en IS NULL`), así que dos peticiones
  simultáneas con el mismo token no pueden ganar las dos.
- El logout siempre responde 204: cerrar una sesión ya cerrada no es un error ni revela nada.
- Un token de acceso ya emitido sigue valiendo hasta que venza (máx. 15 min) tras un logout:
  es el costo de usar JWT sin lista de revocación. Por eso la vida del acceso es corta.

**Pendiente:** limpiar periódicamente los tokens vencidos de la tabla, bloqueo por intentos
fallidos de login, y guardar el refresco en el almacenamiento seguro del teléfono en el cliente.

## D10 — Resumen y listado por mes (HU-28)

**Decisión:** `GET /resumen?mes=2026-10` y `GET /movimientos?mes=2026-10` filtran por mes
calendario (formato AAAA-MM). Sin `mes`, se usa todo el historial, como antes. La respuesta del
resumen indica qué mes se consultó (`mes`, o `null` si fue todo).

**Reglas:**
- Cada mes se mira por separado: lo que sobra de una categoría **no pasa** al mes siguiente.
  Es la lectura más simple del 50/25/15/10; si el informe pide arrastrar saldos, se agrega después.
- Una propuesta (25 % / 15 %) cuenta en el mes de **su ingreso**, no en el mes en que se decide.
- Un mes mal escrito responde 422 (`2026-13`, `octubre`, `26-10`...).
- El mes es de calendario y usa la fecha del movimiento tal como se registró (sin zona horaria).

**Pendiente:** definir con el docente si los saldos deben arrastrarse entre meses, y la zona
horaria (la fecha por omisión de un movimiento usa UTC, y cerca de medianoche puede caer en otro día).

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

## D12 — Versiones fijas en requirements.txt

**Decisión:** cada librería directa de `requirements.txt` queda con su versión exacta
(`fastapi==X.Y.Z`). Se genera con `python -m herramientas.fijar_versiones`, que lee las versiones
instaladas en el entorno donde las pruebas pasan.

**Por qué:** sin versiones fijas, `pip install` instala "lo último" de cada librería; si una
publica un cambio incompatible, el proyecto puede romperse sin que nadie haya tocado el código
(y Actions fallaría un día sin motivo aparente). Con versiones fijas, tu computador, GitHub
Actions y el servidor usan lo mismo, y subir de versión es una decisión consciente.

**Límite conocido:** solo se fijan las librerías directas, no las que ellas traen por dentro
(transitivas). Para fijarlas también convendría una herramienta de bloqueo (pip-tools, uv o
Poetry) o `pip freeze`. Queda como mejora futura.

**Cómo actualizar:** `pip install -U <librería>`, correr `pytest` y `ruff check`, y si todo
pasa, volver a ejecutar `python -m herramientas.fijar_versiones` y subir el cambio.

## D13 — Zonas horarias: guardar en UTC, "hoy" según Chile

**Decisión:** todas las horas (`creado_en`, `decidido_en`, vencimientos de tokens) se guardan y se
entregan en UTC, y en la API siempre terminan en `Z`. En cambio, la **fecha por omisión** de un
ingreso o gasto (cuando la persona no la indica) es la de **hoy en Chile** (`America/Santiago`).

**Por qué:** antes la fecha por omisión usaba UTC. En Chile (UTC-3 en verano, UTC-4 en invierno), un
gasto registrado a las 21:30 caía en el día siguiente, y con eso entraba al mes equivocado en el
resumen mensual (D10). Guardar en UTC evita ambigüedades con el cambio de hora; usar el calendario
de Chile para "hoy" respeta lo que la persona entiende por hoy.

**Reglas:**
- `app/dominio/reloj.py` es el único lugar que decide la fecha de hoy y convierte a UTC.
- `ZoneInfo("America/Santiago")` aplica solo el cambio de hora de verano e invierno.
- En Windows hace falta la librería `tzdata` (Windows no trae la base de zonas horarias).

**Pendiente:** si la app se usa fuera de Chile, la zona debería ser un dato de cada usuario.
