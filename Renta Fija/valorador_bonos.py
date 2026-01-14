"""
===============================================================================
VALORADOR DE BONOS - Práctica de Renta Fija
===============================================================================
Este módulo contiene todas las clases necesarias para valorar bonos:
- CurvaDescuento: Interpola tasas de descuento para cualquier fecha
- Bono: Representa un bono con sus características
- ValoradorBono: Calcula precios, YTC, duraciones y convexidades
===============================================================================
"""

# Importamos las librerías necesarias
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta  # Para sumar meses/años a fechas
from scipy.optimize import root_scalar  # Para encontrar la TIR (Yield)
from scipy.interpolate import interp1d  # Para interpolar


class CurvaDescuento:
    """
    Esta clase representa la curva de tasas de descuento libre de riesgo.
    
    ¿Qué hace?
    ----------
    - Guarda los puntos de la curva ESTR (fechas, tasas, factores de descuento)
    - Interpola para obtener la tasa o factor de descuento para cualquier fecha
    - Usa interpolación exponencial (la forma correcta para tasas de interés)
    
    ¿Por qué es importante?
    -----------------------
    Para valorar un bono, necesitamos descontar sus flujos futuros.
    La curva nos dice qué tasa usar para cada fecha futura.
    """
    
    def __init__(self, df_curva):
        """
        Inicializa la curva de descuento.
        
        Parámetros
        ----------
        df_curva : pandas.DataFrame
            DataFrame con las columnas: Date, Zero Rate, Discount, Plazo_Años
        """
        # Guardamos el DataFrame de la curva
        self.df_curva = df_curva.copy()
        
        # Guardamos la fecha de valoración (la primera fecha de la curva)
        self.fecha_valoracion = df_curva['Date'].iloc[0]
        
        # Ordenamos por plazo 
        self.df_curva = self.df_curva.sort_values('Plazo_Años')
        
        # Creamos interpoladores
        
        
        # Interpolador para las tasas zero (usamos interpolación lineal en tasas)
        self.interpolador_tasa = interp1d(
            self.df_curva['Plazo_Años'],     # X: plazos en años
            self.df_curva['Zero Rate'],       # Y: tasas zero
            kind='linear',                    # Interpolación lineal
            fill_value='extrapolate',         # Si está fuera del rango, extrapolar
            bounds_error=False                # No dar error si está fuera del rango
        )
        
        # Interpolador para factores de descuento (usamos interpolación exponencial)
        # Interpolamos el LOG del factor de descuento, con el logaritmo aplanamos la curva de descuento
        # y así podemos hacer interpolación lineal sobre ella
        # La curva se "desaplana" con el e de la formula de factor de descuento
        log_discount = np.log(self.df_curva['Discount'])
        self.interpolador_log_discount = interp1d(
            self.df_curva['Plazo_Años'],
            log_discount,
            kind='linear',
            fill_value='extrapolate',
            bounds_error=False
        )
    
    def obtener_factor_descuento(self, fecha):
        """
        Obtiene el factor de descuento para una fecha específica.
        
        ¿Qué es el factor de descuento?
        --------------------------------
        Es el factor por el cual multiplicamos un flujo futuro para traerlo a valor presente.
        Por ejemplo, si el factor es 0.95, significa que 100€ en esa fecha valen 95€ hoy.
        
        Fórmula: DF(t) = e^(-r*t)
        Donde:
        - DF = Factor de Descuento
        - r = tasa zero cupón
        - t = tiempo en años
        - e = número de Euler (2.71828...)
        
        Parámetros
        ----------
        fecha : datetime
            La fecha para la cual queremos el factor de descuento
        
        Retorna
        -------
        float
            El factor de descuento (un número entre 0 y 1)
        """
        # Calculamos cuántos años hay desde la fecha de valoración hasta la fecha objetivo
        dias = (fecha - self.fecha_valoracion).days
        plazo_años = dias / 365.0  
        
        # Si el plazo es 0 o negativo (fecha en el pasado), el factor es 1
        if plazo_años <= 0:
            return 1.0
        
        # Interpolamos el LOG del factor de descuento
        log_discount = self.interpolador_log_discount(plazo_años)
        
        # Calculamos el factor de descuento: DF = e^(log_discount)
        factor_descuento = np.exp(log_discount)
        
        return factor_descuento
    
    def obtener_tasa_zero(self, fecha):
        """
        Obtiene la tasa zero cupón para una fecha específica.
        
        Parámetros
        ----------
        fecha : datetime
            La fecha para la cual queremos la tasa
        
        Retorna
        -------
        float
            La tasa zero cupón (como decimal, ej: 0.02 = 2%)
        """
        # Calculamos el plazo en años
        dias = (fecha - self.fecha_valoracion).days
        plazo_años = dias / 365.0
        
        # Si el plazo es 0 o negativo, devolvemos la primera tasa de la curva
        if plazo_años <= 0:
            return self.df_curva['Zero Rate'].iloc[0] / 100.0
        
        # Interpolamos la tasa
        tasa = self.interpolador_tasa(plazo_años)
        
        # La tasa está en porcentaje, la pasamos a decimal
        return tasa / 100.0


class Bono:
    """
    Esta clase representa un bono individual con todas sus características.
    
    """
    
    def __init__(self, isin, cupon, fecha_vencimiento, frecuencia_cupon, fecha_emision=None, 
                 fecha_primer_cupon=None, nominal=100):
        """
        Inicializa un objeto Bono.
        
        Parámetros
        ----------
        isin : str
            Identificador único del bono (International Securities Identification Number)
        cupon : float
            Tasa de cupón anual como decimal (ej: 0.075 = 7.5%)
        fecha_vencimiento : datetime
            Fecha en que el bono vence (o es llamado si hay call)
        frecuencia_cupon : int
            Número de cupones por año (1=anual, 2=semestral, 4=trimestral)
        fecha_emision : datetime, opcional
            Fecha en que se emitió el bono (NECESARIA para cupón corrido)
        fecha_primer_cupon : datetime, opcional
            Fecha del primer pago de cupón
        nominal : float
            Valor nominal del bono (normalmente 100)
        """
        # Guardamos todas las características del bono
        self.isin = isin
        self.cupon = cupon
        self.fecha_vencimiento = fecha_vencimiento
        self.frecuencia_cupon = int(frecuencia_cupon) if not pd.isna(frecuencia_cupon) else 1
        self.fecha_emision = fecha_emision
        self.fecha_primer_cupon = fecha_primer_cupon
        self.nominal = nominal
        
        # Calculamos cuántos meses hay entre pagos
        # Ejemplo: si frecuencia = 2 (semestral), entonces meses_por_pago = 12/2 = 6 meses
        self.meses_por_pago = 12 // self.frecuencia_cupon
    
    def encontrar_fechas_cupon(self, fecha_valoracion):
        """
        Encuentra las fechas del último cupón pagado y el siguiente cupón.
        
        ¿Por qué necesitamos esto?
        ---------------------------
        Para calcular el CUPÓN CORRIDO (accrued interest), necesitamos saber:
        - Cuándo fue el último pago de cupón (fecha_ultimo_cupon)
        - Cuándo será el siguiente pago (fecha_siguiente_cupon)
        - Cuántos días han pasado desde el último pago (para calcular los intereses acumulados)
        
        Ejemplo:
        - Último cupón: 1 de enero
        - Siguiente cupón: 1 de julio (6 meses después)
        - Hoy: 1 de abril (han pasado 3 meses)
        - El vendedor te cobra 3 meses de intereses (50% del cupón semestral)
        
        Parámetros
        ----------
        fecha_valoracion : datetime
            La fecha de hoy (cuando estamos valorando el bono)
        
        Retorna
        -------
        dict
            Diccionario con:
            - 'ultimo': fecha del último cupón pagado
            - 'siguiente': fecha del próximo cupón a pagar
        """
        
        # Empezamos desde la fecha de vencimiento (el último pago definitivo)
        fecha_siguiente_cupon = self.fecha_vencimiento
        
        # Vamos retrocediendo período por período hasta encontrar el período que
        # "envuelve" la fecha de valoración (es decir, que la fecha_valoracion
        # esté entre dos pagos de cupón)
        
        # Mientras la fecha_siguiente_cupon sea DESPUÉS de la fecha_valoracion,
        # seguimos retrocediendo
        while fecha_siguiente_cupon > fecha_valoracion:
            # Guardamos la fecha siguiente
            fecha_anterior = fecha_siguiente_cupon
            
            # Retrocedemos un período de cupón (ej: 6 meses si es semestral)
            # relativedelta nos permite restar meses de forma precisa
            fecha_siguiente_cupon = fecha_siguiente_cupon - relativedelta(months=self.meses_por_pago)
            
            # Si al retroceder nos pasamos de la fecha de valoración,
            # significa que encontramos el período correcto
            if fecha_siguiente_cupon <= fecha_valoracion < fecha_anterior:
                # fecha_siguiente_cupon es el ÚLTIMO cupón pagado
                # fecha_anterior es el SIGUIENTE cupón a pagar
                return {
                    'ultimo': fecha_siguiente_cupon,
                    'siguiente': fecha_anterior
                }
        
        # Si llegamos aquí, algo salió mal (caso muy raro)
        # Devolvemos fechas por defecto
        return {
            'ultimo': fecha_valoracion,
            'siguiente': fecha_valoracion + relativedelta(months=self.meses_por_pago)
        }
    
    def generar_flujos_caja(self, fecha_valoracion):
        """
        Genera todos los flujos de caja futuros del bono.
        
        ¿Qué son los flujos de caja?
        -----------------------------
        Son todos los pagos que el bono hará en el futuro:
        - Cupones periódicos (intereses)
        - Principal al vencimiento (normalmente 100)
        
        Parámetros
        ----------
        fecha_valoracion : datetime
            La fecha desde la cual valoramos (normalmente hoy)
        
        Retorna
        -------
        pandas.DataFrame
            Tabla con dos columnas:
            - 'Fecha': fecha de cada pago
            - 'Flujo': monto de cada pago
        """
        # Lista para guardar los flujos de caja
        flujos = []
        
        # Calculamos cuánto paga cada cupón
        # Fórmula: pago_cupon = nominal * tasa_cupon / frecuencia
        # Ejemplo: Si el cupón anual es 7.5% y paga 1 vez al año:
        #          pago = 100 * 0.075 / 1 = 7.50
        pago_cupon = self.nominal * self.cupon / self.frecuencia_cupon
        
        # Generamos las fechas de pago desde el vencimiento hacia atrás
        # ¿Por qué hacia atrás? Porque es más preciso: sabemos que el último pago
        # es exactamente en la fecha de vencimiento
        
        fecha_actual = self.fecha_vencimiento
        
        # Calculamos cuántos meses hay entre pagos
        # Ejemplo: si frecuencia=2 (semestral), meses_entre_cupones = 12/2 = 6 meses
        meses_entre_cupones = 12 // self.frecuencia_cupon
        
        # Generamos fechas de pago hacia atrás hasta llegar a la fecha de valoración
        while fecha_actual > fecha_valoracion:
            # Si la fecha de pago es en el futuro, la agregamos
            if fecha_actual > fecha_valoracion:
                flujos.append({
                    'Fecha': fecha_actual,
                    'Flujo': pago_cupon
                })
            
            # Retrocedemos un período de cupón
            fecha_actual = fecha_actual - relativedelta(months=meses_entre_cupones)
        
        # El último flujo (en el vencimiento) incluye también el principal
        if len(flujos) > 0:
            flujos[0]['Flujo'] += self.nominal  # Sumamos el nominal (100) al último cupón
        
        # Invertimos la lista para que quede en orden cronológico (del más cercano al más lejano)
        flujos.reverse()
        
        # Convertimos la lista a DataFrame (tabla)
        df_flujos = pd.DataFrame(flujos)
        
        return df_flujos


class ValoradorBono:
    """
    Esta clase se encarga de valorar bonos y calcular sus métricas de riesgo.
    
    ¿Qué hace?
    ----------
    - Calcula el precio teórico de un bono (Parte 2)
    - Calcula el YTC (Yield to Call/Maturity) (Parte 4)
    - Calcula métricas estándar: Duración Macaulay, Modificada, Convexidad (Parte 4)
    - Calcula métricas efectivas: DV01, Duración Efectiva, Convexidad Efectiva (Parte 4 - extra)
    """
    
    def __init__(self, bono, curva_descuento):
        """
        Inicializa el valorador.
        
        Parámetros
        ----------
        bono : Bono
            El objeto Bono que vamos a valorar
        curva_descuento : CurvaDescuento
            La curva de tasas libre de riesgo
        """
        self.bono = bono
        self.curva = curva_descuento
    
    def valorar(self, fecha_valoracion, spread_credito_pb=0):
        """
        PARTE 2: Calcula el precio teórico del bono.
        
        ¿Cómo se valora un bono?
        ------------------------
        1. Generamos todos los flujos de caja futuros (cupones + principal)
        2. Para cada flujo, obtenemos su factor de descuento de la curva
        3. Descontamos cada flujo: Valor = Flujo * Factor_Descuento * Factor_Spread
        4. Sumamos todos los valores presentes = Precio Sucio
        5. Restamos el cupón corrido = Precio Limpio
        
        Parámetros
        ----------
        fecha_valoracion : datetime
            Fecha en la que valoramos el bono
        spread_credito_pb : float
            Spread de crédito en puntos básicos (1% = 100pb)
            Esto se suma a la curva libre de riesgo
        
        Retorna
        -------
        dict
            Diccionario con:
            - 'Precio_Limpio': precio sin cupón corrido
            - 'Precio_Sucio': precio con cupón corrido
            - 'Cupon_Corrido': interés acumulado desde el último pago
        """
        # Generamos los flujos de caja futuros
        df_flujos = self.bono.generar_flujos_caja(fecha_valoracion)
        
        # Si no hay flujos, el bono ya venció
        if len(df_flujos) == 0:
            return {
                'Precio_Limpio': 0,
                'Precio_Sucio': 0,
                'Cupon_Corrido': 0
            }
        
        # Convertimos el spread de puntos básicos a decimal
        # Ejemplo: 100pb = 1% = 0.01
        spread_decimal = spread_credito_pb / 10000.0
        
        # Calculamos el valor presente de cada flujo
        valor_presente_total = 0
        
        for idx, fila in df_flujos.iterrows():
            fecha_flujo = fila['Fecha']
            monto_flujo = fila['Flujo']
            
            # Obtenemos el factor de descuento de la curva libre de riesgo
            factor_descuento_libre_riesgo = self.curva.obtener_factor_descuento(fecha_flujo)
            
            # Calculamos cuántos años hasta ese flujo
            años_hasta_flujo = (fecha_flujo - fecha_valoracion).days / 365.0
            
            # Aplicamos el spread de crédito
            # Factor_spread = e^(-spread * tiempo)
            factor_spread = np.exp(-spread_decimal * años_hasta_flujo)
            
            # Factor de descuento total = riesgo_libre * spread
            factor_descuento_total = factor_descuento_libre_riesgo * factor_spread
            
            # Valor presente de este flujo = Flujo * Factor_Descuento
            valor_presente = monto_flujo * factor_descuento_total
            
            # Sumamos al total
            valor_presente_total += valor_presente
        
        # El precio sucio es la suma de todos los valores presentes
        precio_sucio = valor_presente_total
        

        
        # PASO 1: Encontrar las fechas del último y siguiente cupón
        # ---------------------------------------------------------
        # Usamos el método encontrar_fechas_cupon() 
        fechas = self.bono.encontrar_fechas_cupon(fecha_valoracion)
        fecha_ultimo_cupon = fechas['ultimo']
        fecha_siguiente_cupon = fechas['siguiente']
        
        # PASO 2: Calcular cuántos días tiene el período completo
        # --------------------------------------------------------
        # Ejemplo: del 1 de enero al 1 de julio = 181 días (aprox)
        dias_totales_periodo = (fecha_siguiente_cupon - fecha_ultimo_cupon).days
        
        # PASO 3: Calcular cuántos días han pasado desde el último cupón
        # ---------------------------------------------------------------
        # Ejemplo: si hoy es 1 de abril, han pasado 90 días desde el 1 de enero
        dias_corridos = (fecha_valoracion - fecha_ultimo_cupon).days
        
        # PASO 4: Calcular el importe del cupón de este período
        # ------------------------------------------------------
        # El cupón anual (ej: 7.5%) se divide entre el número de pagos al año
        # Ejemplo: si cupón anual = 7.5% y paga 2 veces al año (semestral):
        #          importe_este_cupon = 7.5 / 2 = 3.75
        
        importe_cupon_anual = self.bono.cupon * self.bono.nominal  # Ej: 0.075 * 100 = 7.5
        importe_este_cupon = importe_cupon_anual / self.bono.frecuencia_cupon  # Ej: 7.5 / 2 = 3.75
        
        # PASO 5: Calcular el cupón corrido (interés acumulado)
        # ------------------------------------------------------
        # CONVENCIÓN ACT/365:
        # - ACT: Días reales (actual days) desde el último cupón
        # - 365: Base fija de 365 días (sin importar el período real)
        # 
        # Fórmula: cupón_corrido = cupón_anual × (días_corridos / 365)
        # 
        # Ejemplo: Cupón anual = 7.5, días corridos = 250
        #          cupón_corrido = 7.5 × (250/365) = 5.137
        # 
        # IMPORTANTE: A diferencia de ACT/ACT, aquí SIEMPRE dividimos por 365,
        
        
        # Calculamos el cupón corrido usando ACT/365
        # El importe anual del cupón lo dividimos por 365 y multiplicamos por los días corridos
        cupon_corrido = importe_cupon_anual * (dias_corridos / 365.0)
        
        # PASO 6: Calcular el precio limpio
        # ----------------------------------
        # El precio limpio es el precio sucio MENOS el cupón corrido
        # ¿Por qué? Porque el precio sucio incluye el cupón acumulado, pero
        # en el mercado se cotiza el "precio limpio" (sin el cupón corrido)
        
        precio_limpio = precio_sucio - cupon_corrido
        
        # Retornamos los tres valores
        return {
            'Precio_Limpio': precio_limpio,
            'Precio_Sucio': precio_sucio,
            'Cupon_Corrido': cupon_corrido
        }
    
    def calcular_ytc(self, fecha_valoracion, precio_mercado_limpio, cupon_corrido):
        """
        PARTE 4 -  Calcula el Yield-to-Call/Maturity (YTC/YTM).
        
        ¿Qué es el YTC?
        ---------------
        Es la tasa interna de retorno (TIR) del bono.
        Es la tasa de descuento que hace que el valor presente de los flujos
        sea igual al precio de mercado.
        
        ¿Cómo lo calculamos?
        --------------------
        Es un problema de búsqueda de raíz:
        Buscamos la tasa 'y' tal que:
        Precio_Mercado_Sucio = Suma[Flujo_i / (1+y)^t_i]
        
        Usamos scipy.optimize.root_scalar para encontrarla.
        
        Parámetros
        ----------
        fecha_valoracion : datetime
            Fecha de valoración
        precio_mercado_limpio : float
            Precio de mercado observado (limpio)
        cupon_corrido : float
            Cupón corrido pre-calculado (obtenido desde valorar())
            
        
        Retorna
        -------
        float
            El YTC como decimal (ej: 0.035 = 3.5%)
        """
        # Generamos los flujos de caja
        df_flujos = self.bono.generar_flujos_caja(fecha_valoracion)
        
        if len(df_flujos) == 0:
            return np.nan
        
        # Convertimos el Precio Limpio a Precio Sucio usando el cupón corrido pre-calculado
       
        precio_mercado_sucio = precio_mercado_limpio + cupon_corrido
        
        # Función objetivo: diferencia entre precio teórico y precio de mercado
        def funcion_objetivo(ytc):
            """
            Esta función calcula: Precio_Teorico_Sucio(ytc) - Precio_Mercado_Sucio
            Cuando esta diferencia es 0, hemos encontrado el YTC correcto.
            
            
            """
            valor_presente = 0
            
            for idx, fila in df_flujos.iterrows():
                fecha_flujo = fila['Fecha']
                monto_flujo = fila['Flujo']
                
                # Años hasta el flujo
                años = (fecha_flujo - fecha_valoracion).days / 365.0
                
                # Descontamos con el YTC
                # VP = Flujo / (1 + ytc)^años
                valor_presente += monto_flujo / ((1 + ytc) ** años)
            
            # Retornamos la diferencia (ahora comparamos Sucio con Sucio)
            return valor_presente - precio_mercado_sucio
        
        # Buscamos la raíz (donde la función objetivo = 0)
        try:
            resultado = root_scalar(
                funcion_objetivo,
                bracket=[0.0001, 0.5],  # Buscamos entre 0.01% y 50% (rango amplio)
                method='brentq'          # Método de Brent 
            )
            ytc = resultado.root
        except:
            # Si falla, usamos un método más robusto
            try:
                resultado = root_scalar(
                    funcion_objetivo,
                    x0=0.03,     # Semilla inicial: 3%
                    x1=0.05,     # Segunda semilla: 5%
                    method='secant'
                )
                ytc = resultado.root
            except:
                # Si todo falla, devolvemos NaN
                ytc = np.nan
        
        return ytc
    
    def calcular_analiticas_std(self, fecha_valoracion, ytc):
        """
        PARTE 4 -  Calcula métricas de riesgo estándar (de libro de texto).
        
        Métricas calculadas:
        --------------------
        1. Duración Macaulay: Promedio ponderado del tiempo hasta cada flujo
           - Medida en años
           - Nos dice el "plazo efectivo" del bono
        
        2. Duración Modificada: Duración Macaulay / (1 + YTC)
           - Sensibilidad del precio a cambios en tasas
           - Si Duración Mod = 5, un aumento de 1% en tasas -> precio cae 5%
        
        3. Convexidad: Curvatura de la relación precio-tasa
           - Corrección de segundo orden
           - Los bonos tienen convexidad positiva (precio sube más de lo que cae)
        
        Parámetros
        ----------
        fecha_valoracion : datetime
            Fecha de valoración
        ytc : float
            Yield-to-Call calculado previamente
        
        Retorna
        -------
        dict
            Diccionario con las métricas calculadas
        """
        # Guardamos los flujos de caja
        df_flujos = self.bono.generar_flujos_caja(fecha_valoracion)
        
        if len(df_flujos) == 0 or np.isnan(ytc):
            return {
                'Duracion_Macaulay': np.nan,
                'Duracion_Modificada': np.nan,
                'Convexidad': np.nan
            }
        
        # Variables para acumular
        precio_total = 0
        duracion_ponderada = 0
        convexidad_ponderada = 0
        
       # Para cada flujo, calculamos su contribución 
        for idx, fila in df_flujos.iterrows():
            fecha_flujo = fila['Fecha']
            monto_flujo = fila['Flujo']
            
            # Tiempo en años
            t = (fecha_flujo - fecha_valoracion).days / 365.0
            
            # Valor presente de este flujo
            # VP = Flujo / (1 + ytc)^t
            vp = monto_flujo / ((1 + ytc) ** t)
            
            # Acumulamos el precio
            precio_total += vp
            
            # Para la Duración Macaulay:
            # Cada flujo aporta: (t * VP)
            duracion_ponderada += t * vp
            
            # Para la Convexidad:
            # Cada flujo aporta: (t * (t+1) * VP)
            convexidad_ponderada += t * (t + 1) * vp
        
        # DURACIÓN MACAULAY
        # Es el promedio ponderado de los tiempos
        # Fórmula: D_Mac = Suma(t * VP_t) / Precio
        duracion_macaulay = duracion_ponderada / precio_total
        
        # DURACIÓN MODIFICADA
        # Es la sensibilidad del precio a cambios en el yield
        # Fórmula: D_Mod = D_Mac / (1 + YTC)
        duracion_modificada = duracion_macaulay / (1 + ytc)
        
        # CONVEXIDAD
        # Mide la curvatura de la relación precio-yield
        # Fórmula: C = Suma(t*(t+1)*VP_t) / (Precio * (1+YTC)^2)
        convexidad = convexidad_ponderada / (precio_total * ((1 + ytc) ** 2))
        
        return {
            'Duracion_Macaulay': duracion_macaulay,
            'Duracion_Modificada': duracion_modificada,
            'Convexidad': convexidad
        }
    
    def calcular_analiticas_efectivas(self, fecha_valoracion, spread_mercado_pb):
        """
        PARTE 4 - Calcula métricas de riesgo efectivas.
        
        ¿Por qué son mejores?
        ---------------------
        Las métricas estándar asumen que todos los flujos se descuentan con la misma tasa (YTC).
        Las métricas efectivas usan la curva completa y miden el impacto de mover TODA la curva.
        
        Método: "Bumping" (sacudida)
        ----------------------------
        1. Valoramos el bono con la curva actual -> Precio_0
        2. Movemos la curva +1bp -> Valoramos -> Precio_up
        3. Movemos la curva -1bp -> Valoramos -> Precio_down
        4. Calculamos las diferencias
        
        Métricas calculadas:
        --------------------
        1. DV01 (Dollar Value of 1bp): Cuánto dinero pierdo si las tasas suben 1bp
           - Ejemplo: DV01 = 0.05 significa que por cada millón de nominal,
             pierdo 500€ si las tasas suben 1bp
        
        2. Duración Efectiva: Sensibilidad en términos porcentuales
           - Similar a Duración Modificada, pero usando la curva completa
        
        3. Convexidad Efectiva: Curvatura usando la curva completa
        
        Parámetros
        ----------
        fecha_valoracion : datetime
            Fecha de valoración
        spread_mercado_pb : float
            Spread de crédito en puntos básicos
        
        Retorna
        -------
        dict
            Diccionario con las métricas efectivas
        """
        # Tamaño del movimiento de la curva (en puntos básicos)
        # 1bp = 0.01% = 0.0001 en decimal
        bump_pb = 1  # 1 punto básico
        bump_decimal = bump_pb / 10000.0
        
        # PASO 1: Valoramos con la curva actual
        resultado_base = self.valorar(fecha_valoracion, spread_mercado_pb)
        precio_base = resultado_base['Precio_Limpio']
        
        # PASO 2: Valoramos con la curva movida +1bp
        # Para esto, creamos una curva temporal modificada
        df_curva_up = self.curva.df_curva.copy()
        # Zero Rate está en PORCENTAJE. 1 bp = 0.01 puntos porcentuales
        df_curva_up['Zero Rate'] = df_curva_up['Zero Rate'] + (bump_pb / 100.0)
        # Recalculamos los factores de descuento
        df_curva_up['Discount'] = np.exp(-df_curva_up['Zero Rate'] / 100.0 * df_curva_up['Plazo_Años'])
        curva_up = CurvaDescuento(df_curva_up)
        
        # Creamos un valorador temporal con la curva movida arriba
        valorador_up = ValoradorBono(self.bono, curva_up)
        resultado_up = valorador_up.valorar(fecha_valoracion, spread_mercado_pb)
        precio_up = resultado_up['Precio_Limpio']
        
        # PASO 3: Valoramos con la curva movida -1bp
        df_curva_down = self.curva.df_curva.copy()
        df_curva_down['Zero Rate'] = df_curva_down['Zero Rate'] - (bump_pb / 100.0)
        df_curva_down['Discount'] = np.exp(-df_curva_down['Zero Rate'] / 100.0 * df_curva_down['Plazo_Años'])
        curva_down = CurvaDescuento(df_curva_down)
        
        # Valorador con curva movida abajo
        valorador_down = ValoradorBono(self.bono, curva_down)
        resultado_down = valorador_down.valorar(fecha_valoracion, spread_mercado_pb)
        precio_down = resultado_down['Precio_Limpio']
        
        # CÁLCULO DE MÉTRICAS
        
        # DV01 (Dollar Value of 1bp)
        # Es la pérdida de valor cuando las tasas suben 1bp
        # Fórmula: DV01 = (Precio_down - Precio_up) / 2
        # (Dividimos entre 2 porque movimos ±1bp, queremos el efecto de 1bp)
        dv01 = (precio_down - precio_up) / 2.0
        
        # DURACIÓN EFECTIVA
        # Mide el cambio porcentual del precio por cambio unitario en tasas
        # Fórmula: D_eff = (P_down - P_up) / (2 * P_0 * Δy)
        # Donde Δy es el cambio en yield (en decimal)
        delta_y = 2 * bump_decimal  # El cambio total es 2bp (de -1bp a +1bp)
        duracion_efectiva = (precio_down - precio_up) / (2 * precio_base * bump_decimal)
        
        # CONVEXIDAD EFECTIVA
        # Mide la curvatura
        # Fórmula: C_eff = (P_up + P_down - 2*P_0) / (P_0 * Δy^2)
        convexidad_efectiva = (precio_up + precio_down - 2 * precio_base) / (precio_base * (bump_decimal ** 2))
        
        return {
            'DV01': dv01,
            'Duracion_Efectiva': duracion_efectiva,
            'Convexidad_Efectiva': convexidad_efectiva,
            'Precio_Base': precio_base,
            'Precio_Up': precio_up,
            'Precio_Down': precio_down
        }
    
    def calcular_cs01(self, fecha_valoracion, spread_mercado_pb):
        """
        Calcula el CS01 (Credit Spread 01).
        
        ¿Qué es el CS01?
        ----------------
        CS01 significa "Credit Spread 01" o "Spread DV01".
        Es la sensibilidad del precio del bono a cambios en el SPREAD DE CRÉDITO.
        
        ¿En qué se diferencia del DV01?
        --------------------------------
        - DV01: Mide el riesgo de TASAS DE INTERÉS (curva ESTR del BCE)
          → Si el BCE sube/baja tasas, ¿cuánto pierdo/gano?
        
        - CS01: Mide el riesgo de CRÉDITO (spread de la empresa)
          → Si la empresa se vuelve más/menos riesgosa, ¿cuánto pierdo/gano?
        
        ¿Por qué es importante?
        -----------------------
        En un bono corporativo hay DOS fuentes de riesgo:
        
        1. RIESGO DE TASAS (DV01):
           - El BCE puede subir tasas → Todos los bonos bajan
           - Lo puedes cubrir con futuros del Bund
        
        2. RIESGO DE CRÉDITO (CS01):
           - La empresa puede empeorar (peor rating) → Su spread sube → Precio baja
           - Lo cubres con CDS (Credit Default Swaps) o vendiendo el bono
        
        Ejemplo práctico:
        -----------------
        Supón que tienes un bono de Telefónica:
        - DV01 = 5.0  → Si BCE sube 1bp, pierdes 5€ por cada 100€
        - CS01 = 3.0  → Si spread de Telefónica sube 1bp, pierdes 3€ por cada 100€
        
        Si las noticias dicen que Telefónica tiene problemas financieros:
        → El spread sube 50bp
        → Pérdida = CS01 × 50 = 3.0 × 50 = 150€ por cada 100€ de nominal
        
        Método de cálculo (Bumping del spread):
        ----------------------------------------
        Similar al DV01, pero movemos el SPREAD en lugar de la curva:
        1. Valoramos con spread actual → Precio_base
        2. Valoramos con spread + 1bp → Precio_up
        3. Valoramos con spread - 1bp → Precio_down
        4. CS01 = (Precio_down - Precio_up) / 2
        
        Parámetros
        ----------
        fecha_valoracion : datetime
            Fecha de valoración
        spread_mercado_pb : float
            Spread de crédito actual en puntos básicos
        
        Retorna
        -------
        float
            El CS01 (sensibilidad al spread en términos monetarios)
        """
        
        # PASO 1: Valoramos con el spread actual (base)
        # ----------------------------------------------
        # Este es el precio con el spread de mercado actual
        resultado_base = self.valorar(fecha_valoracion, spread_mercado_pb)
        precio_base = resultado_base['Precio_Sucio']  # Usamos precio sucio para consistencia
        
        # PASO 2: Valoramos con el spread AUMENTADO en 1bp
        # -------------------------------------------------
        # Si el spread sube 1bp, la empresa es más riesgosa → Precio baja
        # Mantenemos la curva ESTR fija, solo movemos el spread
        spread_up = spread_mercado_pb + 1  # Subimos 1 punto básico
        resultado_up = self.valorar(fecha_valoracion, spread_up)
        precio_up = resultado_up['Precio_Sucio']
        
        # PASO 3: Valoramos con el spread REDUCIDO en 1bp
        # ------------------------------------------------
        # Si el spread baja 1bp, la empresa es menos riesgosa → Precio sube
        spread_down = spread_mercado_pb - 1  # Bajamos 1 punto básico
        resultado_down = self.valorar(fecha_valoracion, spread_down)
        precio_down = resultado_down['Precio_Sucio']
        
        # PASO 4: Calculamos el CS01
        # ---------------------------
        # CS01 = (Precio_down - Precio_up) / 2
        # Dividimos entre 2 porque el movimiento total es 2bp (de -1bp a +1bp)
        # y queremos la sensibilidad a 1bp
        cs01 = (precio_down - precio_up) / 2.0
        
        # Retornamos el CS01
        # Un CS01 positivo significa: si el spread baja, gano dinero (lo normal)
        return cs01
    
    def calcular_z_spread(self, fecha_valoracion, precio_mercado_limpio):
        """
        PARTE 3: Calcula el Z-Spread de un bono.
        
        ¿Qué es el Z-Spread?
        --------------------
        Es el spread constante (en puntos básicos) que, añadido a cada punto de la curva
        de tipos libre de riesgo (ESTR), hace que el valor presente de los flujos del bono
        iguale su precio de mercado observado. A diferencia del spread simple sobre la TIR,
        el Z-Spread considera toda la estructura temporal de tasas de interés.
        
        Es como preguntarse: "¿Cuántos puntos básicos de rendimiento extra (sobre
        la curva libre de riesgo) me está pagando este bono para compensar su riesgo de crédito,
        liquidez y otras primas?"
        
        ¿Por qué es importante?
        ------------------------
       
        
        Nos dice si un bono está "caro" o "barato" comparado con otros:
       
        Ejemplo práctico:
        -----------------
        Si un bono de Telefónica tiene un Z-Spread de 150 pb y uno de Banco Santander
        tiene 120 pb (siendo similares en duración y rating), entonces Telefónica paga
        30 pb más. ¿Es justo? ¿O Telefónica es una oportunidad?
        
        Método de cálculo (Root-finding):
        ----------------------------------
        Utilizamos el método de Brent (scipy.optimize.root_scalar) para encontrar
        el spread Z que satisface: Precio_Mercado = Precio_Teorico(spread_Z)
        
        Probamos diferentes valores de spread hasta encontrar el que hace que
        nuestro precio calculado sea igual al precio de mercado. Es como ajustar un botón
        hasta que dos números coincidan.
        
        Parámetros
        ----------
        fecha_valoracion : datetime
            Fecha de valoración
        precio_mercado_limpio : float
            Precio de mercado observado (clean price)
        
        Retorna
        -------
        float
            El Z-Spread en puntos básicos (ej: 150 significa 1.50%)
        """
        
        # Definimos la función objetivo para el solver: error = precio_calculado - precio_mercado
        # Creamos una función que calcula la diferencia entre el precio que obtenemos
        # con un spread y el precio real del mercado. Queremos que esta diferencia sea cero.
        def objetivo(spread_pb):
            """
            Función que calcula el error de pricing para un spread dado.
            El solver buscará el spread que haga este error = 0.
            """
            # Valoramos el bono con este spread de prueba
            resultado = self.valorar(fecha_valoracion, spread_pb)
            precio_calculado = resultado['Precio_Limpio']
            
            # Retornamos la diferencia (error)
            # Si es positivo: estamos valorando muy alto (spread muy bajo)
            # Si es negativo: estamos valorando muy bajo (spread muy alto)
            return precio_calculado - precio_mercado_limpio
        
        # Utilizamos root_scalar con método 'brent' para encontrar el cero de la función
        # Le pedimos a Python que pruebe diferentes spreads hasta encontrar el correcto
        try:
            # Definimos un intervalo de búsqueda amplio [0, 2000 pb] que cubre
            # desde bonos AAA (spread ~0) hasta bonos en distress (spread ~20%)
            # Le decimos a Python: "el spread correcto está entre 0 y 2000 puntos básicos"
            resultado = root_scalar(
                objetivo,
                bracket=[0, 2000],  # Rango de búsqueda en puntos básicos
                method='brentq',  # Método de Brent (robusto y rápido)
                xtol=0.01  # Tolerancia: 0.01 pb es más que suficiente
            )
            
            # Si el solver convergió, retornamos el spread encontrado
            #  Si Python encontró el spread correcto, lo devolvemos
            if resultado.converged:
                z_spread = resultado.root
                return z_spread
            else:
                # Si no convergió, advertimos y retornamos NaN
                #  Si no se pudo encontrar, avisamos del problema
                print(f"⚠ Advertencia: Z-Spread no convergió para ISIN {self.bono.isin}")
                return np.nan
                
        except Exception as e:
            # Capturamos cualquier error (ej: precio de mercado fuera de rango razonable)
            #  Si algo sale mal (ej: precio de mercado muy raro), avisamos del error
            print(f"⚠ Error calculando Z-Spread para ISIN {self.bono.isin}: {str(e)}")
            return np.nan


# ----- FUNCIÓN DE PRUEBA (OPCIONAL) -----
if __name__ == '__main__':
    """
    Pruebas básicas del módulo.
    """
    print("\n" + "="*80)
    print("PROBANDO EL MÓDULO VALORADOR_BONOS")
    print("="*80)
    
    # Para probar, necesitaríamos cargar datos reales
    print("\nEste módulo está diseñado para ser importado.")
    print("Las pruebas completas se ejecutan desde analisis_principal.py")
    
    print("\n✓✓ MÓDULO CARGADO CORRECTAMENTE ✓✓")

