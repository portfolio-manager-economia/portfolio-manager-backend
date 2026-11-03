# Probar la importación de carteras en local

La función analiza una captura con Gemini y presenta un borrador editable. Analizar no guarda posiciones. Solo se guardan después de completar los campos requeridos y confirmar la revisión. No se necesita configurar una API por usuario.

## Configurar Gemini una vez como desarrollador

1. Abrir https://aistudio.google.com/api-keys con tu cuenta de Google y crear una clave para el proyecto que vas a usar.
2. Consultar https://aistudio.google.com/rate-limit para comprobar modelos y cuotas disponibles. El nivel gratuito no tiene una cantidad universal garantizada de importaciones.
3. En `portfolio-manager-backend/.env`, agregar:

```dotenv
GEMINI_API_KEY=tu_clave_real
GEMINI_MODEL=gemini-3.5-flash-lite
```

El modelo indicado es el valor inicial de la aplicación. Si tu proyecto no lo ofrece, elegir el identificador de un modelo con entrada de imágenes y salida JSON estructurada disponible en tu cuenta. La disponibilidad y gratuidad deben verificarse en AI Studio. No usar un modelo de generación de imágenes.

La clave solo pertenece al backend: no ponerla en variables `VITE_`, el navegador ni Git. Reiniciar el backend al modificar `.env`. Las cuotas se comparten entre todos los usuarios de la aplicación. La aplicación además limita el análisis a 2 solicitudes por minuto y 10 por hora por usuario, en memoria del proceso; este límite se reinicia con el servidor y no sustituye un límite distribuido para producción.

Las capturas se envían al proveedor. La aplicación no persiste imágenes ni respuestas completas del proveedor. En el nivel gratuito, Google puede usar el contenido para mejorar sus productos: probar con datos ficticios o imágenes recortadas sin datos personales. Consultar los términos vigentes del proveedor antes de usar carteras reales.

## Levantar backend — terminal PowerShell 1

Desde la raíz `E:\Cosas\Facultad\eco y finanzas\proyecto`:

```powershell
cd "E:\Cosas\Facultad\eco y finanzas\proyecto\portfolio-manager-backend"
# Solo si todavía no existe el entorno:
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Si no existe .env, copiar .env.example y completar la configuración.
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

No hace falta activar el entorno virtual. Mantener `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` y `CORS_ORIGINS=http://localhost:5173`. Salud: http://localhost:8000/api/health. API: http://localhost:8000/docs.

## Levantar frontend — terminal PowerShell 2

```powershell
cd "E:\Cosas\Facultad\eco y finanzas\proyecto\portfolio-manager-frontend"
npm.cmd install
npm.cmd run dev -- --host localhost --port 5173 --strictPort
```

Se usa `npm.cmd` para evitar el bloqueo de `npm.ps1` de PowerShell sin cambiar la política de ejecución del equipo.

El `.env` del frontend debe contener:

```dotenv
VITE_API_URL=http://localhost:8000/api
VITE_SUPABASE_URL=https://tu-proyecto.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=tu_clave_publicable
```

Usar el mismo proyecto Supabase en ambos servicios. Si ya estaba configurado, conservar los valores existentes. La tabla `positions` y RLS requieren la migración original del README; esta función no necesita una migración nueva. Habilitar email/password y autorizar `http://localhost:5173` en Auth. No usar claves `service_role`.

## Prueba manual antes de commitear

1. Abrir http://localhost:5173 e iniciar sesión con un usuario de prueba.
2. En **Mi Portafolio**, pulsar **Importar cartera desde captura**.
3. Descargar la captura completa desde el enlace del modal, seleccionarla y pulsar **Analizar captura**. También está en `portfolio-manager-frontend/public/examples/cartera-completa.png`.
4. Comprobar las tres filas contra la imagen. Son datos ficticios: AAPL, 5, USD, 150, 2024-01-15; MSFT, 2, USD, 300, 2024-02-20; BTC-USD, 0.01, USD, 35000, 2024-03-10. Las tres compras están en USD y no necesitan MEP.
5. Antes de confirmar, verificar que la cartera no cambió. Marcar la casilla de revisión e importar. Deben aparecer tres posiciones nuevas; recargar la página para comprobar persistencia.
6. Probar `cartera-incompleta.png`: la fecha de AAPL y el precio de compra de MSFT deben quedar vacíos. El botón permanece deshabilitado hasta completarlos y revisar. No deben sustituirse con la fecha actual ni con un precio de mercado.
7. Volver a analizar la misma cartera: deben verse los avisos de activos repetidos. Cancelar esta prueba para evitar agregar las mismas tenencias otra vez. Una importación nueva es una carga nueva: solo los reintentos de un mismo envío tienen protección automática contra duplicados.
8. Probar quitar una fila, editar un ticker y cancelar sin importar. Ninguna de esas acciones debe guardar posiciones.
9. Eliminar las posiciones de prueba al terminar. Con un segundo usuario, comprobar que no vea las posiciones del primero.

La extracción puede equivocarse: la revisión es obligatoria. Si solo hay precios promedio de varios lotes, se necesita completar las compras individuales. Una imagen sin posiciones muestra un aviso. Formatos admitidos: PNG, JPEG y WebP, hasta 5 MB y 20 megapíxeles.

## Errores y reintentos

- Lectura no disponible: revisar `GEMINI_API_KEY` y reiniciar backend.
- No se pudo interpretar: revisar modelo habilitado, clave y legibilidad; no se muestran errores privados del proveedor en la interfaz.
- Cuota alcanzada: revisar AI Studio o esperar. Las llamadas fallidas pueden consumir cuota.
- Moneda incorrecta o ticker desconocido: corregir el borrador. `AAPL` (acción estadounidense) y `AAPL.BA` (CEDEAR) son instrumentos distintos.
- MEP histórico no disponible: ingresar el tipo de cambio efectivo de la compra en la fila ARS.
- Guardado con resultado incierto: usar **Reintentar importación** en el mismo modal. El envío conserva su identificador y sus datos; IDs deterministas más `ON CONFLICT DO NOTHING` evitan duplicarlo. La inserción de las filas es una sola operación atómica. No cerrar y crear una importación nueva para reintentar.

## Verificaciones automáticas

Backend:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend:

```powershell
npm.cmd test
npm.cmd run lint
npm.cmd run build
```

Las pruebas usan Gemini, mercado y almacenamiento simulados: verifican contratos, validación, errores y reintentos. No sustituyen la prueba manual real con tu clave Gemini y tu cuenta Supabase. No considerar verificada la integración externa hasta completar los pasos anteriores.

Referencias: https://ai.google.dev/gemini-api/docs/image-understanding y https://ai.google.dev/gemini-api/docs/structured-output.
