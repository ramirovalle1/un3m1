from django.urls import re_path, include, path
from inno import pro_tutoriaacademica, pro_horarios_actividades_reporte, \
    pro_horarios, pro_horarios_actividades, pro_horarios_noteorias, pro_horario_reemplazo, pro_horarios_old, \
    pro_asistencias, adm_pac, pro_aperturaclase, pro_aperturaclase_old, \
    pro_clases, adm_aperturaclase, data, api, adm_horarios, adm_horarios_clases, adm_horarios_examenes, \
    adm_horarios_examenes_bloques, adm_horarios_examenes_bloques_new, adm_horarios_examenes_sedes, \
    adm_horarios_examenes_sedes_coordinacion, adm_afinidad, adm_laboratorioscomputacion, adm_laboratoriosexterno, \
    adm_horarios_examenes_sedes_asistencias, adm_seguimientoacademico, pro_revisionactividadevidencia, \
    pro_actividadestutorpracticas, \
    adm_gestionactividadessalud, adm_editfotoestudiantes, pro_auditoria,adm_auditoria
from inno.view import adm_disertacion_horario

urlpatterns = [
    # PROFESOR
    re_path(r'^pro_tutoriaacademica$', pro_tutoriaacademica.view, name='pro_tutoriaacademica_view'),
    re_path(r'^pro_horarios_actividades_reporte$', pro_horarios_actividades_reporte.view, name='inno_pro_horarios_actividades_reporte_view'),
    re_path(r'^pro_horarios$', pro_horarios.view, name='inno_pro_horarios_view'),
    re_path(r'^inno/api$', api.view, name='inno_api_view'),
    re_path(r'^pro_horarios/old$', pro_horarios_old.view, name='inno_pro_horarios_view'),
    re_path(r'^pro_horarios_actividades$', pro_horarios_actividades.view, name='inno_pro_horarios_actividades_view'),
    re_path(r'^pro_horarios_noteorias$', pro_horarios_noteorias.view, name='inno_pro_horarios_noteorias_view'),
    re_path(r'^pro_horario_reemplazo$', pro_horario_reemplazo.view, name='inno_pro_horario_reemplazo_view'),
    re_path(r'^pro_asistencias$', pro_asistencias.view, name='inno_pro_asistencias_view'),
    re_path(r'^pro_aperturaclase/old$', pro_aperturaclase_old.view, name='inno_pro_aperturaclase_old_view'),
    re_path(r'^pro_aperturaclase$', pro_aperturaclase.view, name='inno_pro_aperturaclase_view'),
    re_path(r'^pro_clases$', pro_clases.view, name='inno_pro_clases_view'),
    re_path(r'^pro_auditoria$', pro_auditoria.view, name='inno_pro_auditoria_view'),
    re_path(r'^adm_auditoria$', adm_auditoria.view, name='inno_adm_auditoria_view'),
    re_path(r'^pro_revisionactividadevidencia$', pro_revisionactividadevidencia.view, name='inno_pro_revisionactividadevidencia_view'),
    re_path(r'^pro_actividadestutorpracticas$', pro_actividadestutorpracticas.view, name='inno_pro_actividadestutorpracticas_view'),
    # ESTDUAINTE
    # re_path(r'^alu_tutoriaacademica$', alu_tutoriaacademica.view, name='alu_tutoriaacademica_view'),
    # re_path(r'^alu_horarios$', alu_horarios.view, name='inno_alu_horarios_view'),
    # re_path(r'^alu_horarios/old$', alu_horarios_old.view, name='inno_alu_horarios_old_view'),
    # re_path(r'^alu_asistencias$', alu_asistencias.view, name='inno_alu_asistencias_view'),
    # ADMINISTRATIVO
    # SEGUIMIENTO SILABO
    re_path(r'^adm_seguimientoacademico$', adm_seguimientoacademico.view, name='inno_adm_seguimientoacademico_view'),
    re_path(r'^adm_editfotoestudiantes', adm_editfotoestudiantes.view, name='inno_adm_editfotoestudiantes_view'),
    re_path(r'^adm_aperturaclase$', adm_aperturaclase.view, name='inno_adm_aperturaclase_view'),
    re_path(r'^adm_pac$', adm_pac.view, name='inno_adm_pac_view'),
    re_path(r'^adm_horarios$', adm_horarios.view, name='inno_adm_horarios_view'),
    re_path(r'^adm_horarios/clases$', adm_horarios_clases.view, name='inno_adm_horarios_clases_view'),
    re_path(r'^adm_horarios/examenes$', adm_horarios_examenes.view, name='inno_adm_horarios_examenes_view'),
    re_path(r'^adm_horarios/examenes_ensedes$', adm_horarios_examenes_sedes.view, name='inno_adm_horarios_examenes_sedes_view'),
    re_path(r'^adm_horarios/examenes_ensedes/asistencias$', adm_horarios_examenes_sedes_asistencias.view, name='inno_adm_horarios_examenes_sedes_asistencias_view'),
    re_path(r'^adm_horarios/examenes_ensedes/coordinacion$', adm_horarios_examenes_sedes_coordinacion.view, name='inno_adm_horarios_examenes_sedes_coordinacion_view'),
    re_path(r'^adm_horarios/examenes_bloques$', adm_horarios_examenes_bloques.view, name='inno_adm_horarios_examenes_bloques_view'),
    re_path(r'^adm_horarios/examenes_bloques/new$', adm_horarios_examenes_bloques_new.view, name='inno_adm_horarios_examenes_bloques_new_view'),
    re_path(r'^adm_horarios/disertaciones$', adm_disertacion_horario.view, name='inno_adm_disertacion_horario_view'),
    re_path(r'^adm_afinidad$', adm_afinidad.view, name='inno_adm_afinidad_view'),
    # ASISTENCIA EXAMEN SEDE
    re_path(r'^adm_asistenciaexamensede/', include('inno.view.asistencia_examen_sede.urls')),
    # API INTERNA GENERAL
    re_path(r'^api/data/inno$', data.view, name='inno_api_data_view'),

    re_path(r'^adm_laboratorioscomputacion$', adm_laboratorioscomputacion.view, name='inno_adm_laboratorioscomputacion'),
    re_path(r'^viewlaboratorios$', adm_laboratoriosexterno.view, name='inno_adm_viewlaboratorios'),
    re_path(r'^adm_gestionactividadessalud$', adm_gestionactividadessalud.view, name='inno_adm_gestionactividadessalud'),

]
