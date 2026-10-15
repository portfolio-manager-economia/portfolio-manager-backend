# Bitácora de Interacciones y Uso de IA

Este documento registra sistemáticamente el uso de asistentes de Inteligencia Artificial (Antigravity) a lo largo del desarrollo de **Portfolio Manager**, conforme a los criterios de evaluación y rigor académico exigidos por la cátedra de Economía y Finanzas.

---

## Sesión 1: Arquitectura, Núcleo Financiero, API REST y Frontend

- **Fecha:** 2026-10-15
- **Objetivos / Prompts del Usuario:**
  1. *"Buenas ahi te subi un proyecto de economia y finanzas, tambien esta la carpeta de la materia, donde estan las consignas del tp, y el read me. aviasame y arrancamos a codear . que hacemos primero?"*
  2. *"el readme.md que te subi"*
  3. *"capaz deberia ser en vez de para seleccioanr los tipos de acciones, bonos cedears, que aparezca una lista de los que hay asi no escribimos cualquier cosa y seleccionamos uno o varios. dfale?"*

- **Parámetros del Modelo y Configuración:**
  - **Herramienta:** Google Antigravity IDE (Gemini 3.8 Flash).
  - **Temperatura:** 0.1 (cálculo financiero, backend determinista y tests) / 0.5 (documentación y UI).
  - **Top-P:** 0.15.
  - **Directivas operativas:** Reglas establecidas en `AGENTS.md` (funciones puras, tolerancia cero a alucinaciones de precios, tipado estricto, tests con casos analíticos).

- **Componentes Creados y Mejorados:**
  1. **Directivas y Rigor:**
     - `AGENTS.md`: Convenciones para desarrollo asistido por IA, arquitectura desacoplada y verificación matemática.
     - `docs/modelo-economico.md`: Documentación formal de la Teoría Moderna de Portafolios (Markowitz), retornos logarítmicos, covarianza insesgada ($N-1$), anualización ($k=252$ vs $k=365$) y supuestos.
  2. **Núcleo Financiero Puro (`backend/finance/`):**
     - `returns.py`: Cálculo de retornos logarítmicos $r_t = \ln(P_t / P_{t-1})$ y alineación multi-activo por fechas en común.
     - `metrics.py`: Retornos medios esperados anualizados, matriz de covarianza insesgada anualizada, retorno/volatilidad de cartera ($\mu_p = w^\top \mu, \sigma_p = \sqrt{w^\top \Sigma w}$), y ratio de Sharpe ($S = (\mu_p - r_f) / \sigma_p$).
     - `optimizer.py`: Mínima Varianza Global (GMVP), Máximo Ratio de Sharpe (Tangencia) y Frontera Eficiente mediante `scipy.optimize.minimize` (algoritmo SLSQP) con restricciones $\sum w_i = 1$ y $w_i \ge 0$.
  3. **Servicios de Mercado y Persistencia (`backend/market/`, `backend/db/`):**
     - `prices.py`: Descarga y caché en memoria con `yfinance` para acciones, CEDEARs (`.BA`) y criptomonedas.
     - `dolar.py`: Integración con `dolarapi.com` para cotizaciones del dólar oficial, MEP, CCL y Blue.
     - `storage.py`: Persistencia local SQLite (`portfolio.db`) para posiciones con operaciones CRUD completas.
  4. **Catálogo Oficial y Prevención de Errores de Tipeo (`frontend/src/data/assets.js`):**
     - Catálogo estructurado de activos con sus nombres y tickers oficiales de Yahoo Finance:
       - CEDEARs: `AAPL.BA`, `MSFT.BA`, `GOOGL.BA`, `TSLA.BA`, `NVDA.BA`, `MELI.BA`, `KO.BA`, `SPY.BA`.
       - Merval Argentina: `GGAL.BA`, `YPFD.BA`, `PAMP.BA`, `BMA.BA`, `ALUA.BA`.
       - Acciones USA: `AAPL`, `MSFT`, `GOOGL`, `AMZN`, `TSLA`, `NVDA`, `SPY`.
       - Bonos Argentinos: `AL30D.BA`, `GD30D.BA`.
       - Criptomonedas: `BTC-USD`, `ETH-USD`, `SOL-USD`.
     - Presets preconfigurados en un solo clic ("Cartera Tecnológica", "CEDEARs Diversificados", "Merval Líderes", "Cripto & Tech").
  5. **Frontend React + Vite (`frontend/`):**
     - `PositionsTable.jsx`: Grilla interactiva de posiciones, P&L no realizado, métricas globales de cartera.
     - `AddPositionModal.jsx`: Modal con selector desplegable clasificado por categorías para evitar errores de tipeo al cargar posiciones.
     - `App.jsx`: Panel de optimización con selector visual interactivo mediante botones/chips (+/-), eliminando el ingreso manual de tickers erróneos (como "APPLE" o "Tesla").
     - `EfficientFrontierChart.jsx`: Gráfico de dispersión interactivo con `Recharts` mostrando la frontera eficiente, GMVP y tangencia.
     - `OptimalPortfoliosCard.jsx`: Comparación detallada de ponderaciones óptimas.
     - `DolarTicker.jsx`: Cinta superior con cotizaciones del dólar en vivo.

- **Método de Verificación Matemática y Resultados de Pruebas:**
  - **Ejecución de `pytest -v`:** **18 tests ejecutados, 18 aprobados (100% éxito)**.
  - **Cobertura de código (`pytest --cov=backend`): 86% total**.
  - **Pruebas de verificación analítica cerrada:**
    - Cartera de 2 activos: coincidencia exacta ($10^{-12}$) con la fórmula manual $\sigma_p = \sqrt{w_1^2 \sigma_1^2 + w_2^2 \sigma_2^2 + 2 w_1 w_2 \operatorname{Cov}_{12}}$.
    - GMVP de 2 activos: coincidencia con la solución analítica cerrada $w_1^* = \frac{\sigma_2^2 - \sigma_{12}}{\sigma_1^2 + \sigma_2^2 - 2 \sigma_{12}}$.
    - Restricciones de Markowitz comprobadas: $\sum w_i = 1.0$ y $w_i \ge 0.0$.
