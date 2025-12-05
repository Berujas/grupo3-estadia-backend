#!/usr/bin/env python3
"""
Ejemplo de uso del sistema de predicción para pacientes nuevos
"""
import pandas as pd
import numpy as np

def crear_datos_ejemplo():
    """Crea datos de ejemplo para simular pacientes nuevos"""
    
    print("📝 CREANDO DATOS DE EJEMPLO PARA PACIENTES NUEVOS")
    print("=" * 60)
    
    # Datos GRD de ejemplo (pacientes que acaban de llegar)
    grd_data = {
        'Episodio CMBD': [1001, 1002, 1003, 1004, 1005],
        'Edad en años': [65, 45, 78, 32, 55],
        'Sexo  (Desc)': ['Hombre', 'Mujer', 'Hombre', 'Mujer', 'Hombre'],
        'Tipo Ingreso (Descripción)': ['Programado', 'Urgente', 'Programado', 'Urgente', 'Programado'],
        'Servicio Ingreso (Descripción)': ['Medicina', 'Cirugía', 'Medicina', 'Pediatría', 'Cardiología'],
        'Previsión (Desc)': ['FONASA', 'ISAPRE', 'FONASA', 'FONASA', 'ISAPRE'],
        'Diagnóstico Principal': ['I25.1', 'K80.2', 'J44.1', 'A09', 'I21.9'],
        'Estancia Norma GRD ': [4, 3, 5, 2, 6],
        'IR GRD': [1.2, 1.5, 0.8, 2.1, 1.3],
        'IR Tipo GRD': ['M', 'Q', 'M', 'Q', 'M'],
        'IR GRD Código': [51401, 61203, 174121, 81601, 104132],
        'Proced 01 Principal (Cod)': [0, 4651, 9228, 8363, 0]
    }
    
    # Datos Score de ejemplo (encuestas sociales)
    score_data = {
        'episodio': [1001, 1002, 1003, 1004, 1005],
        'total': [75, 85, 60, 90, 70],
        'habitacional': [1, 1, 0, 1, 1],
        'socioeconomica': [1, 1, 0, 1, 1],
        'salud_mental': [1, 1, 0, 1, 1],
        'redes': [1, 1, 0, 1, 1],
        'cuidador': [1, 1, 0, 1, 1],
        'pregunta': [75, 85, 60, 90, 70],
        'pregunta2': [80, 85, 65, 90, 75],
        'pregunta3': [85, 90, 70, 95, 80],
        'pregunta4': [70, 80, 55, 85, 65],
        'situacion_habitabilidad_': ['Condiciones adecuadas', 'Condiciones adecuadas', 
                                    'Condiciones inadecuadas', 'Condiciones adecuadas', 'Condiciones adecuadas'],
        'situacion_economica_': ['Condición económica permite satisfacer necesidades básicas',
                               'Condición económica permite satisfacer necesidades básicas',
                               'Condición económica limitada',
                               'Condición económica permite satisfacer necesidades básicas',
                               'Condición económica permite satisfacer necesidades básicas'],
        'red_familiar': ['Cuenta con redes familiares o sociales suficientes',
                        'Cuenta con redes familiares o sociales suficientes',
                        'Redes familiares limitadas',
                        'Cuenta con redes familiares o sociales suficientes',
                        'Cuenta con redes familiares o sociales suficientes'],
        'cuidador_al_alta': ['Disponibilidad de cuidador con capacidad de hacerse cargo',
                            'Disponibilidad de cuidador con capacidad de hacerse cargo',
                            'Sin cuidador disponible',
                            'Disponibilidad de cuidador con capacidad de hacerse cargo',
                            'Disponibilidad de cuidador con capacidad de hacerse cargo']
    }
    
    # Crear DataFrames
    df_grd = pd.DataFrame(grd_data)
    df_score = pd.DataFrame(score_data)
    
    # Guardar archivos
    df_grd.to_excel('nuevos_pacientes_grd.xlsx', index=False)
    df_score.to_excel('nuevos_pacientes_score.xlsx', index=False)
    
    print(f"✅ Archivos de ejemplo creados:")
    print(f"   - nuevos_pacientes_grd.xlsx ({len(df_grd)} pacientes)")
    print(f"   - nuevos_pacientes_score.xlsx ({len(df_score)} pacientes)")
    
    print(f"\n📋 DATOS DE LOS PACIENTES:")
    for i in range(len(df_grd)):
        print(f"   Paciente {i+1}: {df_grd.iloc[i]['Edad en años']} años, {df_grd.iloc[i]['Sexo  (Desc)']}, {df_grd.iloc[i]['Servicio Ingreso (Descripción)']}")
    
    return df_grd, df_score

def mostrar_instrucciones():
    """Muestra las instrucciones de uso"""
    
    print("📋 INSTRUCCIONES PARA USAR EL SISTEMA")
    print("=" * 60)
    print()
    print("🔧 PREPARACIÓN DE TUS DATOS:")
    print("   1. Archivo GRD debe contener:")
    print("      - Columna de ID de episodio (ej: 'Episodio CMBD', 'episodio_cmbd')")
    print("      - Datos demográficos: edad, sexo, servicio, diagnóstico")
    print("      - Estancia normativa (sin estancia real)")
    print()
    print("   2. Archivo Score debe contener:")
    print("      - Columna de ID de episodio que coincida con GRD")
    print("      - Datos de encuesta social: total, habitacional, socioeconomica, etc.")
    print()
    print("🚀 COMANDO PARA EJECUTAR:")
    print("   python predict_new_patients.py --grd tu_archivo_grd.xlsx --score tu_archivo_score.xlsx")
    print()
    print("📊 RESULTADOS:")
    print("   - Archivo CSV con probabilidades de exceso para cada paciente")
    print("   - Categorización de riesgo: Baja, Media, Alta")
    print("   - Recomendaciones de intervención")
    print()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ejemplo de uso del sistema de predicción")
    parser.add_argument("--crear-ejemplo", action="store_true", help="Crear datos de ejemplo")
    parser.add_argument("--instrucciones", action="store_true", help="Mostrar instrucciones")
    parser.add_argument("--probar", action="store_true", help="Probar con datos de ejemplo")
    
    args = parser.parse_args()
    
    if args.crear_ejemplo:
        crear_datos_ejemplo()
    elif args.instrucciones:
        mostrar_instrucciones()
    elif args.probar:
        print("🧪 PROBANDO CON DATOS DE EJEMPLO")
        print("=" * 40)
        
        # Crear datos de ejemplo
        df_grd, df_score = crear_datos_ejemplo()
        
        # Ejecutar predicción
        import subprocess
        result = subprocess.run([
            'python', 'predict_new_patients.py',
            '--grd', 'nuevos_pacientes_grd.xlsx',
            '--score', 'nuevos_pacientes_score.xlsx',
            '--output', 'predicciones_ejemplo.csv'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ ¡PRUEBA EXITOSA!")
            print(result.stdout)
        else:
            print("❌ Error en la prueba:")
            print(result.stderr)
    else:
        print("❌ Debes especificar una opción:")
        print("   --crear-ejemplo: Crear datos de ejemplo")
        print("   --instrucciones: Mostrar instrucciones de uso")
        print("   --probar: Probar el sistema con datos de ejemplo")

