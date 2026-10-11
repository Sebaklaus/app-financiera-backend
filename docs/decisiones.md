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

## D15 — CORS por lista de invitados y métricas de seguridad

**CORS:** el navegador solo deja que una página web llame a la API si la API la autoriza. Las
direcciones autorizadas se escriben en `CORS_ORIGINS` (separadas por coma) en el `.env`. Vacío =
nadie (por defecto); `*` está prohibido. No se usan cookies (`allow_credentials=False`): el token
viaja en el encabezado `Authorization`. Las apps móviles no usan CORS; es para Flutter Web.

**Métricas de seguridad:** `python -m herramientas.metricas_seguridad` entrega recuentos
(usuarios, sesiones activas, sesiones revocadas, cuentas bloqueadas ahora, cuentas con fallos
recientes). Solo cuenta filas; nunca muestra emails, contraseñas ni tokens. Sirven como
evidencia medible para el informe y como base de una futura alerta.

## D16 — Derechos sobre los datos (Ley 21.719): ver, corregir y borrar

**Decisión:** la persona puede, desde la API y con sesión iniciada:
- `GET /yo/datos`: descargar todo lo que la app guarda de ella (acceso y portabilidad).
- `PATCH /yo/email`: corregir su email (rectificación).
- `POST /yo/contrasena`: cambiar su contraseña; se cierran todas sus sesiones.
- `POST /yo/eliminar`: borrar su cuenta y todos sus datos (supresión), en una sola operación.

**Pide la contraseña otra vez** en cambiar clave, cambiar email y eliminar: quien encuentre un
teléfono desbloqueado no puede adueñarse ni destruir la cuenta. Esa verificación comparte el
bloqueo del login (5 fallos → 429), así no sirve para adivinar claves.

**Contraseña de confirmación incorrecta = 403, no 401.** El 401 queda reservado para "tu token no
sirve"; así el front no confunde un error de contraseña con una sesión vencida y no cierra la
sesión de la persona por error. Se usa `POST /yo/eliminar` (y no DELETE con cuerpo) porque algunos
clientes HTTP no envían cuerpo en DELETE.

**Pendiente:** consentimientos separados (HU-03) y perfil de riesgo en el registro; recuperar
contraseña olvidada (necesita envío de correos); retención de datos tras borrar (hoy se borra
todo de inmediato).

## D17 — Consentimientos separados y perfil de riesgo (HU-03)

**Decisión:** tres consentimientos, cada uno con su propio interruptor y guardado por separado:
`terminos_y_privacidad` y `datos_financieros` (obligatorios para usar la app) y `comunicaciones`
(opcional). El perfil de riesgo (`conservador`, `moderado`, `arriesgado`) se declara aparte.

**Historial que no se borra:** cada cambio agrega una fila con fecha y versión del texto aceptado
(`VERSION_TEXTOS`); retirar un consentimiento agrega una fila nueva, no borra la anterior. Así se
puede demostrar qué aceptó la persona y cuándo (Ley 21.719: consentimiento libre, informado y
específico). Un obligatorio no se puede retirar (422); para eso se elimina la cuenta.

**Cómo se usa:** el front, justo después del registro, llama `GET /yo/consentimientos`; si
`pendientes` no está vacío, muestra los interruptores y envía `PUT /yo/consentimientos`. Luego
`PUT /yo/perfil-riesgo`. `/registro` no cambió, así que nada existente se rompe.

**Datos:** tablas `consentimientos` y `perfiles_riesgo` (migración 0002). `GET /yo/datos` las
incluye y `POST /yo/eliminar` las borra.

**Pendiente (decisión de producto):** hoy el backend no bloquea operaciones si faltan los
consentimientos; solo informa. Se puede exigirlos en el front, o bloquear en el backend.
Los textos legales y su versión final los define el abogado.

## D18 — Recuperar la contraseña olvidada

**Flujo:** `POST /recuperacion/solicitar` (email) envía por correo un token de un solo uso que
dura 30 minutos; `POST /recuperacion/restablecer` (token + contraseña nueva) cambia la clave.
Estas dos rutas no llevan sesión, porque la persona no puede entrar.

**Decisiones de seguridad:**
- `solicitar` responde siempre 202 y lo mismo, exista o no la cuenta: no se revela qué emails
  están registrados.
- El token es aleatorio (48 bytes) y solo se guarda su huella SHA-256, como el token de refresco.
- Solo sirve el último token enviado; sirve una sola vez (marcado atómico: si dos peticiones lo
  usan a la vez, una gana) y vence a los 30 minutos.
- Pedir otro correo antes de 1 minuto se ignora en silencio: evita usar la app para llenar de
  correos el buzón de otra persona.
- Una contraseña débil se rechaza ANTES de gastar el token, así puede corregirla y reintentar.
- Al restablecer se cierran todas las sesiones y se quita el bloqueo del login.

**Correo:** el envío está detrás del puerto `EnviadorCorreo`. Hoy solo existe `CORREO_MODO=consola`,
que escribe el correo (con el token) en la terminal del servidor, solo para desarrollo. Antes de
producción hay que contratar un proveedor (por ejemplo SendGrid o Amazon SES), escribir su
adaptador y cambiar `CORREO_MODO`; el modo consola nunca debe usarse en producción.

**Pendiente:** el enlace del correo (hoy es solo el token; falta decidir si abre la app con un
enlace profundo o una página web), plantilla del correo en español y límite por IP (paquete 4).

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

## D20 — Endurecimiento: cabeceras, salud, límites por IP y revisión automática

**Cabeceras de seguridad** en todas las respuestas (`nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy: no-referrer`, HSTS). Las respuestas de la API además llevan `Cache-Control:
no-store` (datos financieros: que nadie guarde copias) y una política CSP cerrada. `/docs` y
`/redoc` quedan sin estas dos últimas porque cargan scripts externos y se romperían.

**`/salud/listo`:** comprueba que la app puede hablar con la base (`SELECT 1`); si no, 503 sin
detalles. Cloud Run lo usará como sonda de arranque. `/salud` sigue indicando solo que el proceso vive.

**Límites por IP ampliados:** además del login (30 fallos / 15 min), `/registro` (20 peticiones /
15 min) y `/recuperacion/solicitar` (10 peticiones / 15 min) responden 429 con `Retry-After`. Frenan
la creación de cuentas en masa y el uso de la app para llenar de correos el buzón de otras personas.

**Revisión automática de seguridad** (`.github/workflows/seguridad.yml`): `pip-audit` busca
librerías con vulnerabilidades conocidas y `bandit` busca errores de seguridad en nuestro código;
corre en cada cambio y cada lunes. Si `pip-audit` falla por una librería vulnerable, se actualiza su
versión en `requirements.txt`.

**Secretos fuera de la URL:** `tests/test_secretos_fuera_de_la_url.py` recorre todas las rutas y
falla si alguna pide una contraseña o un token por la dirección (quedarían en registros).

**Pendiente:** registro de auditoría de eventos de seguridad; el modo `consola` del correo escribe
el token en el registro y es solo para desarrollo.

## D21 — Bitácora de eventos de seguridad (auditoría)

**Decisión:** la app anota en la tabla `eventos_seguridad` qué ocurrió y cuándo: logins exitosos
y fallidos, rechazos por bloqueo (de cuenta o de IP), reuso de token de refresco (señal de token
robado), cierres de sesión masivos, confirmaciones de contraseña fallidas, cambios de clave y email,
recuperación de contraseña y eliminación de cuenta (13 tipos en `TipoEvento`).

**Qué NO se anota:** contraseñas, tokens ni textos escritos por la persona. La IP se guarda solo
como huella (SHA-256), nunca en claro. Un login fallido no lleva usuario (no se sabe de quién es).

**Si la bitácora falla, la operación de la persona sigue:** se deja un aviso en el registro del
servidor. Anotar es importante, pero no más que dejar entrar a la gente.

**Transparencia:** `GET /yo/actividad` muestra a cada persona sus últimos eventos de seguridad
(inicios de sesión, cambios, etc.): si ve algo que no hizo, sabe que debe cambiar la clave.

**Eliminación de cuenta (Ley 21.719):** los eventos se conservan SIN vínculo con la persona
(`usuario_id` queda vacío; no es clave foránea a propósito). Sirven para investigar incidentes
(Ley 21.663) aunque la cuenta ya no exista, y sin la IP ni el usuario no identifican a nadie.

**Retención:** 365 días; después los borra `python -m herramientas.limpieza`.

**Métricas:** `python -m herramientas.metricas_seguridad` ahora incluye `eventos_24h_<tipo>`,
la cantidad de cada tipo de evento en las últimas 24 horas: base para alertas (por ejemplo,
muchos `login_fallido` o cualquier `refresco_reutilizado`).

**Pendiente:** alertas automáticas, y el procedimiento de reporte de incidentes (Ley 21.663).
