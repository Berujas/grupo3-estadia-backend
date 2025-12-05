# 📋 Columnas de Input para el Modelo de Predicción de Exceso de Estadía

## 🎯 Resumen
El modelo requiere **64 columnas** en total para funcionar correctamente:
- **26 columnas numéricas**
- **38 columnas categóricas**

---

## 🔢 **COLUMNAS NUMÉRICAS** (26)

### Datos Demográficos y Clínicos
1. `estancia_norma_grd` - Estancia normativa según GRD
2. `edad_en_anos` - Edad del paciente en años
3. `ir_grd_codigo_` - Código del GRD
4. `proced_01_principal_cod_` - Código del procedimiento principal

### Encuesta Social (Preguntas)
5. `pregunta` - Puntuación pregunta 1
6. `pregunta2` - Puntuación pregunta 2  
7. `pregunta3` - Puntuación pregunta 3
8. `pregunta4` - Puntuación pregunta 4
9. `numerodetelefonoocontactodelfamiliar` - Teléfono familiar

### Dimensiones de Evaluación Social
10. `habitacional` - Evaluación habitacional (0-1)
11. `socioeconomica` - Evaluación socioeconómica (0-1)
12. `salud_mental` - Evaluación salud mental (0-1)
13. `redes` - Evaluación redes sociales (0-1)
14. `cuidador` - Evaluación cuidador (0-1)

### Evaluaciones Clínicas
15. `presencia_de_patologia_neurocognitiva` - Patología neurocognitiva
16. `que_tipo_de_cuidado_requiere_el_paciente` - Tipo de cuidado requerido
17. `el_la_paciente_producto_de_la_hospitalizacion_actual_presentara_alguna_secuela_que_afecte_su_independencia` - Secuelas esperadas

### Puntuaciones y Gestión
18. `total` - Puntuación total de la encuesta
19. `gestion` - Código de gestión
20. `categorizacion_de_gestion` - Categorización de gestión
21. `fecha_intervencion` - Fecha de intervención (timestamp)
22. `registro_en_trakecare` - Registro en sistema

### Datos Demográficos Adicionales
23. `edad` - Edad (duplicado, puede diferir de edad_en_anos)
24. `dias_estadia` - Días de estadía

### Columnas de Resultado (NO incluir en input)
25. `p_excede_norma` - **PROBABILIDAD PREDICHA** (resultado)
26. `y_real` - **VALOR REAL** (resultado)

---

## 📝 **COLUMNAS CATEGÓRICAS** (38)

### Información de Ingreso
1. `tipo_ingreso_descripcion_` - Tipo de ingreso (Programado/Urgente)
2. `ir_grd` - Descripción del GRD
3. `diagnostico_principal` - Diagnóstico principal (código ICD-10)
4. `ir_tipo_grd` - Tipo de GRD (M/Q)
5. `prevision_desc_` - Previsión de salud
6. `servicio_ingreso_descripcion_` - Servicio de ingreso
7. `sexo_desc_` - Sexo del paciente

### Información Temporal y Logística
8. `dia_habil_inhabil` - Día hábil/inhábil
9. `rut_pasaporte` - RUT o pasaporte
10. `direccion_del_paciente` - Dirección del paciente

### Registro Social de Hogares
11. `cuenta_con_registro_social_de_hogares_` - Tiene registro social
12. `cual_es_el_porcentaje_otorgado_de_acuerdo_el_registro_social_de_hogares_` - Porcentaje RSH

### Actividad y Discapacidad
13. `que_actividad_realizada_` - Actividad que realiza
14. `persona_en_situacion_de_discapacidad` - Situación de discapacidad

### Atención Primaria
15. `atencion_en_salud_primaria_cesfam_o_consultorio_` - Atención primaria
16. `nombre_del_cesfam_o_consultorio` - Nombre del centro

### Información Familiar
17. `nombre_del_tutor_familiar_otro_quien_se_hara_cargo_del_cuidado_del_la_paciente` - Tutor familiar
18. `relacion_o_parentesco_con_el_la_paciente` - Parentesco

### Direcciones y Contacto
19. `direccion_del_domicilio_al_alta_del_la_paciente` - Dirección al alta
20. `correo_electronico2` - Email de contacto

### Evaluaciones Categóricas
21. `situacion_habitabilidad_` - Situación habitacional
22. `situacion_economica_` - Situación económica
23. `consumo_de_drogas_salud_mental` - Consumo de drogas/salud mental
24. `red_familiar` - Red familiar
25. `cuidador_al_alta` - Cuidador al alta

### Identificación y Gestión
26. `buscar_episodio_con_asignacion_encuesta` - ID episodio para encuesta
27. `nivel_de_dependencia` - Nivel de dependencia
28. `aseguradora` - Aseguradora
29. `prevision_homologa` - Previsión homologada
30. `tipo_de_aseguradora2` - Tipo de aseguradora

### Marcas y Categorización
31. `marca1` - Marca 1
32. `marca2` - Marca 2  
33. `marca3` - Marca 3
34. `fe_alta` - Fecha estimada de alta

### Fechas y Grupos
35. `fecha_de_nacimiento` - Fecha de nacimiento
36. `grupo_etario` - Grupo etario
37. `fecha_adm_` - Fecha de admisión
38. `fecha_asignacion` - Fecha de asignación

---

## ⚠️ **COLUMNAS PROHIBIDAS** (Fuga de Información)

**NO incluir estas columnas** porque contienen información del futuro:
- `estancia_del_episodio` - Estancia real (ya ocurrida)
- `horas_de_estancia` - Horas reales de estadía
- `estancias_` - Cualquier columna que contenga "estancias_"
- `impacto_estancias` - Impacto de estancias
- `estancia_inlier_outlier` - Clasificación de estancia

---

## 📊 **COLUMNAS MÁS IMPORTANTES**

### **Críticas para la Predicción:**
1. `edad_en_anos` - Edad del paciente
2. `sexo_desc_` - Sexo
3. `tipo_ingreso_descripcion_` - Tipo de ingreso
4. `servicio_ingreso_descripcion_` - Servicio
5. `prevision_desc_` - Previsión
6. `diagnostico_principal` - Diagnóstico
7. `estancia_norma_grd` - Estancia normativa
8. `total` - Puntuación total encuesta social

### **Dimensiones Sociales Clave:**
- `habitacional` - Condiciones de vivienda
- `socioeconomica` - Situación económica  
- `salud_mental` - Salud mental
- `redes` - Redes de apoyo
- `cuidador` - Disponibilidad de cuidador

---

## 🚀 **Cómo Usar**

Para hacer predicciones, tu archivo de datos debe contener **TODAS** estas 64 columnas. Si faltan columnas, el modelo fallará.

**Formato recomendado:** CSV o Excel con exactamente estas columnas y nombres.

**Ejemplo de uso:**
```bash
python -m src.predict --config config.yaml --input mi_archivo.csv --output predicciones.csv
```
