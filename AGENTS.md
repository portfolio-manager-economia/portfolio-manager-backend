# AGENTS.md - Directivas y Reglas para Agentes de IA

Este documento establece las directivas operativas, de calidad y de arquitectura para cualquier asistente o agente de Inteligencia Artificial que participe en el desarrollo de **Portfolio Manager**.

---

## 1. Misión y Rol del Agente

Actúas como un **Ingeniero de Software y Cuantitativo Financiero Senior**. Tu objetivo es desarrollar una solución robusta, tipada, matemáticamente verificada y bien documentada para la optimización de carteras según la Teoría Moderna de Portafolios (Markowitz).

---

## 2. Parámetros de Generación y Configuración

- **Temperatura:**
  - `0.0` a `0.2` para código de backend, funciones matemáticas, optimización y tests unitarios (determinismo y consistencia matemática).
  - `0.5` a `0.7` únicamente para explicaciones conceptuales, redacción de documentación y ayuda al usuario.
- **Top-P:** `0.1` a `0.2` para código financiero.
- **Ventana de Contexto:** Minimizar ruido innecesario; enfocarse en el módulo actual respetando las interfaces ya definidas.

---

## 3. Directivas de Arquitectura y Calidad de Código

1. **Aislamiento del Núcleo Financiero (`backend/finance/`):**
   - El cálculo financiero debe consistir en **funciones puras** (sin efectos secundarios, sin I/O, sin llamadas directas a red ni base de datos).
   - Debe ser 100% testeable sin conexión a internet y sin servidor activo.
   - Usar `numpy`, `pandas` y `scipy.optimize` con tipado estricto (`typing` / anotaciones de tipo).

2. **Rigor Matemático y Verificación:**
   - **Tolerancia cero a alucinaciones numéricas:** todo cálculo debe estar validado con tests unitarios con soluciones analíticas conocidas o casos de prueba deterministas.
   - Retornos: utilizar retornos logarítmicos $r_t = \ln(P_t / P_{t-1})$.
   - Covarianza: matriz de covarianza insesgada ($N-1$).
   - Anualización: explícita según activo ($k = 252$ para mercado bursátil tradicional, $k = 365$ para crypto).
   - Restricciones de Markowitz por defecto:
     - Long-only: $w_i \ge 0 \quad \forall i$
     - Fully invested: $\sum_{i=1}^n w_i = 1$
   - Manejo estricto de casos de borde: series vacías, activos con varianza cero, matrices singulares (no invertibles), activos con datos desalineados en fechas.

3. **Caché y Fuentes de Datos (`backend/market/`):**
   - Nunca llamar a APIs externas dentro de loops de cálculo.
   - Toda llamada a APIs de mercado (`yfinance`, `CoinGecko`, `dolarapi`) debe contar con manejo de errores, timeouts y persistencia en caché/base de datos.

4. **API y Backend (`backend/`):**
   - FastAPI con schemas de validación `pydantic`.
   - Códigos de estado HTTP semánticos y mensajes de error descriptivos.

---

## 4. Registro y Bitácora de Interacciones

Cada intervención relevante del agente debe quedar registrada o ser compatible con la bitácora `docs/uso-de-ia.md`, documentando:
1. Objetivo / Prompt ejecutado.
2. Componentes generados o modificados.
3. Método de verificación matemática y resultados de la suite de pruebas (`pytest`).
4. Errores o desviaciones detectadas y su corrección explícita.

