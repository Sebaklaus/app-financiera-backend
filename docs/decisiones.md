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
