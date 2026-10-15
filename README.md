# Portfolio Manager

Aplicacion web para el seguimiento y la optimizacion de un portfolio de inversion (acciones, CEDEARs, bonos y crypto), con datos reales de mercado y analisis cuantitativo basado en el modelo de Markowitz.

Trabajo practico de Economia y Finanzas. Eje tematico: Finanzas Cuantitativas y Personales (Optimizador de Portafolios), desarrollado con asistencia de agentes de IA (Antigravity).

---

## 1. Problema economico

Un inversor reparte su capital entre varios activos. Cada activo tiene un retorno esperado y un riesgo, y los activos se mueven de forma correlacionada. El problema es decidir en que proporcion mantener cada uno para obtener el mejor retorno posible para un nivel de riesgo dado.

La aplicacion permite:

1. Registrar las posiciones propias y hacer seguimiento de su valor.
2. Medir el riesgo y el retorno del portfolio actual con precios reales.
3. Calcular la frontera eficiente y los portfolios optimos.
4. Comparar el portfolio actual contra el optimo.

## 2. Modelo economico

### Retornos logaritmicos

$$
r_t = \ln\left(\frac{P_t}{P_{t-1}}\right)
$$

### Retorno esperado y covarianzas

Para cada activo $i$ se estima el retorno medio y, entre pares de activos, la covarianza:

$$
\mu_i = \frac{1}{T}\sum_{t=1}^{T} r_{i,t}
\qquad
\Sigma_{ij} = \operatorname{Cov}(r_i, r_j)
$$

### Retorno y riesgo del portfolio

Con vector de pesos $w$, vector de retornos esperados $\mu$ y matriz de covarianzas $\Sigma$:

$$
\mu_p = w^\top \mu
\qquad
\sigma_p^2 = w^\top \Sigma\, w
\qquad
\sigma_p = \sqrt{w^\top \Sigma\, w}
$$

### Ratio de Sharpe

$$
S = \frac{\mu_p - r_f}{\sigma_p}
$$

donde $r_f$ es la tasa libre de riesgo.

### Problema de optimizacion

**Minima varianza:**

$$
\min_{w} \; w^\top \Sigma\, w
$$

**Maximo Sharpe:**

$$
\max_{w} \; \frac{w^\top \mu - r_f}{\sqrt{w^\top \Sigma\, w}}
$$

**Frontera eficiente** (para cada retorno objetivo $\mu^*$):

$$
\min_{w} \; w^\top \Sigma\, w
\quad \text{s.a.} \quad
w^\top \mu = \mu^*
$$

**Restricciones comunes** (sin ventas en corto):

$$
\sum_{i=1}^{n} w_i = 1
\qquad
w_i \ge 0 \quad \forall i
$$

### Anualizacion

Con $k$ periodos de operacion por ano ($k = 252$ para activos tradicionales y $k = 365$ para crypto):

$$
\mu_{anual} = k \cdot \mu_{diario}
\qquad
\sigma_{anual} = \sqrt{k} \cdot \sigma_{diario}
$$

Si el portfolio mezcla ambos tipos de activo, las series se alinean por fechas en comun.

### Supuestos y limitaciones

- El modelo asume retornos normales. En crypto las colas son mas pesadas y el riesgo puede subestimarse.
- Los retornos historicos no garantizan retornos futuros.
- Las correlaciones no son estables y tienden a subir en periodos de crisis.
- No se consideran costos de transaccion ni impuestos.
- Los retornos esperados estimados con datos historicos son sensibles a la ventana elegida.

## 3. Arquitectura

    Frontend (React + Vite)
            |  HTTP / JSON
            v
    Backend (FastAPI, Python)
        |-- Calculo financiero (numpy, pandas, scipy)
        |-- Clientes de datos de mercado
        |-- Acceso a base de datos
            |
            v
    Supabase (PostgreSQL + Auth)

    Fuentes de datos externas:
      - yfinance: acciones, CEDEARs (sufijo .BA), bonos
      - CoinGecko o Binance: crypto
      - dolarapi.com: tipo de cambio (oficial, MEP, CCL)

Decisiones de diseno:

- El calculo financiero esta aislado de la API y de la base de datos. Son funciones puras, testeables sin servidor ni internet.
- Los precios historicos se guardan en la base (cache). Se evita depender de las APIs en cada consulta y se respetan sus limites de uso.
- Cada usuario tiene su propio portfolio, mediante Supabase Auth y reglas de acceso por fila (RLS).

## 4. Funcionalidades

| Modulo | Descripcion |
|---|---|
| Autenticacion | Registro e inicio de sesion. Cada usuario ve solo su portfolio. |
| Gestion de activos | Alta, baja y modificacion de posiciones: ticker, tipo, cantidad, precio y fecha de compra. |
| Datos de mercado | Descarga y actualizacion de precios historicos y cotizaciones actuales. |
| Seguimiento | Valor actual, ganancia o perdida por activo y total, distribucion por tipo de activo. |
| Metricas | Retorno, volatilidad, matriz de correlaciones, ratio de Sharpe. |
| Optimizacion | Frontera eficiente, portfolio de minima varianza y de maximo Sharpe. |
| Comparacion | Pesos y metricas del portfolio actual frente al optimo. |

## 5. Estructura del proyecto

    portfolio-manager/
    |-- backend/
    |   |-- main.py              # App FastAPI y rutas
    |   |-- finance/             # Retornos, metricas, optimizador (funciones puras)
    |   |-- market/              # Clientes de yfinance, CoinGecko, dolarapi
    |   |-- db/                  # Acceso a Supabase
    |   |-- schemas.py           # Validacion de datos (Pydantic)
    |-- frontend/
    |   |-- src/
    |   |   |-- components/
    |   |   |-- pages/
    |   |   |-- api/             # Llamadas al backend
    |-- tests/
    |   |-- unit/                # Calculos con valores de referencia
    |   |-- integration/         # API + base de datos
    |   |-- fixtures/            # Series de precios fijas
    |-- docs/
    |   |-- uso-de-ia.md         # Bitacora de prompts, comandos y correcciones
    |   |-- modelo-economico.md  # Formulas y supuestos
    |-- AGENTS.md                # Reglas para el agente de IA
    |-- requirements.txt
    |-- README.md

## 6. Stack

- Backend: Python 3.11+, FastAPI, Uvicorn, Pydantic
- Calculo: numpy, pandas, scipy
- Frontend: React, Vite, Recharts
- Base de datos y autenticacion: Supabase (PostgreSQL)
- Datos de mercado: yfinance, CoinGecko, dolarapi.com
- Tests: pytest, pytest-cov, httpx

## 7. Instalacion y uso

    git clone <url-del-repo>
    cd portfolio-manager

    # Backend
    python -m venv venv
    source venv/bin/activate          # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env              # completar credenciales de Supabase
    uvicorn backend.main:app --reload

    # Frontend
    cd frontend
    npm install
    npm run dev

Variables de entorno (`.env`):

    SUPABASE_URL=
    SUPABASE_KEY=

## 8. Pruebas automatizadas

    pytest -v
    pytest --cov=backend

La guia exige que los calculos esten verificados matematicamente.

Pruebas unitarias (sin internet ni base de datos):

- Portfolio de 2 activos con covarianzas conocidas: la varianza coincide con el calculo manual de la formula.
- Los pesos optimizados suman 1 y son no negativos.
- Con un solo activo, el portfolio optimo es 100% ese activo.
- Retorno logaritmico de una serie con valores simples (por ejemplo 100 -> 110) igual a ln(1.1).
- Anualizacion con el factor correcto segun el tipo de activo.
- Casos de borde: serie vacia, un solo precio, activos con desvio cero.

Pruebas de integracion:

- Carga de precios (fixture) -> calculo de metricas -> persistencia en la base.
- Endpoints de la API con datos de prueba.
- Los clientes de APIs externas se prueban con respuestas simuladas (mocks), no con llamadas reales.

## 9. Uso de IA

El proyecto se desarrolla con Antigravity. Toda la interaccion con agentes se documenta en `docs/uso-de-ia.md`.

Flujo de trabajo previsto:

| Etapa | Herramienta | Uso |
|---|---|---|
| Definicion de requerimientos | `/grill-me` | El agente entrevista al equipo antes de escribir codigo. |
| Implementacion por modulo | `/goal` | Objetivo acotado con criterio de cumplimiento (por ejemplo, "todos los tests de `finance/` pasan"). |
| Aprendizaje de errores | `/learn` | Se registran correcciones para que el agente no repita fallos. |
| Contexto de la base | MCP de Supabase | El agente consulta el esquema real de la base al escribir codigo. |
| Reglas del agente | `AGENTS.md` | Directivas del proyecto (ver abajo). |

Configuracion deliberada del agente:

- Temperatura baja (0.0 a 0.2) para codigo y calculos, con Top-P bajo para respuestas deterministas.
- Temperatura mas alta solo para lluvia de ideas o textos explicativos.
- System prompt orientado a rigor financiero: validar consistencia matematica, tipar el codigo y no inventar datos de mercado.
- Manejo de la ventana de contexto: se entregan al agente solo los archivos relevantes para cada tarea.

Uso critico de la IA. Para cada modulo se registra:

1. El prompt o comando utilizado.
2. Que genero el agente.
3. Como se verifico (tests, calculo manual).
4. Errores o alucinaciones numericas detectados y como se corrigieron.

## 10. Criterios de evaluacion

| Criterio de la guia | Como se cubre |
|---|---|
| Rigor del modelo economico | Formulas de Markowitz documentadas, supuestos y limitaciones explicitos, verificacion manual. |
| Uso critico de la IA | Bitacora en `docs/uso-de-ia.md`, configuracion de agentes justificada, errores registrados. |
| Cobertura de pruebas | Tests unitarios con valores de referencia y tests de integracion, sin dependencia de internet. |
| Contexto y datos | Codigo modular, calculo separado de la API y la base, datos reales cacheados, documentacion. |

## 11. Hoja de ruta

1. Definir requerimientos con `/grill-me` y escribir `AGENTS.md`.
2. Modulo `finance/` con sus tests (retornos, metricas, optimizador).
3. Clientes de datos de mercado y cache de precios.
4. Esquema de base de datos en Supabase y autenticacion.
5. API REST con tests de integracion.
6. Frontend en React: gestion de activos y seguimiento.
7. Frontend: metricas, frontera eficiente y comparacion.
8. Documentacion final y preparacion de la defensa.

## 12. Integrantes

- Nombre y apellido
- Nombre y apellido

## 13. Licencia

Proyecto academico. Uso educativo.
