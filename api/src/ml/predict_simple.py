#!/usr/bin/env python3
"""
Script simplificado para predicción de exceso de estadía
Solo requiere las columnas más importantes
"""
import pandas as pd
import sys
import os
sys.path.append('src')

from utils import read_excel_or_csv, coerce_dtypes, categorize_probabilities, align_columns_to_template
from joblib import load

def create_complete_template():
    """Crea un template completo con valores por defecto para todas las columnas necesarias"""
    
    # Valores por defecto para todas las columnas necesarias
    template_completo = {
        # Columnas numéricas
        'estancia_norma_grd': 4,
        'edad_en_anos': 65,
        'ir_grd_codigo_': 51401,
        'proced_01_principal_cod_': 0,
        'pregunta': 75,
        'pregunta2': 80,
        'pregunta3': 85,
        'pregunta4': 70,
        'numerodetelefonoocontactodelfamiliar': 0,
        'habitacional': 1,
        'socioeconomica': 1,
        'salud_mental': 1,
        'redes': 1,
        'cuidador': 1,
        'presencia_de_patologia_neurocognitiva': 0,
        'que_tipo_de_cuidado_requiere_el_paciente': 0,
        'el_la_paciente_producto_de_la_hospitalizacion_actual_presentara_alguna_secuela_que_afecte_su_independencia': 0,
        'total': 75,
        'gestion': 0,
        'categorizacion_de_gestion': 0,
        'fecha_intervencion': 0,
        'registro_en_trakecare': 0,
        'edad': 65,
        'dias_estadia': 0,
        
        # Columnas categóricas
        'tipo_ingreso_descripcion_': 'Programado',
        'ir_grd': '051401 - PROCEDIMIENTO CARDIACO',
        'diagnostico_principal': 'I25.1',
        'ir_tipo_grd': 'M',
        'prevision_desc_': 'FONASA',
        'servicio_ingreso_descripcion_': 'Medicina',
        'sexo_desc_': 'Hombre',
        'dia_habil_inhabil': 'Hábil',
        'rut_pasaporte': '12345678-9',
        'direccion_del_paciente': 'Dirección no especificada',
        'cuenta_con_registro_social_de_hogares_': 'No',
        'cual_es_el_porcentaje_otorgado_de_acuerdo_el_registro_social_de_hogares_': 'S/I',
        'que_actividad_realizada_': 'No especificado',
        'persona_en_situacion_de_discapacidad': 'No',
        'atencion_en_salud_primaria_cesfam_o_consultorio_': 'No',
        'nombre_del_cesfam_o_consultorio': 'No especificado',
        'nombre_del_tutor_familiar_otro_quien_se_hara_cargo_del_cuidado_del_la_paciente': 'No especificado',
        'relacion_o_parentesco_con_el_la_paciente': 'No especificado',
        'direccion_del_domicilio_al_alta_del_la_paciente': 'Misma dirección',
        'situacion_habitabilidad_': 'Condiciones adecuadas',
        'situacion_economica_': 'Condición económica permite satisfacer necesidades básicas',
        'consumo_de_drogas_salud_mental': 'Ausencia de patología psiquiátrica y/o adicciones',
        'red_familiar': 'Cuenta con redes familiares o sociales suficientes',
        'cuidador_al_alta': 'Disponibilidad de cuidador con capacidad de hacerse cargo',
        'correo_electronico2': 'no@especificado.com',
        'buscar_episodio_con_asignacion_encuesta': 'ASIGNADO',
        'nivel_de_dependencia': 5,
        'aseguradora': 'FONASA',
        'prevision_homologa': 'Fonasa',
        'tipo_de_aseguradora2': 'Fonasa',
        'marca1': '',
        'marca2': '',
        'marca3': '',
        'fe_alta': '',
        'fecha_de_nacimiento': '1950-01-01',
        'grupo_etario': 'Adulto',
        'fecha_adm_': '2024-01-01',
        'fecha_asignacion': '2024-01-01'
    }
    
    return template_completo

def complete_missing_columns(df_input, template_completo):
    """Completa las columnas faltantes con valores por defecto"""
    
    df_complete = align_columns_to_template(df_input.copy(), template_completo.keys())
    
    # Agregar columnas faltantes con valores por defecto
    for col, default_value in template_completo.items():
        if col not in df_complete.columns:
            df_complete[col] = default_value
        else:
            df_complete[col] = df_complete[col].fillna(default_value)
    
    # Mantener columnas originales y añadir las nuevas al final
    ordered_cols = list(df_input.columns)
    for col in template_completo.keys():
        if col not in ordered_cols:
            ordered_cols.append(col)
    
    df_complete = df_complete.reindex(columns=ordered_cols)
    
    return df_complete

def predict_with_minimal_data(input_file, output_file="predicciones.csv"):
    """
    Hace predicciones con solo las columnas más importantes
    
    Args:
        input_file: Archivo CSV con las columnas importantes
        output_file: Archivo de salida con las predicciones
    """
    
    print("🏥 PREDICCIÓN DE EXCESO DE ESTADÍA - VERSIÓN FLEXIBLE")
    print("=" * 60)
    
    try:
        # Cargar modelo
        model_path = "models/model_hgb_calibrated.joblib"
        if not os.path.exists(model_path):
            model_path = "models/model_baseline.joblib"
        
        print(f"📦 Cargando modelo: {model_path}")
        model = load(model_path)
        
        # Cargar datos de entrada
        print(f"📊 Cargando datos: {input_file}")
        df_input = pd.read_csv(input_file)
        
        print(f"   - Registros: {len(df_input)}")
        print(f"   - Columnas proporcionadas: {len(df_input.columns)}")
        
        # Mostrar columnas proporcionadas
        print(f"   - Columnas incluidas: {list(df_input.columns)}")
        
        # Crear template completo
        template_completo = create_complete_template()
        
        # Completar columnas faltantes
        print("🔧 Completando columnas faltantes...")
        df_complete = complete_missing_columns(df_input, template_completo)
        
        # Coerción de tipos
        df_complete, _, _ = coerce_dtypes(df_complete)
        
        # Hacer predicciones
        print("🔮 Generando predicciones...")
        probabilities = model.predict_proba(df_complete)[:, 1]
        
        # Crear resultados
        df_results = df_input.copy()
        df_results['probabilidad_exceso'] = probabilities
        df_results['riesgo_categoria'] = categorize_probabilities(probabilities)
        
        # Guardar resultados
        df_results.to_csv(output_file, index=False)
        
        # Mostrar estadísticas
        print(f"\n📈 RESULTADOS:")
        print(f"   - Total de pacientes: {len(df_results)}")
        print(f"   - Probabilidad promedio: {probabilities.mean():.3f}")
        print(f"   - Probabilidad máxima: {probabilities.max():.3f}")
        print(f"   - Probabilidad mínima: {probabilities.min():.3f}")
        
        # Distribución de riesgo
        risk_dist = df_results['riesgo_categoria'].value_counts()
        print(f"\n🎯 DISTRIBUCIÓN DE RIESGO:")
        for categoria, count in risk_dist.items():
            percentage = (count / len(df_results)) * 100
            print(f"   - {categoria}: {count} pacientes ({percentage:.1f}%)")
        
        # Casos de alto riesgo
        alto_riesgo = df_results[df_results['riesgo_categoria'] == 'Alta']
        if len(alto_riesgo) > 0:
            print(f"\n⚠️  PACIENTES DE ALTO RIESGO ({len(alto_riesgo)}):")
            for idx, row in alto_riesgo.iterrows():
                edad = row.get('edad_en_anos', 'N/A')
                sexo = row.get('sexo_desc_', 'N/A')
                prob = row['probabilidad_exceso']
                print(f"   - Paciente {idx+1}: {prob:.3f} | Edad: {edad} | Sexo: {sexo}")
        
        # Recomendaciones
        print(f"\n💡 RECOMENDACIONES:")
        alto_riesgo_count = len(alto_riesgo)
        medio_riesgo_count = len(df_results[df_results['riesgo_categoria'] == 'Media'])
        bajo_riesgo_count = len(df_results[df_results['riesgo_categoria'] == 'Baja'])
        
        if alto_riesgo_count > 0:
            print(f"   🚨 {alto_riesgo_count} pacientes requieren intervención inmediata")
        if medio_riesgo_count > 0:
            print(f"   ⚠️  {medio_riesgo_count} pacientes necesitan monitoreo intensivo")
        if bajo_riesgo_count > 0:
            print(f"   ✅ {bajo_riesgo_count} pacientes tienen riesgo bajo")
        
        print(f"\n💾 Resultados guardados en: {output_file}")
        return df_results
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def create_example_file():
    """Crea un archivo de ejemplo con las columnas mínimas necesarias"""
    
    # Datos de ejemplo
    data = {
        'edad_en_anos': [65, 45, 78, 32, 55],
        'sexo_desc_': ['Hombre', 'Mujer', 'Hombre', 'Mujer', 'Hombre'],
        'tipo_ingreso_descripcion_': ['Programado', 'Urgente', 'Programado', 'Urgente', 'Programado'],
        'servicio_ingreso_descripcion_': ['Medicina', 'Cirugía', 'Medicina', 'Pediatría', 'Cardiología'],
        'prevision_desc_': ['FONASA', 'ISAPRE', 'FONASA', 'FONASA', 'ISAPRE'],
        'diagnostico_principal': ['I25.1', 'K80.2', 'J44.1', 'A09', 'I21.9'],
        'estancia_norma_grd': [4, 3, 5, 2, 6],
        'total': [75, 85, 60, 90, 70],
        'habitacional': [1, 1, 0, 1, 1],
        'socioeconomica': [1, 1, 0, 1, 1],
        'salud_mental': [1, 1, 0, 1, 1],
        'redes': [1, 1, 0, 1, 1],
        'cuidador': [1, 1, 0, 1, 1]
    }
    
    df_example = pd.DataFrame(data)
    df_example.to_csv('ejemplo_datos_minimos.csv', index=False)
    print("📄 Archivo de ejemplo creado: ejemplo_datos_minimos.csv")
    print("   - Contiene solo las columnas más importantes")
    print("   - Puedes usarlo como template para tus datos")
    
    return df_example

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Predicción de exceso de estadía - Versión flexible")
    parser.add_argument("--input", type=str, help="Archivo CSV con datos de entrada")
    parser.add_argument("--output", type=str, default="predicciones.csv", help="Archivo de salida")
    parser.add_argument("--ejemplo", action="store_true", help="Crear archivo de ejemplo")
    
    args = parser.parse_args()
    
    if args.ejemplo:
        create_example_file()
    elif args.input:
        predict_with_minimal_data(args.input, args.output)
    else:
        print("❌ Debes proporcionar un archivo de entrada o usar --ejemplo")
        print("   Ejemplo: python predict_simple.py --input mi_archivo.csv")
        print("   Ejemplo: python predict_simple.py --ejemplo")
