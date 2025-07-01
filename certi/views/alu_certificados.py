# -*- coding: latin-1 -*-
import os
from datetime import datetime
import code128
import pyqrcode
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import SITE_STORAGE
from sga.commonviews import adduserdata, obtener_reporte
from sga.models import Matricula, Inscripcion, Certificados
from certi.models import Certificado, CertificadoUnidadCertificadora, CertificadoAsistenteCertificadora
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavecertificados
from django.db import connections
from django.db import transaction
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'certificadomatricula':
            try:
                from itertools import chain
                data['matricula'] = matricula = Matricula.objects.get(id=request.POST['matriculaid'], retiradomatricula=False,status=True)
                # data['materiaasignada'] = materiaasignada = matricula.materiaasignada_set.filter(status=True)
                cursor = connections['sga_select'].cursor()
                sql = """
                SELECT a.nombre,mat.creditos,(case when (select cc1.coordinacion_id from sga_malla ma1, sga_coordinacion_carrera cc1  where ma1.id=ml.malla_id and ma1.carrera_id=cc1.carrera_id)=9 then 'NIVELACION' else nm.nombre end ) AS nivel,
                array_to_string(ARRAY(select CASE WHEN cl.dia=1 THEN 'Lunes' WHEN cl.dia=2 THEN 'Martes' WHEN cl.dia=3 THEN 'Miercoles'
                WHEN cl.dia=4 THEN 'jueves' WHEN cl.dia=5 THEN 'viernes' WHEN cl.dia=6 THEN 'Sabado' WHEN cl.dia=7 THEN 'Domingo'
                END  || '('||t.comienza||' - '||t.termina||')'
                from sga_clase cl
                inner join sga_turno t on t.id=cl.turno_id
                where cl.materia_id=ma.materia_id
                order by cl.dia,t.comienza
                ),', ') as Horario
                from sga_matricula m
                inner join sga_materiaasignada ma on ma.matricula_id=m.id
                inner join sga_materia mat on mat.id=ma.materia_id
                inner join sga_asignatura a on a.id=mat.asignatura_id
                inner join sga_asignaturamalla ml on ml.id=mat.asignaturamalla_id
                inner join sga_nivelmalla nm on nm.id=ml.nivelmalla_id
                where m.id=%s and 
                ma.id not in(select mr.materiaasignada_id 
                from sga_materiaasignadaretiro mr 
                where mr.materiaasignada_id=ma.id)
                order by a.nombre
                """ % matricula.id
                cursor.execute(sql)
                results = cursor.fetchall()
                notaporcen = "0"
                qrname = 'qrcer_mat_' + str(matricula.id)
                codigomatri = encrypt(matricula.id)
                # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificadomatricula', 'qr'))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                # url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/evaluaciondocente/' + qrname + '.pdf')
                url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/certificadomatricula/' + qrname + '.pdf')
                # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/certificadomatricula/' + qrname + '.pdf')
                # url = pyqrcode.create('http://127.0.0.1:8000/certificadovalido?codi='+codigomatri)
                # url = pyqrcode.create('http://sga.unemi.edu.ec/certificadovalido?codi='+codigomatri)
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                # imagebarcode = code128.image(notaporcen).save(folder + qrname + "_bar.png")
                data['qrname'] = 'qr' + qrname
                data['storage'] = SITE_STORAGE
                return conviert_html_to_pdfsavecertificados('alu_certificados/certificadomatricula_pdf.html',
                                                            {'pagesize': 'A4',
                                                             'matricula': matricula,
                                                             'hoy': datetime.now().date(),
                                                             'qrname': 'qr' + qrname,
                                                             'materiaasignada': results},
                                                            qrname + '.pdf',
                                                            'certificadomatricula')
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'certificadoasistenciaxmat':
            try:
                from itertools import chain
                data['matricula'] = matricula = Matricula.objects.get(id=request.POST['matriculaid'], retiradomatricula=False,status=True)
                # data['materiaasignada'] = materiaasignada = matricula.materiaasignada_set.filter(status=True)
                cursor = connections['sga_select'].cursor()
                sql = """
                SELECT
                 sga_asignatura."nombre" AS sga_asignatura_nombre,
                 sga_nivelmalla."nombre" AS sga_nivelmalla_nombre,
                 sga_materiaasignada."matricula_id" AS sga_materiaasignada_matricula_id,
                 sga_materiaasignada."asistenciafinal" AS sga_materiaasignada_asistenciafinal,
                 sga_materia."inicio" AS sga_materia_inicio,
                 sga_materia."fin" AS sga_materia_fin,
                array_to_string(ARRAY(
                select CASE WHEN cl.dia=1 THEN 'Lunes' WHEN cl.dia=2 THEN 'Martes' WHEN cl.dia=3 THEN 'Miercoles'
                WHEN cl.dia=4 THEN 'Jueves' WHEN cl.dia=5 THEN 'Viernes' WHEN cl.dia=6 THEN 'Sabado' WHEN cl.dia=7 THEN 'Domingo'
                END  || '('||t.comienza||' - '||t.termina||')'
                from sga_clase cl
				inner join sga_turno t on t.id=cl.turno_id
                where cl.materia_id=sga_materiaasignada.materia_id
                order by cl.dia,t.comienza
                ),', ') as Horario
                FROM
                 "public"."sga_asignatura" sga_asignatura RIGHT OUTER JOIN "public"."sga_asignaturamalla" sga_asignaturamalla ON sga_asignatura."id" = sga_asignaturamalla."asignatura_id"
                 RIGHT OUTER JOIN "public"."sga_materia" sga_materia ON sga_asignaturamalla."id" = sga_materia."asignaturamalla_id"
                 LEFT OUTER JOIN "public"."sga_nivelmalla" sga_nivelmalla ON sga_asignaturamalla."nivelmalla_id" = sga_nivelmalla."id"
                 RIGHT OUTER JOIN "public"."sga_materiaasignada" sga_materiaasignada ON sga_materia."id" = sga_materiaasignada."materia_id"
                WHERE
                sga_materiaasignada.matricula_id = %s
                ORDER BY
                sga_asignatura."nombre" ASC
                """ % matricula.id
                cursor.execute(sql)
                results = cursor.fetchall()
                notaporcen = "0"
                qrname = 'qrcer_asis_' + str(matricula.id)
                codigomatri = encrypt(matricula.id)
                # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificadomatricula', 'qr'))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                # url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/evaluaciondocente/' + qrname + '.pdf')
                # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/certificadomatricula/' + qrname + '.pdf')
                # url = pyqrcode.create('http://127.0.0.1:8000/certificadovalido?codi='+codigomatri)
                url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/certificadomatricula/' + qrname + '.pdf')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                # imagebarcode = code128.image(notaporcen).save(folder + qrname + "_bar.png")
                data['qrname'] = 'qr' + qrname
                data['storage'] = SITE_STORAGE
                return conviert_html_to_pdfsavecertificados('alu_certificados/certificadoasistenciaxmat_pdf.html',
                                                            {'pagesize': 'A4',
                                                             'matricula': matricula,
                                                             'hoy': datetime.now().date(),
                                                             'qrname': 'qr' + qrname,
                                                             'asistenciamaterias': results},
                                                            qrname + '.pdf',
                                                            'certificadomatricula')
                # if valida:
                #     os.remove(rutaimg)
                #
                # return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'certificadoasistenciaxperiodo':
            try:
                from itertools import chain
                data['matricula'] = matricula = Matricula.objects.get(id=request.POST['matriculaid'],  retiradomatricula=False, status=True)
                # data['materiaasignada'] = materiaasignada = matricula.materiaasignada_set.filter(status=True)
                cursor = connections['sga_select'].cursor()
                sql = """
                select round(avg(asistenciafinal),0)
                 from sga_materiaasignada
                 where matricula_id=%s
                """ % matricula.id
                cursor.execute(sql)
                results = cursor.fetchall()
                notaporcen = "0"
                qrname = 'qrcer_asisxper_' + str(matricula.id)
                codigomatri = encrypt(matricula.id)
                # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                folder = os.path.join(
                    os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificadomatricula', 'qr'))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/certificadomatricula/' + qrname + '.pdf')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = 'qr' + qrname
                data['storage'] = SITE_STORAGE
                return conviert_html_to_pdfsavecertificados(
                    'alu_certificados/certificadoasistenciaxperiodo_pdf.html',
                    {'pagesize': 'A4',
                     'matricula': matricula,
                     'hoy': datetime.now().date(),
                     'qrname': 'qr' + qrname,
                     'asistenciaxperiodo': results},
                    qrname + '.pdf',
                    'certificadomatricula')
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'certificadomodalidadestudio':
            try:
                from itertools import chain
                data['inscripcionestudiantes'] = inscripcionestudiante = Inscripcion.objects.get(pk=request.POST['codiinscripcion'], status=True)
                qrname = 'qrcer_modalest_' + str(inscripcionestudiante.id)
                codigoinscripcion = encrypt(inscripcionestudiante.id)
                # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                folder = os.path.join(
                    os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificadomatricula', 'qr'))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                url = pyqrcode.create(
                    'http://sga.unemi.edu.ec/certificadovalido?action=certificadomodalidadestudio&codi=' + codigoinscripcion)
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = 'qr' + qrname
                data['storage'] = SITE_STORAGE
                return conviert_html_to_pdfsavecertificados(
                    'alu_certificados/certificadomodalidadestudio_pdf.html',
                    {'pagesize': 'A4',
                     'inscripcion': inscripcionestudiante,
                     'hoy': datetime.now().date(),
                     'qrname': 'qr' + qrname},
                    qrname + '.pdf',
                    'certificadomatricula')
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'certificadonosancionado':
            try:
                from itertools import chain
                data['matricula'] = matricula = Matricula.objects.get(id=request.POST['matriculaid'],  retiradomatricula=False, status=True)
                cursor = connections['sga_select'].cursor()
                sql = """
                SELECT
                 sga_persona."nombres"||' '||sga_persona."apellido1"||' '||sga_persona."apellido2"
                  AS nombrecompleto,
                 CASE WHEN to_char(now(),'mm')='01'
                  THEN 'Enero'WHEN to_char(now(),'mm')='02'
                  THEN 'Febrero'WHEN to_char(now(),'mm')='03'THEN 'Marzo'WHEN to_char(now(),'mm')='04'THEN 'Abril'WHEN to_char(now(),'mm')='05'THEN 'Mayo'WHEN to_char(now(),'mm')='06'THEN 'Junio'WHEN to_char(now(),'mm')='07'THEN 'Julio'WHEN to_char(now(),'mm')='08'THEN 'Agosto'WHEN to_char(now(),'mm')='09'THEN 'Septiembre'WHEN to_char(now(),'mm')='10'THEN 'Octubre'WHEN to_char(now(),'mm')='11'THEN 'Noviembre'WHEN to_char(now(),'mm')='12'THEN 'Diciembre'END AS mes,
                 to_char(now(),'dd') AS dia,
                 to_char(now(),'yyyy') AS anio,
                 to_char(now(),'mm') AS nmes,
                 sga_matricula."inscripcion_id" AS sga_matricula_inscripcion_id,
                 sga_carrera."nombre" AS carrera,
                 sga_persona."cedula" AS cedula,
                 sga_modalidad."nombre" AS modalidad,
                 sga_nivelmalla."nombre" AS nivel,
                 sga_sesion."nombre" AS sesion,
                 sga_periodo."nombre" AS periodo_activo,
                 sga_periodo."activo" AS activo,
                 sga_sede."nombre" AS sga_sede_nombre,
                 sga_matricula."id" AS sga_matricula_id,
                 sga_inscripcion."id" AS sga_inscripcion_id,
                 sga_inscripcionnivel."id" AS sga_inscripcionnivel_id,
                 sga_inscripcionnivel."inscripcion_id" AS sga_inscripcionnivel_inscripcion_id,
                 sga_inscripcionnivel."nivel_id" AS sga_inscripcionnivel_nivel_id,
                 sga_matricula."fecha" AS sga_matricula_fecha,
                 sga_matricula."hora" AS sga_matricula_hora,
                 sga_carrera."mencion" AS sga_carrera_mencion,
                 sga_coordinacion."nombre" AS facultad,
                 sancion.id as sancionado
                 FROM
                 "public"."sga_nivel" sga_nivel RIGHT OUTER JOIN "public"."sga_matricula" sga_matricula ON sga_nivel."id" = sga_matricula."nivel_id"
                 LEFT OUTER JOIN "public"."sga_inscripcion" sga_inscripcion ON sga_matricula."inscripcion_id" = sga_inscripcion."id"
                 LEFT OUTER JOIN "public"."sga_carrera" sga_carrera ON sga_inscripcion."carrera_id" = sga_carrera."id"
                 LEFT OUTER JOIN "public"."sga_persona" sga_persona ON sga_inscripcion."persona_id" = sga_persona."id"
                 LEFT OUTER JOIN "public"."sga_modalidad" sga_modalidad ON sga_inscripcion."modalidad_id" = sga_modalidad."id"
                 LEFT OUTER JOIN "public"."sga_sesion" sga_sesion ON sga_inscripcion."sesion_id" = sga_sesion."id"
                 LEFT OUTER JOIN "public"."sga_inscripcionnivel" sga_inscripcionnivel ON sga_inscripcion."id" = sga_inscripcionnivel."inscripcion_id"
                 LEFT OUTER JOIN "public"."sga_nivelmalla" sga_nivelmalla ON sga_inscripcionnivel."nivel_id" = sga_nivelmalla."id"
                 LEFT OUTER JOIN "public"."sga_periodo" sga_periodo ON sga_nivel."periodo_id" = sga_periodo."id"
                 LEFT OUTER JOIN "public"."sga_sede" sga_sede ON sga_nivel."sede_id" = sga_sede."id"
                 LEFT OUTER JOIN "public"."sga_coordinacion_carrera" sga_coordinacion_carrera ON sga_coordinacion_carrera."carrera_id" = sga_carrera."id"
                 LEFT OUTER JOIN "public"."sga_coordinacion" sga_coordinacion ON sga_coordinacion."id" = sga_coordinacion_carrera."coordinacion_id"
                 left join sga_sacionestudiante  sancion on sancion.inscripcion_id = sga_inscripcion.id
                 WHERE
                 sga_matricula."id" = %s
                """ % matricula.id
                cursor.execute(sql)
                results = cursor.fetchall()
                notaporcen = "0"
                qrname = 'qrcer_nosancion_' + str(matricula.id)
                codigomatri = encrypt(matricula.id)
                # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                folder = os.path.join(
                    os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificadomatricula', 'qr'))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/certificadomatricula/' + qrname + '.pdf')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = 'qr' + qrname
                data['storage'] = SITE_STORAGE
                return conviert_html_to_pdfsavecertificados(
                    'alu_certificados/certificadonosancionado_pdf.html',
                    {'pagesize': 'A4',
                     'matricula': matricula,
                     'hoy': datetime.now().date(),
                     'qrname': 'qr' + qrname,
                     'sancionalumno': results},
                    qrname + '.pdf',
                    'certificadomatricula')
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'certificadonotasxperiodo':
            try:
                matricula = Matricula.objects.get(pk=request.POST['matriculaid'], retiradomatricula=False, status=True)
                materiaasignada = matricula.materiaasignada_set.filter(retiramateria=False, status=True)
                qrname = 'qrcer_notaxper_' + str(matricula.id)
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificadomatricula', 'qr'))
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/certificadomatricula/' + qrname + '.pdf')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = 'qr' + qrname
                data['storage'] = SITE_STORAGE
                return conviert_html_to_pdfsavecertificados(
                    'alu_certificados/certificadonotasxperiodo_pdf.html',
                    {'pagesize': 'A4',
                     'matricula': matricula,
                     'hoy': datetime.now().date(),
                     'qrname': 'qr' + qrname,
                     'materiaasignada': materiaasignada},
                    qrname + '.pdf',
                    'certificadomatricula')
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Certificados'
                if inscripcion.matricula_set.filter(status=True).exists():
                    # data['matriculas'] = inscripcion.matricula_set.filter(status=True).order_by("-nivel__periodo__inicio")
                    data['matriculas'] = Matricula.objects.filter(inscripcion=inscripcion, status=True).order_by("-nivel__periodo__inicio")
                else:
                    data['matriculas'] = []
                if 'matriculaid' in request.GET:
                    data['matricula'] = matricula = Matricula.objects.get(pk=int(request.GET['matriculaid']))
                    data['matriculaid'] = matricula.id
                else:
                    data['matricula'] = []
                    data['matriculaid'] = 0

                data['inscripcion'] = inscripcion.id
                data['coordinacion'] = coordinacionid = inscripcion.carrera.coordinacion_set.all()[0].id
                data['certificados'] = Certificados.objects.filter(status=True)

                # data['reporte_0'] = obtener_reporte('certificado_matricula_alumno_unemi')
                data['reporte_0'] = obtener_reporte('certificado_matricula_alumno_unemi_digital')
                # data['reporte_1'] = obtener_reporte('certificado_asistencia_alumno_unemi')
                data['reporte_1'] = obtener_reporte('certificado_asistencia_alumno_unemi_digital')
                # data['reporte_2'] = obtener_reporte('certificado_asistenciaperiodo_alumno_unemi')
                data['reporte_2'] = obtener_reporte('certificado_asistenciaperiodo_alumno_unemi_digital')
                data['reporte_3'] = obtener_reporte('certificado_modalidad_estudio_unemi') # no esta en la matriz y no habilitado
                # data['reporte_4'] = obtener_reporte('certificado_sancion_alumno_unemi')
                data['reporte_4'] = obtener_reporte('certificado_sancion_alumno_unemi_digital')
                data['reporte_5'] = obtener_reporte('certificado_costo_carrera_unemi') # no esta en la matriz y no habilitado
                data['reporte_6'] = obtener_reporte('certificado_malla_carrera_unemi') # no habilitado
                data['reporte_7'] = obtener_reporte('certificado_plan_estudios_unemi') # no habilitado
                data['reporte_8'] = obtener_reporte('certificado_programa_analitico_unemi') # no habilitado
                data['reporte_9'] = obtener_reporte('certificado_ficha_estudiantil') # no habilitado
                # data['reporte_10'] = obtener_reporte('certificado_no_adeudo') if coordinacionid == 7 else obtener_reporte('certificado_no_adeudotn')
                data['reporte_10'] = obtener_reporte('certificado_no_adeudo_digital') if coordinacionid == 7 else obtener_reporte('certificado_no_adeudotn_digital')
                data['reporte_11'] = obtener_reporte('certificado_modulos_ingles')
                data['reporte_12'] = obtener_reporte('certificado_modulos_computacion')
                data['reporte_13'] = obtener_reporte('certificado_vinculacion_alumno_unemi') # no habilitado
                data['reporte_14'] = obtener_reporte('certificado_penultimo_malla')
                data['reporte_15'] = obtener_reporte('certificado_toda_malla')
                # data['reporte_16'] = obtener_reporte('certificado_matricula_alumno_ipec')
                data['reporte_16'] = obtener_reporte('certificado_matricula_alumno_ipec_digital')
                data['reporte_17'] = obtener_reporte('certificado_calificaciones_alumno_unemi_digital')

                data['reporte_18'] = obtener_reporte('certificado_beca_alumno_unemi_digital')
                data['reporte_19'] = obtener_reporte('certificado_estar_apto_internado_rotativo')

                data['tienebeca'] = inscripcion.tiene_becas_asignadas()
                filter_carreras = CertificadoAsistenteCertificadora.objects.filter(status=True, carrera__id=inscripcion.carrera.id, asistente__firmapersona__tipofirma=2)
                filter_unidades = CertificadoUnidadCertificadora.objects.filter(coordinacion_id=coordinacionid, status=True, pk__in=filter_carreras.values_list('unidad_certificadora_id', flat=True).distinct(), responsable__firmapersona__tipofirma=2)
                certificado_internos_1 = Certificado.objects.filter(status=True, visible=True, tipo_origen=1, destino=1, pk__in=filter_unidades.values_list('certificado_id', flat=True).distinct())
                filter_unidades = CertificadoUnidadCertificadora.objects.filter(coordinacion__isnull=True, status=True, responsable__firmapersona__tipofirma=2)
                certificado_internos_2 = Certificado.objects.filter(status=True, visible=True, tipo_origen=1, destino=1, coordinacion__in=inscripcion.carrera.coordinacion_set.all(), pk__in=filter_unidades.values_list('certificado_id', flat=True).distinct()).exclude(pk__in=certificado_internos_1.values_list('id', flat=True).distinct())
                certificado_internos = certificado_internos_1 | certificado_internos_2
                filter_unidades = CertificadoUnidadCertificadora.objects.filter(coordinacion__isnull=True, status=True, responsable__firmapersona__tipofirma=2)
                certificado_externos = Certificado.objects.filter(status=True, visible=True, tipo_origen=2, destino=1, coordinacion__in=inscripcion.carrera.coordinacion_set.all(), pk__in=filter_unidades.values_list('certificado_id', flat=True).distinct())
                data['certificado_internos'] = certificado_internos
                data['certificado_externos'] = certificado_externos
                if 'v' in request.GET and int(request.GET['v']) == 1:
                    return render(request, "alu_certificados/view.html", data)
                return render(request, "alu_certificados/view_new.html", data)

            except Exception as ex:
                HttpResponseRedirect("/?info=%s" % ex)
