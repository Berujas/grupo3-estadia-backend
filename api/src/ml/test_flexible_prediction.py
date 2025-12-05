#!/usr/bin/env python3
"""
Script para probar la predicción flexible con solo columnas importantes
"""
import pandas as pd
import sys
sys.path.append('src')

def create_minimal_data():
    """Crea datos con solo las columnas más importantes"""
    
    # Datos de ejemplo con solo las columnas más importantes
    data = {
        # Datos básicos del paciente
        'edad_en_anos': [65, 45, 78, 32, 55],
        'sexo_desc_': ['Hombre', 'Mujer', 'Hombre', 'Mujer', 'Hombre'],
        'tipo_ingreso_descripcion_': ['Programado', 'Urgente', 'Programado', 'Urgente', 'Programado'],
        'servicio_ingreso_descripcion_': ['Medicina', 'Cirugía', 'Medicina', 'Pediatría', 'Cardiología'],
        'prevision_desc_': ['FONASA', 'ISAPRE', 'FONASA', 'FONASA', 'ISAPRE'],
        'diagnostico_principal': ['I25.1', 'K80.2', 'J44.1', 'A09', 'I21.9'],
        'estancia_norma_grd': [4, 3, 5, 2, 6],
        
        # Datos de encuesta social
        'total': [75, 85, 60, 90, 70],
        'habitacional': [1, 1, 0, 1, 1],
        'socioeconomica': [1, 1, 0, 1, 1],
        'salud_mental': [1, 1, 0, 1, 1],
        'redes': [1, 1, 0, 1, 1],
        'cuidador': [1, 1, 0, 1, 1],
        
        # Datos adicionales necesarios
        'ir_grd': ['051401 - PROCEDIMIENTO CARDIACO', '061203 - PROCEDIMIENTO DIGESTIVO', 
                  '174121 - RADIOTERAPIA', '081601 - PROCEDIMIENTO MUSCULOESQUELÉTICO', 
                  '104132 - TRASTORNO ENDOCRINO'],
        'ir_tipo_grd': ['M', 'Q', 'M', 'Q', 'M'],
        'ir_grd_codigo_': [51401, 61203, 174121, 81601, 104132],
        'proced_01_principal_cod_': [0, 4651, 9228, 8363, 0],
        'pregunta': [75, 85, 60, 90, 70],
        'pregunta2': [80, 85, 65, 90, 75],
        'pregunta3': [85, 90, 70, 95, 80],
        'pregunta4': [70, 80, 55, 85, 65]
    }
    
    return pd.DataFrame(data)

def test_flexible_prediction():
    """Prueba la predicción flexible"""
    print("🧪 PROBANDO PREDICCIÓN FLEXIBLE")
    print("=" * 50)
    
    try:
        # Crear datos mínimos
        print("📊 Creando datos con columnas importantes...")
        df_minimal = create_minimal_data()
        
        print(f"   - Registros: {len(df_minimal)}")
        print(f"   - Columnas: {len(df_minimal.columns)}")
        print(f"   - Columnas incluidas: {list(df_minimal.columns)}")
        
        # Guardar datos de prueba
        test_file = "datos_minimos_test.csv"
        df_minimal.to_csv(test_file, index=False)
        print(f"   - Datos guardados en: {test_file}")
        
        # Ejecutar predicción flexible
        print("\n🔮 Ejecutando predicción flexible...")
        import subprocess
        result = subprocess.run([
            'python', '-m', 'src.predict_flexible', 
            '--config', 'config.yaml',
            '--input', test_file,
            '--output', 'predicciones_flexibles_test.csv'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ ¡PREDICCIÓN FLEXIBLE EXITOSA!")
            print(result.stdout)
            
            # Cargar y mostrar resultados
            df_results = pd.read_csv('predicciones_flexibles_test.csv')
            print(f"\n📈 RESULTADOS:")
            print(f"   - Total de pacientes: {len(df_results)}")
            print(f"   - Probabilidad promedio: {df_results['p_excede_norma'].mean():.3f}")
            
            # Mostrar distribución de riesgo
            risk_dist = df_results['riesgo_categoria'].value_counts()
            print(f"\n🎯 DISTRIBUCIÓN DE RIESGO:")
            for categoria, count in risk_dist.items():
                percentage = (count / len(df_results)) * 100
                print(f"   - {categoria}: {count} pacientes ({percentage:.1f}%)")
            
            # Mostrar casos individuales
            print(f"\n📋 CASOS INDIVIDUALES:")
            for idx, row in df_results.iterrows():
                edad = row['edad_en_anos']
                sexo = row['sexo_desc_']
                servicio = row['servicio_ingreso_descripcion_']
                prob = row['p_excede_norma']
                riesgo = row['riesgo_categoria']
                print(f"   {idx+1}. Edad: {edad} | Sexo: {sexo} | Servicio: {servicio} | Prob: {prob:.3f} ({riesgo})")
            
            return True
            
        else:
            print("❌ Error en la predicción:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_flexible_prediction()
    
    if success:
        print(f"\n✅ ¡PRUEBA EXITOSA!")
        print(f"   - El modelo ahora funciona con solo las columnas importantes")
        print(f"   - Se completan automáticamente las columnas faltantes")
        print(f"   - Revisa 'predicciones_flexibles_test.csv' para ver los resultados")
    else:
        print(f"\n❌ La prueba falló. Revisa los errores arriba.")


