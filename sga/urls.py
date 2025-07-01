from django.urls import re_path, include
import sakai
import mooc_campusvirtual
from evath import adm_evaluacion, adm_misevaluaciones
from sagest import adm_aprobacionhoras
from sga import commonviews, administrativos, observacion_tecnica, asignacion_aula, ver_solicitudes, \
    reportes, adm_paextracurriculares, sistemasag, alu_sistemasag, \
    solicitudes, adm_retirados, adm_retiradoscarrera, mallas, \
    docentes, pro_autoevaluacion, cons_documentos, adm_asignaturas, cons_alumnos, \
    cons_prematricula, cons_prematriculamodulo, alu_prematriculamodulo, alu_prematriculamoduloespecial, \
    alu_prematriculamodulocomputacion, lecciones_dia, adm_asistencias, adm_coordinaciones, adm_anteproyecto, \
    adm_anteproyectos, adm_criteriosactividades, adm_criteriosactividadesdocente, \
    adm_promateriaspreferencias, adm_proyectosgrado, adm_complexivo, adm_complexivo_view, \
    adm_solicitudcupo, asistencias_periodo, doc_planificacion, aprobar_silabo, pro_silabos, \
    adm_laboratoriosacademia, pra_profesionales_prog, pra_profesionalesinscripcion, \
    inscripciones, inscripciones_admision, matriculas, matriculas_admision, graduados, egresados, fecha_evaluaciones, \
    adm_periodos, adm_bibliotecavirtual, adm_modelosevaluativos, pro_evaluaciones, \
    pro_evaluaciones_masivo, pro_documentos, pro_apelaciones, pro_aluevaluacion, pro_planificacion, \
    pro_personaevaluacion, pro_cronograma, pro_tutorias, pro_certificados, pro_reemplazo, \
    adm_ippermitida, alu_prematricula, alu_automatricula, \
    alu_automatriculamodulos, alu_notas, alu_solicitudes, \
    alu_cronograma, alu_actextracurricular, alu_vinculacion, alu_ofertalaboral, alu_hojavida, alu_tutorias, \
    alu_complexivo, alu_practicaspreprofesionalesinscripcion, alu_citasmedicas, alu_practicaspro, \
    alu_cambioseccion, alu_cambioseccionaprobacion, alu_addmatematri, seguimiento, dobe, adm_docentes, noticias, \
    incidencias, programasinvestigacion, programasvinculacion, articulosinvestigacion, ponenciasinvestigacion, \
    librosinvestigacion, alu_finanzas, \
    con_distributivo, cons_distributivo, adm_evaluaciondocentesacreditacion, adm_evaluaciondocentesacreditacioncoord, \
    cons_evaluaciondocentesacreditacion, adm_evaluaciondocentesacreditacioncoordvice, adm_grupos, api, estadisticas, qr, \
    encuestas, adm_becarios, adm_discapacitados, databasebackup, adm_actextracurricular, adm_calendario, calendario, \
    adm_carreras, adm_institucioneducacionsuperior, adm_vinculacion, adm_pasantias, mailbox, preinscrito, bolsalaboral, \
    adm_ofertalaboral, crm, datosiniciales, adm_cursoscomplementarios, adm_conveniopago, alu_conveniopago, \
    doc_generales, doc_credencial, descargaarchivo, adm_indicadores, alu_anteproyecto, pro_anteproyecto, \
    pro_tutoriasproyecto, alu_tutoriasproyecto, adm_fichaproyecto, adm_periodotitulacion, \
    adm_tipotitulacion, adm_modelotitulacion, adm_alternativatitulacion, alu_matriculaciontitulacion, \
    alu_propuestatitulacion, adm_cronogramatitulacion, alu_complexivocurso, \
    pro_complexivoclase, adm_complexivoasignatura, pro_complexivoexamen, adm_complexivotematica, \
    adm_complexivoaprobartematica, pro_grupo_investigacion, adm_grupoinvestigacion, adm_tipopublicacion, \
    pro_complexivotematica, adm_convocatoriainvestigacion, \
    pro_solicitudgrupoinvestigacion, adm_solicitudaprobacioninvestigacion_dr, adm_solicitudaprobacioninvestigacion_inv, \
    adm_planificacionsilabo, alu_solicitudjustificacionasistencia, \
    adm_casosjustificacionasistencias, adm_ayudantiacatedra, pro_ayudantiacatedra, alu_ayudantiacatedra, adm_becas, \
    librosbiblioteca, adm_justificacionasistenciaaprobacion_dr, alu_becas, adm_institucionescolegio, \
    adm_tipoformacioncarrera, alu_documentosall, adm_inscripcionesingles, adm_gimnasio, adm_librofotocopiado, \
    adm_polideportivo, pro_consejerias, alu_consejerias, adm_docenteconsejeria, adm_convenioempresa, dir_convenios, \
    consulta_inscripcion, proyectovinculaciondocente, th_cantones, alu_proyectovinculacion, calificacion_tardia, \
    adm_aprobarsemanavirtual, virtual_soporte_online, \
    virtual_admsoporte_online, adm_gestionvideo, adm_aprobarvideoclasevirtual, adm_crai, adm_crai_biblioteca, \
    adm_aprobarcapdocente, adm_crai_directores, alu_mundocrai, adm_crai_actividades, adm_configuracion_mundocrai, \
    alu_preinscripcionppp, manualusuario, lineatiempo, \
    adm_sancionestudiante, inscripcionescursos, contenidosonline, cons_ponencia, adm_crai_pantalla, \
    inscripcionescongresos, alu_movilidad, \
    encuestaparentesco, adm_planpractica, alu_gestionarmatricula, \
    adm_solicitudretiromatricula, testunemi, certificadovalido, adm_encuestagrupoestudiantes, adm_archivonotas, \
    aprobar_silabo_decano, adm_configuracionpropuestaposgrado, adm_mecanismotitulacionposgrado, \
    alu_tematitulacionposgrado, adm_aprobartematitulacion, pro_titulacionposgrado, pro_tutoriaposgrado, \
    alu_tutoriaposgrado, adm_configuraciondescuentoposgrado, alu_descuentoposgrado, adm_rediseno, alu_devoluciondinero, \
    adm_rubrica, adm_convalidacionpractica, alu_convalidacionpractica, pro_tutoria, alu_solicitudtutor, \
    adm_rubrica_profesor, adm_rubrica_director, adm_validarrequisitostitulacion, notificacion, adm_tasks, \
    alu_refinanciamientoposgrado, adm_refinanciamientoposgrado, \
    solicitudexterna, enlace_descarga, inscripcionescursos_edcon, adm_gedcevaluacion, gedc_encuesta, monitoreo, \
    adm_padronelectoral, milugarvotacion, alu_justificacionsufragio, pro_justificacionsufragio, api_2, \
    adm_ubicacionestudiantes, dir_cronograma, adm_manual_usuario, adm_promociondocente, alu_cambiocarrera, \
    alu_solicitudcambiocarrera, adm_verificacion_documento, adm_verificacion_documento_externos, \
    adm_verificacion_documento_deportistas, adm_verificacion_documento_discapacitados, \
    adm_verificacion_documento_etnias, adm_verificacion_documento_migrantes, adm_verificacion_documento_artistas, \
    adm_asesoramientosee, congresos, alu_solicitudcambioies, firma, \
    adm_aprobaringles, alu_practicassalud, adm_verificacion_documento_hojas_vida, \
    comunicacion_institucional, solicitud_productos, pro_capacitacion, pro_evaluaciones_firmas, insignias, adm_insignia, \
    mis_activos, gestion_operaciones_tecnologicas, operaciones_prestamoactivos, alu_actualizadatos, \
    dir_ayudantiacatedra, simuladorcostocarrera, adm_verificacion_documento_enfermedades, alu_practicassaludinscripcion, \
    uxplora, about
from sga.niveles.views import index as niveles_new, index_old as niveles_old
from investigacion import adm_propuestalineainvestigacion

from socioecon import alu_socioecon
from med import box_medical, box_odontologica, box_psicologica, alu_medical, \
    inventariomedico, box_citasmedicas, commonviews as commonviewsmed, box_nutricion, adm_bienestar_recepcion, \
    box_planificaciontemas
from voto import adm_ingresoacta
from bib import busqueda,prestamos,documentos


urlpatterns = [re_path(r'^loginsga$', commonviews.login_user, name='LoginUser'),
            re_path(r'^sga-oauth2/$', commonviews.oauth2epunemi, name='LoginEpunemi'),
            re_path(r'^logout$', commonviews.logout_user, name='LogoutUser'),
            re_path(r'^cu$', commonviews.changeuser, name='changeuser'),
            re_path(r'^cudu$', commonviews.changeuserdu, name='changeuserdu'),
            re_path(r'^pass$', commonviews.passwd, name='passwd'),
            re_path(r'^about$', about.view, name='about'),
            re_path(r'^$', commonviews.panel, name='panel'),
            # # ADMINISTRATIVOS
            re_path(r'^milugarvotacion', milugarvotacion.view, name='milugarvotacion_view'),
            re_path(r'^adm_padronelectoral', adm_padronelectoral.view, name='adm_padronelectoral_view'),
            re_path(r'^alu_procesoelectoral', alu_justificacionsufragio.view, name='alu_justificacionsufragio_view'),
            re_path(r'^pro_procesoelectoral', pro_justificacionsufragio.view, name='pro_justificacionsufragio_view'),
            re_path(r'^adm_gedcevaluacion', adm_gedcevaluacion.view, name='adm_gedc_view'),
            re_path(r'^gedc', gedc_encuesta.view, name='gedc_encuesta'),
            re_path(r'^adm_rubrica$', adm_rubrica.view, name='adm_rubrica_view'),
            re_path(r'^adm_rubrica_profesor$', adm_rubrica_profesor.view, name='adm_rubrica_profesor_view'),
            re_path(r'^adm_rubrica_director$', adm_rubrica_director.view, name='adm_rubrica_director_view'),
            re_path(r'^administrativos$', administrativos.view, name='administrativos_view'),
            re_path(r'^observacion_tecnica$', observacion_tecnica.view, name='sga_observacion_tecnica_view'),
            re_path(r'^asignacion_aula$', asignacion_aula.view, name='sga_asignacion_aula_view'),
            re_path(r'^ver_solicitudes$', ver_solicitudes.view, name='sga_ver_solicitudes_view'),

            re_path(r'^adm_aprobacionhoras$', adm_aprobacionhoras.view, name='sga_adm_aprobacionhoras_view'),
            re_path(r'^adm_archivonotas$', adm_archivonotas.view, name='sga_adm_archivonotas_view'),
            re_path(r'^th_cantones$', th_cantones.view, name='sga_th_cantones_view'),
            re_path(r'^calificacion_tardia$', calificacion_tardia.view, name='sga_calificacion_tardia_view'),
            re_path(r'^adm_configuracionpropuesta$', adm_configuracionpropuestaposgrado.view, name='adm_configuracionpropuesta_view'),
            re_path(r'^adm_configuraciondescuento$', adm_configuraciondescuentoposgrado.view, name='adm_configuraciondescuento_view'),
            re_path(r'^alu_descuentoposgrado$', alu_descuentoposgrado.view, name='alu_descuentoposgrado_view'),
            re_path(r'^adm_mecanismotitulacionposgrado$', adm_mecanismotitulacionposgrado.view, name='adm_mecanismotitulacionposgrado_view'),
            re_path(r'^adm_aprobartematitulacion$', adm_aprobartematitulacion.view, name='adm_aprobartematitulacion_view'),
            # # REPORTES
            re_path(r'^reportes$', reportes.view, name='sga_reportes_view'),
            re_path(r'^qweb$', reportes.qweb, name='qweb'),
            # ACTIVIDADES EXTRACURRICULARES
            re_path(r'^adm_paextracurriculares$', adm_paextracurriculares.view, name='sga_adm_paextracurriculares_view'),
            # # SAG
            re_path(r'^sistemasag$', sistemasag.view, name='sga_sistemasag_view'),
            re_path(r'^alu_sistemasag$', alu_sistemasag.view, name='sga_alu_sistemasag_view'),
            # SOLICITUDES A SECRETARIA
            re_path(r'^solicitudes$', solicitudes.view, name='sga_solicitudes_view'),
            # COORDINACION
            re_path(r'^adm_retirados$', adm_retirados.view, name='sga_adm_retirados_view'),
            re_path(r'^adm_retiradoscarrera$', adm_retiradoscarrera.view, name='sga_adm_retiradoscarrera_view'),
            re_path(r'^mallas$', mallas.view, name='sga_mallas_view'),
            re_path(r'^niveles$', niveles_new.view, name='sga_niveles_new_view'),
            re_path(r'^niveles_old$', niveles_old.view, name='sga_niveles_old_view'),
            re_path(r'^docentes$', docentes.view, name='sga_docentes_view'),
            re_path(r'^pdf_listaevaluacion$', pro_autoevaluacion.pdf_listaevaluacion, name='sga_pro_autoevaluacion_pdf_listaevaluacion'),
            re_path(r'^cons_documentos$', cons_documentos.view, name='sga_cons_documentos_view'),
            re_path(r'^adm_asignaturas$', adm_asignaturas.view, name='sga_adm_asignaturas_view'),
            re_path(r'^adm_rediseno$', adm_rediseno.view, name='adm_rediseno_view'),
            re_path(r'^librosbiblioteca$', librosbiblioteca.view, name='sga_librosbiblioteca_view'),

            re_path(r'^cons_alumnos$', cons_alumnos.view, name='sga_cons_alumnos_view'),
            re_path(r'^cons_prematricula$', cons_prematricula.view, name='sga_cons_prematricula_view'),
            re_path(r'^cons_prematriculamodulo$', cons_prematriculamodulo.view, name='sga_cons_prematriculamodulo_view'),
            re_path(r'^alu_prematriculamodulo$', alu_prematriculamodulo.view, name='sga_alu_prematriculamodulo_view'),
            re_path(r'^alu_prematriculamoduloespecial$', alu_prematriculamoduloespecial.view, name='sga_alu_prematriculamoduloespecial_view'),
            re_path(r'^alu_prematriculamodulocomputacion$', alu_prematriculamodulocomputacion.view, name='sga_alu_prematriculamodulocomputacion_view'),

            re_path(r'^lecciones_dia$', lecciones_dia.view, name='sga_lecciones_dia_view'),
            re_path(r'^adm_asistencias$', adm_asistencias.view, name='sga_adm_asistencias_view'),
            re_path(r'^adm_coordinaciones$', adm_coordinaciones.view, name='sga_adm_coordinaciones_view'),
            re_path(r'^adm_anteproyectos$', adm_anteproyectos.view, name='sga_adm_anteproyectos_view'),
            re_path(r'^adm_criteriosactividades$', adm_criteriosactividades.view, name='sga_adm_criteriosactividades_view'),
            re_path(r'^adm_criteriosactividadesdocente$', adm_criteriosactividadesdocente.view, name='sga_adm_criteriosactividadesdocente_view'),

            re_path(r'^adm_promateriaspreferencias$', adm_promateriaspreferencias.view, name='sga_adm_promateriaspreferencias_view'),
            re_path(r'^adm_proyectosgrado$', adm_proyectosgrado.view, name='sga_adm_proyectosgrado_view'),

            re_path(r'^adm_complexivo$', adm_complexivo.view, name='sga_adm_complexivo_view'),
            re_path(r'^adm_complexivo_view$', adm_complexivo_view.view, name='sga_adm_complexivo_view_view'),
            # re_path(r'^adm_computacion$', adm_computacion.view, name='sga_adm_computacion_view'),

            re_path(r'^adm_solicitudcupo$', adm_solicitudcupo.view, name='sga_adm_solicitudcupo_view'),
            re_path(r'^asistencias_periodo$', asistencias_periodo.view, name='sga_asistencias_periodo_view'),
            re_path(r'^doc_planificacion$', doc_planificacion.view, name='sga_doc_planificacion_view'),
            re_path(r'^aprobar_silabo$', aprobar_silabo.view, name='sga_aprobar_silabo_view'),
            re_path(r'^aprobar_silabo_decano$', aprobar_silabo_decano.view, name='sga_aprobar_silabo_decano_view'),
            re_path(r'^pro_silabos$', pro_silabos.view, name='sga_pro_silabos_view'),

            re_path(r'^adm_laboratoriosacademia$', adm_laboratoriosacademia.view, name='sga_adm_laboratoriosacademia_view'),
            # INSCRIPCIONES PRACTICAS PREPROFESIONALES
            re_path(r'^pra_profesionales_prog$', pra_profesionales_prog.view, name='sga_pra_profesionales_prog_view'),
            re_path(r'^pra_profesionalesinscripcion$', pra_profesionalesinscripcion.view, name='sga_pra_profesionalesinscripcion_view'),
            # INSCRIPCIONES Y MATRICULAS
            re_path(r'^inscripciones$', inscripciones.view, name='sga_inscripciones_view'),
            re_path(r'^consulta_inscripcion$', consulta_inscripcion.view, name='sga_consulta_inscripcion_view'),
            re_path(r'^adm_inscripcionesingles$', adm_inscripcionesingles.view, name='sga_adm_inscripcionesingles_view'),
            re_path(r'^inscripciones_admision$', inscripciones_admision.view, name='sga_inscripciones_admision_view'),
            re_path(r'^matriculas$', matriculas.view, name='sga_matriculas_view'),
            re_path(r'^matriculas_admision$', matriculas_admision.view, name='sga_matriculas_admision_view'),
            re_path(r'^graduados$', graduados.view, name='sga_graduados_view'),
            re_path(r'^egresados$', egresados.view, name='sga_egresados_view'),
            re_path(r'^fecha_evaluaciones$', fecha_evaluaciones.view, name='sga_fecha_evaluaciones_view'),
            re_path(r'^adm_periodos$', adm_periodos.view, name='sga_adm_periodos_view'),
            re_path(r'^adm_modelosevaluativos$', adm_modelosevaluativos.view, name='sga_adm_modelosevaluativos_view'),
            re_path(r'^alu_gestionarmatricula$', alu_gestionarmatricula.view, name='sga_alu_gestionarmatricula_view'),
            #Revisar solicitudes de retiro de matriculas
            re_path(r'^adm_solicitudretiromatricula$', adm_solicitudretiromatricula.view, name='sga_adm_solicitudretiromatricula_view'),
            # PROFESORES
            re_path(r'^pro_evaluaciones$', pro_evaluaciones.view, name='sga_pro_evaluaciones_view'),
            re_path(r'^pro_evaluaciones_masivo$', pro_evaluaciones_masivo.view, name='sga_pro_evaluaciones_masivo_view'),
            re_path(r'^pro_evaluaciones_firmas$', pro_evaluaciones_firmas.view, name='sga_pro_evaluaciones_firmas_view'),
            re_path(r'^pro_documentos$', pro_documentos.view, name='sga_pro_documentos_view'),
            re_path(r'^pro_autoevaluacion$', pro_autoevaluacion.view, name='sga_pro_autoevaluacion_view'),
            re_path(r'^pro_apelaciones$', pro_apelaciones.view, name='sga_pro_apelaciones_view'),
            re_path(r'^pro_aluevaluacion$', pro_aluevaluacion.view, name='sga_pro_aluevaluacion_view'),
            re_path(r'^pro_planificacion$', pro_planificacion.view, name='sga_pro_planificacion_view'),
            re_path(r'^pro_personaevaluacion$', pro_personaevaluacion.view, name='sga_pro_personaevaluacion_view'),
            re_path(r'^pro_cronograma$', pro_cronograma.view, name='sga_pro_cronograma_view'),
            re_path(r'^pro_tutorias$', pro_tutorias.view, name='sga_pro_tutorias_view'),
            re_path(r'^pro_tutoria$', pro_tutoria.view, name='sga_pro_tutoria_view'),
            re_path(r'^pro_certificados$', pro_certificados.view, name='sga_pro_certificados_view'),
            re_path(r'^pro_reemplazo$', pro_reemplazo.view, name='sga_pro_reemplazo_view'),

            re_path(r'^adm_ippermitida$', adm_ippermitida.view, name='sga_adm_ippermitida_view'),
            re_path(r'^adm_aprobarcapdocente$', adm_aprobarcapdocente.view, name='sga_adm_aprobarcapdocente_view'),
            re_path(r'^cons_ponencia$', cons_ponencia.view, name='sga_cons_ponencia_view'),
            re_path(r'^pro_titulacionposgrado$', pro_titulacionposgrado.view, name='pro_titulacionposgrado_view'),
            re_path(r'^pro_tutoriaposgrado$', pro_tutoriaposgrado.view, name='pro_tutoriaposgrado_view'),
            re_path(r'^alu_tutoriaposgrado$', alu_tutoriaposgrado.view, name='alu_tutoriaposgrado_view'),



            # ALUMNOS HORARIOS
            re_path(r'^alu_prematricula$', alu_prematricula.view, name='sga_alu_prematricula_view'),
            re_path(r'^alu_automatricula$', alu_automatricula.view, name='sga_alu_automatricula_view'),
            re_path(r'^alu_automatriculamodulos$', alu_automatriculamodulos.view, name='sga_alu_automatriculamodulos_view'),
            # re_path(r'^alu_materias$', alu_materias.view, name='sga_alu_materias_view'),
            re_path(r'^alu_notas$', alu_notas.view, name='sga_alu_notas_view'),
            re_path(r'^alu_solicitudes$', alu_solicitudes.view, name='sga_alu_solicitudes_view'),
            # re_path(r'^alu_documentos$', alu_documentos.view, name='sga_alu_documentos_view'),
            # re_path(r'^fechaatrasada987654321$', alu_documentosall.view,  name='sga_alu_documentosall_view'),
            re_path(r'^alu_finanzas$', alu_finanzas.view, name='sga_alu_finanzas_view'),
            re_path(r'^alu_actualizadatos$', alu_actualizadatos.view, name='sga_alu_actualizadatos_view'),
            # re_path(r'^alu_malla$', alu_malla.view, name='sga_alu_malla_view'),
            re_path(r'^alu_medical$', alu_medical.view, name='med_alu_medical_view'),
            re_path(r'^alu_cronograma$', alu_cronograma.view, name='sga_alu_cronograma_view'),
            re_path(r'^alu_actextracurricular$', alu_actextracurricular.view, name='sga_alu_actextracurricular_view'),
            re_path(r'^alu_vinculacion$', alu_vinculacion.view, name='sga_alu_vinculacion_view'),
            re_path(r'^alu_ofertalaboral$', alu_ofertalaboral.view, name='sga_alu_ofertalaboral_view'),
            re_path(r'^alu_hojavida$', alu_hojavida.view, name='sga_alu_hojavida_view'),
            re_path(r'^alu_socioecon$', alu_socioecon.view, name='socioecon_alu_socioecon_view'),
            re_path(r'^alu_tutorias$', alu_tutorias.view, name='sga_alu_tutorias_view'),
            re_path(r'^alu_complexivo$', alu_complexivo.view, name='sga_alu_complexivo_view'),
            re_path(r'^alu_proyectovinculacion$', alu_proyectovinculacion.view, name='sga_alu_proyectovinculacion_view'),
            re_path(r'^alu_practicaspreprofesionalesinscripcion$', alu_practicaspreprofesionalesinscripcion.view, name='sga_alu_practicaspreprofesionalesinscripcion_view'),
            re_path(r'^alu_practicassalud$', alu_practicassalud.view, name='sga_alu_practicassalud_view'),
            re_path(r'^alu_citasmedicas$', alu_citasmedicas.view, name='sga_alu_citasmedicas_view'),
            re_path(r'^alu_practicaspro$', alu_practicaspro.view, name='sga_alu_practicaspro_view'),
            re_path(r'^alu_cambioseccion$', alu_cambioseccion.view, name='sga_alu_cambioseccion_view'),
            re_path(r'^adm_bibliotecavirtual$', adm_bibliotecavirtual.view, name='sga_adm_bibliotecavirtual_view'),
            re_path(r'^alu_cambioseccionaprobacion$', alu_cambioseccionaprobacion.view, name='sga_alu_cambioseccionaprobacion_view'),
            re_path(r'^alu_addmatematri$', alu_addmatematri.view, name='sga_alu_addmatematri_view'),
            re_path(r'^alu_tematitulacionposgrado$', alu_tematitulacionposgrado.view, name='sga_alu_tematitulacionposgrado_view'),
            re_path(r'^alu_solicitudtutor$', alu_solicitudtutor.view, name='sga_alu_solicitudtutor_view'),
            re_path(r'^alu_cambiocarrera$', alu_cambiocarrera.view, name='sga_alu_cambiocarrera_view'),
            re_path(r'^alu_solicitudcambiocarrera$', alu_solicitudcambiocarrera.view, name='sga_alu_solicitudcambiocarrera_view'),
            re_path(r'^alu_solicitudcambioies$', alu_solicitudcambioies.view, name='sga_alu_solicitudcambioies_view'),
               # SEGUIMIENTO ALUMNOS
            re_path(r'^seguimiento$', seguimiento.view, name='sga_seguimiento_view'),
            # BIENESTAR ESTUDIANTIL Y DPTO. MEDICO
            re_path(r'^dobe$',dobe.view, name='sga_dobe_view'),
            re_path(r'^box_medical$', box_medical.view, name='med_box_medical_view'),
            re_path(r'^box_odontologica$', box_odontologica.view, name='med_box_odontologica_view'),
            re_path(r'^box_psicologica$', box_psicologica.view, name='med_box_psicologica_view'),
            re_path(r'^box_nutricion$', box_nutricion.view, name='med_box_nutricion_view'),
            re_path(r'^box_planificaciontemas$', box_planificaciontemas.view, name='med_box_planificaciontemas_view'),
            re_path(r'^inventariomedico', inventariomedico.view, name='med_inventariomedico_view'),
            re_path(r'^box_citasmedicas$', box_citasmedicas.view, name='med_box_citasmedicas_view'),
            re_path(r'^box_inventario$', commonviewsmed.box_inventario, name='med_commonviews_box_inventario'),
            re_path(r'^box_recepcion$', adm_bienestar_recepcion.view, name='adm_bienestar_recepcion_view'),
            # ADMINISTRAR CLASES Y EVALUACIONES DE DOCENTES POR EL JEFE ACADEMICO
            re_path(r'^adm_docentes$', adm_docentes.view, name='sga_adm_docentes_view'),
            # NOTICIAS
            re_path(r'^noticias$', noticias.view, name='sga_noticias_view'),
            # INCIDENCIAS
            re_path(r'^incidencias$', incidencias.view, name='sga_incidencias_view'),
            # MATRICES INVESTIGACION/VINCULACION
            re_path(r'^programasinvestigacion$', programasinvestigacion.view, name='sga_programasinvestigacion_view'),
            re_path(r'^programasvinculacion$', programasvinculacion.view, name='sga_programasvinculacion_view'),
            re_path(r'^proyectovinculaciondocente$', proyectovinculaciondocente.view, name='sga_proyectovinculaciondocente_view'),
            re_path(r'^articulosinvestigacion$', articulosinvestigacion.view, name='sga_articulosinvestigacion_view'),
            re_path(r'^ponenciasinvestigacion$', ponenciasinvestigacion.view, name='sga_ponenciasinvestigacion_view'),
            re_path(r'^librosinvestigacion$', librosinvestigacion.view, name='sga_librosinvestigacion_view'),
            # DISTRIBUTIVO DOCENTES
            re_path(r'^con_distributivo$', con_distributivo.view, name='sga_con_distributivo_view'),
            # # DISTRIBUTIVO DE AULAS
            re_path(r'^cons_distributivo$', cons_distributivo.view, name='sga_cons_distributivo_view'),
            # GESTION DE EVALUACION DE DOCENTES
            re_path(r'^adm_evaluaciondocentesacreditacion$', adm_evaluaciondocentesacreditacion.view, name='sga_adm_evaluaciondocentesacreditacion_view'),
            re_path(r'^adm_evaluaciondocentesacreditacioncoord$', adm_evaluaciondocentesacreditacioncoord.view, name='sga_adm_evaluaciondocentesacreditacioncoord_view'),
            re_path(r'^cons_evaluaciondocentesacreditacion$', cons_evaluaciondocentesacreditacion.view, name='sga_cons_evaluaciondocentesacreditacion_view'),
            re_path(r'^adm_evaluaciondocentesacreditacioncoordvice$', adm_evaluaciondocentesacreditacioncoordvice.view, name='sga_adm_evaluaciondocentesacreditacioncoordvice_view'),
            # GESTION DE GRUPOS
            re_path(r'^adm_grupos$', adm_grupos.view, name='sga_adm_grupos_view'),
            # API FOR THIRD PARTY APPS
            re_path(r'^api$', api.view, name='sga_api_view'),
            re_path(r'^api_2$', api_2.view, name='sga_api_2_view'),
            # ESTADISTICAS Y GRAFICOS
            re_path(r'^estadisticas$', estadisticas.view, name='sga_estadisticas_view'),
            # INTEGRACION QR
            re_path(r'^aula/(?P<ida>\d+)$', qr.aula, name='sga_qr_aula'),
            re_path(r'^qr/(?P<ida>\d+)$', qr.qraula, name='sga_qr_qraula'),
            # BIBLIOTECA
            re_path(r'^documentos$', documentos.view, name='bib_documentos_view'),
            re_path(r'^prestamos$', prestamos.view, name='bib_prestamos_view'),
            re_path(r'^bibliosearch$', busqueda.view, name='bib_busqueda_view'),
            re_path(r'^biblioteca$', busqueda.consulta, name='bib_busqueda_consulta'),
            re_path(r'^otrasbiblio$', busqueda.otras, name='bib_busqueda_otras'),
            re_path(r'^gourl$', busqueda.gourl, name='bib_busqueda_gourl'),
            re_path(r'^book/(?P<id>\d+)$', busqueda.book, name='bib.busqueda.book'),
            re_path(r'^encuestas$', encuestas.view, name='sga_encuestas_view'),
            # ESTUDIANTES CON BECA ASIGNADA (BECARIOS)
            re_path(r'^adm_becarios$', adm_becarios.view, name='sga_adm_becarios_view'),
            re_path(r'^adm_discapacitados$', adm_discapacitados.view, name='sga_adm_discapacitados_view'),
            # BACKUP DE LA BASE DE DATOS
            re_path(r'^databasebackup$', databasebackup.view, name='sga_databasebackup_view'),
            # ACTIVIDADES EXTRACURRICULARES COORDINACION
            re_path(r'^adm_actextracurricular', adm_actextracurricular.view, name='sga_adm_actextracurricular_view'),
            # ADMINISTRADOR DE CALENDARIO DE ACTIVIDADES
            re_path(r'^adm_calendario$', adm_calendario.view, name='sga_adm_calendario_view'),
            # CALENDARIO DE ACTIVIDADES
            re_path(r'^calendario$', calendario.view, name='sga_calendario_view'),
            # CARRERAS
            re_path(r'^adm_carreras$', adm_carreras.view, name='sga_adm_carreras_view'),
            # institucioneducacionsuperior
            re_path(r'^adm_institucioneducacionsuperior$', adm_institucioneducacionsuperior.view, name='sga_adm_institucioneducacionsuperior_view'),
            re_path(r'^adm_institucionescolegio$', adm_institucionescolegio.view, name='sga_adm_institucionescolegio_view'),
            # VINCULACION
            re_path(r'^adm_vinculacion$', adm_vinculacion.view, name='sga_adm_vinculacion_view'),
            # PASANTIAS DE ESTUDIANTES
            re_path(r'^adm_pasantias$', adm_pasantias.view, name='sga_adm_pasantias_view'),
            # BUZON DE MENSAJES
            re_path(r'^mailbox$', mailbox.view, name='sga_mailbox_view'),
            # BOLSA LABORAL
            re_path(r'^preinscrito$', preinscrito.view, name='sga_preinscrito_view'),
            re_path(r'^bolsalaboral$', bolsalaboral.view, name='sga_bolsalaboral_view'),
            re_path(r'^adm_ofertalaboral$', adm_ofertalaboral.view, name='sga_adm_ofertalaboral_view'),
            # CRM
            re_path(r'^crm$', crm.view, name='sga_crm_view'),
            # OTROS
            re_path(r'^datos$', datosiniciales.view, name='sga_datosiniciales_view'),
            re_path(r'^adm_cursoscomplementarios$', adm_cursoscomplementarios.view, name='sga_adm_cursoscomplementarios_view'),
            re_path(r'^adm_conveniopago$', adm_conveniopago.view, name='sga_adm_conveniopago_view'),
            re_path(r'^alu_conveniopago$', alu_conveniopago.view, name='sga_alu_conveniopago_view'),
            re_path(r'^doc_generales$', doc_generales.view, name='sga_doc_generales_view'),
            re_path(r'^doc_credencial$', doc_credencial.view, name='sga_doc_credencial_view'),
            re_path(r'^descargaarchivo$', descargaarchivo.view, name='sga_descargaarchivo_view'),
            re_path(r'^adm_indicadores$', adm_indicadores.view, name='sga_adm_indicadores_view'),
            #estos son los lines de nosotros Misael, Byron
            re_path(r'^alu_anteproyecto$', alu_anteproyecto.view, name='sga_alu_anteproyecto_view'),
            re_path(r'^adm_anteproyecto$', adm_anteproyecto.view, name='sga_adm_anteproyecto_view'),
            re_path(r'^pro_anteproyecto$', pro_anteproyecto.view, name='sga_pro_anteproyecto_view'),
            re_path(r'^pro_tutoriasproyecto$', pro_tutoriasproyecto.view, name='sga_pro_tutoriasproyecto_view'),
            re_path(r'^alu_tutoriasproyecto$', alu_tutoriasproyecto.view, name='sga_alu_tutoriasproyecto_view'),
            re_path(r'^adm_fichaproyecto$', adm_fichaproyecto.view, name='sga_adm_fichaproyecto_view'),
            re_path(r'^adm_periodotitulacion$', adm_periodotitulacion.view, name='sga_adm_periodotitulacion_view'),
            re_path(r'^adm_tipotitulacion$', adm_tipotitulacion.view, name='sga_adm_tipotitulacion_view'),
            re_path(r'^adm_modelotitulacion$', adm_modelotitulacion.view, name='sga_adm_modelotitulacion_view'),
            re_path(r'^adm_alternativatitulacion$', adm_alternativatitulacion.view, name='sga_adm_alternativatitulacion_view'),
            re_path(r'^alu_matriculaciontitulacion$', alu_matriculaciontitulacion.view, name='sga_alu_matriculaciontitulacion_view'),
            re_path(r'^alu_propuestatitulacion$', alu_propuestatitulacion.view, name='sga_alu_propuestatitulacion_view'),
            re_path(r'^adm_prolineainvestigacion$', adm_propuestalineainvestigacion.view, name='sga_adm_propuestalineainvestigacion_view'),
            re_path(r'^adm_laboratoriosacademia$', adm_laboratoriosacademia.view, name='sga_adm_laboratoriosacademia_view'),
            #-------------------URLS COMPLEXIVO------------------
            re_path(r'^adm_cronogramatitulacion$', adm_cronogramatitulacion.view, name='sga_adm_cronogramatitulacion_view'),
            re_path(r'^alu_complexivocurso$', alu_complexivocurso.view, name='sga_alu_complexivocurso_view'),
            re_path(r'^pro_complexivoclase$', pro_complexivoclase.view, name='sga_pro_complexivoclase_view'),
            re_path(r'^adm_complexivoasignatura$', adm_complexivoasignatura.view, name='sga_adm_complexivoasignatura_view'),
            re_path(r'^pro_complexivoexamen$', pro_complexivoexamen.view, name='sga_pro_complexivoexamen_view'),
            re_path(r'^adm_complexivotematica$', adm_complexivotematica.view, name='sga_adm_complexivotematica_view'),
            re_path(r'^adm_aprobartematica$', adm_complexivoaprobartematica.view, name='sga_adm_complexivoaprobartematica_view'),
            re_path(r'^pro_grupoinvestigacion$', pro_grupo_investigacion.view, name='sga_pro_grupo_investigacion_view'),
            re_path(r'^adm_grupoinvestigacion$', adm_grupoinvestigacion.view, name='sga_adm_grupoinvestigacion_view'),
            re_path(r'^adm_tipopublicacion$', adm_tipopublicacion.view, name='sga_adm_tipopublicacion_view'),
            re_path(r'^pro_complexivotematica$', pro_complexivotematica.view, name='sga_pro_complexivotematica_view'),
            re_path(r'^adm_complexivo$', adm_complexivo.view, name='sga_adm_complexivo_view'),
            #GRUPO INVESTIGACION
            re_path(r'^adm_convocatoriainvestigacion$', adm_convocatoriainvestigacion.view, name='sga_adm_convocatoriainvestigacion_view'),
            re_path(r'^pro_solgrupoinvestigacion$', pro_solicitudgrupoinvestigacion.view, name='sga_pro_solicitudgrupoinvestigacion_view'),
            re_path(r'^adm_solaprobar_dr$', adm_solicitudaprobacioninvestigacion_dr.view, name='sga_adm_solicitudaprobacioninvestigacion_dr_view'),
            re_path(r'^adm_solaprobar_inv$', adm_solicitudaprobacioninvestigacion_inv.view, name='sga_adm_solicitudaprobacioninvestigacion_inv_view'),
            #AYUDANTIA CATEDRA
            re_path(r'^adm_ayudantiacatedra$', adm_ayudantiacatedra.view, name='sga_adm_ayudantiacatedra_view'),
            re_path(r'^pro_ayudantiacatedra$', pro_ayudantiacatedra.view, name='sga_pro_ayudantiacatedra_view'),
            re_path(r'^alu_ayudantiacatedra$', alu_ayudantiacatedra.view, name='sga_alu_ayudantiacatedra_view'),
            re_path(r'^dir_ayudantiacatedra$', dir_ayudantiacatedra.view, name='sga_dir_ayudantiacatedra_view'),
            #BECAS
            re_path(r'^adm_becas$', adm_becas.view, name='sga_adm_becas_view'),
            #CASOS DE JUSTIFICACION DE FALTA
            re_path(r'^alu_justificacion_asis$', alu_solicitudjustificacionasistencia.view, name='sga_alu_solicitudjustificacionasistencia_view'),
            re_path(r'^adm_justificacion_asis$', adm_casosjustificacionasistencias.view, name='sga_adm_becas_view'),
            re_path(r'^adm_justificacion_asis_dr$', adm_justificacionasistenciaaprobacion_dr.view, name='sga_adm_becas_view'),
            #PLANIFICACION DE CLASES(SILABOS)
            re_path(r'^adm_planificacionsilabo$', adm_planificacionsilabo.view, name='sga_adm_planificacionclases_view'),
            re_path(r'^alu_becas$', alu_becas.view, name='sga_alu_becas_view'),
            #TIPO DE FORMACIONES(CARRERA)
            re_path(r'^adm_tipoformacion$', adm_tipoformacioncarrera.view, name='sga_adm_tipoformacioncarrera_view'),
            #GIMNACIO y POLIDEPORTIVO y CRAI
            re_path(r'^adm_gimnasio$', adm_gimnasio.view, name='sga_adm_gimnasio_view'),
            re_path(r'^adm_crai$', adm_crai.view, name='sga_adm_crai_view'),
            re_path(r'^adm_crai_pantalla$', adm_crai_pantalla.view, name='sga_adm_crai_pantalla_view'),
            re_path(r'^adm_crai_directores$', adm_crai_directores.view, name='sga_adm_crai_directores_view'),
            re_path(r'^alu_mundocrai$', alu_mundocrai.view, name='sga_alu_mundocrai_view'),
            re_path(r'^adm_crai_actividades$', adm_crai_actividades.view, name='sga_adm_crai_actividades_view'),
            re_path(r'^adm_configuracion_mundocrai$', adm_configuracion_mundocrai.view, name='sga_adm_configuracion_mundocrai_view'),
            re_path(r'^adm_crai_biblioteca$', adm_crai_biblioteca.view, name='sga_adm_crai_biblioteca_view'),
            re_path(r'^adm_polideportivo$', adm_polideportivo.view, name='sga_adm_polideportivo_view'),
            #Libro fotocopiado
            re_path(r'^adm_librofotocopiado$', adm_librofotocopiado.view, name='sga_adm_librofotocopiado_view'),
            # CONSEJERIAS
            re_path(r'^pro_consejerias$', pro_consejerias.view, name=u'sga_pro_consejerias_view'),
            re_path(r'^alu_consejerias$', alu_consejerias.view, name=u'sga_alu_consejerias_view'),
            re_path(r'^adm_docenteconsejeria$', adm_docenteconsejeria.view, name=u'sga_adm_docenteconsejeria_view'),
            #CONVENIOS
            re_path(r'^adm_convenioempresa$', adm_convenioempresa.view, name=u'sga_adm_convenioempresa_view'),
            re_path(r'^alu_convenioempresa$', adm_convenioempresa.view, name=u'sga_alu_convenioempresa_view'),#alu
            re_path(r'^dir_convenios$', dir_convenios.view, name=u'sga_dir_convenios_view'),#alu
            #PRE-INSCRIPCIONES DE PRACTICAS PRE-PROFESIONALES
            re_path(r'^alu_preinscripcioppp$', alu_preinscripcionppp.view, name=u'sga_alu_preinscripcioppp_view'),
            re_path(r'^alu_practicassaludinscripcion', alu_practicassaludinscripcion.view, name=u'sga_alu_practicassaludinscripcion_view'),
            #Modulo de sanciones de estudiantes
            re_path(r'^adm_sancionestudiante', adm_sancionestudiante.view, name=u'sga_adm_sancionestudiante_view'),
            #Modulo modalidada virtual
            re_path(r'^adm_aprobarsemanavirtual', adm_aprobarsemanavirtual.view, name=u'sga_adm_aprobarsemanavirtual_view'),
            re_path(r'^virtual_soporte_online$', virtual_soporte_online.view, name=u'sga_virtual_soporte_online_view'),
            re_path(r'^virtual_admsoporte_online$', virtual_admsoporte_online.view, name=u'sga_virtual_soporte_online_view'),
            re_path(r'^adm_gestionvideo', adm_gestionvideo.view, name=u'sga_adm_gestionvideo_view'),
            re_path(r'^adm_aprobarvideoclasevirtual', adm_aprobarvideoclasevirtual.view, name=u'sga_adm_aprobarvideoclasevirtual_view'),
            #reporte sakai
            re_path(r'^campusvirtual$', sakai.view, name=u'sga_virtual_soporte_online_view'),
            re_path(r'^mooc_campusvirtual$', mooc_campusvirtual.view, name=u'sga_virtual_soporte_online_view'),
            re_path(r'^contenidosonline$', contenidosonline.view, name=u'sga_contenidosonline_view'),
            #formulario ingreso de cursos
            re_path(r'^inscripcionescursos$', inscripcionescursos.view, name='sga_inscripcionescursos_view'),
            re_path(r'^inscripcionescursos_edcon$', inscripcionescursos_edcon.view, name='sga_inscripcionescursos_edcon_view'),
            re_path(r'^testunemi$', testunemi.view, name='sga_testunemi_view'),
            re_path(r'^certificadovalido$', certificadovalido.view, name='sga_certificadovalido_view'),
            # INSCRIPCIONES CONGRESOS
            re_path(r'^inscripcionescongresos$', inscripcionescongresos.view, name='sga_inscripcionescongresos_view'),
            re_path(r'^congresos$', congresos.view, name='sga_congresos_view'),

            # MANUAL DE USUARIOS
            re_path(r'^manualusuario$', manualusuario.view, name='sga_manualusuario_view'),

            # LINEA DE TIEMPO
            re_path(r'^lineatiempo$', lineatiempo.view, name='sga_lineatiempo_view'),

            # ENCUESTA BIENESTAR
            re_path(r'^encuestaparentesco$', encuestaparentesco.view, name='sga_encuestaparentesco_view'),

            # ENCUESTA GRUPO ESTUDIANTES
            re_path(r'^adm_encuestagrupoestudiantes$', adm_encuestagrupoestudiantes.view, name='sga_encuestagrupoestudiantes_view'),

            # PLAAN DE PRACTICAS PRE PROFESIONALES
            re_path(r'^adm_planpractica$', adm_planpractica.view, name='sga_adm_planpractica_view'),
            # DEVOLUCION DE DINERO
            re_path(r'^alu_devoluciondinero$', alu_devoluciondinero.view, name='sga_alu_devoluciondinero_view'),
            # REFINANCIAMIENTO DEUDAS POSGRADO
            re_path(r'^alu_refinanciamientoposgrado$', alu_refinanciamientoposgrado.view, name='sga_alu_refinanciamientoposgrado_view'),
            re_path(r'^adm_refinanciamientoposgrado$', adm_refinanciamientoposgrado.view, name='sga_adm_refinanciamientoposgrado_view'),
            # CONVALIDACION DE PRACTICAS Y VINCULACION
            re_path(r'^adm_convalidacionpractica$', adm_convalidacionpractica.view, name='sga_adm_convalidacionpractica_view'),
            re_path(r'^alu_convalidacionpractica$', alu_convalidacionpractica.view, name='sga_alu_convalidacionpractica_view'),
            #SOLICITUDES PARA MOVILIDAD
            re_path(r'^alu_movilidad$', alu_movilidad.view, name='sga_alu_movilidad_view'),
            #SECRETARIA GENERAL - VALIDACIÓN DE REQUISITOS DE TITULACIÓN
            re_path(r'^adm_validarrequisitostitulacion$', adm_validarrequisitostitulacion.view, name='sga_adm_validarrequisitostitulacion_view'),
            #NOTIFICACIONES
            re_path(r'^notificacion$', notificacion.view, name='sga_notificacion_view'),
            #UBICACION MAPA
            re_path(r'^adm_ubicacionestudiantes$', adm_ubicacionestudiantes.view, name='sga_ubicacionestudiantes'),
            #PROCESOS BATCH
            re_path(r'^adm_tasks$', adm_tasks.view, name='sga_adm_tasks_view'),

            re_path(r'^solicitud$', solicitudexterna.view, name='sga_solicitudexterna_view'),
            re_path(r'^enlace_descarga$', enlace_descarga.view, name='sga_enlace_descarga_view'),
            re_path(r'^monitoreo$', monitoreo.view, name='sga_monitoreo_view'),
            #INGRESO ACTA
            re_path(r'^adm_ingresoacta$', adm_ingresoacta.view, name='sga_adm_ingresoacta_view'),
            #EVALUACIONTH
            re_path(r'^adm_evaluacion$', adm_evaluacion.view, name='sga_adm_evaluacion_view'),
            re_path(r'^adm_misevaluaciones$', adm_misevaluaciones.view, name='sga_adm_evaluacion_view'),
            #VENTANA DIRECTOR
            re_path(r'^dir_cronograma$', dir_cronograma.view, name='sga_dir_cronograma'),
            #MANUAL DE USUARIO PARA ADMINISTRAR
            re_path(r'^adm_manual_usuario', adm_manual_usuario.view, name='sga_adm_manual_usuario'),
            #PROMOCIÓN DOCENTE
            re_path(r'^adm_promociondocente$', adm_promociondocente.view, name='sga_adm_promociondocente'),
            #VERIFICAR DOCUMENTOS BECAS
            re_path(r'^adm_verificacion_documento$', adm_verificacion_documento.view, name='sga_adm_verificacion_documento'),
            re_path(r'^adm_verificacion_documento/artistas$', adm_verificacion_documento_artistas.view, name='sga_adm_verificacion_documento_artistas'),
            re_path(r'^adm_verificacion_documento/externos$', adm_verificacion_documento_externos.view, name='sga_adm_verificacion_documento_externos'),
            re_path(r'^adm_verificacion_documento/deportistas$', adm_verificacion_documento_deportistas.view, name='sga_adm_verificacion_documento_deportistas'),
            re_path(r'^adm_verificacion_documento/discapacitados$', adm_verificacion_documento_discapacitados.view, name='sga_adm_verificacion_documento_discapacitados'),
            re_path(r'^adm_verificacion_documento/etnias$', adm_verificacion_documento_etnias.view, name='sga_adm_verificacion_documento_etnias'),
            re_path(r'^adm_verificacion_documento/migrantes$', adm_verificacion_documento_migrantes.view, name='sga_adm_verificacion_documento_migrantes'),
            re_path(r'^adm_verificacion_documento/hojas_vida$', adm_verificacion_documento_hojas_vida.view, name='adm_verificacion_documento_hojas_vida'),
            re_path(r'^adm_verificacion_documento/enfermedad$', adm_verificacion_documento_enfermedades.view, name='adm_verificacion_documento_enfermedades'),

            #ASESORAMIENTO DE SERVICIOS DE ESTUDIOS ESTADISTICOS
            re_path(r'^adm_asesoramientosee$', adm_asesoramientosee.view, name='sga_adm_asesoramientosee'),
            re_path(r'^firma$', firma.view, name='sga_firma'),
            re_path(r'^adm_aprobaringles$', adm_aprobaringles.view, name='sga_aprobar_ingles'),
            re_path(r'^comunicacion_institucional', comunicacion_institucional.view, name='sga_comunicacion_institucional'),
            re_path(r'^solicitud_productos', solicitud_productos.view, name='sga_solicitud_productos'),
            re_path(r'^mis_activos', mis_activos.view, name='sga_mis_activos'),
            re_path(r'^gestion_operaciones', gestion_operaciones_tecnologicas.view, name='sga_gestion_operaciones'),
            re_path(r'^operaciones_prestamoactivos', operaciones_prestamoactivos.view, name='sga_operaciones_prestamoactivos'),

           #INSCRIPCION CAPACITACION DOCENTE
            re_path(r'^pro_capacitacion$', pro_capacitacion.view, name='sga_pro_capacitacion_view'),

            #INSIGNIAS
            re_path(r'^insignia$', insignias.view, name='sga_insignia_view'),
            re_path(r'^adm_insignia$', adm_insignia.view, name='sga_adm_insignia_view'),
            re_path(r'^simuladorcostocarrera$', simuladorcostocarrera.view, name='sga_simuladorcostocarrera_view'),

            re_path(r'^uxplora$', uxplora.view, name='sga_uxplora_view'),

            re_path(r'^', include('sga.views.urls')),
           ]
