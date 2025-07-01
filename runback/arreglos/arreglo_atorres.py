#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import os
import sys

# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
from datetime import datetime

import pyqrcode

# from runback.arreglos.arreglo_jussy2 import get_valor_crobro_arancel_nse, get_valor_cobro_matricula
import xlsxwriter

YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
print(f"YOUR_PATH: {YOUR_PATH}")
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
# print(f"SITE_ROOT: {SITE_ROOT}")
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# print(f"your_djangoproject_home: {your_djangoproject_home}")
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from django.db import transaction
from django.db.models import F
from certi.models import Carnet
from sga.models import Periodo, Matricula
from settings import SITE_STORAGE, PORCIENTO_RECUPERACION_FALTAS


# def eliminar_carnet_sin_fotos():
#     print(f"ELIMINACION DE CARNETS")
#     carnets = Carnet.objects.filter(persona__fotopersona__isnull=True)
#     print(f'se eliminaran {carnets.count()} carnets sin fotos')
#     for key, carnet in enumerate(carnets):
#         persona = carnet.persona
#         carnet.delete()
#         print(f'{key + 1}-> se elimino el carnet  de {persona}')
#
#
# def eliminar_carnet_creadado_y_despues_subido_fotos():
#     print(f"ELIMINACION DE CARNETS")
#     carnets = Carnet.objects.filter(fecha_creacion__lt=F('persona__fotopersona__fecha_creacion'))
#     print(f'se eliminaran {carnets.count()} carnets generado antes de subir foto')
#     for key, carnet in enumerate(carnets):
#         persona = carnet.persona
#         carnet.delete()
#         print(f'{key + 1}-> se elimino el carnet  de {persona}')
#
#
#
#
#
# # eliminar_carnet_sin_fotos()
# # eliminar_carnet_creadado_y_despues_subido_fotos()
#
#
# def notas_e_intentos_admision(periodo=136, coordinacion=9):
#     from django.db import connections
#     from sga.models import Matricula
#     from admision.models import Calificacion, Actividad
#     cursor = connections['moodle_pos'].cursor()
#     matriculas = Matricula.objects.filter(nivel__periodo_id=periodo, inscripcion__carrera__coordinacion__id=coordinacion, estado_matricula__in=[2, 3], status=True)
#     errores = []
#     try:
#         for matricula in matriculas:
#             usuario = matricula.inscripcion.persona.usuario.username
#             # print('Matricula: ', matricula)
#             for materiaasignada in matricula.materiaasignada_set.filter(estado_id__in=[2, 3], retiramateria=False):
#                 # print('------->Materia Asignada: ', materiaasignada)
#                 with transaction.atomic(using='default'):
#                     try:
#                         sql = """
#                                     SELECT us.id userid, gc.id categoryid , ROUND(nota.finalgrade,2) calificacion, UPPER(gc.fullname) evaluativo
#                                             FROM mooc_grade_grades nota
#                                     INNER JOIN mooc_grade_items it ON nota.itemid=it.id AND courseid=%s AND itemtype='category'
#                                     INNER JOIN mooc_grade_categories gc ON gc.courseid=it.courseid AND gc.id=it.iteminstance AND gc.depth=2
#                                     INNER JOIN mooc_user us ON nota.userid=us.id
#                                     WHERE us.username ='%s' and not UPPER(gc.fullname)='RE'
#                                     ORDER BY it.sortorder
#                                 """ % (str(materiaasignada.materia.idcursomoodle), usuario)
#                         cursor.execute(sql)
#                         calificacionesmoodle = cursor.fetchall()
#                         if calificacionesmoodle:
#                             for calificacionmoodle in calificacionesmoodle:
#                                 evaluaciongenerica = materiaasignada.evaluaciongenerica_set.filter(detallemodeloevaluativo__nombre=calificacionmoodle[3]).first()
#                                 # detalleevaluativo = DetalleModeloEvaluativo.objects.filter(nombre=calificacionmoodle[3], status=True)
#
#                                 calificacion = Calificacion.objects.filter(materiaasignada=materiaasignada,
#                                                                            detallemodeloevaluativo=evaluaciongenerica.detallemodeloevaluativo,
#                                                                            status=True).first()
#                                 if not calificacion:
#                                     calificacion = Calificacion(materiaasignada=materiaasignada,
#                                                                 detallemodeloevaluativo=evaluaciongenerica.detallemodeloevaluativo,
#                                                                 calificacionmoodle=calificacionmoodle[2])
#                                 else:
#                                     calificacion.calificacionmoodle = calificacionmoodle[2]
#                                 calificacion.save()
#                                 # print('-------------> Calificacion Moodle: ', calificacion)
#                                 sql = """
#                                         SELECT
#                                             it.iteminstance, it.itemname,
#                                             (select COUNT(attempt) FROM  mooc_quiz_attempts WHERE quiz = it.iteminstance AND userid=%s) intentos,
#                                             (SELECT sumgrades FROM  mooc_quiz_attempts WHERE quiz = it.iteminstance AND userid=%s ORDER BY sumgrades DESC  LIMIT 1) calificacion
#                                         FROM mooc_grade_items it
#                                         WHERE
#                                             it.courseid=%s
#                                             AND it.categoryid=%s
#                                             AND  it.itemtype='mod'
#                                             AND it.itemmodule='quiz'
#                                         """ % (calificacionmoodle[0], calificacionmoodle[0], str(materiaasignada.materia.idcursomoodle), calificacionmoodle[1])
#                                 cursor.execute(sql)
#                                 actividadesmoodle = cursor.fetchall()
#
#                                 for actividadmoodle in actividadesmoodle:
#                                     actividad = Actividad.objects.filter(calificacion=calificacion,
#                                                                          idactividadmoodle=actividadmoodle[0],
#                                                                          nombreactividad=actividadmoodle[1]).first()
#                                     if not actividad:
#                                         actividad = Actividad(calificacion=calificacion,
#                                                               idactividadmoodle=actividadmoodle[0],
#                                                               nombreactividad=actividadmoodle[1],
#                                                               numerointentos=actividadmoodle[2],
#                                                               calificacionmoodle=actividadmoodle[3])
#                                     else:
#                                         actividad.numerointentos = actividadmoodle[2]
#                                         actividad.calificacionmoodle = actividadmoodle[3]
#                                     actividad.save()
#                                     # print('------------------------>', actividad)
#                                 # print(matricula, materiaasignada.materia.asignatura, actividadesmoodle)
#                         else:
#                             evaluacionesgenericas = materiaasignada.evaluaciongenerica_set.filter(status=True)
#                             for evaluacion in evaluacionesgenericas:
#                                 calificacion = Calificacion.objects.filter(materiaasignada=materiaasignada,
#                                                                            detallemodeloevaluativo=evaluacion.detallemodeloevaluativo,
#                                                                            status=True).first()
#                                 if not calificacion:
#                                     calificacion = Calificacion(materiaasignada=materiaasignada,
#                                                                 detallemodeloevaluativo=evaluacion.detallemodeloevaluativo)
#                                 else:
#                                     calificacion.detallemodeloevaluativo = evaluacion.detallemodeloevaluativo
#                                 calificacion.save()
#                     except Exception as ex:
#                         transaction.set_rollback(True)
#                         msg = str(ex)
#                         msg = f'Ocurrio un error en Materia {materiaasignada} de la persona {matricula.inscripcion.persona} detalle eror:{msg}'
#                         print(msg)
#                         errores.append(msg)
#         if errores:
#             for error in errores:
#                 print(error)
#         else:
#             print('Ejecución exitosamente de todos los registros')
#     except Exception as ex:
#         print(ex)
#         print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
#         error = True
#         mensaje_ex = ex.__str__()
#
#
# def eliminacion__preinscripcionbecas_mal_generadas():
#     from sga.models import PreInscripcionBeca
#     preinscripciones = PreInscripcionBeca.objects.filter(periodo_id=126)  # Periodo 126 es el Periodo Mayo a Septiembre 2022
#     numero = preinscripciones.count()
#     print(f'Se eliminaran {numero} registros de PreInscripcionBecas')
#     for i, preinscripcion in enumerate(preinscripciones):
#         print(i+1, preinscripcion)
#         preinscripcion.delete()
#
# # eliminacion__preinscripcionbecas_mal_generadas()
# def insertar_requisitos_preinscripcionbecas():
#     from sga.models import PreInscripcionBeca, PreInscripcionBecaRequisito
#     preinscripciones = PreInscripcionBeca.objects.filter(periodo_id=119)
#     for preinscripcion in preinscripciones:
#         configuracion = preinscripcion.becatipo.becatipoconfiguracion_set.filter(becaperiodo__periodo_id=113).first()
#         print(preinscripcion)
#         if configuracion:
#             requistos_removido = preinscripcion.preinscripcionbecarequisito_set.all().exclude(detallerequisitobeca__in=configuracion.requisitosbecas.all())
#             requistos_removido.delete()
#             for i, detallerequisitobeca in enumerate(configuracion.requisitosbecas.all()):
#                 preinscripcionbecarequisito = preinscripcion.preinscripcionbecarequisito_set.filter(detallerequisitobeca=detallerequisitobeca)
#                 if not preinscripcionbecarequisito:
#                     preinscripcionbecarequisito = PreInscripcionBecaRequisito(
#                         preinscripcion=preinscripcion,
#                         detallerequisitobeca=detallerequisitobeca
#                     )
#                 # preinscripcionbecarequisito.save()
#                 print(f'----------------->{i+1} ', preinscripcionbecarequisito)
#         else:
#             print(f'-----------------> No se ah configurardo tipo periodo beca')
#
# #
# # periodoanterior = Periodo.objects.get(pk=113)
# # periodoactual = Periodo.objects.get(pk=119)
# # insertar_requisitos_preinscripcionbecas()
#
# def actualizar_requisitos_becas(periodo_id, detallerequisitobeca_ids= [1], becatipo_id=None):
#     from sga.models import PreInscripcionBecaRequisito
#     preinscripcionrequisitos = PreInscripcionBecaRequisito.objects.filter(preinscripcion__periodo_id=periodo_id, detallerequisitobeca_id__in=detallerequisitobeca_ids)
#     print('Cantidad de Requisitos-->', preinscripcionrequisitos.count())
#     if becatipo_id:
#         preinscripcionrequisitos = preinscripcionrequisitos.filter(preinscripcion__beca_id=becatipo_id)
#
#     for prerequisito in preinscripcionrequisitos:
#         prerequisito.run()
#         prerequisito.save()
#         print(prerequisito, f'Estado -->{prerequisito.cumplerequisito}')
#
# # periodoactual = Periodo.objects.get(pk=119)
# # actualizar_requisitos_becas(periodoactual.id)
#
# def eliminar_preinscripciones_primernivel_pagos_vencidos(becatipo_id=16, periodo_id=119):
#     from sga.models import PreInscripcionBeca
#     preinscripciones = PreInscripcionBeca.objects.filter(becatipo_id=becatipo_id, inscripcion__matricula__estado_matricula=1, periodo_id=periodo_id)
#     print('Total a eliminar', preinscripciones.count())
#     for preinscripcion in preinscripciones:
#         print(preinscripcion)
#         preinscripcion.delete()
#
#
# #eliminar_preinscripciones_primernivel_pagos_vencidos()

def crear_requisitos_becas_configuracion_x_periodo(periodo_id=119):
    from sga.models import BecaTipoConfiguracion, BecaRequisitos
    configuraciones = BecaTipoConfiguracion.objects.filter(becaperiodo__periodo_id=periodo_id)
    for i, configuracion in enumerate(configuraciones):
        print(f'{i + 1}.- {configuracion}')
        with transaction.atomic(using='default'):
            try:
                for index, detrequisito in enumerate(configuracion.requisitosbecas.filter(visible=True, status=True)):
                    requisitogeneral = detrequisito
                    becarequisitos = BecaRequisitos.objects.filter(becatipo=configuracion.becatipo, periodo_id=periodo_id, requisitogeneral=requisitogeneral).first()
                    if becarequisitos is None:
                        becarequisitos = BecaRequisitos(
                            nombre=requisitogeneral.requisitobeca.nombre,
                            periodo_id=periodo_id,
                            becatipo=configuracion.becatipo,
                            numero=detrequisito.numero,
                            requisitogeneral=requisitogeneral,
                            obligatorio=True)
                        becarequisitos.save()
                        print(f'---------------------->{index + 1}.- {becarequisitos}')

            except Exception as ex:
                transaction.set_rollback(True)
                msg = str(ex)
                msg = f'Ocurrio un error en detalle eror:{msg}'
                print(msg)


def actualizar_pagos():
    from sga.models import SolicitudPagoBeca
    from django.db.models import Sum
    try:
        pagos = SolicitudPagoBeca.objects.filter(periodo_id=119, status=True)
        for key, pago in enumerate(pagos):
            total_beneficiarios = pago.solicitudpagobecadetalle_set.filter(status=True).count()
            total_monto = pago.solicitudpagobecadetalle_set.filter(status=True).aggregate(valor=Sum('monto'))['valor']
            pago.cantidadbenef = total_beneficiarios
            pago.montopago = total_monto
            pago.save()
            print(f'{key + 1}.- {pago}')
    except Exception as ex:
        print(ex)


# actualizar_pagos()
def actualizar_pagos_a_45(periodo_id):
    from sga.models import SolicitudPagoBeca
    from django.db.models import Sum
    try:
        pagos = SolicitudPagoBeca.objects.filter(periodo_id=periodo_id, status=True)
        for key, pago in enumerate(pagos):
            # total_beneficiarios = pago.solicitudpagobecadetalle_set.filter(status=True).count()
            # pago.solicitudpagobecadetalle_set.update(monto=45.00)
            for detallepago in pago.solicitudpagobecadetalle_set.filter(status=True):
                detallepago.monto = 45.00
                detallepago.save()
                asignacion = detallepago.asignacion
                asignacion.montomensual = (45.00 / asignacion.cantidadmeses)
                asignacion.montobeneficio = 45.00
                asignacion.save()
            total_monto = pago.solicitudpagobecadetalle_set.filter(status=True).aggregate(valor=Sum('monto'))['valor']
            # pago.cantidadbenef = total_beneficiarios
            pago.montopago = total_monto
            pago.save()
            print(f'{key + 1}.- {pago}')
    except Exception as ex:
        print(ex)


# actualizar_pagos_a_45(119)
# actualizar_pagos_a_45(126)

def actualizar_datos_infoactualizada(periodo_id):
    from sga.models import BecaAsignacion
    from django.db.models import Sum
    try:
        becasasignacion = BecaAsignacion.objects.filter(solicitud__periodo_id=periodo_id, status=True)
        for key, beca in enumerate(becasasignacion):
            if beca.solicitud.cumple_todos_documentos_requeridos():
                beca.cargadocumento = True
                beca.save()
            print(f'{key + 1}.- {beca}')
    except Exception as ex:
        print(ex)


# actualizar_datos_infoactualizada(119)
# actualizar_datos_infoactualizada(126)

def actualizar_cuenta_bancarias_activapago(periodo_id):
    from sga.models import BecaAsignacion
    from django.db.models import Sum
    try:
        becasasignacion = BecaAsignacion.objects.filter(solicitud__periodo_id=periodo_id, status=True)
        for key, beca in enumerate(becasasignacion):
            persona = beca.solicitud.inscripcion.persona
            cuentabacaria = persona.cuentabancaria_becas()
            if cuentabacaria and not persona.cuentabancaria():
                cuentabacaria = cuentabacaria
                cuentabacaria.activapago = True
                cuentabacaria.save()
            print(f'{key + 1}.- {beca}, {cuentabacaria if cuentabacaria else "SIN CUENTA BANCARIA"}')
    except Exception as ex:
        print(ex)


# print('PERIODO 2S 2021')
# actualizar_cuenta_bancarias_activapago(119)
# print('PERIODO 1S 2022')
# actualizar_cuenta_bancarias_activapago(126)
def actualizar_actacompromiso_becasolicitud(periodo_id):
    from settings import DEBUG, SITE_STORAGE
    from sga.models import BecaAsignacion, BecaSolicitud
    from sga.funciones import elimina_tildes
    from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqr_generico
    from django.db.models import Sum
    becas_solicitudes = BecaSolicitud.objects.filter(periodo_id=periodo_id,
                                                     becaaceptada=2,
                                                     archivoactacompromiso__isnull=False,
                                                     status=True)
    for key, becasolicitud in enumerate(becas_solicitudes):
        with transaction.atomic():
            try:
                persona = becasolicitud.inscripcion.persona
                output_folder = ''
                aData = {}
                url_path = 'http://127.0.0.1:8000'
                if not DEBUG:
                    url_path = 'https://sga.unemi.edu.ec'
                aData['documentopersonal'] = documentopersonal = persona.personadocumentopersonal_set.filter(status=True).first()
                aData['cuentabancaria'] = cuentabancaria = cuentabancaria = persona.cuentabancaria_becas()
                aData['perfil'] = perfil = persona.mi_perfil()
                aData['deportista'] = deportista = persona.deportistapersona_set.filter(status=True).first()
                aData['isPersonaExterior'] = isPersonaExterior = persona.ecuatoriano_vive_exterior()
                aData['configuracionbecatipoperiodo'] = becatipoconfiguracion = becasolicitud.obtener_configuracionbecatipoperiodo()
                aData['matricula'] = matricula = becasolicitud.obtener_matricula()
                eInscripcion = becasolicitud.inscripcion
                ePeriodo = becasolicitud.periodo
                eUsuario = persona.usuario
                username = elimina_tildes(eUsuario.username)
                filename = f'acta_compromiso_{eInscripcion.id}_{ePeriodo.id}_{becasolicitud.id}'
                filenametemp = os.path.join(os.path.join(SITE_STORAGE, 'media', 'becas', 'temp', 'actas_compromisos', username, filename + '.pdf'))
                filenameqrtemp = os.path.join(os.path.join(SITE_STORAGE, 'media', 'becas', 'temp', 'actas_compromisos', username, 'qrcode', filename + '.png'))
                url_actafirmada = None
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'becas', 'actas_compromisos', username, ''))
                folder2 = os.path.join(os.path.join(SITE_STORAGE, 'media', 'becas', 'actas_compromisos', username, 'qrcode', ''))
                aData['aceptobeca'] = True
                aData['url_qr'] = rutaimg = folder2 + filename + '.png'
                aData['rutapdf'] = rutapdf = folder + filename + '.pdf'
                aData['url_pdf'] = url_pdf = f'{url_path}/media/becas/actas_compromisos/{username}/{filename}.pdf'
                if os.path.isfile(rutapdf):
                    os.remove(rutapdf)
                elif os.path.isfile(rutaimg):
                    os.remove(rutaimg)
                os.makedirs(folder, exist_ok=True)
                os.makedirs(folder2, exist_ok=True)
                firma = f'ACEPTADO POR: {eInscripcion.persona.__str__()}\nUSUARIO:{username}\nFECHA: {datetime.utcnow()}\nACEPTO EN: sga.unemi.edu.ec\nDOCUMENTO:{url_pdf}'
                url = pyqrcode.create(firma)
                imageqr = url.png(rutaimg, 16, '#000000')
                aData['version'] = datetime.now().strftime('%Y%m%d_%H%M%S')
                aData['image_qrcode'] = f'{url_path}/media/becas/actas_compromisos/{username}/qrcode/{filename}.png'
                aData['fechaactual'] = datetime.now()
                url_acta = f'becas/actas_compromisos/{username}/{filename}.pdf'
                rutapdf = folder + filename + '.pdf'
                request = {}
                valida, pdf, result = conviert_html_to_pdfsaveqr_generico(request, 'alu_becas/actacompromiso.html', {
                    'pagesize': 'A4',
                    'data': aData,

                }, folder, filename + '.pdf')
                if not valida:
                    raise NameError('Error al generar el pdf de acta de compromiso')
                montobeca = becatipoconfiguracion.becamonto
                meses = becatipoconfiguracion.becameses
                montomensual = becatipoconfiguracion.monto_x_mes()
                becasolicitud.montomensual = montomensual
                becasolicitud.meses = meses
                becasolicitud.montobeneficio = montobeca
                print(f'{key + 1}.- {becasolicitud}, {url_pdf}')
            except Exception as ex:
                print(ex)


# actualizar_actacompromiso_becasolicitud(119)

# crear_requisitos_becas_configuracion_x_periodo(periodo_id=119)
# crear_requisitos_becas_configuracion_x_periodo(periodo_id=126)
# #crear_requisitos_becas_configuracion_x_periodo()
# def corregir_incoveniente_becas_socioeconomico(periodoactual, periodoanterior):
#     from datetime import datetime, timedelta
#     from sga.models import PreInscripcionBeca, BecaTipo, Inscripcion, Malla
#     from sga.funciones import lista_gruposocioeconomico_beca, asignar_orden_portipo_beca
#     #excluir preinscriciones del este Periodo
#     ID_GRUPO_VULNERABLE = 18
#     EXCLUDES = []
#     preinscripciones = PreInscripcionBeca.objects.filter(periodo=periodoactual).exclude(becatipo_id=18)
#     preinscripciones_tipobeca = PreInscripcionBeca.objects.filter(periodo=periodoactual).exclude(becatipo_id=18)
#     preinscripcionesbeca_tipo = list(preinscripciones.filter(becatipo_id=ID_GRUPO_VULNERABLE).values_list('inscripcion__carrera_id', flat=True))
#     inscripciones_ex = Inscripcion.objects.filter(matricula__nivel__periodo=periodoactual, carrera_id__in=preinscripcionesbeca_tipo)
#     EXCLUDES = list(inscripciones_ex.values_list('id', flat=True))
#     EXCLUDES.extend(list(preinscripciones.values_list('inscripcion_id', flat=True)))
#     filtro_malla = None #Malla.objects.get(pk=219)
#     with transaction.atomic():
#         try:
#             grupo = []
#             for grupo_id in [4, 5]:
#                 grupo.extend(lista_gruposocioeconomico_beca(periodoactual=periodoactual, periodoanterior=periodoanterior, tipogrupo_id=grupo_id, excludes=EXCLUDES, limit=20, filter_malla=filtro_malla))
#             inscripciones_grupo = grupo
#             #print(len(inscripciones_grupo), inscripciones_grupo)
#             row = 1
#             dPreinscripcionbeca_actualizado = []
#             preinscripciones_economico = PreInscripcionBeca.objects.filter(becatipo_id=18, periodo=periodoactual)
#             malla_aux = None
#             count_preincripciones = 0
#             for key, inscripcion in enumerate(inscripciones_grupo):
#                 mimalla = inscripcion.mi_malla()
#                 if malla_aux != mimalla:
#                     malla_aux = mimalla
#                     preinscripciones_economico = preinscripciones_economico.filter(inscripcion__inscripcionmalla__malla=malla_aux).distinct().order_by('orden')
#                     count_preincripciones = preinscripciones_economico.count()
#                 if preinscripciones_economico.exists():
#                     if key < count_preincripciones:
#                         print('Actual: (%s, %s)'%(preinscripciones_economico[key], preinscripciones_economico[key].promedio), 'Reemplazo : (%s, %s)'%(inscripcion, inscripcion.promediototal))
#                         print(preinscripciones_economico[key])
#                         preinscripcion = preinscripciones_economico[key]
#                         preinscripcion.inscripcion = inscripcion
#                         preinscripcion.promedio = inscripcion.promediototal
#                         preinscripcion.save()
#                         print(preinscripcion)
#                     else:
#                         preinscripcion = PreInscripcionBeca.objects.filter(periodo=periodoactual, inscripcion=inscripcion).first()
#                         if preinscripcion is None:
#                             print('Nuevo Preinscripcion Beca', inscripcion)
#                             preinscripcion = PreInscripcionBeca(periodo=periodoactual,
#                                                                 inscripcion=inscripcion,
#                                                                 becatipo_id=ID_GRUPO_VULNERABLE,
#                                                                 promedio=inscripcion.promediototal,
#                                                                 fecha=datetime.now().date())
#                             preinscripcion.save()
#                             preinscripcion.generar_requistosbecas()
#
#                         else:
#                             print('Ya existe Preinscripcion con otro tipo de Beca', inscripcion, preinscripcion.becatipo)
#                 else:
#                     print('Nuevo Preinscripcion Beca Sin Malla', inscripcion)
#                     preinscripcion = PreInscripcionBeca(periodo=periodoactual,
#                                                         inscripcion=inscripcion,
#                                                         becatipo_id=ID_GRUPO_VULNERABLE,
#                                                         promedio=inscripcion.promediototal,
#                                                         fecha=datetime.now().date())
#                     preinscripcion.save()
#                     preinscripcion.generar_requistosbecas()
#
#             asignar_orden_portipo_beca(ID_GRUPO_VULNERABLE, periodoactual)
#         except Exception as ex:
#             transaction.set_rollback(True)
#             print(str(ex))
#
#
# def corregir_tipo_becas_preinscripciones(periodoactual, periodoanterior):
#     from sga.models import PreInscripcionBeca, BecaTipo, Inscripcion
#     from openpyxl import load_workbook
#
#     preinscripciones = PreInscripcionBeca.objects.filter(periodo=periodoactual, becatipo_id=19)
#     archivo_ = 'data_discapacitados_cambio_tipo'
#     url_archivo = "{}/media/{}.xlsx".format(SITE_STORAGE, archivo_)
#     wb = load_workbook(filename=url_archivo, read_only=True)
#     sheet = wb[wb.sheetnames[0]]
#     for row in range(2, sheet.max_row + 1):
#         perfilinscripcion_id = int(sheet.cell(row=row, column=1).value)
#         tipodiscapacidad_id = int(sheet.cell(row=row, column=4).value)
#         tipodiscapacidad = sheet.cell(row=row, column=5).value
#         preinscripcion = preinscripciones.filter(inscripcion__persona__perfilinscripcion__id=perfilinscripcion_id).first()
#         if preinscripcion is not None:
#             perfilinscripcion = preinscripcion.inscripcion.persona.perfilinscripcion_set.filter(status=True).first()
#             if perfilinscripcion is not None:
#                 if perfilinscripcion.tipodiscapacidad_id is None:
#                     perfilinscripcion.tipodiscapacidad_id = tipodiscapacidad_id
#                     perfilinscripcion.save()
#                     print(perfilinscripcion_id, tipodiscapacidad_id, tipodiscapacidad, preinscripcion)
#
# def asignar_becas_preinscripciones_etnias(periodoactual, periodoanterior):
#     from sga.models import PreInscripcionBeca, BecaTipo, Inscripcion, PerfilInscripcion
#     from openpyxl import load_workbook
#
#     preinscripciones = PreInscripcionBeca.objects.filter(periodo=periodoactual, becatipo_id=21)
#     archivo_ = 'data_becados_etnia_migracion'
#     url_archivo = "{}/media/{}.xlsx".format(SITE_STORAGE, archivo_)
#     wb = load_workbook(filename=url_archivo, read_only=True)
#     sheet = wb[wb.sheetnames[0]]
#     cont = 1
#     for row in range(2, sheet.max_row + 1):
#         perfilinscripcion_id = int(sheet.cell(row=row, column=1).value)
#         raza_id = int(sheet.cell(row=row, column=3).value)
#         raza = sheet.cell(row=row, column=4).value
#         preinscripcion = preinscripciones.filter(inscripcion__persona__perfilinscripcion__id=perfilinscripcion_id).first()
#         if preinscripcion is not None:
#             preinscripcion.raza_id = raza_id
#             preinscripcion.save()
#             print('%s.- PREINSCRIPCION: %s RAZA: %s' % (cont, preinscripcion, preinscripcion.raza))
#         else:
#             perfilinscripcion = PerfilInscripcion.objects.filter(id=perfilinscripcion_id).first()
#             if perfilinscripcion is not None:
#                 print('%s.- NO EXISTE UNA PREINSCRIPCIONBECA PARA EL PERFILINSCRIPCION  %s CON RAZA %s' % (cont, perfilinscripcion, raza))
#             else:
#                 print('%s.- NO EXISTE UNA PREINSCRIPCIONBECA PARA EL ID  %s CON RAZA %s' % (cont, perfilinscripcion_id, raza))
#         cont += 1
#
#
# def asignar_info_tipobeca_discapacitados_preinscripciones(periodoactual, periodoanterior):
#     from sga.models import PreInscripcionBeca, BecaTipo, Inscripcion, PerfilInscripcion
#     from openpyxl import load_workbook
#
#     preinscripciones = PreInscripcionBeca.objects.filter(periodo=periodoactual, becatipo_id=19)
#     archivo_ = 'data_becados_discapacitad_migracion'
#     url_archivo = "{}/media/{}.xlsx".format(SITE_STORAGE, archivo_)
#     wb = load_workbook(filename=url_archivo, read_only=True)
#     sheet = wb[wb.sheetnames[0]]
#     cont = 1
#     for row in range(2, sheet.max_row + 1):
#         perfilinscripcion_id = int(sheet.cell(row=row, column=1).value)
#         tipodiscapacidad_id = sheet.cell(row=row, column=4).value
#         tipodiscapacidad_id = int(tipodiscapacidad_id) if isinstance(tipodiscapacidad_id, int) else None
#         tipodiscapacidad = sheet.cell(row=row, column=5).value
#         porcientodiscapacidad = sheet.cell(row=row, column=6).value
#         carnetdiscapacidad = sheet.cell(row=row, column=7).value
#
#         preinscripcion = preinscripciones.filter(inscripcion__persona__perfilinscripcion__id=perfilinscripcion_id).first()
#         if preinscripcion is not None:
#             preinscripcion.tipodiscapacidad_id = tipodiscapacidad_id
#             preinscripcion.porcientodiscapacidad = porcientodiscapacidad
#             preinscripcion.carnetdiscapacidad = carnetdiscapacidad
#             preinscripcion.save()
#             print('%s.- PREINSCRIPCION: %s CON TIPO DISCAPACIDAD: %s (%s ,%s)' % (cont, preinscripcion, preinscripcion.tipodiscapacidad, preinscripcion.porcientodiscapacidad, preinscripcion.carnetdiscapacidad))
#         else:
#             perfilinscripcion = PerfilInscripcion.objects.filter(id=perfilinscripcion_id).first()
#             if perfilinscripcion is not None:
#                 print('%s.- NO EXISTE UNA PREINSCRIPCIONBECA PARA EL PERFILINSCRIPCION  %s CON TIPO DISCAPACIDAD %s' % (cont, perfilinscripcion, perfilinscripcion.tipodiscapacidad))
#             else:
#                 print('%s.- NO EXISTE UNA PREINSCRIPCIONBECA PARA EL ID  %s CON TIPO DISCAPACIDAD %s' % (cont, perfilinscripcion_id, tipodiscapacidad))
#         cont += 1
#
# def corregir_incoveniente_becas_socioeconomico_v2(periodoactual, periodoanterior):
#     from datetime import datetime, timedelta
#     from sga.models import PreInscripcionBeca, BecaTipo, Inscripcion, Malla
#     from sga.funciones import lista_gruposocioeconomico_beca, asignar_orden_portipo_beca
#     ID_GRUPO_VULNERABLE = 18
#     EXCLUDES = []
#     with transaction.atomic():
#         try:
#             preinscripcion_old = PreInscripcionBeca.objects.filter(periodo=periodoactual, becatipo_id=18)
#             print(preinscripcion_old)
#             print(preinscripcion_old.delete())
#             preinscripciones = PreInscripcionBeca.objects.filter(periodo=periodoactual)
#             EXCLUDES.extend(list(preinscripciones.values_list('inscripcion_id', flat=True)))
#             print('Exclude ', EXCLUDES, len(EXCLUDES))
#             filtro_malla = None
#             grupo = []
#             for grupo_id in [4, 5]:
#                 grupo.extend(lista_gruposocioeconomico_beca(periodoactual=periodoactual, periodoanterior=periodoanterior, tipogrupo_id=grupo_id, excludes=EXCLUDES, limit=20, filter_malla=filtro_malla))
#             inscripciones_grupo = grupo
#             for key, inscripcion in enumerate(inscripciones_grupo):
#                 preinscripcion = PreInscripcionBeca.objects.filter(inscripcion=inscripcion, periodo=periodoactual).first()
#                 if not preinscripcion:
#                     preinscripcion = PreInscripcionBeca(inscripcion=inscripcion,
#                                                         promedio=inscripcion.promediototal,
#                                                         becatipo=BecaTipo.objects.get(pk=ID_GRUPO_VULNERABLE),
#                                                         periodo=periodoactual,
#                                                         fecha=datetime.now().date())
#                     preinscripcion.save()
#                     preinscripcion.generar_requistosbecas()
#             asignar_orden_portipo_beca(ID_GRUPO_VULNERABLE, periodoactual)
#             preinscripciones_sin_requisitos = PreInscripcionBeca.objects.filter(periodo=periodoactual, preinscripcionbecarequisito__isnull=True)
#             for preinscripcionbeca in preinscripciones_sin_requisitos:
#                 preinscripcionbeca.generar_requistosbecas()
#         except Exception as ex:
#             transaction.set_rollback(True)
#             err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
#             mensaje_ex = f'{err} {ex.__str__()}'
#             print(mensaje_ex)
# periodoactual= Periodo.objects.get(pk=119)
# periodoanterior= Periodo.objects.get(pk=113)
# #corregir_tipo_becas_preinscripciones(periodoactual, periodoanterior)
# # print("""
# # °°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°
# # |                                                                                                                    |
# # |                  CORRECCIÓN PREINSCRIPCIÓN BECAS CON INSCONSISTENCIAS EN EL PROCESO (SOCIOECONOMICO)               |
# # |                                                                                                                    |
# # °°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°
# # """)
# # #corregir_incoveniente_becas_socioeconomico_v2(periodoactual, periodoanterior)
# # print("""
# # °°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°
# # |                                                                                                                    |
# # |                  CORRECCIÓN PREINSCRIPCIÓN BECAS CON INSCONSISTENCIAS EN EL PROCESO (ETNIAS)                       |
# # |                                                                                                                    |
# # °°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°
# # """)
# # #asignar_becas_preinscripciones_etnias(periodoactual, periodoanterior)
# # print("""
# # °°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°
# # |                                                                                                                    |
# # |                  CORRECCIÓN PREINSCRIPCIÓN BECAS CON INSCONSISTENCIAS EN EL PROCESO (DISCAPACITADO)                |
# # |                                                                                                                    |
# # °°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°
# # """)
# # #asignar_info_tipobeca_discapacitados_preinscripciones(periodoactual, periodoanterior)
#
#
# def copy_files_cne():
#     from openpyxl import load_workbook
#     from xlwt import Workbook
#     from sga.models import Coordinacion
#     coordinaciones = Coordinacion.objects.filter(status=True)
#     archivo_ = 'PLANTILLA_INSTITUCION_EDUCACION_SUPERIOR_MJRV_CNE_ELECCIONES__SECCIONALES_CPCCS_2023_FACULTADES'
#     url_archivo = "{}/media/{}.xlsx".format(your_djangoproject_home, archivo_)
#     wb = load_workbook(filename=url_archivo, read_only=True)
#     sheet = wb[wb.sheetnames[3]]
#     # for key, row in enumerate(sheet.iter_rows()):
#     #     if key == 22:
#     #         print(row, row[16].value)
#     # wb_new = Workbook(encoding='utf-8')
#     # cont = 1
#     # nombre_archivo = 'alumnos_discapacitados'
#     # ws_new = wb_new.add_sheet('PLANTILLA LISTADO')
#
#     coordinacion = None
#     carrera = None
#     carrera_aux = None
#     coordinacion_aux = None
#     lista = []
#     rows_temp = []
#     row_new = 21
#     ws_new = None
#     nombre_archivo = 'demo'
#     bandera = None
#     wb_new = None
#     for row in range(22, sheet.max_row + 1):
#         coordinacion = sheet.cell(row=row, column=20).value
#         carrera = sheet.cell(row=row, column=21).value
#         bandera = coordinacion_aux != coordinacion and bandera != None
#         if coordinacion_aux != coordinacion:
#             coordinacion_aux = coordinacion
#         if carrera_aux != carrera:
#             carrera_aux = carrera
#             if rows_temp:
#                 lista.append(rows_temp)
#                 print(rows_temp)
#             if bandera:
#                 print(f'Guardando Libro {nombre_archivo}')
#                 wb_new.save(nombre_archivo)
#             else:
#                 wb_new = Workbook(encoding='utf-8')
#                 row_new = 21
#                 nombre_archivo = f'UNIVERSIDAD ESTATAL DE MILAGRO, {coordinacion_aux}, CARRERA DE {carrera_aux}.xlsx'
#                 ws_new = wb_new.add_sheet('PLANTILLA LISTADO')
#                 bandera = False
#         if carrera_aux == carrera:
#             for col in range(1, sheet.max_column + 1):
#                 ws_new.write(row_new, col-1, sheet.cell(row=row_new, column=col).value)
#             row_new += 1
#         else:
#             bandera = True
#
#         # print(sheet.cell(row=row, column=20).value, sheet.cell(row=row, column=21).value)
#         #for col in range(1, sheet.max_column + 1):
#
#
# def all_prueba():
#     from django.db.models import Q, F, Value, Subquery, OuterRef, IntegerField, Deferrable
#     from django.db.models.aggregates import Count
#     from sga.models import Materia, Aula, HorarioExamen, HorarioExamenDetalle, Coordinacion, Sesion,Nivel, Malla, Paralelo, NivelMalla
#     from django.db.models.expressions import RawSQL
#
#     materia = Materia.objects.get(pk=52947)
#     horarioexamen = materia.horarioexamen_set.first()
#     horarioexamendetalle = horarioexamen.horarioexamendetalle_set.first()
#     sqlwhere = """((sga_horarioexamendetalle.horafin >= %s AND sga_horarioexamendetalle.horainicio <= %s)
#     			OR( %s  BETWEEN sga_horarioexamendetalle.horainicio  AND sga_horarioexamendetalle.horafin)
#     			OR ( %s  BETWEEN sga_horarioexamendetalle.horainicio  AND sga_horarioexamendetalle.horafin))"""
#
#
#
#
#
#
#     #print(materia.horarioexamen_set.filter(status=True).values_list('horarioexamendetalle__id', 'fecha',  'horarioexamendetalle__aula', 'detallemodelo','horarioexamendetalle__horainicio','horarioexamendetalle__horafin'))
#
#     # sqlwhere = """And ((sga_horarioexamendetalle.horafin >= '17:29:00' AND sga_horarioexamendetalle.horainicio <= '16:00:00')
# 	# 				OR( '16:00:00'  BETWEEN sga_horarioexamendetalle.horainicio  AND sga_horarioexamendetalle.horafin)
# 	# 				OR ( '17:29:00'  BETWEEN sga_horarioexamendetalle.horainicio  AND sga_horarioexamendetalle.horafin))"""
#     #
#     #
#     # sqlwhere = """((sga_horarioexamendetalle.horafin >= %s AND sga_horarioexamendetalle.horainicio <= %s)
# 	# 				OR( %s  BETWEEN sga_horarioexamendetalle.horainicio  AND sga_horarioexamendetalle.horafin)
# 	# 				OR ( %s  BETWEEN sga_horarioexamendetalle.horainicio  AND sga_horarioexamendetalle.horafin))"""
#     #
#     #
#     #
#     #
#     # verificador = HorarioExamenDetalle.objects.filter(
#     #                                                 horarioexamen__fecha=horarioexamendetalle.horarioexamen.fecha,
#     #                                                 status=True,
#     #                                                 aula=horarioexamendetalle.aula).extra(where=[sqlwhere], params=['17:29:00', '16:00:00', '16:00:00', '17:29:00']).exclude(pk=horarioexamendetalle.pk)
#
#     eCoordinacion = Coordinacion.objects.get(pk=4)
#     eSesion = Sesion.objects.get(pk=5)
#     eNiveles = Nivel.objects.filter(status=True, periodo_id=126, sesion=eSesion, nivellibrecoordinacion__coordinacion=eCoordinacion)
#     eMaterias = Materia.objects.filter(nivel__in=eNiveles, status=True)
#     eMallas = Malla.objects.filter(pk__in=eMaterias.values_list("asignaturamalla__malla_id", flat=True)).order_by('carrera__nombre')
#     eMalla = eMallas.first()
#     eNivelesMalla = NivelMalla.objects.filter(pk__in=eMaterias.values_list("asignaturamalla__nivelmalla_id", flat=True).filter(asignaturamalla__malla=eMalla)).distinct().order_by('orden')
#     eNivelMalla = eNivelesMalla.first()
#     eParalelos = Paralelo.objects.filter(pk__in=eMaterias.values_list("paralelomateria_id", flat=True).filter(asignaturamalla__malla=eMalla, asignaturamalla__nivelmalla=eNivelMalla)).distinct()
#     eParalelo = eParalelos.first()
#     eMaterias = eMaterias.filter(asignaturamalla__malla=eMalla, asignaturamalla__nivelmalla=eNivelMalla, paralelomateria=eParalelo)
#
#     sql = """
#             SELECT
#                 COUNT("sga_horarioexamendetalle"."id")
#             FROM "sga_horarioexamendetalle"
#                 INNER JOIN "sga_horarioexamen" ON ("sga_horarioexamendetalle"."horarioexamen_id" = "sga_horarioexamen"."id")
#             WHERE
#                 (
#                 "sga_horarioexamendetalle"."aula_id" = %s
#                 AND "sga_horarioexamen"."detallemodelo_id" = %s
#                 AND "sga_horarioexamen"."fecha" = %s
#                 AND "sga_horarioexamen"."status"
#                 AND "sga_horarioexamendetalle"."status"
#                 AND
#                     (((sga_horarioexamendetalle.horafin >= %s AND sga_horarioexamendetalle.horainicio <= %s)
#                                 OR( %s  BETWEEN sga_horarioexamendetalle.horainicio  AND sga_horarioexamendetalle.horafin)
#                                 OR ( %s  BETWEEN sga_horarioexamendetalle.horainicio  AND sga_horarioexamendetalle.horafin)))
#             AND NOT ("sga_horarioexamendetalle"."id" = %s)
#
#             """
#
#     resultado1 = eMaterias.annotate(conflicto_horario=RawSQL(sql, (OuterRef('horarioexamendetalle__aula_id'),
#                                                                    OuterRef('detallemodelo_id'),
#                                                                    OuterRef('fecha'),
#                                                                    OuterRef('horarioexamendetalle__horafin'),
#                                                                    OuterRef('horarioexamendetalle__horainicio'),
#                                                                    OuterRef('horarioexamendetalle__horainicio'),
#                                                                    OuterRef('horarioexamendetalle__horafin'),
#                                                                    OuterRef('horarioexamendetalle__id'),
#                                                                    ))).distinct()
#     #
#     # subquery = HorarioExamenDetalle.objects.filter(
#     #     Q(Q(horainicio__lte=OuterRef('horarioexamen__horarioexamendetalle__horafin'),
#     #         horafin__gte=OuterRef('horarioexamen__horarioexamendetalle__horainicio')) |
#     #         Q(horainicio__gte=OuterRef('horarioexamen__horarioexamendetalle__horainicio'), horafin__lt=OuterRef('horarioexamen__horarioexamendetalle__horainicio')) |
#     #         Q(horainicio__gte=OuterRef('horarioexamen__horarioexamendetalle__horafin'), horafin__lt=OuterRef('horarioexamen__horarioexamendetalle__horafin'))
#     #       ),
#     #     horarioexamen__fecha=OuterRef('horarioexamen__fecha'),
#     #     horarioexamen__status=OuterRef('horarioexamen__status'),
#     #     horarioexamen__detallemodelo=OuterRef('horarioexamen__detallemodelo'),
#     #     status=True,
#     #     aula=OuterRef('horarioexamen__horarioexamendetalle__aula')).exclude(pk=OuterRef('horarioexamen__horarioexamendetalle__id')).count()
#
#     #subquery = HorarioExamenDetalle.objects.filter(status=True).exclude(pk=OuterRef('horarioexamen__horarioexamendetalle__id'))
#     #resultado1 = eMaterias.annotate(conflicto_horario=Subquery(subquery.count()))
#     resultado = eMaterias.annotate(conflicto=Count('horarioexamen__horarioexamendetalle',
#                                                    filter=Q(Q(horarioexamen__horarioexamendetalle__horainicio__lte=F('horarioexamen__horarioexamendetalle__horafin'), horarioexamen__horarioexamendetalle__horafin__gte=F('horarioexamen__horarioexamendetalle__horainicio'))|
#                                                             Q(horarioexamen__horarioexamendetalle__horainicio__lte=F('horarioexamen__horarioexamendetalle__horainicio'), horarioexamen__horarioexamendetalle__horafin__gte=F('horarioexamen__horarioexamendetalle__horainicio'))|
#                                                             Q(horarioexamen__horarioexamendetalle__horainicio__lte=F('horarioexamen__horarioexamendetalle__horafin'), horarioexamen__horarioexamendetalle__horafin__gte=F('horarioexamen__horarioexamendetalle__horafin'))
#                                                             ) & Q(
#                                                             status=True,
#                                                             horarioexamen__detallemodelo=F('horarioexamen__detallemodelo'),
#                                                             horarioexamen__fecha=F('horarioexamen__fecha'),
#                                                             horarioexamen__status=True,
#                                                             horarioexamen__horarioexamendetalle__aula=F('horarioexamen__horarioexamendetalle__aula')), distinct=True, exclude=Q(horarioexamen__horarioexamendetalle__id=F('horarioexamen__horarioexamendetalle__id')))).values('conflicto', 'asignatura__nombre')
#
#
#
#
#     print(resultado)
#     #print(resultado1)
#     #print(horarioexamendetalle.conflicto_horarioexamen())

# print("""
# °°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°
# |                                                                                                                    |
# |                                               CLASES SINCRONICAS                                                  |
# |                                                                                                                    |
# °°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°
# """)
from sga.models import Clase, ClaseSincronica, Leccion, ClaseAsincronica, LeccionGrupo, MateriaAsignada, PracticaPreProfesional, AsistenciaLeccion, ParticipantePracticaPreProfesional


def consultar_clases_sincronica_sin_lecciones():
    clasessincronica = ClaseSincronica.objects.filter(status=True, clase__materia__nivel__periodo_id=126, lecciones__isnull=True, fechaforo__lt='2022-07-12')
    print('Cantidad Registros: ', clasessincronica.count())
    for classincronica in clasessincronica:
        leccion = Leccion.objects.filter(clase=classincronica.clase, fecha=classincronica.fechaforo)
        with transaction.atomic():
            try:
                if leccion:
                    print(classincronica, leccion.count(), leccion.first().lecciongrupo_set.all().exists(), leccion.first().status)
                else:
                    print(classincronica, 'SIN LECCION')
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                mensaje_ex = f'{err} {ex.__str__()}'
                print(mensaje_ex)


# consultar_clases_sincronica_sin_lecciones()

# print("""
# °°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°
# |                                                                                                                    |
# |                                               CLASES ASINCRONICAS                                                  |
# |                                                                                                                    |
# °°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°
# """)

def consultar_clases_asincronica_sin_lecciones():
    clasesasincronicas = ClaseAsincronica.objects.filter(status=True, lecciones__isnull=True, clase__materia__nivel__periodo_id=126, fechaforo__lt='2022-07-12').distinct()
    print('Cantidad Registros: ', clasesasincronicas.count())
    for clasesasincronica in clasesasincronicas:
        leccion = Leccion.objects.filter(clase=clasesasincronica.clase, fecha=clasesasincronica.fechaforo)
        with transaction.atomic():
            try:
                if leccion:
                    print(clasesasincronica.status, clasesasincronica, leccion.count(), leccion.first().lecciongrupo_set.all().exists(), leccion.first().status)
                else:
                    print(clasesasincronica.status, clasesasincronica, 'SIN LECCION')
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {} {} {}'.format(clasesasincronica.id, clasesasincronica, sys.exc_info()[-1].tb_lineno)
                mensaje_ex = f'{err} {ex.__str__()}'
                print(mensaje_ex)


# consultar_clases_asincronica_sin_lecciones()

def correccion_lecciones():
    lecciones = Leccion.objects.filter(status=False, fecha__lt='2022-07-12', )
    ePeriodoAcademia = Periodo.objects.get(pk=126)
    with transaction.atomic():
        try:
            for index, leccion in enumerate(lecciones):
                # if leccion.all().exists():
                #    print(leccion, leccion.lecciongrupo_set.all())

                lecciongrupo = leccion.lecciongrupo_set.all()
                clasesincronica = leccion.clasesincronica_set.all()
                claseasincronica = leccion.claseasincronica_set.all()
                if lecciongrupo.exists() == False and clasesincronica.exists() == False and claseasincronica.exists() == False:
                    print(index + 1, leccion, 'Borrar Leccion')
                    # leccion.delete()
                if lecciongrupo and (clasesincronica or claseasincronica):
                    leccion.status = True
                    leccion.save()
                elif not lecciongrupo and (clasesincronica or claseasincronica):
                    lecciongrupo = LeccionGrupo(profesor=leccion.clase.profesor,
                                                turno=leccion.clase.turno,
                                                aula=leccion.clase.aula,
                                                dia=leccion.clase.dia,
                                                fecha=leccion.fecha,
                                                horaentrada=leccion.clase.turno.comienza,
                                                abierta=True,
                                                solicitada=False,
                                                contenido='SIN CONTENIDO',
                                                estrategiasmetodologicas='SIN CONTENIDO',
                                                observaciones='SIN OBSERVACIONES',
                                                ipingreso='',
                                                ipexterna='')
                    lecciongrupo.save()
                    lecciongrupo.lecciones.add(leccion)
                    claseprincipal = leccion.clase
                    materia = leccion.clase.materia
                    practicapreprofesional = None
                    asignados = None
                    clases = claseprincipal.turno.horario_profesor_actual_horario(claseprincipal.dia, claseprincipal.profesor, ePeriodoAcademia, False, False)
                    for clase in clases:
                        if clase.tipoprofesor.id in [2, 13] and clase.tipohorario in [1, 2, 8]:
                            if clase.grupoprofesor:
                                if clase.grupoprofesor.paralelopractica:
                                    # grupoprofesor_id = clase.grupoprofesor.id
                                    if clase.grupoprofesor.listado_inscritos_grupos_practicas().exists():
                                        listado_alumnos_practica = clase.grupoprofesor.listado_inscritos_grupos_practicas()
                                        if ePeriodoAcademia.valida_asistencia_pago:
                                            asignados = MateriaAsignada.objects.filter(pk__in=listado_alumnos_practica.values_list('materiaasignada_id', flat=True), matricula__estado_matricula__in=[2, 3]).distinct()
                                        else:
                                            asignados = MateriaAsignada.objects.filter(pk__in=listado_alumnos_practica.values_list('materiaasignada_id', flat=True)).distinct()
                                        if leccion.leccion_es_practica_salud():
                                            if leccion.fecha_clase_verbose():
                                                lecciongrupo.fecha = leccion.fecha_clase_verbose()
                                                lecciongrupo.horaentrada = leccion.clase.turno.comienza
                                                lecciongrupo.horasalida = leccion.clase.turno.termina
                                                lecciongrupo.save()
                                                leccion.fecha = lecciongrupo.fecha
                                                leccion.horaentrada = lecciongrupo.horaentrada
                                                leccion.horasalida = lecciongrupo.horasalida
                                                leccion.status = True
                                                # leccion.usuario_creacion_id = persona.usuario.id
                                                leccion.save()
                                            practicapreprofesional = PracticaPreProfesional.objects.filter(materia=materia,
                                                                                                           profesor=clase.grupoprofesor.profesormateria.profesor,
                                                                                                           horas=int(clase.turno.horas),
                                                                                                           fecha=leccion.fecha_clase_verbose() if leccion.fecha_clase_verbose() else leccion.fecha,
                                                                                                           grupopractica=clase.grupoprofesor,
                                                                                                           leccion=leccion)
                                            if practicapreprofesional.exists():
                                                practicapreprofesional = PracticaPreProfesional(materia=materia,
                                                                                                profesor=clase.grupoprofesor.profesormateria.profesor,
                                                                                                lugar=u"SIN LUGAR DE PRÁCTICA",
                                                                                                horas=int(clase.turno.horas),
                                                                                                fecha=leccion.fecha_clase_verbose() if leccion.fecha_clase_verbose() else leccion.fecha,
                                                                                                objetivo=u'SIN OBJETIVO',
                                                                                                cerrado=False,
                                                                                                grupopractica=clase.grupoprofesor,
                                                                                                leccion=leccion)
                                                practicapreprofesional.save()
                        else:
                            asignados = materia.asignados_a_esta_materia()

                        for materiaasignada in asignados:
                            asistencialeccion = AsistenciaLeccion.objects.filter(leccion=leccion, materiaasignada=materiaasignada)
                            if not asistencialeccion.exists():
                                asistencialeccion = AsistenciaLeccion(leccion=leccion,
                                                                      materiaasignada=materiaasignada,
                                                                      asistio=True,
                                                                      virtual=False,
                                                                      virtual_fecha=None,
                                                                      virtual_hora=None,
                                                                      ip_private=None,
                                                                      ip_public=None,
                                                                      browser=None,
                                                                      ops=None,
                                                                      screen_size=None,
                                                                      )
                                asistencialeccion.save()
                                # if variable_valor('ACTUALIZA_ASISTENCIA'):
                                #     if not asistencialeccion.materiaasignada.sinasistencia:
                                #         ActualizaAsistencia(asistencialeccion.materiaasignada.id)
                                if practicapreprofesional:
                                    participantepractica = ParticipantePracticaPreProfesional.objects.filter(practica=practicapreprofesional,
                                                                                                             materiaasignada=materiaasignada,
                                                                                                             asistencialeccion=asistencialeccion)
                                    if not participantepractica.exists():
                                        participantepractica = ParticipantePracticaPreProfesional(practica=practicapreprofesional,
                                                                                                  materiaasignada=materiaasignada,
                                                                                                  nota=0,
                                                                                                  asistencia=asistencialeccion.asistio,
                                                                                                  observacion='',
                                                                                                  asistencialeccion=asistencialeccion)
                                        participantepractica.save()
                    leccion.status = True
                    leccion.save()
                    print(index + 1, leccion, 'Creado Correctamente')

                elif lecciongrupo:
                    leccion.status = True
                    leccion.save()
        except Exception as ex:
            transaction.set_rollback(True)
            err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
            mensaje_ex = f'{err} {ex.__str__()}'
            print(mensaje_ex)


def arreglar_leccion_sin_asistencia():
    lecciones = Leccion.objects.filter(asistencialeccion__isnull=True, fecha__gte='2022-05-29', fecha__lt='2022-07-12', lecciongrupo__isnull=False).distinct()
    ePeriodoAcademia = Periodo.objects.get(pk=126)
    with transaction.atomic():
        try:
            for index, leccion in enumerate(lecciones):
                lecciongrupo = leccion.lecciongrupo_set.all().first()
                claseprincipal = leccion.clase
                materia = leccion.clase.materia
                practicapreprofesional = None
                asignados = None
                if claseprincipal.profesor:
                    clase = claseprincipal
                    if clase.tipoprofesor.id in [2, 13] and clase.tipohorario in [1, 2, 8]:
                        if clase.grupoprofesor:
                            if clase.grupoprofesor.paralelopractica:
                                # grupoprofesor_id = clase.grupoprofesor.id
                                if clase.grupoprofesor.listado_inscritos_grupos_practicas().exists():
                                    listado_alumnos_practica = clase.grupoprofesor.listado_inscritos_grupos_practicas()
                                    if ePeriodoAcademia.valida_asistencia_pago:
                                        asignados = MateriaAsignada.objects.filter(pk__in=listado_alumnos_practica.values_list('materiaasignada_id', flat=True), matricula__estado_matricula__in=[2, 3]).distinct()
                                    else:
                                        asignados = MateriaAsignada.objects.filter(pk__in=listado_alumnos_practica.values_list('materiaasignada_id', flat=True)).distinct()
                                    if leccion.leccion_es_practica_salud():
                                        if leccion.fecha_clase_verbose():
                                            lecciongrupo.fecha = leccion.fecha_clase_verbose()
                                            lecciongrupo.horaentrada = leccion.clase.turno.comienza
                                            lecciongrupo.horasalida = leccion.clase.turno.termina
                                            lecciongrupo.save()
                                            leccion.fecha = lecciongrupo.fecha
                                            leccion.horaentrada = lecciongrupo.horaentrada
                                            leccion.horasalida = lecciongrupo.horasalida
                                            leccion.status = True
                                            # leccion.usuario_creacion_id = persona.usuario.id
                                            leccion.save()
                                        practicapreprofesional = PracticaPreProfesional.objects.filter(materia=materia,
                                                                                                       profesor=clase.grupoprofesor.profesormateria.profesor,
                                                                                                       horas=int(clase.turno.horas),
                                                                                                       fecha=leccion.fecha_clase_verbose() if leccion.fecha_clase_verbose() else leccion.fecha,
                                                                                                       grupopractica=clase.grupoprofesor,
                                                                                                       leccion=leccion)
                                        if practicapreprofesional.exists():
                                            practicapreprofesional = PracticaPreProfesional(materia=materia,
                                                                                            profesor=clase.grupoprofesor.profesormateria.profesor,
                                                                                            lugar=u"SIN LUGAR DE PRÁCTICA",
                                                                                            horas=int(clase.turno.horas),
                                                                                            fecha=leccion.fecha_clase_verbose() if leccion.fecha_clase_verbose() else leccion.fecha,
                                                                                            objetivo=u'SIN OBJETIVO',
                                                                                            cerrado=False,
                                                                                            grupopractica=clase.grupoprofesor,
                                                                                            leccion=leccion)
                                            practicapreprofesional.save()
                    else:
                        asignados = materia.asignados_a_esta_materia()

                    for materiaasignada in asignados:
                        asistencialeccion = AsistenciaLeccion.objects.filter(leccion=leccion, materiaasignada=materiaasignada)
                        if not asistencialeccion.exists():
                            asistencialeccion = AsistenciaLeccion(leccion=leccion,
                                                                  materiaasignada=materiaasignada,
                                                                  asistio=True,
                                                                  virtual=False,
                                                                  virtual_fecha=None,
                                                                  virtual_hora=None,
                                                                  ip_private=None,
                                                                  ip_public=None,
                                                                  browser=None,
                                                                  ops=None,
                                                                  screen_size=None,
                                                                  )
                            asistencialeccion.save()
                            # if variable_valor('ACTUALIZA_ASISTENCIA'):
                            #     if not asistencialeccion.materiaasignada.sinasistencia:
                            #         ActualizaAsistencia(asistencialeccion.materiaasignada.id)
                            if practicapreprofesional:
                                participantepractica = ParticipantePracticaPreProfesional.objects.filter(practica=practicapreprofesional,
                                                                                                         materiaasignada=materiaasignada,
                                                                                                         asistencialeccion=asistencialeccion)
                                if not participantepractica.exists():
                                    participantepractica = ParticipantePracticaPreProfesional(practica=practicapreprofesional,
                                                                                              materiaasignada=materiaasignada,
                                                                                              nota=0,
                                                                                              asistencia=asistencialeccion.asistio,
                                                                                              observacion='',
                                                                                              asistencialeccion=asistencialeccion)
                                    participantepractica.save()
                leccion.status = True
                leccion.save()
                print(index + 1, leccion, 'Creado Correctamente')
            else:
                print(index + 1, leccion, 'Leccion sin Profesor')
        except Exception as ex:
            transaction.set_rollback(True)
            err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
            mensaje_ex = f'{err} {ex.__str__()}'
            print(mensaje_ex)


def agregar_inscripciones_a_participantes_ferias():
    from feria.models import ParticipanteFeria
    participantes = ParticipanteFeria.objects.all()
    print('total de registros', participantes.count())
    for index, participante in enumerate(participantes):
        if participante.matricula:
            participante.inscripcion = participante.matricula.inscripcion
            participante.save()
            print(f'{index + 1}.- Matricula: {participante.matricula} Inscripcion: {participante.inscripcion}')


def generar_qr_logo():
    # import modules
    import qrcode
    import qrcode.image.svg
    from PIL import Image

    # taking image which user wants
    # in the QR code center
    Logo_link = "{}/static/{}".format(SITE_STORAGE, 'logosga_qr.jpg')

    logo = Image.open(Logo_link)

    # taking base width
    basewidth = 100

    # adjust image size
    wpercent = (basewidth / float(logo.size[0]))
    hsize = int((float(logo.size[1]) * float(wpercent)))
    logo = logo.resize((basewidth, hsize), Image.ANTIALIAS)
    QRcode = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H
    )

    # taking url or text
    url = 'https://www.geeksforgeeks.org/'

    # addingg URL or text to QRcode
    QRcode.add_data(url)

    # generating QR code
    QRcode.make()

    # taking color name from user
    QRcolor = '#1c3247'

    # adding color to QR code
    QRimg = QRcode.make_image(fill_color=QRcolor, back_color="white").convert('RGB')

    # set size of QR code
    pos = ((QRimg.size[0] - logo.size[0]) // 2,
           (QRimg.size[1] - logo.size[1]) // 2)
    QRimg.paste(logo, pos)

    # save the QR code generated
    QRimg.save('gfg_QR.png')

    print('QR code generated!')


def genr():
    import qrcode
    import qrcode.image.svg
    from PIL import Image
    Logo_link = 'logo_SGA.png'

    logo = Image.open(Logo_link)
    basewidth = 100

    # adjust image size
    wpercent = (basewidth / float(logo.size[0]))
    hsize = int((float(logo.size[1]) * float(wpercent)))
    logo = logo.resize((basewidth, hsize), Image.ANTIALIAS)
    # definir un método para elegir qué método de fábrica utilizar
    # possible values 'basic' 'fragment' 'path'

    method = "basic"

    data = "Algún texto que desea almacenar en el código qr"

    if method == 'basic':
        # Fábrica simple, solo un conjunto de rectas.
        factory = qrcode.image.svg.SvgImage
    elif method == 'fragment':
        # Fábrica de fragmentos (también solo un conjunto de rectos)
        factory = qrcode.image.svg.SvgFragmentImage
    elif method == 'path':
        # Fábrica de ruta combinada, corrige los espacios en blanco que pueden ocurrir al hacer zoom
        factory = qrcode.image.svg.SvgPathImage

    # taking image which user wants
    # in the QR code center
    Logo_link = 'logo_SGA.png'

    logo = Image.open(Logo_link)

    # taking base width
    basewidth = 100

    # adjust image size
    wpercent = (basewidth / float(logo.size[0]))
    hsize = int((float(logo.size[1]) * float(wpercent)))
    logo = logo.resize((basewidth, hsize), Image.ANTIALIAS)

    QRcode = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        image_factory=factory
    )
    # taking url or text
    url = 'https://www.geeksforgeeks.org/'

    # addingg URL or text to QRcode
    QRcode.add_data(url)

    # generating QR code
    QRcode.make()
    QRimg = QRcode.make_image().convert('RGB')
    pos = ((QRimg.size[0] - logo.size[0]) // 2,
           (QRimg.size[1] - logo.size[1]) // 2)
    QRimg.paste(logo, pos)

    # save the QR code generated
    QRimg.save('EjemploQR.svg')

    print('QR code generated!')

    # Establecer datos en qrcode
    img = qrcode.make(data, image_factory=factory)

    # Guarde el archivo svg en algún lugar
    img.save("qrcode.svg")


# generar_qr_logo()
# genr()
# agregar_inscripciones_a_participantes_ferias()
# arreglar_leccion_sin_asistencia()
# all_prueba()
# copy_files_cne()


def correccion_solicitud_pagos_doble_triples(periodo_id):
    from django.db.models import Count, Q
    from sga.models import BecaAsignacion
    from django.db.models import Sum
    try:
        becasasignacion = BecaAsignacion.objects.filter(solicitud__periodo_id=periodo_id,
                                                        status=True).annotate(cantidad_solicitud=Count('solicitudpagobecadetalle__id', filter=Q(solicitudpagobecadetalle__status=True))).filter(cantidad_solicitud__gt=1)

        for key, beca in enumerate(becasasignacion):
            persona = beca.solicitud.inscripcion.persona
            primerasolicitud = beca.solicitudpagobecadetalle_set.filter(status=True).first()
            solcitudes_extras = beca.solicitudpagobecadetalle_set.filter(status=True).exclude(pk=primerasolicitud.id)
            tipoasignacion = primerasolicitud.tipoasignacion
            becatipo = primerasolicitud.becatipo
            becas = BecaAsignacion.objects.filter(status=True, solicitud__periodo_id=periodo_id,
                                                  solicitud__becatipo_id=becatipo,
                                                  solicitudpagobecadetalle__asignacion__isnull=True,
                                                  tipo=tipoasignacion).exclude(solicitudpagobecadetalle__isnull=False).distint()
            if becas:
                if tipoasignacion == 1:
                    becas = becas.filter(  # fecha_modificacion__range=(desde, hasta),
                        solicitud__inscripcion__persona__personadocumentopersonal__estadocedula=2,
                        # solicitud__inscripcion__persona__personadocumentopersonal__estadopapeleta=2,
                        # solicitud__inscripcion__persona__personadocumentopersonal__estadocedularepresentantesol=2,
                        # solicitud__inscripcion__persona__personadocumentopersonal__estadopapeletarepresentantesol=2,
                        solicitud__inscripcion__persona__cuentabancariapersona__status=True,
                        solicitud__inscripcion__persona__cuentabancariapersona__estadorevision__in=[1, 2],
                        solicitud__archivoactacompromiso__isnull=False).distinct()
                    idbs = [beca.pk for beca in becas if beca.solicitud.cumple_todos_documentos_requeridos_aprobados()]
                    becas = becas.filter(id__in=idbs)
            print(f'La beca de {beca}  tiene {beca.cantidad_solicitud}')
            print('primera solicitud', primerasolicitud.id)
            print('solicitud adicionales', solcitudes_extras.values_list('id', flat=True))

            # print(f'{key + 1}.- {beca},')
    except Exception as ex:
        print(ex)


# correccion_solicitud_pagos_doble_triples(119)
# crear_requisitos_becas_configuracion_x_periodo(periodo_id=153)
# def liberar__cache_de_becados(periodo=153):
#     ePeriodo = Periodo.objects.get(pk=periodo)
#     solicitudes = ePeriodo.becasolicitud_set.filter(status=True)
#     for key, solicitud in enumerate(solicitudes):
#         solicitud.delete_cache()
#         solicitud.delete_documentacion_cache()
#         print(f'{key+1} {solicitud} liberado')

# liberar__cache_de_becados(153)


# Estudf
def justificar_solicitudes_asistencias_pendientes(periodo_id, dev=True):
    from sga.models import JustificacionAusenciaAsistenciaLeccion, AsistenciaLeccion, SolicitudJustificacionAsistencia, DetalleMateriaJustificacionAsistencia, JustificacionAsistencia, DetalleSolicitudJustificacionAsistencia
    solicitudes = SolicitudJustificacionAsistencia.objects.filter(estadosolicitud=1, status=True, matricula__nivel__periodo_id=periodo_id)
    for key_sol, solicitud in enumerate(solicitudes):
        if solicitud.extendida:
            print(f'{key_sol + 1}.- {solicitud.matricula} {solicitud.fechainicioreposo} {solicitud.fechafinreposo} Extendida')
            eAsistenciasLecciones = AsistenciaLeccion.objects.filter(
                materiaasignada__matricula=solicitud.matricula,
                leccion__fecha__range=[solicitud.fechainicioreposo, solicitud.fechafinreposo],
                asistio=False
            )
            for key_asis, eAsistenciaLeccion in enumerate(eAsistenciasLecciones):
                eMateriaAsignada = eAsistenciaLeccion.materiaasignada
                if not eAsistenciaLeccion.justificacionausenciaasistencialeccion_set.filter(status=True).values('id').exists():
                    hora = f'[{eAsistenciaLeccion.leccion.horaentrada.strftime("%H:%M")} - { eAsistenciaLeccion.leccion.horasalida.strftime("%H:%M")  if eAsistenciaLeccion.leccion.horasalida else "Sin definir"}]'
                    print(f'----> {key_asis + 1}.- {eMateriaAsignada.materia}  {eAsistenciaLeccion.leccion.fecha.strftime("%d-%m-%Y")} {hora} ---> JUSTIFICADA')
                    eJustificacionAusenciaAsistenciaLeccion = JustificacionAusenciaAsistenciaLeccion(
                        asistencialeccion=eAsistenciaLeccion,
                        porcientojustificado=PORCIENTO_RECUPERACION_FALTAS,
                        motivo=f'SE JUSTIFICÓ POR SOLICITUD {solicitud.id} POR CASO DE {solicitud.casojustificacion}',
                        fecha=solicitud.fechasolicitud,
                        persona_id=1
                    )
                    eJustificacionAusenciaAsistenciaLeccion.save()
                    eAsistenciaLeccion.asistenciajustificada = True
                    eAsistenciaLeccion.asistio = True
                    eAsistenciaLeccion.save()
                eMateriaAsignada.save(actualiza=True)
                eMateriaAsignada.actualiza_estado()
            if eAsistenciasLecciones.__len__() > 0:
                solicitud.estadosolicitud = 2
                solicitud.save()
        else:
            print(f'{key_sol + 1}.- {solicitud.matricula} {solicitud.fechainicioreposo} {solicitud.fechafinreposo} NO Extendida')
            detallesmateriajustificacion =DetalleMateriaJustificacionAsistencia.objects.filter(materiajustificacion__solicitudjustificacion=solicitud, status=True)
            for materiajustificacion in solicitud.justificacion_materias():
                justifico_materia = False
                for key_dma, detalle_materia in enumerate(materiajustificacion.detalle_materia()):
                    justifico_hora = False
                    if detalle_materia in detallesmateriajustificacion:
                        asistencialeccion = detalle_materia.asistencialeccion
                        asistencialeccion.asistenciajustificada = True
                        asistencialeccion.asistio = True
                        asistencialeccion.save()
                        justifico_hora = True
                        justifico_materia = True
                        print(f'---------> {key_dma + 1}.- {detalle_materia.materiajustificacion.materiaasignada.materia} {detalle_materia} --> JUSTIFICADA')
                    detalle = JustificacionAsistencia(detallemateriajustificacion=detalle_materia, fechaajustificacion=datetime.now(), estadojustificado=justifico_hora)
                    detalle.save()
                if justifico_materia:
                    materiajustificacion.materiaasignada.save(actualiza=True)
            solicitud.estadosolicitud=2
            solicitud.save()

#justificar_solicitudes_asistencias_pendientes(153)


def genenerar_registros_inscripciones_record_nivelmalla():
    from sga.models import Inscripcion
    inscripciones = Inscripcion.objects.filter(status=True,
                                               recordacademico__status=True,
                                               recordacademico__aprobada=True,
                                               coordinacion_id__in=[1, 2, 3, 4, 5],
                                               recordacademico__validapromedio=True,
                                               recordacademico__valida=True,
                                               perfilusuario__status=True,
                                               perfilusuario__visible=True,
                                               perfilusuario__inscripcionprincipal=True,
                                               matricula__nivel__periodo_id__in=[153,177],
                                               matricula__status=True,
                                               matricula__retiradomatricula=False
                                               ).distinct()
    print("Cantidad Estudiantes: ", inscripciones.__len__())
    for key, inscripcion in enumerate(inscripciones):
        with transaction.atomic(using='default'):
            try:
                print(f"{key+1}.-  Estudiante: {inscripcion}\n")
                inscripcion.crear_actualizar_inscripcion_recordacademico_nivelmalla()
            except Exception as ex:
                transaction.set_rollback(True)
                msg = str(ex)
                print(f"{key+1}.- Estudiante: {inscripcion}", msg)



def corregir_matriculas_retiradas_cantidad_asignaturas():
    from sga.models import Matricula, Periodo
    from django.db.models import Q, Count, F
    periodos = Periodo.objects.all()
    for periodo in periodos:
        matriculas = Matricula.objects.filter(status=True,
                                              retiradomatricula=True,
                                              nivel__periodo=periodo).annotate(
                                                    total_asignatura_matriculadas=Count('materiaasignada__id', filter=Q(materiaasignada__status=True)),
                                                    total_asignatura_retiradas=Count('materiaasignada__id', filter=Q(materiaasignada__status=True, materiaasignada__retiramateria=True)),
        ).filter(total_asignatura_matriculadas=0, total_asignatura_retiradas=0)

        print(f"Cantidad: {matriculas.__len__()}")
        for key, matricula in enumerate(matriculas):
            print(f"{key + 1}.- {matricula} , {matricula.total_asignatura_matriculadas} del periodo -> {periodo}")
            matricula.retiradomatricula = False
            matricula.save()



corregir_matriculas_retiradas_cantidad_asignaturas()