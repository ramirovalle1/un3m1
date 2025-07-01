# -*- coding: UTF-8 -*-
import unicodedata
import subprocess
import json
import os
import io
import xlsxwriter
import random
from _decimal import Context
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import chain
from builtins import float

import pyqrcode
import xlwt
from django.contrib.auth.decorators import login_required
from django.db.models.aggregates import Sum
from django.forms import model_to_dict
from django.template.context import Context
from django.template.loader import get_template
from django.contrib.contenttypes.models import ContentType
from certi.models import Certificado, CertificadoAsistenteCertificadora, CertificadoUnidadCertificadora
from sagest.models import DistributivoPersona
from sga.funciones_templatepdf import listadovalidarequisitos
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from decorators import secure_module, last_access
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from xlwt import *
from settings import MODULO_INGLES_ID, POSGRADO_EDUCACION_ID, \
    MODULOS_COMPUTACION_ID, ADMISION_ID, PROYECTOS_TITULACION_ID, CUPO_POR_ALTERNATIVATITULACION, NOTA_ESTADO_APROBADO, \
    ESTADO_GESTACION, JR_USEROUTPUT_FOLDER, MEDIA_URL, SITE_STORAGE, JR_JAVA_COMMAND, JR_RUN, DATABASES, \
    SUBREPOTRS_FOLDER, MEDIA_ROOT, DEBUG, STATIC_URL, STATIC_ROOT
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import log, MiPaginador, generar_nombre, null_to_decimal, null_to_numeric, convertir_fecha, \
    generar_codigo
from sga.models import Carrera, Coordinacion, PeriodoGrupoTitulacion, GrupoTitulacion, AlternativaTitulacion, \
    HistorialMigracionMatriculaTitulacion, MatriculaRequisitosTitulacion, ValidacionRequisitosTitulacion, \
    ObservacionRequisitosTitulacion, ESTADOS_REQUISITOS_TITULACION, Malla, RequisitoSustentar, Inscripcion, \
    AsignaturaMalla, NivelMalla, EjeFormativo, TIPO_CELULAR, NivelTitulacion, Titulacion, Persona, BecaPersona, \
    BecaAsignacion, DeportistaPersona, MigrantePersona, ArtistaPersona, PracticasPreprofesionalesInscripcion, \
    ModuloMalla, ParticipantesMatrices, CertificadoRequisitosTitulacion, Reporte, LogReporteDescarga, Periodo, \
    CoordinadorCarrera, FirmaPersona, Materia, MateriaTitulacion, MateriaAsignada, MatriculaTitulacion
from sagest.models import Rubro, Pago, TipoOtroRubro, SesionCaja, Factura, RubroNotaDebito, \
    IvaAplicado, PagoLiquidacion, PagoCheque, PagoTransferenciaDeposito, PagoTarjeta, PagoCuentaporCobrar, \
    PagoDineroElectronico, null_to_decimal, ReciboCaja, CapEventoPeriodoIpec
from sga.reportes import elimina_tildes, transform_jasperstarter

from sga.tasks import send_html_mail
from socioecon.models import FichaSocioeconomicaINEC
from sga.templatetags.sga_extras import encrypt

unicode = str

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'LoadCarrerasByCoordinacion':
            try:
                idc = int(request.POST['idc']) if request.POST['idc'] else 0
                if idc == 0:
                    raise NameError(u'No se encontro datos que mostrar')

                carreras = Coordinacion.objects.get(pk=idc).carreras()
                eCarreras = []
                for carrera in carreras:
                    malla = Malla.objects.filter(carrera=carrera, status=True, vigente=True).order_by('-inicio')[0]
                    eCarreras.append({"id": carrera.id, "text": u"%s [%s]" % (carrera.nombre, str(malla.inicio_anno()))})

                return JsonResponse({"result": "ok", "eCarreras": eCarreras})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % ex})

        if action == 'LoadDataTable':
            try:
                post = request.POST
                idc = int(request.POST['idc']) if request.POST['idc'] else 0
                idp = int(request.POST['idp']) if request.POST['idp'] else 0
                ide = int(request.POST['ide']) if request.POST['ide'] else 0
                txt_filter = request.POST['sSearch'] if request.POST['sSearch'] else ''
                limit = int(request.POST['iDisplayLength']) if request.POST['iDisplayLength'] else 25
                offset = int(request.POST['iDisplayStart']) if request.POST['iDisplayStart'] else 0
                aaData = []
                tCount = 0

                if idc == 0 or idp == 0:
                    raise NameError(u"Error al cargar los datos.")
                    #return JsonResponse({"result": "bad", "mensaje": u""})

                periodo_titulacion = PeriodoGrupoTitulacion.objects.get(pk=idp)
                carrera = Carrera.objects.get(pk=idc)
                matriculas = MatriculaRequisitosTitulacion.objects.filter(matricula__alternativa__carrera=carrera, matricula__alternativa__grupotitulacion__periodogrupo=periodo_titulacion)
                if not ide == 0:
                    matriculas = matriculas.filter(estado_usuario=ide)
                isView = 1
                if not persona.usuario.is_staff:
                    matriculas = matriculas.filter(status=True)
                    isView = 0

                if txt_filter:
                    matriculas = matriculas.filter(Q(inscripcion__persona__nombres__icontains=txt_filter) |
                                                   Q(inscripcion__persona__apellido1__icontains=txt_filter) |
                                                   Q(inscripcion__persona__apellido2__icontains=txt_filter) |
                                                   Q(inscripcion__persona__cedula__icontains=txt_filter) |
                                                   Q(inscripcion__persona__pasaporte__icontains=txt_filter))

                matriculas = matriculas.order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')

                tCount = matriculas.count()
                if offset == 0:
                    matriculasRows = matriculas[offset:limit]
                elif offset == limit:
                    matriculasRows = matriculas[offset:tCount]
                else:
                    matriculasRows = matriculas[offset:offset + limit]
                aaData = []

                for dataRow in matriculasRows:
                    persona = u'%s %s %s' % (dataRow.inscripcion.persona.apellido1, dataRow.inscripcion.persona.apellido2, dataRow.inscripcion.persona.nombres)

                    aaData.append([persona,
                                   dataRow.matricula.alternativa.carrera.nombre,
                                   dataRow.matricula.alternativa.tipotitulacion.nombre,
                                   dataRow.estado_usuario,
                                   dataRow.status,
                                   {
                                       'id': dataRow.id,
                                       'idm': dataRow.matricula.id,
                                       'idi': dataRow.inscripcion.id,
                                       'status': dataRow.status,
                                       'alumno': persona,
                                   }])
                return JsonResponse({"result": "ok", "mensaje": u"Cargo los datos.", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos: %s" % ex, "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        if action == 'LoadDataInformationMigrate':
            try:
                idp = int(request.POST['idp']) if ('idp' in request.POST or request.POST['idp']) else 0
                idc = int(request.POST['idc']) if ('idc' in request.POST or request.POST['idc']) else 0
                isCoordinacion = int(request.POST['isCoordinacion']) if ('isCoordinacion' in request.POST or request.POST['isCoordinacion']) else 0
                isCoordinacion = bool(True if isCoordinacion == 1 else False)
                if not isCoordinacion:
                    idcc = json.loads(request.POST['idcc'])
                    if not idcc:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al consultar la carrera"})
                    carreras = Carrera.objects.filter(id__in=idcc)
                if idp == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar periodo de titulación"})
                if idc == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar la coordinación"})

                periodo = PeriodoGrupoTitulacion.objects.get(pk=idp)
                coordinacion = Coordinacion.objects.get(pk=idc)
                grupos = GrupoTitulacion.objects.filter(periodogrupo=periodo, facultad=coordinacion, status=True)
                aGrupos = []
                aTotalMatriculados = 0
                for grupo in grupos:
                    alternativas = AlternativaTitulacion.objects.filter(grupotitulacion=grupo, status=True, facultad=coordinacion)
                    if not isCoordinacion:
                        alternativas = alternativas.filter(carrera__in=carreras)
                    idsH = MatriculaRequisitosTitulacion.objects.values_list('matricula_id').filter(matricula__alternativa__in=alternativas)
                    aAlternativas = []
                    for alternativa in alternativas:
                        cMatriculados = alternativa.matriculatitulacion_set.values("id").filter(
                            Q(estado=1) | Q(estado=9) | Q(estado=10) | Q(estado=6) | Q(estado=7)).exclude(id__in=idsH).count()
                        aTotalMatriculados += cMatriculados
                        aAlternativas.append({"id": alternativa.id,
                                              "aTipo": {"id": alternativa.tipotitulacion.id,
                                                        "nombre": alternativa.tipotitulacion.nombre},
                                              "aCarrera": {"id": alternativa.carrera.id,
                                                           "nombre": alternativa.carrera.nombre},
                                              "aMatriculados": cMatriculados
                                              })
                    aGrupos.append({"id": grupo.id, "nombre": grupo.nombre, "aAlternativas": aAlternativas})

                aData = {"aPeriodo": {"id": periodo.id, "nombre": periodo.nombre},
                         "aFacultad": {"id": coordinacion.id, "nombre": coordinacion.nombre},
                         "aGrupos": aGrupos,
                         "aTotalMatriculados": aTotalMatriculados,
                         }
                return JsonResponse({"result": "ok", "mensaje": u"Cargo los datos.", "aData": [aData]})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos: %s" % ex})

        if action == 'SaveMigrateData':
            try:
                idp = int(request.POST['idp']) if ('idp' in request.POST or request.POST['idp']) else 0
                idc = int(request.POST['idc']) if ('idc' in request.POST or request.POST['idc']) else 0
                total = int(request.POST['total']) if ('total' in request.POST or request.POST['total']) else 0
                isCoordinacion = int(request.POST['isCoordinacion']) if ('isCoordinacion' in request.POST or request.POST['isCoordinacion']) else 0
                isCoordinacion = bool(True if isCoordinacion == 1 else False)
                carreras = None
                alternativas = None
                if not isCoordinacion:
                    idcc = json.loads(request.POST['idcc'])
                    if not idcc:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al consultar la carrera"})
                    carreras = Carrera.objects.filter(id__in=idcc)
                if idp == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar periodo de titulación"})
                if idc == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar la coordinación"})
                idas = json.loads(request.POST['idas'])
                if not idas or not total:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})
                if len(idas) == 0 or total == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"No existe registros a migrar"})

                alternativas = AlternativaTitulacion.objects.filter(id__in=idas)
                ePeriodo = PeriodoGrupoTitulacion.objects.get(pk=idp)
                eCoordinacion = Coordinacion.objects.get(pk=idc)
                historialMatriculados = HistorialMigracionMatriculaTitulacion(periodo=ePeriodo,
                                                                              coordinacion=eCoordinacion,
                                                                              total_matriculados=total)
                historialMatriculados.save(request)
                if carreras:
                    for carrera in carreras:
                        historialMatriculados.carrera.add(carrera)
                    historialMatriculados.save(request)
                for alternativa in alternativas:
                    historialMatriculados.alternativa.add(alternativa)
                historialMatriculados.save(request)
                log(u'Adiciono historial de migración de matriculados de titulación: %s' % historialMatriculados, request, "add")

                requisitos = RequisitoSustentar.objects.filter(Q(validasecretariageneral=True) | Q(validasecretariageneral__isnull=True), status=True)
                for alternativa in alternativas:
                    matriculaciones = alternativa.matriculatitulacion_set.filter(Q(estado=1) | Q(estado=9) | Q(estado=10) | Q(estado=6) | Q(estado=7))
                    for matricula in matriculaciones:
                        if not MatriculaRequisitosTitulacion.objects.filter(matricula=matricula, inscripcion=matricula.inscripcion).exists():
                            matricula_requisito_titulacion = MatriculaRequisitosTitulacion(inscripcion=matricula.inscripcion,
                                                                                           matricula=matricula,
                                                                                           estado_sistema=3,
                                                                                           estado_usuario=3)
                            matricula_requisito_titulacion.save(request)
                            log(u'Adiciono la matricula de titulación: %s' % matricula_requisito_titulacion, request, "add")
                            for requisito in requisitos:
                                validacion = ValidacionRequisitosTitulacion(matricula=matricula_requisito_titulacion,
                                                                   requisito=requisito,
                                                                   estado_sistema=3,
                                                                   estado_usuario=3)
                                validacion.save(request)
                                log(u'Adiciono requisitos a validar: %s' % validacion, request, "add")
                                observacion = ObservacionRequisitosTitulacion(validacion=validacion,
                                                                              estado_sistema=3,
                                                                              estado_usuario=3)
                                observacion.save(request)
                                log(u'Adiciono observación: %s' % observacion, request, "add")

                return JsonResponse({"result": "ok", "mensaje": u"Migrado Correctamente!"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos: %s" % ex})

        if action == 'LoadRequirementsStudentInformation':
            try:
                id = int(request.POST['id']) if ('id' in request.POST or request.POST['id']) else 0
                # idm = int(request.POST['idm']) if ('idm' in request.POST or request.POST['idm']) else 0
                # idi = int(request.POST['idi']) if ('idi' in request.POST or request.POST['idi']) else 0
                matricularequisito = MatriculaRequisitosTitulacion.objects.get(pk=id)
                if not matricularequisito:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos"})

                validaciones = matricularequisito.validacionrequisitostitulacion_set.all()
                aData = []
                for validacion in validaciones:
                    if validacion.usuario_modificacion:
                        ultimo_usuario = validacion.usuario_modificacion.username
                        ultima_fecha = validacion.fecha_modificacion.date().strftime('%d-%m-%Y')
                    else:
                        ultimo_usuario = validacion.usuario_creacion.username
                        ultima_fecha = validacion.fecha_creacion.date().strftime('%d-%m-%Y')

                    aData.append({"id": validacion.id,
                                  "requisito": validacion.requisito.nombre,
                                  "estado_sistema": validacion.estado_sistema,
                                  "observacion_sistema": validacion.observacion_sistema if validacion.observacion_sistema else '',
                                  "estado_usuario": validacion.estado_usuario,
                                  "observacion_usuario": validacion.observacion_usuario if validacion.observacion_usuario else '',
                                  "ultimo_usuario": ultimo_usuario,
                                  "ultima_fecha": ultima_fecha,
                                  "tiporequisito": validacion.requisito.tiporequisito,
                                  "inscripcion": validacion.matricula.inscripcion.id
                                  })

                return JsonResponse({"result": "ok", "mensaje": u"Cargo los datos.", "aData": aData})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos: %s" % ex})

        if action == 'verdetallerequisitos':
            try:
                id = int(request.POST['id']) if ('id' in request.POST or request.POST['id']) else 0
                asignada = MateriaAsignada.objects.get(pk=id)
                inscripcion = asignada.matricula.inscripcion
                alumno = Inscripcion.objects.filter(id=inscripcion.id)
                carrera = asignada.matricula.inscripcion.carrera
                malla = Malla.objects.get(carrera=carrera, vigente=True)
                listadorequisitos = malla.requisitotitulacionmalla_set.filter(status=True).order_by('requisito__nombre')
                if not MatriculaRequisitosTitulacion.objects.filter(inscripcion=inscripcion).exists():
                    matricularequisitos = MatriculaRequisitosTitulacion(inscripcion=inscripcion)
                    matricularequisitos.save()
                matricularequisitos = MatriculaRequisitosTitulacion.objects.get(inscripcion=inscripcion)
                if not ValidacionRequisitosTitulacion.objects.filter(matricula=matricularequisitos).exists():
                    for requisito in listadorequisitos:
                        validacion = ValidacionRequisitosTitulacion(matricula=matricularequisitos, requisitot=requisito.requisito)
                        validacion.save()
                validaciones = matricularequisitos.validacionrequisitostitulacion_set.all()
                data['validaciones'] = validaciones
                data['alumno'] = alumno
                template = get_template("adm_validarrequisitostitulacion/modal/validarequisitos.html")
                return JsonResponse({"result": True, 'data': template.render(data)})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'cargarrequisitodetalle':
            try:
                id = int(request.POST['id']) if ('id' in request.POST or request.POST['id']) else 0
                if id == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos"})
                aData = {}
                # TIPO_REQUISITOS = ((1, u"ESTADO CREDITO"),
                #                    (2, u"ESTADO NIVEL"),
                #                    (3, u"ESTADO ADEUDAR"),
                #                    (4, u"ESTADO FICHA ESTUDIANTIL"),
                #                    (5, u"ESTADO INGLES"),
                #                    (6, u"ESTADO PRACTICAS PREPROFESIONALES"),
                #                    (7, u"ESTADO VINCULACION"),
                #                    (8, u"ESTADO COMPUTACION"))

                validacion = ValidacionRequisitosTitulacion.objects.get(pk=id)
                data['validacion'] = validacion
                data['inscripcion'] = inscripcion = validacion.matricula.inscripcion
                # alternativa = AlternativaTitulacion.objects.get(pk=validacion.matricula.matricula.alternativa_id)
                # data['alternativa'] = alternativa
                data['item'] = validacion.requisitot.funcion
                data['esta_mat_ultimo_nivel'] = inscripcion.esta_matriculado_ultimo_nivel()
                malla = inscripcion.inscripcionmalla_set.filter(status=True)[0].malla
                excluiralumnos = datetime(2009, 1, 21, 23, 59, 59).date()
                fechainicioprimernivel = inscripcion.fechainicioprimernivel if inscripcion.fechainicioprimernivel else datetime.now().date()

                if validacion.requisitot.funcion == 1 or validacion.requisitot.funcion == 2 or validacion.requisitot.funcion == 11 or validacion.requisitot.funcion == 12:
                    asignaturas_modulo = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(status=True, malla__id__in=[22,32])
                    data['records'] = inscripcion.recordacademico_set.filter(status=True).exclude(asignatura__id__in=asignaturas_modulo).order_by('asignaturamalla__nivelmalla', 'asignatura', 'fecha')
                    #data['records'] = inscripcion.recordacademico_set.filter(status=True).order_by('asignaturamalla__nivelmalla', 'asignatura', 'fecha')
                    data['total_creditos'] = inscripcion.total_creditos()
                    data['total_creditos_malla'] = inscripcion.total_creditos_malla()
                    data['total_creditos_modulos'] = inscripcion.total_creditos_modulos()
                    data['total_creditos_otros'] = inscripcion.total_creditos_otros()
                    data['total_horas'] = inscripcion.total_horas()
                    data['promedio'] = inscripcion.promedio_record()
                    data['aprobadas'] = inscripcion.recordacademico_set.filter(aprobada=True, valida=True).exclude(asignatura__id__in=asignaturas_modulo).count()
                    data['reprobadas'] = inscripcion.recordacademico_set.filter(aprobada=False, valida=True).exclude(asignatura__id__in=asignaturas_modulo).count()
                    data['inscripcion_malla'] = inscripcionmalla = inscripcion.malla_inscripcion()
                    data['malla'] = malla = inscripcionmalla.malla
                    data['nivelesdemallas'] = nivelmalla = NivelMalla.objects.all().order_by('id')
                    data['ejesformativos'] = EjeFormativo.objects.all().order_by('nombre')
                    listadoasignaturamalla = AsignaturaMalla.objects.filter(malla=malla)
                    listas_asignaturasmallas = []
                    for x in listadoasignaturamalla.exclude(ejeformativo_id=4):
                        listas_asignaturasmallas.append([x, inscripcion.aprobadaasignatura(x)])

                    for ni in nivelmalla:
                        listadooptativa = listadoasignaturamalla.filter(nivelmalla=ni, ejeformativo_id=4)
                        if inscripcion.recordacademico_set.filter(asignatura__in=listadooptativa.values_list('asignatura__id', flat=True)).exists():
                            for d in listadooptativa:
                                if inscripcion.aprobadaasignatura(d):
                                    listas_asignaturasmallas.append([d, inscripcion.aprobadaasignatura(d)])
                        else:
                            for d in listadooptativa:
                                listas_asignaturasmallas.append([d, inscripcion.aprobadaasignatura(d)])
                    data['asignaturasmallas'] = listas_asignaturasmallas
                    resumenniveles = [{'id': x.id, 'horas': x.total_horas(malla), 'creditos': x.total_creditos(malla)} for x in NivelMalla.objects.all().order_by('id')]
                    data['resumenes'] = resumenniveles

                    if validacion.requisitot.funcion == 1 or validacion.requisitot.funcion == 2:
                        data['creditos'] = inscripcion.aprobo_asta_penultimo_malla()
                        data['cantasigaprobadas'] = inscripcion.cantidad_asig_aprobada_penultimo_malla()
                        data['cantasigaprobar'] = inscripcion.cantidad_asig_aprobar_penultimo_malla()
                        data['esta_mat_ultimo_nivel'] = inscripcion.esta_matriculado_ultimo_nivel()
                        aData['estado_sistema'] = 1 if (inscripcion.aprobo_asta_penultimo_malla() and inscripcion.esta_matriculado_ultimo_nivel()) else 2

                    else:

                        total_materias_malla = malla.cantidad_materiasaprobadas()
                        cantidad_materias_aprobadas_record = inscripcion.recordacademico_set.filter(aprobada=True, status=True, asignatura__in=[x.asignatura for x in malla.asignaturamalla_set.filter(status=True)]).count()
                        poraprobacion = round(cantidad_materias_aprobadas_record * 100 / total_materias_malla, 0)
                        data['mi_nivel'] = nivel = inscripcion.mi_nivel()
                        inscripcionmalla = inscripcion.malla_inscripcion()
                        niveles_maximos = inscripcionmalla.malla.niveles_regulares

                        if poraprobacion >= 100:
                            data['nivel'] = True
                            aData['estado_sistema'] = 1
                        else:
                            aData['estado_sistema'] = 2
                            if niveles_maximos == nivel.nivel.id:
                                data['septimo'] = True

                    template = get_template("adm_validarrequisitostitulacion/modal/record_malla.html")
                if validacion.requisitot.funcion == 3:
                    data['alumno'] = alumno = inscripcion.persona
                    data['documentopersonal'] = alumno.documentos_personales()
                    data['datosextension'] = alumno.datos_extension()
                    data['examenfisico'] = alumno.datos_examen_fisico()
                    if alumno.tipocelular == 0:
                        data['tipocelular'] = '-'
                    else:
                        data['tipocelular'] = TIPO_CELULAR[int(alumno.tipocelular) - 1][1]
                    data['perfil'] = perfil = alumno.mi_perfil()
                    data['niveltitulo'] = NivelTitulacion.objects.filter(status=True).order_by('-rango')
                    lista_becas = []
                    becasinternas = BecaAsignacion.objects.filter(solicitud__inscripcion__persona=alumno, status=True)
                    for beca in becasinternas:
                        lista_becas.append(
                            ['INTERNA', 'PÚBLICA', 'UNIVERSIDAD ESTATAL DE MILAGRO', beca.solicitud.periodo,
                             beca.solicitud.becatipo, None, beca.fecha,
                             'NO' if beca.solicitud.periodo.finalizo() else 'SI', None, None, None, None])

                    becasexternas = BecaPersona.objects.filter(persona=alumno, status=True)
                    for beca in becasexternas:
                        becaarchivo = None
                        becafechainicio = None
                        if beca.archivo:
                            becaarchivo = beca.archivo.url
                        if beca.fechainicio:
                            becafechainicio = beca.fechainicio
                        lista_becas.append(
                            ['EXTERNA', beca.get_tipoinstitucion_display(), beca.institucion.nombre, None, None,
                             becaarchivo, becafechainicio, 'NO' if beca.fechafin else 'SI', beca.estadoarchivo,
                             beca.get_estadoarchivo_display(), beca.observacion, encrypt(beca.id)])

                    lista_becas.sort(key=lambda beca: beca[6], reverse=True)

                    data['becas'] = lista_becas
                    data['deportista'] = DeportistaPersona.objects.filter(persona=alumno, status=True).order_by('-id')
                    data['migrante'] = MigrantePersona.objects.filter(persona=alumno)[
                        0] if MigrantePersona.objects.filter(persona=alumno).exists() else None
                    data['artistas'] = ArtistaPersona.objects.filter(persona=alumno, status=True).order_by('-id')
                    aData['estado_sistema'] = 2
                    ficha = 0
                    if inscripcion.persona.nombres and inscripcion.persona.apellido1 and inscripcion.persona.apellido2 and inscripcion.persona.nacimiento and inscripcion.persona.cedula and inscripcion.persona.nacionalidad and inscripcion.persona.email and inscripcion.persona.estado_civil and inscripcion.persona.sexo:
                        data['datospersonales'] = True
                        ficha += 1
                    if inscripcion.persona.paisnacimiento and inscripcion.persona.provincianacimiento and inscripcion.persona.cantonnacimiento and inscripcion.persona.parroquianacimiento:
                        data['datosnacimientos'] = True
                        ficha += 1
                    examenfisico = inscripcion.persona.datos_examen_fisico()
                    if inscripcion.persona.sangre and examenfisico.peso and examenfisico.talla:
                        data['datosmedicos'] = True
                        ficha += 1
                    if inscripcion.persona.pais and inscripcion.persona.provincia and inscripcion.persona.canton and inscripcion.persona.parroquia and inscripcion.persona.direccion and inscripcion.persona.direccion2 and inscripcion.persona.num_direccion and inscripcion.persona.telefono_conv or inscripcion.persona.telefono:
                        data['datosdomicilio'] = True
                        ficha += 1
                    if perfil.raza:
                        data['etnia'] = True
                        ficha += 1
                    if ficha == 5:
                        aData['estado_sistema'] = 1
                    template = get_template("adm_validarrequisitostitulacion/modal/hojavida.html")
                if validacion.requisitot.funcion == 4 or validacion.requisitot.funcion == 5:
                    aData['estado_sistema'] = 2
                    if validacion.requisitot.funcion == 4:
                        malla_ids = [22]
                    else:
                        malla_ids = [32]
                    asignaturas_modulo = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(status=True, malla__id__in=malla_ids)
                    data['records'] = inscripcion.recordacademico_set.filter(status=True, asignatura__id__in=asignaturas_modulo).order_by('asignaturamalla__nivelmalla', 'asignatura', 'fecha')
                    data['total_horas'] = null_to_numeric(inscripcion.recordacademico_set.filter(valida=True, status=True, asignatura__id__in=asignaturas_modulo).aggregate(horas=Sum('horas'))['horas'])
                    data['total_creditos'] = null_to_numeric(inscripcion.recordacademico_set.filter(valida=True, status=True, asignatura__id__in=asignaturas_modulo).aggregate(creditos=Sum('creditos'))['creditos'])
                    data['aprobadas'] = inscripcion.recordacademico_set.filter(aprobada=True, valida=True, status=True, asignatura__id__in=asignaturas_modulo).count()
                    data['reprobadas'] = inscripcion.recordacademico_set.filter(aprobada=False, valida=True, status=True, asignatura__id__in=asignaturas_modulo).count()
                    if validacion.requisitot.funcion == 4:
                        modulo_ingles = ModuloMalla.objects.filter(malla=malla, status=True).exclude(asignatura_id=782)
                        numero_modulo_ingles = modulo_ingles.count()
                        lista = []
                        listaid = []
                        for modulo in modulo_ingles:
                            if inscripcion.estado_asignatura(modulo.asignatura) == NOTA_ESTADO_APROBADO:
                                lista.append(modulo.asignatura.nombre)
                                listaid.append(modulo.asignatura.id)
                        data['modulo_ingles_aprobados'] = lista
                        data['modulo_ingles_faltante'] = modulo_ingles.exclude(asignatura_id__in=[int(i) for i in listaid])
                        if numero_modulo_ingles == len(listaid):
                            data['modulo_ingles'] = True
                            aData['estado_sistema'] = 1
                    else:
                        computacion_asignatura_ids = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(malla__id=32)
                        data['record_computacion'] = record = inscripcion.recordacademico_set.filter(asignatura__id__in=computacion_asignatura_ids, aprobada=True)
                        creditos_computacion = 0
                        data['malla_creditos_computacion'] = malla.creditos_computacion
                        for comp in record:
                            creditos_computacion += comp.creditos
                        if creditos_computacion >= malla.creditos_computacion:
                            data['computacion'] = True
                            aData['estado_sistema'] = 1
                        data['creditos_computacion'] = creditos_computacion

                    template = get_template("adm_validarrequisitostitulacion/modal/modulos_ingles_computacion.html")
                if validacion.requisitot.funcion == 6:
                    aData['estado_sistema'] = 2
                    data['practicas'] = PracticasPreprofesionalesInscripcion.objects.filter(culminada=True, status=True,inscripcion=inscripcion)
                    totalhoras = 0
                    practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(inscripcion=inscripcion, status=True, culminada=True)
                    data['malla_horas_practicas'] = malla.horas_practicas
                    if fechainicioprimernivel > excluiralumnos:
                        if practicaspreprofesionalesinscripcion.exists():
                            for practicas in practicaspreprofesionalesinscripcion:
                                if practicas.tiposolicitud == 3:
                                    totalhoras += practicas.horahomologacion if practicas.horahomologacion else 0
                                else:
                                    totalhoras += practicas.numerohora
                            if totalhoras >= malla.horas_practicas:
                                data['practicaspreprofesionales'] = True
                                aData['estado_sistema'] = 1
                        data['practicaspreprofesionalesvalor'] = totalhoras
                    else:
                        data['practicaspreprofesionales'] = True
                        aData['estado_sistema'] = 1
                        data['practicaspreprofesionalesvalor'] = malla.horas_practicas
                    template = get_template("adm_validarrequisitostitulacion/modal/practicaspreprofesionales.html")
                if validacion.requisitot.funcion == 7:
                    aData['estado_sistema'] = 2
                    data['malla_horas_vinculacion'] = malla.horas_vinculacion
                    horastotal = ParticipantesMatrices.objects.filter(matrizevidencia_id=2, status=True, inscripcion_id=inscripcion.id).aggregate(horastotal=Sum('horas'))['horastotal']
                    horastotal = horastotal if horastotal else 0
                    if fechainicioprimernivel > excluiralumnos:
                        if horastotal >= malla.horas_vinculacion:
                            data['vinculacion'] = True
                            aData['estado_sistema'] = 1
                        data['horas_vinculacion'] = horastotal
                    else:
                        data['horas_vinculacion'] = malla.horas_vinculacion
                        data['vinculacion'] = True
                        aData['estado_sistema'] = 1

                    data['vinculaciones'] = inscripcion.mis_proyectos_vinculacion()
                    template = get_template("adm_validarrequisitostitulacion/modal/proyectosvinculacion.html")
                if validacion.requisitot.funcion == 8:
                    aData['estado_sistema'] = 2
                    data['cliente'] = cliente = inscripcion.persona
                    rubrosnocancelados = cliente.rubro_set.filter(cancelado=False, status=True).order_by('cancelado', 'fechavence')
                    rubroscanceldos = cliente.rubro_set.filter(cancelado=True, status=True).order_by('fechavence')
                    rubros = list(chain(rubrosnocancelados, rubroscanceldos))
                    data['rubros'] = rubros
                    data['tiene_nota_debito'] = RubroNotaDebito.objects.filter(rubro__persona=cliente, rubro__cancelado=False).exists()
                    if inscripcion.adeuda_a_la_fecha() == 0:
                        data['deudas'] = True
                        aData['estado_sistema'] = 1
                    data['deudasvalor'] = inscripcion.adeuda_a_la_fecha()
                    template = get_template("adm_validarrequisitostitulacion/modal/finanzas_rubros.html")

                json_content = template.render(data)
                return JsonResponse({"result": True, 'data': template.render(data)})
            except Exception as ex:
                return JsonResponse({"result": False, "mensaje": u"Error al cargar los datos: %s" % ex})

        if action == 'noaplica':
            try:
                id = int(request.POST['id']) if ('id' in request.POST or request.POST['id']) else 0
                idvalidacion = int(request.POST['idvalidacion']) if ('idvalidacion' in request.POST or request.POST['idvalidacion']) else 0
                observacion = str(request.POST['observacion']) if ('observacion' in request.POST or request.POST['observacion']) else ''
                if id == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos"})
                validacion = ValidacionRequisitosTitulacion.objects.get(pk=idvalidacion)


                return JsonResponse({"result": True})
            except Exception as ex:
                return JsonResponse({"result": False, "mensaje": u"Error al cargar los datos: %s" % ex})

        if action == 'LoadDetalleTitulo':
            try:
                data['titulacion'] = titulacion = Titulacion.objects.get(pk=int(request.POST['id']))
                if titulacion.usuario_creacion:
                    data['personacreacion'] = Persona.objects.get(usuario=titulacion.usuario_creacion) if titulacion.usuario_creacion.id > 1 else ""
                template = get_template("th_hojavida/detalletitulo.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'LoadDetailEvent':
            try:
                data['evento'] = CapEventoPeriodoIpec.objects.get(pk=int(request.POST['id']))
                template = get_template("adm_validarrequisitostitulacion/detalle_evento.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'LoadInfRequestStudent':
            try:
                id = int(request.POST['id']) if ('id' in request.POST or request.POST['id']) else 0
                if id == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos"})
                aData = {}
                # TIPO_REQUISITOS = ((1, u"ESTADO CREDITO"),
                #                    (2, u"ESTADO NIVEL"),
                #                    (3, u"ESTADO ADEUDAR"),
                #                    (4, u"ESTADO FICHA ESTUDIANTIL"),
                #                    (5, u"ESTADO INGLES"),
                #                    (6, u"ESTADO PRACTICAS PREPROFESIONALES"),
                #                    (7, u"ESTADO VINCULACION"),
                #                    (8, u"ESTADO COMPUTACION"))

                validacion = ValidacionRequisitosTitulacion.objects.get(pk=id)
                data['inscripcion'] = inscripcion = validacion.matricula.inscripcion
                alternativa = AlternativaTitulacion.objects.get(pk=validacion.matricula.matricula.alternativa_id)
                data['alternativa'] = alternativa
                data['item'] = validacion.requisito.tiporequisito
                data['esta_mat_ultimo_nivel'] = inscripcion.esta_matriculado_ultimo_nivel()
                malla = inscripcion.inscripcionmalla_set.filter(status=True)[0].malla
                excluiralumnos = datetime(2009, 1, 21, 23, 59, 59).date()
                fechainicioprimernivel = inscripcion.fechainicioprimernivel if inscripcion.fechainicioprimernivel else datetime.now().date()

                if validacion.requisito.tiporequisito == 1 or validacion.requisito.tiporequisito == 2:
                    asignaturas_modulo = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(status=True, malla__id__in=[22,32])
                    data['records'] = inscripcion.recordacademico_set.filter(status=True).exclude(asignatura__id__in=asignaturas_modulo).order_by('asignaturamalla__nivelmalla', 'asignatura', 'fecha')
                    #data['records'] = inscripcion.recordacademico_set.filter(status=True).order_by('asignaturamalla__nivelmalla', 'asignatura', 'fecha')
                    data['total_creditos'] = inscripcion.total_creditos()
                    data['total_creditos_malla'] = inscripcion.total_creditos_malla()
                    data['total_creditos_modulos'] = inscripcion.total_creditos_modulos()
                    data['total_creditos_otros'] = inscripcion.total_creditos_otros()
                    data['total_horas'] = inscripcion.total_horas()
                    data['promedio'] = inscripcion.promedio_record()
                    data['aprobadas'] = inscripcion.recordacademico_set.filter(aprobada=True, valida=True).exclude(asignatura__id__in=asignaturas_modulo).count()
                    data['reprobadas'] = inscripcion.recordacademico_set.filter(aprobada=False, valida=True).exclude(asignatura__id__in=asignaturas_modulo).count()
                    data['inscripcion_malla'] = inscripcionmalla = inscripcion.malla_inscripcion()
                    data['malla'] = malla = inscripcionmalla.malla
                    data['nivelesdemallas'] = nivelmalla = NivelMalla.objects.all().order_by('id')
                    data['ejesformativos'] = EjeFormativo.objects.all().order_by('nombre')
                    listadoasignaturamalla = AsignaturaMalla.objects.filter(malla=malla)
                    listas_asignaturasmallas = []
                    for x in listadoasignaturamalla.exclude(ejeformativo_id=4):
                        listas_asignaturasmallas.append([x, inscripcion.aprobadaasignatura(x)])

                    for ni in nivelmalla:
                        listadooptativa = listadoasignaturamalla.filter(nivelmalla=ni, ejeformativo_id=4)
                        if inscripcion.recordacademico_set.filter(asignatura__in=listadooptativa.values_list('asignatura__id', flat=True)).exists():
                            for d in listadooptativa:
                                if inscripcion.aprobadaasignatura(d):
                                    listas_asignaturasmallas.append([d, inscripcion.aprobadaasignatura(d)])
                        else:
                            for d in listadooptativa:
                                listas_asignaturasmallas.append([d, inscripcion.aprobadaasignatura(d)])
                    data['asignaturasmallas'] = listas_asignaturasmallas
                    resumenniveles = [{'id': x.id, 'horas': x.total_horas(malla), 'creditos': x.total_creditos(malla)} for x in NivelMalla.objects.all().order_by('id')]
                    data['resumenes'] = resumenniveles

                    if validacion.requisito.tiporequisito == 1:
                        data['creditos'] = inscripcion.aprobo_asta_penultimo_malla()
                        data['cantasigaprobadas'] = inscripcion.cantidad_asig_aprobada_penultimo_malla()
                        data['cantasigaprobar'] = inscripcion.cantidad_asig_aprobar_penultimo_malla()
                        data['esta_mat_ultimo_nivel'] = inscripcion.esta_matriculado_ultimo_nivel()
                        aData['estado_sistema'] = 1 if (inscripcion.aprobo_asta_penultimo_malla() and inscripcion.esta_matriculado_ultimo_nivel()) else 2

                    else:

                        total_materias_malla = malla.cantidad_materiasaprobadas()
                        cantidad_materias_aprobadas_record = inscripcion.recordacademico_set.filter(aprobada=True, status=True, asignatura__in=[x.asignatura for x in malla.asignaturamalla_set.filter(status=True)]).count()
                        poraprobacion = round(cantidad_materias_aprobadas_record * 100 / total_materias_malla, 0)
                        data['mi_nivel'] = nivel = inscripcion.mi_nivel()
                        inscripcionmalla = inscripcion.malla_inscripcion()
                        niveles_maximos = inscripcionmalla.malla.niveles_regulares

                        if poraprobacion >= 100:
                            data['nivel'] = True
                            aData['estado_sistema'] = 1
                        else:
                            aData['estado_sistema'] = 2
                            if niveles_maximos == nivel.nivel.id:
                                data['septimo'] = True

                    template = get_template("adm_validarrequisitostitulacion/record_malla.html")
                if validacion.requisito.tiporequisito == 3:
                    aData['estado_sistema'] = 2
                    data['cliente'] = cliente = inscripcion.persona
                    rubrosnocancelados = cliente.rubro_set.filter(cancelado=False, status=True).order_by('cancelado', 'fechavence')
                    rubroscanceldos = cliente.rubro_set.filter(cancelado=True, status=True).order_by('fechavence')
                    rubros = list(chain(rubrosnocancelados, rubroscanceldos))
                    data['rubros'] = rubros
                    data['tiene_nota_debito'] = RubroNotaDebito.objects.filter(rubro__persona=cliente, rubro__cancelado=False).exists()
                    if inscripcion.adeuda_a_la_fecha() == 0:
                        data['deudas'] = True
                        aData['estado_sistema'] = 1
                    data['deudasvalor'] = inscripcion.adeuda_a_la_fecha()
                    template = get_template("adm_validarrequisitostitulacion/finanzas_rubros.html")
                if validacion.requisito.tiporequisito == 4:
                    data['alumno'] = alumno = inscripcion.persona
                    data['documentopersonal'] = alumno.documentos_personales()
                    data['datosextension'] = alumno.datos_extension()
                    data['examenfisico'] = alumno.datos_examen_fisico()
                    if alumno.tipocelular == 0:
                        data['tipocelular'] = '-'
                    else:
                        data['tipocelular'] = TIPO_CELULAR[int(alumno.tipocelular) - 1][1]
                    data['perfil'] = perfil = alumno.mi_perfil()
                    data['niveltitulo'] = NivelTitulacion.objects.filter(status=True).order_by('-rango')
                    lista_becas = []
                    becasinternas = BecaAsignacion.objects.filter(solicitud__inscripcion__persona=alumno, status=True)
                    for beca in becasinternas:
                        lista_becas.append(
                            ['INTERNA', 'PÚBLICA', 'UNIVERSIDAD ESTATAL DE MILAGRO', beca.solicitud.periodo,
                             beca.solicitud.becatipo, None, beca.fecha,
                             'NO' if beca.solicitud.periodo.finalizo() else 'SI', None, None, None, None])

                    becasexternas = BecaPersona.objects.filter(persona=alumno, status=True)
                    for beca in becasexternas:
                        becaarchivo = None
                        becafechainicio = None
                        if beca.archivo:
                            becaarchivo = beca.archivo.url
                        if beca.fechainicio:
                            becafechainicio = beca.fechainicio
                        lista_becas.append(
                            ['EXTERNA', beca.get_tipoinstitucion_display(), beca.institucion.nombre, None, None,
                             becaarchivo, becafechainicio, 'NO' if beca.fechafin else 'SI', beca.estadoarchivo,
                             beca.get_estadoarchivo_display(), beca.observacion, encrypt(beca.id)])

                    lista_becas.sort(key=lambda beca: beca[6], reverse=True)

                    data['becas'] = lista_becas
                    data['deportista'] = DeportistaPersona.objects.filter(persona=alumno, status=True).order_by('-id')
                    data['migrante'] = MigrantePersona.objects.filter(persona=alumno)[
                        0] if MigrantePersona.objects.filter(persona=alumno).exists() else None
                    data['artistas'] = ArtistaPersona.objects.filter(persona=alumno, status=True).order_by('-id')
                    aData['estado_sistema'] = 2
                    ficha = 0
                    if inscripcion.persona.nombres and inscripcion.persona.apellido1 and inscripcion.persona.apellido2 and inscripcion.persona.nacimiento and inscripcion.persona.cedula and inscripcion.persona.nacionalidad and inscripcion.persona.email and inscripcion.persona.estado_civil and inscripcion.persona.sexo:
                        data['datospersonales'] = True
                        ficha += 1
                    if inscripcion.persona.paisnacimiento and inscripcion.persona.provincianacimiento and inscripcion.persona.cantonnacimiento and inscripcion.persona.parroquianacimiento:
                        data['datosnacimientos'] = True
                        ficha += 1
                    examenfisico = inscripcion.persona.datos_examen_fisico()
                    if inscripcion.persona.sangre and examenfisico.peso and examenfisico.talla:
                        data['datosmedicos'] = True
                        ficha += 1
                    if inscripcion.persona.pais and inscripcion.persona.provincia and inscripcion.persona.canton and inscripcion.persona.parroquia and inscripcion.persona.direccion and inscripcion.persona.direccion2 and inscripcion.persona.num_direccion and inscripcion.persona.telefono_conv or inscripcion.persona.telefono:
                        data['datosdomicilio'] = True
                        ficha += 1
                    if perfil.raza:
                        data['etnia'] = True
                        ficha += 1
                    if ficha == 5:
                        aData['estado_sistema'] = 1
                    template = get_template("adm_validarrequisitostitulacion/hojavida.html")
                if validacion.requisito.tiporequisito == 5 or validacion.requisito.tiporequisito == 8:
                    aData['estado_sistema'] = 2
                    if validacion.requisito.tiporequisito == 5:
                        malla_ids = [22]
                    else:
                        malla_ids = [32]
                    asignaturas_modulo = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(status=True, malla__id__in=malla_ids)
                    data['records'] = inscripcion.recordacademico_set.filter(status=True, asignatura__id__in=asignaturas_modulo).order_by('asignaturamalla__nivelmalla', 'asignatura', 'fecha')
                    data['total_horas'] = null_to_numeric(inscripcion.recordacademico_set.filter(valida=True, status=True, asignatura__id__in=asignaturas_modulo).aggregate(horas=Sum('horas'))['horas'])
                    data['total_creditos'] = null_to_numeric(inscripcion.recordacademico_set.filter(valida=True, status=True, asignatura__id__in=asignaturas_modulo).aggregate(creditos=Sum('creditos'))['creditos'])
                    data['aprobadas'] = inscripcion.recordacademico_set.filter(aprobada=True, valida=True, status=True, asignatura__id__in=asignaturas_modulo).count()
                    data['reprobadas'] = inscripcion.recordacademico_set.filter(aprobada=False, valida=True, status=True, asignatura__id__in=asignaturas_modulo).count()
                    if validacion.requisito.tiporequisito == 5:
                        modulo_ingles = ModuloMalla.objects.filter(malla=malla, status=True).exclude(asignatura_id=782)
                        numero_modulo_ingles = modulo_ingles.count()
                        lista = []
                        listaid = []
                        for modulo in modulo_ingles:
                            if inscripcion.estado_asignatura(modulo.asignatura) == NOTA_ESTADO_APROBADO:
                                lista.append(modulo.asignatura.nombre)
                                listaid.append(modulo.asignatura.id)
                        data['modulo_ingles_aprobados'] = lista
                        data['modulo_ingles_faltante'] = modulo_ingles.exclude(asignatura_id__in=[int(i) for i in listaid])
                        if numero_modulo_ingles == len(listaid):
                            data['modulo_ingles'] = True
                            aData['estado_sistema'] = 1
                    else:
                        computacion_asignatura_ids = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(malla__id=32)
                        data['record_computacion'] = record = inscripcion.recordacademico_set.filter(asignatura__id__in=computacion_asignatura_ids, aprobada=True)
                        creditos_computacion = 0
                        data['malla_creditos_computacion'] = malla.creditos_computacion
                        for comp in record:
                            creditos_computacion += comp.creditos
                        if creditos_computacion >= malla.creditos_computacion:
                            data['computacion'] = True
                            aData['estado_sistema'] = 1
                        data['creditos_computacion'] = creditos_computacion

                    template = get_template("adm_validarrequisitostitulacion/modulos_ingles_computacion.html")
                if validacion.requisito.tiporequisito == 6:
                    aData['estado_sistema'] = 2
                    data['practicas'] = PracticasPreprofesionalesInscripcion.objects.filter(culminada=True, status=True,inscripcion=inscripcion)
                    totalhoras = 0
                    practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(inscripcion=inscripcion, status=True, culminada=True)
                    data['malla_horas_practicas'] = malla.horas_practicas
                    if fechainicioprimernivel > excluiralumnos:
                        if practicaspreprofesionalesinscripcion.exists():
                            for practicas in practicaspreprofesionalesinscripcion:
                                if practicas.tiposolicitud == 3:
                                    totalhoras += practicas.horahomologacion if practicas.horahomologacion else 0
                                else:
                                    totalhoras += practicas.numerohora
                            if totalhoras >= malla.horas_practicas:
                                data['practicaspreprofesionales'] = True
                                aData['estado_sistema'] = 1
                        data['practicaspreprofesionalesvalor'] = totalhoras
                    else:
                        data['practicaspreprofesionales'] = True
                        aData['estado_sistema'] = 1
                        data['practicaspreprofesionalesvalor'] = malla.horas_practicas
                    template = get_template("adm_validarrequisitostitulacion/practicaspreprofesionales.html")
                if validacion.requisito.tiporequisito == 7:
                    aData['estado_sistema'] = 2
                    data['malla_horas_vinculacion'] = malla.horas_vinculacion
                    horastotal = ParticipantesMatrices.objects.filter(matrizevidencia_id=2, status=True, inscripcion_id=inscripcion.id).aggregate(horastotal=Sum('horas'))['horastotal']
                    horastotal = horastotal if horastotal else 0
                    if fechainicioprimernivel > excluiralumnos:
                        if horastotal >= malla.horas_vinculacion:
                            data['vinculacion'] = True
                            aData['estado_sistema'] = 1
                        data['horas_vinculacion'] = horastotal
                    else:
                        data['horas_vinculacion'] = malla.horas_vinculacion
                        data['vinculacion'] = True
                        aData['estado_sistema'] = 1

                    data['vinculaciones'] = inscripcion.mis_proyectos_vinculacion()
                    template = get_template("adm_validarrequisitostitulacion/proyectosvinculacion.html")

                json_content = template.render(data)
                return JsonResponse({"result": "ok", "mensaje": u"Cargo los datos.", "data": json_content, "aData": aData})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos: %s" % ex})

        if action == 'SaveRequestStudent':
            try:
                observacion = None
                id = int(request.POST['id']) if ('id' in request.POST or request.POST['id']) else 0
                ide = int(request.POST['ide']) if ('ide' in request.POST or request.POST['ide']) else 0
                id_estado_sistema = int(request.POST['id_estado_sistema']) if ('id_estado_sistema' in request.POST or request.POST['id_estado_sistema']) else 3
                observacion = request.POST['observacion'] if ('observacion' in request.POST or request.POST['observacion']) else None
                if id == 0 or ide == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                if ide == 2 and not observacion:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar, falta observación"})

                if observacion == 'null':
                    observacion = None

                validacion = ValidacionRequisitosTitulacion.objects.get(pk=id)
                observacion_sistema = None
                if id_estado_sistema == 2:
                    observacion_sistema = validacion.requisito.mensajenocumple
                observacionrequisito = ObservacionRequisitosTitulacion(estado_sistema=id_estado_sistema,
                                                                       estado_usuario=ide,
                                                                       observacion_sistema=observacion_sistema,
                                                                       observacion_usuario=observacion,
                                                                       validacion=validacion)
                observacionrequisito.save(request)
                log(u'Adiciono observación: %s' % observacionrequisito, request, "add")
                validacion.estado_sistema = id_estado_sistema
                validacion.estado_usuario = ide
                validacion.observacion_sistema = observacion_sistema
                validacion.observacion_usuario = observacion
                validacion.save(request)
                log(u'Edito validación: %s' % validacion, request, "edit")

                total_validaciones = ValidacionRequisitosTitulacion.objects.filter(matricula=validacion.matricula, status=True).exclude(estado_usuario=4).count()
                total_no_validados = ValidacionRequisitosTitulacion.objects.filter(matricula=validacion.matricula, status=True, estado_usuario=3).exclude(estado_usuario=4).count()
                total_aptos = ValidacionRequisitosTitulacion.objects.filter(matricula=validacion.matricula, status=True, estado_usuario=1).exclude(estado_usuario=4).count()
                total_no_aptos = ValidacionRequisitosTitulacion.objects.filter(matricula=validacion.matricula, status=True, estado_usuario=2).exclude(estado_usuario=4).count()
                estado_usu = 5
                if total_validaciones == total_aptos:
                    estado_usu = 1
                elif total_validaciones == total_no_aptos or total_no_aptos > 0:
                    estado_usu = 2
                elif total_validaciones == total_no_validados:
                    estado_usu = 3

                sis_total_validaciones = ValidacionRequisitosTitulacion.objects.filter(matricula=validacion.matricula, status=True).exclude(estado_sistema=4).count()
                sis_total_no_validados = ValidacionRequisitosTitulacion.objects.filter(matricula=validacion.matricula, status=True, estado_sistema=3).exclude(estado_sistema=4).count()
                sis_total_aptos = ValidacionRequisitosTitulacion.objects.filter(matricula=validacion.matricula, status=True, estado_sistema=1).exclude(estado_sistema=4).count()
                sis_total_no_aptos = ValidacionRequisitosTitulacion.objects.filter(matricula=validacion.matricula,status=True, estado_sistema=2).exclude(estado_sistema=4).count()
                estado_sis = 5
                if sis_total_validaciones == sis_total_aptos:
                    estado_sis = 1
                elif sis_total_validaciones == sis_total_no_aptos or sis_total_no_aptos > 0:
                    estado_sis = 2
                elif sis_total_validaciones == sis_total_no_validados:
                    estado_sis = 3

                validacion.matricula.estado_sistema = estado_sis
                validacion.matricula.estado_usuario = estado_usu
                validacion.matricula.save(request)
                log(u'Edito estado de matricula: %s' % validacion.matricula, request, "edit")

                matricularequisito = MatriculaRequisitosTitulacion.objects.get(pk=validacion.matricula_id)
                if not matricularequisito:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos"})

                validaciones = matricularequisito.validacionrequisitostitulacion_set.all()
                aData = []
                for validacion in validaciones:
                    if validacion.usuario_modificacion:
                        ultimo_usuario = validacion.usuario_modificacion.username
                        ultima_fecha = validacion.fecha_modificacion.date().strftime('%d-%m-%Y')
                    else:
                        ultimo_usuario = validacion.usuario_creacion.username
                        ultima_fecha = validacion.fecha_creacion.date().strftime('%d-%m-%Y')

                    aData.append({"id": validacion.id,
                                  "requisito": validacion.requisito.nombre,
                                  "estado_sistema": validacion.estado_sistema,
                                  "observacion_sistema": validacion.observacion_sistema if validacion.observacion_sistema else '',
                                  "estado_usuario": validacion.estado_usuario,
                                  "observacion_usuario": validacion.observacion_usuario if validacion.observacion_usuario else '',
                                  "ultimo_usuario": ultimo_usuario,
                                  "ultima_fecha": ultima_fecha,
                                  "tiporequisito": validacion.requisito.tiporequisito
                                  })

                return JsonResponse({"result": "ok", "mensaje": u"Datos Guardado correctamente!", "aData": aData})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos, %s" % ex})

        if action == 'LoadInfCertificateStudent':
            try:
                id = int(request.POST['id']) if ('id' in request.POST or request.POST['id']) else 0
                if id == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos"})
                validacion = ValidacionRequisitosTitulacion.objects.get(pk=id)
                if not validacion:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos"})
                certificados = CertificadoRequisitosTitulacion.objects.filter(validacion=validacion).order_by('-activo', '-fecha_creacion')
                aData = []
                for certificado in certificados:
                    user_persona = Persona.objects.get(usuario=certificado.usuario_creacion)
                    aData.append({"validacion": validacion.id,
                                  "certificado": certificado.id,
                                  "url": certificado.url,
                                  "activo": 1 if certificado.activo else 0,
                                  "fecha_genearacion": certificado.fecha_creacion.strftime('%Y-%m-%d %H:%M'),
                                  "usuario_generacion": u'%s %s %s' % (
                                  user_persona.apellido1, user_persona.apellido2, user_persona.nombres)})
                return JsonResponse({"result": "ok", "mensaje": u"Cargo los datos.", "aData": aData})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos: %s" % ex})

        if action == 'SaveCertificateStudent':
            try:
                id = int(request.POST['id']) if ('id' in request.POST or request.POST['id']) else 0
                url = request.POST['url'] if 'url' in request.POST or request.POST['url'] else None
                if id == 0 or not url:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos"})
                validacion = ValidacionRequisitosTitulacion.objects.get(pk=id)
                if not validacion:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos"})

                data['url'] = request.POST['url']
                template = get_template("adm_validarrequisitostitulacion/informacion_pdf.html")
                json_content = template.render(data)

                certs = CertificadoRequisitosTitulacion.objects.filter(validacion=validacion, status=True)
                if certs.exists():
                    for cert in certs:
                        cert.activo = False
                        cert.save(request)

                oCertificado = CertificadoRequisitosTitulacion(validacion=validacion, url=url, activo=True)
                oCertificado.save(request)
                log(u'Adiciono historial de certificado: %s' % oCertificado, request, "add")

                certificados = CertificadoRequisitosTitulacion.objects.filter(validacion=validacion).order_by('-activo', '-fecha_creacion')
                aData = []
                for certificado in certificados:
                    user_persona = Persona.objects.get(usuario=certificado.usuario_creacion)
                    aData.append({"validacion": validacion.id,
                                  "certificado": certificado.id,
                                  "url": certificado.url,
                                  "activo": 1 if certificado.activo else 0,
                                  "fecha_genearacion": certificado.fecha_creacion.strftime('%Y-%m-%d %H:%M'),
                                  "usuario_generacion": u'%s %s %s' % (user_persona.apellido1, user_persona.apellido2, user_persona.nombres)})
                return JsonResponse({"result": "ok", "mensaje": u"Se genero correctamente el certificado.", "aData": aData, "data": json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos: %s" % ex})

        if action == 'LoadCertificate':
            try:
                data['url'] = request.POST['url']
                template = get_template("adm_validarrequisitostitulacion/informacion_pdf.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos: %s" % ex})

        if action == 'ActiveCertificate':
            try:
                id = int(request.POST['id']) if ('id' in request.POST or request.POST['id']) else 0
                if id == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos"})
                oCertificado = CertificadoRequisitosTitulacion.objects.get(pk=id)
                if not oCertificado:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos"})

                certificados = CertificadoRequisitosTitulacion.objects.filter(validacion=oCertificado.validacion, status=True)
                if certificados.exists():
                    for certificado in certificados:
                        certificado.activo = False
                        certificado.save(request)

                oCertificado.activo = True
                oCertificado.save(request)
                log(u'Activo el certificado: %s' % oCertificado, request, "edit")

                certificados = CertificadoRequisitosTitulacion.objects.filter(validacion=oCertificado.validacion).order_by('-activo', '-fecha_creacion')
                aData = []
                for certificado in certificados:
                    user_persona = Persona.objects.get(usuario=certificado.usuario_creacion)
                    aData.append({"validacion": certificado.validacion.id,
                                  "certificado": certificado.id,
                                  "url": certificado.url,
                                  "activo": 1 if certificado.activo else 0,
                                  "fecha_genearacion": certificado.fecha_creacion.strftime('%Y-%m-%d %H:%M'),
                                  "usuario_generacion": u'%s %s %s' % (user_persona.apellido1, user_persona.apellido2, user_persona.nombres)})
                return JsonResponse({"result": "ok", "mensaje": u"Se activo certificado correctamente.", "aData": aData})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos: %s" % ex})

        elif action == 'run':
            try:
                if not 'rid' in request.POST:
                    raise NameError(u"Parametros no encontrados")
                reporte = None
                if 'n' in request.POST or 'rid' in request.POST:
                    if 'n' in request.POST:
                        reporte = Reporte.objects.get(nombre=request.POST['n'])
                    else:
                        reporte = Reporte.objects.get(pk=request.POST['rid'])
                if not reporte:
                    raise NameError(u"Reporte no encontrado")
                if reporte.version != 2:
                    raise NameError(u"Versión de reporte no soportado")
                if not reporte.archivo:
                    raise NameError(u"Archivo de reporte no encontrado")
                if not 'ptid' in request.POST:
                    raise NameError(u"Parametro periodo de titulación no encontrado")
                if not PeriodoGrupoTitulacion.objects.values('id').filter(pk=int(request.POST['ptid'])).exists():
                    raise NameError(u"Periodo de titulación no encontrado")
                ePeriodoGrupoTitulacion = PeriodoGrupoTitulacion.objects.get(pk=int(request.POST['ptid']))
                if not 'pmid' in request.POST:
                    raise NameError(u"Parametro periodo de matricula no encontrado")
                if not Periodo.objects.values('id').filter(pk=int(request.POST['pmid'])).exists():
                    raise NameError(u"Periodo de matricula no encontrado")
                ePeriodo = Periodo.objects.get(pk=int(request.POST['pmid']))
                if not 'cid' in request.POST:
                    raise NameError(u"Parametro carrera no encontrado")
                if not Carrera.objects.values('id').filter(pk=int(request.POST['cid'])).exists():
                    raise NameError(u"Carrera no encontrado")
                eCarrera = Carrera.objects.get(pk=int(request.POST['cid']))
                eCoordinacion = eCarrera.coordinaciones()[0]
                if not CoordinadorCarrera.objects.filter(periodo=ePeriodo, sede_id=1, tipo=3, carrera=eCarrera).exists():
                    raise NameError(u"No se registra director de carrera")
                eCoordinadorCarrera = CoordinadorCarrera.objects.filter(periodo=ePeriodo, sede_id=1, tipo=3, carrera=eCarrera)[0]
                if not eCoordinadorCarrera.persona:
                    raise NameError(u"No se registra responsable para la dirección de carrera")
                if not FirmaPersona.objects.filter(persona=eCoordinadorCarrera.persona, tipofirma=2).exists():
                    raise NameError(u"No existe firma del director de carrera")
                codigo = None
                certificado = None
                base_url = request.META['HTTP_HOST']
                tipo = 'pdf'
                output_folder = os.path.join(JR_USEROUTPUT_FOLDER, elimina_tildes(request.user.username))
                try:
                    os.makedirs(output_folder)
                except Exception as ex:
                    pass
                d = datetime.now()
                pdfname = reporte.nombre + d.strftime('%Y%m%d_%H%M%S')
                content_type = None
                object_id = None
                persona = Persona.objects.filter(usuario_id=request.user.id)[0]
                content_type = ContentType.objects.get_for_model(persona)
                object_id = persona.id
                if not Certificado.objects.filter(reporte=reporte, visible=True).exists():
                    raise NameError(u"No se encontro certificado activo")
                if Certificado.objects.filter(reporte=reporte, visible=True).count() > 1:
                    raise NameError(u"Mas de un certificado activo")
                certificado = Certificado.objects.get(reporte=reporte, visible=True)
                if not certificado:
                    raise NameError(u"No se encontro certificado.")
                SUFFIX = None
                uc = None
                ac = None

                if not certificado.tiene_unidades_certificadoras():
                    raise NameError(u"Certificado no tiene configurado Unidad certificadora")
                if certificado.tipo_origen == 1:
                    if not CertificadoAsistenteCertificadora.objects.filter(status=True, carrera=eCarrera, unidad_certificadora__certificado=certificado, unidad_certificadora__coordinacion=eCoordinacion).exists():
                        raise NameError(u"Certificado no tiene configurado Asistente certificadora")
                    ac = CertificadoAsistenteCertificadora.objects.get(status=True, carrera=eCarrera, unidad_certificadora__certificado=certificado, unidad_certificadora__coordinacion=eCoordinacion)
                    uc = ac.unidad_certificadora
                else:
                    if not certificado.unidades_certificadoras().count() > 0:
                        raise NameError(u"Certificado tiene configurado mas de una Unidad certificadora")
                    uc = CertificadoUnidadCertificadora.objects.get(certificado=certificado)
                if not uc or not uc.alias:
                    raise NameError(u"Certificado no tiene configurado Unidad certificadora")
                SUFFIX = uc.alias
                secuencia = 1
                try:
                    if datetime.now().month == 1 and datetime.now().day == 1 and not LogReporteDescarga.objects.filter(fechahora__gte=datetime.now().date(), suffix=SUFFIX, secuencia__gt=0).exists():
                        secuencia = 1
                    else:
                        if LogReporteDescarga.objects.filter(secuencia__gt=0, suffix=SUFFIX).order_by("-secuencia").exists():
                            sec = LogReporteDescarga.objects.filter(secuencia__gt=0, suffix=SUFFIX).order_by("-secuencia")[0].secuencia
                            if sec:
                                secuencia = int(sec) + 1
                except:
                    pass
                codigo = generar_codigo(secuencia, 'UNEMI', SUFFIX, 7)

                url = "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), pdfname + "." + tipo])
                logreporte = LogReporteDescarga(reporte=reporte,
                                                content_type=content_type,
                                                object_id=object_id,
                                                url=url,
                                                fechahora=datetime.now())
                logreporte.save(request)
                logreporte.secuencia = secuencia
                logreporte.codigo = codigo
                logreporte.prefix = 'UNEMI'
                logreporte.suffix = SUFFIX
                logreporte.save(request)

                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'documentos', 'userreports', elimina_tildes(request.user.username), ''))
                # folder = '/mnt/nfs/home/storage/media/qrcode/evaluaciondocente/'
                rutapdf = folder + pdfname + '.pdf'
                if os.path.isfile(rutapdf):
                    os.remove(rutapdf)

                runjrcommand = [JR_JAVA_COMMAND, '-jar',
                                os.path.join(JR_RUN, 'jasperstarter.jar'),
                                'pr', reporte.archivo.file.name,
                                '--jdbc-dir', JR_RUN,
                                '-f', tipo,
                                '-t', 'postgres',
                                '-H', DATABASES['sga_select']['HOST'],
                                '-n', DATABASES['sga_select']['NAME'],
                                '-u', DATABASES['sga_select']['USER'],
                                '-p', f"'{DATABASES['sga_select']['PASSWORD']}'",
                                '--db-port', DATABASES['sga_select']['PORT'],
                                '-o', output_folder + os.sep + pdfname]
                parametros = reporte.parametros()
                paramlist = [transform_jasperstarter(p, request, 'POST') for p in parametros]
                if paramlist:
                    runjrcommand.append('-P')
                    for parm in paramlist:
                        runjrcommand.append(parm)
                else:
                    runjrcommand.append('-P')

                runjrcommand.append(u'userweb=' + unicode(request.user.username))
                runjrcommand.append(u'MEDIA_DIR=' + unicode("/".join([MEDIA_ROOT, ''])))
                # runjrcommand.append(u'STATIC_DIR=' + unicode("/".join([STATIC_ROOT, ''])))
                runjrcommand.append(u'IMAGE_DIR=' + unicode(SUBREPOTRS_FOLDER))
                runjrcommand.append(u'SUBREPORT_DIR=' + reporte.ruta_subreport())
                runjrcommand.append(u'URL_QR=' + unicode(base_url + "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), pdfname + "." + tipo])))
                runjrcommand.append(u'CODIGO_QR=' + unicode(codigo))
                runjrcommand.append(u'CERTIFICADO_ID=' + unicode(certificado.id))
                mens = ''
                for m in runjrcommand:
                    mens += ' ' + m
                if DEBUG:
                    runjr = subprocess.run(mens, shell=True, check=True)
                    # print('runjr:', runjr.returncode)
                else:
                    runjr = subprocess.call(mens.encode("latin1"), shell=True)
                sp = os.path.split(reporte.archivo.file.name)
                return JsonResponse({'result': "ok", 'mensaje': "Se genero la certificación correctamente", 'reportfile': "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), pdfname + "." + tipo])})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar el reporte: %s" % ex.__str__()})

        elif action == 'carrerascoordinacion':
            try:
                lista = []
                id_carreras = MateriaTitulacion.objects.values_list('materiaasignada__materia__asignaturamalla__malla__carrera__id', flat=True).filter(materiaasignada__materia__asignaturamalla__malla__carrera__coordinacion__id=request.POST['id_coordinacion'], materiaasignada__materia__nivel__periodo=periodo, status=True).distinct()
                carreras = Carrera.objects.filter(pk__in=id_carreras)
                for carrera in carreras:
                    lista.append([carrera.id, carrera.__str__()])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos, no encontro acción a ejecutar"})



    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'reportasignatura':
                try:
                    if 'idmalla' in request.GET:
                        idmalla=int(encrypt(request.GET['idmalla']))
                        periodo=request.session['periodo']
                        if idmalla == 383:
                            materias = Materia.objects.filter(nivel__periodo_id=periodo, asignaturamalla__malla__id=idmalla, status=True).order_by('paralelo')
                        else:
                            materias = Materia.objects.filter(nivel__periodo_id=periodo, asignaturamalla__validarequisitograduacion=True, asignaturamalla__malla__id=idmalla, status=True).order_by('paralelo')
                        output = io.BytesIO()
                        workbook = xlsxwriter.Workbook(output)
                        formatorojo = workbook.add_format({'bold': True, 'font_color': 'red'})
                        for materia in materias:
                            worksheet = workbook.add_worksheet()
                            requisitos = materia.requisitomateriaunidadintegracioncurricular_set.filter(titulacion=True, status=True).order_by('id')
                            asignados = materia.materiaasignada_set.filter(status=True, retiramateria=False).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                            worksheet.write(0, 0, 'Inscrito')
                            worksheet.write(0, 1, 'Identificación')
                            worksheet.write(0, 2, 'Correo Inst')
                            worksheet.write(0, 3, 'Correo Personal')
                            worksheet.write(0, 4, 'Materia')
                            worksheet.write(0, 5, 'Paralelo')
                            worksheet.write(0, 6, 'Facultad')
                            worksheet.write(0, 7, 'Carrera')
                            worksheet.write(0, 8, 'Malla')
                            col = 9
                            fil = 1
                            for erequisito in requisitos:
                                worksheet.write(0, col, str(erequisito.requisito))
                                col += 1
                            for asignado in asignados:
                                inscripcion = asignado.matricula.inscripcion
                                worksheet.write(fil, 0, str(inscripcion.persona))
                                worksheet.write(fil, 1, str(inscripcion.persona.identificacion()))
                                worksheet.write(fil, 2, str(inscripcion.persona.emailinst))
                                worksheet.write(fil, 3, str(inscripcion.persona.email))
                                worksheet.write(fil, 4, str(materia))
                                worksheet.write(fil, 5, str(materia.paralelo))
                                worksheet.write(fil, 6, str(materia.asignaturamalla.malla.carrera.mi_coordinacion()))
                                worksheet.write(fil, 7, str(materia.asignaturamalla.malla.carrera))
                                worksheet.write(fil, 8, str(materia.asignaturamalla.malla))
                                col = 9
                                for erequisito in requisitos:
                                    cumple = erequisito.run(inscripcion.pk)
                                    estadocumple = 'NO CUMPLE'
                                    if cumple:
                                        estadocumple = 'SI CUMPLE'
                                        worksheet.write(fil, col, estadocumple)
                                    else:
                                        worksheet.write(fil, col, estadocumple, formatorojo)
                                    col += 1
                                fil += 1
                        workbook.close()
                        output.seek(0)
                        filename = 'reporte_requisitos' + random.randint(1, 10000).__str__() + '.xlsx'
                        response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                        response['Content-Disposition'] = 'attachment; filename=%s' % filename
                        return response
                    else:
                        listado1 = Materia.objects.values_list('asignaturamalla__malla_id', flat=True).filter(asignaturamalla__validarequisitograduacion=True, nivel__periodo=periodo, asignaturamalla__status=True, status=True).distinct()
                        listado2 = Materia.objects.values_list('asignaturamalla__malla_id', flat=True).filter(asignaturamalla__malla_id=383, nivel__periodo=periodo, asignaturamalla__status=True, status=True).distinct()
                        listadomalla = listado1 | listado2
                        data['mallas'] = Malla.objects.filter(pk__in=listadomalla, status=True).order_by('carrera__nombre')
                        data['action'] = action
                        template = get_template("adm_validarrequisitostitulacion/modal/formreporte.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'asignaturastitulacion':
                try:
                    data['title'] = 'Asignaturas de titulación'
                    sinrequisitos = False
                    search, idfacultad, idcarrera, url_vars = request.GET.get('s', ''), request.GET.get('idf',''), request.GET.get('idc', ''), ''
                    materiatitulacion = MateriaTitulacion.objects.filter(
                        materiaasignada__materia__nivel__periodo=periodo, materiaasignada__status=True, status=True,
                        materiaasignada__estado_id=1, materiaasignada__retiramateria=False)
                    data['listadocoordinacion'] = materiatitulacion.values_list(
                        'materiaasignada__materia__asignaturamalla__malla__carrera__coordinacion__id',
                        'materiaasignada__materia__asignaturamalla__malla__carrera__coordinacion__nombre').distinct()
                    if idfacultad:
                        data['listadocarrera'] = materiatitulacion.values_list(
                            'materiaasignada__materia__asignaturamalla__malla__carrera__id',
                            'materiaasignada__materia__asignaturamalla__malla__carrera__nombre').filter(
                            materiaasignada__materia__asignaturamalla__malla__carrera__coordinacion__id=idfacultad).distinct()
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            materiatitulacion = materiatitulacion.filter(
                                Q(materiaasignada__matricula__inscripcion__persona__nombres__icontains=search) |
                                Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=search) |
                                Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=search) |
                                Q(materiaasignada__matricula__inscripcion__persona__cedula__icontains=search) |
                                Q(materiaasignada__matricula__inscripcion__persona__pasaporte__icontains=search) |
                                Q(materiaasignada__matricula__inscripcion__persona__usuario__username__icontains=search),
                                materiaasignada__materia__nivel__periodo=periodo, materiaasignada__status=True,
                                status=True, materiaasignada__estado_id=1, materiaasignada__retiramateria=False)

                        else:
                            materiatitulacion = materiatitulacion.filter(
                                Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=ss[0]) &
                                Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=ss[1]),
                                materiaasignada__materia__nivel__periodo=periodo, materiaasignada__estado_id=1,
                                materiaasignada__status=True, status=True, materiaasignada__retiramateria=False)
                    url_vars += "&action=asignaturastitulacion"
                    if idfacultad:
                        data['idf'] = int(request.GET['idf'])
                        url_vars += "&idf={}".format(idfacultad)
                        materiatitulacion = materiatitulacion.filter(
                            materiaasignada__materia__asignaturamalla__malla__carrera__coordinacion__id=idfacultad)
                    if idcarrera:
                        data['idc'] = int(request.GET['idc'])
                        url_vars += "&idc={}".format(idcarrera)
                        materiatitulacion = materiatitulacion.filter(
                            materiaasignada__materia__asignaturamalla__malla__carrera__id=idcarrera)
                    numerofilas = 25
                    materiatitulacion = materiatitulacion.order_by(
                        'materiaasignada__materia__asignaturamalla__malla__carrera__coordinacion__id',
                        'materiaasignada__materia__asignaturamalla__malla__carrera__id',
                        'materiaasignada__materia__asignaturamalla__asignatura__nombre',
                        'materiaasignada__materia__paralelo',
                        'materiaasignada__matricula__inscripcion__persona__apellido1',
                        'materiaasignada__matricula__inscripcion__persona__apellido2',
                        'materiaasignada__matricula__inscripcion__persona__nombres')
                    paging = MiPaginador(materiatitulacion, numerofilas)
                    p = 1

                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                            if p == 1:
                                numerofilasguiente = numerofilas
                            else:
                                numerofilasguiente = numerofilas * (p - 1)
                        else:
                            p = paginasesion
                            if p == 1:
                                numerofilasguiente = numerofilas
                            else:
                                numerofilasguiente = numerofilas * (p - 1)
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['numerofilasguiente'] = numerofilasguiente
                    data['numeropagina'] = p
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    return render(request, 'adm_validarrequisitostitulacion/asignaturastitulacion.html', data)
                except Exception as ex:
                    pass



            if action == 'listadoalumnos':
                try:
                    data['title'] = 'Asignaturas de titulación'
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                    data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['idm'])))
                    sinrequisitos = False
                    if not materia.requisitomateriaunidadintegracioncurricular_set.values("id").filter(status=True).exists():
                        sinrequisitos = True
                    data['sinrequisitos'] = sinrequisitos
                    hoy = datetime.now().date()
                    rezagados = False
                    if materia.asignaturamalla.malla.id == 383:
                        rezagados = True
                    if hoy >  materia.fin:
                        if not MateriaTitulacion.objects.values("id").filter(materiaasignada__materia=materia, rezagados=rezagados).exists():
                            lmateriaasignada = materia.materiaasignada_set.filter(status=True)
                            for lasignado in lmateriaasignada:
                                if not MateriaTitulacion.objects.values("id").filter(materiaasignada=lasignado).exists():
                                    mtitulacion = MateriaTitulacion(materiaasignada=lasignado,
                                                                    rezagados=rezagados)
                                    mtitulacion.save()
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            listado = MateriaTitulacion.objects.filter(Q(materiaasignada__matricula__inscripcion__persona__nombres__icontains=search) |
                                                                       Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=search) |
                                                                       Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=search) |
                                                                       Q(materiaasignada__matricula__inscripcion__persona__cedula__icontains=search) |
                                                                       Q(materiaasignada__matricula__inscripcion__persona__pasaporte__icontains=search) |
                                                                       Q(materiaasignada__matricula__inscripcion__persona__usuario__username__icontains=search),
                                                                       materiaasignada__materia=materia, materiaasignada__status=True, status=True,materiaasignada__retiramateria=False).order_by('materiaasignada__matricula__inscripcion__persona__apellido1', 'materiaasignada__matricula__inscripcion__persona__apellido2', 'materiaasignada__matricula__inscripcion__persona__nombres')

                        else:
                            listado = MateriaTitulacion.objects.filter(Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=ss[0]) &
                                                                       Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=ss[1]), materiaasignada__materia=materia, materiaasignada__status=True, status=True, materiaasignada__retiramateria=False).order_by('materiaasignada__matricula__inscripcion__persona__apellido1', 'materiaasignada__matricula__inscripcion__persona__apellido2', 'materiaasignada__matricula__inscripcion__persona__nombres')
                    else:
                        listado = MateriaTitulacion.objects.filter(materiaasignada__materia=materia, materiaasignada__status=True, status=True, materiaasignada__retiramateria=False).order_by('materiaasignada__matricula__inscripcion__persona__apellido1', 'materiaasignada__matricula__inscripcion__persona__apellido2', 'materiaasignada__matricula__inscripcion__persona__nombres')
                    data['cronograma'] = materia.cronogramacalificaciones()
                    numerofilas = 25
                    paging = MiPaginador(listado, numerofilas)
                    p = 1
                    url_vars += "&action=listadoalumnos&idm="+request.GET['idm']
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                            if p == 1:
                                numerofilasguiente = numerofilas
                            else:
                                numerofilasguiente = numerofilas * (p - 1)
                        else:
                            p = paginasesion
                            if p == 1:
                                numerofilasguiente = numerofilas
                            else:
                                numerofilasguiente = numerofilas * (p - 1)
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['numerofilasguiente'] = numerofilasguiente
                    data['numeropagina'] = p
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    return render(request, 'adm_validarrequisitostitulacion/listaralumnos.html', data)
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Validación de Requisitos de Titulación'
                periodo = None
                coordinacion = None
                carrera = None
                periodos = None
                coordinaciones = None
                carreras = None
                coordiciones_ids = persona.mis_coordinaciones()
                data['coordinaciones'] = coordinaciones = Coordinacion.objects.filter(pk__in=coordiciones_ids, status=True).distinct().exclude(Q(id=MODULO_INGLES_ID) | Q(id=POSGRADO_EDUCACION_ID) | Q(id=MODULOS_COMPUTACION_ID) | Q(id=ADMISION_ID))
                # if 'coordinacion' in request.GET:
                #     coordinacion = Coordinacion.objects.GET(pk=int(request.GET['coordinacion']))
                # else:
                if coordinaciones.exists():
                    coordinacion = coordinaciones[0]
                data['carreras'] = carreras = Coordinacion.objects.get(pk=coordinacion.id).carreras()
                # if 'carrera' in request.GET:
                #     carrera = Carrera.objects.GET(pk=int(request.GET['carrera']))
                # else:
                if carreras.exists():
                    carrera = carreras[0]
                data['periodos'] = periodos = PeriodoGrupoTitulacion.objects.filter(status=True).order_by('-id')
                data['periodos_matriculacion'] = Periodo.objects.filter(status=True, tipo_id=2).order_by('-id')
                # if 'periodo' in request.GET:
                #     periodo = PeriodoGrupoTitulacion.objects.get(pk=int(request.GET['periodo']))
                # else:
                if periodos.exists():
                    periodo = periodos[0]

                data['periodoid'] = periodo
                data['coordinacionid'] = coordinacion
                data['carreraid'] = carreras
                ESTADOS = (
                    (1, u'APTO'),
                    (2, u'NO APTO'),
                    (3, u'NO VALIDADO'),
                    (5, u'EN REVISIÓN'),
                )
                data['estados'] = ESTADOS
                data['reporte_0'] = obtener_reporte('rpt_certificado_estar_apto_proceso_titulacion')
                data['reporte_1'] = obtener_reporte('rpt_certificado_estar_apto_titularse')
                return render(request, "adm_validarrequisitostitulacion/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect("/")

