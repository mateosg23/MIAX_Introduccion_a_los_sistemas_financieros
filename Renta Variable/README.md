# Arbitrage Study in BME (Renta Variable)

## 📌 Descripción del proyecto
Este proyecto analiza oportunidades de **arbitraje en el mercado de renta variable español (BME)** a partir de datos históricos de cotizaciones y del estado del mercado. El objetivo es estudiar ineficiencias temporales en precios y evaluar su viabilidad bajo condiciones reales de mercado.

El trabajo se centra en acciones líquidas del mercado continuo español, utilizando datos estructurados por ISIN y combinando información de precios con el estado operativo del mercado.

---

## 🎯 Objetivos
- Ingerir y limpiar grandes volúmenes de datos bursátiles.
- Analizar cotizaciones históricas de acciones del IBEX y mercado continuo.
- Cruzar datos de precios con el estado del mercado (apertura, subastas, etc.).
- Identificar y estudiar posibles situaciones de arbitraje.
- Aplicar técnicas de análisis cuantitativo con Python.

---

## 📊 Datos utilizados
Los datos empleados incluyen:
- **Cotizaciones históricas** de acciones españolas.
- **Estado del mercado** (horarios, fases de negociación).
- Identificación de activos mediante **ISIN**.

> ⚠️ Algunos conjuntos de datos requieren una cantidad significativa de memoria para su carga completa.

---

## 🧹 Ingesta y limpieza de datos
El proyecto incluye:
- Lectura manual y optimizada de archivos de cotizaciones.
- Almacenamiento estructurado en diccionarios por activo.
- Normalización de fechas y precios.
- Filtrado por activos y periodos relevantes.

Se implementan dos enfoques:
- **Ejecución manual** (más control, mayor coste computacional).
- **Ejecución rápida** (optimizada para grandes volúmenes de datos).

---

## 📈 Metodología
- Análisis exploratorio de precios.
- Cruce entre cotizaciones y estado del mercado.
- Visualización de series temporales.
- Identificación de posibles ineficiencias de mercado.
- Uso de librerías estándar de análisis financiero y científico en Python.

---

## 🛠️ Tecnologías utilizadas
- **Python**
- **Pandas** – manipulación de datos
- **NumPy** – cálculo numérico
- **Matplotlib** – visualización

---

## 📂 Estructura del proyecto
