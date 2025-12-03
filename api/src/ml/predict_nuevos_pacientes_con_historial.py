#!/usr/bin/env python3
"""
Sistema de predicción de exceso de estadía para pacientes nuevos
Versión con historial - NO sobrescribe archivos anteriores
"""
import pandas as pd
import sys
import os
from datetime import datetime
sys.path.append('src')

from utils import (
    read_excel_or_csv,
    coerce_dtypes,
    standardize_col,
    categorize_probabilities,
    align_columns_to_template
)
from joblib import load

def predict_nuevos_pacientes_con_historial():
    """
    Predice exceso de estadía para pacientes nuevos
    Genera archivos con timestamp para conservar historial
    """
    
    print("🏥 SISTEMA DE PREDICCIÓN PARA PACIENTES NUEVOS (CON HISTORIAL)")
    print("=" * 70)
    
    # Verificar que existe la carpeta
    carpeta_nuevos = "nuevos_pacientes"
    if not os.path.exists(carpeta_nuevos):
        os.makedirs(carpeta_nuevos)
        print(f"📁 Carpeta creada: {carpeta_nuevos}/")
    
    # Rutas de archivos
    grd_file = os.path.join(carpeta_nuevos, "GRD.xlsx")
    score_file = os.path.join(carpeta_nuevos, "Score.xlsx")
    
    # Generar nombre de archivo con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(carpeta_nuevos, f"predicciones_{timestamp}.csv")
    
    print(f"📂 Buscando archivos en: {carpeta_nuevos}/")
    print(f"   - GRD: {grd_file}")
    print(f"   - Score: {score_file}")
    print(f"   - Salida: {output_file}")
    
    # Verificar que existen los archivos
    if not os.path.exists(grd_file):
        print(f"❌ No se encontró: {grd_file}")
        print(f"   Coloca tu archivo GRD.xlsx en la carpeta {carpeta_nuevos}/")
        return None
    
    if not os.path.exists(score_file):
        print(f"❌ No se encontró: {score_file}")
        print(f"   Coloca tu archivo Score.xlsx en la carpeta {carpeta_nuevos}/")
        return None
    
    try:
        # Cargar modelo
        model_path = "models/model_hgb_calibrated.joblib"
        if not os.path.exists(model_path):
            model_path = "models/model_baseline.joblib"
        
        print(f"\n📦 Cargando modelo: {model_path}")
        model = load(model_path)
        
        # Cargar datos GRD
        print(f"\n📊 Cargando datos GRD...")
        df_grd = read_excel_or_csv(grd_file)
        print(f"   - Registros GRD: {len(df_grd)}")
        print(f"   - Columnas GRD: {len(df_grd.columns)}")
        
        # Cargar datos Score
        print(f"\n📊 Cargando datos Score...")
        df_score = read_excel_or_csv(score_file)
        print(f"   - Registros Score: {len(df_score)}")
        print(f"   - Columnas Score: {len(df_score.columns)}")
        
        # Buscar columnas de unión
        print(f"\n🔗 BUSCANDO COLUMNAS DE UNIÓN...")
        
        # Buscar ID de episodio en GRD
        grd_id_candidates = ['episodio_cmbd', 'Episodio CMBD', 'episodio', 'id_episodio', 'ID']
        grd_id_col = None
        for col in grd_id_candidates:
            if col in df_grd.columns:
                grd_id_col = col
                break
        
        if not grd_id_col:
            print(f"   - ⚠️  No se encontró ID de episodio en GRD")
            print(f"   - Columnas disponibles: {list(df_grd.columns)}")
            return None
        
        print(f"   - ID GRD encontrado: '{grd_id_col}'")
        
        # Buscar ID de episodio en Score
        score_id_candidates = ['episodio', 'buscar_episodio_con_asignacion_encuesta', 'id_episodio', 'ID']
        score_id_col = None
        for col in score_id_candidates:
            if col in df_score.columns:
                score_id_col = col
                break
        
        if not score_id_col:
            print(f"   - ⚠️  No se encontró ID de episodio en Score")
            print(f"   - Columnas disponibles: {list(df_score.columns)}")
            return None
        
        print(f"   - ID Score encontrado: '{score_id_col}'")
        
        # Hacer merge de los datos
        print(f"\n🔗 UNIENDO DATOS GRD Y SCORE...")
        df_merged = df_grd.merge(df_score, left_on=grd_id_col, right_on=score_id_col, how='left', suffixes=('', '_score'))
        print(f"   - Registros después del merge: {len(df_merged)}")
        
        if len(df_merged) == 0:
            print(f"   - ❌ No se encontraron coincidencias entre GRD y Score")
            return None
        
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
        
        # Crear resultados con timestamp
        df_results = pd.DataFrame({
            'fecha_prediccion': [timestamp] * len(df_merged),
            'id_episodio': df_merged[grd_id_col].values,
            'probabilidad_exceso': probabilities,
            'riesgo_categoria': categorize_probabilities(probabilities)
        })
        
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
        
        # Mostrar resultados detallados
        print(f"\n📋 RESULTADOS DETALLADOS:")
        print(f"{'ID Episodio':<15} {'Probabilidad':<12} {'Riesgo':<8}")
        print("-" * 40)
        for _, row in df_results.iterrows():
            print(f"{row['id_episodio']:<15} {row['probabilidad_exceso']:<12.3f} {row['riesgo_categoria']:<8}")
        
        # Casos de alto riesgo
        alto_riesgo = df_results[df_results['riesgo_categoria'] == 'Alta']
        if len(alto_riesgo) > 0:
            print(f"\n⚠️  PACIENTES DE ALTO RIESGO ({len(alto_riesgo)}):")
            for _, row in alto_riesgo.iterrows():
                print(f"   - ID {row['id_episodio']}: {row['probabilidad_exceso']:.3f} ({row['probabilidad_exceso']*100:.1f}%)")
        
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
        
        # Mostrar historial de archivos
        print(f"\n📚 HISTORIAL DE PREDICCIONES:")
        archivos_predicciones = [f for f in os.listdir(carpeta_nuevos) if f.startswith('predicciones_') and f.endswith('.csv')]
        archivos_predicciones.sort(reverse=True)  # Más recientes primero
        
        for i, archivo in enumerate(archivos_predicciones[:5], 1):  # Mostrar últimos 5
            ruta_archivo = os.path.join(carpeta_nuevos, archivo)
            timestamp_archivo = archivo.replace('predicciones_', '').replace('.csv', '')
            fecha_legible = datetime.strptime(timestamp_archivo, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
            print(f"   {i}. {archivo} ({fecha_legible})")
        
        if len(archivos_predicciones) > 5:
            print(f"   ... y {len(archivos_predicciones) - 5} archivos más")
        
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
    
    parser = argparse.ArgumentParser(description="Sistema de predicción para pacientes nuevos (con historial)")
    parser.add_argument("--predecir", action="store_true", help="Ejecutar predicción con historial")
    
    args = parser.parse_args()
    
    if args.predecir:
        result = predict_nuevos_pacientes_con_historial()
        if result is not None:
            print(f"\n✅ ¡PREDICCIÓN COMPLETADA EXITOSAMENTE!")
            print(f"   - Archivo guardado con timestamp")
            print(f"   - Historial de predicciones conservado")
        else:
            print(f"\n❌ La predicción falló.")
    else:
        print("🏥 SISTEMA DE PREDICCIÓN PARA PACIENTES NUEVOS (CON HISTORIAL)")
        print("=" * 70)
        print("📋 INSTRUCCIONES:")
        print("   1. Coloca tus archivos GRD.xlsx y Score.xlsx en la carpeta 'nuevos_pacientes/'")
        print("   2. Ejecuta: python predict_nuevos_pacientes_con_historial.py --predecir")
        print("   3. Los resultados se guardan con timestamp (no se sobrescriben)")
        print()
        print("💡 VENTAJAS:")
        print("   - Conserva historial de todas las predicciones")
        print("   - Archivos con timestamp: predicciones_YYYYMMDD_HHMMSS.csv")
        print("   - Puedes comparar resultados de diferentes ejecuciones")
