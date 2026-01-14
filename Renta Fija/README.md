# Análisis de Cartera de Bonos Corporativos

**Autores:**
- Borja Castelló
- Higinio Paterna
- Mateo Santos

---

## 1. Instalación y Ejecución del Programa

### 1.1 Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### 1.2 Creación del Entorno Virtual

#### En Windows:

```bash
# Crear el entorno virtual
python -m venv venv

# Activar el entorno virtual
venv\Scripts\activate
```

#### En macOS/Linux:

```bash
# Crear el entorno virtual
python3 -m venv venv

# Activar el entorno virtual
source venv/bin/activate
```

### 1.3 Instalación de Dependencias

Una vez activado el entorno virtual, instala las dependencias necesarias:

```bash
pip install -r requirements.txt
```

Las dependencias incluyen:
- **pandas** (>=1.5.0): Manipulación y análisis de datos
- **numpy** (>=1.23.0): Operaciones numéricas y álgebra lineal
- **scipy** (>=1.9.0): Optimización y cálculos científicos
- **python-dateutil** (>=2.8.2): Manejo de fechas
- **matplotlib** (>=3.5.0): Visualización de datos
- **seaborn** (>=0.12.0): Visualizaciones estadísticas avanzadas
- **scikit-learn** (>=1.1.0): Herramientas de machine learning y análisis

### 1.4 Ejecución del Programa

Para ejecutar el análisis completo:

```bash
python analisis_principal.py
```

Los resultados se guardarán automáticamente en la carpeta `resultados/`.

---

## 2. Estructura y Funcionamiento del Programa

### 2.1 Arquitectura del Proyecto

```
P2 SUBIR/
│
├── data/                              # Datos de entrada
│   ├── universo.csv                   # Universo de bonos corporativos
│   ├── curvaESTR.csv                  # Curva de tipos libre de riesgo (€STR)
│   ├── precios_historicos_universo.csv # Histórico de precios de bonos
│   └── precios_historicos_varios.csv   # Índices de referencia (iTraxx, etc.)
│
├── resultados/                        # Salidas y análisis generados
│   ├── *.csv                          # Tablas con métricas calculadas
│   └── *.png                          # Gráficos y visualizaciones
│
├── cargador_datos.py                  # Módulo de carga y limpieza de datos
├── valorador_bonos.py                 # Motor de valoración de bonos
├── gestor_carteras.py                 # Optimización y gestión de carteras
├── analisis_principal.py              # Script principal de ejecución
├── requirements.txt                   # Dependencias del proyecto
└── README.md                          # Este archivo
```

### 2.2 Descripción de Módulos

#### **cargador_datos.py**
Gestiona la carga, validación y limpieza de todos los datasets:
- Lee los archivos CSV de la carpeta `data/`
- Valida la integridad de los datos
- Maneja valores nulos y formatea fechas
- Proporciona funciones auxiliares para acceder a los datos

**Funciones principales:**
- `cargar_universo()`: Carga el universo de bonos
- `cargar_curva_tipos()`: Carga la curva €STR
- `cargar_historicos()`: Carga precios históricos

#### **valorador_bonos.py**
Contiene el motor de valoración de instrumentos de renta fija:
- **Cálculo de flujos de caja**: Genera cupones y amortizaciones
- **Descuento de flujos**: Valoración teórica usando curvas de tipos
- **Métricas de riesgo**: Duración, duración modificada, convexidad
- **Cálculo de spreads**: Z-Spread, OAS, credit spread
- **TIR (Yield to Maturity)**: Cálculo iterativo mediante Newton-Raphson

**Clases principales:**
- `Bono`: Representa un bono con sus características
- `MotorValoracion`: Motor de cálculo de precios y métricas

#### **gestor_carteras.py**
Implementa la lógica de construcción y optimización de carteras:
- **Optimización con restricciones**: Usa `scipy.optimize` para maximizar retorno/ajustar riesgo
- **Backtesting**: Simulación histórica de estrategias
- **Gestión de rebalanceos**: Ajuste periódico de pesos
- **Cálculo de métricas de cartera**: Sharpe, Sortino, máximo drawdown
- **Cobertura de riesgos**: Tipos de interés (futuros) y crédito (CDS)

**Clases principales:**
- `Cartera`: Representa una cartera de bonos con pesos
- `Optimizador`: Realiza la optimización sujeta a restricciones
- `Backtester`: Simula evolución histórica

#### **analisis_principal.py**
Script ejecutable que orquesta todo el análisis:
1. **Parte 1**: Análisis exploratorio del universo de bonos
2. **Parte 2**: Valoración teórica con curva libre de riesgo
3. **Parte 3**: Cálculo de spreads y análisis de riesgo de crédito
4. **Parte 4**: Métricas de TIR, duración y convexidad
5. **Parte 5**: Backtest de cartera equiponderada
6. **Parte 6**: Construcción de cartera restringida optimizada
7. **Parte 7**: Cobertura de riesgo de tipos de interés (futuros)
8. **Parte 8**: Cobertura de riesgo de crédito (CDS)
9. **Parte 9**: Estrategia de valor relativo (curve trading)

### 2.3 Funcionamiento Básico

1. **Carga de Datos**: El programa carga el universo de bonos, la curva de tipos €STR y los históricos de precios.

2. **Análisis Exploratorio**: Se generan visualizaciones sobre ratings, sectores, vencimientos, cupones y liquidez.

3. **Valoración de Bonos**: Para cada bono del universo, se calculan:
   - Precio teórico descontando con curva libre de riesgo
   - Spread de crédito (diferencia vs. precio de mercado)
   - TIR (Yield to Maturity)
   - Duración y Convexidad

4. **Construcción de Carteras**:
   - **Equiponderada**: Asigna el mismo peso a todos los bonos
   - **Optimizada**: Maximiza rentabilidad sujeto a restricciones:
     - Máximo 20 bonos
     - Duración ≤ 3 años
     - High Yield ≤ 10%
     - Sin deuda subordinada
     - Emisiones ≥ 500 millones
     - Límite por emisión (10%) y emisor (15%)

5. **Backtesting**: Simula la evolución de las carteras en el período histórico disponible con rebalanceo mensual.

6. **Gestión de Riesgos**:
   - **Riesgo de tipos**: Cobertura mediante futuros (Schatz, BOBL, Bund)
   - **Riesgo de crédito**: Cobertura mediante CDS índices (iTraxx Main/Crossover)

7. **Generación de Resultados**: Todos los outputs (CSV y gráficos) se guardan en `resultados/`.

### 2.4 Notas Técnicas Importantes

- **Interpolación de curvas**: Se utiliza interpolación cúbica (spline) para obtener tasas en cualquier plazo.
- **Manejo de bonos callable**: Se calcula la duración efectiva considerando la opcionalidad.
- **Tratamiento de bonos perpetuos**: Se asume un horizonte de 100 años para valoración.
- **Convenciones de mercado**: Act/360 para tipos flotantes, Act/Act para tipos fijos.

---

## 3. Análisis y Resultados

### 3.1 Análisis Exploratorio del Universo de Bonos

#### Preguntas y Respuestas sobre el Universo

**¿Divisas?**

Vemos que el único tipo de divisa con el que vamos a trabajar es el euro.

**¿Tipo de bonos? ¿Fijo/Flotante? ¿Prelación? ¿Opcionalidad? ¿Hay bonos perpetuos?**

Vemos que los bonos con cupón fijo predominan sobre los de tipo variable. También, los bonos de tipo Senior (prioridad de cobro frente a la deuda subordinada) Unsecured (no están ligados a activos concretos) predominan sobre el resto de órdenes de prioridad, mientras que los de tipo First Lien (los que tienen mayor prioridad) son los minoritarios. Hay una mayoría de bonos con opción de compra, y solamente 19 perpetuos.

**¿Sectores? ¿Emisores? Si invirtéramos en todos los bonos, ¿dirías a priori que la cartera está diversificada?**

A priori la cartera no estaría diversificada por sectores, ya que el sector financiero tendría más del 40% del peso total de la cartera. Sin embargo, sí que tendría una buena diversificación por emisores, ya que ninguno de ellos superaría el 5% del total de la cartera.

**¿Ratings? (Riesgo de crédito)**

Tenemos que el mayor porcentaje de bonos tienen rating BBB+, entrando dentro del rango de investment grade, lo que indica una capacidad adecuada del emisor para cumplir sus obligaciones. Sin embargo, la segunda mayor categoría son bonos sin rating, que puede ser debido a diversos factores, aunque es innegable que introducen mayor incertidumbre al no disponer de una estimación oficial de su riesgo. Vamos a incluir esta categoría dentro de high yield para lo que sigue.

**¿Otros datos cuantitativos?**

*Riesgo de liquidez - Horquillas y nominal vivo*

Como podemos observar, para nominales vivos más bajos las horquillas posibles varían mucho más que en emisiones más grandes, lo cual tiene bastante sentido, pues los volúmenes más pequeños suelen negociarse menos, lo que implica que cualquier transacción que se introduzca va a afectar mucho más al precio al que se está negociando.

**¿Hay *gaps* en la información que vamos a tener que tratar?**

Nos ha quedado un dataset de precios históricos donde se ha decidido dejar que cada bono tenga un período distinto, de manera no tendremos datos de cada bono desde el 2 de octubre de 2023.

---

### 3.2 Valoración Teórica vs. Precio de Mercado

#### Ejercicio: Valoración con Spread de Crédito = 0

Si asumimos que el **spread de crédito es 0**, y la ejecutamos para el 01/10/2025...

- **¿Qué observas si comparas los precios obtenidos y los precios de mercado?**
- **¿Crees que la diferencia se debe a un factor relacionado sólo con el riesgo crediticio?**
- **¿Qué otros factores influyen en ese spread?**

#### Análisis de Resultados

**Divergencia Precio Teórico vs. Precio de Mercado**

Al valorar los activos descontando flujos exclusivamente con la curva libre de riesgo cargada desde `curvaESTR.csv` (tasas ESTR), obtenemos precios teóricos sistemáticamente superiores a los precios de mercado (columna `Price` en `universo.csv`).

**Interpretación Económica**

Esa diferencia de precio no es un error, es la **prima de riesgo**. El mercado exige una rentabilidad (Yield) mayor a la tasa libre de riesgo ESTR. Este diferencial descuenta:

1. **Riesgo de Crédito**: La probabilidad de que el emisor (columna `PD 1YR`) quiebre.
2. **Prima de Liquidez**: Compensación por la menor negociabilidad frente a deuda pública.
3. **Factores Técnicos**: Costes de balance para los bancos que mantienen estos bonos en inventario.

---

### 3.3 Análisis de Spreads de Crédito

#### Preguntas sobre Spreads

- **¿Qué observas? ¿Tienen sentido los resultados?**
- **¿Con qué datos de los que tenemos compararías para ver si los resultados son coherentes?**

#### Análisis de Spreads

Los spreads constituyen la diferencia porcentual entre los precios teóricos y de mercado. Es un indicador del riesgo, cuanto mayor sea el spread mayor es el riesgo asociado. Es por ello, que si el spread aumenta, el precio tiende a disminuir.

**Tipos de spreads:**

- **Credit spread**: spread entre un bono corporativo y uno gubernamental.
- **Spread soberano**: spread entre un bono de un país emergente y un bono libre de riesgo, que por lo general, es el bono alemán.
- **Spread swap**: diferencia entre la yield del bono y la tasa swap.
- **Z-spread / OAS**: spreads ajustados por características del bono (callables, amortizaciones, etc.).

En este ejercicio se ha implementado el cálculo de los spreads para cada bono del universo. A partir de aquí se pueden sacar muchas conclusiones en función de las variables categóricas existentes en el universo y las que se pueden crear a partir de las variables numéricas. Algunas de estas conclusiones son:

- El spread esperado (media de los spreads) es mayor que el proporcionado por indicadores como ITRAXX Main.
- Los bonos High Yield son los que presentan un mayor spread, que es esperable porque son los que tienen un mayor riesgo. Por otro lado, el comportamiento de los bonos sin clasificar y los Investment Grade es muy similar pero son preferibles los Investment Grade porque tienen un menor riesgo.
- Según el rating de los bonos se aprecia que la apuesta más segura son los bonos AAA. Si consideramos los bonos BBB+ como el umbral que marca los bonos de mucho o poco riesgo tenemos que:
    - Dentro de los bonos de poco riesgo (rating mayor o igual a BBB+): los bonos A+, A y A- pueden ser una buena opción por la alta relación entre rentabilidad y riesgo (índice de Sharpe).
    - Dentro de los bonos de mucho riesgo (rating menor a BBB+): los bonos BBB y BB+ presentan una razonable relación entre rentabilidad y riesgo (índice de Sharpe).
- Según el sector de actividad del emisor tenemos:
    - El sector financiero es el spread esperado más alto.
    - La inversión en el sector de la energía es excelente por su alta relación entre rentabilidad y riesgo.
    - Destacan los bonos de los sectores Industrial y Consumer Cyclical por su elevado riesgo. Habría que evitar inversiones en bonos de estos sectores porque hay otros bonos de otros sectores que ofrecen una rentabilidad esperada similar pero con un riesgo significativamente menor.

También destaca la escasa correlación entre la probabilidad de default y el spread. Sería esperable que conforme el spread sea mayor, la probabilidad de default fuera mayor.

En cuanto a la liquidez de los bonos, tenemos que conforme más líquido en un bono, es decir, la diferencia entre los precios Bid y Ask son menores, hay una mayor variabilidad de spreads (caso claro de heterocedasticidad).

---

### 3.4 Análisis de TIR, Duración y Convexidad

#### Relación entre TIR y Spread

**¿Qué relación hay entre la TIR calculada y el spread calculado en el apartado anterior?**

La relación es aditiva y directa. La **TIR (Yield to Maturity)** es, aproximadamente, la suma de la tasa libre de riesgo (Swap Rate al vencimiento del bono) más el Z-Spread.

Mientras que la TIR es una medida de rentabilidad total absoluta, el Z-Spread aísla la prima de riesgo (crédito + liquidez) eliminando el efecto de la curva de tipos base. Si el BCE sube tipos, la TIR del bono subirá, pero su Z-Spread debería permanecer constante si la solvencia del emisor no ha cambiado.

#### Duración y Vencimiento

**¿Qué relación hay entre la duración y el vencimiento? ¿Qué refleja la duración? ¿De qué otra forma se podría obtener esta sensibilidad?**

- **Relación**: La duración es siempre menor o igual al vencimiento (solo es igual en los bonos cupón cero). Cuanto mayor es el cupón, menor es la duración respecto al vencimiento.

- **Reflejo**: Financieramente, la duración refleja la sensibilidad lineal del precio ante cambios en los tipos de interés (cuánto varía el precio ante un cambio del 1% en la yield). Temporalmente, es el plazo medio ponderado de recuperación de los flujos de caja.

- **Cálculo alternativo**: Además de la fórmula analítica cerrada, se puede obtener mediante **"Full Repricing"** (diferencias finitas): se calcula el precio actual (P₀), se desplaza toda la curva de tipos +1 punto básico, se recalcula el precio (P₁) y se mide la variación (PV01).

#### Estimación con Duración y Convexidad

**Estima el precio del bono usando la duración y convexidad, ¿qué observas?**

Utilizando la expansión de Taylor:

**ΔP ≈ (−Dur × Δy) + (½ × Conv × (Δy)²)**

**Observación**: La estimación utilizando solo la duración (lineal) siempre subestima el precio real del bono (tanto si los tipos suben como si bajan). Al añadir el término de convexidad, la estimación se ajusta mucho mejor a la realidad, corrigiendo la curvatura de la relación precio-tipo. Sin embargo, en nuestros bonos callables, observamos que la convexidad efectiva puede reducirse drásticamente (o volverse negativa), haciendo que el precio suba menos de lo esperado por la fórmula tradicional ante bajadas de tipos.

---

### 3.5 Backtest de Cartera Equiponderada

#### Consideraciones Metodológicas

**¿Qué sería lo más correcto en lugar de utilizar los precios MID?**

Utilizar precios MID (punto medio entre compra y venta) no es correcto para una simulación realista de gestión de carteras. Lo correcto es valorar la compra de activos al **precio ASK** (el precio al que el mercado nos vende, que es más caro) y la valoración de cierre o venta al **precio BID** (el precio al que el mercado nos compra, más barato). Utilizar el MID ignora el Bid-Ask Spread, que es un coste de transacción implícito. En bonos corporativos con horquillas amplias, usar MID sobreestima la rentabilidad inicial de la cartera.

**¿Se te ocurre algún otro benchmark que se podría utilizar?**

Aunque el benchmark utilizado actualmente (RECMTREU Index) es correcto metodológicamente por ser un índice Total Return (incluye cupones y reinversión), no es el más adecuado para nuestra cartera específica.

**El Problema**: Nuestra cartera tiene una duración efectiva de ~1.64 años (según Parte 7). El índice de mercado genérico suele tener una duración mucho mayor (aprox. 4-5 años). Al comparar nuestra cartera con este índice, estamos mezclando perfiles de riesgo de tipos muy diferentes.

**La Alternativa**: Sería mucho más preciso utilizar un índice acotado por vencimiento, como el **Bloomberg Euro Corporate 1-3 Year Index**. De esta forma, aislamos la calidad de nuestra gestión de crédito (selección de bonos) sin que el resultado se vea distorsionado porque la curva de tipos haya subido o bajado (riesgo de duración).

**Otra opción**: Utilizar un **ETF Líquido** (como iShares € Corp Bond 1-5yr). Al ser un activo negociable, incorpora costes reales de fricción que un índice teórico ignora.

---

### 3.6 Construcción de Cartera Restringida Optimizada

#### Mandato de Inversión

Como adelantábamos en el enunciado, tienes el mandato de construir una cartera de como máximo **20** bonos corporativos con ese universo y una serie de restricciones y, claro, maximizando la rentabilidad total de la cartera:

- La duración de la cartera no debe superar los 3 años
- La exposición a emisiones HY no puede superar el 10% de la cartera
- No puedes invertir en deuda subordinada
- No se puede invertir en emisiones de tamaño igual o inferior a 500 millones
- No se puede invertir más de un 10% del capital en una misma emisión
- No puede haber más de un 15% de concentración en un mismo emisor

*(¡OJO! No estamos teniendo en cuenta en este ejercicio si hubiera un mínimo de inversión, lo cuál sería un dato relevante tener en cuenta en un caso real)*

#### Restricciones Adicionales

**Teniendo en cuenta la naturaleza que nos están pidiendo para la cartera, ¿añadirías alguna otra restricción?**

Como restricción adicional, añadiría la imposición de una cota máxima para la correlación entre emisores (que se podría calcular utilizando el histórico de precios del que disponemos), porque aunque ya impongamos una restricción sobre la concentración en un emisor, podría darse el caso de que se introdujeran emisores altamente correlacionados, perdiendo la diversificación buscada.

#### Medición del Riesgo de Crédito

**¿Cómo medirías el riesgo de crédito de la cartera?**

En primer lugar, podríamos considerar la probabilidad de default a 1 año ponderada, ya que disponemos de dicho valor para cada bono del universo (PD 1YR), indicándonos como de probable sería un impago de la cartera. En segundo lugar, la diversificación de la cartera sería también un buen indicador, ya que cuanto más concentración tengamos en unos pocos emisores, en caso de impago de estos, mayor sería nuestra pérdida. Por último, tendríamos la exposición por rating, de manera que una alta concentración de High Yield o sin puntuación aumentaría nuestro riesgo de crédito.

#### Medición del Riesgo de Liquidez

**¿Cómo medirías el riesgo de liquidez de la cartera? ¿Se te ocurre alguna otra información que se podría utilizar aunque no se te haya dado?**

Como vimos en el punto 1, tanto la horquilla entre bid y ask como el nominal vivo son buenos indicadores de la liquidez de un bono, por lo que para una cartera podemos cojer la suma ponderada de su valor para todas las componentes. De estas métricas podemos derivar otras como el turnover potencial, que viene a expresar la capacidad que tendríamos de liquidar rápidamente la cartera en caso de que quisiéramos cambiar su composición de bonos. Otra métrica que sería relevante de cara a la liquidez sería el volumen diario de negociación de cada uno de los bonos de la cartera, que podríamos estudiar si tuviéramos disponibles para cada día todos los precios negociados de cada bono, en vez de sólamente el de cierre como ahora.

#### Backtesting de la Cartera

**Describe cómo habría que hacer el backtest de esta cartera, no hace falta que lo implementes en este caso**

En primer lugar, debemos seleccionar el período. Como disponemos de datos históricos entre el el 02/10/2023 y el 01/10/2024, este puede ser el período. A continuación, habría que configurar una serie de parámetros, como son la frecuencia de rebalanceo (mensual por ejemplo), el capital inicial de la cartera (10 millones de euros) y un benchmark contra el que comparar, que tenga características similares a la de nuestra cartera. Una vez hecho esto, podríamos ya construir una primera versión de nuestra cartera en la fecha de inicio del período seleccionado, obteniendo una serie de bonos y pesos de acuerdo a las restricciones impuestas y a la función a optimizar. En cada fecha de rebalanceo, tendremos que volver a repetir la misma operativa, realizando además las correspondientes órdenes de compra y venta de bonos para ajustarse a la nueva cartera. Una vez finalizado el período, debemos realizar una comparativa de las métricas obtenidas a lo largo de todo el proceso, y compararlas con con las obtenidas por nuestro benchmark. Como extra, podría ser interesante la introducción de stress testing en el período, mediante la introducción de escenarios como subidas de tipos, ensanchamiento de spreads o default de bonos.

---

### 3.7 Cobertura del Riesgo de Tipos de Interés

#### Instrumentos Disponibles

Utiliza alguno de los siguientes instrumentos de los que te hemos dado para cubrir la duración (sensibilidad de tipos de interés) de la cartera que has construido según el mandato. Asume una inversión en la cartera de 10 millones:

- Futuros sobre el **Schatz** (ticker: DU1) - Duración a 01/10/2025: 1.92
- Futuros sobre el **BOBL** (ticker: OE1) - Duración a 01/10/2025: 5.44
- Futuros sobre el **BUND** (ticker: RX1) - Duración a 01/10/2025: 10

*Contract size* en todos los casos: 100,000 euros

#### Elección y Razonamiento

**Investiga sobre estos instrumentos antes de tomar la decisión. Razona tu elección del instrumento y el número de contratos que has decidido comprar/vender.**

Nuestra **cartera optimizada** (Parte 6) tiene una duración de **3.00 años exactos** (resultado de la restricción del optimizador: duración ≤ 3 años). 

**Decisión:** El futuro más adecuado para la cobertura es el **Euro-Schatz (DU1)** por las siguientes razones:

1. **Match de duración:** Con duración de 1.92 años, es el más cercano a nuestra cartera (3.00 años).
2. **Menor basis risk:** La diferencia de duraciones (3.00 - 1.92 = 1.08 años) es menor que con BOBL (5.44) o BUND (10.00).
3. **Eficiencia de cobertura:** Requiere aproximadamente **156 contratos**, un número manejable que permite ajustes precisos.

**Cálculo:**
```
Sensibilidad cartera = Duración × Valor = 3.00 × 10,000,000 = 30,000,000 € × años
Número de contratos = 30,000,000 / (1.92 × 100,000) = 156.25 contratos
```

**Estrategia:** Queremos reducir la sensibilidad a tipos de interés, por lo que la posición es de **VENTA de 156 contratos** de Schatz.

**Efecto:** Si los tipos suben +1%, la cartera pierde ~3% (duración 3.00), pero los futuros vendidos ganan ~1.92% × 156 contratos, compensando la pérdida.

#### Análisis de Sobrecobertura

**¿Qué pasaría si comprásemos/vendiésemos 100 futuros?**

Si en vez de 156 contratos vendemos solo **100**, estaríamos **infracoberturados**:
- Cobertura actual: 100 contratos × 1.92 × 100,000 = 19,200,000 de sensibilidad
- Cobertura necesaria: 30,000,000 de sensibilidad
- **Hedge Ratio: 64%** (solo cubrimos el 64% del riesgo)

**Consecuencia:** Ante una subida de tipos de +1%, la cartera perdería ~3%, pero los futuros solo compensarían ~1.92% × (100/156) = 1.23%. **Pérdida neta: -1.77%** en lugar de estar protegidos.

Por el contrario, si vendiéramos **200 contratos**:
- Estaríamos **sobrecoberturados** (Hedge Ratio: 128%)
- Ahora el riesgo se invierte: **perdemos dinero si los tipos BAJAN**
- Ante una bajada de tipos de -1%, la cartera gana +3%, pero los futuros pierden -1.92% × (200/156) = -2.46%. **Ganancia neta reducida: +0.54%**

#### Instrumentos Alternativos

**¿Se te ocurre algún otro instrumento con el que cubrir la sensibilidad a los tipos de interés de la cartera?**

Otro instrumento que podríamos utilizar serían los **swaps de tipos de interés**. Más concretamente, un swap **pay fixed / receive float**, que tiene duración negativa, de manera que como nuestra cartera tiene duración positiva podemos neutralizar el riesgo de subida de tipos.

---

### 3.8 Cobertura del Riesgo de Crédito

#### Elección del Índice: iTraxx Main (Investment Grade)

El archivo `precios_historicos_varios.csv` nos ofrece dos índices de crédito:

- **ITRX EUR CDSI GEN 5Y Corp (Main)**: Empresas de alta calidad (Investment Grade). CS01: 4,500 €/bp por 10M nominal.
- **ITRX XOVER CDSI GEN 5Y Corp (Crossover)**: Empresas de menor calidad (Sub-IG/High Yield). CS01: 6,500 €/bp por 10M nominal.

**Decisión**: Seleccionamos el **iTraxx Main**.

#### Justificación: Composición de la Cartera Optimizada

Nuestra **cartera optimizada** (Parte 6) tiene la siguiente composición por calidad crediticia (por peso):

**Bonos con rating explícito (7 bonos, 51% del peso):**
- **Investment Grade (BBB+ a BBB-):** 51.0% del peso
  - Heathrow Funding (BBB+): 10%
  - WMG Acquisition (BBB-): 15% (dos emisiones)
  - Stellantis (BBB): 15% (dos emisiones)
  - Upjohn Finance (BBB-): 1%
  - Heimstaden Bostad (BBB-): 10%

**Bonos sin rating (NR) - Reclasificados por Z-Spread (5 bonos, 49% del peso):**

Análisis de spreads de los NR:
- TDC Net (187 pb), Teleperformance (172 pb), CA Immobilien (156 pb), Banca Transilvania (149 pb), Aroundtown (143 pb)
- **Todos tienen Z-Spread 140-190 pb** → Equivalente a **BBB-/BBB** (Investment Grade)
- Todos están **muy por debajo del umbral de 200 pb** que separa IG de HY

**Composición ajustada final:**
- **Investment Grade:** 51.0% + 49.0% = **100.0%** (IG con rating + NR reclasificados como IG)
- **High Yield:** **0.0%** (no hay bonos HY en la cartera)

**¿Por qué iTraxx Main?**

Con **100% de calidad IG**, la decisión correcta es claramente usar **iTraxx Main**:

1. **Match de composición:** 100% IG → Cartera exclusivamente Investment Grade.
2. **Análisis de spreads históricos:** El Main cotiza en niveles bajos (~80 bps) reflejando empresas de alta calidad, perfectamente alineado con nuestra cartera 100% IG.
3. **Correlación en crisis:** En momentos de estrés crediticio:
   - Nuestros bonos IG (BBB+ a BBB-) → spreads se amplían +100-150 bps
   - Bonos sin rating (Z-Spread 140-190 pb, calidad IG) → spreads se amplían +150-200 bps
   - **Main → se amplía +80-120 bps (correlación adecuada ✓)**
   - Crossover → se amplía +300-400 bps (excesivo, sobrecobertura ✗)
4. **Evitar sobrecobertura:** Usar el Crossover sería completamente inadecuado. Con 0% de HY real (100% IG), pagar la prima del Crossover (~300 bps) para proteger una cartera exclusivamente Investment Grade sería muy ineficiente.
5. **Eficiencia de costes:** 
   - Prima Main: ~80 bps/año sobre el nominal
   - Prima Crossover: ~300 bps/año sobre el nominal
   - **Ahorro con Main: ~220 bps** (diferencia muy significativa)

#### Cálculo de la Cobertura

**Datos de la cartera optimizada:**
- Valor nominal: 10,000,000 € (inversión total)
- CS01 de la cartera: 3,165 €/bp (sensibilidad al spread de crédito)
- Composición: 100% Investment Grade (12 bonos)

**Decisión de índice:**
Dado que tenemos 100% IG (51% con rating explícito + 49% NR reclasificados como IG por Z-Spread), seleccionamos **iTraxx Main** (CS01: 4,500 €/bp por 10M).

**Cálculo del nominal de protección:**
```
Ratio CS01 = CS01_cartera / CS01_índice = 3,165 / 4,500 = 0.7033
Nominal CDS = Ratio × 10,000,000 = 0.7033 × 10,000,000 = 7,033,300 €
```

**Resultado:** Compramos **7.03 millones de nominal** de protección en iTraxx Main.

**Verificación:**
- CS01 del CDS comprado: (7.03M / 10M) × 4,500 = 3,165 €/bp ✓
- **Hedge Ratio: 100%** (cobertura perfecta del riesgo de crédito)

#### Reflexión sobre Cobertura Total

**Reflexión sobre Cobertura Total**: Cubrir el 100% del riesgo de crédito es **técnicamente posible** (como hemos calculado) y su coste es acotado:

1. **Coste de la prima:** El Main cotiza a ~80 bps anuales. Comprar 7.03M de protección cuesta:
   - Prima anual = 7,033,300 × 0.0080 = **56,266 €/año**
   - Rentabilidad bruta de la cartera: 10,000,000 × 0.0619 = **619,000 €/año**
   - Prima como % de rentabilidad: 56,266 / 619,000 = **9.1%**
   - **La prima anual es ~9% de la rentabilidad de la cartera**
   - Rentabilidad neta: 619,000 - 56,266 = **562,734 €/año** (≈5.63% sobre 10M)

2. **Trade-off rentabilidad-riesgo:**
   - Sin cobertura: Rentabilidad 6.19%, riesgo de crédito 100%
   - Cobertura 100%: Rentabilidad efectiva ≈ **5.63%/año**, riesgo de crédito ≈ 0%
   - **Óptimo:** Cobertura parcial 10-30% → coste anual ≈ **5.6k–16.9k €** (0.06–0.17% del nominal), reduce riesgo sin afectar significativamente la rentabilidad

3. **Eventos de cola vs riesgo continuo:** Lo óptimo suele ser una **cobertura selectiva** para protegerse de eventos extremos (tail risk como quiebras), no necesariamente una inmunización total.

**Recomendación práctica:** Comprar protección por **0.7–2.1 millones** de nominal (10–30% del riesgo), priorizando:
- Los bonos sin rating de mayor peso (TDC Net, Teleperformance, CA Immobilien)
- Los bonos BBB- en el límite de IG (Heimstaden, WMG)
- **Prima anual estimada:** **5.6k–16.9k €/año** (≈0.9–2.7% de la rentabilidad bruta)

---

### 3.9 Estrategia de Valor Relativo (Curve Trading)

#### Contexto y Oportunidad

Analizando el universo de bonos disponible, hemos observado que existen grandes emisores (como Volkswagen o Telefónica) que tienen múltiples bonos vivos en la curva con vencimientos escalonados (2026, 2028, 2030, etc.). A menudo, debido a ineficiencias de liquidez o flujos de oferta/demanda puntuales, la curva de crédito (Z-Spreads) de un mismo emisor no es perfectamente suave y presenta dislocaciones ("kinks").

#### Propuesta: Estrategia de Valor Relativo (Market Neutral)

Nuestra propuesta es una estrategia de **Valor Relativo (Market Neutral)** para explotar estas ineficiencias.

1. **Identificación**: Buscar dos bonos del mismo emisor y misma prelación (ej. Senior Unsecured) con vencimientos cercanos.

2. **Señal**: Si el Bono A (vencimiento 2029) tiene un Z-Spread de 140 bps y el Bono B (vencimiento 2030) tiene un Z-Spread de 190 bps, la curva está injustificadamente empinada en ese tramo (50 bps de diferencia por solo 1 año extra de riesgo).

3. **Ejecución**:
   - Comprar el Bono B (el "barato", con spread alto).
   - Vender (Corto) el Bono A (el "caro", con spread bajo) o cubrir su duración con futuros.

4. **Racional**: No apostamos a que el mercado suba o baje en general. Ganamos dinero si la curva del emisor se "normalice" (aplanamiento), es decir, si el spread del Bono B se estrecha relativo al Bono A. Es una estrategia de **bajo riesgo direccional** pero **alto valor técnico**.

---

## 4. Contacto y Contribuciones

Este proyecto fue desarrollado como parte de una práctica académica de análisis de renta fija y gestión de carteras de bonos corporativos.

**Autores:**
- Borja Castelló
- Higinio Paterna
- Mateo Santos

Para dudas o consultas sobre el código, por favor revisa la documentación en los módulos o contacta con los autores.

---

## 5. Licencia

Este proyecto es de uso académico y educativo.

---

**Última actualización**: Noviembre 2025

