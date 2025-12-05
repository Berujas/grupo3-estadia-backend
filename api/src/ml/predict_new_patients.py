#!/usr/bin/env python3
"""
Script para predecir exceso de estadía en pacientes nuevos
Simula el escenario real: pacientes que acaban de llegar a la clínica
"""
import pandas as pd
import sys
import os
sys.path.append('src')

from utils import (
    read_excel_or_csv,
    coerce_dtypes,
    standardize_col,
    categorize_probabilities,
    align_columns_to_template
)
from joblib import load

def process_new_patients(grd_file, score_file, output_file="predicciones_nuevos_pacientes.csv"):
    """
    Procesa pacientes nuevos (sin datos de estancia real) y hace predicciones
    
    Args:
        grd_file: Archivo Excel/CSV con datos GRD de pacientes nuevos
        score_file: Archivo Excel/CSV con datos Score de pacientes nuevos  
        output_file: Archivo de salida con las predicciones
    """
    
    print("🏥 PREDICCIÓN DE EXCESO DE ESTADÍA - PACIENTES NUEVOS")
    print("=" * 60)
    
    try:
        # Cargar modelo
        model_path = "models/model_hgb_calibrated.joblib"
        if not os.path.exists(model_path):
            model_path = "models/model_baseline.joblib"
        
        print(f"📦 Cargando modelo: {model_path}")
        model = load(model_path)
        
        # Cargar datos GRD
        print(f"\n📊 Cargando datos GRD: {grd_file}")
        df_grd = read_excel_or_csv(grd_file)
        print(f"   - Registros GRD: {len(df_grd)}")
        print(f"   - Columnas GRD: {len(df_grd.columns)}")
        
        # Cargar datos Score
        print(f"\n📊 Cargando datos Score: {score_file}")
        df_score = read_excel_or_csv(score_file)
        print(f"   - Registros Score: {len(df_score)}")
        print(f"   - Columnas Score: {len(df_score.columns)}")
        
        # Mostrar columnas disponibles
        print(f"\n🔍 COLUMNAS DISPONIBLES:")
        print(f"   - GRD: {list(df_grd.columns[:5])}... (primeras 5)")
        print(f"   - Score: {list(df_score.columns[:5])}... (primeras 5)")
        
        # Buscar columnas de unión
        print(f"\n🔗 BUSCANDO COLUMNAS DE UNIÓN:")
        
        # Buscar ID de episodio en GRD
        grd_id_candidates = ['episodio_cmbd', 'Episodio CMBD', 'episodio', 'id_episodio']
        grd_id_col = None
        for col in grd_id_candidates:
            if col in df_grd.columns:
                grd_id_col = col
                break
        
        if grd_id_col:
            print(f"   - ID GRD encontrado: '{grd_id_col}'")
        else:
            print(f"   - ⚠️  No se encontró ID de episodio en GRD")
            print(f"   - Columnas disponibles: {list(df_grd.columns)}")
            return None
        
        # Buscar ID de episodio en Score
        score_id_candidates = ['episodio', 'buscar_episodio_con_asignacion_encuesta', 'id_episodio']
        score_id_col = None
        for col in score_id_candidates:
            if col in df_score.columns:
                score_id_col = col
                break
        
        if score_id_col:
            print(f"   - ID Score encontrado: '{score_id_col}'")
        else:
            print(f"   - ⚠️  No se encontró ID de episodio en Score")
            print(f"   - Columnas disponibles: {list(df_score.columns)}")
            return None
        
        # Hacer merge de los datos
        print(f"\n🔗 UNIENDO DATOS GRD Y SCORE...")
        df_merged = df_grd.merge(df_score, left_on=grd_id_col, right_on=score_id_col, how='left', suffixes=('', '_score'))
        print(f"   - Registros después del merge: {len(df_merged)}")
        
        # Estandarizar nombres de columnas
        print(f"\n🔧 ESTANDARIZANDO NOMBRES DE COLUMNAS...")
        df_merged.columns = [standardize_col(col) for col in df_merged.columns]
        
        # Crear template completo con valores por defecto
        template_completo = create_complete_template()
        
        # Completar columnas faltantes
        print(f"🔧 COMPLETANDO COLUMNAS FALTANTES...")
        df_complete = complete_missing_columns(df_merged, template_completo)
        
        # Coerción de tipos
        df_complete, _, _ = coerce_dtypes(df_complete)
        
        # Hacer predicciones
        print(f"\n🔮 GENERANDO PREDICCIONES...")
        probabilities = model.predict_proba(df_complete)[:, 1]
        
        # Crear resultados
        df_results = df_merged.copy()
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
            for idx, row in alto_riesgo.head(10).iterrows():
                edad = row.get('edad_en_anos', 'N/A')
                sexo = row.get('sexo_desc_', 'N/A')
                servicio = row.get('servicio_ingreso_descripcion_', 'N/A')
                prob = row['probabilidad_exceso']
                print(f"   - Paciente {idx+1}: {prob:.3f} | Edad: {edad} | Sexo: {sexo} | Servicio: {servicio}")
        
        # Recomendaciones
        print(f"\n💡 RECOMENDACIONES:")
        alto_riesgo_count = len(alto_riesgo)
        medio_riesgo_count = len(df_results[df_results['riesgo_categoria'] == 'Media'])
        bajo_riesgo_count = len(df_results[df_results['riesgo_categoria'] == 'Baja'])
        
        if alto_riesgo_count > 0:
            print(f"   🚨 {alto_riesgo_count} pacientes requieren intervención inmediata")
            print(f"      - Asignar trabajo social prioritario")
            print(f"      - Revisar protocolos de alta temprana")
        if medio_riesgo_count > 0:
            print(f"   ⚠️  {medio_riesgo_count} pacientes necesitan monitoreo intensivo")
            print(f"      - Seguimiento diario recomendado")
        if bajo_riesgo_count > 0:
            print(f"   ✅ {bajo_riesgo_count} pacientes tienen riesgo bajo")
            print(f"      - Seguimiento normal")
        
        print(f"\n💾 Resultados guardados en: {output_file}")
        return df_results
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

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

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Predicción de exceso de estadía para pacientes nuevos")
    parser.add_argument("--grd", type=str, required=True, help="Archivo GRD de pacientes nuevos")
    parser.add_argument("--score", type=str, required=True, help="Archivo Score de pacientes nuevos")
    parser.add_argument("--output", type=str, default="predicciones_nuevos_pacientes.csv", help="Archivo de salida")
    
    args = parser.parse_args()
    
    print("🏥 SISTEMA DE PREDICCIÓN PARA PACIENTES NUEVOS")
    print("=" * 60)
    print("📋 INSTRUCCIONES:")
    print("   1. Asegúrate de que tus archivos GRD y Score tengan columnas de ID de episodio")
    print("   2. Los archivos pueden ser Excel (.xlsx) o CSV (.csv)")
    print("   3. El sistema unirá automáticamente los datos por ID de episodio")
    print("   4. Se completarán automáticamente las columnas faltantes")
    print()
    
    result = process_new_patients(args.grd, args.score, args.output)
    
    if result is not None:
        print(f"\n✅ ¡PREDICCIÓN COMPLETADA EXITOSAMENTE!")
        print(f"   - Revisa el archivo '{args.output}' para ver los resultados")
        print(f"   - Los pacientes de alto riesgo requieren atención inmediata")
    else:
        print(f"\n❌ La predicción falló. Revisa los errores arriba.")
