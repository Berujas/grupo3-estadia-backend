#!/usr/bin/env python3
"""
Script para analizar los resultados de predicción del modelo
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys

sys.path.append('src')

from utils import (
    categorize_probabilities,
    LOW_RISK_THRESHOLD,
    HIGH_RISK_THRESHOLD
)

def analyze_predictions():
    """Analiza los resultados de predicción"""
    print("📊 ANÁLISIS DE PREDICCIONES DEL MODELO")
    print("=" * 50)
    
    try:
        # Cargar resultados
        df = pd.read_csv("predicciones_test.csv")
        
        print(f"📈 DATOS GENERALES:")
        print(f"   - Total de pacientes analizados: {len(df)}")
        print(f"   - Columnas en el dataset: {len(df.columns)}")
        
        # Análisis de probabilidades
        probs = df['p_excede_norma']
        
        print(f"\n📊 ESTADÍSTICAS DE PROBABILIDAD:")
        print(f"   - Probabilidad promedio: {probs.mean():.3f}")
        print(f"   - Probabilidad mediana: {probs.median():.3f}")
        print(f"   - Probabilidad máxima: {probs.max():.3f}")
        print(f"   - Probabilidad mínima: {probs.min():.3f}")
        print(f"   - Desviación estándar: {probs.std():.3f}")
        
        # Categorización de riesgo
        df['riesgo_categoria'] = categorize_probabilities(probs)
        
        risk_dist = df['riesgo_categoria'].value_counts()
        print(f"\n🎯 DISTRIBUCIÓN DE RIESGO:")
        for categoria, count in risk_dist.items():
            percentage = (count / len(df)) * 100
            print(f"   - {categoria}: {count} pacientes ({percentage:.1f}%)")
        
        # Top 10 pacientes con mayor riesgo
        top_risk = df.nlargest(10, 'p_excede_norma')
        print(f"\n⚠️  TOP 10 PACIENTES CON MAYOR RIESGO:")
        print("-" * 60)
        for idx, row in top_risk.iterrows():
            edad = row.get('edad_en_anos', 'N/A')
            sexo = row.get('sexo_desc_', 'N/A')
            servicio = row.get('servicio_ingreso_descripcion_', 'N/A')
            prob = row['p_excede_norma']
            categoria = row['riesgo_categoria']
            print(f"   {idx+1:2d}. Prob: {prob:.3f} ({categoria}) | Edad: {edad} | Sexo: {sexo} | Servicio: {servicio}")
        
        # Análisis por características
        print(f"\n🔍 ANÁLISIS POR CARACTERÍSTICAS:")
        
        # Por edad
        if 'edad_en_anos' in df.columns:
            df['grupo_edad'] = pd.cut(df['edad_en_anos'], 
                                     bins=[0, 30, 50, 70, 100], 
                                     labels=['<30', '30-50', '50-70', '70+'])
            edad_risk = df.groupby('grupo_edad')['p_excede_norma'].agg(['mean', 'count'])
            print(f"\n   📊 RIESGO POR GRUPO DE EDAD:")
            for grupo, stats in edad_risk.iterrows():
                print(f"      {grupo}: {stats['mean']:.3f} (n={stats['count']})")
        
        # Por sexo
        if 'sexo_desc_' in df.columns:
            sexo_risk = df.groupby('sexo_desc_')['p_excede_norma'].agg(['mean', 'count'])
            print(f"\n   📊 RIESGO POR SEXO:")
            for sexo, stats in sexo_risk.iterrows():
                print(f"      {sexo}: {stats['mean']:.3f} (n={stats['count']})")
        
        # Por servicio
        if 'servicio_ingreso_descripcion_' in df.columns:
            servicio_risk = df.groupby('servicio_ingreso_descripcion_')['p_excede_norma'].agg(['mean', 'count']).sort_values('mean', ascending=False)
            print(f"\n   📊 RIESGO POR SERVICIO (Top 5):")
            for servicio, stats in servicio_risk.head().iterrows():
                print(f"      {servicio}: {stats['mean']:.3f} (n={stats['count']})")
        
        # Recomendaciones
        print(f"\n💡 RECOMENDACIONES:")
        alto_riesgo = len(df[df['p_excede_norma'] > HIGH_RISK_THRESHOLD])
        medio_riesgo = len(df[(df['p_excede_norma'] >= LOW_RISK_THRESHOLD) & (df['p_excede_norma'] <= HIGH_RISK_THRESHOLD)])
        bajo_riesgo = len(df[df['p_excede_norma'] < LOW_RISK_THRESHOLD])
        
        low_pct = int(LOW_RISK_THRESHOLD * 100)
        high_pct = int(HIGH_RISK_THRESHOLD * 100)
        print(f"   - Pacientes de RIESGO ALTO (>{high_pct}%): {alto_riesgo} - Requieren intervención inmediata")
        print(f"   - Pacientes de RIESGO MEDIO ({low_pct}-{high_pct}%): {medio_riesgo} - Monitoreo intensivo recomendado")
        print(f"   - Pacientes de RIESGO BAJO (<{low_pct}%): {bajo_riesgo} - Seguimiento normal")
        
        if alto_riesgo > 0:
            print(f"\n   🚨 ACCIONES INMEDIATAS:")
            print(f"      - Revisar protocolos de alta para {alto_riesgo} pacientes de alto riesgo")
            print(f"      - Asignar trabajo social a casos prioritarios")
            print(f"      - Coordinar con servicios de apoyo social")
        
        # Guardar análisis detallado
        analysis_file = "analisis_predicciones.csv"
        df_analysis = df[['edad_en_anos', 'sexo_desc_', 'servicio_ingreso_descripcion_', 
                          'p_excede_norma', 'riesgo_categoria']].copy()
        df_analysis.to_csv(analysis_file, index=False)
        print(f"\n💾 Análisis detallado guardado en: {analysis_file}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error durante el análisis: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = analyze_predictions()
    
    if results is not None:
        print(f"\n✅ ¡Análisis completado exitosamente!")
        print(f"   - Revisa el archivo 'analisis_predicciones.csv' para detalles")
    else:
        print(f"\n❌ El análisis falló. Revisa los errores arriba.")
