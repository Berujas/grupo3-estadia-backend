#!/usr/bin/env python3
"""
Script para probar el modelo con solo las columnas más importantes
"""
import pandas as pd
import numpy as np
from joblib import load
import sys
sys.path.append('src')

from utils import categorize_probability

def test_minimal_input():
    """Prueba el modelo con solo las columnas más importantes"""
    print("🧪 PROBANDO MODELO CON COLUMNAS MÍNIMAS")
    print("=" * 50)
    
    try:
        # Cargar modelo
        model = load("models/model_hgb_calibrated.joblib")
        print("✅ Modelo cargado exitosamente")
        
        # Crear datos con solo las columnas más importantes
        print("\n📊 Creando datos con columnas mínimas...")
        
        # Columnas más importantes según el análisis
        columnas_importantes = {
            # Datos básicos del paciente
            'edad_en_anos': [65],
            'sexo_desc_': ['Hombre'],
            'tipo_ingreso_descripcion_': ['Programado'],
            'servicio_ingreso_descripcion_': ['Medicina'],
            'prevision_desc_': ['FONASA'],
            'diagnostico_principal': ['I25.1'],
            'estancia_norma_grd': [4],
            
            # Datos de encuesta social
            'total': [75],
            'habitacional': [1],
            'socioeconomica': [1], 
            'salud_mental': [1],
            'redes': [1],
            'cuidador': [1],
            
            # Datos adicionales necesarios
            'ir_grd': ['051401 - PROCEDIMIENTO CARDIACO'],
            'ir_tipo_grd': ['M'],
            'ir_grd_codigo_': ['051401'],
            'proced_01_principal_cod_': ['0'],
            'pregunta': [75],
            'pregunta2': [80],
            'pregunta3': [85],
            'pregunta4': [70]
        }
        
        df_minimal = pd.DataFrame(columnas_importantes)
        print(f"   - Columnas incluidas: {len(df_minimal.columns)}")
        print(f"   - Registros: {len(df_minimal)}")
        
        # Intentar predicción
        print("\n🔮 Intentando predicción...")
        probabilities = model.predict_proba(df_minimal)[:, 1]
        
        print(f"✅ ¡PREDICCIÓN EXITOSA!")
        print(f"   - Probabilidad de exceso: {probabilities[0]:.3f} ({probabilities[0]*100:.1f}%)")
        
        categoria = categorize_probability(probabilities[0])
        if categoria in ['Baja', 'Media', 'Alta']:
            print(f"   - Categoría: RIESGO {categoria.upper()}")
        else:
            print(f"   - Categoría: {categoria}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\n🔍 Analizando qué columnas faltan...")
        
        # Intentar identificar columnas faltantes
        try:
            # Cargar datos completos para comparar
            df_completo = pd.read_csv('artifacts/X_test_preview.csv')
            columnas_completas = set(df_completo.columns)
            columnas_minimal = set(columnas_importantes.keys())
            columnas_faltantes = columnas_completas - columnas_minimal
            
            print(f"   - Columnas faltantes: {len(columnas_faltantes)}")
            print(f"   - Columnas faltantes principales:")
            for i, col in enumerate(sorted(columnas_faltantes)[:10], 1):
                print(f"     {i}. {col}")
            if len(columnas_faltantes) > 10:
                print(f"     ... y {len(columnas_faltantes) - 10} más")
                
        except Exception as e2:
            print(f"   - No se pudo analizar columnas faltantes: {e2}")
            
        return False

def test_with_missing_columns():
    """Prueba agregando columnas faltantes con valores por defecto"""
    print("\n🔧 PROBANDO CON COLUMNAS FALTANTES COMPLETADAS")
    print("=" * 50)
    
    try:
        # Cargar modelo
        model = load("models/model_hgb_calibrated.joblib")
        
        # Cargar estructura completa
        df_template = pd.read_csv('artifacts/X_test_preview.csv')
        
        # Crear datos mínimos con todas las columnas necesarias
        df_complete = df_template.iloc[:1].copy()  # Tomar primera fila como template
        
        # Llenar con datos de ejemplo
        df_complete['edad_en_anos'] = 65
        df_complete['sexo_desc_'] = 'Hombre'
        df_complete['tipo_ingreso_descripcion_'] = 'Programado'
        df_complete['servicio_ingreso_descripcion_'] = 'Medicina'
        df_complete['prevision_desc_'] = 'FONASA'
        df_complete['diagnostico_principal'] = 'I25.1'
        df_complete['estancia_norma_grd'] = 4
        df_complete['total'] = 75
        df_complete['habitacional'] = 1
        df_complete['socioeconomica'] = 1
        df_complete['salud_mental'] = 1
        df_complete['redes'] = 1
        df_complete['cuidador'] = 1
        
        print(f"   - Columnas totales: {len(df_complete.columns)}")
        print(f"   - Registros: {len(df_complete)}")
        
        # Intentar predicción
        print("\n🔮 Intentando predicción con datos completos...")
        probabilities = model.predict_proba(df_complete)[:, 1]
        
        print(f"✅ ¡PREDICCIÓN EXITOSA!")
        print(f"   - Probabilidad de exceso: {probabilities[0]:.3f} ({probabilities[0]*100:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 PRUEBA 1: Solo columnas importantes")
    success1 = test_minimal_input()
    
    print("\n" + "="*60)
    print("🧪 PRUEBA 2: Con todas las columnas necesarias")
    success2 = test_with_missing_columns()
    
    print("\n" + "="*60)
    print("📊 RESULTADOS:")
    print(f"   - Prueba con columnas mínimas: {'✅ ÉXITO' if success1 else '❌ FALLO'}")
    print(f"   - Prueba con columnas completas: {'✅ ÉXITO' if success2 else '❌ FALLO'}")
    
    if not success1 and success2:
        print("\n💡 CONCLUSIÓN: El modelo requiere TODAS las columnas del dataset original")
        print("   - No funciona con solo las columnas 'importantes'")
        print("   - Necesita la estructura completa de 64 columnas")
    elif success1:
        print("\n💡 CONCLUSIÓN: El modelo SÍ funciona con columnas mínimas")
        print("   - Se puede usar solo con las columnas más importantes")
    else:
        print("\n💡 CONCLUSIÓN: El modelo tiene problemas de configuración")
