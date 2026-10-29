# Portfolio Manager · Backend

Trabajo práctico de Economía y Finanzas: seguimiento de inversiones y optimización de Markowitz con FastAPI, NumPy, pandas y SciPy. El frontend está en el repositorio hermano `portfolio-manager-frontend`.

## Funcionalidades implementadas

- Sesiones de Supabase Auth: el backend valida el JWT contra Auth antes de acceder a posiciones o ejecutar optimizaciones.
- Persistencia en PostgreSQL de Supabase, por usuario. Las llamadas a PostgREST usan el JWT del usuario para conservar las políticas RLS. No hay usuario compartido ni fallback a SQLite.
- Alta, listado y eliminación de posiciones. Se guardan cantidad, precio, fecha, moneda y MEP de compra. No hay edición de posiciones.
- Valuación y ganancia/pérdida en USD. Precios de compra y cotización permanecen en la moneda nativa; nunca se suman pesos con dólares.
- Cotizaciones intradía de Yahoo cuando están disponibles, con último cierre como alternativa fechada. Caché con vencimiento de 60 segundos para cotizaciones, una hora para históricos, y bypass al solicitar actualización manual.
- Dólar actual desde DolarAPI y MEP histórico de venta desde ArgentinaDatos. No se generan tipos de cambio ni precios ficticios cuando falla un proveedor.
- Frontera eficiente (hasta 30 puntos), mínima varianza y máximo Sharpe, con pesos no negativos que suman uno.
- Comparación contra la cartera actual: pesos por valor de mercado en USD, agregando compras del mismo ticker. Las métricas usan la misma moneda, ventana y calendario que las alternativas óptimas.
- Anualización de 365 para carteras exclusivamente cripto y 252 para tradicionales o mixtas, alineadas a sesiones comunes.

## Crear y conectar el proyecto Supabase

1. Crear un proyecto **nuevo** en Supabase. Elegir organización, región y plan en la cuenta; la contraseña de PostgreSQL no se usa en el código de esta aplicación.
2. Ejecutar `supabase/migrations/202610280001_positions.sql` en el SQL Editor del proyecto nuevo. Crea la tabla, índice y políticas RLS. También puede aplicarse con Supabase CLI enlazada al proyecto (`supabase db push`). La migración debe ejecutarse una vez.
3. Ejecutar `supabase/tests/positions_rls.sql` en ese proyecto de desarrollo. Verifica lectura propia, invisibilidad de otro usuario, bloqueo de inserción y eliminación ajena y denegación al rol anónimo. Termina en `rollback`, sin conservar usuarios ni posiciones de prueba.
4. En Authentication, habilitar email/password, mantener confirmación por correo y configurar Site URL y Redirect URLs para `http://localhost:5173` (y el dominio real cuando se despliegue).
5. Copiar `.env.example` a `.env`. Completar `SUPABASE_URL` y `SUPABASE_PUBLISHABLE_KEY` con la URL y clave **publicable** del mismo proyecto. Se admite también la clave `anon` heredada; no usar `service_role` ni claves secretas en el frontend.
6. Configurar el frontend con la misma URL y clave publicable. Registrarse, confirmar el correo e iniciar sesión.

El esquema y el cliente están implementados en este repositorio. Aplicar la migración, probar RLS y confirmar login/persistencia contra un proyecto real requieren acceso a la cuenta Supabase; las pruebas Python no sustituyen esa validación.

## Instalación en Windows / PowerShell

Python 3.11+:

```powershell
py -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Completar la configuración antes de iniciar sesión.
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Variables:

| Variable | Uso |
| --- | --- |
| `SUPABASE_URL` | URL del proyecto |
| `SUPABASE_PUBLISHABLE_KEY` | Clave publicable o `anon` |
| `CORS_ORIGINS` | Orígenes separados por coma; por defecto `http://localhost:5173` |

No subir `.env` a Git. La documentación interactiva de la API está en `http://localhost:8000/docs`.

## Contrato de API

`GET /api/health` y `GET /api/market/dolar` son públicos. Los demás endpoints requieren `Authorization: Bearer <access_token>` de Supabase.

| Método | Ruta | Resultado |
| --- | --- | --- |
| GET | `/api/positions?refresh=false` | Posiciones del usuario, precios fechados y valores USD |
| POST | `/api/positions` | Crear posición; infiere MEP histórico de compra si falta |
| DELETE | `/api/positions/{uuid}` | Eliminar posición propia; 404 si no es accesible |
| POST | `/api/optimize` | Frontera, óptimos y comparación opcional |

Ejemplo de posición:

```json
{"ticker":"GGAL.BA","asset_type":"stock","currency":"ARS","quantity":10,"buy_price":1000,"buy_date":"2024-01-15","buy_fx_rate":1100}
```

`buy_fx_rate` es ARS por USD y puede omitirse para buscar la última observación histórica no posterior a la compra, como máximo diez días antes. Para compras en USD se guarda 1. Bonos soberanos: `quantity` representa valor nominal y `buy_price` precio por 100 VN.

Ejemplo de optimización:

```json
{"tickers":["AAPL","GGAL.BA"],"period":"1y","risk_free_rate":0.04,"allow_short":false,"compare_current":true}
```

La comparación exige incluir todos los tickers de la cartera para evitar omitir posiciones; pueden agregarse activos nuevos con peso actual cero. Los pesos se calculan en el servidor, nunca se aceptan importes o IDs de otro usuario desde el navegador. La tasa es anual en USD; `0.04` es solo un ejemplo editable, no una tasa de mercado vigente.

## Metodología y límites

Ver `docs/modelo-economico.md` para las ecuaciones. Se calculan retornos logarítmicos, covarianza muestral N−1 y optimización media-varianza long-only. Los precios históricos en ARS se convierten con el MEP de su fecha, sin usar dólar actual, rellenar con FX futuro ni inventar datos faltantes. Se informan fechas efectivas y observaciones; los huecos reducen la muestra.

Las cotizaciones pueden estar demoradas o faltar para determinados tickers, especialmente bonos. El catálogo del frontend no garantiza cobertura de Yahoo. Si no hay precio o MEP actual, la posición se informa sin valuación, se ocultan totales incompletos y se bloquea la comparación. La fecha de la cotización permite distinguir una consulta reciente de un precio antiguo. Las cachés son en memoria del proceso, no una base histórica permanente.

Las carteras mixtas usan 252 sesiones comunes: el retorno cripto del fin de semana queda incluido entre viernes y lunes. Se trata de una aproximación de calendario; los resultados son estimaciones históricas, no un backtest de movimientos ni una promesa de rentabilidad. No se modelan impuestos, costos, dividendos cobrados, cupones cobrados ni riesgo de ejecución.

## Pruebas

```powershell
.venv/Scripts/python.exe -m pytest -q
```

La suite no usa internet ni datos de producción. Cubre soluciones financieras deterministas, conversión histórica, calendario cripto/mixto, pesos por valor de mercado, lotes duplicados, validación de sesión, propagación del JWT, filtros por usuario, caché y fallos de proveedores. Las pruebas RLS reales se ejecutan por separado con el SQL indicado arriba.

Fuentes: [Supabase Auth](https://supabase.com/docs/guides/auth), [RLS](https://supabase.com/docs/guides/database/postgres/row-level-security), [DolarAPI](https://dolarapi.com/docs/argentina/), [ArgentinaDatos](https://argentinadatos.com/docs/operations/get-cotizaciones-dolares).
