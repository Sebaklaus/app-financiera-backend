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
