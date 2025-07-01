# coding=utf-8
from __future__ import division

import os
from datetime import datetime, timedelta

import pyqrcode
from django.template.loader import get_template
from django.template import Context
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Avg, Q
from decimal import Decimal
from django.db import connections, transaction
from django.contrib.auth.decorators import login_required
from posgrado.models import InscripcionCohorte, CambioAdmitidoCohorteInscripcion, ConfigFinanciamientoCohorte, \
    GarantePagoMaestria, Revision, RecordatorioPagoMaestrante, Informe, ConfiguraInformePrograma, Contrato, \
    CohorteMaestria
from sagest.models import CapConfiguracionIpec, PersonaDepartamentoFirmas, Rubro, Departamento
from settings import SITE_STORAGE, MEDIA_URL, DEBUG
from sga.funciones import numero_a_letras, null_to_decimal, null_to_numeric, generar_nombre
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, download_html_to_pdf, conviert_html_to_pdfsaveadmitidos, \
    conviert_html_to_pdfsavecontratomae, conviert_html_to_pdfsaveactas, conviert_html_to_pdfsaveactagrado, \
    html_to_pdfsave_informemensualdocente, conviert_html_to_pdf_titulacion_exa_complexivo, \
    download_html_to_pdf_get_content, conviert_html_to_pdf_save_file_model
from sga.models import ProfesorMateria, CoordinadorCarrera, HistorialaprobacionTarea, HistorialaprobacionForo, \
    HistorialaprobacionTareaPractica, HistorialaprobacionDiapositiva, HistorialaprobacionGuiaEstudiante, \
    HistorialaprobacionGuiaDocente, HistorialaprobacionCompendio, HistorialaprobacionTest, FirmaPersona, Malla, \
    ComplexivoDetalleGrupo, RubricaTitulacion, RubricaTitulacionCabPonderacion, ModeloRubricaTitulacion, \
    CalificacionDetalleModeloRubricaTitulacion, CalificacionDetalleRubricaTitulacion, Graduado, \
    FirmaCertificadoSecretaria, TemaTitulacionPosgradoMatricula, RubricaTitulacionPosgrado, \
    DetalleRubricaTitulacionPosgrado, RubricaTitulacionCabPonderacionPosgrado, MESES_CHOICES, InformeMensualDocentesPPP, Notificacion,\
    TemaTitulacionPosgradoMatriculaCabecera, ItinerarioMallaEspecilidad, MateriaAsignada, MateriaTitulacion, Matricula, Inscripcion, Materia, CriterioDocenciaPeriodo, DetalleDistributivo, CriterioInvestigacionPeriodo, CriterioGestionPeriodo, ConfiguracionTitulacionPosgrado, CargoInstitucion, Egresado, PerfilInscripcion, CertificadoIdioma, PracticasPreprofesionalesInscripcion, RecordAcademico, AsignaturaMalla

from sagest.models import DistributivoPersona
from inno.models import TipoFormaPagoPac, GrupoTitulacionIC, FirmaGrupoTitulacion
from secretaria.models import Solicitud, IntegrantesCronogramaTituEx
unicode = str


# @login_required(redirect_field_name='ret', login_url='/loginsga')
def evidenciassilabosxcarrera(periodo, persona):
    data = {}
    data['persona'] = persona
    listadcarr = CoordinadorCarrera.objects.values_list('carrera_id').filter(persona=persona, periodo=periodo)
    data['profesormaterias'] = ProfesorMateria.objects.filter(activo=True, status=True, materia__nivel__periodo__visible=True, materia__nivel__periodo=periodo, materia__asignaturamalla__malla__carrera__in=listadcarr).distinct('materia').order_by('materia')
    return conviert_html_to_pdf(
        'template_htmlfree/evidenciasilabos_pdf.html',
        {
            'pagesize': 'A4',
            'datos': data,
        }
    )


def totalestutoriasacademicas(periodo, profesor):
    data = {}
    lista = []
    data['periodo'] = periodo
    data['profesor'] = profesor
    # cursor = connections['default'].cursor()
    data['profesormaterias'] = profesormaterias = profesor.profesormateria_set.select_related('materia').filter(status=True, activo=True, materia__nivel__periodo=periodo).exclude(tipoprofesor__id__in=[8]).order_by('materia')
    # for proma in profesormaterias:
    #     # total = profesor.solicitudtutoriaindividual_set.select_related().filter(profesor=profesor, materiaasignada__materia=proma.materia, status=True)
    #     querynsemana = """
    #         SELECT numsemana,
    #         (
    #         (
    #         SELECT rangofecha FROM (
    #         SELECT CURRENT_DATE + GENERATE_SERIES(inicio- CURRENT_DATE, fin - CURRENT_DATE ) as rangofecha,
    #         extract(week FROM CURRENT_DATE + generate_series(inicio- CURRENT_DATE, fin - CURRENT_DATE )) AS nsemana
    #         FROM sga_materia WHERE id =%s) fecha1
    #         WHERE nsemana=listasemana.numsemana
    #         ORDER BY rangofecha ASC
    #         LIMIT 1
    #         )
    #         ) AS fechaini,
    #         (
    #         (
    #         SELECT rangofecha FROM (
    #         SELECT CURRENT_DATE + GENERATE_SERIES(inicio- CURRENT_DATE, fin - CURRENT_DATE ) as rangofecha,
    #         extract(week FROM CURRENT_DATE + generate_series(inicio- CURRENT_DATE, fin - CURRENT_DATE )) AS nsemana
    #         FROM sga_materia WHERE id =%s) fecha1
    #         WHERE nsemana=listasemana.numsemana
    #         ORDER BY rangofecha desc
    #         LIMIT 1
    #         )
    #         ) AS fechafin
    #
    #         FROM (
    #         SELECT distinct extract(week FROM CURRENT_DATE + generate_series(inicio- CURRENT_DATE, fin - CURRENT_DATE )) AS numsemana
    #         FROM sga_materia WHERE id =%s
    #         ORDER BY 1)
    #         AS listasemana
    #
    #     """% (proma.materia.id,proma.materia.id,proma.materia.id)
    #     cursor.execute(querynsemana)
    #     listadonsemana = cursor.fetchall()
    #     for nsemanas in listadonsemana:
    #         numerosemana = nsemanas[0]
    #         fechaini = nsemanas[1]
    #         fechafin = nsemanas[2]
    #         sql1 = """SELECT * FROM (
    #             SELECT * FROM (SELECT
    #             distinct extract(week FROM CURRENT_DATE + generate_series(inicio- CURRENT_DATE, fin - CURRENT_DATE )) AS numerosemana
    #             FROM sga_materia WHERE id = %s
    #             ORDER BY 1) AS TABLE1,
    #             (
    #             SELECT "inno_solicitudtutoriaindividual"."id",
    #             "inno_solicitudtutoriaindividual"."fechasolicitud",
    #               "inno_solicitudtutoriaindividual"."estado",
    #               extract(week FROM inno_solicitudtutoriaindividual.fechasolicitud::DATE) AS nsemana
    #             FROM "inno_solicitudtutoriaindividual"
    #             INNER JOIN "sga_materiaasignada" ON ("inno_solicitudtutoriaindividual"."materiaasignada_id" = "sga_materiaasignada"."id")
    #             LEFT OUTER
    #             JOIN "inno_horariotutoriaacademica" ON ("inno_solicitudtutoriaindividual"."horario_id" = "inno_horariotutoriaacademica"."id")
    #             LEFT OUTER
    #             JOIN "sga_profesor" T6 ON ("inno_horariotutoriaacademica"."profesor_id" = T6."id")
    #             LEFT OUTER
    #             JOIN "sga_persona" ON (T6."persona_id" = "sga_persona"."id")
    #             WHERE ("inno_solicitudtutoriaindividual"."profesor_id" = %s
    #             AND "inno_solicitudtutoriaindividual"."profesor_id" = %s AND "sga_materiaasignada"."materia_id" = %s
    #             AND "inno_solicitudtutoriaindividual"."status" = TRUE)
    #             ORDER BY "sga_persona"."apellido1" ASC, "sga_persona"."apellido2" ASC, "sga_persona"."nombres" ASC
    #             ) AS TABLE2
    #             WHERE TABLE1.numerosemana=TABLE2.nsemana
    #             AND TABLE2.estado=%s ) AS todo where todo.nsemana=%s
    #         """% (proma.materia.id,profesor.id,profesor.id,proma.materia.id,1,numerosemana)
    #         cursor.execute(sql1)
    #         registro1 = cursor.fetchall()
    #
    #         sql2 = """SELECT * FROM (
    #                         SELECT * FROM (SELECT
    #                         distinct extract(week FROM CURRENT_DATE + generate_series(inicio- CURRENT_DATE, fin - CURRENT_DATE )) AS numerosemana
    #                         FROM sga_materia WHERE id = %s
    #                         ORDER BY 1) AS TABLE1,
    #                         (
    #                         SELECT "inno_solicitudtutoriaindividual"."id",
    #                         "inno_solicitudtutoriaindividual"."fechatutoria",
    #                           "inno_solicitudtutoriaindividual"."estado",
    #                           extract(week FROM inno_solicitudtutoriaindividual.fechatutoria::DATE) AS nsemana
    #                         FROM "inno_solicitudtutoriaindividual"
    #                         INNER JOIN "sga_materiaasignada" ON ("inno_solicitudtutoriaindividual"."materiaasignada_id" = "sga_materiaasignada"."id")
    #                         LEFT OUTER
    #                         JOIN "inno_horariotutoriaacademica" ON ("inno_solicitudtutoriaindividual"."horario_id" = "inno_horariotutoriaacademica"."id")
    #                         LEFT OUTER
    #                         JOIN "sga_profesor" T6 ON ("inno_horariotutoriaacademica"."profesor_id" = T6."id")
    #                         LEFT OUTER
    #                         JOIN "sga_persona" ON (T6."persona_id" = "sga_persona"."id")
    #                         WHERE ("inno_solicitudtutoriaindividual"."profesor_id" = %s
    #                         AND "inno_solicitudtutoriaindividual"."profesor_id" = %s AND "sga_materiaasignada"."materia_id" = %s
    #                         AND "inno_solicitudtutoriaindividual"."status" = TRUE)
    #                         ORDER BY "sga_persona"."apellido1" ASC, "sga_persona"."apellido2" ASC, "sga_persona"."nombres" ASC
    #                         ) AS TABLE2
    #                         WHERE TABLE1.numerosemana=TABLE2.nsemana
    #                         AND TABLE2.estado=%s ) AS todo where todo.nsemana=%s
    #                     """ % (proma.materia.id, profesor.id, profesor.id, proma.materia.id, 2, numerosemana)
    #         cursor.execute(sql2)
    #         registro2 = cursor.fetchall()
    #
    #         sql3 = """SELECT * FROM (
    #                         SELECT * FROM (SELECT
    #                         distinct extract(week FROM CURRENT_DATE + generate_series(inicio- CURRENT_DATE, fin - CURRENT_DATE )) AS numerosemana
    #                         FROM sga_materia WHERE id = %s
    #                         ORDER BY 1) AS TABLE1,
    #                         (
    #                         SELECT "inno_solicitudtutoriaindividual"."id",
    #                         "inno_solicitudtutoriaindividual"."fechatutoria",
    #                           "inno_solicitudtutoriaindividual"."estado",
    #                           extract(week FROM inno_solicitudtutoriaindividual.fechatutoria::DATE) AS nsemana
    #                         FROM "inno_solicitudtutoriaindividual"
    #                         INNER JOIN "sga_materiaasignada" ON ("inno_solicitudtutoriaindividual"."materiaasignada_id" = "sga_materiaasignada"."id")
    #                         LEFT OUTER
    #                         JOIN "inno_horariotutoriaacademica" ON ("inno_solicitudtutoriaindividual"."horario_id" = "inno_horariotutoriaacademica"."id")
    #                         LEFT OUTER
    #                         JOIN "sga_profesor" T6 ON ("inno_horariotutoriaacademica"."profesor_id" = T6."id")
    #                         LEFT OUTER
    #                         JOIN "sga_persona" ON (T6."persona_id" = "sga_persona"."id")
    #                         WHERE ("inno_solicitudtutoriaindividual"."profesor_id" = %s
    #                         AND "inno_solicitudtutoriaindividual"."profesor_id" = %s AND "sga_materiaasignada"."materia_id" = %s
    #                         AND "inno_solicitudtutoriaindividual"."status" = TRUE)
    #                         ORDER BY "sga_persona"."apellido1" ASC, "sga_persona"."apellido2" ASC, "sga_persona"."nombres" ASC
    #                         ) AS TABLE2
    #                         WHERE TABLE1.numerosemana=TABLE2.nsemana
    #                         AND TABLE2.estado=%s ) AS todo where todo.nsemana=%s
    #                     """ % (proma.materia.id, profesor.id, profesor.id, proma.materia.id, 3, numerosemana)
    #         cursor.execute(sql3)
    #         registro3 = cursor.fetchall()
    #
    #         sql4 = """SELECT * FROM (
    #                         SELECT * FROM (SELECT
    #                         distinct extract(week FROM CURRENT_DATE + generate_series(inicio- CURRENT_DATE, fin - CURRENT_DATE )) AS numerosemana
    #                         FROM sga_materia WHERE id = %s
    #                         ORDER BY 1) AS TABLE1,
    #                         (
    #                         SELECT "inno_solicitudtutoriaindividual"."id",
    #                         "inno_solicitudtutoriaindividual"."fechatutoria",
    #                           "inno_solicitudtutoriaindividual"."estado",
    #                           extract(week FROM inno_solicitudtutoriaindividual.fechatutoria::DATE) AS nsemana
    #                         FROM "inno_solicitudtutoriaindividual"
    #                         INNER JOIN "sga_materiaasignada" ON ("inno_solicitudtutoriaindividual"."materiaasignada_id" = "sga_materiaasignada"."id")
    #                         LEFT OUTER
    #                         JOIN "inno_horariotutoriaacademica" ON ("inno_solicitudtutoriaindividual"."horario_id" = "inno_horariotutoriaacademica"."id")
    #                         LEFT OUTER
    #                         JOIN "sga_profesor" T6 ON ("inno_horariotutoriaacademica"."profesor_id" = T6."id")
    #                         LEFT OUTER
    #                         JOIN "sga_persona" ON (T6."persona_id" = "sga_persona"."id")
    #                         WHERE ("inno_solicitudtutoriaindividual"."profesor_id" = %s
    #                         AND "inno_solicitudtutoriaindividual"."profesor_id" = %s AND "sga_materiaasignada"."materia_id" = %s
    #                         AND "inno_solicitudtutoriaindividual"."status" = TRUE)
    #                         ORDER BY "sga_persona"."apellido1" ASC, "sga_persona"."apellido2" ASC, "sga_persona"."nombres" ASC
    #                         ) AS TABLE2
    #                         WHERE TABLE1.numerosemana=TABLE2.nsemana
    #                         AND TABLE2.estado=%s ) AS todo where todo.nsemana=%s
    #                     """ % (proma.materia.id, profesor.id, profesor.id, proma.materia.id, 4, numerosemana)
    #         cursor.execute(sql4)
    #         registro4 = cursor.fetchall()
    #         # lista.append([proma.materia,total.filter(estado=1).count(),total.filter(estado=2).count(),total.filter(estado=3).count(),total.filter(estado=4).count()])
    #         lista.append([proma.materia,registro1.__len__(),registro2.__len__(),registro3.__len__(),registro4.__len__(), numerosemana, fechaini, fechafin])
    # data['listadotutorias'] = lista
    return conviert_html_to_pdf(
        'template_htmlfree/totalestutoriasacademicas.html',
        {
            'pagesize': 'A4',
            'datos': data,
        }
    )

def totalorientarmodallinea(periodo, profesor, idcrite):
    data = {}
    lista = []
    data['periodo'] = periodo
    data['profesor'] = profesor
    data['crite'] = critedocencia = CriterioDocenciaPeriodo.objects.get(pk=idcrite)
    data['critedocencia'] = critedocencia.horario_seguimiento_tutor_fecha(profesor,critedocencia.periodo.inicio,datetime.now().date())
    data['profesormaterias'] = profesormaterias = profesor.profesormateria_set.select_related('materia').filter(status=True, activo=True, materia__nivel__periodo=periodo).exclude(tipoprofesor__id__in=[8]).order_by('materia')
    return conviert_html_to_pdf(
        'template_htmlfree/totalorientarmodallinea.html',
        {
            'pagesize': 'A4',
            'datos': data,
        }
    )

def seguimientotransver(periodo, profesor, idcrite):
    data = {}
    lista = []
    data['periodo'] = periodo
    data['profesor'] = profesor
    data['crite'] = critedocencia = CriterioDocenciaPeriodo.objects.get(pk=idcrite)
    data['critedocencia'] = critedocencia.horario_seguimiento_transaversal_fecha(profesor,critedocencia.periodo.inicio,datetime.now().date())
    return conviert_html_to_pdf(
        'template_htmlfree/seguimientotransver.html',
        {
            'pagesize': 'A4',
            'datos': data,
        }
    )

def sistemanacionalnivadmision(periodo, profesor, idcrite):
    data = {}
    lista = []
    data['periodo'] = periodo
    data['profesor'] = profesor
    data['crite'] = critedocencia = CriterioDocenciaPeriodo.objects.get(pk=idcrite)
    data['fini'] = critedocencia.periodo.inicio
    data['ffin'] = datetime.now().date()
    data['critedocencia'] = profesor.asignaturas_periodos_relacionado(critedocencia.periodosrelacionados.all(),critedocencia.periodo.inicio,datetime.now().date())
    data['profesormaterias'] = profesormaterias = profesor.profesormateria_set.select_related('materia').filter(status=True, activo=True, materia__nivel__periodo=periodo).exclude(tipoprofesor__id__in=[8]).order_by('materia')
    return download_html_to_pdf(
        'template_htmlfree/sistemanacionalnivadmision.html',
        {
            'pagesize': 'A4',
            'datos': data,
        }
    )

def certificadoadmtidoprograma(idins):
    from posgrado.models import ConfigurarFirmaAdmisionPosgrado
    try:
        data = {}
        data['fechaactual'] = datetime.now()
        firmas = ConfigurarFirmaAdmisionPosgrado.objects.filter(status=True).order_by('id')
        data['firmas'] = firmas

        # director = CapConfiguracionIpec.objects.all()
        # data['directornombre'] = director[0].aprobado3
        # directorfirma = None
        # if FirmaPersona.objects.filter(persona=director[0].aprobado3, tipofirma=2, status=True):
        #     directorfirma = FirmaPersona.objects.get(persona=director[0].aprobado3, tipofirma=2, status=True)
        # data['directorfirma'] = directorfirma
        # data['directordepartamento'] = director[0].denominacionaprobado3
        # if CambioAdmitidoCohorteInscripcion.objects.filter(status=True, inscripcionCohorte__id=idins, inscripcionCohorte__status=True).exists():
        #     data['inscripcioncohortecambio'] = inscripcioncohorte = CambioAdmitidoCohorteInscripcion.objects.filter(status=True, inscripcionCohorte=idins).order_by('-id').first()
        #     data['malla'] = malla = Malla.objects.filter(carrera=inscripcioncohorte.inscripcionCohorte.cohortes.maestriaadmision.carrera, status=True).order_by('-id')[0]
        #     data['valorprogramaletra'] = numero_a_letras(inscripcioncohorte.cohortes.valorprogramacertificado)
        # else:
        data['inscripcioncohorte'] = inscripcioncohorte = InscripcionCohorte.objects.get(pk=idins, status=True)
        data['malla'] = malla = Malla.objects.filter(carrera=inscripcioncohorte.cohortes.maestriaadmision.carrera, status=True).order_by('-id')[0]
        data['valorprogramaletra'] = numero_a_letras(inscripcioncohorte.cohortes.valorprogramacertificado)


        # if CambioAdmitidoCohorteInscripcion.objects.filter(status=True, inscripcionCohorte__id=idins, inscripcionCohorte__status=True).exists():
        #     if inscripcioncohorte.inscripcionCohorte.itinerario !=0:
        #         data['mencion'] = mencion = ItinerarioMallaEspecilidad.objects.get(malla=malla, itinerario=inscripcioncohorte.inscripcionCohorte.itinerario, status=True)
        #         data['asignaturasmallas'] = listamaterias = malla.asignaturamalla_set.filter(Q(status=True, itinerario_malla_especialidad__id=mencion.id) | Q(itinerario_malla_especialidad__id__isnull=True))
        #         data['totalmaterias'] = malla.asignaturamalla_set.filter(Q(status=True, itinerario_malla_especialidad__id=mencion.id) | Q(itinerario_malla_especialidad__id__isnull=True)).count()
        #     else:
        data['asignaturasmallas'] = listamaterias = malla.asignaturamalla_set.filter(status=True)
        data['totalmaterias'] = malla.asignaturamalla_set.filter(status=True).count()
        # else:
        #     if inscripcioncohorte.itinerario !=0:
        #         data['mencion'] = mencion = ItinerarioMallaEspecilidad.objects.get(malla=malla, itinerario=inscripcioncohorte.itinerario, status=True)
        #         data['asignaturasmallas'] = listamaterias = malla.asignaturamalla_set.filter(Q(status=True, itinerario_malla_especialidad__id=mencion.id) | Q(itinerario_malla_especialidad__id__isnull=True))
        #         data['totalmaterias'] = malla.asignaturamalla_set.filter(Q(status=True, itinerario_malla_especialidad__id=mencion.id) | Q(itinerario_malla_especialidad__id__isnull=True)).count()
        #     else:
        #         data['asignaturasmallas'] = listamaterias = malla.asignaturamalla_set.filter(status=True)
        #         data['totalmaterias'] = malla.asignaturamalla_set.filter(status=True).count()

        data['totaleshorasacdtotal'] = listamaterias.aggregate(horas=Sum('horasacdtotal'))
        data['totaleshorasapetotal'] = listamaterias.aggregate(horas=Sum('horasapetotal'))
        data['totaleshorasautonomas'] = listamaterias.aggregate(horas=Sum('horasautonomas'))
        data['totaleshoras'] = listamaterias.aggregate(horas=Sum('horas'))

        qrname = 'qr_admitidos_' + str(idins)
        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'admitidos', 'qr'))
        rutapdf = folder + qrname + '.pdf'
        rutaimg = folder + qrname + '.png'

        if os.path.isfile(rutapdf):
            os.remove(rutaimg)
            os.remove(rutapdf)

        # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/admitidos/' + qrname + '.pdf')
        url = pyqrcode.create('https://sga.unemi.edu.ec//media/qrcode/admitidos/' + qrname + '.pdf')
        imageqr = url.png(folder + qrname + '.png', 16, '#000000')
        imagenqr = 'qr' + qrname

        valida = conviert_html_to_pdfsaveadmitidos(
            'alu_requisitosmaestria/certificadomatricula_pdf.html',
            {
                'pagesize': 'A4',
                'data': data,
                'imprimeqr': True,
                'qrname': imagenqr
            }, qrname + '.pdf'
        )

        if valida:
            os.remove(rutaimg)
            # if CambioAdmitidoCohorteInscripcion.objects.filter(status=True, inscripcionCohorte__id=idins, inscripcionCohorte__status=True).exists():
            #     inscripcioncohorte.inscripcionCohorte.codigoqr = True
            #     inscripcioncohorte.inscripcionCohorte.save()
            # else:
            inscripcioncohorte.codigoqr = True
            inscripcioncohorte.save()
        return 'https://sga.unemi.edu.ec/media/qrcode/admitidos/' + qrname + '.pdf'
        # return 'http://127.0.0.1:8000/media/qrcode/admitidos/' + qrname + '.pdf'
    except Exception as ex:
        pass

def cronogramatituex(id):
    from posgrado.models import DetalleActividadCronogramaTitulacion
    from sga.models import PerfilAccesoUsuario, Persona
    data = {}
    data['fechaactual'] = datetime.now()
    data['year'] = datetime.now().date().year

    solicitud = Solicitud.objects.get(status=True, pk=int(id))
    cronograma = DetalleActividadCronogramaTitulacion.objects.filter(status=True, solicitud=solicitud).order_by('inicio')
    data['solicitante'] = solicitud
    data['cronograma'] = cronograma

    if solicitud.perfil.inscripcion.carrera.escuelaposgrado.id == 1:
        dirsal = Departamento.objects.filter(id=216).first()
        director = dirsal.responsable.administrativo()
        var1 = 'A' if director.persona.sexo.id == 1 else ''
        cargo = f'DIRECTOR{var1} DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD'

        if not IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=solicitud, tipo=1):
            eIntegrante = IntegrantesCronogramaTituEx(solicitud=solicitud,
                                                      tipo=1,
                                                      administrativo=director,
                                                      cargo=cargo,
                                                      responsabilidad='Aprobado por')
            eIntegrante.save()
        else:
            eIntegrante = IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=solicitud, tipo=1).first()
        data['director'] = eIntegrante

    elif solicitud.perfil.inscripcion.carrera.escuelaposgrado.id == 2:

        diredu = Departamento.objects.filter(id=215).first()
        director = diredu.responsable.administrativo()
        var2 = 'A' if director.persona.sexo.id == 1 else ''
        cargo = f'DIRECTOR{var2} DE LA ESCUELA DE POSGRADO DE EDUCACIÓN'

        if not IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=solicitud, tipo=1):
            eIntegrante = IntegrantesCronogramaTituEx(solicitud=solicitud,
                                                      tipo=1,
                                                      administrativo=director,
                                                      cargo=cargo,
                                                      responsabilidad='Aprobado por')
            eIntegrante.save()
        else:
            eIntegrante = IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=solicitud, tipo=1).first()
        data['director'] = eIntegrante

    elif solicitud.perfil.inscripcion.carrera.escuelaposgrado.id == 3:
        dirneg = Departamento.objects.filter(id=163).first()

        director = dirneg.responsable.administrativo()
        var3 = 'A' if director.persona.sexo.id == 1 else ''
        cargo = f'DIRECTOR{var3} DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO'

        if not IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=solicitud, tipo=1):
            eIntegrante = IntegrantesCronogramaTituEx(solicitud=solicitud,
                                                      tipo=1,
                                                      administrativo=director,
                                                      cargo=cargo,
                                                      responsabilidad='Aprobado por')
            eIntegrante.save()
        else:
            eIntegrante = IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=solicitud, tipo=1).first()
        data['director'] = eIntegrante
    else:
        data['director'] = None


    eCohorte = CohorteMaestria.objects.filter(maestriaadmision__carrera=solicitud.perfil.inscripcion.carrera).order_by('-id').first()
    if eCohorte:
        eCoordinador = eCohorte.coordinador.administrativo()
        eMaestria = eCohorte.maestriaadmision.carrera.nombre
        if eCohorte.maestriaadmision.carrera.mencion:
            eMaestria = f'{eMaestria} CON MENCIÓN EN {eCohorte.maestriaadmision.carrera.mencion}'
        var = 'A' if eCoordinador.persona.sexo.id == 1 else ''
        cargo_cor = f'COORDINADOR{var} DEL PROGRAMA DE {eMaestria}'

        if not IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=solicitud, tipo=2):
            eIntegrante = IntegrantesCronogramaTituEx(solicitud=solicitud,
                                                      tipo=2,
                                                      administrativo=eCoordinador,
                                                      cargo=cargo_cor,
                                                      responsabilidad='Revisado por')
            eIntegrante.save()
        else:
            eIntegrante = IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=solicitud, tipo=2).first()
        data['coordinador'] = eIntegrante
    else:
        data['coordinador'] = None

    qrname = 'cte_cronograma_titulacion_ex_' + str(id)
    directory = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'cronogramas')
    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'cronogramas', 'cte'))
    try:
        os.stat(directory)
    except:
        os.mkdir(directory)
    rutapdf = folder + qrname + '.pdf'

    if os.path.isfile(rutapdf):
        os.remove(rutapdf)

    # url = pyqrcode.create('http://127.0.0.1:8000/media/qrcode/cronogramas/' + qrname + '.pdf')
    url = pyqrcode.create('https://sga.unemi.edu.ec/media/qrcode/cronogramas/' + qrname + '.pdf')

    htmlcontrato = 'adm_secretaria/cronogramatitex_pdf.html'

    imagenqr = 'qr' + qrname

    conviert_html_to_pdfsavecontratomae(
        htmlcontrato,
        {
            'pagesize': 'A4',
            'data': data,
            'imprimeqr': True,
            'qrname': imagenqr
        }, qrname + '.pdf', 'cronogramas'
    )

    fe = datetime.now().date()
    # return 'http://127.0.0.1:8000/media/qrcode/cronogramas/' + qrname + '.pdf'
    return 'https://sga.unemi.edu.ec/media/qrcode/cronogramas/' + qrname + '.pdf' + '?v=' + str(fe)

def contratoformapagoprograma(idins, idtf, numcontrato):
    data = {}
    data['fechaactual'] = datetime.now()
    tipopago = TipoFormaPagoPac.objects.filter(pk=int(idtf)).last()
    data['numcontrato'] = str(numcontrato).zfill(4) + "-" + str(datetime.now().year)
    valorprograma = 0
    if CambioAdmitidoCohorteInscripcion.objects.filter(status=True, inscripcionCohorte__id=idins, inscripcionCohorte__status=True).exists():
        data['inscripcioncohortecambio'] = inscripcioncohorte = CambioAdmitidoCohorteInscripcion.objects.filter(status=True, inscripcionCohorte=idins).order_by('-id').first()

        if inscripcioncohorte.inscripcionCohorte.itinerario and inscripcioncohorte.inscripcionCohorte.itinerario != 0:
            data['malla'] = malla = Malla.objects.get(carrera=inscripcioncohorte.inscripcionCohorte.cohortes.maestriaadmision.carrera, status=True)
            data['mencion'] = ItinerarioMallaEspecilidad.objects.get(malla=malla, itinerario=inscripcioncohorte.inscripcionCohorte.itinerario, status=True)
        if tipopago.id == 2:
            if inscripcioncohorte.inscripcionCohorte.Configfinanciamientocohorte:
                data['valorprograma'] = inscripcioncohorte.inscripcionCohorte.Configfinanciamientocohorte.valortotalprograma
                data['valorprogramaletra'] = numero_a_letras(inscripcioncohorte.inscripcionCohorte.Configfinanciamientocohorte.valortotalprograma)
                data['meses'] = inscripcioncohorte.inscripcionCohorte.Configfinanciamientocohorte.maxnumcuota
            else:
                raise NameError(' Usted no tiene asignado un tipo de financiamiento.')
        else:
            if inscripcioncohorte.inscripcionCohorte.cohortes.valorprograma > 0:
                valorprograma = inscripcioncohorte.inscripcionCohorte.cohortes.valorprograma
            elif inscripcioncohorte.inscripcionCohorte.cohortes.valorprogramacertificado > 0:
                valorprograma = inscripcioncohorte.inscripcionCohorte.cohortes.valorprogramacertificado
            else:
                raise NameError('Falta configurar el valor total del programa en %s'%(inscripcioncohorte.inscripcionCohorte.cohortes))
            data['valorprograma'] = valorprograma
            data['valorprogramaletra'] = numero_a_letras(valorprograma)
    else:
        data['inscripcioncohorte'] = inscripcioncohorte = InscripcionCohorte.objects.get(pk=idins, status=True)
        if inscripcioncohorte.itinerario and inscripcioncohorte.itinerario != 0:
            data['malla'] = malla = Malla.objects.get(carrera=inscripcioncohorte.cohortes.maestriaadmision.carrera, status=True)
            data['mencion'] = ItinerarioMallaEspecilidad.objects.get(malla=malla, itinerario=inscripcioncohorte.itinerario, status=True)
        if tipopago.id == 2:
            if inscripcioncohorte.Configfinanciamientocohorte:
                data['valorprograma'] = inscripcioncohorte.Configfinanciamientocohorte.valortotalprograma
                data['valorprogramaletra'] = numero_a_letras(inscripcioncohorte.Configfinanciamientocohorte.valortotalprograma)
                data['meses'] = inscripcioncohorte.Configfinanciamientocohorte.maxnumcuota
            else:
                raise NameError(' Usted no tiene asignado un tipo de financiamiento.')
        else:
            if inscripcioncohorte.cohortes.valorprograma > 0:
                valorprograma = inscripcioncohorte.cohortes.valorprograma
            elif inscripcioncohorte.cohortes.valorprogramacertificado > 0:
                valorprograma = inscripcioncohorte.cohortes.valorprogramacertificado
            else:
                raise NameError('Falta configurar el valor total del programa en %s'%(inscripcioncohorte.cohortes))
            data['valorprograma'] = valorprograma
            data['valorprogramaletra'] = numero_a_letras(valorprograma)


    qrname = 'cp_contratopago_' + str(idins)
    directory = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'contratopago')
    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'contratopago', 'cp'))
    try:
        os.stat(directory)
    except:
        os.mkdir(directory)
    rutapdf = folder + qrname + '.pdf'

    if os.path.isfile(rutapdf):
        os.remove(rutapdf)

    # url = pyqrcode.create('http://127.0.0.1:8000/media/qrcode/contratopago/' + qrname + '.pdf')
    url = pyqrcode.create('https://sga.unemi.edu.ec/media/qrcode/contratopago/' + qrname + '.pdf')

    if tipopago:
        if tipopago.id == 1:
            htmlcontrato = 'alu_requisitosmaestria/contratopagocontado_pdf.html'
        if tipopago.id == 2:
            htmlcontrato = 'alu_requisitosmaestria/contratopagofinanciamiento_pdf.html'

    imagenqr = 'qr' + qrname

    conviert_html_to_pdfsavecontratomae(
        htmlcontrato,
        {
            'pagesize': 'A4',
            'data': data,
            'imprimeqr': True,
            'qrname': imagenqr
        }, qrname + '.pdf', 'contratopago'
    )

    fe = datetime.now().date()
    # return 'http://127.0.0.1:8000/media/qrcode/contratopago/' + qrname + '.pdf'
    return 'https://sga.unemi.edu.ec/media/qrcode/contratopago/' + qrname + '.pdf' + '?v=' + str(fe)

def oficioterminacioncontrato(idcon):
    data = {}
    data['fechaactual'] = datetime.now()
    data['contrato'] = contrato = Contrato.objects.get(pk=idcon, status=True)


    qrname = 'cp_oficioterminacioncontrato_' + str(idcon)
    directory = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'oficioterminacioncontrato')
    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'oficioterminacioncontrato', 'otc'))
    try:
        os.stat(directory)
    except:
        os.mkdir(directory)
    rutapdf = folder + qrname + '.pdf'

    if os.path.isfile(rutapdf):
        os.remove(rutapdf)

    # url = pyqrcode.create('http://127.0.0.1:8000/media/qrcode/oficioterminacioncontrato/' + qrname + '.pdf')
    url = pyqrcode.create('https://sga.unemi.edu.ec/media/qrcode/oficioterminacioncontrato/' + qrname + '.pdf')

    htmlcontrato = 'alu_requisitosmaestria/oficioterminacioncontrato.html'

    imagenqr = 'qr' + qrname

    conviert_html_to_pdfsavecontratomae(
        htmlcontrato,
        {
            'pagesize': 'A4',
            'data': data,
            'imprimeqr': True,
            'qrname': imagenqr
        }, qrname + '.pdf', 'oficioterminacioncontrato'
    )

    # return 'http://127.0.0.1:8000/media/qrcode/oficioterminacioncontrato/' + qrname + '.pdf'
    return 'https://sga.unemi.edu.ec/media/qrcode/oficioterminacioncontrato/' + qrname + '.pdf'

def pagareaspirantemae(idins, idconfig, numpagare):
    try:
        data = {}
        data['fechaactual'] = datetime.now()
        data['numpagare'] = str(numpagare).zfill(4) + "-" + str(datetime.now().year)
        data['garante'] = garantemaestria = GarantePagoMaestria.objects.filter(inscripcioncohorte_id=idins, status=True).last()
        data['financiamiento'] = financiamiento = ConfigFinanciamientoCohorte.objects.get(pk=idconfig)
        data['valorprogramaletra'] = numero_a_letras(financiamiento.valortotalprograma)
        data['tablaamortizacion'] = financiamiento.tablaamortizacioncohortemaestria(idins,datetime.now())


        # if CambioAdmitidoCohorteInscripcion.objects.filter(status=True, inscripcionCohorte__id=idins, inscripcionCohorte__status=True).exists():
        #     data['inscripcioncohortecambio'] = inscripcioncohorte = CambioAdmitidoCohorteInscripcion.objects.filter(status=True, inscripcionCohorte=idins).order_by('-id').first()
        #
        #     if inscripcioncohorte.inscripcionCohorte.contrato_set.filter(status=True).values('id').last() and inscripcioncohorte.inscripcionCohorte.contrato_set.filter(status=True).last().tablaamortizacion_set.values('id').filter(status=True) and inscripcioncohorte.inscripcionCohorte.contrato_set.filter(status=True).last().tablaamortizacionajustada:
        #         tablaamortizacion = []
        #         contrato = inscripcioncohorte.inscripcionCohorte.contrato_set.filter(status=True).last()
        #         montototal = contrato.tablaamortizacion_set.values_list('valor').filter(status=True)
        #         total = Decimal(0)
        #         valorpendiente = Decimal(0)
        #         for valor in montototal:
        #             total = total + valor[0]
        #         data['total'] = total
        #         tablaamortizacionajustada = contrato.tablaamortizacion_set.values_list('cuota', 'fecha', 'fechavence', 'valor').filter(status=True)
        #
        #         for tabla in tablaamortizacionajustada:
        #             if tabla[0] == 0:
        #                 valorarancel = total - tabla[3]
        #                 valorpendiente = valorarancel
        #                 tablaamortizacion += [('', '', '', tabla[3], valorarancel)]
        #             else:
        #                 valorpendiente = valorpendiente - tabla[3]
        #                 tablaamortizacion += [(tabla[0], tabla[1], tabla[2], tabla[3], valorpendiente)]
        #         data['numerodecuotas'] = tablaamortizacionajustada.count() - 1
        #         data['tablaamortizacion'] = tablaamortizacion
        #     else:
        #         data['tablaamortizacion'] = financiamiento.tablaamortizacioncohortemaestria(idins, datetime.now())
        # else:
        data['inscripcioncohorte'] = inscripcioncohorte = InscripcionCohorte.objects.get(pk=idins, status=True)

        if inscripcioncohorte.contrato_set.filter(status=True).values('id').last() and inscripcioncohorte.contrato_set.filter(status=True).last().tablaamortizacion_set.values('id').filter(status=True) and inscripcioncohorte.contrato_set.filter(status=True).last().tablaamortizacionajustada:
            tablaamortizacion = []
            contrato = inscripcioncohorte.contrato_set.filter(status=True).last()
            montototal = contrato.tablaamortizacion_set.values_list('valor').filter(status=True)
            total = Decimal(0)
            valorpendiente = Decimal(0)
            for valor in montototal:
                total = total + valor[0]
            data['total'] = total
            tablaamortizacionajustada = contrato.tablaamortizacion_set.values_list('cuota', 'fecha', 'fechavence', 'valor').filter(status=True)

            for tabla in tablaamortizacionajustada:
                if tabla[0] == 0:
                    valorarancel = total - tabla[3]
                    valorpendiente = valorarancel
                    tablaamortizacion += [('', '', '', tabla[3], valorarancel)]
                else:
                    valorpendiente = valorpendiente - tabla[3]
                    tablaamortizacion += [(tabla[0], tabla[1], tabla[2], tabla[3], valorpendiente)]
            data['numerodecuotas'] = tablaamortizacionajustada.count() - 1
            data['tablaamortizacion'] = tablaamortizacion
        else:
            data['tablaamortizacion'] = financiamiento.tablaamortizacioncohortemaestria(idins, datetime.now())

        qrname = 'pp_pagareaspirantemaestria_' + str(idins)
        directory = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'pagareaspirantemaestria')
        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'pagareaspirantemaestria', 'pp'))
        try:
            os.stat(directory)
        except:
            os.mkdir(directory)

        rutapdf = folder + qrname + '.pdf'
        if os.path.isfile(rutapdf):
            os.remove(rutapdf)

        # url = pyqrcode.create('http://127.0.0.1:8000/media/qrcode/pagareaspirantemaestria/' + qrname + '.pdf')
        url = pyqrcode.create('https://sga.unemi.edu.ec/media/qrcode/pagareaspirantemaestria/' + qrname + '.pdf')
        imagenqr = 'qr' + qrname
        conviert_html_to_pdfsavecontratomae(
            'alu_requisitosmaestria/pagareaspirantemaestria_pdf.html',
            {
                'pagesize': 'A4',
                'data': data,
                'imprimeqr': True,
                'qrname': imagenqr
            }, qrname + '.pdf','pagareaspirantemaestria'
        )

        fe = datetime.now().date()
        # return 'http://127.0.0.1:8000/media/qrcode/pagareaspirantemaestria/' + qrname + '.pdf'
        return 'https://sga.unemi.edu.ec/media/qrcode/pagareaspirantemaestria/' + qrname + '.pdf' + '?v=' + str(fe)

    except Exception as ex:
        pass

def contratoconsultadeuda(idins, idmat, numcontrato):
    try:
        data = {}
        data['fechaactual'] = datetime.now()
        data['numcontrato'] = str(numcontrato).zfill(4) + "-" + str(datetime.now().year)
        valorprograma = 0
        data['matricula'] = matricula = Matricula.objects.get(status=True, id=idmat)
        if CambioAdmitidoCohorteInscripcion.objects.filter(status=True, inscripcionCohorte__id=idins, inscripcionCohorte__status=True).exists():
            data['inscripcioncohortecambio'] = inscripcioncohorte = CambioAdmitidoCohorteInscripcion.objects.filter(status=True, inscripcionCohorte=idins).order_by('-id').first()
            if inscripcioncohorte.inscripcionCohorte.itinerario and inscripcioncohorte.inscripcionCohorte.itinerario != 0:
                data['malla'] = malla = Malla.objects.get(carrera=inscripcioncohorte.inscripcionCohorte.cohortes.maestriaadmision.carrera, status=True)
                data['mencion'] = ItinerarioMallaEspecilidad.objects.get(malla=malla, itinerario=inscripcioncohorte.inscripcionCohorte.itinerario, status=True)
            if matricula.cantidad_rubros_matricula() > 1:
                if inscripcioncohorte.inscripcionCohorte.cohortes.valorprogramacertificado:
                    data['valorprograma'] = inscripcioncohorte.inscripcionCohorte.cohortes.valorprogramacertificado
                    data['valorprogramaletra'] = numero_a_letras(inscripcioncohorte.inscripcionCohorte.cohortes.valorprogramacertificado)
                    data['meses'] = matricula.cantidad_rubros_matricula() - 1
                else:
                    raise NameError('No tiene configurado el valor del programa')
            else:
                if inscripcioncohorte.inscripcionCohorte.cohortes.valorprograma > 0:
                    valorprograma = inscripcioncohorte.inscripcionCohorte.cohortes.valorprograma
                elif inscripcioncohorte.inscripcionCohorte.cohortes.valorprogramacertificado > 0:
                    valorprograma = inscripcioncohorte.inscripcionCohorte.cohortes.valorprogramacertificado
                else:
                    raise NameError('Falta configurar el valor total del programa en %s'%(inscripcioncohorte.inscripcionCohorte.cohortes))
                data['valorprograma'] = valorprograma
                data['valorprogramaletra'] = numero_a_letras(valorprograma)
        else:
            data['inscripcioncohorte'] = inscripcioncohorte = InscripcionCohorte.objects.get(pk=idins, status=True)
            if inscripcioncohorte.itinerario and inscripcioncohorte.itinerario != 0:
                data['malla'] = malla = Malla.objects.get(carrera=inscripcioncohorte.cohortes.maestriaadmision.carrera, status=True)
                data['mencion'] = ItinerarioMallaEspecilidad.objects.get(malla=malla, itinerario=inscripcioncohorte.itinerario, status=True)
            if matricula.cantidad_rubros_matricula() > 1:
                if inscripcioncohorte.cohortes.valorprogramacertificado:
                    data['valorprograma'] = inscripcioncohorte.cohortes.valorprogramacertificado
                    data['valorprogramaletra'] = numero_a_letras(inscripcioncohorte.cohortes.valorprogramacertificado)
                    data['meses'] = matricula.cantidad_rubros_matricula() - 1
                else:
                    raise NameError('No tiene configurado el valor del programa')
            else:
                if inscripcioncohorte.cohortes.valorprograma > 0:
                    valorprograma = inscripcioncohorte.cohortes.valorprograma
                elif inscripcioncohorte.cohortes.valorprogramacertificado > 0:
                    valorprograma = inscripcioncohorte.cohortes.valorprogramacertificado
                else:
                    raise NameError('Falta configurar el valor total del programa en %s'%(inscripcioncohorte.cohortes))
                data['valorprograma'] = valorprograma
                data['valorprogramaletra'] = numero_a_letras(valorprograma)


        qrname = 'cp_contratopago_' + str(idins)
        directory = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'contratopago')
        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'contratopago', 'cp'))
        try:
            os.stat(directory)
        except:
            os.mkdir(directory)
        rutapdf = folder + qrname + '.pdf'

        if os.path.isfile(rutapdf):
            os.remove(rutapdf)

        # url = pyqrcode.create('http://127.0.0.1:8000/media/qrcode/contratopago/' + qrname + '.pdf')
        url = pyqrcode.create('https://sga.unemi.edu.ec/media/qrcode/contratopago/' + qrname + '.pdf')

        if matricula:
            if matricula.cantidad_rubros_matricula() == 1:
                htmlcontrato = 'rec_consultaalumnos/contratopagocontadocd_pdf.html'
            if matricula.cantidad_rubros_matricula() > 1:
                htmlcontrato = 'rec_consultaalumnos/contratopagofinanciamientocd_pdf.html'

        imagenqr = 'qr' + qrname

        conviert_html_to_pdfsavecontratomae(
            htmlcontrato,
            {
                'pagesize': 'A4',
                'data': data,
                'imprimeqr': True,
                'qrname': imagenqr
            }, qrname + '.pdf', 'contratopago'
        )

        # return 'http://127.0.0.1:8000/media/qrcode/contratopago/' + qrname + '.pdf'
        return 'https://sga.unemi.edu.ec/media/qrcode/contratopago/' + qrname + '.pdf'
    except Exception as ex:
        pass


def evidenciasrecursossilabo(periodo, persona, tipo):
    data = {}
    if int(tipo) == 1:
        data['detallerecurso'] = HistorialaprobacionTarea.objects.values_list('tarea__silabosemanal__silabo__materia__asignaturamalla__malla__carrera__nombre',
                                                                              'tarea__silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre',
                                                                              'tarea__silabosemanal__silabo__materia__paralelo',
                                                                              'tarea__silabosemanal__numsemana',
                                                                              'tarea__silabosemanal__fechainiciosemana',
                                                                              'tarea__silabosemanal__fechafinciosemana',
                                                                              'tarea__nombre',
                                                                              'tarea__fecha_creacion'
                                                                              ).filter(tarea__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=persona.usuario, estado_id=2, tarea__silabosemanal__silabo__status=True, tarea__silabosemanal__status=True, tarea__status=True, status=True).distinct().order_by('tarea__silabosemanal__silabo__materia__asignaturamalla__malla__carrera__nombre',
                                                                                                                                                                                                                                                                                                                                        'tarea__silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre',
                                                                                                                                                                                                                                                                                                                                        'tarea__silabosemanal__silabo__materia__paralelo',
                                                                                                                                                                                                                                                                                                                                        'tarea__silabosemanal__numsemana')

    if int(tipo) == 2:
        data['detallerecurso'] = HistorialaprobacionForo.objects.values_list('foro__silabosemanal__silabo__materia__asignaturamalla__malla__carrera__nombre',
                                                                             'foro__silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre',
                                                                             'foro__silabosemanal__silabo__materia__paralelo',
                                                                             'foro__silabosemanal__numsemana',
                                                                             'foro__silabosemanal__fechainiciosemana',
                                                                             'foro__silabosemanal__fechafinciosemana',
                                                                             'foro__nombre').filter(foro__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=persona.usuario, estado_id=2, foro__silabosemanal__silabo__status=True, foro__silabosemanal__status=True, foro__status=True, status=True).distinct().order_by('foro__silabosemanal__silabo__materia__asignaturamalla__malla__carrera__nombre',
                                                                                                                                                                                                                                                                                                                                                 'foro__silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre',
                                                                                                                                                                                                                                                                                                                                                 'foro__silabosemanal__silabo__materia__paralelo',
                                                                                                                                                                                                                                                                                                                                                 'foro__silabosemanal__numsemana')
    if int(tipo) == 3:
        data['detallerecurso'] = HistorialaprobacionTareaPractica.objects.values_list('tareapractica__silabosemanal__silabo__materia__asignaturamalla__malla__carrera__nombre',
                                                                                      'tareapractica__silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre',
                                                                                      'tareapractica__silabosemanal__silabo__materia__paralelo',
                                                                                      'tareapractica__silabosemanal__numsemana',
                                                                                      'tareapractica__silabosemanal__fechainiciosemana',
                                                                                      'tareapractica__silabosemanal__fechafinciosemana',
                                                                                      'tareapractica__nombre').filter(tareapractica__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=persona.usuario, estado_id=2, tareapractica__silabosemanal__silabo__status=True, tareapractica__silabosemanal__status=True, tareapractica__status=True, status=True).distinct().order_by('tareapractica__silabosemanal__silabo__materia__asignaturamalla__malla__carrera__nombre',
                                                                                                                                                                                                                                                                                                                                                                                                       'tareapractica__silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre',
                                                                                                                                                                                                                                                                                                                                                                                                       'tareapractica__silabosemanal__silabo__materia__paralelo',
                                                                                                                                                                                                                                                                                                                                                                                                       'tareapractica__silabosemanal__numsemana')
    if int(tipo) == 4:
        data['detallerecurso'] = HistorialaprobacionDiapositiva.objects.values_list('diapositiva__silabosemanal__silabo__materia__asignaturamalla__malla__carrera__nombre',
                                                                                    'diapositiva__silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre',
                                                                                    'diapositiva__silabosemanal__silabo__materia__paralelo',
                                                                                    'diapositiva__silabosemanal__numsemana',
                                                                                    'diapositiva__silabosemanal__fechainiciosemana',
                                                                                    'diapositiva__silabosemanal__fechafinciosemana',
                                                                                    'diapositiva__nombre').filter(diapositiva__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=persona.usuario, estado_id=2, diapositiva__silabosemanal__silabo__status=True, diapositiva__silabosemanal__status=True, diapositiva__status=True, status=True).distinct().order_by('diapositiva__silabosemanal__silabo__materia__asignaturamalla__malla__carrera__nombre',
                                                                                                                                                                                                                                                                                                                                                                                           'diapositiva__silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre',
                                                                                                                                                                                                                                                                                                                                                                                           'diapositiva__silabosemanal__silabo__materia__paralelo',
                                                                                                                                                                                                                                                                                                                                                                                           'diapositiva__silabosemanal__numsemana')
    if int(tipo) == 5:
        data['detallerecurso'] = HistorialaprobacionGuiaEstudiante.objects.values_list('guiaestudiante__silabosemanal__silabo__materia__asignaturamalla__malla__carrera__nombre',
                                                                                       'guiaestudiante__silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre',
                                                                                       'guiaestudiante__silabosemanal__silabo__materia__paralelo',
                                                                                       'guiaestudiante__silabosemanal__numsemana',
                                                                                       'guiaestudiante__silabosemanal__fechainiciosemana',
                                                                                       'guiaestudiante__silabosemanal__fechafinciosemana',
                                                                                       'guiaestudiante__observacion').filter(guiaestudiante__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=persona.usuario, estado_id=2, guiaestudiante__silabosemanal__silabo__status=True, guiaestudiante__silabosemanal__status=True, guiaestudiante__status=True, status=True).distinct().order_by('guiaestudiante__silabosemanal__silabo__materia__asignaturamalla__malla__carrera__nombre',
                                                                                                                                                                                                                                                                                                                                                                                                                  'guiaestudiante__silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre',
                                                                                                                                                                                                                                                                                                                                                                                                                  'guiaestudiante__silabosemanal__silabo__materia__paralelo',
                                                                                                                                                                                                                                                                                                                                                                                                                  'guiaestudiante__silabosemanal__numsemana')
    if int(tipo) == 6:
        data['detallerecurso'] = HistorialaprobacionGuiaDocente.objects.values_list('guiadocente__silabosemanal__silabo__materia__asignaturamalla__malla__carrera__nombre',
                                                                                    'guiadocente__silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre',
                                                                                    'guiadocente__silabosemanal__silabo__materia__paralelo',
                                                                                    'guiadocente__silabosemanal__numsemana',
                                                                                    'guiadocente__silabosemanal__fechainiciosemana',
                                                                                    'guiadocente__silabosemanal__fechafinciosemana',
                                                                                    'guiadocente__observacion').filter(guiadocente__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=persona.usuario, estado_id=2, guiadocente__silabosemanal__silabo__status=True, guiadocente__silabosemanal__status=True, guiadocente__status=True, status=True).distinct().order_by('guiadocente__silabosemanal__silabo__materia__asignaturamalla__malla__carrera__nombre',
                                                                                                                                                                                                                                                                                                                                                                                                'guiadocente__silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre',
                                                                                                                                                                                                                                                                                                                                                                                                'guiadocente__silabosemanal__silabo__materia__paralelo',
                                                                                                                                                                                                                                                                                                                                                                                                'guiadocente__silabosemanal__numsemana')
    if int(tipo) == 7:
        data['detallerecurso'] = HistorialaprobacionCompendio.objects.values_list('compendio__silabosemanal__silabo__materia__asignaturamalla__malla__carrera__nombre',
                                                                                  'compendio__silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre',
                                                                                  'compendio__silabosemanal__silabo__materia__paralelo',
                                                                                  'compendio__silabosemanal__numsemana',
                                                                                  'compendio__silabosemanal__fechainiciosemana',
                                                                                  'compendio__silabosemanal__fechafinciosemana',
                                                                                  'compendio__descripcion').filter(compendio__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=persona.usuario, estado_id=2, compendio__silabosemanal__silabo__status=True, compendio__silabosemanal__status=True, compendio__status=True, status=True).distinct().order_by('compendio__silabosemanal__silabo__materia__asignaturamalla__malla__carrera__nombre',
                                                                                                                                                                                                                                                                                                                                                                                    'compendio__silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre',
                                                                                                                                                                                                                                                                                                                                                                                    'compendio__silabosemanal__silabo__materia__paralelo',
                                                                                                                                                                                                                                                                                                                                                                                    'compendio__silabosemanal__numsemana')
    if int(tipo) == 8:
        data['detallerecurso'] = HistorialaprobacionTest.objects.values_list('test__silabosemanal__silabo__materia__asignaturamalla__malla__carrera__nombre',
                                                                             'test__silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre',
                                                                             'test__silabosemanal__silabo__materia__paralelo',
                                                                             'test__silabosemanal__numsemana',
                                                                             'test__silabosemanal__fechainiciosemana',
                                                                             'test__silabosemanal__fechafinciosemana',
                                                                             'test__nombretest').filter(test__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=persona.usuario, estado_id=2, test__silabosemanal__silabo__status=True, test__silabosemanal__status=True, test__status=True, status=True).distinct().order_by('test__silabosemanal__silabo__materia__asignaturamalla__malla__carrera__nombre',
                                                                                                                                                                                                                                                                                                                                                     'test__silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre',
                                                                                                                                                                                                                                                                                                                                                     'test__silabosemanal__silabo__materia__paralelo',
                                                                                                                                                                                                                                                                                                                                                     'test__silabosemanal__numsemana')
    template = get_template("template_htmlfree/evidenciasrecursos.html")
    json_content = template.render(data)
    return JsonResponse({"result": "ok", 'data': json_content})


def prapreprofesionales(profesor, periodo):
    from datetime import date
    data = {}
    listaid = []
    listadopp = InformeMensualDocentesPPP.objects.filter(status=True, persona=profesor).order_by('-fechageneracion')
    if listadopp:
        for lisfecha in listadopp:
            new_date = date(lisfecha.anio, lisfecha.mes, 1)
            if periodo.inicio <= new_date and periodo.fin >= new_date:
                listaid.append(lisfecha.id)
        if listaid:
            listadopp = InformeMensualDocentesPPP.objects.filter(pk__in=listaid).order_by('-fechageneracion')
    data['docentepracticas'] = profesor
    data['listado'] = listadopp
    template = get_template("template_htmlfree/evidenciaspprofesionales.html")
    json_content = template.render(data)
    return JsonResponse({"result": "ok", 'data': json_content})


def actatribunalcalificacion(iddetallegrupo):
    data = {}
    data['fechaactual'] = datetime.now()
    fechainiciaactagenerar = datetime.strptime('2020-05-10', '%Y-%m-%d').date()
    data['participante'] = participante = ComplexivoDetalleGrupo.objects.get(pk=iddetallegrupo)

    if not participante.actatribunalgenerada:
        if participante.grupo.fechadefensa > fechainiciaactagenerar:
            participante.actatribunalgenerada = True
            participante.numeroacta = ComplexivoDetalleGrupo.objects.filter(status=True).order_by('-numeroacta')[0].numeroacta + 1
            participante.fechaacta = datetime.now().date()
            participante.save()
    data['detallecalificacion'] = detallecalificacion = participante.calificacionrubricatitulacion_set.filter(status=True).order_by('tipojuradocalificador')
    modelorubricatitulacion = ModeloRubricaTitulacion.objects.filter(rubrica=participante.rubrica, status=True).order_by('id')
    for detjurado in detallecalificacion:
        if not detjurado.calificaciondetallemodelorubricatitulacion_set.filter(status=True):
            for rubmodelo in modelorubricatitulacion:
                calificacionmodelorubrica = CalificacionDetalleModeloRubricaTitulacion(calificacionrubrica=detjurado,
                                                                                       modelorubrica=rubmodelo,
                                                                                       puntaje=0)
                calificacionmodelorubrica.save()
                detcalificacion = CalificacionDetalleRubricaTitulacion.objects.filter(calificacionrubrica=detjurado, rubricatitulacion__modelorubrica=calificacionmodelorubrica.modelorubrica, status=True).aggregate(valor=Sum('puntaje'))['valor']
                calificacionmodelorubrica.puntaje = detcalificacion
                calificacionmodelorubrica.save()

    data['promediopuntajetrabajointegral'] = detallecalificacion.values_list('puntajetrabajointegral').aggregate(promedio=Avg('puntajetrabajointegral'))['promedio']
    data['promediodefensaoral'] = detallecalificacion.values_list('puntajedefensaoral').aggregate(promedio=Avg('puntajedefensaoral'))['promedio']
    data['promediofinal'] = promediofinal = null_to_decimal(detallecalificacion.values_list('puntajerubricas').aggregate(promedio=Avg('puntajerubricas'))['promedio'], 2)
    data['listadomodelorubrica'] = participante.rubrica.modelorubricatitulacion_set.filter(status=True).order_by('orden')
    if participante.matricula.alternativa.tipotitulacion.tipo == 2:
        data['finalcomplexivo'] = null_to_decimal(((float(participante.notafinal()) + float(promediofinal)) / 2), 2)
    return conviert_html_to_pdf('adm_complexivotematica/acta_calificaciontribunalnew_pdf.html',
                                {
                                    'pagesize': 'A4',
                                    'data': data,
                                }
                                )


def rubricatribunalcalificacion(iddetallegrupo):
    data = {}
    lista = []
    data['fechaactual'] = datetime.now()
    data['participante'] = participante = ComplexivoDetalleGrupo.objects.get(pk=iddetallegrupo)
    data['calificacionrubricatitulacion'] = calificacionrubricatitulacion = participante.calificacionrubricatitulacion_set.filter(status=True).order_by('tipojuradocalificador')
    data['numerotribunales'] = calificacionrubricatitulacion.count()
    data['promediofinal'] = null_to_decimal(calificacionrubricatitulacion.values_list('puntajerubricas').aggregate(promedio=Avg('puntajerubricas'))['promedio'], 2)
    rubricasevaluadas = RubricaTitulacion.objects.select_related().filter(modelorubrica__rubrica=participante.rubrica, status=True).order_by('modelorubrica__orden', 'orden')
    for rubrica in rubricasevaluadas:
        puntajepresidente = rubrica.calificaciondetallerubricatitulacion_set.filter(calificacionrubrica__complexivodetallegrupo=participante, status=True).order_by('calificacionrubrica__tipojuradocalificador')
        lista.append([rubrica, puntajepresidente])
    data['ponderacionesrubrica'] = RubricaTitulacionCabPonderacion.objects.filter(rubrica=rubricasevaluadas[0].rubrica, status=True).order_by('orden')
    data['rubricasevaluadas'] = lista
    return conviert_html_to_pdf('adm_complexivotematica/pdfrubricacalificacionesnew_pdf.html',
                                {
                                    'pagesize': 'A4',
                                    'data': data,
                                }
                                )


def actagradoposgrado(idinscripcion):
    #hace lo mismo en la funcion de abajo que es para graduados  -< actagradoposgradograduados
    data = {}
    data['matriculadoposgrado'] = matriculadoposgrado = TemaTitulacionPosgradoMatricula.objects.get(id=idinscripcion)
    data['graduadoposgrado'] = graduado =Graduado.objects.get(inscripcion=matriculadoposgrado.matricula.inscripcion)
    if matriculadoposgrado.cabeceratitulacionposgrado:
        tribunalmatriculado = matriculadoposgrado.cabeceratitulacionposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
    else:
        tribunalmatriculado = matriculadoposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]

    data['tribunalmatriculado'] = tribunalmatriculado
    data['fechagraduados'] = fecha_letra_con_dia_numero(str(tribunalmatriculado.fechadefensa))
    data['firmasecretaria'] = FirmaCertificadoSecretaria.objects.filter(areafirma=1, activo=True, status=True)[0]
    firma_departamento = PersonaDepartamentoFirmas.objects.get(tipopersonadepartamento_id=1, departamentofirma_id=1,status=True, actualidad=True)

    listafirmaspersonadepartamento = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=1, departamentofirma_id=1, status=True)
    for firma in listafirmaspersonadepartamento:
        if firma.fechafin  is not None and firma.fechainicio  is not None:
            if tribunalmatriculado.fechadefensa <= firma.fechafin and tribunalmatriculado.fechadefensa >= firma.fechainicio:
                firma_departamento = firma

    data['firmadirector'] = firma_departamento
    data['nombrepromediofinal'] = numero_a_letras(graduado.promediotitulacion)
    return download_html_to_pdf(
        'graduados/actagradoposgrado_pdf.html',
        {
            'pagesize': 'A4',
            'data': data,
        }
    )

def actagradoposgradoconintegrantesfirma(request):
    from sga.models import TipoActaTemaTitulacionPosgradoMatricula
    import datetime
    data = {}
    data['matriculadoposgrado'] = matriculadoposgrado = TemaTitulacionPosgradoMatricula.objects.get(id=request.POST['id'])
    data['graduadoposgrado'] = graduado =Graduado.objects.get(inscripcion=matriculadoposgrado.matricula.inscripcion)
    if matriculadoposgrado.cabeceratitulacionposgrado:
        tribunalmatriculado = matriculadoposgrado.cabeceratitulacionposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
    else:
        tribunalmatriculado = matriculadoposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]

    data['tribunalmatriculado'] = tribunalmatriculado
    data['fechagraduados'] = fecha_letra_con_dia_numero(str(tribunalmatriculado.fechadefensa))

    listafirmaspersonadepartamento = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=1, departamentofirma_id=1, status=True)
    obj_director = None
    for firma in listafirmaspersonadepartamento:
        if firma.fechafin  is not None and firma.fechainicio  is not None:
            if tribunalmatriculado.fechadefensa <= firma.fechafin and tribunalmatriculado.fechadefensa >= firma.fechainicio:
                obj_director = firma

    if obj_director is None:
        obj_director = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=1, departamentofirma_id=1, status=True, actualidad=True).first()

    data['firmadirector'] = obj_director

    # obtener secretaria
    fecha = tribunalmatriculado.fechadefensa
    secretarias = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=5, departamentofirma_id=3, status=True, activo=True)
    obj_secretaria = None
    for secretaria in secretarias:
        if secretaria.fechafin is not None and secretaria.fechainicio is not None:
            if fecha <= secretaria.fechafin and fecha >= secretaria.fechainicio:
                obj_secretaria = secretaria
    if obj_secretaria is None:
        obj_secretaria = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=5, departamentofirma_id=3, status=True, activo=True, actualidad=True).first()
    data['firmasecretaria'] = obj_secretaria

    # obtener RECTOR
    data['firmarector'] = obj_rector = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=6, departamentofirma_id=3,status=True, activo=True, actualidad=True).first()
    data['nombrepromediofinal'] = numero_a_letras(graduado.promediotitulacion)

    if matriculadoposgrado.califico and matriculadoposgrado.actacerrada:
        # crear tipo de acta:
        nombre_acta = matriculadoposgrado.mecanismotitulacionposgrado if matriculadoposgrado.mecanismotitulacionposgrado else 'ACTA DE GRADO'
        tipoacta = TipoActaTemaTitulacionPosgradoMatricula.objects.filter(status=True, nombre=nombre_acta)
        if not tipoacta.exists():
            tipoacta = TipoActaTemaTitulacionPosgradoMatricula(nombre=nombre_acta)
            tipoacta.save(request)
        else:
            tipoacta = tipoacta.first()

        # crea orden firma rector
        nombre_cargo = 'RECTOR'
        orden_firma_cargo_rector = matriculadoposgrado.get_or_create_orden_firma(request, nombre_cargo, 3, tipoacta)

        # crea orden firma director
        nombre_cargo = obj_director.denominacionpuesto.descripcion
        orden_firma_cargo_director = matriculadoposgrado.get_or_create_orden_firma(request, nombre_cargo, 1, tipoacta)

        # crea orden firma secretaria
        nombre_cargo = obj_secretaria.denominacionpuesto.descripcion
        orden_firma_cargo_secretaria = matriculadoposgrado.get_or_create_orden_firma(request, nombre_cargo, 2, tipoacta)

        text = matriculadoposgrado.update_or_create_integrante(request, obj_rector.personadepartamento, orden_firma_cargo_rector.id)
        text += matriculadoposgrado.update_or_create_integrante(request, obj_director.personadepartamento, orden_firma_cargo_director.id)
        text += matriculadoposgrado.update_or_create_integrante(request, obj_secretaria.personadepartamento, orden_firma_cargo_secretaria.id)

        plantilla_pdf = 'graduados/actagradoposgradoconintegrantefirma_pdf.html'
        archivo_pdf = matriculadoposgrado.generar_actualizar_acta_graduado_pdf(request, data, plantilla_pdf).replace('\\', '/')

        # observacion historial
        if matriculadoposgrado.archivo_acta_grado:
            observacion = f'Se actualizó el acta de grado, {text if text else ""} en la fecha: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        else:
            observacion = f'Se generó el acta de grado, {text if text else ""} en la fecha: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

        matriculadoposgrado.archivo_acta_grado = archivo_pdf
        matriculadoposgrado.estado_firmas_acta_graduado = 0
        matriculadoposgrado.save(request)

        matriculadoposgrado.reset_integrantes_firma()

        archivo = matriculadoposgrado.archivo_acta_grado
        response = HttpResponse(archivo.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{archivo.name}"'

        # guradar historial
        matriculadoposgrado.guardar_historial_firma_titulacion_pos_mat(request, observacion, archivo_pdf)

        # notificar
        matriculadoposgrado.notificar_integrante_acta_de_grado_generada(request)

        return matriculadoposgrado.get_documento_informe()
    else:
        return False

def certificaciondefensaposgradoconintegrantesfirma(request):
    from sga.models import TipoActaTemaTitulacionPosgradoMatricula
    import datetime
    data = {}
    data['matriculadoposgrado'] = matriculadoposgrado = TemaTitulacionPosgradoMatricula.objects.get(id=int(request.POST['id']))
    data['graduadoposgrado'] = graduadoposgrado = Graduado.objects.get(inscripcion=matriculadoposgrado.matricula.inscripcion)
    nombequivalencia = 'Deficiente / Reprobado'
    if graduadoposgrado.promediotitulacion >= 96:
        nombequivalencia = 'Excelente'
    if graduadoposgrado.promediotitulacion >= 85 and graduadoposgrado.promediotitulacion < 96:
        nombequivalencia = 'Muy Bueno'
    if graduadoposgrado.promediotitulacion >= 80 and graduadoposgrado.promediotitulacion < 85:
        nombequivalencia = 'Bueno'
    if graduadoposgrado.promediotitulacion >= 70 and graduadoposgrado.promediotitulacion < 80:
        nombequivalencia = 'Regular'
    data['nombequivalencia'] = nombequivalencia

    data['detallecalificacion'] = detallecalificacion = matriculadoposgrado.calificaciontitulacionposgrado_set.filter( status=True).order_by('tipojuradocalificador')
    data['promediofinal'] =  detallecalificacion.values_list('puntajerubricas').aggregate(promedio=Avg('puntajerubricas'))['promedio']
    data['listadomodelorubrica'] = matriculadoposgrado.rubrica.modelorubricatitulacionposgrado_set.filter( status=True).order_by('orden')
    if matriculadoposgrado.cabeceratitulacionposgrado:
        tribunalmatriculado = matriculadoposgrado.cabeceratitulacionposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
    else:
        tribunalmatriculado = matriculadoposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]

    data['tribunalmatriculado'] = tribunalmatriculado

    PRESIDENTE = 4
    SECRETEARIO = 6
    VOCAL = 5

    text = matriculadoposgrado.update_or_create_integrante(request, tribunalmatriculado.presidentepropuesta.persona,PRESIDENTE)
    text += matriculadoposgrado.update_or_create_integrante(request, tribunalmatriculado.delegadopropuesta.persona,VOCAL)
    text += matriculadoposgrado.update_or_create_integrante(request, tribunalmatriculado.secretariopropuesta.persona, SECRETEARIO)

    plantilla_pdf = 'graduados/titulacionposgrado/certificaciondefensaconintegrantefirma_pdf.html'
    archivo_pdf = matriculadoposgrado.generar_actualizar_certificacion_defensa_pdf(request, data, plantilla_pdf).replace('\\', '/')

    # observacion historial
    if matriculadoposgrado.archivo_certificacion_defensa:
        observacion = f'Se actualizó certificación de la defensa, {text if text else ""} en la fecha: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
    else:
        observacion = f'Se generó certificación de la defensa, {text if text else ""} en la fecha: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

    CERTIFICACION_DEFENSA = 9
    matriculadoposgrado.reset_integrantes_firma_por_tipo(CERTIFICACION_DEFENSA)

    matriculadoposgrado.archivo_certificacion_defensa = archivo_pdf
    matriculadoposgrado.save(request)


    archivo = matriculadoposgrado.archivo_certificacion_defensa

    # guradar historial
    matriculadoposgrado.guardar_historial_firma_titulacion_pos_mat_certificacion_defensa(request, observacion, archivo_pdf)
    matriculadoposgrado.notificar_integrantes_a_firmar_certificacion_defensa(request)
    response = HttpResponse(archivo.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{archivo.name}"'

    return matriculadoposgrado.get_documento_certificacion_defensa()


def actasustentacionnotaposgradoconintegrantesfirma(request):
    from sga.models import TipoActaTemaTitulacionPosgradoMatricula
    import datetime
    data = {}
    data['matriculadoposgrado'] = matriculadoposgrado = TemaTitulacionPosgradoMatricula.objects.get(id=request.POST['id'])
    data['graduadoposgrado'] = graduadoposgrado = Graduado.objects.get( inscripcion=matriculadoposgrado.matricula.inscripcion)
    nombequivalencia = 'Deficiente / Reprobado'
    if graduadoposgrado.promediotitulacion >= 96:
        nombequivalencia = 'Excelente'
    if graduadoposgrado.promediotitulacion >= 85 and graduadoposgrado.promediotitulacion < 96:
        nombequivalencia = 'Muy Bueno'
    if graduadoposgrado.promediotitulacion >= 80 and graduadoposgrado.promediotitulacion < 85:
        nombequivalencia = 'Bueno'
    if graduadoposgrado.promediotitulacion >= 70 and graduadoposgrado.promediotitulacion < 80:
        nombequivalencia = 'Regular'
    data['nombequivalencia'] = nombequivalencia

    if matriculadoposgrado.cabeceratitulacionposgrado:
        tribunalmatriculado =  matriculadoposgrado.cabeceratitulacionposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
    else:
        tribunalmatriculado = matriculadoposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]

    firma_departamento = PersonaDepartamentoFirmas.objects.get(tipopersonadepartamento_id=1, departamentofirma_id=1, status=True, actualidad=True)

    listafirmaspersonadepartamento = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=1,departamentofirma_id=1, status=True)
    for firma in listafirmaspersonadepartamento:
        if firma.fechafin is not None and firma.fechainicio is not None:
            if tribunalmatriculado.fechadefensa <= firma.fechafin and tribunalmatriculado.fechadefensa >= firma.fechainicio:
                firma_departamento = firma

    data['firmadirector'] = firma_departamento
    data['tribunalmatriculado'] = tribunalmatriculado
    data['fechagraduados'] = fecha_letra(str(tribunalmatriculado.fechadefensa))
    data['firmasecretaria'] = FirmaCertificadoSecretaria.objects.filter(areafirma=1, activo=True, status=True)[0]
    data['firmadirector'] = PersonaDepartamentoFirmas.objects.get(tipopersonadepartamento_id=1, departamentofirma_id=1, status=True, actualidad=True)


    plantilla_pdf = 'graduados/titulacionposgrado/actasustentacionnotaconintegrantefirma_pdf.html'
    archivo_pdf = matriculadoposgrado.generar_actualizar_acta_sustentacion_nota_pdf(request, data, plantilla_pdf).replace('\\', '/')

    PRESIDENTE = 7
    SECRETEARIO = 8
    VOCAL = 9
    MAESTRANTE = 10
    text = matriculadoposgrado.update_or_create_integrante(request, tribunalmatriculado.presidentepropuesta.persona, PRESIDENTE)
    text += matriculadoposgrado.update_or_create_integrante(request, tribunalmatriculado.delegadopropuesta.persona, VOCAL)
    text += matriculadoposgrado.update_or_create_integrante(request, tribunalmatriculado.secretariopropuesta.persona, SECRETEARIO)
    text += matriculadoposgrado.update_or_create_integrante(request, graduadoposgrado.inscripcion.persona, MAESTRANTE)

    # observacion historial
    if matriculadoposgrado.archivo_acta_sustentacion:
        observacion = f'Se actualizó el acta de sustentación con nota, {text if text else ""} en la fecha: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
    else:
        observacion = f'Se generó el acta de sustentación con nota, {text if text else ""} en la fecha: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

    ACTA_SUSTENTACION_CON_NOTA = 10
    matriculadoposgrado.reset_integrantes_firma_por_tipo(ACTA_SUSTENTACION_CON_NOTA)

    matriculadoposgrado.archivo_acta_sustentacion = archivo_pdf
    matriculadoposgrado.save(request)
    archivo = matriculadoposgrado.archivo_acta_sustentacion

    # guradar historial
    matriculadoposgrado.guardar_historial_firma_titulacion_pos_mat_acta_sustentacion_nota(request, observacion, archivo_pdf)
    matriculadoposgrado.notificar_integrantes_a_firmar_acta_sustentacion(request)
    response = HttpResponse(archivo.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{archivo.name}"'


    return matriculadoposgrado.get_documento_acta_sustentacion_nota()

def actagradoposgrado2(idinscripcion):
    data = {}
    data['matriculadoposgrado'] = matriculadoposgrado = TemaTitulacionPosgradoMatricula.objects.get(id=idinscripcion)
    data['graduadoposgrado'] = graduado = Graduado.objects.get(inscripcion=matriculadoposgrado.matricula.inscripcion)
    if matriculadoposgrado.cabeceratitulacionposgrado:
        tribunalmatriculado = matriculadoposgrado.cabeceratitulacionposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
    else:
        tribunalmatriculado = matriculadoposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]

    data['tribunalmatriculado'] = tribunalmatriculado
    data['fechagraduados'] = fecha_letra_con_dia_numero(str(tribunalmatriculado.fechadefensa))
    data['firmasecretaria'] = FirmaCertificadoSecretaria.objects.filter(areafirma=1, activo=True, status=True)[0]
    firma_departamento = PersonaDepartamentoFirmas.objects.get(tipopersonadepartamento_id=1, departamentofirma_id=1,status=True, actualidad=True)

    listafirmaspersonadepartamento = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=1, departamentofirma_id=1, status=True)
    for firma in listafirmaspersonadepartamento:
        if firma.fechafin is not None and firma.fechainicio is not None:
            if tribunalmatriculado.fechadefensa <= firma.fechafin and tribunalmatriculado.fechadefensa >= firma.fechainicio:
                firma_departamento = firma

    data['firmadirector'] = firma_departamento
    data['nombrepromediofinal'] = numero_a_letras(graduado.promediotitulacion)
    qrname = 'actasdegrado' + str(matriculadoposgrado.id)
    directory = os.path.join(SITE_STORAGE, 'media', 'tematitulacionposgrado')
    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'tematitulacionposgrado', 'actasdegrado'))
    try:
        os.stat(directory)
    except:
        os.mkdir(directory)
    directory = os.path.join(SITE_STORAGE, 'media', 'tematitulacionposgrado','actasdegrado')
    try:
        os.stat(directory)
    except:
        os.mkdir(directory)
    rutapdf = folder + qrname + '.pdf'

    if os.path.isfile(rutapdf):
        os.remove(rutapdf)
    conviert_html_to_pdfsaveactagrado(
        'graduados/actagradoposgrado_pdf.html',
        {
            'pagesize': 'A4',
            'data': data,
        }, qrname + '.pdf', 'actasdegrado'
    )
    return 'tematitulacionposgrado/actasdegrado/' + qrname + '.pdf' ,  'https://sga.unemi.edu.ec/media/tematitulacionposgrado/actasdegrado/' + qrname + '.pdf'

def actagradoposgradograduados(idinscripcion):
    data = {}
    data['graduadoposgrado'] = graduado =Graduado.objects.get(inscripcion=idinscripcion)
    data['matriculadoposgrado'] = matriculadoposgrado = TemaTitulacionPosgradoMatricula.objects.filter(matricula__inscripcion=idinscripcion).order_by('-id')[0]
    if not matriculadoposgrado.mecanismotitulacionposgrado.id == 15: #complexivo
        if matriculadoposgrado.cabeceratitulacionposgrado:
            tribunalmatriculado = matriculadoposgrado.cabeceratitulacionposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
        else:
            tribunalmatriculado = matriculadoposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]

        data['tribunalmatriculado'] = tribunalmatriculado
        data['fechagraduados'] = fecha_letra_con_dia_numero(str(tribunalmatriculado.fechadefensa))
        data['firmasecretaria'] = FirmaCertificadoSecretaria.objects.filter(areafirma=1, activo=True, status=True)[0]
        firma_departamento = PersonaDepartamentoFirmas.objects.get(tipopersonadepartamento_id=1, departamentofirma_id=1,status=True, actualidad=True)

        listafirmaspersonadepartamento = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=1, departamentofirma_id=1, status=True)
        for firma in listafirmaspersonadepartamento:
            if firma.fechafin  is not None and firma.fechainicio  is not None:
                if tribunalmatriculado.fechadefensa <= firma.fechafin and tribunalmatriculado.fechadefensa >= firma.fechainicio:
                    firma_departamento = firma

        data['firmadirector'] = firma_departamento
        data['nombrepromediofinal'] = numero_a_letras(graduado.promediotitulacion)
        return download_html_to_pdf(
            'graduados/actagradoposgrado_pdf.html',
            {
                'pagesize': 'A4',
                'data': data,
            }
        )
    else:
        data['detalleexamen'] = fecha_examen_complexivo = matriculadoposgrado.detallegrupotitulacionpostgrado_set.filter(status=True)[0]
        data['fechagraduados'] = fecha_letra_con_dia_numero(str(fecha_examen_complexivo.grupoTitulacionPostgrado.fecha))

        data['firmasecretaria'] = FirmaCertificadoSecretaria.objects.filter(areafirma=1, activo=True, status=True)[0]
        data['firmadirector'] = PersonaDepartamentoFirmas.objects.get(tipopersonadepartamento_id=1,
                                                                      departamentofirma_id=1, status=True,
                                                                      actualidad=True)
        data['nombrepromediofinal'] = numero_a_letras(graduado.promediotitulacion)
        return download_html_to_pdf(
            'graduados/actagradoposgradocomplexivo_pdf.html',
            {
                'pagesize': 'A4',
                'data': data,
            }
        )

def getactagradoposgradograduados2(idinscripcion):
    data = {}
    data['graduadoposgrado'] = graduado =Graduado.objects.get(inscripcion=idinscripcion)
    data['matriculadoposgrado'] = matriculadoposgrado = TemaTitulacionPosgradoMatricula.objects.filter(matricula__inscripcion=idinscripcion).order_by('-id')[0]
    if not matriculadoposgrado.mecanismotitulacionposgrado.id == 15: #complexivo
        if matriculadoposgrado.cabeceratitulacionposgrado:
            tribunalmatriculado = matriculadoposgrado.cabeceratitulacionposgrado.tribunaltematitulacionposgradomatricula_set.filter(
                status=True)[0]
        else:
            tribunalmatriculado = matriculadoposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
        data['tribunalmatriculado'] = tribunalmatriculado
        data['fechagraduados'] = fecha_letra_con_dia_numero(str(tribunalmatriculado.fechadefensa))
        listafirmaspersonadepartamento = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=1,
                                                                                  departamentofirma_id=1,
                                                                                  status=True)
        for firma in listafirmaspersonadepartamento:
            if firma.fechafin is not None and firma.fechainicio is not None:
                if tribunalmatriculado.fechadefensa <= firma.fechafin and tribunalmatriculado.fechadefensa >= firma.fechainicio:
                    obj_director = firma
        data['firmadirector'] = obj_director

        fecha = tribunalmatriculado.fechadefensa
        secretarias = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=5, departamentofirma_id=3,
                                                               status=True, activo=True)
        obj_secretaria = None
        for secretaria in secretarias:
            if secretaria.fechafin is not None and secretaria.fechainicio is not None:
                if fecha <= secretaria.fechafin and fecha >= secretaria.fechainicio:
                    obj_secretaria = secretaria
        if obj_secretaria is None:
            obj_secretaria = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=5,
                                                                      departamentofirma_id=3, status=True,
                                                                      activo=True, actualidad=True).first()
        data['firmasecretaria'] = obj_secretaria

        data['firmarector'] = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=6,
                                                                       departamentofirma_id=3,
                                                                       status=True, activo=True,
                                                                       actualidad=True).first()
        data['nombrepromediofinal'] = numero_a_letras(graduado.promediotitulacion)
        return download_html_to_pdf(
            'graduados/actagradoposgradoconintegrantefirma_pdf.html',
            {
                'pagesize': 'A4',
                'data': data,
            }
        )
    else:
        data['detalleexamen'] = fecha_examen_complexivo = \
        matriculadoposgrado.detallegrupotitulacionpostgrado_set.filter(status=True)[0]
        data['fechagraduados'] = fecha_letra_con_dia_numero(
            str(fecha_examen_complexivo.grupoTitulacionPostgrado.fecha))
        data['nombrepromediofinal'] = numero_a_letras(graduado.promediotitulacion)
        fecha = fecha_examen_complexivo.grupoTitulacionPostgrado.fecha
        secretarias = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=5, departamentofirma_id=3,
                                                               status=True, activo=True)
        obj_secretaria = None
        for secretaria in secretarias:
            if secretaria.fechafin is not None and secretaria.fechainicio is not None:
                if fecha <= secretaria.fechafin and fecha >= secretaria.fechainicio:
                    obj_secretaria = secretaria
        if obj_secretaria is None:
            obj_secretaria = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=5,
                                                                      departamentofirma_id=3, status=True,
                                                                      activo=True, actualidad=True).first()
        data['firmasecretaria'] = obj_secretaria

        data['firmadirector'] = PersonaDepartamentoFirmas.objects.get(tipopersonadepartamento_id=1,
                                                                      departamentofirma_id=1,
                                                                      status=True, activo=True,
                                                                      actualidad=True)

        data['firmarector'] = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=6,
                                                                       departamentofirma_id=3,
                                                                       status=True, activo=True,
                                                                       actualidad=True).first()
        return download_html_to_pdf(
            'graduados/actagradoposgradocomplexivoconintegrantefirma_pdf.html',
            {
                'pagesize': 'A4',
                'data': data,
            }
        )


def actagradoposgradocomplexivo(idinscripcion):
    data = {}
    data['matriculadoposgrado'] = matriculadoposgrado = TemaTitulacionPosgradoMatricula.objects.get(id=idinscripcion)
    data['graduadoposgrado'] = graduado = Graduado.objects.get(inscripcion=matriculadoposgrado.matricula.inscripcion)
    data['detalleexamen'] = fecha_examen_complexivo = matriculadoposgrado.detallegrupotitulacionpostgrado_set.filter(status=True)[0]
    data['fechagraduados'] = fecha_letra_con_dia_numero(str(fecha_examen_complexivo.grupoTitulacionPostgrado.fecha))

    data['firmasecretaria'] = FirmaCertificadoSecretaria.objects.filter(areafirma=1, activo=True, status=True)[0]
    data['firmadirector'] = PersonaDepartamentoFirmas.objects.get(tipopersonadepartamento_id=1, departamentofirma_id=1, status=True, actualidad=True)
    data['nombrepromediofinal'] = numero_a_letras(graduado.promediotitulacion)
    return download_html_to_pdf(
        'graduados/actagradoposgradocomplexivo_pdf.html',
        {
            'pagesize': 'A4',
            'data': data,
        }
    )

def actagradoposgradocomplexivoconintegantesfirma(request):
    from sga.models import TipoActaTemaTitulacionPosgradoMatricula
    import datetime
    data = {}
    data['matriculadoposgrado'] = matriculadoposgrado = TemaTitulacionPosgradoMatricula.objects.get(id=request.POST['id'])
    data['graduadoposgrado'] = graduado = Graduado.objects.get(inscripcion=matriculadoposgrado.matricula.inscripcion)
    data['detalleexamen'] = fecha_examen_complexivo = matriculadoposgrado.detallegrupotitulacionpostgrado_set.filter(status=True)[0]
    data['fechagraduados'] = fecha_letra_con_dia_numero(str(fecha_examen_complexivo.grupoTitulacionPostgrado.fecha))
    data['nombrepromediofinal'] = numero_a_letras(graduado.promediotitulacion)

    #obtener secretaria
    fecha = fecha_examen_complexivo.grupoTitulacionPostgrado.fecha

    secretarias = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=5, departamentofirma_id=3, status=True, activo=True)
    obj_secretaria = None
    for secretaria in secretarias:
        if secretaria.fechafin is not None and secretaria.fechainicio is not None:
            if fecha <= secretaria.fechafin and fecha >= secretaria.fechainicio:
                obj_secretaria = secretaria
    if obj_secretaria is None:
        obj_secretaria = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=5, departamentofirma_id=3, status=True, activo=True, actualidad=True).first()
    data['firmasecretaria'] = obj_secretaria

    # obtener director
    data['firmadirector'] = obj_director = PersonaDepartamentoFirmas.objects.get(tipopersonadepartamento_id=1, departamentofirma_id=1, status=True, activo=True, actualidad=True)

    # obtener RECTOR
    data['firmarector'] = obj_rector = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=6, departamentofirma_id=3,status=True, activo=True, actualidad=True).first()

    if matriculadoposgrado.califico and matriculadoposgrado.actacerrada:
        # crear tipo de acta:
        nombre_acta = matriculadoposgrado.mecanismotitulacionposgrado if matriculadoposgrado.mecanismotitulacionposgrado else 'ACTA DE GRADO'
        tipoacta = TipoActaTemaTitulacionPosgradoMatricula.objects.filter(status=True, nombre=nombre_acta)
        if not tipoacta.exists():
            tipoacta = TipoActaTemaTitulacionPosgradoMatricula(nombre=nombre_acta)
            tipoacta.save(request)
        else:
            tipoacta = tipoacta.first()

        # crea orden firma rector
        nombre_cargo = 'RECTOR'
        orden_firma_cargo_rector = matriculadoposgrado.get_or_create_orden_firma(request, nombre_cargo, 3, tipoacta)

        # crea orden firma director
        nombre_cargo = obj_director.denominacionpuesto.descripcion
        orden_firma_cargo_director = matriculadoposgrado.get_or_create_orden_firma(request, nombre_cargo, 1, tipoacta)

        # crea orden firma secretaria
        nombre_cargo = obj_secretaria.denominacionpuesto.descripcion
        orden_firma_cargo_secretaria = matriculadoposgrado.get_or_create_orden_firma(request, nombre_cargo, 2, tipoacta)

        text = matriculadoposgrado.update_or_create_integrante(request, obj_rector.personadepartamento, orden_firma_cargo_rector.id)
        text += matriculadoposgrado.update_or_create_integrante(request, obj_director.personadepartamento, orden_firma_cargo_director.id)
        text += matriculadoposgrado.update_or_create_integrante(request, obj_secretaria.personadepartamento, orden_firma_cargo_secretaria.id)

        plantilla_pdf = 'graduados/actagradoposgradocomplexivoconintegrantefirma_pdf.html'
        archivo_pdf = matriculadoposgrado.generar_actualizar_acta_graduado_pdf(request, data, plantilla_pdf).replace('\\', '/')

        # observacion historial
        if matriculadoposgrado.archivo_acta_grado:
            observacion = f'Se actualizó el acta de grado, {text if text else ""}en la fecha: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        else:
            observacion = f'Se generó el acta de grado, {text if text else ""}en la fecha: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

        matriculadoposgrado.archivo_acta_grado = archivo_pdf
        matriculadoposgrado.estado_firmas_acta_graduado = 0
        matriculadoposgrado.save(request)

        matriculadoposgrado.reset_integrantes_firma()

        archivo = matriculadoposgrado.archivo_acta_grado
        response = HttpResponse(archivo.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{archivo.name}"'

        # guradar historial
        matriculadoposgrado.guardar_historial_firma_titulacion_pos_mat(request, observacion, archivo_pdf)

        # notificar
        matriculadoposgrado.notificar_integrante_acta_de_grado_generada(request)

        return matriculadoposgrado.get_documento_informe()
    else:
        return False


def actagradoposgradocomplexivoconintegantesfirmamasivo(request):
    from sga.models import TipoActaTemaTitulacionPosgradoMatricula
    import datetime
    data = {}
    temas = TemaTitulacionPosgradoMatricula.objects.filter(califico=True, actacerrada=True, status=True, estado_acta_firma=4,
                                                           mecanismotitulacionposgrado__in=(15, 21), convocatoria_id=request.POST.get('id'))
    actasgeneradas = 0
    eroractas = 0
    for item in temas:
        with transaction.atomic():
            try:
                if not item.archivo_acta_grado:
                    data['matriculadoposgrado'] = matriculadoposgrado = TemaTitulacionPosgradoMatricula.objects.get(id=item.id)
                    data['graduadoposgrado'] = graduado = Graduado.objects.get(inscripcion=matriculadoposgrado.matricula.inscripcion)
                    data['detalleexamen'] = fecha_examen_complexivo = matriculadoposgrado.detallegrupotitulacionpostgrado_set.filter(status=True)[0]
                    data['fechagraduados'] = fecha_letra_con_dia_numero(str(fecha_examen_complexivo.grupoTitulacionPostgrado.fecha))
                    data['nombrepromediofinal'] = numero_a_letras(graduado.promediotitulacion)

                    # obtener secretaria
                    fecha = fecha_examen_complexivo.grupoTitulacionPostgrado.fecha
                    secretarias = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=5, departamentofirma_id=3,
                                                                           status=True, activo=True)
                    obj_secretaria = None
                    for secretaria in secretarias:
                        if secretaria.fechafin is not None and secretaria.fechainicio is not None:
                            if fecha <= secretaria.fechafin and fecha >= secretaria.fechainicio:
                                obj_secretaria = secretaria
                    if obj_secretaria is None:
                        obj_secretaria = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=5,
                                                                                  departamentofirma_id=3, status=True,
                                                                                  activo=True, actualidad=True).first()
                    data['firmasecretaria'] = obj_secretaria
                    # obtener director
                    data['firmadirector'] = obj_director = PersonaDepartamentoFirmas.objects.get(tipopersonadepartamento_id=1,
                                                                                                 departamentofirma_id=1,
                                                                                                 status=True, activo=True,
                                                                                                 actualidad=True)

                    # obtener RECTOR
                    data['firmarector'] = obj_rector = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=6,
                                                                                                departamentofirma_id=3,
                                                                                                status=True, activo=True,
                                                                                                actualidad=True).first()

                    nombre_acta = matriculadoposgrado.mecanismotitulacionposgrado if matriculadoposgrado.mecanismotitulacionposgrado else 'ACTA DE GRADO'
                    tipoacta = TipoActaTemaTitulacionPosgradoMatricula.objects.filter(status=True, nombre=nombre_acta)
                    if not tipoacta.exists():
                        tipoacta = TipoActaTemaTitulacionPosgradoMatricula(nombre=nombre_acta)
                        tipoacta.save(request)
                    else:
                        tipoacta = tipoacta.first()

                    # crea orden firma rector
                    nombre_cargo = 'RECTOR'
                    orden_firma_cargo_rector = matriculadoposgrado.get_or_create_orden_firma(request, nombre_cargo, 3,
                                                                                             tipoacta)

                    # crea orden firma director
                    nombre_cargo = obj_director.denominacionpuesto.descripcion
                    orden_firma_cargo_director = matriculadoposgrado.get_or_create_orden_firma(request, nombre_cargo, 1,
                                                                                               tipoacta)

                    # crea orden firma secretaria
                    nombre_cargo = obj_secretaria.denominacionpuesto.descripcion
                    orden_firma_cargo_secretaria = matriculadoposgrado.get_or_create_orden_firma(request, nombre_cargo, 2,
                                                                                                 tipoacta)

                    text = matriculadoposgrado.update_or_create_integrante(request, obj_rector.personadepartamento,
                                                                           orden_firma_cargo_rector.id)
                    text += matriculadoposgrado.update_or_create_integrante(request, obj_director.personadepartamento,
                                                                            orden_firma_cargo_director.id)
                    text += matriculadoposgrado.update_or_create_integrante(request, obj_secretaria.personadepartamento,
                                                                            orden_firma_cargo_secretaria.id)

                    plantilla_pdf = 'graduados/actagradoposgradocomplexivoconintegrantefirma_pdf.html'
                    archivo_pdf = matriculadoposgrado.generar_actualizar_acta_graduado_pdf(request, data,
                                                                                           plantilla_pdf).replace('\\', '/')

                    # observacion historial
                    if matriculadoposgrado.archivo_acta_grado:
                        observacion = f'Se actualizó el acta de grado, {text if text else ""}en la fecha: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
                    else:
                        observacion = f'Se generó el acta de grado, {text if text else ""}en la fecha: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

                    matriculadoposgrado.archivo_acta_grado = archivo_pdf
                    matriculadoposgrado.estado_firmas_acta_graduado = 0
                    matriculadoposgrado.save(request)

                    matriculadoposgrado.reset_integrantes_firma()

                    archivo = matriculadoposgrado.archivo_acta_grado
                    response = HttpResponse(archivo.read(), content_type='application/pdf')
                    response['Content-Disposition'] = f'inline; filename="{archivo.name}"'

                    # guradar historial
                    matriculadoposgrado.guardar_historial_firma_titulacion_pos_mat(request, observacion, archivo_pdf)
                    actasgeneradas += 1
            except Exception as e:
                eroractas += 1
                print(e)

    return actasgeneradas, eroractas, obj_director.personadepartamento

def actagradoposgradocomplexivocontent(idinscripcion):
    data = {}
    data['matriculadoposgrado'] = matriculadoposgrado = TemaTitulacionPosgradoMatricula.objects.get(id=idinscripcion)
    data['graduadoposgrado'] = graduado = Graduado.objects.get(inscripcion=matriculadoposgrado.matricula.inscripcion)
    data['detalleexamen'] = fecha_examen_complexivo = matriculadoposgrado.detallegrupotitulacionpostgrado_set.filter(status=True)[0]
    data['fechagraduados'] = fecha_letra_con_dia_numero(str(fecha_examen_complexivo.grupoTitulacionPostgrado.fecha))

    data['firmasecretaria'] = FirmaCertificadoSecretaria.objects.filter(areafirma=1, activo=True, status=True)[0]
    data['firmadirector'] = PersonaDepartamentoFirmas.objects.get(tipopersonadepartamento_id=1, departamentofirma_id=1, status=True, actualidad=True)
    data['nombrepromediofinal'] = numero_a_letras(graduado.promediotitulacion)
    return download_html_to_pdf_get_content(
        'graduados/actagradoposgradocomplexivo_pdf.html',
        {
            'pagesize': 'A4',
            'data': data,
        }
    )


def actagradoposgradocomplexivo2(idinscripcion):
    data = {}
    data['matriculadoposgrado'] = matriculadoposgrado = TemaTitulacionPosgradoMatricula.objects.get(id=idinscripcion)
    data['graduadoposgrado'] = graduado = Graduado.objects.get(inscripcion=matriculadoposgrado.matricula.inscripcion)
    data['detalleexamen'] = fecha_examen_complexivo = matriculadoposgrado.detallegrupotitulacionpostgrado_set.filter(status=True)[0]
    data['fechagraduados'] = fecha_letra_con_dia_numero(str(fecha_examen_complexivo.grupoTitulacionPostgrado.fecha))

    data['firmasecretaria'] = FirmaCertificadoSecretaria.objects.filter(areafirma=1, activo=True, status=True)[0]
    data['firmadirector'] = PersonaDepartamentoFirmas.objects.get(tipopersonadepartamento_id=1, departamentofirma_id=1, status=True, actualidad=True)
    data['nombrepromediofinal'] = numero_a_letras(graduado.promediotitulacion)
    qrname = 'actasdegrado' + str(matriculadoposgrado.id)
    directory = os.path.join(SITE_STORAGE, 'media', 'tematitulacionposgrado')
    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'tematitulacionposgrado', 'actasdegradocomplexivo'))
    try:
        os.stat(directory)
    except:
        os.mkdir(directory)
    directory = os.path.join(SITE_STORAGE, 'media', 'tematitulacionposgrado', 'actasdegradocomplexivo')
    try:
        os.stat(directory)
    except:
        os.mkdir(directory)
    rutapdf = folder + qrname + '.pdf'

    if os.path.isfile(rutapdf):
        os.remove(rutapdf)
    conviert_html_to_pdfsaveactagrado(
        'graduados/actagradoposgrado_pdf.html',
        {
            'pagesize': 'A4',
            'data': data,
        }, qrname + '.pdf', 'actasdegradocomplexivo'
    )
    return 'tematitulacionposgrado/actasdegradocomplexivo/' + qrname + '.pdf', 'https://sga.unemi.edu.ec/media/tematitulacionposgrado/actasdegradocomplexivo/' + qrname + '.pdf'


def certificaciondefensa(idinscripcion):
    data = {}
    data['matriculadoposgrado'] = matriculadoposgrado = TemaTitulacionPosgradoMatricula.objects.get(id=idinscripcion)
    data['graduadoposgrado'] = graduadoposgrado = Graduado.objects.get(inscripcion=matriculadoposgrado.matricula.inscripcion)
    nombequivalencia = 'Deficiente / Reprobado'
    if graduadoposgrado.promediotitulacion >= 96:
        nombequivalencia = 'Excelente'
    if graduadoposgrado.promediotitulacion >= 85 and graduadoposgrado.promediotitulacion < 96:
        nombequivalencia = 'Muy Bueno'
    if graduadoposgrado.promediotitulacion >= 80 and graduadoposgrado.promediotitulacion < 85:
        nombequivalencia = 'Bueno'
    if graduadoposgrado.promediotitulacion >= 70 and graduadoposgrado.promediotitulacion < 80:
        nombequivalencia = 'Regular'
    data['nombequivalencia'] = nombequivalencia

    data['detallecalificacion'] = detallecalificacion = matriculadoposgrado.calificaciontitulacionposgrado_set.filter(status=True).order_by('tipojuradocalificador')
    data['promediofinal'] = detallecalificacion.values_list('puntajerubricas').aggregate(promedio=Avg('puntajerubricas'))['promedio']
    data['listadomodelorubrica'] = matriculadoposgrado.rubrica.modelorubricatitulacionposgrado_set.filter(status=True).order_by('orden')
    if matriculadoposgrado.cabeceratitulacionposgrado:
        tribunalmatriculado = matriculadoposgrado.cabeceratitulacionposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
    else:
        tribunalmatriculado = matriculadoposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]

    data['tribunalmatriculado'] = tribunalmatriculado
    return download_html_to_pdf(
        'graduados/certificaciondefensapos_pdf.html',
        {
            'pagesize': 'A4',
            'data': data,
        }
    )


def actadefensaposgrado(idinscripcion):
    data = {}
    data['matriculadoposgrado'] = matriculadoposgrado = TemaTitulacionPosgradoMatricula.objects.get(id=idinscripcion)
    if matriculadoposgrado.cabeceratitulacionposgrado:
        data['tribunalmatriculado'] = tribunalmatriculado = matriculadoposgrado.cabeceratitulacionposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
    else:
        data['tribunalmatriculado'] = tribunalmatriculado = matriculadoposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
    data['fechagraduados'] = fecha_letra(str(tribunalmatriculado.fechadefensa))
    data['firmasecretaria'] = FirmaCertificadoSecretaria.objects.filter(areafirma=1, activo=True, status=True)[0]
    firma_departamento = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=1, departamentofirma_id=1,
                                                               status=True, actualidad=True).first()

    listafirmaspersonadepartamento = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=1,
                                                                              departamentofirma_id=1, status=True)
    for firma in listafirmaspersonadepartamento:
        if firma.fechafin is not None and firma.fechainicio is not None:
            if tribunalmatriculado.fechadefensa <= firma.fechafin and tribunalmatriculado.fechadefensa >= firma.fechainicio:
                firma_departamento = firma

    data['firmadirector'] = firma_departamento
    return download_html_to_pdf(
        'graduados/actadefensaposgrado_pdf.html',
        {
            'pagesize': 'A4',
            'data': data,
        }
    )
def obtener_maestria_mencion(eTemaTitulacionPosgradoMatricula):
    einscripcion = eTemaTitulacionPosgradoMatricula.matricula.inscripcion
    malla = eTemaTitulacionPosgradoMatricula.matricula.inscripcion.malla_inscripcion().malla
    if malla.tiene_itinerario_malla_especialidad():
        eItinerarioMallaEspecilidad = ItinerarioMallaEspecilidad.objects.filter(malla=malla,itinerario=einscripcion.itinerario,status=True).first()
        return f'{einscripcion.carrera.titulootorga } CON MENCIÓN EN {eItinerarioMallaEspecilidad.nombre}'
    return None

def actaaprobacionexamencomplexivoposgrado(idinscripcion):
    data = {}
    data['matriculadoposgrado'] = matriculadoposgrado = TemaTitulacionPosgradoMatricula.objects.get(id=idinscripcion)
    data['nota_examen'] = nota_examen = matriculadoposgrado.obtener_nota_examen_complexivo().nota
    data ['titulo_otorga_mencion'] = obtener_maestria_mencion(matriculadoposgrado)
    if matriculadoposgrado.cabeceratitulacionposgrado:
        nota_ensayo = matriculadoposgrado.obtener_calificacion_ensayo_pareja()
    else:
        nota_ensayo =matriculadoposgrado.obtener_calificacion_ensayo_individual()

    if nota_ensayo:

        data['nota_ensayo']= nota_ensayo
        data['total_nota']= float(nota_ensayo) +float(nota_examen)
    else:
        data['total_nota']= float(nota_examen)
    teorico = 0
    practico = 0
    if matriculadoposgrado.convocatoria.carrera_id == 227:
        teorico= 40
        practico= 60
    else:
        teorico = 60
        practico = 40
    data['teorico'] =teorico
    data['practico'] =practico


    return download_html_to_pdf(
        'graduados/actaaproacionexamenposgrado_pdf.html',
        {
            'pagesize': 'A4',
            'data': data,
        }
    )


def actadefensaposgradonotas(idinscripcion):
    data = {}
    data['matriculadoposgrado'] = matriculadoposgrado = TemaTitulacionPosgradoMatricula.objects.get(id=idinscripcion)
    data['graduadoposgrado'] = graduadoposgrado = Graduado.objects.get(inscripcion=matriculadoposgrado.matricula.inscripcion)
    nombequivalencia = 'Deficiente / Reprobado'
    if graduadoposgrado.promediotitulacion >= 96:
        nombequivalencia = 'Excelente'
    if graduadoposgrado.promediotitulacion >= 85 and graduadoposgrado.promediotitulacion < 96:
        nombequivalencia = 'Muy Bueno'
    if graduadoposgrado.promediotitulacion >= 80 and graduadoposgrado.promediotitulacion < 85:
        nombequivalencia = 'Bueno'
    if graduadoposgrado.promediotitulacion >= 70 and graduadoposgrado.promediotitulacion < 80:
        nombequivalencia = 'Regular'
    data['nombequivalencia'] = nombequivalencia

    if matriculadoposgrado.cabeceratitulacionposgrado:
        tribunalmatriculado = matriculadoposgrado.cabeceratitulacionposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
    else:
        tribunalmatriculado = matriculadoposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]

    firma_departamento = PersonaDepartamentoFirmas.objects.get(tipopersonadepartamento_id=1, departamentofirma_id=1,
                                                               status=True, actualidad=True)

    listafirmaspersonadepartamento = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=1,
                                                                              departamentofirma_id=1, status=True)
    for firma in listafirmaspersonadepartamento:
        if firma.fechafin is not None and firma.fechainicio is not None:
            if tribunalmatriculado.fechadefensa <= firma.fechafin and tribunalmatriculado.fechadefensa >= firma.fechainicio:
                firma_departamento = firma

    data['firmadirector'] = firma_departamento

    data['tribunalmatriculado'] = tribunalmatriculado
    data['fechagraduados'] = fecha_letra(str(tribunalmatriculado.fechadefensa))
    data['firmasecretaria'] = FirmaCertificadoSecretaria.objects.filter(areafirma=1, activo=True, status=True)[0]
    data['firmadirector'] = PersonaDepartamentoFirmas.objects.get(tipopersonadepartamento_id=1, departamentofirma_id=1, status=True, actualidad=True)
    return download_html_to_pdf(
        'graduados/actadefensaposgradonotas_pdf.html',
        {
            'pagesize': 'A4',
            'data': data,
        }
    )


def rubricatribunalcalificacionposgrado(iddetallegrupo):
    data = {}
    lista = []
    data['fechaactual'] = datetime.now()
    data['participante'] = participante = TemaTitulacionPosgradoMatricula.objects.get(pk=iddetallegrupo)
    data['calificacionrubricatitulacion'] = calificacionrubricatitulacion = participante.calificaciontitulacionposgrado_set.filter(status=True).order_by('tipojuradocalificador')
    data['numerotribunales'] = calificacionrubricatitulacion.count()
    data['promediofinal'] = null_to_decimal(calificacionrubricatitulacion.values_list('puntajerubricas').aggregate(promedio=Avg('puntajerubricas'))['promedio'], 2)
    rubricasevaluadas = DetalleRubricaTitulacionPosgrado.objects.select_related().filter(modelorubrica__rubrica=participante.rubrica, status=True).order_by('modelorubrica__orden', 'orden')
    for rubrica in rubricasevaluadas:
        puntajepresidente = rubrica.calificaciondetallerubricatitulacionposgrado_set.filter(calificacionrubrica__tematitulacionposgradomatricula=participante, status=True).order_by('calificacionrubrica__tipojuradocalificador')
        lista.append([rubrica, puntajepresidente])
    data['ponderacionesrubrica'] = RubricaTitulacionCabPonderacionPosgrado.objects.filter(rubrica=rubricasevaluadas[0].rubricatitulacionposgrado, status=True).order_by('orden')
    data['rubricasevaluadas'] = lista
    return download_html_to_pdf('graduados/calificacionrubricasposgrado_pdf.html',
                                {
                                    'pagesize': 'A4',
                                    'data': data,
                                }
                                )


def informetribunaltitulacionposgrado(id):
    data = {}
    revision = Revision.objects.get(pk=id)
    data['revision'] = revision

    fecha = datetime.today().date()
    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
    return download_html_to_pdf(
        'pro_tutoriaposgrado/informetribunaltitulacionposgrado.html',
        {
            'pagesize': 'A4',
            'data': data,
        }
    )

def informe_posgrado(id):
    data = {}
    informe = Informe.objects.get(pk=id)
    data['informe'] = informe

    fecha = datetime.today().date()
    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
    return download_html_to_pdf(
        'pro_tutoriaposgrado/informeposgrado.html',
        {
            'pagesize': 'A4',
            'data': data,
        }
    )

def acompanamientoposgrado(idinscripcion):
    data = {}
    data['grupo'] = grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=idinscripcion)
    periodo = grupo.matricula.nivel.periodo
    carrera = grupo.matricula.inscripcion.carrera
    data['configuracion'] = None
    if periodo.configuraciontitulacionposgrado_set.filter(carrera=carrera, status=True).exists():
        data['configuracion'] = periodo.configuraciontitulacionposgrado_set.filter(carrera=carrera, status=True).latest('id')
    data['acompanamientos'] = grupo.tutoriastematitulacionposgradoprofesor_set.filter(status=True).order_by('fecharegistro')
    data['integrantes'] = integrantes = grupo
    data['facultad'] = grupo.matricula.inscripcion.coordinacion
    fecha = datetime.today().date()
    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
    return download_html_to_pdf(
        'pro_tutoriaposgrado/actaacompanamiento_pdf.html',
        {
            'pagesize': 'A4',
            'data': data,
        }
    )


def reporte_informe_tutoria_posgrado(idtema):
    data = {}
    data['grupo'] = grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=idtema)
    data['tribunalmatriculado'] = tribunalmatriculado =grupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
    data['trabajo_titulacion'] = trabajo_titulacion =grupo.revisiontutoriastematitulacionposgradoprofesor_set.filter(estado=2, status=True)[0]
    fecha = datetime.today().date()
    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
    return download_html_to_pdf(
        'pro_tutoriaposgrado/informe_tutorias_posgrado_posgrado_pdf.html',
        {
            'pagesize': 'A4',
            'data': data,
        }
    )

def reporte_informe_tutoria_posgrado_pareja(idtema):
    data = {}
    data['grupo'] = grupo = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=idtema)
    data['tribunalmatriculado'] = tribunalmatriculado =grupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
    data['trabajo_titulacion'] = trabajo_titulacion =grupo.revisiontutoriastematitulacionposgradoprofesor_set.filter(estado=2, status=True)[0]
    fecha = datetime.today().date()
    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
    return download_html_to_pdf(
        'pro_tutoriaposgrado/informe_tutorias_posgrado_posgrado_pareja_pdf.html',
        {
            'pagesize': 'A4',
            'data': data,
        }
    )


def acompanamientoposgradopareja(idpareja):
    data = {}
    data['grupo'] = grupo = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=idpareja)
    periodo = grupo.convocatoria.periodo
    carrera = grupo.convocatoria.carrera
    data['configuracion'] = None
    if periodo.configuraciontitulacionposgrado_set.filter(carrera=carrera, status=True).exists():
        data['configuracion'] = periodo.configuraciontitulacionposgrado_set.filter(carrera=carrera, status=True).latest('id')
    data['acompanamientos'] = grupo.tutoriastematitulacionposgradoprofesor_set.filter(status=True).order_by('fecharegistro')
    data['integrantes'] = integrantes = grupo.obtener_parejas
    data['facultad'] = grupo.obtener_parejas()[0].matricula.inscripcion.coordinacion
    fecha = datetime.today().date()
    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
    return download_html_to_pdf(
        'pro_tutoriaposgrado/actaacompanamientopareja_pdf.html',
        {
            'pagesize': 'A4',
            'data': data,
        }
    )

def actatitulacioncomplexivo(idasignado):
    import time
    data = {}
    respuesta = False
    data['fechaactual'] = datetime.now()
    data['asignado'] = asignado = MateriaTitulacion.objects.get(pk=idasignado)
    qrname = 'qr_actatitulacion_' + str(asignado.id)

    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'actatitulacion', ''))
    os.makedirs(folder, exist_ok=True)
    rutapdf = folder + qrname + '.pdf'
    rutaimg = folder + qrname + '.png'

    if os.path.isfile(rutapdf):
        os.remove(rutapdf)

    # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/actatitulacion/' + qrname + '_firmado.pdf')
    url = pyqrcode.create('https://sga.unemi.edu.ec//media/qrcode/actatitulacion/' + qrname + '_firmado.pdf')
    imageqr = url.png(folder + qrname + '.png', 16, '#000000')
    imagenqr = qrname
    grupo = GrupoTitulacionIC.objects.get(materia_id=asignado.materiaasignada.materia.id)
    if grupo.tiporubrica == 4:
        data['listadodocentesfirmas'] = listadodocentesfirmas = FirmaGrupoTitulacion.objects.filter(grupofirma=asignado.grupofirma).order_by('orden')
        data['totalfirmas'] = listadodocentesfirmas.count()
        valida = conviert_html_to_pdfsaveactas('adm_complexivotematica/acta_titulacionv3_pdf.html',
                                               {
                                                   'pagesize': 'A4',
                                                   'data': data,
                                                   'qrname': imagenqr
                                               }, qrname + '.pdf', 'actatitulacion'
                                               )
    else:
        data['listadodocentesfirmas'] = FirmaGrupoTitulacion.objects.filter(grupofirma=asignado.grupofirma).order_by('orden')
        valida = conviert_html_to_pdfsaveactas('adm_complexivotematica/acta_titulacionv2_pdf.html',
                                               {
                                                   'pagesize': 'A4',
                                                   'data': data,
                                                   'qrname': imagenqr
                                               }, qrname + '.pdf', 'actatitulacion'
                                               )
    if valida:
        time.sleep(2)
        respuesta = True
        if os.path.isfile(rutaimg):
            os.remove(rutaimg)

    # return 'https://sga.unemi.edu.ec/media/qrcode/actatitulacion/' + qrname + '.pdf'
    return respuesta

def actagradocomplexivo(idgraduado):
    data = {}
    data['fechaactual'] = datetime.now()
    data['graduado'] = graduado = Graduado.objects.get(pk=idgraduado)
    data['firmasecretaria'] = FirmaCertificadoSecretaria.objects.filter(persona=graduado.secretariageneral, areafirma=1, status=True)[0]
    return download_html_to_pdf('graduados/acta_gradocomplexivo_pdf.html',
                                {
                                    'pagesize': 'A4',
                                    'data': data,
                                }
                                )

def actagradocomplexivofirma(idgraduado):
    data = {}
    respuesta = False
    data['fechaactual'] = datetime.now()
    data['graduado'] = graduado = Graduado.objects.get(pk=idgraduado)
    qrname = 'fe_actagrado_' + str(idgraduado)
    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'actatitulacion', ''))
    rutapdf = folder + qrname + '.pdf'
    if os.path.isfile(rutapdf):
        os.remove(rutapdf)
    data['firmasecretaria'] = FirmaCertificadoSecretaria.objects.filter(persona=graduado.secretariageneral, areafirma=1, status=True)[0]
    valida = conviert_html_to_pdfsaveactas('graduados/actagrado_fe_pdf.html',
                                           {
                                               'pagesize': 'A4',
                                               'data': data,
                                           }, qrname + '.pdf', 'actatitulacion'
                                           )
    if valida:
        import time
        respuesta = True

    return respuesta

def actaconsolidadafirma(idgraduado):
    data = {}

    data['graduado'] = graduado = Graduado.objects.get(pk=idgraduado)
    ultimonivelmalla = graduado.inscripcion.mi_malla().ultimo_nivel_malla()

    nombreniveles = ['PRIMERO', 'SEGUNDO', 'TERCERO', 'CUARTO', 'QUINTO', 'SEXTO', 'SEPTIMO', 'OCTAVO', 'NOVENO', 'DECIMO']
    data['miultimonivelnombre'] = nombreniveles[int(ultimonivelmalla.orden-1)]

    qrname = 'fe_actaconsolidada_' + str(idgraduado)
    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'actatitulacion', ''))
    rutapdf = folder + qrname + '.pdf'
    if os.path.isfile(rutapdf):
        os.remove(rutapdf)
    data['directores'] = graduado.directoresfacultad.all()
    data['es_complexivo'] = False
    data['firmasecretaria'] = FirmaCertificadoSecretaria.objects.filter(persona=graduado.secretariageneral, areafirma=1, status=True)[0]
    promediofinal = graduado.notagraduacion
    data['totaltitulacion'] = null_to_decimal(graduado.promediotitulacion, 2)

    if graduado.fechagraduado in [None, '']:
        data['fechagraduados'] = ''
    else:
        data['fechagraduados'] = fecha_letra(str(graduado.fechagraduado))
    if graduado.fechaconsejo in [None, '']:
        data['fechaconsejo'] = ''
    else:
        data['fechaconsejo'] = fecha_letra(str(graduado.fechaconsejo))
    if graduado.fechaconsejo in [None, '']:
        data['mesconsejo'] = ''
    else:
        data['mesconsejo'] = fecha_letra(str(graduado.fechaconsejo))
    if graduado.inscripcion.egresado_set.filter(status=True).exists():
        data['egresado'] = Egresado.objects.get(inscripcion_id=graduado.inscripcion.id, status=True)
    if graduado.inscripcion.persona.perfilinscripcion_set.filter(status=True).exists():
        data['perfilinscripcion'] = PerfilInscripcion.objects.get(persona=graduado.inscripcion.persona.id)
    else:
        data['perfilinscripcion'] = ''

    data['horasvinculacion'] = graduado.inscripcion.numero_horas_proyectos_vinculacion()
    data['vinculacion'] = graduado.inscripcion.mis_proyectos_vinculacion()
    data['listacertificadoidioma'] = CertificadoIdioma.objects.values_list('id', 'idioma__nombre', 'nivelsuficencia__descripcion').filter(persona=graduado.inscripcion.persona,
                                                                                                                                          historialcertificacionpersona__perfilusuario=graduado.inscripcion.perfil_usuario(),
                                                                                                                                          historialcertificacionpersona__estado=1,
                                                                                                                                          status=True).distinct()
    if PracticasPreprofesionalesInscripcion.objects.filter(inscripcion_id=graduado.inscripcion.id, status=True, culminada=True).exists():
        data['parcticas'] = PracticasPreprofesionalesInscripcion.objects.filter(inscripcion_id=graduado.inscripcion.id, status=True, culminada=True)
        data['horaspracticas'] = null_to_numeric(PracticasPreprofesionalesInscripcion.objects.filter(inscripcion=graduado.inscripcion.id, status=True, culminada=True).aggregate(valor=Sum('numerohora'))['valor'])

    data['recordhistorico'] = RecordAcademico.objects.filter(status=True,
                                                             inscripcion_id=graduado.inscripcion.id,
                                                             validapromedio=True,
                                                             aprobada=True,
                                                             noaplica=False,
                                                             asignatura__modulo=False).order_by('asignaturamalla__nivelmalla__id')

    asignaturaingles = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(malla__id=22, status=True)
    data['modulo_ingles'] = RecordAcademico.objects.filter(status=True, inscripcion__id=graduado.inscripcion.id, asignatura__id__in=asignaturaingles, aprobada=True, noaplica=False).order_by('asignatura__nombre')
    asignaturaingles = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(malla__id=32, status=True)
    data['modulo_computacion'] = RecordAcademico.objects.filter(status= True, inscripcion__id=graduado.inscripcion.id, asignatura__id__in=asignaturaingles, aprobada=True, noaplica=False)
    if graduado.decano:
        data['decano_es_hombre'] = graduado.decano.es_hombre()
    if graduado.subdecano:
        data['subdecano_es_hombre'] = graduado.subdecano.es_hombre()
    data['totalhoras'] = graduado.inscripcion.total_horas()
    if graduado.creditotitulacion:
        data['totalcreditos'] = null_to_decimal(graduado.inscripcion.creditos() + graduado.creditovinculacion + graduado.creditopracticas + graduado.creditotitulacion, 2)
    else:
        data['totalcreditos'] = null_to_decimal((graduado.inscripcion.creditos() + graduado.creditovinculacion + graduado.creditopracticas + 0), 2)
    data['promfinal'] = promediofinal
    data['asistentefacultad'] = str(graduado.asistentefacultad.nombre_completo()) if graduado.asistentefacultad else None
    valida = conviert_html_to_pdfsaveactas('graduados/actaconsolidada_fe_pdf.html',
                                           {'pagesize': 'A4', 'data': data}, qrname + '.pdf', 'actatitulacion'
                                           )
    respuesta = False
    if valida:
        import time
        respuesta = True

    return respuesta
CHOICES_FUNCION_VIEW_REQUISITO = (
    (1, u"detallematriculadoultimo"),
    (2, u"detallemallapenultimoaprobada"),
    (4, u"detalleingles"),
    (4, u"detalleingles"),
    (5, u"detallecomputacion"),
    (6, u"detallepracprofesionales"),
    (7, u"detallevinculacion"),
    (8, u"noadeudar"),
    (10, u"aprobaringlesdirector"),
    (11, u"detallemallaaprobada"),
    (12, u"detallemallapenultimoaprobada"),
    (13, u"aprobaringlesdirector"),
)
def listadovalidarequisitos(inscripcion, materia=None, requisitotitulacion=None):
    data = {}
    lista = []
    if materia and requisitotitulacion:
        listrequisitos = materia.requisitomateriaunidadintegracioncurricular_set.filter(activo=True, titulacion=True, status=True)

        for lis in listrequisitos:
            valida = False
            vistafuncion = ''
            for li in CHOICES_FUNCION_VIEW_REQUISITO:
                if lis.requisito.funcion == li[0]:
                    valida = True
            if valida:
                if dict(CHOICES_FUNCION_VIEW_REQUISITO)[lis.requisito.funcion]:
                    vistafuncion = dict(CHOICES_FUNCION_VIEW_REQUISITO)[lis.requisito.funcion]
            lista.append([lis.requisito.nombre, lis.run(inscripcion.id), lis.detarequisitos(inscripcion.id), vistafuncion])
    data['materia'] = materia
    data['inscripcion'] = inscripcion
    mimalla = 0
    ultimonivelmalla = 0
    penultimonivel = 0
    if inscripcion.mi_malla():
        mimalla = inscripcion.mi_malla()
        ultimonivelmalla = inscripcion.mi_malla().ultimo_nivel_malla()
        penultimonivel = inscripcion.mi_malla().ultimo_nivel_malla().orden - 1
    data['mimalla'] = mimalla
    data['ultimonivelmalla'] = ultimonivelmalla
    data['penultimonivel'] = penultimonivel
    data['listrequisitos'] = lista
    template = get_template("adm_alternativatitulacion/viewrequisitos.html")
    json_content = template.render(data)
    return JsonResponse({"result": "ok", 'data': json_content })

def listadofaltantefirmaracta(materiatitulacion):
    data = {}
    data['alumno'] = materiatitulacion
    data['docentesfirman'] = materiatitulacion.grupofirma.profesoresgrupo_firman()
    data['idfirmado'] = materiatitulacion.materiatitulacionfirma_set.values_list('firmadocente_id', flat=True).filter(status=True)
    template = get_template("adm_alternativatitulacion/viewfaltantesfirmar.html")
    json_content = template.render(data)
    return JsonResponse({"result": "ok", 'data': json_content })


def listadodocentescriterios(idcriterio, opc):
    data = {}
    if opc == '1':
        criterio = CriterioDocenciaPeriodo.objects.get(pk=idcriterio, criterio__tipo=1)
        listadodocentes = DetalleDistributivo.objects.filter(criteriodocenciaperiodo=criterio).order_by('distributivo__profesor__persona__apellido1','distributivo__profesor__persona__apellido2','distributivo__profesor__persona__nombres')
    if opc == '2':
        criterio = CriterioInvestigacionPeriodo.objects.get(pk=idcriterio)
        listadodocentes = DetalleDistributivo.objects.filter(criterioinvestigacionperiodo=criterio).order_by('distributivo__profesor__persona__apellido1', 'distributivo__profesor__persona__apellido2', 'distributivo__profesor__persona__nombres')
    if opc == '3':
        criterio = CriterioGestionPeriodo.objects.get(pk=idcriterio)
        listadodocentes = DetalleDistributivo.objects.filter(criteriogestionperiodo=criterio).order_by('distributivo__profesor__persona__apellido1', 'distributivo__profesor__persona__apellido2', 'distributivo__profesor__persona__nombres')
    if opc == '4':
        criterio = CriterioDocenciaPeriodo.objects.get(pk=idcriterio, criterio__tipo=2)
        listadodocentes = DetalleDistributivo.objects.filter(criteriodocenciaperiodo=criterio).order_by('distributivo__profesor__persona__apellido1', 'distributivo__profesor__persona__apellido2', 'distributivo__profesor__persona__nombres')

    data['criterio'] = criterio
    data['opc'] = int(opc) if opc else 0
    data['listadodocentes'] = listadodocentes
    template = get_template("adm_evaluaciondocentesacreditacion/viewdocentescriterios.html")
    json_content = template.render(data)
    return JsonResponse({"result": "ok", 'data': json_content })



def fecha_letra(valor):
    mes = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    a = int(valor[0:4])
    m = int(valor[5:7])
    d = int(valor[8:10])
    if d == 1:
        return u"al %s día del mes de %s del %s" % (numero_a_letras(d), str(mes[m - 1]), numero_a_letras(a))
    else:
        if d == 21:
            return u"a los %s días del mes de %s del %s" % (u'veintiún', str(mes[m - 1]), numero_a_letras(a))
        else:
            if d == 31:
                return u"a los %s días del mes de %s del %s" % (u'treintaiún', str(mes[m - 1]), numero_a_letras(a))
            else:
                return u"a los %s días del mes de %s del %s" % (numero_a_letras(d), str(mes[m - 1]), numero_a_letras(a))


def fecha_letra_con_dia_numero(valor):
    mes = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    a = int(valor[0:4])
    m = int(valor[5:7])
    d = int(valor[8:10])
    if d == 1:
        return u"al %s (%s) día del mes de %s del %s" % (numero_a_letras(d),d, str(mes[m - 1]), numero_a_letras(a))
    else:
        if d == 21:
            return u"a los %s (%s) días del mes de %s del %s" % (u'veintiún',d, str(mes[m - 1]), numero_a_letras(a))
        else:
            if d == 31:
                return u"a los %s (%s) días del mes de %s del %s" % (u'treintaiún',d, str(mes[m - 1]), numero_a_letras(a))
            else:
                return u"a los %s (%s)  días del mes de %s del %s" % (numero_a_letras(d),d, str(mes[m - 1]), numero_a_letras(a))


def recordatoriopagomaestrante(idmat):
    data = {}
    data['fechaactual'] = fe = datetime.now().date()
    data['maestrante'] = matricula = Matricula.objects.get(status=True, pk=int(idmat))
    data['vencidas'] = Rubro.objects.filter(status=True, matricula=matricula, fechavence__lt=fe, cancelado=False).count()
    data['totalvencido'] = Decimal(null_to_decimal(Rubro.objects.values_list('valor').filter(status=True, matricula=matricula, fechavence__lt=fe, cancelado=False).aggregate(valor=Sum('valor'))['valor'],2)).quantize(Decimal('.01'))

    d = datetime.now()
    qrname = 'recordatoriopago_' + str(idmat) + '_' + d.strftime('%Y%m%d_%H%M%S')
    directory = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'recordatoriopago')
    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'recordatoriopago', 'rp'))
    try:
        os.stat(directory)
    except:
        os.mkdir(directory)
    rutapdf = folder + qrname + '.pdf'

    if os.path.isfile(rutapdf):
        os.remove(rutapdf)

    archi = 'recordatoriopago/' + qrname + '.pdf'

    ru = matricula.rubro_set.filter(fechavence__lt=fe, tipo__tiporubro=1, cancelado=False, status=True).order_by('-fechavence').first()

    if not RecordatorioPagoMaestrante.objects.filter(status=True, matricula=matricula, rubro=ru).exists():
        reco = RecordatorioPagoMaestrante(matricula=matricula,
                                          rubro=ru,
                                          archivo=archi)
        reco.save()

    # url = pyqrcode.create('http://127.0.0.1:8000/media/qrcode/recordatoriopago/' + qrname + '.pdf')
    url = pyqrcode.create('https://sga.unemi.edu.ec/media/qrcode/recordatoriopago/' + qrname + '.pdf')

    htmlcontrato = 'alu_requisitosmaestria/recordatoriopagosvencidos.html'

    imagenqr = 'qr' + qrname

    conviert_html_to_pdfsavecontratomae(
        htmlcontrato,
        {
            'pagesize': 'A4',
            'data': data,
            'imprimeqr': True,
            'qrname': imagenqr
        }, qrname + '.pdf', 'recordatoriopago'
    )

    fe = datetime.now().date()
    # return 'http://127.0.0.1:8000/media/qrcode/recordatoriopago/' + qrname + '.pdf' + '?v=' + str(fe)
    return 'https://sga.unemi.edu.ec/media/qrcode/recordatoriopago/' + qrname + '.pdf'


def recordatoriopagoavencermaestrante(idmat):
    data = {}
    data['fechaactual'] = fe = datetime.now().date()
    data['maestrante'] = matricula = Matricula.objects.get(status=True, pk=int(idmat))
    data['rubroavencer'] = matricula.rubro_set.filter(tipo__tiporubro=1, cancelado=False, status=True).order_by('fechavence').first()
    data['totalvencido'] = Decimal(null_to_decimal(Rubro.objects.values_list('valor').filter(status=True, matricula=matricula, fechavence__lt=fe, cancelado=False).aggregate(valor=Sum('valor'))['valor'],2)).quantize(Decimal('.01'))

    d = datetime.now()

    qrname = 'recordatoriopago_' + str(idmat) + '_' + d.strftime('%Y%m%d_%H%M%S')
    directory = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'recordatoriopago')
    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'recordatoriopago', 'rp'))
    try:
        os.stat(directory)
    except:
        os.mkdir(directory)
    rutapdf = folder + qrname + '.pdf'

    if os.path.isfile(rutapdf):
        os.remove(rutapdf)

    # url = pyqrcode.create('http://127.0.0.1:8000/media/qrcode/recordatoriopago/' + qrname + '.pdf')
    url = pyqrcode.create('https://sga.unemi.edu.ec/media/qrcode/recordatoriopago/' + qrname + '.pdf')

    htmlcontrato = 'alu_requisitosmaestria/recordatoriopagosavencer.html'

    imagenqr = 'qr' + qrname

    conviert_html_to_pdfsavecontratomae(
        htmlcontrato,
        {
            'pagesize': 'A4',
            'data': data,
            'imprimeqr': True,
            'qrname': imagenqr
        }, qrname + '.pdf', 'recordatoriopago'
    )

    fe = datetime.now().date()
    # return 'http://127.0.0.1:8000/media/qrcode/recordatoriopago/' + qrname + '.pdf' + '?v=' + str(fe)
    return 'https://sga.unemi.edu.ec/media/qrcode/recordatoriopago/' + qrname + '.pdf'


def actaaprobacionexamencomplexivoposgrado_svelte(idinscripcion,request):
    fechaactual = datetime.now()
    directory_qr = os.path.join(SITE_STORAGE, 'media', 'tematitulacionposgrado', '')
    try:
        os.stat(directory_qr)
    except:
        os.mkdir(directory_qr)

    data = {}
    data['matriculadoposgrado'] = matriculadoposgrado = TemaTitulacionPosgradoMatricula.objects.get(id=idinscripcion)
    data['nota_examen']= nota_examen = matriculadoposgrado.obtener_nota_examen_complexivo().nota
    data['titulo_otorga_mencion'] = obtener_maestria_mencion(matriculadoposgrado)
    if matriculadoposgrado.cabeceratitulacionposgrado:
        nota_ensayo = matriculadoposgrado.obtener_calificacion_ensayo_pareja()
    else:
        nota_ensayo =matriculadoposgrado.obtener_calificacion_ensayo_individual()

    if nota_ensayo:

        data['nota_ensayo']= nota_ensayo
        data['total_nota']= float(nota_ensayo) +float(nota_examen)
    else:
        data['total_nota']= float(nota_examen)

    teorico = 0
    practico = 0
    if matriculadoposgrado.convocatoria.carrera_id == 227:
        teorico= 40
        practico= 60
    else:
        teorico = 60
        practico = 40
    data['teorico'] =teorico
    data['practico'] =practico

    filename = f'actacomplexivo_{fechaactual.year}{fechaactual.month}{fechaactual.day}_{fechaactual.hour}{fechaactual.minute}{fechaactual.second}'
    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'tematitulacionposgrado', ''))
    valida, pdf, result = conviert_html_to_pdf_titulacion_exa_complexivo(request, 'graduados/actaaproacionexamenposgrado_pdfsvelte.html', data,folder, filename + '.pdf')
    if not valida:
        raise NameError('Error al generar el oficio')
    file_pdf = "{}/{}/{}".format(MEDIA_URL, 'tematitulacionposgrado/', filename + '.pdf')
    return file_pdf

def generar_acta_compromiso_v2(detallepreins):
    url_path = 'http://127.0.0.1:8000'
    if not DEBUG:
        url_path = 'https://sga.unemi.edu.ec'
    hoy = datetime.now()
    data = {}
    data['fecha'] = hoy.date
    data['hora'] = hoy.time()
    data['preins'] = detallepreins
    nombre_archivo = generar_nombre(f'acta_compromiso_{detallepreins.id}_', 'generado') + '.pdf'
    data['persona'] = persona = detallepreins.inscripcion.persona

    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'preinscripcion', 'actacompromiso', ''))
    filename = generar_nombre(f'acta_compromiso_preinscripcion_{persona.usuario.username}_{detallepreins.id}_','')
    os.makedirs(folder, exist_ok=True)
    os.makedirs(f'{folder}/qrcode/', exist_ok=True)
    data['url_pdf'] = url_pdf = f'{url_path}/media/preinscripcion/actacompromiso/{nombre_archivo}'
    url = pyqrcode.create(url_pdf)
    imageqr = url.png(f'{folder}/qrcode/{filename}.png', 16, '#000000')
    data['url_qr'] = f'{folder}/qrcode/{filename}.png'
    pdf, response = conviert_html_to_pdf_save_file_model(
        'matriculacion/acta_compromiso_asignaturapracticas_presencial_semipresencial.html',
        {'pagesize': 'a4 landscape',
         'data': data, }, nombre_archivo)
    return pdf, response

def generar_acta_compromiso_v3(proyectovinculacioninscripcion):
    url_path = 'http://127.0.0.1:8000'
    if not DEBUG:
        url_path = 'https://sga.unemi.edu.ec'
    hoy = datetime.now()
    data = {}
    data['fecha'] = hoy.date
    data['hora'] = hoy.time()
    data['inscrip'] = proyectovinculacioninscripcion
    nombre_archivo = generar_nombre(f'acta_compromiso_{proyectovinculacioninscripcion.id}_', 'generado') + '.pdf'
    data['nombre_proyecto'] = proyectovinculacioninscripcion.periodo.proyecto
    data['persona'] = persona = proyectovinculacioninscripcion.inscripcion.persona
    formato_acta = 'matriculacion/acta_compromiso_vinculacion_enlinea.html' if proyectovinculacioninscripcion.inscripcion.carrera.modalidad == 3 else 'matriculacion/acta_compromiso_vinculacion_presencial_semipresencial.html'
    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'proyectovinculacion', 'actacompromiso', ''))
    filename = generar_nombre(f'acta_compromiso_vinculacion_{persona.usuario.username}_{proyectovinculacioninscripcion.id}_','')
    os.makedirs(folder, exist_ok=True)
    os.makedirs(f'{folder}/qrcode/', exist_ok=True)
    data['url_pdf'] = url_pdf = f'{url_path}/media/proyectovinculacion/actacompromiso/{nombre_archivo}'
    url = pyqrcode.create(url_pdf)
    imageqr = url.png(f'{folder}/qrcode/{filename}.png', 16, '#000000')
    data['url_qr'] = f'{folder}/qrcode/{filename}.png'
    pdf, response = conviert_html_to_pdf_save_file_model(
        formato_acta,
        {'pagesize': 'a4 landscape',
         'data': data, }, nombre_archivo)
    return pdf, response