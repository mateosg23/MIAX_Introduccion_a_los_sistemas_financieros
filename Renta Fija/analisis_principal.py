"""
===============================================================================
ANÁLISIS PRINCIPAL - Práctica de Valoración de Bonos Corporativos
===============================================================================
"""
""" CREAR ENTORNO VIRTUAL E INSTALAR DEPENDENCIAS PARA QUE FUNCIONE"""

import cargador_datos
import valorador_bonos
import gestor_carteras
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import os
import matplotlib
matplotlib.use('Agg')  # Para guardar gráficos sin mostrarlos
import matplotlib.pyplot as plt
warnings.filterwarnings('ignore')

# Configuración de visualización
try:
    plt.style.use('ggplot')  # Estilo profesional sin necesidad de seaborn
except:
    plt.style.use('default')


def main():
    """
    Función principal que ejecuta todo el análisis.
    """
    # Crear carpeta de resultados si no existe
    if not os.path.exists('resultados'):
        os.makedirs('resultados')
    
    print("\n" + "="*80)
    print("ANÁLISIS DE RENTA FIJA - VALORACIÓN DE BONOS CORPORATIVOS".center(80))
    print("="*80)
    print(f"\nFecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("Resultados se guardarán en: resultados/\n")
    
    # =========================================================================
    # PARTE 1: CARGA DE DATOS
    # =========================================================================
    
    # Cargar datos sin que se muestren los mensajes por pantalla
    import sys
    from io import StringIO
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    
    df_universo = cargador_datos.cargar_y_limpiar_universo('data/universo.csv')
    df_curva_estr = cargador_datos.cargar_curva_estr('data/curvaESTR.csv')
    df_indices_futuros = cargador_datos.cargar_indices_y_futuros('data/precios_historicos_varios.csv')
    
    # Cargar TODOS los precios históricos LIMPIOS (una sola vez)
    # Esta función ya limpia ISINs, transpone, y convierte fechas
    df_precios_historicos_completo = cargador_datos.cargar_precios_historicos_completo('data/precios_historicos_universo.csv')
    
    sys.stdout = old_stdout
    
    # =========================================================================
    # EXTRAER PRECIOS DE LA FECHA OBJETIVO (del histórico ya cargado)
    # =========================================================================
    
    print("\n" + "="*80)
    print("EXTRAYENDO PRECIOS DE MERCADO PARA LA FECHA DE VALORACIÓN")
    print("="*80)
    
    # Fecha objetivo: 01/10/2025
    fecha_valoracion = datetime(2025, 10, 1)
    
    # Verificar si la fecha existe en el índice
    if fecha_valoracion in df_precios_historicos_completo.index:
        # Caso ideal: la fecha está en el histórico
        serie_precios = df_precios_historicos_completo.loc[fecha_valoracion]
        print(f"✓ Fecha {fecha_valoracion.strftime('%d/%m/%Y')} encontrada en el histórico")
    else:
        # Plan B: Buscar la fecha más cercana
        print(f"⚠ La fecha {fecha_valoracion.strftime('%d/%m/%Y')} no está disponible")
        print(f"  Fechas disponibles (primeras 5): {df_precios_historicos_completo.index[:5].strftime('%d/%m/%Y').tolist()}")
        print(f"  Fechas disponibles (últimas 5): {df_precios_historicos_completo.index[-5:].strftime('%d/%m/%Y').tolist()}")
        
        # Buscar la fecha más cercana
        idx_fecha_cercana = df_precios_historicos_completo.index.get_indexer([fecha_valoracion], method='nearest')[0]
        fecha_cercana = df_precios_historicos_completo.index[idx_fecha_cercana]
        serie_precios = df_precios_historicos_completo.loc[fecha_cercana]
        
        dias_distancia = abs((fecha_cercana - fecha_valoracion).days)
        print(f"  ✓ Usando fecha más cercana: {fecha_cercana.strftime('%d/%m/%Y')} (distancia: {dias_distancia} días)")
        
        # Actualizamos fecha_valoracion para que coincida con los precios reales
        fecha_valoracion = fecha_cercana
    
    # Convertir la Serie a DataFrame con formato esperado
    df_precios_mercado = pd.DataFrame({
        'ISIN': serie_precios.index,
        'Precio_Mercado': pd.to_numeric(serie_precios.values, errors='coerce')
    })
    
    # Eliminar bonos sin precio (NaN)
    df_precios_mercado = df_precios_mercado.dropna(subset=['Precio_Mercado'])
    
    print(f"\n✓ Precios extraídos para {fecha_valoracion.strftime('%d/%m/%Y')}")
    print(f"✓ Bonos con precio disponible: {len(df_precios_mercado)}")
    print(f"  - Precio mínimo: {df_precios_mercado['Precio_Mercado'].min():.2f}")
    print(f"  - Precio máximo: {df_precios_mercado['Precio_Mercado'].max():.2f}")
    print(f"  - Precio promedio: {df_precios_mercado['Precio_Mercado'].mean():.2f}")
    print("="*80)
    
    # Unir datos
    df_completo = df_universo.merge(df_precios_mercado, on='ISIN', how='inner')
    df_completo = df_completo.dropna(subset=['Coupon', 'Coupon Frequency', 'Fecha_Vencimiento_Efectiva', 'Precio_Mercado'])
    df_analisis = df_completo.copy()
    
    # NOTA: fecha_valoracion ya fue definida al extraer los precios del histórico
    # Corresponde a 01/10/2025 (o la fecha más cercana disponible)
    
    print(f"\n✓ Datos cargados: {len(df_analisis)} bonos")
    print(f"✓ Fecha de valoración confirmada: {fecha_valoracion.strftime('%d/%m/%Y')}\n")
    
    # =========================================================================
    # PARTE 1.1: ANÁLISIS VISUAL DEL UNIVERSO
    # =========================================================================
    
    print("="*80)
    print("PARTE 1: ANÁLISIS VISUAL DEL UNIVERSO".center(80))
    print("="*80 + "\n")
    
    # Realizamos un análisis exploratorio del universo de bonos
    
    # Estadísticas básicas
    print("✓ Resumen estadístico del universo:")
    print(f"  - Cupón medio: {df_analisis['Coupon'].mean()*100:.2f}%")
    print(f"  - Cupón mínimo: {df_analisis['Coupon'].min()*100:.2f}%")
    print(f"  - Cupón máximo: {df_analisis['Coupon'].max()*100:.2f}%")
    print(f"  - Precio medio de mercado: {df_analisis['Precio_Mercado'].mean():.2f}")
    
    # Gráfico 1: Distribución de Ratings
    # -----------------------------------
    # Visualización de la calidad crediticia del universo (IG vs HY split)
    
    
    columna_rating = None
    for col in ['Composite Rating', 'Rating', 'S&P Rating', 'Moody Rating']:
        if col in df_analisis.columns:
            columna_rating = col
            break
    
    if columna_rating:
        plt.figure(figsize=(12, 6))
        
        # Contar ratings
        ratings_counts = df_analisis[columna_rating].value_counts().head(15)
        
        # Gráfico de barras
        ax = ratings_counts.plot(kind='bar', color='steelblue', edgecolor='black')
        plt.title('Distribución de Ratings del Universo', fontsize=14, fontweight='bold')
        plt.xlabel('Rating', fontsize=12)
        plt.ylabel('Número de Bonos', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        # Guardar
        plt.savefig('resultados/01_distribucion_ratings.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print("  ✓ Gráfico guardado: 01_distribucion_ratings.png")
    
    # Gráfico 2: Distribución Sectorial
    # -----------------------------------
    #  Análisis de diversificación sectorial del universo
    
    
    columna_sector = None
    for col in ['Ticker', 'Industry Sector', 'Sector']:
        if col in df_analisis.columns:
            columna_sector = col
            break
    
    if columna_sector:
        plt.figure(figsize=(12, 8))
        
        # Top 10 sectores
        sectores_counts = df_analisis[columna_sector].value_counts().head(10)
        
        # Gráfico de pastel
        plt.pie(sectores_counts.values, labels=sectores_counts.index, autopct='%1.1f%%',
                startangle=90, textprops={'fontsize': 10})
        plt.title('Distribución Sectorial del Universo (Top 10)', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        # Guardar
        plt.savefig('resultados/02_distribucion_sectorial.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print("  ✓ Gráfico guardado: 02_distribucion_sectorial.png")
    
    # Gráfico 3: Perfil de Vencimientos
    # ----------------------------------
    #  Análisis de la estructura temporal de vencimientos (concentración de riesgo)
    
    
    if 'Fecha_Vencimiento_Efectiva' in df_analisis.columns:
        # Calculamos años hasta vencimiento
        años_hasta_vencimiento = (df_analisis['Fecha_Vencimiento_Efectiva'] - fecha_valoracion).dt.days / 365.0
        
        plt.figure(figsize=(12, 6))
        plt.hist(años_hasta_vencimiento, bins=30, color='coral', edgecolor='black', alpha=0.7)
        plt.title('Perfil de Vencimientos del Universo', fontsize=14, fontweight='bold')
        plt.xlabel('Años hasta Vencimiento', fontsize=12)
        plt.ylabel('Número de Bonos', fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        # Guardar
        plt.savefig('resultados/03_perfil_vencimientos.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print("  ✓ Gráfico guardado: 03_perfil_vencimientos.png")
    
    # Gráfico 4: Scatter Cupón vs Rating
    # -----------------------------------
    # Validación de la relación riesgo-retorno 
    # Verificamos que los bonos más arriesgados pagan más intereses 
    
    if columna_rating and 'Coupon' in df_analisis.columns:
        # Convertir ratings a números para el gráfico
        def rating_a_numero(rating):
            if pd.isna(rating):
                return None
            rating_str = str(rating).upper().strip()
            if 'AAA' in rating_str:
                return 1
            elif 'AA' in rating_str:
                return 3
            elif rating_str.startswith('A') and not 'AA' in rating_str:
                return 5
            elif 'BBB' in rating_str:
                return 8
            elif 'BB' in rating_str:
                return 11
            elif 'B' in rating_str and 'BB' not in rating_str:
                return 14
            else:
                return 10
        
        df_analisis['Rating_Numerico'] = df_analisis[columna_rating].apply(rating_a_numero)
        df_plot = df_analisis.dropna(subset=['Rating_Numerico', 'Coupon'])
        
        if len(df_plot) > 0:
            plt.figure(figsize=(12, 6))
            plt.scatter(df_plot['Rating_Numerico'], df_plot['Coupon'], 
                       alpha=0.5, s=50, color='darkgreen', edgecolors='black')
            plt.title('Relación Cupón vs Rating', fontsize=14, fontweight='bold')
            plt.xlabel('Rating (1=AAA, 20=C)', fontsize=12)
            plt.ylabel('Cupón (%)', fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            # Guardar
            plt.savefig('resultados/04_cupon_vs_rating.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            print("  ✓ Gráfico guardado: 04_cupon_vs_rating.png")
    
    print("\n✓ Análisis visual completado\n")
    
    # =========================================================================
    # PARTE 1 - AMPLIACIÓN: DIVISAS, TIPO DE BONO, PRELACIÓN, OPCIONALIDAD,
    #                        PERPETUOS, LIQUIDEZ Y NULOS
    # =========================================================================
    
    print("="*80)
    print("PARTE 1: ATRIBUTOS ADICIONALES DEL UNIVERSO".center(80))
    print("="*80 + "\n")
    
    # 1) Cuadro de nulos por columna clave
    columnas_clave = [
        'ISIN', 'Description', 'Currency', 'Coupon', 'Coupon Frequency',
        'Maturity', 'Next Call Date', 'Issue date', 'Bid Price', 'Ask Price',
        'Amount Outstanding', 'Seniority', 'Security Type', 'Type'
    ]
    cols_presentes = [c for c in columnas_clave if c in df_analisis.columns]
    df_nulos = df_analisis[cols_presentes].isna().sum().reset_index()
    df_nulos.columns = ['Columna', 'Nulos']
    df_nulos.to_csv('resultados/01a_nulos.csv', index=False)
    print("  ✓ Cuadro de nulos guardado: 01a_nulos.csv")
    
    # 2) Divisas
    if 'Currency' in df_analisis.columns:
        plt.figure(figsize=(12, 6))
        df_analisis['Currency'].value_counts().head(10).plot(kind='bar', color='slateblue', edgecolor='black')
        plt.title('Distribución por Divisa (Top 10)', fontsize=14, fontweight='bold')
        plt.xlabel('Divisa', fontsize=12)
        plt.ylabel('Número de Bonos', fontsize=12)
        plt.tight_layout()
        plt.savefig('resultados/01b_distribucion_divisas.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("  ✓ Gráfico guardado: 01b_distribucion_divisas.png")
    
    # 3) Tipo de bono: fijo vs flotante (heurística por texto)
    col_tipo_bono = None
    for col in ['Coupon Type', 'Security Type', 'Type', 'Description']:
        if col in df_analisis.columns:
            col_tipo_bono = col
            break
    if col_tipo_bono:
        serie_tipo = df_analisis[col_tipo_bono].astype(str).str.upper()
        es_flotante = serie_tipo.str.contains('FLOAT|FRN|FLOATING', na=False)
        conteo = pd.Series({
            'Fixed (aprox)': (~es_flotante).sum(),
            'Floating/FRN (aprox)': es_flotante.sum()
        })
        plt.figure(figsize=(6, 4))
        conteo.plot(kind='bar', color=['teal', 'orange'], edgecolor='black')
        plt.title('Tipo de Bono (Heurístico: Fixed vs Floating)', fontsize=12, fontweight='bold')
        plt.xticks(rotation=0)
        plt.tight_layout()
        plt.savefig('resultados/01c_tipo_bono.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("  ✓ Gráfico guardado: 01c_tipo_bono.png")
    
    # 4) Prelación (Seniority)
    col_seniority = None
    for col in ['Seniority', 'Security Type', 'Type']:
        if col in df_analisis.columns:
            col_seniority = col
            break
    if col_seniority:
        plt.figure(figsize=(12, 6))
        df_analisis[col_seniority].astype(str).value_counts().head(10).plot(kind='bar', color='indianred', edgecolor='black')
        plt.title('Prelación / Seniority (Top 10)', fontsize=14, fontweight='bold')
        plt.xlabel('Seniority', fontsize=12)
        plt.ylabel('Número de Bonos', fontsize=12)
        plt.tight_layout()
        plt.savefig('resultados/01d_prelacion.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("  ✓ Gráfico guardado: 01d_prelacion.png")
    
    # 5) Opcionalidad y Perpetuos (conteos básicos)
    tiene_call = 'Next Call Date' in df_analisis.columns and df_analisis['Next Call Date'].notna()
    es_perpetuo = (
        ('Maturity' in df_analisis.columns) and
        df_analisis['Maturity'].isna()
    ) | df_analisis.get('Description', '').astype(str).str.upper().str.contains('PERP', na=False)
    resumen_opc = pd.DataFrame({
        'Metric': ['Con Call', 'Perpetuo (heurístico)'],
        'Count': [tiene_call.sum() if isinstance(tiene_call, pd.Series) else 0, es_perpetuo.sum()]
    })
    resumen_opc.to_csv('resultados/01e_opcionalidad_perpetuos.csv', index=False)
    print("  ✓ Resumen guardado: 01e_opcionalidad_perpetuos.csv")
    
    # 6) Liquidez: horquilla y tamaño de emisión
    if 'Bid Price' in df_analisis.columns and 'Ask Price' in df_analisis.columns:
        df_analisis['Bid_Ask_Spread'] = pd.to_numeric(df_analisis['Ask Price'], errors='coerce') - pd.to_numeric(df_analisis['Bid Price'], errors='coerce')
        plt.figure(figsize=(12, 6))
        df_analisis['Bid_Ask_Spread'].dropna().clip(lower=0, upper=df_analisis['Bid_Ask_Spread'].quantile(0.99)).hist(bins=40, color='gray', edgecolor='black')
        plt.title('Histograma de Horquillas Bid–Ask (acotado 99%)', fontsize=14, fontweight='bold')
        plt.xlabel('Bid–Ask (precio)', fontsize=12)
        plt.ylabel('Número de Bonos', fontsize=12)
        plt.tight_layout()
        plt.savefig('resultados/01f_horquillas.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("  ✓ Gráfico guardado: 01f_horquillas.png")
    
    if 'Amount Outstanding' in df_analisis.columns:
        serie_out = pd.to_numeric(df_analisis['Amount Outstanding'], errors='coerce')
        plt.figure(figsize=(12, 6))
        serie_out.dropna().clip(upper=serie_out.quantile(0.99)).hist(bins=40, color='seagreen', edgecolor='black')
        plt.title('Distribución de Amount Outstanding (M EUR, acotado 99%)', fontsize=14, fontweight='bold')
        plt.xlabel('Outstanding (millones EUR)', fontsize=12)
        plt.ylabel('Número de Bonos', fontsize=12)
        plt.tight_layout()
        plt.savefig('resultados/01g_amount_outstanding.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("  ✓ Gráfico guardado: 01g_amount_outstanding.png")
    
    # 7) Emisores y concentración (HHI / Top-10)
    columna_emisor = None
    for col in ['Issuer Name', 'Issuer', 'Name', 'Description']:
        if col in df_analisis.columns:
            columna_emisor = col
            break
    if columna_emisor:
        # Conteo por emisor
        conteo_emisores = df_analisis[columna_emisor].astype(str).str.strip().value_counts()
        total_bonos = conteo_emisores.sum()
        top10_emisores = conteo_emisores.head(10)
        
        # Gráfico Top-10 emisores
        plt.figure(figsize=(14, 6))
        ax = top10_emisores.plot(kind='bar', color='steelblue', edgecolor='black')
        plt.title('Top-10 Emisores por Número de Bonos', fontsize=14, fontweight='bold')
        plt.xlabel('Emisor', fontsize=12)
        plt.ylabel('Número de Bonos', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        plt.savefig('resultados/01h_top_emisores.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("  ✓ Gráfico guardado: 01h_top_emisores.png")
        
        # Top-10 emisores (tabla)
        df_top10_emisores = top10_emisores.reset_index()
        df_top10_emisores.columns = ['Emisor', 'Bonos']
        df_top10_emisores['Peso_%'] = (df_top10_emisores['Bonos'] / total_bonos) * 100.0
        df_top10_emisores.to_csv('resultados/01i_top10_emisores.csv', index=False)
        print("  ✓ Tabla guardada: 01i_top10_emisores.csv")
        
        # HHI y CR10 (concentración)
        pesos_por_emisor = conteo_emisores / total_bonos
        hhi = float((pesos_por_emisor ** 2).sum())
        cr10 = float(top10_emisores.sum() / total_bonos)
        df_concentracion = pd.DataFrame({
            'Metric': ['HHI (por participación en nº de bonos)', 'CR10 (Top-10 participación)'],
            'Value': [hhi, cr10]
        })
        df_concentracion.to_csv('resultados/01j_concentracion_emisores_resumen.csv', index=False)
        print("  ✓ Resumen guardado: 01j_concentracion_emisores_resumen.csv")
    
    # =========================================================================
    # PARTE 2: VALORACIÓN TEÓRICA
    # =========================================================================
    
    print("="*80)
    print("PARTE 2: VALORACIÓN TEÓRICA (SPREAD = 0)".center(80))
    print("="*80 + "\n")
    
    curva = valorador_bonos.CurvaDescuento(df_curva_estr)
    resultados_parte2 = []
    
    # Valorar bonos 
    for idx, fila in df_analisis.iterrows():
        bono = valorador_bonos.Bono(
            isin=fila['ISIN'],
            cupon=fila['Coupon'],
            fecha_vencimiento=fila['Fecha_Vencimiento_Efectiva'],
            frecuencia_cupon=fila['Coupon Frequency'],
            fecha_emision=fila.get('Issue date'),  # CLAVE para cupón corrido
            fecha_primer_cupon=fila.get('First Coupon Date')
        )
        
        valorador = valorador_bonos.ValoradorBono(bono, curva)
        resultado_valoracion = valorador.valorar(fecha_valoracion, spread_credito_pb=0)
        
        resultados_parte2.append({
            'ISIN': fila['ISIN'],
            'Descripcion': fila['Description'],
            'Precio_Mercado': fila['Precio_Mercado'],
            'Precio_Sucio': resultado_valoracion['Precio_Sucio'],
            'Cupon_Corrido': resultado_valoracion['Cupon_Corrido'],
            'Precio_Teorico': resultado_valoracion['Precio_Limpio'],
            'Diferencia': resultado_valoracion['Precio_Limpio'] - fila['Precio_Mercado'],
            'Diferencia_Pct': ((resultado_valoracion['Precio_Limpio'] / fila['Precio_Mercado']) - 1) * 100
        })
    
    df_resultados_parte2 = pd.DataFrame(resultados_parte2)
    
    # Mostrar primeros 10 resultados (incluyendo Cupón Corrido)
    print(df_resultados_parte2[['ISIN', 'Precio_Mercado', 'Precio_Sucio', 'Cupon_Corrido', 'Precio_Teorico']].head(10).to_string(index=False))
    
    print(f"\n✓ Estadísticas:")
    print(f"  Cupón Corrido promedio: {df_resultados_parte2['Cupon_Corrido'].mean():.2f}")
    print(f"  Cupón Corrido máximo: {df_resultados_parte2['Cupon_Corrido'].max():.2f}")
    print(f"  Diferencia promedio (Teórico - Mercado): {df_resultados_parte2['Diferencia'].mean():.2f}")
    print(f"  Diferencia porcentual promedio: {df_resultados_parte2['Diferencia_Pct'].mean():.2f}%")
    
    # Guardar
    df_resultados_parte2.to_csv('resultados/parte2_valoracion.csv', index=False)
    print(f"\n✓ Guardado: resultados/parte2_valoracion.csv\n")
    
    # =========================================================================
    # PARTE 3: CÁLCULO DE Z-SPREAD
    # =========================================================================
    
    print("="*80)
    print("PARTE 3: CÁLCULO DE Z-SPREAD".center(80))
    print("="*80 + "\n")
    
    # Calculamos el Z-Spread de cada bono (spread constante sobre la curva que iguala precio de mercado)
    # Calculamos cuánto extra paga cada bono sobre la tasa libre de riesgo
    
    resultados_parte3 = []
    
    for idx, fila in df_analisis.iterrows():
        bono = valorador_bonos.Bono(
            isin=fila['ISIN'],
            cupon=fila['Coupon'],
            fecha_vencimiento=fila['Fecha_Vencimiento_Efectiva'],
            frecuencia_cupon=fila['Coupon Frequency'],
            fecha_emision=fila.get('Issue date'),
            fecha_primer_cupon=fila.get('First Coupon Date')
        )
        
        valorador = valorador_bonos.ValoradorBono(bono, curva)
        
        try:
            z_spread = valorador.calcular_z_spread(fecha_valoracion, fila['Precio_Mercado'])
            
            resultados_parte3.append({
                'ISIN': fila['ISIN'],
                'Descripcion': fila['Description'],
                'Precio_Mercado': fila['Precio_Mercado'],
                'Z_Spread': z_spread
            })
        except:
            continue
    
    df_resultados_parte3 = pd.DataFrame(resultados_parte3)
    
    # Mostrar primeros 10 resultados
    print(df_resultados_parte3[['ISIN', 'Precio_Mercado', 'Z_Spread']].head(10).to_string(index=False))
    
    print(f"\n✓ Estadísticas:")
    print(f"  Z-Spread promedio: {df_resultados_parte3['Z_Spread'].mean():.2f} pb")
    print(f"  Z-Spread mínimo: {df_resultados_parte3['Z_Spread'].min():.2f} pb")
    print(f"  Z-Spread máximo: {df_resultados_parte3['Z_Spread'].max():.2f} pb")
    
    # Guardar
    df_resultados_parte3.to_csv('resultados/parte3_z_spread.csv', index=False)
    print(f"\n✓ Guardado: resultados/parte3_z_spread.csv\n")
    
    # =========================================================================
    # PARTE 4 
    # =========================================================================
    
    print("="*80)
    print("PARTE 4: MÉTRICAS ESTÁNDAR".center(80))
    print("="*80 + "\n")
    
    resultados_parte4_nivel1 = []
    
    for idx, fila in df_analisis.iterrows():
        bono = valorador_bonos.Bono(
            isin=fila['ISIN'],
            cupon=fila['Coupon'],
            fecha_vencimiento=fila['Fecha_Vencimiento_Efectiva'],
            frecuencia_cupon=fila['Coupon Frequency'],
            fecha_emision=fila.get('Issue date')
        )
        
        valorador = valorador_bonos.ValoradorBono(bono, curva)
        
        # Obtenemos el cupón corrido de valorar() para reutilizarlo en calcular_ytc()
        
        resultado_valoracion = valorador.valorar(fecha_valoracion, spread_credito_pb=0)
        cupon_corrido = resultado_valoracion['Cupon_Corrido']
        
        ytc = valorador.calcular_ytc(fecha_valoracion, fila['Precio_Mercado'], cupon_corrido)
        analiticas_std = valorador.calcular_analiticas_std(fecha_valoracion, ytc)
        
        resultados_parte4_nivel1.append({
            'ISIN': fila['ISIN'],
            'Descripcion': fila['Description'],
            'Precio_Mercado': fila['Precio_Mercado'],
            'YTC': ytc * 100 if not np.isnan(ytc) else np.nan,
            'Duracion_Macaulay': analiticas_std['Duracion_Macaulay'],
            'Duracion_Modificada': analiticas_std['Duracion_Modificada'],
            'Convexidad': analiticas_std['Convexidad']
        })
    
    df_resultados_nivel1 = pd.DataFrame(resultados_parte4_nivel1)
    
    # Mostrar primeros 10 resultados
    print(df_resultados_nivel1[['ISIN', 'YTC', 'Duracion_Macaulay', 'Duracion_Modificada', 'Convexidad']].head(10).to_string(index=False))
    
    print(f"\n✓ Estadísticas:")
    print(f"  YTC promedio: {df_resultados_nivel1['YTC'].mean():.2f}%")
    print(f"  Duración Modificada promedio: {df_resultados_nivel1['Duracion_Modificada'].mean():.2f} años")
    print(f"  Convexidad promedio: {df_resultados_nivel1['Convexidad'].mean():.2f}")
    
    # Guardar
    df_resultados_nivel1.to_csv('resultados/parte4_nivel1_metricas_estandar.csv', index=False)
    print(f"\n✓ Guardado: resultados/parte4_nivel1_metricas_estandar.csv\n")
    
    # =========================================================================
    # PARTE 4 MÉTRICAS EFECTIVAS
    # =========================================================================
    
    print("="*80)
    print("PARTE 4: MÉTRICAS EFECTIVAS".center(80))
    print("="*80 + "\n")
    
    SPREAD_MERCADO_PB = 100
    resultados_parte4_nivel2 = []
    
    for idx, fila in df_analisis.iterrows():
        bono = valorador_bonos.Bono(
            isin=fila['ISIN'],
            cupon=fila['Coupon'],
            fecha_vencimiento=fila['Fecha_Vencimiento_Efectiva'],
            frecuencia_cupon=fila['Coupon Frequency'],
            fecha_emision=fila.get('Issue date')
        )
        
        valorador = valorador_bonos.ValoradorBono(bono, curva)
        
        try:
            # Calcular métricas efectivas (DV01)
            analiticas_eff = valorador.calcular_analiticas_efectivas(fecha_valoracion, SPREAD_MERCADO_PB)
            
            # Calcular CS01 (riesgo de crédito)
            cs01 = valorador.calcular_cs01(fecha_valoracion, SPREAD_MERCADO_PB)
            
            resultados_parte4_nivel2.append({
                'ISIN': fila['ISIN'],
                'Descripcion': fila['Description'],
                'Precio_Mercado': fila['Precio_Mercado'],
                'DV01': analiticas_eff['DV01'],
                'CS01': cs01,
                'Duracion_Efectiva': analiticas_eff['Duracion_Efectiva'],
                'Convexidad_Efectiva': analiticas_eff['Convexidad_Efectiva'],
                'Precio_Base': analiticas_eff.get('Precio_Base'),
                'Precio_Up': analiticas_eff.get('Precio_Up'),
                'Precio_Down': analiticas_eff.get('Precio_Down')
            })
        except:
            continue
    
    df_resultados_nivel2 = pd.DataFrame(resultados_parte4_nivel2)
    
    # Mostrar primeros 10 resultados (ahora con CS01)
    print(df_resultados_nivel2[['ISIN', 'DV01', 'CS01', 'Duracion_Efectiva']].head(10).to_string(index=False))
    
    print(f"\n✓ Estadísticas:")
    print(f"  DV01 promedio: {df_resultados_nivel2['DV01'].mean():.4f}")
    print(f"  CS01 promedio: {df_resultados_nivel2['CS01'].mean():.4f}")
    print(f"  Duración Efectiva promedio: {df_resultados_nivel2['Duracion_Efectiva'].mean():.2f} años")
    print(f"  Convexidad Efectiva promedio: {df_resultados_nivel2['Convexidad_Efectiva'].mean():.2f}")
    
    # Análisis DV01 vs CS01
    print(f"\n✓ Análisis DV01 vs CS01:")
    print(f"  Ratio DV01/CS01 promedio: {(df_resultados_nivel2['DV01'] / df_resultados_nivel2['CS01']).mean():.2f}")
    print(f"  → El riesgo de tasas (DV01) es ~{(df_resultados_nivel2['DV01'] / df_resultados_nivel2['CS01']).mean():.1f}x el riesgo de crédito (CS01)")
    
    # Guardar
    df_resultados_nivel2.to_csv('resultados/parte4_nivel2_metricas_efectivas.csv', index=False)
    print(f"\n✓ Guardado: resultados/parte4_nivel2_metricas_efectivas.csv\n")
    
    # =========================================================================
    # PARTE 4 (EXTRA): ESTIMACIÓN DE PRECIO POR DURACIÓN Y CONVEXIDAD
    # =========================================================================
    
    print("="*80)
    print("PARTE 4 (EXTRA): ESTIMACIÓN ΔP POR DURACIÓN Y CONVEXIDAD".center(80))
    print("="*80 + "\n")
    
    # Usamos el bump efectivo de ±1 bp (dy = 0.0001) para validar la aproximación
    dy = 0.0001
    df_est = df_resultados_nivel1[['ISIN', 'Duracion_Modificada', 'Convexidad']].merge(
        df_resultados_nivel2[['ISIN', 'Precio_Mercado', 'DV01', 'Precio_Base', 'Precio_Up', 'Precio_Down']],
        on='ISIN',
        how='inner'
    )
    # Estimación teórica (up/down) con fórmula de Taylor de 2º orden
    # ΔP/P ≈ -D_mod*dy + 0.5*Conv*dy^2
    df_est['P_est_up'] = df_est['Precio_Base'] * (1 - df_est['Duracion_Modificada'] * dy + 0.5 * df_est['Convexidad'] * (dy ** 2))
    df_est['P_est_down'] = df_est['Precio_Base'] * (1 + df_est['Duracion_Modificada'] * dy + 0.5 * df_est['Convexidad'] * (dy ** 2))
    # Errores contra precios efectivos (calculados bumping la curva)
    df_est['Error_up_abs'] = df_est['P_est_up'] - df_est['Precio_Up']
    df_est['Error_down_abs'] = df_est['P_est_down'] - df_est['Precio_Down']
    df_est['Error_up_pct'] = (df_est['P_est_up'] / df_est['Precio_Up'] - 1) * 100
    df_est['Error_down_pct'] = (df_est['P_est_down'] / df_est['Precio_Down'] - 1) * 100
    
    # Guardar resultados
    columnas_out = ['ISIN', 'Precio_Base', 'Precio_Up', 'Precio_Down', 'P_est_up', 'P_est_down',
                    'Duracion_Modificada', 'Convexidad', 'DV01', 'Error_up_abs', 'Error_down_abs',
                    'Error_up_pct', 'Error_down_pct']
    df_est[columnas_out].to_csv('resultados/parte4_estimacion_dyc.csv', index=False)
    print("✓ Guardado: resultados/parte4_estimacion_dyc.csv\n")
    
    # =========================================================================
    # COMPARACIÓN
    # =========================================================================
    
    print("="*80)
    print("COMPARACIÓN: MÉTRICAS ESTÁNDAR vs EFECTIVAS".center(80))
    print("="*80 + "\n")
    
    df_comparacion = df_resultados_nivel1[['ISIN', 'Duracion_Modificada', 'Convexidad']].merge(
        df_resultados_nivel2[['ISIN', 'Duracion_Efectiva', 'Convexidad_Efectiva', 'DV01', 'CS01']],
        on='ISIN'
    )
    
    print(df_comparacion[['ISIN', 'Duracion_Modificada', 'Duracion_Efectiva', 'DV01', 'CS01']].head(10).to_string(index=False))
    
    # Guardar
    df_comparacion.to_csv('resultados/comparacion_metricas.csv', index=False)
    print(f"\n✓ Guardado: resultados/comparacion_metricas.csv")
    
    # =========================================================================
    # EXPLICACIÓN CS01 vs DV01
    # =========================================================================
    
    print("\n" + "-"*80)
    print("ANÁLISIS: DV01 vs CS01 (RIESGO DE TASAS vs RIESGO DE CRÉDITO)")
    print("-"*80 + "\n")
    
    print("EXTRA:Descomposición del Riesgo Total\n")
    print("Un bono corporativo tiene DOS fuentes principales de riesgo:\n")
    
    print("1. DV01 (Riesgo de Tasas de Interés):")
    print("   → Sensibilidad a cambios en la curva ESTR (tipos libres de riesgo del BCE)")
    print("   → Si el BCE sube tasas → Todos los bonos bajan de precio")
    print("   → Se cubre con: Futuros del Bund, Swaps de tipos\n")
    
    print("2. CS01 (Riesgo de Crédito/Spread):")
    print("   → Sensibilidad a cambios en el spread de crédito de la empresa")
    print("   → Si la empresa empeora → Su spread sube → Precio del bono baja")
    print("   → Se cubre con: CDS (Credit Default Swaps), venta del bono\n")
    
    ratio_promedio = (df_resultados_nivel2['DV01'] / df_resultados_nivel2['CS01']).mean()
    print(f"Resultado del análisis:")
    print(f"   Ratio DV01/CS01 = {ratio_promedio:.2f}")
    print(f"   → El riesgo de tasas es {ratio_promedio:.1f} veces mayor que el riesgo de crédito")
    print(f"   → Por cada €1 que pierdes por spread, pierdes €{ratio_promedio:.1f} por tasas\n")
    
    print("Implicaciones para la gestión de riesgo:")
    print("   - Para cobertura completa, necesitas cubrir AMBOS riesgos")
    print("   - DV01: Operaciones con derivados de tipos de interés")
    print("   - CS01: Operaciones con derivados de crédito o diversificación")
    
    # =========================================================================
    # PREPARACIÓN PARA GESTIÓN DE CARTERAS (Partes 5-9)
    # =========================================================================
    
    # Merge completo con todas las métricas calculadas
    # CRÍTICO: Este DataFrame alimentará el GestorCarteras y DEBE tener DV01, CS01, etc.
    df_completo_metricas = df_analisis.copy()
    
    print("\n" + "="*80)
    print("📊 INTEGRANDO MÉTRICAS DE RIESGO EN EL DATASET PRINCIPAL")
    print("="*80)
    print(f"✓ Dataset inicial: {len(df_completo_metricas)} bonos")
    
    # Añadir Z-Spread (Parte 3)
    if len(df_resultados_parte3) > 0:
        df_completo_metricas = df_completo_metricas.merge(
            df_resultados_parte3[['ISIN', 'Z_Spread']],
            on='ISIN',
            how='left'
        )
        print(f"✓ Z-Spread añadido: {df_completo_metricas['Z_Spread'].notna().sum()} bonos con datos")
    
    # Añadir métricas de Nivel 1 (YTC, Duracion_Modificada, Convexidad)
    if len(df_resultados_nivel1) > 0:
        df_completo_metricas = df_completo_metricas.merge(
            df_resultados_nivel1[['ISIN', 'YTC', 'Duracion_Modificada', 'Convexidad']],
            on='ISIN',
            how='left'
        )
        print(f"✓ Métricas Nivel 1 añadidas: {df_completo_metricas['Duracion_Modificada'].notna().sum()} bonos con datos")
    
    # Añadir métricas de Nivel 2 (DV01, CS01, Duracion_Efectiva, Convexidad_Efectiva)
    if len(df_resultados_nivel2) > 0:
        df_completo_metricas = df_completo_metricas.merge(
            df_resultados_nivel2[['ISIN', 'DV01', 'CS01', 'Duracion_Efectiva', 'Convexidad_Efectiva']],
            on='ISIN',
            how='left'
        )
        print(f"✓ Métricas Nivel 2 añadidas:")
        print(f"  - DV01: {df_completo_metricas['DV01'].notna().sum()} bonos con datos")
        print(f"  - CS01: {df_completo_metricas['CS01'].notna().sum()} bonos con datos")
        print(f"  - Duracion_Efectiva: {df_completo_metricas['Duracion_Efectiva'].notna().sum()} bonos con datos")
    
    print(f"\n✓✓ DATASET COMPLETO LISTO: {len(df_completo_metricas)} bonos con todas las métricas")
    print("="*80 + "\n")
    
    # Crear el gestor de carteras
    gestor = gestor_carteras.GestorCarterasBonos(
        df_bonos=df_universo,
        df_valoraciones=df_completo_metricas,
        df_indices_futuros=df_indices_futuros
    )
    
    # =========================================================================
    # PARTE 5: CARTERA EQUIPONDERADA Y BACKTEST
    # =========================================================================
    
    print("\n" + "="*80)
    print("PARTE 5: CARTERA EQUIPONDERADA Y BACKTEST".center(80))
    print("="*80 + "\n")
    
    # Construir cartera equiponderada
    cartera_equiponderada = gestor.construir_cartera_equiponderada(capital_inicial=1000000)
    
    print(f"✓ Cartera equiponderada construida:")
    print(f"  - Número de bonos: {len(cartera_equiponderada)}")
    print(f"  - Peso por bono: {cartera_equiponderada['Peso'].iloc[0]*100:.4f}%")
    print(f"  - Capital por bono: {cartera_equiponderada['Nominal_Invertido'].iloc[0]:,.2f} EUR")
    
    # Guardar composición
    cartera_equiponderada.to_csv('resultados/parte5_cartera_equiponderada.csv', index=False)
    print(f"\n✓ Guardado: resultados/parte5_cartera_equiponderada.csv")
    
    # Backtest vs Benchmark
    # Periodo completo de históricos disponibles (01/10/2023 a 01/10/2025)
    # Usamos todo el período de datos que tenemos (2 años)
    fecha_inicio_backtest = datetime(2023, 10, 1)
    fecha_fin_backtest = datetime(2025, 10, 1)
    
    resultado_backtest = gestor.backtest_cartera_vs_benchmark(
        cartera_equiponderada,
        fecha_inicio_backtest,
        fecha_fin_backtest,
        df_precios_historicos_completo,
        frecuencia_rebalanceo='M'
    )
    
    if resultado_backtest:
        print(f"\n✓ Backtest completado:")
        for metrica, valor in resultado_backtest['metricas'].items():
            print(f"  - {metrica}: {valor:.2f}")
        
        # Generar gráfico
        gestor.generar_grafico_backtest(resultado_backtest, 'resultados/parte5_backtest_grafico.png')
        
        # Guardar métricas
        df_metricas_backtest = pd.DataFrame([resultado_backtest['metricas']])
        df_metricas_backtest.to_csv('resultados/parte5_backtest_metricas.csv', index=False)
        print(f"✓ Guardado: resultados/parte5_backtest_metricas.csv\n")
    
    # =========================================================================
    # PARTE 6: CARTERA OPTIMIZADA (PROGRAMACIÓN LINEAL)
    # =========================================================================
    
    print("\n" + "="*80)
    print("PARTE 6: CARTERA OPTIMIZADA".center(80))
    print("="*80 + "\n")
    
    # Construir cartera maximizando rentabilidad (YTC) con restricciones
    # -------------------------------------------------------------------
    # Usamos programación lineal para encontrar los pesos óptimos que
    # maximizan la rentabilidad (YTC promedio) respetando todas las restricciones
    
    cartera_restringida = gestor.construir_cartera_restringida(capital_inicial=1000000)
    
    if len(cartera_restringida) > 0:
        # Calcular métricas de la cartera
        ytc_promedio = (cartera_restringida['Peso'] * cartera_restringida['YTC']).sum()
        duracion_promedio = (cartera_restringida['Peso'] * cartera_restringida['Duracion_Modificada']).sum()
        
        print(f"\n" + "="*80)
        print("COMPOSICIÓN DE LA CARTERA OPTIMIZADA".center(80))
        print("="*80 + "\n")
        
        # Mostrar tabla con bonos seleccionados
        print(cartera_restringida[['ISIN', 'Nombre', 'Peso', 'YTC', 'Duracion_Modificada', 'Rating']].to_string(index=False))
        
        print(f"\n" + "="*80)
        print("RENTABILIDAD Y RESTRICCIONES".center(80))
        print("="*80)
        
        print(f"\n🎯 RENTABILIDAD DE LA CARTERA:")
        print(f"  • YTC promedio ponderado: {ytc_promedio:.2f}% anual")
        
        print(f"\n✓ RESTRICCIONES CUMPLIDAS:")
        print(f"  • Número de bonos: {len(cartera_restringida)} (máximo: 20)")
        print(f"  • Duración de cartera: {duracion_promedio:.2f} años (límite: 3.0)")
        
        # Verificar restricción de HY
        if 'Clasificacion_Rating' in cartera_restringida.columns:
            peso_hy = (cartera_restringida['Peso'] * (cartera_restringida['Clasificacion_Rating'] == 'HY').astype(float)).sum()
            print(f"  • Peso High Yield: {peso_hy*100:.2f}% (límite: 10%)")
        
        # Verificar peso máximo por emisión
        peso_max_emision = cartera_restringida['Peso'].max()
        print(f"  • Peso máximo por emisión: {peso_max_emision*100:.2f}% (límite: 10%)")
        
        # Verificar peso máximo por emisor
        peso_max_emisor = cartera_restringida.groupby('Nombre')['Peso'].sum().max()
        print(f"  • Peso máximo por emisor: {peso_max_emisor*100:.2f}% (límite: 15%)")
        
        print("\n" + "="*80 + "\n")
        
        # Guardar composición de la cartera
        cartera_restringida.to_csv('resultados/parte6_cartera_optimizada.csv', index=False)
        print(f"✓ Guardado: resultados/parte6_cartera_optimizada.csv")
        
        # Guardar métricas de rentabilidad y restricciones
        metricas_cartera = {
            'Rentabilidad_YTC_Anual (%)': [ytc_promedio],
            'Numero_Bonos': [len(cartera_restringida)],
            'Duracion_Cartera_Años': [duracion_promedio],
            'Peso_High_Yield (%)': [peso_hy * 100 if 'Clasificacion_Rating' in cartera_restringida.columns else 0],
            'Peso_Maximo_Emision (%)': [peso_max_emision * 100],
            'Peso_Maximo_Emisor (%)': [peso_max_emisor * 100],
            'Restriccion_Duracion_Max': [3.0],
            'Restriccion_HY_Max (%)': [10.0],
            'Restriccion_Emision_Max (%)': [10.0],
            'Restriccion_Emisor_Max (%)': [15.0]
        }
        
        df_metricas = pd.DataFrame(metricas_cartera)
        df_metricas.to_csv('resultados/parte6_rentabilidad_cartera.csv', index=False)
        print(f"✓ Guardado: resultados/parte6_rentabilidad_cartera.csv\n")
    else:
        print("⚠ No se pudo construir la cartera optimizada\n")
    
    # =========================================================================
    # PARTE 7: COBERTURA DE TIPOS (FUTUROS)
    # =========================================================================
    
    # Usamos la cartera restringida (más realista)
    cartera_para_coberturas = cartera_restringida if len(cartera_restringida) > 0 else cartera_equiponderada
    
    # VERIFICACIÓN: La cartera ya debería tener DV01 y CS01 de construir_cartera_restringida()
    # Si por alguna razón no los tiene, hacemos un merge adicional
    if 'DV01' not in cartera_para_coberturas.columns or 'CS01' not in cartera_para_coberturas.columns:
        print(f"\n⚠ Añadiendo métricas de riesgo faltantes a la cartera...")
        cartera_para_coberturas = cartera_para_coberturas.merge(
            df_completo_metricas[['ISIN', 'Precio_Mercado', 'DV01', 'CS01', 'Duracion_Efectiva']],
            on='ISIN',
            how='left',
            suffixes=('', '_extra')
        )
        print(f"✓ Métricas añadidas mediante merge")
    
    cobertura_tipos = gestor.calcular_cobertura_tipos(cartera_para_coberturas, fecha_valoracion)
    
    if cobertura_tipos:
        # Guardar resultados
        df_cobertura_tipos = pd.DataFrame([cobertura_tipos])
        df_cobertura_tipos.to_csv('resultados/parte7_cobertura_tipos.csv', index=False)
        print(f"\n✓ Guardado: resultados/parte7_cobertura_tipos.csv\n")
    
    # =========================================================================
    # PARTE 8: COBERTURA DE CRÉDITO (CDS)
    # =========================================================================
    
    cobertura_credito = gestor.calcular_cobertura_credito(cartera_para_coberturas, fecha_valoracion)
    
    if cobertura_credito:
        # Guardar resultados
        df_cobertura_credito = pd.DataFrame([cobertura_credito])
        df_cobertura_credito.to_csv('resultados/parte8_cobertura_credito.csv', index=False)
        print(f"\n✓ Guardado: resultados/parte8_cobertura_credito.csv\n")
    
    # =========================================================================
    # PARTE 9: ESTRATEGIA DE VALOR RELATIVO (REGRESIÓN)
    # =========================================================================
    
    # PARTE 9: ANÁLISIS DE VALOR RELATIVO (COMENTADO POR EL USUARIO)
    # El usuario eliminó esta parte del código
    # resultado_valor_relativo = gestor.analisis_valor_relativo()
    
    print("\n" + "="*80)
    print("ANÁLISIS COMPLETADO".center(80))
    print("="*80)
    print(f"\nTodos los resultados guardados en: resultados/")
    print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
