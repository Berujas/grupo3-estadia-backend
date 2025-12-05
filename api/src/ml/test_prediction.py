#!/usr/bin/env python3
"""
Script para probar el modelo de predicción de exceso de estadía
"""
import os
import sys
import pandas as pd
import numpy as np
from joblib import load
import yaml

# Agregar el directorio src al path
sys.path.append('src')

from utils import read_excel_or_csv, coerce_dtypes, categorize_probabilities

def load_model():
    """Carga el modelo entrenado"""
    model_path = "models/model_hgb_calibrated.joblib"
    if not os.path.exists(model_path):
        model_path = "models/model_baseline.joblib"
    
    if not os.path.exists(model_path):
        raise FileNotFoundError("No se encontraron modelos entrenados")
    
    print(f"📦 Cargando modelo: {model_path}")
    return load(model_path)

def load_config():
    """Carga la configuración"""
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def test_prediction():
    """Prueba el modelo con datos de ejemplo"""
    print("🏥 Sistema de Predicción de Exceso de Estadía")
    print("=" * 50)
    
    try:
        # Cargar configuración y modelo
        config = load_config()
        model = load_model()
        
        # Cargar datos de prueba
        test_file = "data/nuevos.csv"
        if not os.path.exists(test_file):
            print(f"❌ No se encontró archivo de datos: {test_file}")
            return
        
        print(f"📊 Cargando datos de prueba: {test_file}")
        df_test = read_excel_or_csv(test_file)
        print(f"   - Registros encontrados: {len(df_test)}")
        print(f"   - Columnas: {len(df_test.columns)}")
        
        # Preparar datos
        print("🔧 Preparando datos...")
        df_processed, _, _ = coerce_dtypes(df_test.copy())
        
        # Hacer predicciones
        print("🔮 Generando predicciones...")
        probabilities = model.predict_proba(df_processed)[:, 1]
        
        # Crear resultados
        results = df_test.copy()
        results['probabilidad_exceso'] = probabilities
        results['riesgo_categoria'] = categorize_probabilities(probabilities)
        
        # Mostrar resultados
        print("\n📈 RESULTADOS DE PREDICCIÓN:")
        print("-" * 40)
        
        # Estadísticas generales
        print(f"📊 Estadísticas generales:")
        print(f"   - Probabilidad promedio: {probabilities.mean():.3f}")
        print(f"   - Probabilidad máxima: {probabilities.max():.3f}")
        print(f"   - Probabilidad mínima: {probabilities.min():.3f}")
        
        # Distribución de riesgo
        risk_dist = results['riesgo_categoria'].value_counts()
        print(f"\n🎯 Distribución de riesgo:")
        for categoria, count in risk_dist.items():
            percentage = (count / len(results)) * 100
            print(f"   - {categoria}: {count} pacientes ({percentage:.1f}%)")
        
        # Top 5 pacientes con mayor riesgo
        top_risk = results.nlargest(5, 'probabilidad_exceso')
        print(f"\n⚠️  TOP 5 PACIENTES CON MAYOR RIESGO:")
        print("-" * 50)
        for idx, row in top_risk.iterrows():
            print(f"   Paciente {idx+1}: {row['probabilidad_exceso']:.3f} ({row['riesgo_categoria']})")
        
        # Guardar resultados
        output_file = "predicciones_test.csv"
        results.to_csv(output_file, index=False)
        print(f"\n💾 Resultados guardados en: {output_file}")
        
        # Mostrar algunas filas de ejemplo
        print(f"\n📋 MUESTRA DE RESULTADOS:")
        print("-" * 50)
        sample_cols = ['probabilidad_exceso', 'riesgo_categoria']
        if 'edad_en_anos' in results.columns:
            sample_cols = ['edad_en_anos'] + sample_cols
        if 'sexo_desc_' in results.columns:
            sample_cols = ['sexo_desc_'] + sample_cols
            
        print(results[sample_cols].head(10).to_string(index=False))
        
        return results
        
    except Exception as e:
        print(f"❌ Error durante la predicción: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = test_prediction()
    
    if results is not None:
        print(f"\n✅ ¡Predicción completada exitosamente!")
        print(f"   - Total de pacientes analizados: {len(results)}")
        print(f"   - Archivo de resultados: predicciones_test.csv")
    else:
        print(f"\n❌ La predicción falló. Revisa los errores arriba.")
