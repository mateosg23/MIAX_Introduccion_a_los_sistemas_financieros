"""
===============================================================================
GESTOR DE CARTERAS - Práctica de Renta Fija
===============================================================================
Este módulo contiene todas las clases y funciones necesarias para:
- Construir carteras de bonos (equiponderadas y restringidas)
- Realizar backtesting vs benchmark
- Calcular coberturas con futuros (Duration Hedging)
- Calcular coberturas con CDS (Credit Hedging)
- Estrategias de valor relativo (Regresión multifactorial)

===============================================================================
"""

# Importamos las librerías necesarias
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder
from scipy.optimize import linprog  # Para optimización lineal (Parte 6)
import warnings
warnings.filterwarnings('ignore')

# Configuración de visualización
    #  Usamos estilos nativos de matplotlib para gráficos profesionales
    #  Hacemos que los gráficos se vean bonitos sin necesidad de librerías extra
try:
    plt.style.use('ggplot')  # Estilo similar a seaborn
except:
    plt.style.use('default')  # Fallback si ggplot no está disponible


class GestorCarterasBonos:
    """
    Clase principal para gestión de carteras de bonos de renta fija.
    
    ¿Qué hace esta clase?
    ---------------------
    Implementa estrategias de construcción de carteras (equiponderadas, optimizadas),
    backtesting con métricas de performance, y cálculo de coberturas con derivados.
    

    """
    
    def __init__(self, df_bonos, df_valoraciones, df_indices_futuros):
        """
        Inicializa el gestor de carteras.
        
        Parámetros
        ----------
        df_bonos : pandas.DataFrame
            DataFrame con información de los bonos (rating, sector, vencimiento, etc.)
        df_valoraciones : pandas.DataFrame
            DataFrame con las valoraciones de los bonos (precios, duraciones, spreads, etc.)
        df_indices_futuros : pandas.DataFrame
            DataFrame con precios históricos de índices y futuros
        """
        self.df_bonos = df_bonos
        self.df_valoraciones = df_valoraciones
        self.df_indices_futuros = df_indices_futuros
        
        # Merge de datos de bonos con valoraciones/métricas
        # Juntamos toda la información de los bonos en una sola tabla grande
        # CRÍTICO: Usamos sufijos para evitar colisiones de columnas
        self.df_completo = pd.merge(
            df_bonos,
            df_valoraciones,
            on='ISIN',
            how='inner',
            suffixes=('_base', '')  # Preferimos las columnas de df_valoraciones (sin sufijo)
        )
        
        # DIAGNÓSTICO: Verificamos que las métricas críticas están presentes
        metricas_criticas = ['DV01', 'CS01', 'Duracion_Efectiva', 'Z_Spread']
        metricas_presentes = [col for col in metricas_criticas if col in self.df_completo.columns]
        metricas_faltantes = [col for col in metricas_criticas if col not in self.df_completo.columns]
        
        print(f"\n✓ GestorCarteras inicializado:")
        print(f"  - Bonos totales: {len(self.df_completo)}")
        print(f"  - Métricas presentes: {', '.join(metricas_presentes) if metricas_presentes else 'Ninguna'}")
        if metricas_faltantes:
            print(f"  ⚠ Métricas faltantes: {', '.join(metricas_faltantes)}")
    
    # =========================================================================
    # PARTE 5: CARTERA EQUIPONDERADA Y BACKTEST
    # =========================================================================
    
    def construir_cartera_equiponderada(self, capital_inicial=1000000):
        """
        PARTE 5: Construye una cartera equiponderada (equal-weighted).
        
        ¿Qué es una cartera equiponderada?
        -----------------------------------
        Estrategia de asignación 1/N donde cada activo recibe el mismo peso
        (wi = 1/N para todo i). Es la estrategia más simple y sorprendentemente efectiva
        según DeMiguel, Garlappi & Uppal (2009).
        
        Dividimos nuestro dinero en partes iguales entre todos los bonos.
        Si tenemos 100 bonos y 1 millón de euros, invertimos 10.000€ en cada bono.
        Es como repartir una pizza en partes iguales para todos los invitados.
        
        ¿Por qué funciona bien?
        ------------------------
        Minimiza el error de estimación en la optimización de Markowitz.
        Evita concentración excesiva en pocos activos que suelen generar carteras
        con alta volatilidad ex-post.
    
        
        Parámetros
        ----------
        capital_inicial : float
            Capital total a invertir (default: 1 millón de euros)
        
        Retorna
        -------
        pandas.DataFrame
            DataFrame con la composición de la cartera (ISIN, Peso, Nominal invertido)
        """
        
        # Calculamos el peso unitario (1/N)
        
        n_bonos = len(self.df_completo)
        peso_unitario = 1.0 / n_bonos
        
        
        # Calculamos cuántos euros invertimos en cada bono
        nominal_por_bono = capital_inicial * peso_unitario
        
        
        # Creamos una tabla con todos los bonos y cuánto compramos de cada uno
        cartera = pd.DataFrame({
            'ISIN': self.df_completo['ISIN'],
            'Nombre': self.df_completo.get('Description', self.df_completo.get('Issuer Name', 'N/A')),
            'Peso': peso_unitario,
            'Nominal_Invertido': nominal_por_bono
        })
        
        
        # Calculamos el resumen de la cartera (duración promedio, yield promedio, etc.)
        cartera['Precio_Mercado'] = self.df_completo['Precio_Mercado'].values
        cartera['Duracion_Modificada'] = self.df_completo['Duracion_Modificada'].values
        cartera['YTC'] = self.df_completo['YTC'].values
        
        # Añadimos el cupón para el cálculo de Total Return en el backtest
        if 'Coupon' in self.df_completo.columns:
            cartera['Coupon'] = self.df_completo['Coupon'].values
        
        # Añadimos métricas de riesgo calculadas en Parte 4 para coberturas
        # Estas métricas son necesarias para las Partes 7 y 8 (coberturas)
        if 'DV01' in self.df_completo.columns:
            cartera['DV01'] = self.df_completo['DV01'].values
        
        if 'CS01' in self.df_completo.columns:
            cartera['CS01'] = self.df_completo['CS01'].values
        
        if 'Duracion_Efectiva' in self.df_completo.columns:
            cartera['Duracion_Efectiva'] = self.df_completo['Duracion_Efectiva'].values
        
        return cartera
    
    def backtest_cartera_vs_benchmark(self, cartera, fecha_inicio, fecha_fin, df_precios_historicos, frecuencia_rebalanceo='M'):
        """
        PARTE 5: Realiza backtest REAL de la cartera vs el benchmark (MÉTODO DIRECTO).
        
        ¿Qué es un backtest?
        --------------------
        Simulación histórica que calcula el retorno total (precio + cupón) de una cartera
        periodo a periodo usando precios reales de mercado, sin asumir correlación con ningún índice.
        
        
        ¿Qué es el rebalanceo?
        -----------------------
        Proceso de reajustar los pesos a 1/N periódicamente para mantener la estrategia
        equiponderada tras los movimientos de precios que alteran los pesos naturalmente.
        
        
        
        Fórmula del Retorno Total (The Real Deal):
        -------------------------------------------
        R_total_t = (P_t - P_{t-1}) / P_{t-1}  +  (Cupón_Anual / 365) * Días
                    └─ Capital Gain ─┘            └─── Carry/Income ───┘
        
        
        Tu ganancia = Cuánto subió el precio + Cuánto interés te pagaron
        
        Parámetros
        ----------
        cartera : pandas.DataFrame
            Cartera a testear (debe tener columnas 'ISIN', 'Peso', 'YTC' o 'Cupón')
        fecha_inicio : datetime
            Fecha de inicio del backtest
        fecha_fin : datetime
            Fecha de fin del backtest
        df_precios_historicos : pandas.DataFrame
            DataFrame con precios históricos (fechas en columnas, ISINs en filas)
        frecuencia_rebalanceo : str
            Frecuencia de rebalanceo ('D'=diario, 'W'=semanal, 'M'=mensual)
        
        Retorna
        -------
        dict
            Diccionario con:
            - 'serie_retornos_cartera': Serie temporal de valor acumulado de la cartera
            - 'serie_retornos_benchmark': Serie temporal del benchmark
            - 'metricas': Métricas de performance (Sharpe, TE, IR, etc.)
        """
        
        print("\n✓ Iniciando backtest REAL (Método Directo - Total Return)...")
        
        
        
        # Los ISINs de nuestra cartera
        isins_cartera = cartera['ISIN'].tolist()
        
        # Filtramos solo las columnas (ISINs) de nuestra cartera
        isins_disponibles = [isin for isin in isins_cartera if isin in df_precios_historicos.columns]
        precios_cartera = df_precios_historicos[isins_disponibles].copy()
        
        print(f"  - ISINs en cartera: {len(isins_cartera)}")
        print(f"  - ISINs con datos históricos: {len(isins_disponibles)}")
        
        # Filtramos al período de backtest
        precios_cartera = precios_cartera.loc[
            (precios_cartera.index >= fecha_inicio) & 
            (precios_cartera.index <= fecha_fin)
        ]
        
        if len(precios_cartera) == 0:
            print(f"⚠ Error: No hay datos de precios para el período {fecha_inicio} - {fecha_fin}")
            return None
        
        print(f"  - Período: {precios_cartera.index.min().strftime('%d/%m/%Y')} a {precios_cartera.index.max().strftime('%d/%m/%Y')}")
        print(f"  - Días de trading: {len(precios_cartera)}")
        
        # PASO 2: Obtener cupones anuales de cada bono
        # ---------------------------------------------
        # Creamos un diccionario ISIN → Cupón para lookup rápido
        # Guardamos cuánto paga de interés cada bono para usarlo después
        
        cupones = {}
        for idx, fila in cartera.iterrows():
            isin = fila['ISIN']
            # Usamos SOLO cupón (no YTC) para el carry; 'Coupon' viene en decimal (ej: 0.055)
            if ('Coupon' in fila) and (not pd.isna(fila['Coupon'])):
                cupones[isin] = fila['Coupon'] * 100  # 0.055 -> 5.5%
            else:
                cupones[isin] = 0.0  # Si no hay cupón, asumimos 0
        
        print(f"  - Cupón promedio de la cartera: {np.mean(list(cupones.values())):.2f}%")
        
        # PASO 2.5: Forward Fill de Precios (Manejo de Festivos/Fines de Semana)
        # -------------------------------------------------------------------------
        # Rellenamos días sin precio (NaN) con el último precio conocido (Last Traded Price)
        # Si un día es festivo o fin de semana y no hay precio en el Excel (NaN), 
        # no podemos saltarnos el día porque dejaríamos de cobrar el cupón.
        # Usamos ffill() para rellenar esos huecos con el precio del último día hábil.
        # Así, la variación de precio será 0%, pero el código seguirá contando los días
        # transcurridos y sumará los intereses acumulados correctamente.
        precios_cartera = precios_cartera.ffill()
        
        # PASO 3: Calcular retornos diarios REALES (Total Return = Precio + Cupón)
        # --------------------------------------------------------------------------
        # Aplicamos la fórmula de total return para cada bono en cada fecha
        # Calculamos cuánto ganamos día a día con cada bono
        
        retornos_diarios_bonos = pd.DataFrame(index=precios_cartera.index[1:], columns=precios_cartera.columns)
        
        for i in range(1, len(precios_cartera)):
            fecha_actual = precios_cartera.index[i]
            fecha_anterior = precios_cartera.index[i-1]
            dias_transcurridos = (fecha_actual - fecha_anterior).days
            
            for isin in precios_cartera.columns:
                precio_anterior = precios_cartera.iloc[i-1][isin]
                precio_actual = precios_cartera.iloc[i][isin]
                
                # Si faltan precios, skip
                if pd.isna(precio_anterior) or pd.isna(precio_actual) or precio_anterior <= 0:
                    retornos_diarios_bonos.loc[fecha_actual, isin] = np.nan
                    continue
                
                # FÓRMULA DEL TOTAL RETURN:
                # Retorno = (P_t - P_{t-1}) / P_{t-1}  +  (Cupón / 365) * días
                retorno_precio = (precio_actual - precio_anterior) / precio_anterior
                retorno_cupon = (cupones.get(isin, 0) / 100 / 365) * dias_transcurridos  # Carry
                retorno_total = retorno_precio + retorno_cupon
                
                retornos_diarios_bonos.loc[fecha_actual, isin] = retorno_total
        
        # Convertimos a numérico
        retornos_diarios_bonos = retornos_diarios_bonos.apply(pd.to_numeric, errors='coerce')
        
        # PASO 4: Calcular retorno de la cartera CON REBALANCEO MENSUAL
        # ---------------------------------------------------------------
        # El retorno de la cartera equiponderada es el promedio aritmético de los retornos
        # Nuestro retorno total = promedio de lo que ganó cada bono (porque invertimos igual en todos)
        
        # Identificamos las fechas de rebalanceo (primer día de cada mes)
        fechas_rebalanceo = pd.date_range(start=fecha_inicio, end=fecha_fin, freq='MS')
        
        # Inicializamos los pesos a 0 y reconstituimos en el primer día observado
        pesos = pd.Series(0.0, index=retornos_diarios_bonos.columns)
        
        # Lista para guardar el valor de la cartera cada día
        valores_cartera = []
        
        # Iteramos día a día calculando el valor de la cartera
        for fecha in retornos_diarios_bonos.index:
            # Si es fecha de rebalanceo (inicio de mes) o aún no tenemos pesos, reconstituimos universo "vivo"
            if (frecuencia_rebalanceo == 'M' and fecha.day == 1) or (pesos.sum() == 0):
                precios_hoy = precios_cartera.loc[fecha]
                activos_hoy = precios_hoy[~precios_hoy.isna()].index.tolist()
                if len(activos_hoy) > 0:
                    pesos = pd.Series(0.0, index=retornos_diarios_bonos.columns)
                    pesos.loc[activos_hoy] = 1.0 / len(activos_hoy)
                else:
                    pesos = pd.Series(0.0, index=retornos_diarios_bonos.columns)
            
            # Obtenemos los retornos de este día
            retornos_hoy = retornos_diarios_bonos.loc[fecha]
            
            # Calculamos el retorno de la cartera como suma ponderada
            retorno_cartera = (pesos * retornos_hoy).sum(skipna=True)
            
            # Actualizamos los pesos: cada bono crece según su retorno
            # Peso_nuevo = Peso_viejo × (1 + retorno_bono)
            for isin in retornos_diarios_bonos.columns:
                if not pd.isna(retornos_hoy[isin]):
                    pesos[isin] = pesos[isin] * (1 + retornos_hoy[isin])
            
            # Renormalizamos para que sumen 1
            suma_pesos = pesos.sum()
            if suma_pesos > 0:
                pesos = pesos / suma_pesos
            
            valores_cartera.append(retorno_cartera)
        
        # Creamos serie de retornos diarios de la cartera
        retornos_diarios_cartera = pd.Series(valores_cartera, index=retornos_diarios_bonos.index)
        
        # Contamos cuántos retornos válidos tenemos
        retornos_validos = retornos_diarios_cartera.notna().sum()
        print(f"  - Días con retornos válidos: {retornos_validos}/{len(retornos_diarios_cartera)} ({retornos_validos/len(retornos_diarios_cartera)*100:.1f}%)")
        print(f"  - Retorno diario promedio: {retornos_diarios_cartera.mean()*100:.4f}%")
        print(f"  - Volatilidad diaria: {retornos_diarios_cartera.std()*100:.4f}%")
        
        # PASO 5: Acumular geométricamente (Interés Compuesto)
        # -----------------------------------------------------
        # Valor_t = Valor_{t-1} × (1 + R_t)
        # Empezamos con 100€ y cada día lo multiplicamos por (1 + lo que ganamos/perdimos ese día)
        
        valor_cartera = [100.0]  # Empezamos con 100
        for retorno in retornos_diarios_cartera:
            if not pd.isna(retorno):
                valor_cartera.append(valor_cartera[-1] * (1 + retorno))
            else:
                valor_cartera.append(valor_cartera[-1])  # Si no hay dato, mantenemos el valor
        
        # Creamos la serie temporal (sin el primer valor duplicado)
        serie_cartera = pd.Series(valor_cartera[1:], index=retornos_diarios_cartera.index)
        
        # PASO 6: Obtener serie del Benchmark para comparar
        # --------------------------------------------------
        # Extraemos la serie del índice de referencia del mismo período
        # Sacamos los datos del "mercado general" para comparar
        
        df_periodo_benchmark = self.df_indices_futuros.loc[
            (self.df_indices_futuros.index >= fecha_inicio) & 
            (self.df_indices_futuros.index <= fecha_fin)
        ].copy()
        
        if len(df_periodo_benchmark) > 0 and 'Benchmark' in df_periodo_benchmark.columns:
            benchmark_inicial = df_periodo_benchmark['Benchmark'].iloc[0]
            serie_benchmark = (df_periodo_benchmark['Benchmark'] / benchmark_inicial) * 100
        else:
            print("⚠ Advertencia: No hay datos de benchmark disponibles")
            serie_benchmark = pd.Series([100] * len(serie_cartera), index=serie_cartera.index)
        
        # PASO 7: Calcular métricas de performance
        # -----------------------------------------
        # Calculamos ratios de Sharpe, Information Ratio y Tracking Error
        # Calculamos números que nos dicen qué tan bien lo hicimos vs el mercado
        
        # Retornos del benchmark
        retornos_benchmark = serie_benchmark.pct_change().dropna()
        
        # Alineamos las series temporalmente
        fechas_comunes = serie_cartera.index.intersection(serie_benchmark.index)
        if len(fechas_comunes) == 0:
            print("⚠ Advertencia: No hay fechas comunes entre cartera y benchmark")
            fechas_comunes = serie_cartera.index
        
        serie_cartera_aligned = serie_cartera.loc[fechas_comunes]
        serie_benchmark_aligned = serie_benchmark.loc[fechas_comunes]
        
        retornos_cartera_aligned = serie_cartera_aligned.pct_change().dropna()
        retornos_benchmark_aligned = serie_benchmark_aligned.pct_change().dropna()
        
        # Tracking Error
        excess_returns = retornos_cartera_aligned - retornos_benchmark_aligned
        tracking_error = excess_returns.std() * np.sqrt(252)  # Anualizado
        
        # Sharpe Ratio (asumiendo rf=0)
        sharpe_ratio = (retornos_cartera_aligned.mean() / retornos_cartera_aligned.std()) * np.sqrt(252) if retornos_cartera_aligned.std() > 0 else 0
        
        # Information Ratio
        information_ratio = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252) if excess_returns.std() > 0 else 0
        
        # Retorno total (%)
        retorno_total_cartera = ((serie_cartera.iloc[-1] / 100) - 1) * 100
        retorno_total_benchmark = ((serie_benchmark_aligned.iloc[-1] / 100) - 1) * 100
        
        print(f"\n✓ Backtest completado (Método Directo):")
        print(f"  - Retorno cartera: {retorno_total_cartera:.2f}%")
        print(f"  - Retorno benchmark: {retorno_total_benchmark:.2f}%")
        print(f"  - Alpha generado: {retorno_total_cartera - retorno_total_benchmark:.2f}%")
        
        # Resultado final
        resultado = {
            'serie_retornos_cartera': serie_cartera,
            'serie_retornos_benchmark': serie_benchmark_aligned,
            'metricas': {
                'Retorno_Total_Cartera (%)': retorno_total_cartera,
                'Retorno_Total_Benchmark (%)': retorno_total_benchmark,
                'Alpha (%)': retorno_total_cartera - retorno_total_benchmark,
                'Tracking_Error (% anual)': tracking_error * 100,
                'Sharpe_Ratio': sharpe_ratio,
                'Information_Ratio': information_ratio,
                'Dias_Trading': len(serie_cartera),
                'Volatilidad_Anual (%)': retornos_cartera_aligned.std() * np.sqrt(252) * 100
            }
        }
        
        return resultado
    
    def backtest_cartera_custom_weights(self, cartera, fecha_inicio, fecha_fin, df_precios_historicos, frecuencia_rebalanceo='M'):
        """
        PARTE 6 (BACKTEST): Backtest respetando pesos personalizados de la columna 'Peso'.
        
        ¿Qué hace este método?
        -----------------------
        Simula el rendimiento histórico de una cartera optimizada RESPETANDO los pesos
        específicos de cada bono. Cada mes rebalancea a los pesos originales.
        
        Diferencia vs backtest_cartera_vs_benchmark:
        ---------------------------------------------
        - Anterior: Todos los bonos tienen peso 1/N (equiponderado)
        - Este: Cada bono tiene su peso óptimo (ej: Bono A=8%, Bono B=5%)
        
        Parámetros
        ----------
        cartera : DataFrame con columna 'Peso'
        fecha_inicio, fecha_fin : datetime
        df_precios_historicos : DataFrame con precios
        frecuencia_rebalanceo : str ('M' = mensual)
        
        Retorna
        -------
        dict con serie_retornos_cartera, serie_retornos_benchmark, metricas
        """
        
        print("\n✓ Iniciando backtest con PESOS PERSONALIZADOS...")
        
        # Validar que existe columna 'Peso'
        if 'Peso' not in cartera.columns:
            print("⚠ ERROR: La cartera no tiene columna 'Peso'")
            return None
        
        # Verificar que pesos suman ~1.0
        suma_pesos = cartera['Peso'].sum()
        if not np.isclose(suma_pesos, 1.0, atol=0.01):
            cartera = cartera.copy()
            cartera['Peso'] = cartera['Peso'] / suma_pesos
            print(f"  → Pesos normalizados (sumaban {suma_pesos:.4f})")
        
        # Extraer ISINs y filtrar precios
        isins_cartera = cartera['ISIN'].tolist()
        isins_disponibles = [isin for isin in isins_cartera if isin in df_precios_historicos.columns]
        precios_cartera = df_precios_historicos[isins_disponibles].copy()
        
        print(f"  - ISINs en cartera: {len(isins_cartera)}")
        print(f"  - ISINs con históricos: {len(isins_disponibles)}")
        
        # Filtrar período
        precios_cartera = precios_cartera.loc[
            (precios_cartera.index >= fecha_inicio) & 
            (precios_cartera.index <= fecha_fin)
        ]
        
        if len(precios_cartera) == 0:
            print(f"⚠ No hay datos para el período")
            return None
        
        print(f"  - Período: {precios_cartera.index.min().strftime('%d/%m/%Y')} a {precios_cartera.index.max().strftime('%d/%m/%Y')}")
        
        # Diccionario de pesos objetivo
        pesos_objetivo = {fila['ISIN']: fila['Peso'] for _, fila in cartera.iterrows()}
        
        # Cupones
        cupones = {}
        for _, fila in cartera.iterrows():
            if 'Coupon' in fila and not pd.isna(fila['Coupon']):
                cupones[fila['ISIN']] = fila['Coupon'] * 100
            else:
                cupones[fila['ISIN']] = 0.0
        
        print(f"  - Cupón promedio: {np.mean(list(cupones.values())):.2f}%")
        
        # Forward fill
        precios_cartera = precios_cartera.ffill()
        
        # Calcular retornos diarios (Total Return)
        retornos_diarios_bonos = pd.DataFrame(index=precios_cartera.index[1:], columns=precios_cartera.columns)
        
        for i in range(1, len(precios_cartera)):
            fecha_actual = precios_cartera.index[i]
            fecha_anterior = precios_cartera.index[i-1]
            dias = (fecha_actual - fecha_anterior).days
            
            for isin in precios_cartera.columns:
                p_ant = precios_cartera.iloc[i-1][isin]
                p_act = precios_cartera.iloc[i][isin]
                
                if pd.isna(p_ant) or pd.isna(p_act) or p_ant <= 0:
                    retornos_diarios_bonos.loc[fecha_actual, isin] = np.nan
                    continue
                
                ret_precio = (p_act - p_ant) / p_ant
                ret_cupon = (cupones.get(isin, 0) / 100 / 365) * dias
                retornos_diarios_bonos.loc[fecha_actual, isin] = ret_precio + ret_cupon
        
        retornos_diarios_bonos = retornos_diarios_bonos.apply(pd.to_numeric, errors='coerce')
        
        # Backtest con pesos personalizados
        pesos = pd.Series(0.0, index=retornos_diarios_bonos.columns)
        for isin in retornos_diarios_bonos.columns:
            if isin in pesos_objetivo:
                pesos[isin] = pesos_objetivo[isin]
        
        if pesos.sum() > 0:
            pesos = pesos / pesos.sum()
        
        valores_cartera = []
        
        for fecha in retornos_diarios_bonos.index:
            # Rebalanceo mensual
            if (frecuencia_rebalanceo == 'M' and fecha.day == 1) or (pesos.sum() == 0):
                precios_hoy = precios_cartera.loc[fecha]
                activos_hoy = precios_hoy[~precios_hoy.isna()].index.tolist()
                
                if len(activos_hoy) > 0:
                    pesos = pd.Series(0.0, index=retornos_diarios_bonos.columns)
                    for isin in activos_hoy:
                        if isin in pesos_objetivo:
                            pesos[isin] = pesos_objetivo[isin]
                    
                    if pesos.sum() > 0:
                        pesos = pesos / pesos.sum()
            
            retornos_hoy = retornos_diarios_bonos.loc[fecha]
            retorno_cartera = (pesos * retornos_hoy).sum(skipna=True)
            
            # Actualizar pesos
            for isin in retornos_diarios_bonos.columns:
                if not pd.isna(retornos_hoy[isin]):
                    pesos[isin] = pesos[isin] * (1 + retornos_hoy[isin])
            
            if pesos.sum() > 0:
                pesos = pesos / pesos.sum()
            
            valores_cartera.append(retorno_cartera)
        
        retornos_diarios_cartera = pd.Series(valores_cartera, index=retornos_diarios_bonos.index)
        
        print(f"  - Retorno diario promedio: {retornos_diarios_cartera.mean()*100:.4f}%")
        print(f"  - Volatilidad diaria: {retornos_diarios_cartera.std()*100:.4f}%")
        
        # Acumular geométricamente
        valor_cartera = [100.0]
        for ret in retornos_diarios_cartera:
            if not pd.isna(ret):
                valor_cartera.append(valor_cartera[-1] * (1 + ret))
            else:
                valor_cartera.append(valor_cartera[-1])
        
        serie_cartera = pd.Series(valor_cartera[1:], index=retornos_diarios_cartera.index)
        
        # Benchmark
        df_periodo_benchmark = self.df_indices_futuros.loc[
            (self.df_indices_futuros.index >= fecha_inicio) & 
            (self.df_indices_futuros.index <= fecha_fin)
        ].copy()
        
        if len(df_periodo_benchmark) > 0 and 'Benchmark' in df_periodo_benchmark.columns:
            benchmark_inicial = df_periodo_benchmark['Benchmark'].iloc[0]
            serie_benchmark = (df_periodo_benchmark['Benchmark'] / benchmark_inicial) * 100
        else:
            serie_benchmark = pd.Series([100] * len(serie_cartera), index=serie_cartera.index)
        
        # Métricas
        fechas_comunes = serie_cartera.index.intersection(serie_benchmark.index)
        serie_cartera_aligned = serie_cartera.loc[fechas_comunes]
        serie_benchmark_aligned = serie_benchmark.loc[fechas_comunes]
        
        retornos_cartera_aligned = serie_cartera_aligned.pct_change().dropna()
        retornos_benchmark_aligned = serie_benchmark_aligned.pct_change().dropna()
        
        excess_returns = retornos_cartera_aligned - retornos_benchmark_aligned
        tracking_error = excess_returns.std() * np.sqrt(252)
        sharpe_ratio = (retornos_cartera_aligned.mean() / retornos_cartera_aligned.std()) * np.sqrt(252) if retornos_cartera_aligned.std() > 0 else 0
        information_ratio = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252) if excess_returns.std() > 0 else 0
        
        retorno_total_cartera = ((serie_cartera.iloc[-1] / 100) - 1) * 100
        retorno_total_benchmark = ((serie_benchmark_aligned.iloc[-1] / 100) - 1) * 100
        
        print(f"\n✓ Backtest completado:")
        print(f"  - Retorno cartera: {retorno_total_cartera:.2f}%")
        print(f"  - Retorno benchmark: {retorno_total_benchmark:.2f}%")
        print(f"  - Alpha: {retorno_total_cartera - retorno_total_benchmark:.2f}%")
        
        return {
            'serie_retornos_cartera': serie_cartera,
            'serie_retornos_benchmark': serie_benchmark_aligned,
            'metricas': {
                'Retorno_Total_Cartera (%)': retorno_total_cartera,
                'Retorno_Total_Benchmark (%)': retorno_total_benchmark,
                'Alpha (%)': retorno_total_cartera - retorno_total_benchmark,
                'Tracking_Error (% anual)': tracking_error * 100,
                'Sharpe_Ratio': sharpe_ratio,
                'Information_Ratio': information_ratio,
                'Dias_Trading': len(serie_cartera),
                'Volatilidad_Anual (%)': retornos_cartera_aligned.std() * np.sqrt(252) * 100
            }
        }
    
    # =========================================================================
    # PARTE 6: CARTERA RESTRINGIDA (SCREENING)
    # =========================================================================
    
    def construir_cartera_restringida(self, capital_inicial=1000000):
        """
        PARTE 6: Construye una cartera óptima con OPTIMIZACIÓN MATEMÁTICA.
        
        Enunciado del ejercicio:
        ------------------------
        Construir una cartera de MÁXIMO 20 bonos corporativos maximizando la
        rentabilidad total con las siguientes restricciones:
        
        1. Duración de la CARTERA ≤ 3 años (no de bonos individuales)
        2. Exposición a HY ≤ 10% de la cartera
        3. No invertir en deuda subordinada
        4. Tamaño de emisión > 500 millones
        5. Máximo 10% en una misma emisión
        6. Máximo 15% de concentración en un mismo emisor
        
        Estrategia de optimización:
        ---------------------------
        Usamos PROGRAMACIÓN LINEAL (scipy.optimize.linprog) para encontrar
        la combinación óptima de pesos que maximiza el Z-Spread promedio
        respetando todas las restricciones simultáneamente.
        
        ¿Por qué programación lineal?
        -----------------------------
        - Programación lineal: GARANTIZA la mejor solución matemáticamente posible
        
        Parámetros
        ----------
        capital_inicial : float
            Capital total a invertir (default: 1 millón EUR)
        
        Retorna
        -------
        pandas.DataFrame
            Cartera óptima (máximo 20 bonos con pesos optimizados)
        """
        
        print("\n" + "="*80)
        print("PARTE 6: CONSTRUYENDO CARTERA OPTIMIZADA (PROGRAMACIÓN LINEAL)")
        print("="*80)
        
        # PASO 1: Pre-screening del enunciado
        # ====================================================
        # Aplicamos las restricciones binarias (sí/no) antes de optimizar:
        # - No deuda subordinada
        # - Tamaño > 500M
        
        df_trabajo = self.df_completo.copy()
        print(f"\n✓ Universo inicial: {len(df_trabajo)} bonos")
        
        # FILTRO 1: No Subordinados
        # --------------------------
        # Eliminamos deuda subordinada, AT1, CoCos (prelación inferior)
        # Estos bonos pierden primero si la empresa tiene problemas
        columna_seniority = None
        for col in ['Seniority', 'Security Type', 'Type']:
            if col in df_trabajo.columns:
                columna_seniority = col
                break
        
        if columna_seniority:
            patrones_sub = (
                'Subordinated|Junior|Tier 2|Tier2|Lower|'
                'AT1|Additional\\s*Tier\\s*1|Tier\\s*1|'
                'CoCo|Coco|RT1'
            )
            df_trabajo = df_trabajo[
                ~df_trabajo[columna_seniority].astype(str).str.contains(
                    patrones_sub,
                    case=False,
                    na=False
                )
            ]
            print(f"✓ Filtro: No Subordinados → {len(df_trabajo)} bonos")
        
        # FILTRO 2: Tamaño > 500M (liquidez)
        # -----------------------------------
        # Nos quedamos solo con emisiones grandes que tienen liquidez
        # Los bonos pequeños tienen horquillas (bid-ask) muy anchas
        columna_size = None
        for col in ['Amount Outstanding', 'Issue Size', 'Outstanding Amount']:
            if col in df_trabajo.columns:
                columna_size = col
                break
        
        if columna_size:
            df_trabajo[columna_size] = pd.to_numeric(df_trabajo[columna_size], errors='coerce')
            df_trabajo = df_trabajo[df_trabajo[columna_size] > 500]
            print(f"✓ Filtro: Tamaño > 500M → {len(df_trabajo)} bonos")
        
        # Eliminamos bonos sin métricas necesarias para el optimizador
        df_trabajo = df_trabajo.dropna(subset=['Z_Spread', 'Duracion_Modificada'])
        print(f"✓ Bonos con métricas completas: {len(df_trabajo)}")
        
        if len(df_trabajo) == 0:
            print("⚠ No hay bonos después de los filtros")
            return pd.DataFrame()
        
        # PASO 2: CLASIFICACIÓN DE RATINGS (IG vs HY)
        # ============================================
        # Necesitamos saber qué bonos son HY para la restricción de HY ≤ 10%
        
        def clasificar_rating(rating):
            """Clasifica un rating como Investment Grade (IG) o High Yield (HY)."""
            if pd.isna(rating):
                return 'Unknown'
            rating_str = str(rating).upper().strip()
            # Investment Grade: AAA, AA, A, BBB
            if any(x in rating_str for x in ['AAA', 'AA', 'A+']):
                return 'IG'
            if rating_str.startswith('A') and not rating_str.startswith('A-'):
                return 'IG'
            if 'BBB' in rating_str:
                return 'IG'
            # High Yield: BB o inferior
            if any(x in rating_str for x in ['BB', 'B', 'CCC', 'CC', 'C', 'D']):
                return 'HY'
            return 'Unknown'
        
        columna_rating = None
        for col in ['Composite Rating', 'Rating', 'S&P Rating', 'Moody Rating']:
            if col in df_trabajo.columns:
                columna_rating = col
                break
        
        if columna_rating:
            df_trabajo['Clasificacion_Rating'] = df_trabajo[columna_rating].apply(clasificar_rating)
        else:
            df_trabajo['Clasificacion_Rating'] = 'IG'  # Asumimos IG si no hay rating
        
        # RECLASIFICAR bonos "Unknown" basándose en Z-Spread
        # ---------------------------------------------------
        # Los bonos sin rating (NR) se pueden clasificar analizando su spread:
        # - Z-Spread < 200 pb → Riesgo equivalente a BBB- o mejor (IG)
        # - Z-Spread >= 200 pb → Riesgo equivalente a BB+ o peor (HY)
        # Esto es CRÍTICO para que el optimizador aplique correctamente la restricción de HY <= 10%
        mask_unknown = df_trabajo['Clasificacion_Rating'] == 'Unknown'
        df_trabajo.loc[mask_unknown & (df_trabajo['Z_Spread'] < 200), 'Clasificacion_Rating'] = 'IG'
        df_trabajo.loc[mask_unknown & (df_trabajo['Z_Spread'] >= 200), 'Clasificacion_Rating'] = 'HY'
        
        n_hy = (df_trabajo['Clasificacion_Rating'] == 'HY').sum()
        n_ig = (df_trabajo['Clasificacion_Rating'] == 'IG').sum()
        n_unknown = (df_trabajo['Clasificacion_Rating'] == 'Unknown').sum()
        print(f"✓ Clasificación (con NR reclasificados por Z-Spread): {n_ig} IG, {n_hy} HY, {n_unknown} sin clasificar")
        
        # PASO 3: PRE-SELECCIÓN INTELIGENTE (Hybrid Pool)
        # ================================================
        # Estrategia dual para garantizar viabilidad matemática:
        # 1. TOP bonos por YTC (maximizar objetivo)
        # 2. TOP bonos por Z-Spread CON Duración < 3 (garantizar bonos cortos)
        # Esto asegura que el optimizador siempre tenga "ingredientes" para cumplir Duración ≤ 3
        
        # Grupo 1: Mejores por rentabilidad (YTC)
        top_ytc = df_trabajo.nlargest(60, 'YTC')
        
        # Grupo 2: Mejores por spread CON duración corta (garantía de feasibility)
        bonos_cortos = df_trabajo[df_trabajo['Duracion_Modificada'] < 3.0]
        if len(bonos_cortos) > 0:
            top_cortos = bonos_cortos.nlargest(60, 'Z_Spread')
            print(f"✓ Bonos cortos disponibles (Duración < 3): {len(bonos_cortos)}")
        else:
            print(f"⚠ No hay bonos con Duración < 3. Tomando los más cortos disponibles.")
            top_cortos = df_trabajo.nsmallest(60, 'Duracion_Modificada')
        
        # Unir ambos grupos y eliminar duplicados
        df_trabajo = pd.concat([top_ytc, top_cortos]).drop_duplicates(subset=['ISIN'])
        
        print(f"✓ Pre-selección híbrida:")
        print(f"  - Pool A: 60 bonos por mayor YTC")
        print(f"  - Pool B: 60 bonos por mayor Z-Spread con Duración < 3")
        print(f"  - Pool final: {len(df_trabajo)} candidatos (tras eliminar duplicados)")
        
        # PASO 4: BUCLE DE OPTIMIZACIÓN ITERATIVO CON CARDINALIDAD
        # =========================================================
        # Estrategia: Optimizar iterativamente eliminando el bono de menor peso
        # hasta que tengamos <= 20 bonos (cardinalidad del enunciado)
        # Esto garantiza feasibility matemática sin romper restricciones
        
        df_pool = df_trabajo.copy()  # Pool dinámico de candidatos
        iteracion = 0
        MAX_ITERACIONES = 50  # Límite de seguridad
        cartera_optima_encontrada = False
        
        print(f"\n🔧 Iniciando optimización iterativa...")
        
        while iteracion < MAX_ITERACIONES:
            iteracion += 1
            
            # Preparar datos del pool actual
            n = len(df_pool)
            
            if n == 0:
                print(f"⚠ Iteración {iteracion}: Pool vacío")
                break
            
            # Vectores para el optimizador
            ytc_values = df_pool['YTC'].values  # Objetivo: maximizar YTC
            duraciones = df_pool['Duracion_Modificada'].values
            es_hy = (df_pool['Clasificacion_Rating'] == 'HY').values.astype(float)
            
            # Emisores
            columna_emisor = None
            for col in ['Issuer Name', 'Issuer', 'Name', 'Description']:
                if col in df_pool.columns:
                    columna_emisor = col
                    break
            
            if columna_emisor:
                emisores = df_pool[columna_emisor].astype(str).values
            else:
                emisores = np.array([f"EMI_{i}" for i in range(n)])
            
            emisores_unicos = np.unique(emisores)
            
            # Construir restricciones
            A_ub = []
            b_ub = []
            
            # RESTRICCIÓN 1: Duración de CARTERA ≤ 3 años
            A_ub.append(duraciones)
            b_ub.append(3.0)
            
            # RESTRICCIÓN 2: HY ≤ 10%
            A_ub.append(es_hy)
            b_ub.append(0.10)
            
            # RESTRICCIÓN 3: Concentración por emisor ≤ 15%
            for emisor in emisores_unicos:
                es_de_emisor = (emisores == emisor).astype(float)
                A_ub.append(es_de_emisor)
                b_ub.append(0.15)
            
            A_ub = np.array(A_ub)
            b_ub = np.array(b_ub)
            
            # Restricción de igualdad: suma = 1.0
            A_eq = np.array([np.ones(n)])
            b_eq = np.array([1.0])
            
            # Bounds individuales: 0 ≤ wi ≤ 10%
            bounds = [(0, 0.10) for _ in range(n)]
            
            # Función objetivo: maximizar YTC
            c = -ytc_values
            
            # RESOLVER
            resultado = linprog(
                c=c,
                A_ub=A_ub,
                b_ub=b_ub,
                A_eq=A_eq,
                b_eq=b_eq,
                bounds=bounds,
                method='highs',
                options={'disp': False}
            )
            
            if not resultado.success:
                print(f"⚠ Iteración {iteracion}: Optimización falló ({resultado.message})")
                break
            
            # Identificar bonos con peso significativo (> 0.1%)
            pesos_optimos = resultado.x
            mask_significativos = pesos_optimos > 0.001
            num_activos_seleccionados = mask_significativos.sum()
            
            # CHECK CARDINALIDAD
            if num_activos_seleccionados <= 20:
                # ¡ÉXITO! Tenemos <= 20 bonos
                print(f"✓ Iteración {iteracion}: Solución encontrada con {num_activos_seleccionados} bonos")
                
                # Guardar solución
                indices_finales = np.where(mask_significativos)[0]
                pesos_finales = pesos_optimos[indices_finales]
                pesos_finales = pesos_finales / pesos_finales.sum()  # Renormalizar
                df_cartera_final = df_pool.iloc[indices_finales].copy()
                cartera_optima_encontrada = True
                break
            else:
                # Tenemos > 20 bonos → Eliminar el de menor peso y repetir
                indices_activos = np.where(mask_significativos)[0]
                pesos_activos = pesos_optimos[mask_significativos]
                idx_menor_peso = indices_activos[np.argmin(pesos_activos)]
                
                print(f"  Iteración {iteracion}: {num_activos_seleccionados} bonos > 20 → Eliminando bono de menor peso")
                
                # Eliminar del pool y repetir
                df_pool = df_pool.drop(df_pool.index[idx_menor_peso]).reset_index(drop=True)
        
        # Verificar que encontramos solución
        if not cartera_optima_encontrada:
            print(f"⚠ No se encontró solución tras {iteracion} iteraciones")
            return pd.DataFrame()
        
        # PASO 5: CONSTRUIR CARTERA FINAL
        # ================================
        cartera = pd.DataFrame({
            'ISIN': df_cartera_final['ISIN'].values,
            'Nombre': df_cartera_final[columna_emisor].values if columna_emisor else ['N/A'] * len(df_cartera_final),
            'Peso': pesos_finales,
            'Nominal_Invertido': pesos_finales * capital_inicial,
            'YTC': df_cartera_final['YTC'].values,
            'Z_Spread': df_cartera_final['Z_Spread'].values,
            'Duracion_Modificada': df_cartera_final['Duracion_Modificada'].values,
            'Rating': df_cartera_final[columna_rating].values if columna_rating and columna_rating in df_cartera_final.columns else ['N/A'] * len(df_cartera_final)
        })
        
        # Añadir métricas adicionales
        if 'DV01' in df_cartera_final.columns:
            cartera['DV01'] = df_cartera_final['DV01'].values
        if 'CS01' in df_cartera_final.columns:
            cartera['CS01'] = df_cartera_final['CS01'].values
        if 'Duracion_Efectiva' in df_cartera_final.columns:
            cartera['Duracion_Efectiva'] = df_cartera_final['Duracion_Efectiva'].values
        if 'Clasificacion_Rating' in df_cartera_final.columns:
            cartera['Clasificacion_Rating'] = df_cartera_final['Clasificacion_Rating'].values
        if 'Coupon' in df_cartera_final.columns:
            cartera['Coupon'] = df_cartera_final['Coupon'].values
        
        # PASO 6: MÉTRICAS DE LA CARTERA
        # ================================
        # Calcular la RENTABILIDAD (YTC promedio ponderado) - ESTO ES LO QUE PIDE EL ENUNCIADO
        ytc_cartera = (cartera['Peso'] * cartera['YTC'].values).sum()
        duracion_cartera = (cartera['Peso'] * cartera['Duracion_Modificada']).sum()
        peso_hy = (cartera['Peso'].values * (cartera['Clasificacion_Rating'] == 'HY').values.astype(float)).sum()
        
        print(f"\n✓ CARTERA OPTIMIZADA:")
        print(f"  - Número de bonos: {len(cartera)} (máximo: 20)")
        print(f"\n  🎯 RENTABILIDAD DE LA CARTERA (YTC promedio): {ytc_cartera:.2f}% anual")
        print(f"\n  Restricciones cumplidas:")
        print(f"  - Duración de cartera: {duracion_cartera:.2f} años (límite: 3.0)")
        print(f"  - Peso HY: {peso_hy*100:.2f}% (límite: 10%)")
        print(f"  - Peso máximo individual: {cartera['Peso'].max()*100:.2f}% (límite: 10%)")
        
        if columna_emisor:
            max_emisor = cartera.groupby('Nombre')['Peso'].sum().max()
            print(f"  - Máx. por emisor: {max_emisor*100:.2f}% (límite: 15%)")
        
        return cartera
    
    # =========================================================================
    # PARTE 7: COBERTURA DE TIPOS (DURATION HEDGING)
    # =========================================================================
    
    def calcular_cobertura_tipos(self, cartera, fecha_valoracion):
        """
        PARTE 7: Calcula la cobertura de riesgo de tipos de interés con futuros.
        
        Basado en el enunciado del profesor:
        - Cartera: 10.000.000 € (supuesto)
        - Futuros disponibles: Schatz (1.92), BOBL (5.44), BUND (10.00)
        - Tamaño contrato: 100.000 €
        
        Parámetros
        ----------
        cartera : pandas.DataFrame
            Cartera a cubrir
        fecha_valoracion : datetime
            Fecha de valoración
        
        Retorna
        -------
        dict
            Diccionario con el resultado de la cobertura
        """
        
        print("\n" + "="*80)
        print("PARTE 7: COBERTURA DE RIESGO DE TIPOS (DURATION HEDGING)")
        print("="*80)
        print("Basado en supuesto del enunciado: Cartera de 10.000.000 €")
        
        # PASO 1: Calcular duración media de la cartera
        # ------------------------------------------------
        # Promedio ponderado de las duraciones de los bonos
        # Este es el riesgo de tipos que queremos neutralizar
        duracion_media_cartera = (
            (cartera['Duracion_Modificada'] * cartera['Peso']).sum()
            if 'Duracion_Modificada' in cartera.columns
            else 0
        )
        
        print(f"\n✓ Duración media de la cartera: {duracion_media_cartera:.2f} años")
        
        # PASO 2: Datos de futuros (del enunciado del profesor)
        # -------------------------------------------------------
    
        VALOR_CARTERA = 10_000_000  # 10 Millones €
        TAMANO_CONTRATO = 100_000   # 100.000 € por contrato
        
        futuros_info = {
            'Schatz': {'duracion': 1.92, 'nombre': 'Euro-Schatz (2Y)'},
            'BOBL':   {'duracion': 5.44, 'nombre': 'Euro-BOBL (5Y)'},
            'BUND':   {'duracion': 10.00, 'nombre': 'Euro-BUND (10Y)'}
        }
        
        # PASO 3: Seleccionar el futuro óptimo
        # --------------------------------------
        # Elegimos el futuro cuya duración esté más cerca de la nuestra
        # Así nos aseguramos que loa cartera y el futuro se comporten lo más parecido posible
        mejor_futuro = min(
            futuros_info.keys(),
            key=lambda f: abs(futuros_info[f]['duracion'] - duracion_media_cartera)
        )
        
        info_futuro = futuros_info[mejor_futuro]
        
        print(f"\n✓ Futuro seleccionado: {info_futuro['nombre']}")
        print(f"  - Duración: {info_futuro['duracion']} años (dato del enunciado)")
        
        # PASO 4: Calcular sensibilidad de la cartera
        # ---------------------------------------------
        # Sensibilidad = Duración × Valor de la Cartera
        # Mide cuánto pierde la cartera por cada movimiento de tipos
        sensibilidad_cartera = duracion_media_cartera * VALOR_CARTERA
        
        # PASO 5: Calcular número de contratos
        # --------------------------------------
        # Vendemos futuros para neutralizar el riesgo de tipos
        # Si los tipos suben, la cartera pierde pero los futuros ganan (posición corta)
        # Número de contratos = Sensibilidad_Cartera / (Duración_Futuro × Tamaño_Contrato)
        numero_contratos = sensibilidad_cartera / (info_futuro['duracion'] * TAMANO_CONTRATO)
        
        print(f"\n✓ Cálculo de cobertura:")
        print(f"  - Sensibilidad de la cartera: {sensibilidad_cartera:,.0f} € × años")
        print(f"  - Número de contratos a VENDER: {numero_contratos:.2f}")
        print(f"  - Valor nocional: {numero_contratos * TAMANO_CONTRATO:,.0f} €")
        
        # PASO 6: Análisis de efectividad
        # ---------------------------------
        # Basis Risk = diferencia de duraciones
        # Cuanto menor, mejor es el match
        basis_risk = abs(info_futuro['duracion'] - duracion_media_cartera)
        
        print(f"\n✓ Efectividad:")
        print(f"  - Basis Risk: {basis_risk:.2f} años")
        if basis_risk < 0.5:
            print(f"  ✓ Cobertura EXCELENTE (basis risk < 0.5)")
        elif basis_risk < 1.0:
            print(f"  ✓ Cobertura BUENA (basis risk < 1.0)")
        else:
            print(f"  ⚠ Cobertura ACEPTABLE (basis risk >= 1.0)")
        
        resultado = {
            'futuro_seleccionado': mejor_futuro,
            'nombre_futuro': info_futuro['nombre'],
            'duracion_futuro': info_futuro['duracion'],
            'duracion_cartera': duracion_media_cartera,
            'numero_contratos': numero_contratos,
            'valor_cartera': VALOR_CARTERA,
            'sensibilidad_cartera': sensibilidad_cartera,
            'basis_risk': basis_risk
        }
        
        return resultado
    
    # =========================================================================
    # PARTE 8: COBERTURA DE CRÉDITO (CDS HEDGING)
    # =========================================================================
    
    def calcular_cobertura_credito(self, cartera, fecha_valoracion):
        """
        PARTE 8: Calcula la cobertura de riesgo de crédito con CDS (iTraxx).
        
        Basado en el enunciado del profesor:
        - Cartera: 10.000.000 € (supuesto)
        - Sensibilidad CDS: 4.500 € por bp para 10M (dato del enunciado)
        - Índices: iTraxx Main (IG) o iTraxx Crossover (HY)
        
        Parámetros
        ----------
        cartera : pandas.DataFrame
            Cartera a cubrir
        fecha_valoracion : datetime
            Fecha de valoración
        
        Retorna
        -------
        dict
            Diccionario con el resultado de la cobertura de crédito
        """
        
        print("\n" + "="*80)
        print("PARTE 8: COBERTURA DE RIESGO DE CRÉDITO (CDS HEDGING)")
        print("="*80)
        print("Basado en supuesto del enunciado: Cartera de 10.000.000 €")
        print("Sensibilidad CDS (dato del profesor): 4.500 €/bp para 10M")
        
        # PASO 1: Verificar que tenemos CS01
        # ------------------------------------
        if 'CS01' not in cartera.columns:
            print("\n❌ ERROR: La cartera no tiene la columna CS01")
            print("   Verifica que las métricas de Parte 4 se calcularon correctamente")
            return None
        
        # PASO 2: Calcular CS01 total de la cartera
        # -------------------------------------------
        # Sumamos el CS01 de todos los bonos
        # Este es el riesgo de crédito que queremos neutralizar
        # IMPORTANTE: El CS01 calculado por bono está expresado por 100 de nominal.
        # Para pasarlo a euros, monetizamos por el nominal invertido en cada bono.
        if 'Nominal_Invertido' in cartera.columns:
            cs01_total_cartera = (cartera['CS01'] * (cartera['Nominal_Invertido'] / 100.0)).sum()
        else:
            cs01_total_cartera = cartera['CS01'].sum()
        
        # Calcular el valor nominal real de la cartera
        valor_nominal_real = cartera['Nominal_Invertido'].sum() if 'Nominal_Invertido' in cartera.columns else 1_000_000
        
        print(f"\n✓ CS01 total de la cartera real: {cs01_total_cartera:.2f} €/bp")
        print(f"✓ Valor nominal real de la cartera: {valor_nominal_real:,.0f} €")
        
        # PASO 3: Ajustar CS01 a la escala de 10M
        # -----------------------------------------
        # Como el enunciado trabaja con 10M, escalamos nuestro CS01 real
        # CS01_Ajustado = (CS01_Real / Nominal_Real) × 10.000.000
        VALOR_CARTERA_SUPUESTO = 10_000_000
        cs01_ajustado = (cs01_total_cartera / valor_nominal_real) * VALOR_CARTERA_SUPUESTO
        
        print(f"✓ CS01 ajustado a 10M€: {cs01_ajustado:.2f} €/bp")
        
        # PASO 4: Seleccionar el índice CDS
        # -----------------------------------
        # Si más del 50% (por PESO) es Investment Grade → iTraxx Main
        # Si no → iTraxx Crossover
        # IMPORTANTE: Usamos PESO, no número de bonos
        # NOTA: La clasificación ya viene correcta desde la Parte 6 (NR reclasificados por Z-Spread)
        if 'Clasificacion_Rating' in cartera.columns and 'Peso' in cartera.columns:
            peso_ig = (cartera['Peso'] * (cartera['Clasificacion_Rating'] == 'IG').astype(float)).sum()
            peso_hy = (cartera['Peso'] * (cartera['Clasificacion_Rating'] == 'HY').astype(float)).sum()
            peso_unknown = (cartera['Peso'] * (cartera['Clasificacion_Rating'] == 'Unknown').astype(float)).sum()
            pct_ig = peso_ig * 100
            pct_hy = peso_hy * 100
            pct_unknown = peso_unknown * 100
        else:
            pct_ig = 80  # Asumimos mayormente IG si no hay info
            pct_hy = 10
            pct_unknown = 10
        
        print(f"\n✓ Composición de la cartera (por peso):")
        print(f"  - Investment Grade: {pct_ig:.1f}%")
        print(f"  - High Yield: {pct_hy:.1f}%")
        if pct_unknown > 0:
            print(f"  - Sin clasificar: {pct_unknown:.1f}%")
        
        # Selección del índice
        if pct_ig > 50:
            nombre_indice = 'iTraxx Europe Main (Investment Grade)'
            CS01_INDICE = 4500.0  # Dato del enunciado del profesor
        else:
            nombre_indice = 'iTraxx Crossover (High Yield)'
            CS01_INDICE = 6500.0  # Valor típico para Crossover
        
        print(f"\n✓ Índice CDS seleccionado: {nombre_indice}")
        print(f"  - CS01 por 10M: {CS01_INDICE:,.0f} €/bp (dato del enunciado)")
        
        # PASO 5: Calcular nominal de protección a comprar
        # ---------------------------------------------------
        # Compramos CDS para neutralizar el riesgo de crédito
        # Si los spreads suben, la cartera pierde pero el CDS gana
        # Nominal = (CS01_Ajustado / CS01_Indice) × 10M
        nominal_proteccion = (cs01_ajustado / CS01_INDICE) * VALOR_CARTERA_SUPUESTO
        
        print(f"\n✓ Cálculo de cobertura:")
        print(f"  - Nominal de CDS a COMPRAR: {nominal_proteccion:,.0f} €")
        
        # PASO 6: Análisis de efectividad
        # ---------------------------------
        # Verificamos que la cobertura es efectiva
        # El CS01 del CDS comprado debe igualar al CS01 de la cartera
        cs01_cobertura = (nominal_proteccion / VALOR_CARTERA_SUPUESTO) * CS01_INDICE
        hedge_ratio = min(1.0, cs01_cobertura / cs01_ajustado) if cs01_ajustado > 0 else 0
        
        print(f"\n✓ Efectividad de la cobertura:")
        print(f"  - Hedge Ratio: {hedge_ratio*100:.2f}% (100% = cobertura perfecta)")
        print(f"  - CS01 cubierto: {cs01_cobertura:.2f} €/bp")
        print(f"  - CS01 residual: {cs01_ajustado - cs01_cobertura:.2f} €/bp")
        
        if hedge_ratio >= 0.95:
            print(f"  ✓ Cobertura EXCELENTE (>95%)")
        elif hedge_ratio >= 0.85:
            print(f"  ✓ Cobertura BUENA (85-95%)")
        else:
            print(f"  ⚠ Cobertura MODERADA (<85%)")
        
        resultado = {
            'nombre_indice': nombre_indice,
            'cs01_total_real': cs01_total_cartera,
            'cs01_ajustado_10M': cs01_ajustado,
            'cs01_indice_per_10M': CS01_INDICE,
            'nominal_proteccion': nominal_proteccion,
            'hedge_ratio': hedge_ratio,
            'cs01_cubierto': cs01_cobertura,
            'cs01_residual': cs01_ajustado - cs01_cobertura
        }
        
        return resultado
    
    # =========================================================================
    # UTILIDADES: GENERACIÓN DE GRÁFICOS
    # =========================================================================
    
    def generar_grafico_backtest(self, resultado_backtest, guardar_como='resultados/backtest_vs_benchmark.png'):
        """
        Genera gráfico del backtest de la cartera vs benchmark.
        """
        if resultado_backtest is None:
            return
        
        plt.figure(figsize=(12, 6))
        
        plt.plot(
            resultado_backtest['serie_retornos_cartera'].index,
            resultado_backtest['serie_retornos_cartera'].values,
            label='Nuestra Cartera',
            linewidth=2,
            color='blue'
        )
        
        plt.plot(
            resultado_backtest['serie_retornos_benchmark'].index,
            resultado_backtest['serie_retornos_benchmark'].values,
            label='Benchmark (Mercado)',
            linewidth=2,
            color='red',
            linestyle='--'
        )
        
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=12)
        plt.title('Backtest: Cartera vs Benchmark', fontsize=14, fontweight='bold')
        plt.xlabel('Fecha', fontsize=12)
        plt.ylabel('Retorno Acumulado (%)', fontsize=12)
        plt.tight_layout()
        
        plt.savefig(guardar_como, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Gráfico guardado: {guardar_como}")
