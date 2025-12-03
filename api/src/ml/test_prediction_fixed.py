#!/usr/bin/env python3
"""
Script para probar el modelo de predicción de exceso de estadía
Versión corregida que maneja el preprocesamiento correctamente
"""
import os
import sys
import pandas as pd
import numpy as np
from joblib import load
import yaml

# Agregar el directorio src al path
sys.path.append('src')

from utils import (
    coerce_dtypes,
    categorize_probabilities,
    categorize_probability
)

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

def create_sample_data():
    """Crea datos de muestra basados en la estructura esperada"""
    print("🔧 Creando datos de muestra...")
    
    # Datos de muestra para un paciente
    sample_data = {
        'episodio_cmbd': ['TEST001'],
        'edad_en_anos': [65],
        'sexo_desc_': ['Hombre'],
        'tipo_ingreso_descripcion_': ['Programado'],
        'servicio_ingreso_descripcion_': ['Medicina'],
        'prevision_desc_': ['FONASA'],
        'ir_grd': [1.2],
        'ir_tipo_grd': ['No'],
        'ir_grd_codigo_': ['051401'],
        'diagnostico_principal': ['I25.1'],
        'proced_01_principal_cod_': ['0'],
        'estancia_norma_grd': [4],
        'fecha_ingreso_completa': ['2024-01-15'],
        # Datos de encuesta social
        'pregunta': [75],
        'pregunta2': [80],
        'pregunta3': [85],
        'pregunta4': [70],
        'habitacional': [1],
        'socioeconomica': [1],
        'salud_mental': [1],
        'redes': [1],
        'cuidador': [1],
        'total': [75]
    }
    
    return pd.DataFrame(sample_data)

def test_prediction():
    """Prueba el modelo con datos de ejemplo"""
    print("🏥 Sistema de Predicción de Exceso de Estadía")
    print("=" * 50)
    
    try:
        # Cargar configuración y modelo
        config = load_config()
        model = load_model()
        
        # Crear datos de muestra
        df_test = create_sample_data()
        print(f"📊 Datos de muestra creados:")
        print(f"   - Registros: {len(df_test)}")
        print(f"   - Columnas: {len(df_test.columns)}")
        
        # Mostrar algunos datos
        print(f"\n📋 Datos del paciente:")
        print(f"   - Edad: {df_test['edad_en_anos'].iloc[0]} años")
        print(f"   - Sexo: {df_test['sexo_desc_'].iloc[0]}")
        print(f"   - Tipo ingreso: {df_test['tipo_ingreso_descripcion_'].iloc[0]}")
        print(f"   - Servicio: {df_test['servicio_ingreso_descripcion_'].iloc[0]}")
        print(f"   - Estancia norma: {df_test['estancia_norma_grd'].iloc[0]} días")
        
        # Preparar datos (aplicar el mismo preprocesamiento que en entrenamiento)
        print("\n🔧 Preparando datos...")
        df_processed, num_cols, cat_cols = coerce_dtypes(df_test.copy())
        
        print(f"   - Columnas numéricas: {len(num_cols)}")
        print(f"   - Columnas categóricas: {len(cat_cols)}")
        
        # Hacer predicciones
        print("\n🔮 Generando predicciones...")
        probabilities = model.predict_proba(df_processed)[:, 1]
        
        # Crear resultados
        results = df_test.copy()
        results['probabilidad_exceso'] = probabilities
        results['riesgo_categoria'] = categorize_probabilities(probabilities)
        
        # Mostrar resultados
        print("\n📈 RESULTADOS DE PREDICCIÓN:")
        print("-" * 40)
        
        prob = probabilities[0]
        categoria = categorize_probability(prob)
        
        print(f"🎯 RESULTADO PARA EL PACIENTE:")
        print(f"   - Probabilidad de exceso: {prob:.3f} ({prob*100:.1f}%)")
        print(f"   - Categoría de riesgo: {categoria}")
        
        if categoria == 'Alta':
            print(f"   ⚠️  RIESGO ALTO: Se recomienda intervención temprana")
        elif categoria == 'Media':
            print(f"   ⚠️  RIESGO MEDIO: Monitoreo recomendado")
        elif categoria == 'Baja':
            print(f"   ✅ RIESGO BAJO: Seguimiento normal")
        else:
            print(f"   ℹ️  Riesgo no determinado")
        
        # Guardar resultados
        output_file = "predicciones_test.csv"
        results.to_csv(output_file, index=False)
        print(f"\n💾 Resultados guardados en: {output_file}")
        
        # Mostrar interpretación
        print(f"\n📊 INTERPRETACIÓN:")
        print(f"   - El modelo predice que hay un {prob*100:.1f}% de probabilidad")
        print(f"     de que este paciente exceda la estadía normativa de {df_test['estancia_norma_grd'].iloc[0]} días")
        
        if categoria == 'Alta':
            print(f"   - Se recomienda planificar estrategias de alta temprana")
        elif categoria == 'Media':
            print(f"   - Mantener monitoreo cercano mientras evoluciona la estadía")
        else:
            print(f"   - El paciente tiene bajo riesgo de exceso de estadía")
        
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
        print(f"   - Paciente analizado con éxito")
        print(f"   - Archivo de resultados: predicciones_test.csv")
    else:
        print(f"\n❌ La predicción falló. Revisa los errores arriba.")
