"""
===============================================================================
CARGADOR DE DATOS - Práctica de Renta Fija
===============================================================================
Este módulo se encarga de leer y limpiar todos los archivos CSV necesarios
para el análisis de bonos corporativos.
===============================================================================
"""

# Importamos las librerías necesarias
import pandas as pd  # Para trabajar con tablas de datos (DataFrames)
import numpy as np   # Para operaciones matemáticas avanzadas
from datetime import datetime  # Para manejar fechas


def cargar_y_limpiar_universo(ruta_archivo='universo.csv'):
    """
    Esta función lee el archivo del universo de bonos y lo limpia.
    
    ¿Qué hace?
    ----------
    1. Lee el archivo CSV que contiene todos los bonos disponibles
    2. Convierte las fechas de texto (como "24/01/2033") a fechas reales
    3. Convierte los porcentajes de texto (como "7,5") a números decimales (0.075)
    4. Crea la columna de "Fecha_Vencimiento_Efectiva" usando la fecha Call si existe
    
    Parámetros
    ----------
    ruta_archivo : str
        La ruta donde está guardado el archivo universo.csv
    
    Retorna
    -------
    pandas.DataFrame
        Una tabla con todos los bonos limpios y listos para usar
    """
    
    print("\n" + "="*80)
    print("PASO 1: CARGANDO Y LIMPIANDO DATOS DEL UNIVERSO DE BONOS")
    print("="*80)
    
    # Leemos el archivo CSV. El separador es ";" (punto y coma)
    # Esto convierte el archivo Excel/CSV en una tabla de Python
    df_universo = pd.read_csv(ruta_archivo, sep=';', decimal=',')
    
    print(f"✓ Archivo cargado exitosamente: {len(df_universo)} bonos encontrados")
    
    # ----- LIMPIEZA DE FECHAS -----
    # Las fechas vienen como texto "DD/MM/YYYY" y necesitamos convertirlas a fechas reales
    
    # Lista de todas las columnas que contienen fechas
    columnas_fechas = [
        'Maturity',                    # Fecha de vencimiento del bono
        'Next Call Date',              # Fecha en que el emisor puede "llamar" (recomprar) el bono
        'First Coupon Date',           # Primera fecha de pago de cupón
        'Penultimate Coupon Date',     # Penúltima fecha de pago de cupón
        'Issue date'                   # Fecha de emisión del bono
    ]
    
    # Para cada columna de fechas, la convertimos de texto a fecha real
    for columna in columnas_fechas:
        if columna in df_universo.columns:
            # pd.to_datetime convierte texto a fecha. dayfirst=True indica formato DD/MM/YYYY
            # errors='coerce' significa: si no puede convertir, poner NaN (valor vacío)
            df_universo[columna] = pd.to_datetime(
                df_universo[columna], 
                format='%d/%m/%Y',  # El formato que esperamos: día/mes/año
                dayfirst=True,      # El día va primero
                errors='coerce'     # Si hay error, dejar vacío en vez de fallar
            )
    
    print("✓ Fechas convertidas de texto a formato fecha")
    
    # ----- LIMPIEZA DEL CUPÓN -----
    # El cupón viene como número (ej: 7.5) pero representa porcentaje (7.5%)
    # Lo convertimos a decimal: 7.5 -> 0.075 (para poder multiplicar directamente)
    
    if 'Coupon' in df_universo.columns:
        # Dividimos entre 100 para pasar de porcentaje a decimal
        # Ejemplo: 7.5 / 100 = 0.075
        df_universo['Coupon'] = pd.to_numeric(df_universo['Coupon'], errors='coerce') / 100.0
        print("✓ Cupones convertidos a formato decimal (ej: 7.5% -> 0.075)")
    
    # ----- LIMPIEZA DE LA FRECUENCIA DE CUPÓN -----
    # La frecuencia indica cuántas veces al año se pagan cupones
    # Normalmente es 1 (anual) o 2 (semestral)
    
    if 'Coupon Frequency' in df_universo.columns:
        # Convertimos a número entero
        df_universo['Coupon Frequency'] = pd.to_numeric(
            df_universo['Coupon Frequency'], 
            errors='coerce'
        )
        print("✓ Frecuencia de cupón convertida a número")
    
    # ----- CREAR FECHA DE VENCIMIENTO EFECTIVA -----
    # El profesor pide usar la fecha Call si existe, sino la fecha de Maturity
    # Esto es porque si hay una fecha Call, el bono probablemente será llamado
    
    # Primero creamos la columna copiando la fecha de Maturity
    df_universo['Fecha_Vencimiento_Efectiva'] = df_universo['Maturity']
    
    # Luego, para los bonos que SÍ tienen fecha Call
    # En tiene_call guardamos los bonos que si tienen fecha Call
    # notna() significa "no es vacío" y le da valor de true y lo guarda
    tiene_call = df_universo['Next Call Date'].notna()
    # Queremos cambiar la columna Fecha_Vencimiento_Efectiva por la columna Next Call Date pero solo
    # para los bonos que tienen fecha Call 
    df_universo.loc[tiene_call, 'Fecha_Vencimiento_Efectiva'] = df_universo.loc[tiene_call, 'Next Call Date']
    
    print(f"✓ Fecha de vencimiento efectiva creada")
    print(f"  - {tiene_call.sum()} bonos tienen fecha Call y la usaremos")
    print(f"  - {(~tiene_call).sum()} bonos no tienen Call, usaremos fecha Maturity")
    
    # ----- LIMPIEZA DE PRECIOS -----
    # Los precios pueden venir con decimales raros, nos aseguramos que sean números
    
    for columna_precio in ['Price', 'Bid Price', 'Ask Price']:
        if columna_precio in df_universo.columns:
            df_universo[columna_precio] = pd.to_numeric(
                df_universo[columna_precio], 
                errors='coerce'
            )
    
    print("✓ Precios convertidos a números decimales")
    
    # Filtro final de seguridad:
    # Eliminamos los bonos que no tengan ISIN, Vencimiento, Cupón o Fecha de Emisión.
    # La 'Fecha de Emisión' es vital: necesitamos saber cuándo "nació" el bono para 
    # poder calcular bien su calendario de pagos y los intereses acumulados (cupón corrido).
    # Si falta alguno de estos datos, no podemos valorar el bono con precisión.
    bonos_antes_filtro = len(df_universo)
    df_universo = df_universo.dropna(subset=['ISIN', 'Fecha_Vencimiento_Efectiva', 'Coupon', 'Issue date'])
    bonos_despues_filtro = len(df_universo)
    bonos_eliminados = bonos_antes_filtro - bonos_despues_filtro
    
    if bonos_eliminados > 0:
        print(f"✓ Filtro de seguridad aplicado: {bonos_eliminados} bonos eliminados por datos incompletos")
    print(f"✓ Total de bonos válidos para análisis: {bonos_despues_filtro}")
    
    print("\n✓✓ UNIVERSO CARGADO Y LIMPIO ✓✓\n")
    
    # Devolvemos el DataFrame limpio
    return df_universo


def cargar_curva_estr(ruta_archivo='curvaESTR.csv'):
    """
    Esta función lee la curva de tasas ESTR (Euro Short-Term Rate).
    
    ¿Qué es la curva ESTR?
    ----------------------
    Es la curva de tasas de interés libre de riesgo en Europa.
    La usaremos para descontar los flujos de caja futuros del bono.
    Es como la tasa que paga el Banco Central Europeo.
    
    ¿Qué hace esta función?
    ------------------------
    1. Lee el archivo CSV con la curva
    2. Convierte las fechas de texto a fechas reales
    3. Convierte las tasas de porcentaje a decimal
    4. Calcula los plazos en años (para interpolar más fácil)
    
    Parámetros
    ----------
    ruta_archivo : str
        La ruta donde está guardado el archivo curvaESTR.csv
    
    Retorna
    -------
    pandas.DataFrame
        Una tabla con las fechas, tasas y factores de descuento
    """
    
    print("\n" + "="*80)
    print("PASO 2: CARGANDO CURVA DE TASAS ESTR (LIBRE DE RIESGO)")
    print("="*80)
    
    # Leemos el archivo CSV con separador ";"
    df_curva = pd.read_csv(ruta_archivo, sep=';', decimal='.')
    
    print(f"✓ Archivo cargado: {len(df_curva)} puntos en la curva")
    
    # ----- LIMPIEZA DE FECHAS -----
    # Convertimos la columna 'Date' de texto a fecha real
    df_curva['Date'] = pd.to_datetime(
        df_curva['Date'], 
        format='%d/%m/%Y',
        dayfirst=True,
        errors='coerce'
    )
    
    print("✓ Fechas de la curva convertidas")
    
    # ----- LIMPIEZA DE TASAS -----
    # Convertimos las tasas a números. Las columnas son:
    # - Market Rate: tasa de mercado
    # - Zero Rate: tasa cero cupón (la que usaremos para descontar)
    # - Discount: factor de descuento
    
    for columna in ['Market Rate', 'Zero Rate', 'Discount']:
        if columna in df_curva.columns:
            # Convertimos a número decimal
            df_curva[columna] = pd.to_numeric(df_curva[columna], errors='coerce')
    
    print("✓ Tasas convertidas a números")
    
    # ----- CALCULAR PLAZOS EN AÑOS -----
    # Para interpolar, necesitamos saber cuántos años hay desde hoy hasta cada punto
    
    # La primera fecha es la fecha de valoración 
    fecha_valoracion = df_curva['Date'].iloc[0]
    
    # Calculamos los días entre cada fecha y la fecha de valoración
    # Luego dividimos entre 365 para obtener años 
    df_curva['Plazo_Años'] = (df_curva['Date'] - fecha_valoracion).dt.days / 365.0
    
    print("✓ Plazos calculados en años")
    print(f"  - Plazo mínimo: {df_curva['Plazo_Años'].min():.2f} años")
    print(f"  - Plazo máximo: {df_curva['Plazo_Años'].max():.2f} años")
    
    # Eliminamos filas con valores vacíos (NaN) en columnas críticas
    # NOTA: Solo eliminamos si falta 'Date' o 'Zero Rate', pero NO si falta 'Discount'
    # ¿Por qué? Porque el Discount (Factor de Descuento) es algo que podemos calcular
    # matemáticamente a partir del Zero Rate. Si tenemos la fecha y el Zero Rate,
    # podemos recuperar el Discount. Pero si nos falta el Zero Rate, sí perdemos información.
    df_curva = df_curva.dropna(subset=['Date', 'Zero Rate'])
    
    print(f"✓ Filas con datos completos: {len(df_curva)}")
    
    print("\n✓✓ CURVA ESTR CARGADA Y LISTA ✓✓\n")
    
    return df_curva


def cargar_precios_historicos_completo(ruta_archivo='precios_historicos_universo.csv'):
    """
    Carga TODOS los precios históricos limpios para backtesting.
    
    
    Retorna
    -------
    pandas.DataFrame
        DataFrame transpuesto con:
        - Índice: Fechas (datetime)
        - Columnas: ISINs (sin " Corp")
        - Valores: Precios
    """
    
    # Leemos el archivo
    df_precios = pd.read_csv(ruta_archivo, sep=';', decimal='.', index_col=0, na_values=['#N/D', 'N/A', ''])
    
    # Limpiamos ISINs (quitar " Corp")
    df_precios.index = df_precios.index.str.replace(' Corp', '', regex=False).str.strip()
    df_precios.index.name = 'ISIN'
    
    # Transponemos: fechas en índice, ISINs en columnas
    df_precios = df_precios.T
    
    # Convertimos el índice a datetime
    df_precios.index = df_precios.index.str.strip()
    df_precios.index = pd.to_datetime(df_precios.index, format='%d/%m/%Y', dayfirst=True, errors='coerce')
    
    # Eliminamos fechas inválidas
    df_precios = df_precios[df_precios.index.notna()]
    df_precios = df_precios.sort_index()
    
    return df_precios


def cargar_indices_y_futuros(ruta_archivo='data/precios_historicos_varios.csv'):
    """
    Esta función carga los precios históricos de índices y futuros necesarios para:
    - Benchmarking (comparar nuestra cartera vs el mercado)
    - Coberturas (hedging) con futuros de tipos de interés
    - Análisis de crédito con índices CDS
    
    Instrumentos incluidos:
    -----------------------
    1. RECMTREU Index: Índice Bloomberg Euro Aggregate (nuestro benchmark)
    2. RX1 Comdty: Futuro Bund 10 años (para cubrir tipos largos)
    3. OE1 Comdty: Futuro Bobl 5 años (para cubrir tipos medios)
    4. DU1 Comdty: Futuro Schatz 2 años (para cubrir tipos cortos)
    5. ITRX EUR CDSI GEN 5Y: iTraxx Europe Main (CDS Investment Grade)
    6. ITRX XOVER CDSI GEN 5Y: iTraxx Crossover (CDS High Yield)
    
    Parámetros
    ----------
    ruta_archivo : str
        Ruta al archivo CSV con los precios históricos
    
    Retorna
    -------
    pandas.DataFrame
        DataFrame con fechas como índice y cada instrumento como columna
    """
    
    print("\n" + "="*80)
    print("CARGANDO ÍNDICES Y FUTUROS PARA BENCHMARK Y COBERTURAS")
    print("="*80)
    
    #  Leemos el CSV con separador punto y coma (formato europeo)
    df_varios = pd.read_csv(ruta_archivo, sep=';', decimal='.')

    print(f"✓ Archivo cargado: {len(df_varios)} días de histórico")
    
    # El archivo tiene fechas en la primera columna (sin nombre) que necesitamos pasar a formato fechas
    
    
    # Primero identificamos el nombre de la primera columna (puede ser '' o algo parecido)
    columna_fecha = df_varios.columns[0]
    
    # Convertimos a datetime
    df_varios[columna_fecha] = pd.to_datetime(
        df_varios[columna_fecha],
        format='%d/%m/%Y',
        dayfirst=True,
        errors='coerce'
    )
    
    
    # Ponemos las fechas como el "nombre" de cada fila, así es más fácil buscar
    # datos de un día específico (ej: "dame los precios del 01/10/2025")
    df_varios = df_varios.set_index(columna_fecha)
    df_varios.index.name = 'Fecha'
    
    print("✓ Fechas convertidas y establecidas como índice")
    
    
    # Acortamos los nombres para que sean más fáciles de escribir
    nombres_cortos = {
        'ITRX EUR CDSI GEN 5Y Corp': 'iTraxx_Main',
        'ITRX XOVER CDSI GEN 5Y Corp': 'iTraxx_Xover',
        'DU1 Comdty': 'Schatz_2Y',
        'OE1 Comdty': 'Bobl_5Y',
        'RX1 Comdty': 'Bund_10Y',
        'RECMTREU Index': 'Benchmark'
    }
    
    df_varios = df_varios.rename(columns=nombres_cortos)
    
    print("✓ Columnas renombradas para mayor claridad")
    
    # Convertimos todas las columnas a tipo numérico
    
    for col in df_varios.columns:
        df_varios[col] = pd.to_numeric(df_varios[col], errors='coerce')
    
    #  Eliminamos filas donde TODAS las columnas son NaN (días sin datos)
    
    df_varios = df_varios.dropna(how='all')
    
    # Interpolación lineal para días con datos parciales
    #  Si un día solo falta el precio de un producto (pero tenemos los demás),
    # calculamos ese precio como el promedio del día anterior y el día siguiente
    df_varios = df_varios.interpolate(method='linear', limit_direction='both')
    
    print(f"✓ Datos numéricos procesados")
    print(f"✓ Período: {df_varios.index.min().strftime('%d/%m/%Y')} a {df_varios.index.max().strftime('%d/%m/%Y')}")
    print(f"✓ Instrumentos disponibles: {list(df_varios.columns)}")
    
    print("\n✓✓ ÍNDICES Y FUTUROS CARGADOS Y LISTOS ✓✓\n")
    
    return df_varios


# ----- FUNCIÓN DE PRUEBA (OPCIONAL) -----
# Esta función solo se ejecuta si corres este archivo directamente
# No se ejecuta cuando lo importas desde otro archivo

if __name__ == '__main__':
    """
    Este bloque solo se ejecuta si corres directamente: python cargador_datos.py
    Es útil para probar que todo funciona antes de usarlo en el análisis principal.
    """
    print("\n" + "="*80)
    print("PROBANDO EL MÓDULO CARGADOR_DATOS")
    print("="*80)
    
    # Probamos cargar el universo
    universo = cargar_y_limpiar_universo()
    print(f"\nPrimeros 3 bonos del universo:")
    print(universo[['ISIN', 'Description', 'Coupon', 'Maturity', 'Fecha_Vencimiento_Efectiva']].head(3))
    
    # Probamos cargar la curva
    curva = cargar_curva_estr()
    print(f"\nPrimeros 5 puntos de la curva:")
    print(curva[['Date', 'Zero Rate', 'Discount', 'Plazo_Años']].head(5))
    
    # Probamos cargar precios
    precios = cargar_precios_mercado()
    print(f"\nPrimeros 3 precios de mercado:")
    print(precios.head(3))
    
    # Probamos cargar índices y futuros
    indices_futuros = cargar_indices_y_futuros()
    print(f"\nÚltimos 5 días de índices y futuros:")
    print(indices_futuros.tail(5))
    
    print("\n" + "="*80)
    print("✓✓ TODAS LAS PRUEBAS PASARON EXITOSAMENTE ✓✓")
    print("="*80)

