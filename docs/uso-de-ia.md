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

## 2026-10-28 · Supabase, comparación, cotizaciones y moneda común

- **Solicitud:** completar las diferencias detectadas entre README e implementación y usar un proyecto nuevo de Supabase.
- **Cambios:** SQLite y usuario compartido reemplazados por PostgREST con JWT del usuario; verificación de sesión contra Supabase Auth; migración de posiciones e índice por usuario, RLS y script SQL de aislamiento. Frontend con registro, confirmación de email, login y logout.
- **Finanzas:** valuación y P&L en USD, moneda nativa explícita, FX histórico de compra guardado, MEP histórico por fecha para optimización, pesos actuales agregados por valor de mercado y comparación con GMVP/tangencia. Anualización 365 solo cripto y 252 en sesiones comunes para carteras tradicionales/mixtas. El rendimiento ponderado logarítmico se documentó como aproximación media-varianza.
- **Mercado:** TTL de 60 s para cotizaciones y una hora para históricos; actualización manual evita caché. Consulta automática cada 60 s, fecha por cotización, último cierre fechado si no hay intradía y errores visibles. Se eliminaron tasas de dólar ficticias y el fallback al precio de compra.
- **Verificación matemática:** casos analíticos de conversión y P&L (una subida de 50% en ARS con duplicación del FX implica -25% en USD), covarianza N−1 y anualización 365, movimiento cripto acumulado entre viernes y lunes, agregación de lotes y pesos actuales 60/40 calculados por valor de mercado. Se conserva la suite analítica anterior del optimizador.
- **Resultados:** 42 pruebas Python aprobadas; 7 pruebas frontend aprobadas; build de producción y lint exitosos. Python muestra una advertencia de deprecación de Starlette/TestClient relativa a httpx. Las pruebas de sesión, almacenamiento y mercado usan mocks; no prueban una cuenta Supabase real.
- **Verificación externa:** consulta real de AAPL intradía y optimización AAPL/GGAL.BA en USD con ventana de seis meses y 30 puntos de frontera completadas. Yahoo no entregó AL30.BA durante el primer intento de FX implícito: se reemplazó esa dependencia por ArgentinaDatos, cuyo endpoint histórico se verificó con una respuesta real. No se fabricaron datos para salvar el error.
- **Correcciones durante implementación:** se actualizó el export de backend/db/__init__.py al retirar init_db; se descartaron resultados previos al cambiar parámetros; el formulario conserva los datos cuando falla el alta; se respeta una tasa libre de riesgo de cero; se distinguieron posiciones de tickers únicos al habilitar optimización.
- **Pendiente externo:** crear y configurar el proyecto Supabase, aplicar migración, ejecutar supabase/tests/positions_rls.sql y comprobar registro/persistencia reales. No hay integración Supabase conectada ni navegador disponible. No se ejecutó SQL contra una cuenta ni se crearon recursos externos. README y .env.example describen la configuración pendiente sin claves secretas.

## 2026-11-03 · Importación de carteras desde capturas

- **Solicitud:** importar un portfolio externo desde una captura, interpretar los datos con IA, completar los faltantes, revisar y confirmar; configuración de Gemini solo por el desarrollador y ejecución local documentada.
- **Cambios:** endpoint autenticado de análisis Gemini con salida JSON validada; PNG/JPEG/WebP hasta 5 MB y 20 MP; límites en memoria de 2 análisis/minuto y 10/hora por usuario; campos desconocidos nulos y errores de proveedor sin contenido privado. La imagen se transmite a Gemini sin persistirse en la aplicación.
- **Frontend:** modal con vista previa, edición de filas, avisos de faltantes y activos repetidos, eliminación de filas y revisión obligatoria. Clave solo en backend. Dos capturas ficticias descargables para pruebas completas e incompletas.
- **Persistencia:** validación de todas las filas, monedas y MEP antes de una única inserción PostgREST con JWT del usuario y RLS. IDs deterministas por usuario/importación/fila y resolución ignore-duplicates para reintentos de un mismo envío. El frontend conserva el identificador y bloquea el payload cuando el resultado es incierto. Una importación nueva de la misma captura sí puede duplicar tenencias: se advierte al usuario. No se modifica el núcleo financiero ni se requieren migraciones nuevas.
- **Verificación:** 51 pruebas Python y 14 pruebas frontend aprobadas; lint sin observaciones y build exitoso. Las pruebas nuevas verifican autenticación, imágenes inválidas, campos desconocidos, cuota, errores del proveedor, validación completa antes de insertar, propagación JWT, IDs estables y revisión/reintento en frontend. Sin cambios matemáticos; se mantiene toda la suite analítica existente.
- **Correcciones durante el trabajo:** instalación de la nueva dependencia Pillow en el entorno virtual; uso de npm.cmd por la política de PowerShell; corrección del transporte de Prefer para el insert por lote. Las fallas de validación permiten editar y los resultados inciertos preservan el mismo envío.
- **Límites de verificación:** Gemini y Supabase simulados en pruebas; faltaba GEMINI_API_KEY en el .env local, por lo que no se ejecutó extracción real ni escritura contra Supabase. La configuración existente de Supabase se conservó. Guía manual en docs/probar-importacion.md. Build advierte un chunk mayor a 500 kB y Starlette informa deprecación de TestClient/httpx; ambos controles finalizan correctamente.

## 2026-11-03 · Corrección y verificación real de Gemini

- **Problema observado:** la UI mostraba «No se pudo interpretar» ante un rechazo HTTP 404 del proveedor. El modelo gemini-2.5-flash ya no estaba disponible para usuarios nuevos aunque aparecía en el listado de modelos.
- **Diagnóstico real:** la clave respondió correctamente al listado de modelos. Gemini 3.8 Flash y 3.1 Flash Lite respondieron 503 por saturación. Gemini 3.5 Flash Lite respondió correctamente a texto e imágenes; rechazaba el esquema con maxItems (400). Se aisló el parámetro mediante solicitudes mínimas.
- **Corrección:** modelo inicial y .env local cambiados a gemini-3.5-flash-lite. Esquema responseSchema compatible sin restricciones no admitidas; la validación estricta y el máximo de 40 filas permanecen en Pydantic. Errores 400/401/403/404 y 5xx del proveedor se distinguen de imágenes ilegibles. Logs limitados a modelo y código HTTP, sin claves ni contenido de imágenes.
- **Verificación externa:** extracción real de la captura ficticia completa (AAPL/MSFT/BTC), de la incompleta (fecha de AAPL y precio de MSFT correctamente nulos) y de la captura pública Binance indicada por el usuario (ADA/TRX/XRP/LTC/AAVE con cantidades y costos/fechas nulos). Ninguna de estas comprobaciones guardó posiciones en Supabase.
- **Pruebas:** 53 pruebas Python aprobadas. Backend reiniciado con acceso de red. Persistencia real de importación pendiente de la confirmación manual del usuario en la página.

## 2026-11-03 · Logos y búsqueda de activos al agregar posiciones

- **Solicitud:** mostrar logos en la columna Activo y sumar búsqueda por nombre/ticker con sugerencias del proveedor, conservando el catálogo y dejando la entrada manual como última opción.
- **Implementación:** módulo market/assets.py con Yahoo Search, timeout de 10 segundos, caché acotada de una hora y filtrado a instrumentos compatibles con ARS/USD. Endpoints autenticados para buscar y consultar moneda real y cotización fechada. La búsqueda diferencia acciones estadounidenses, CEDEARs conocidos y criptomonedas; instrumentos argentinos desconocidos requieren confirmar el tipo. ETFs permanecen en stock, de acuerdo con el esquema existente.
- **Frontend:** búsqueda con espera de 350 ms, cancelación de solicitudes antiguas, resultados con nombre, ticker, mercado, moneda y logo; verificación al seleccionar y vista de última cotización. Se conserva el precio de compra vacío para ingreso del usuario. Catálogo y modo manual continúan disponibles. El guardado se bloquea mientras se verifica la selección.
- **Logos:** URL derivada del símbolo hacia Financial Modeling Prep, sin nueva clave y sin llamadas de precios por imagen. Adaptación para criptomonedas, CEDEARs y algunos emisores locales; iniciales cuando falta o falla la imagen. Los bonos soberanos no reciben logos de empresas. No se altera la persistencia ni el núcleo financiero.
- **Verificación real:** búsquedas VTI, Apple, AAPL.BA y Bitcoin respondieron con símbolos compatibles; cotización de VTI en USD obtenida con fecha del proveedor. Logos AAPL.BA, ADA-USD y VTI respondieron HTTP 200 image/png. Ambas aplicaciones locales respondieron 200 y OpenAPI incluye las rutas nuevas. No se guardaron posiciones reales durante estas verificaciones.
- **Pruebas:** 57 pruebas Python y 17 pruebas frontend aprobadas; lint y build exitosos. Casos nuevos verifican filtros de mercado, caché, clasificación conservadora, autenticación, moneda del proveedor, selección de un símbolo fuera del catálogo, resultados antiguos ignorados, entrada manual ante error y reemplazo visual ante un logo fallido. Se ajustaron selectores de las pruebas para distinguir los campos de sus botones de ayuda. Se conserva la suite matemática sin modificar sus cálculos.
- **Alcance:** Yahoo puede no tener precios de todos los activos encontrados; se informa la ausencia y se valida moneda antes del alta. Logos opcionales dependen de disponibilidad externa. Estas funciones no consumen Gemini. No hay nuevas variables de entorno ni migraciones.
