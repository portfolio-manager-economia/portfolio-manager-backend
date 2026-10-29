# Modelo Económico y Financiero: Teoría Moderna de Portafolios (Markowitz)

Este documento detalla las bases teóricas, las fórmulas matemáticas y los supuestos implementados en el núcleo financiero de la aplicación.

---

## 1. Retornos Logarítmicos

Dado el precio de cierre ajustado de un activo $i$ en el momento $t$, $P_{i,t}$, el retorno logarítmico (o continuamente compuesto) se define como:

$$
r_{i,t} = \ln\left(\frac{P_{i,t}}{P_{i,t-1}}\right)
$$

### Propiedades clave:
- **Aditividad temporal:** $\sum_{t=1}^T r_{i,t} = \ln(P_{i,T} / P_{i,0})$.
- **Estabilidad numérica:** Previene asimetrías de escala y es adecuado para series temporales financieras.

---

## 2. Parámetros Estadísticos de los Activos

Para una serie de retornos de longitud $T$:

### Retorno Medio Diario ($\mu_i$):
$$
\mu_i = \frac{1}{T}\sum_{t=1}^{T} r_{i,t}
$$

### Matriz de Covarianza Muestral ($\Sigma$):
Para los activos $i, j$:
$$
\Sigma_{ij} = \operatorname{Cov}(r_i, r_j) = \frac{1}{T - 1}\sum_{t=1}^T (r_{i,t} - \mu_i)(r_{j,t} - \mu_j)
$$

---

## 3. Retorno y Riesgo de la Cartera

Sea $w = (w_1, w_2, \dots, w_n)^\top$ el vector de ponderaciones o pesos de los activos en el portafolio:

- **Retorno esperado de la cartera ($\mu_p$):**
  $$
  \mu_p = w^\top \mu = \sum_{i=1}^n w_i \mu_i
  $$

- **Varianza de la cartera ($\sigma_p^2$):**
  $$
  \sigma_p^2 = w^\top \Sigma w = \sum_{i=1}^n \sum_{j=1}^n w_i w_j \Sigma_{ij}
  $$

- **Volatilidad / Desvío estándar de la cartera ($\sigma_p$):**
  $$
  \sigma_p = \sqrt{w^\top \Sigma w}
  $$

---

## 4. Anualización

Para comparar retornos y volatilidad con tasas libres de riesgo anuales ($r_f$), se anualizan los parámetros utilizando el factor $k$ (días hábiles u operativos):
- Activos bursátiles tradicionales (Acciones, CEDEARs, Bonos): $k = 252$.
- Carteras compuestas únicamente por criptoactivos (operan 24/7): $k = 365$.
- Carteras mixtas: $k = 252$ para **todas** las columnas de la matriz, luego de alinear precios a sesiones comunes. El retorno cripto entre viernes y lunes incluye el fin de semana. No se multiplican columnas de una misma covarianza por calendarios diferentes.

### Moneda de análisis y comparación

Todos los retornos, pesos, métricas y totales se expresan en USD. Los precios históricos en ARS se dividen por la cotización MEP de venta de **esa fecha**, publicada por ArgentinaDatos. Se conservan fechas con precios y FX disponibles para todos los activos; no se rellenan huecos con datos futuros ni con el dólar actual. La respuesta informa el período efectivo y el número de observaciones.

El costo de compra en ARS se convierte con el MEP de compra guardado (ingresado por el usuario o estimado con la última observación histórica anterior a la compra, como máximo 10 días antes). La valuación actual usa la cotización MEP de venta de DolarAPI. Las posiciones duplicadas de un ticker se agregan por valor de mercado para obtener los pesos de la cartera actual. Los bonos soberanos se cargan por valor nominal y precio por 100 VN.

La comparación mide la cartera actual y las óptimas sobre la misma ventana, moneda, tasa libre de riesgo y matriz de covarianza. Usa pesos actuales, sin reconstruir un backtest de transacciones. El retorno ponderado de retornos logarítmicos es la aproximación media-varianza usada por este modelo; no equivale exactamente al retorno realizado de una cartera rebalanceada.

$$
\mu_{anual} = k \cdot \mu_{diario}
$$
$$
\Sigma_{anual} = k \cdot \Sigma_{diario}
$$
$$
\sigma_{anual} = \sqrt{k} \cdot \sigma_{diario}
$$

---

## 5. Ratio de Sharpe

Mide el exceso de retorno por unidad de riesgo total asumido frente a la tasa libre de riesgo ($r_f$):

$$
S = \frac{\mu_p - r_f}{\sigma_p}
$$

---

## 6. Problemas de Optimización

### Restricciones Generales (Sin ventas en corto - Long Only):
$$
\sum_{i=1}^n w_i = 1 \quad \text{y} \quad 0 \le w_i \le 1 \quad \forall i = 1, \dots, n
$$

### A. Portafolio de Mínima Varianza Global (GMVP):
Encuentra la combinación de pesos que minimiza el riesgo total sin importar el retorno:
$$
\min_{w} \; w^\top \Sigma w \quad \text{s.a.} \quad \sum w_i = 1, \; w_i \ge 0
$$

### B. Portafolio de Máximo Ratio de Sharpe (Tangencia):
Maximiza la pendiente de la Línea de Asignación de Capital (CAL):
$$
\max_{w} \; \frac{w^\top \mu - r_f}{\sqrt{w^\top \Sigma w}} \quad \text{s.a.} \quad \sum w_i = 1, \; w_i \ge 0
$$

### C. Frontera Eficiente:
Para un conjunto de retornos objetivo $\mu^* \in [\min(\mu), \max(\mu)]$, se resuelve:
$$
\min_{w} \; w^\top \Sigma w \quad \text{s.a.} \quad w^\top \mu = \mu^*, \; \sum w_i = 1, \; w_i \ge 0
$$

---

## 7. Supuestos y Limitaciones

1. **Normalidad de los Retornos:** Se asume que los retornos siguen una distribución normal multivariada. En la práctica, activos como criptomonedas y acciones en mercados emergentes presentan colas pesadas (*fat tails*) y asimetría (*skewness*).
2. **Estacionariedad:** Se asume que las medias y covarianzas históricas reflejan la distribución futura de retornos.
3. **Costos de Transacción e Impuestos:** En esta etapa inicial se consideran nulos o despreciables.

