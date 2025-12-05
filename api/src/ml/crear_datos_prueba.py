#!/usr/bin/env python3
"""
Crea archivos de prueba con datos aleatorios o controlados para probar el sistema.
- Genera archivos en la raíz del proyecto.
- Opcionalmente, deja una copia en la carpeta `nuevos_pacientes/` lista para usar.
"""
import argparse
import os
from datetime import datetime

import numpy as np
import pandas as pd


def guardar_archivos_excel(df_grd, df_score, carpeta, nombre_grd, nombre_score):
    """Guarda dataframes GRD/Score como Excel en la carpeta indicada."""
    os.makedirs(carpeta, exist_ok=True)
    grd_path = os.path.join(carpeta, f"{nombre_grd}.xlsx")
    score_path = os.path.join(carpeta, f"{nombre_score}.xlsx")
    df_grd.to_excel(grd_path, index=False)
    df_score.to_excel(score_path, index=False)
    return grd_path, score_path


def crear_datos_prueba(n_pacientes=10, seed=None):
    """Crea archivos GRD.xlsx y Score.xlsx con datos aleatorios."""
    
    print(f"📝 CREANDO ARCHIVOS DE PRUEBA CON {n_pacientes} FILAS ALEATORIAS")
    print("=" * 60)
    
    if seed is None:
        seed = int(datetime.now().timestamp()) % 1_000_000
    np.random.seed(seed)
    
    # Generar 10 IDs únicos
    ids = [f"TEST{1000+i}" for i in range(1, n_pacientes + 1)]
    
    # Datos GRD de prueba
    print("🔧 Generando datos GRD...")
    
    # Edades aleatorias (18-85 años)
    edades = np.random.randint(18, 86, n_pacientes)
    
    # Sexos aleatorios
    sexos = np.random.choice(['Hombre', 'Mujer'], n_pacientes)
    
    # Tipos de ingreso
    tipos_ingreso = np.random.choice(
        ['Programado', 'Urgente', 'Emergencia'],
        n_pacientes,
        p=[0.6, 0.3, 0.1]
    )
    
    # Servicios aleatorios
    servicios = np.random.choice([
        'Medicina', 'Cirugía', 'Cardiología', 'Neurología', 'Pediatría',
        'Ginecología', 'Traumatología', 'Urología', 'Oftalmología', 'Dermatología'
    ], n_pacientes)
    
    # Previsiones
    previsiones = np.random.choice(
        ['FONASA', 'ISAPRE', 'Particular'],
        n_pacientes,
        p=[0.7, 0.25, 0.05]
    )
    
    # Diagnósticos aleatorios
    diagnosticos = np.random.choice([
        'I25.1', 'K80.2', 'J44.1', 'A09', 'I21.9', 'G93.1', 'M79.3', 'N18.6', 'H25.9', 'L70.9'
    ], n_pacientes)
    
    # Estancias normativas (1-10 días)
    estancias_norma = np.random.uniform(1, 10, n_pacientes).round(2)
    
    # Catálogo IR GRD (código + descripción) basado en casos reales
    ir_grd_catalog = [
        (51401, "051401 - PROCEDIMIENTO CARDIACO"),
        (61203, "061203 - PROCEDIMIENTO DIGESTIVO"),
        (174121, "174121 - RADIOTERAPIA"),
        (81601, "081601 - PROCEDIMIENTO MUSCULOESQUELETICO"),
        (104132, "104132 - TRASTORNOS ENDOCRINOS"),
        (41023, "041023 - PH VENTILACIÓN MECÁNICA PROLONGADA SIN CC"),
        (61201, "061201 - PROCEDIMIENTOS GASTROINTESTINALES"),
        (91501, "091501 - PROCEDIMIENTOS SOBRE MAMA"),
        (121142, "121142 - PROSTATECTOMÍA TRANSURETRAL W/CC"),
        (194163, "194163 - TRASTORNOS ORGÁNICOS W/MCC"),
    ]
    ir_choices = np.random.choice(len(ir_grd_catalog), n_pacientes)
    ir_grd_codigo = [ir_grd_catalog[i][0] for i in ir_choices]
    ir_grd = [ir_grd_catalog[i][1] for i in ir_choices]
    
    # Tipos GRD
    tipos_grd = np.random.choice(['M', 'Q'], n_pacientes, p=[0.7, 0.3])
    
    # Procedimientos
    procedimientos = np.random.choice(
        [0, 4651, 9228, 8363, 9223],
        n_pacientes,
        p=[0.4, 0.2, 0.2, 0.1, 0.1]
    )
    
    # Crear DataFrame GRD
    grd_data = {
        'Episodio CMBD': ids,
        'Edad en años': edades,
        'Sexo  (Desc)': sexos,
        'Tipo Ingreso (Descripción)': tipos_ingreso,
        'Servicio Ingreso (Descripción)': servicios,
        'Previsión (Desc)': previsiones,
        'Diagnóstico Principal': diagnosticos,
        'Estancia Norma GRD ': estancias_norma,
        'IR GRD': ir_grd,
        'IR Tipo GRD': tipos_grd,
        'IR GRD Código': ir_grd_codigo,
        'Proced 01 Principal (Cod)': procedimientos,
        'Dias Estadia': np.zeros(n_pacientes, dtype=int)
    }
    
    df_grd = pd.DataFrame(grd_data)
    
    # Datos Score de prueba
    print("🔧 Generando datos Score...")
    
    # Puntuaciones totales (30-100)
    puntuaciones_totales = np.random.randint(30, 101, n_pacientes)
    
    # Evaluaciones sociales (0 o 1)
    habitacional = np.random.choice([0, 1], n_pacientes, p=[0.3, 0.7])
    socioeconomica = np.random.choice([0, 1], n_pacientes, p=[0.2, 0.8])
    salud_mental = np.random.choice([0, 1], n_pacientes, p=[0.25, 0.75])
    redes = np.random.choice([0, 1], n_pacientes, p=[0.2, 0.8])
    cuidador = np.random.choice([0, 1], n_pacientes, p=[0.3, 0.7])
    
    # Preguntas individuales (basadas en puntuación total)
    pregunta = np.random.randint(30, 101, n_pacientes)
    pregunta2 = np.random.randint(30, 101, n_pacientes)
    pregunta3 = np.random.randint(30, 101, n_pacientes)
    pregunta4 = np.random.randint(30, 101, n_pacientes)
    
    # Crear DataFrame Score
    score_data = {
        'episodio': ids,
        'total': puntuaciones_totales,
        'habitacional': habitacional,
        'socioeconomica': socioeconomica,
        'salud_mental': salud_mental,
        'redes': redes,
        'cuidador': cuidador,
        'pregunta': pregunta,
        'pregunta2': pregunta2,
        'pregunta3': pregunta3,
        'pregunta4': pregunta4
    }
    
    df_score = pd.DataFrame(score_data)
    
    # Guardar archivos en la raíz del proyecto
    grd_file, score_file = guardar_archivos_excel(df_grd, df_score, ".", "GRD_prueba", "Score_prueba")
    
    print(f"✅ Archivos creados en la raíz del proyecto:")
    print(f"   - {grd_file} ({len(df_grd)} pacientes)")
    print(f"   - {score_file} ({len(df_score)} pacientes)")
    
    # Mostrar resumen de datos
    print(f"\n📊 RESUMEN DE DATOS GENERADOS:")
    print(f"   - Total de pacientes: {len(df_grd)}")
    print(f"   - Edades: {df_grd['Edad en años'].min()}-{df_grd['Edad en años'].max()} años")
    print(f"   - Sexos: {df_grd['Sexo  (Desc)'].value_counts().to_dict()}")
    print(f"   - Servicios: {df_grd['Servicio Ingreso (Descripción)'].nunique()} diferentes")
    print(f"   - Puntuaciones Score: {df_score['total'].min()}-{df_score['total'].max()}")
    
    # Mostrar algunos casos de ejemplo
    print(f"\n📋 CASOS DE EJEMPLO:")
    for i in range(min(3, len(df_grd))):
        print(f"   Paciente {i+1}: {df_grd.iloc[i]['Edad en años']} años, {df_grd.iloc[i]['Sexo  (Desc)']}, {df_grd.iloc[i]['Servicio Ingreso (Descripción)']}, Score: {df_score.iloc[i]['total']}")
    
    print(f"\n📁 INSTRUCCIONES:")
    print(f"   1. Los archivos están en la raíz del proyecto")
    print(f"   2. Cópialos a la carpeta 'nuevos_pacientes/'")
    print(f"   3. Renómbralos a 'GRD.xlsx' y 'Score.xlsx'")
    print(f"   4. Ejecuta: python predict_nuevos_pacientes.py --predecir")
    
    return df_grd, df_score


def crear_casos_controlados():
    """Genera 6 pacientes con perfiles Baja/Media/Alta para pruebas dirigidas."""
    ids = [
        "LOW001", "LOW002",
        "MID001", "MID002",
        "HIGH001", "HIGH002"
    ]
    
    grd_rows = [
        # Casos de riesgo bajo (buen puntaje social, estancias cortas)
        {
            'Episodio CMBD': "LOW001",
            'Edad en años': 54,
            'Sexo  (Desc)': 'Mujer',
            'Tipo Ingreso (Descripción)': 'Programado',
            'Servicio Ingreso (Descripción)': 'Medicina',
            'Previsión (Desc)': 'ISAPRE',
            'Diagnóstico Principal': 'I25.1',
            'Estancia Norma GRD ': 3.5,
            'IR GRD': "051401 - PROCEDIMIENTO CARDIACO",
            'IR Tipo GRD': 'M',
            'IR GRD Código': 51401,
            'Proced 01 Principal (Cod)': 0,
            'Dias Estadia': 0
        },
        {
            'Episodio CMBD': "LOW002",
            'Edad en años': 47,
            'Sexo  (Desc)': 'Hombre',
            'Tipo Ingreso (Descripción)': 'Programado',
            'Servicio Ingreso (Descripción)': 'Oftalmología',
            'Previsión (Desc)': 'ISAPRE',
            'Diagnóstico Principal': 'H25.9',
            'Estancia Norma GRD ': 2.0,
            'IR GRD': "091501 - PROCEDIMIENTOS SOBRE MAMA",
            'IR Tipo GRD': 'M',
            'IR GRD Código': 91501,
            'Proced 01 Principal (Cod)': 0,
            'Dias Estadia': 0
        },
        # Casos riesgo medio
        {
            'Episodio CMBD': "MID001",
            'Edad en años': 69,
            'Sexo  (Desc)': 'Hombre',
            'Tipo Ingreso (Descripción)': 'Urgente',
            'Servicio Ingreso (Descripción)': 'Cardiología',
            'Previsión (Desc)': 'FONASA',
            'Diagnóstico Principal': 'I21.9',
            'Estancia Norma GRD ': 6.0,
            'IR GRD': "061203 - PROCEDIMIENTO DIGESTIVO",
            'IR Tipo GRD': 'M',
            'IR GRD Código': 61203,
            'Proced 01 Principal (Cod)': 4651,
            'Dias Estadia': 6
        },
        {
            'Episodio CMBD': "MID002",
            'Edad en años': 58,
            'Sexo  (Desc)': 'Mujer',
            'Tipo Ingreso (Descripción)': 'Urgente',
            'Servicio Ingreso (Descripción)': 'Neurología',
            'Previsión (Desc)': 'FONASA',
            'Diagnóstico Principal': 'G93.1',
            'Estancia Norma GRD ': 6.05,
            'IR GRD': "174121 - RADIOTERAPIA",
            'IR Tipo GRD': 'M',
            'IR GRD Código': 174121,
            'Proced 01 Principal (Cod)': 8363,
            'Dias Estadia': 6
        },
        # Casos riesgo alto
        {
            'Episodio CMBD': "HIGH001",
            'Edad en años': 83,
            'Sexo  (Desc)': 'Mujer',
            'Tipo Ingreso (Descripción)': 'Emergencia',
            'Servicio Ingreso (Descripción)': 'Traumatología',
            'Previsión (Desc)': 'FONASA',
            'Diagnóstico Principal': 'M79.3',
            'Estancia Norma GRD ': 8.5,
            'IR GRD': "081601 - PROCEDIMIENTO MUSCULOESQUELETICO",
            'IR Tipo GRD': 'Q',
            'IR GRD Código': 81601,
            'Proced 01 Principal (Cod)': 9228,
            'Dias Estadia': 45
        },
        {
            'Episodio CMBD': "HIGH002",
            'Edad en años': 76,
            'Sexo  (Desc)': 'Hombre',
            'Tipo Ingreso (Descripción)': 'Emergencia',
            'Servicio Ingreso (Descripción)': 'Neurología',
            'Previsión (Desc)': 'FONASA',
            'Diagnóstico Principal': 'N18.6',
            'Estancia Norma GRD ': 9.0,
            'IR GRD': "041023 - PH VENTILACIÓN MECÁNICA PROLONGADA SIN CC",
            'IR Tipo GRD': 'Q',
            'IR GRD Código': 41023,
            'Proced 01 Principal (Cod)': 9223,
            'Dias Estadia': 50
        },
    ]
    
    df_grd = pd.DataFrame(grd_rows)
    
    score_rows = [
        # Bajo riesgo: puntajes altos
        {
            'episodio': "LOW001",
            'total': 92,
            'habitacional': 1,
            'socioeconomica': 1,
            'salud_mental': 1,
            'redes': 1,
            'cuidador': 1,
            'pregunta': 90,
            'pregunta2': 88,
            'pregunta3': 94,
            'pregunta4': 85
        },
        {
            'episodio': "LOW002",
            'total': 88,
            'habitacional': 1,
            'socioeconomica': 1,
            'salud_mental': 1,
            'redes': 1,
            'cuidador': 1,
            'pregunta': 87,
            'pregunta2': 90,
            'pregunta3': 86,
            'pregunta4': 88
        },
        # Riesgo medio: puntajes mixtos
        {
            'episodio': "MID001",
            'total': 55,
            'habitacional': 1,
            'socioeconomica': 0,
            'salud_mental': 1,
            'redes': 0,
            'cuidador': 1,
            'pregunta': 60,
            'pregunta2': 55,
            'pregunta3': 52,
            'pregunta4': 57
        },
        {
            'episodio': "MID002",
            'total': 48,
            'habitacional': 0,
            'socioeconomica': 1,
            'salud_mental': 0,
            'redes': 1,
            'cuidador': 0,
            'pregunta': 48,
            'pregunta2': 55,
            'pregunta3': 50,
            'pregunta4': 53
        },
        # Riesgo alto: puntajes muy bajos
        {
            'episodio': "HIGH001",
            'total': 12,
            'habitacional': 0,
            'socioeconomica': 0,
            'salud_mental': 0,
            'redes': 0,
            'cuidador': 0,
            'pregunta': 18,
            'pregunta2': 20,
            'pregunta3': 15,
            'pregunta4': 17
        },
        {
            'episodio': "HIGH002",
            'total': 10,
            'habitacional': 0,
            'socioeconomica': 0,
            'salud_mental': 0,
            'redes': 0,
            'cuidador': 0,
            'pregunta': 16,
            'pregunta2': 18,
            'pregunta3': 12,
            'pregunta4': 14
        },
    ]
    
    df_score = pd.DataFrame(score_rows)
    return df_grd, df_score

def main():
    parser = argparse.ArgumentParser(
        description="Genera archivos GRD/Score de prueba para pacientes nuevos."
    )
    parser.add_argument(
        "--n",
        type=int,
        default=10,
        help="Número de pacientes aleatorios a generar (default: 10)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Semilla para la generación aleatoria (default: usa timestamp)"
    )
    parser.add_argument(
        "--dest",
        type=str,
        default="nuevos_pacientes",
        help="Carpeta donde dejar copias listas para probar (default: nuevos_pacientes)"
    )
    parser.add_argument(
        "--sin-controlados",
        action="store_true",
        help="No genera el set con casos controlados (bajo/medio/alto)."
    )
    parser.add_argument(
        "--sin-copia",
        action="store_true",
        help="No deja una copia adicional en la carpeta indicada por --dest."
    )
    
    args = parser.parse_args()
    
    df_grd, df_score = crear_datos_prueba(n_pacientes=args.n, seed=args.seed)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not args.sin_copia:
        dest_grd, dest_score = guardar_archivos_excel(
            df_grd,
            df_score,
            args.dest,
            f"GRD_random_{timestamp}",
            f"Score_random_{timestamp}"
        )
        print(f"\n📁 Copia lista para usar en '{args.dest}/':")
        print(f"   - {dest_grd}")
        print(f"   - {dest_score}")
        print("   ➜ Puedes renombrarlos a GRD.xlsx / Score.xlsx para probar de inmediato.")
    
    if not args.sin_controlados:
        print("\n🧪 Generando casos controlados (Baja/Media/Alta)...")
        control_grd, control_score = crear_casos_controlados()
        control_grd_path, control_score_path = guardar_archivos_excel(
            control_grd,
            control_score,
            args.dest,
            f"GRD_control_{timestamp}",
            f"Score_control_{timestamp}"
        )
        print(f"   - {control_grd_path}")
        print(f"   - {control_score_path}")
        print("   ➜ Incluye 2 pacientes por categoría esperada (Baja/Media/Alta).")
    
    print("\n✅ ¡Listo! Ejecuta tu script de predicción con los archivos generados.")


if __name__ == "__main__":
    main()
