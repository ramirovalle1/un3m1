# -*- coding: latin-1 -*-
import json
import os
import random
import sys
import zipfile
from datetime import datetime, timedelta
from shlex import join

import pandas as pd
from django.db.models.functions import ExtractMonth, ExtractYear
import pyqrcode
import xlwt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q, Count
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.template import Context
from django.template.loader import get_template
from xlwt import *

from decorators import secure_module, last_access
from sagest.funciones import formatear_cabecera_pd
from settings import SITE_STORAGE, DEBUG
from sga.commonviews import adduserdata, obtener_reporte, traerNotificaciones
from sga.excelbackground import reporte_pre_inscritos_ppp, reporte_preinscriptosexcel
from inno.models import ExtraPreInscripcionPracticasPP
from sga.forms import PracticasPreprofesionalesInscripcionForm, EvidenciaPracticasForm, ArpobarEvidenciaPracticasForm, \
    EvidenciaPracticasNormalForm, PracticasDepartamentoForm, PonerFechaLimiteEvidenciaForm, \
    AprobarRechazarSolicitudPracticaForm, OfertasPracticasForm, AperturaPracticaPreProfesionalForm, \
    FormatoPracticaPreProfesionalForm, DetalleFormatoPracticaPreProfesionalForm, EvidenciaPracticasPreProfesionalForm, \
    PeriodoEvidenciaPracticaProfesionalesForm, InformeMensualSupervisorPracticaForm, \
    ArchivoGeneralPracticaPreProfesionalesFrom, PreInscripcionPracticasPPForm, PreguntaPreInscripcionPracticasPPForm, \
    PracticasPreprofesionalesInscripcionMasivoForm, CartaVinculacionForm, DirectorVinculacionFirmaForm, \
    ConfiguracionEvidenciaHomologacionPracticaForm, DetallePreInscripcionPracticasPPForm, \
    EvidenciaHomologacionPracticaForm, ArchivoHomologacionPracticaForm, AsignacionEmpresaPracticaForm, \
    PeriodoEvidenciaPracticaProfesionalesAuxForm, CambioCarreraPracticaForm, DocumentoRequeridoPracticaForm, \
    DocumentoRequeridoCarreraForm, PracticasPreprofesionalesInscripcionSolicitarForm, FinalizarHomologacionForm, \
    SolicitudEmpresaPreinscripcionForm, ValidarSolicitudEmpresaForm, SeguimientoPreProfesionalInscripcionForm, \
    AnilladoPreProfesionalInscripcionForm, ItinerarioMallaDocenteDistributivoForm, AsignacionTutorForm, \
    AcuerdoCompromisoAsignacionTutorForm, EmpresaAsignacionTutorForm, ValidarSolicitudAsignacionTutorForm, \
    CambioCarreraPracticaConActividadForm, \
    ObservacionDecanoForm, ObservacionDirectorForm, PracticasPreprofesionalesInscripcionMasivoSaludForm, \
    PracticasPreprofesionalesInscripcionMasivoEstudianteForm, SgaImportarXLSForm, ImportarPreinscritoPPForm
from sga.funciones import log, MiPaginador, generar_nombre, convertir_fecha, notificacion, \
    remover_caracteres_especiales_unicode, get_director_vinculacion, remover_caracteres_tildes_unicode, convertirfecha2,generar_codigo
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavecartavinculacion, conviert_html_to_pdf_name_savecartavinc,\
    conviert_html_to_pdf_name_save, conviert_html_to_pdf_name
from sga.models import PracticasPreprofesionalesInscripcion, EvidenciaPracticasProfesionales, \
    DetalleEvidenciasPracticasPro, InscripcionMalla, MONTH_NAMES, TIPO_SOLICITUD_PRACTICAPRO, PracticasDepartamento, \
    RotacionesMalla, Inscripcion, Profesor, CUENTAS_CORREOS, OfertasPracticas, NivelMalla, EjeFormativo, \
    AsignaturaMalla, Malla, ItinerariosMalla, Carrera, ProfesorDistributivoHoras, AperturaPracticaPreProfesional, \
    TIPO_PRACTICA_PP, AperturaPracticaPreProfesionalDetalle, \
    FormatoPracticaPreProfesional, DetalleFormatoPracticaPreProfesional, PeriodoEvidenciaPracticaProfesionales, \
    InformeMensualSupervisorPractica, Coordinacion, CoordinadorCarrera, VisitaPractica_Detalle, ESTADO_TIPO_VISITA, \
    ESTADO_VISITA_PRACTICA, ArchivoGeneralPracticaPreProfesionales, PreInscripcionPracticasPP, \
    PreguntaPreInscripcionPracticasPP, RespuestaPreInscripcionPracticasPP, DetallePreInscripcionPracticasPP, \
    ESTADO_PREINSCRIPCIONPPP, DetalleRecoridoPreInscripcionPracticasPP, DetalleRespuestaPreInscripcionPPP, \
    ActividadDetalleDistributivoCarrera, ConvenioEmpresa, AcuerdoCompromiso, CartaVinculacionPracticasPreprofesionales, \
    DetalleCartaInscripcion, DetalleCartaItinerario, ConfiguracionFirmaPracticasPreprofesionales, \
    ConfiguracionEvidenciaHomologacionPractica, EvidenciaHomologacionPractica, InformeHomologacionCarrera, \
    AsignacionEmpresaPractica, PracticasTutoria, CabPeriodoEvidenciaPPP, InformeMensualDocentesPPP, \
    MESES_CHOICES, RequisitosHomologacionPracticas, CarreraHomologacion, CarreraHomologacionRequisitos, \
    TIPO_DOCUMENTO_HOMOLOGACION, ItinerariosMallaDocumentosBase, SolicitudHomologacionPracticas, \
    ESTADOS_PASOS_SOLICITUD, DocumentosSolicitudHomologacionPracticas, ESTADO_SOLICITUD_HOMOLOGACION, \
    ResponsableCoordinacion, ESTADO_SOLICITUD, DatosEmpresaPreInscripcionPracticasPP, ESTADO_SOLICITUD_EMPRESA, \
    FirmaPersona, SeguimientoPreProfesionalesInscripcion, EstudiantesAgendaPracticasTutoria, AgendaPracticasTutoria, \
    AnilladoPracticasPreprofesionalesInscripcion, ItinerariosActividadDetalleDistributivoCarrera, \
    SolicitudVinculacionPreInscripcionPracticasPP, ESTADO_SOLICITUD_VINCULACION_TUTOR, Provincia, Canton, Pais, \
    EmpresaEmpleadora, DetalleDistributivo, Notificacion, HistorialDocumentosSolicitudHomologacionPracticas, \
    InscripcionActividadConvalidacionPPV, \
    HistoricoRevisionesSolicitudHomologacionPracticas, Persona, ActividadConvalidacionPPV, PreinscribirMasivoHistorial
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt, encrypt_alu, docentes_practicas_estudiantes
import xlsxwriter
import io

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    persona = request.session['persona']
    coordinacion = []
    periodo = request.session['periodo']
    data = {}
    PREFIX = 'UNEMI'
    SUFFIX = 'VICEVIN-PPP'
    # data['practicasalud'] = practicasalud = request.user.has_perm('sga.puede_gestionar_practicas_salud')
    data['practicasalud'] = practicasalud = False
    if persona.es_profesor():
        coordinacion = persona.profesor().coordinacion
    if persona.id in [17579, 818, 5194, 23532, 169, 12130, 16630, 1652, 21604, 30751, 30802, 27946, 16781]:
        coordinacion = []
    miscarreras = persona.mis_carreras_tercer_nivel()
    tiene_carreras_director = True if miscarreras else False
    querydecano = ResponsableCoordinacion.objects.filter(periodo=periodo, status=True, persona=persona, tipo=1)

    es_director_carr = tiene_carreras_director if not querydecano.exists() else False

    if querydecano.exists() and tiene_carreras_director:
        es_director_carr = True

    data['es_director_carr'] = es_director_carr
    data['es_decano'] = es_decano = querydecano.exists()

    responsablevinculacion = get_director_vinculacion()

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'editarasignaciontutor':
            try:
                id, asignacion = request.POST['id'], None
                asignacion = SolicitudVinculacionPreInscripcionPracticasPP.objects.get(pk=id)
                preinscripcion = DetallePreInscripcionPracticasPP.objects.get(pk=asignacion.preinscripcion.pk)
                if 'documentoaceptacion' in request.FILES:
                    newfile = request.FILES['documentoaceptacion']
                    if newfile.size > 8194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 8 Mb."})
                    else:
                        newfilename = newfile._name
                        ext = newfilename[newfilename.rfind("."):]
                        if not ext == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                f = AsignacionTutorForm(request.POST)
                if f.is_valid():
                    asignacion.tipovinculacion = f.cleaned_data['tipovinculacion']
                    asignacion.tipopracticas = f.cleaned_data['tipopracticas']
                    asignacion.acuerdo = f.cleaned_data['acuerdo']
                    asignacion.convenio = f.cleaned_data['convenio']
                    asignacion.direccion = f.cleaned_data['direccion']
                    asignacion.empresanombre = f.cleaned_data['empresanombre']
                    asignacion.empresaruc = f.cleaned_data['empresaruc']
                    asignacion.tipoinstitucion = f.cleaned_data['tipoinstitucion']
                    asignacion.sectoreconomico = f.cleaned_data['sectoreconomico']
                    asignacion.empresatelefonos = f.cleaned_data['empresatelefonos']
                    asignacion.empresaemail = f.cleaned_data['empresaemail']
                    asignacion.empresacanton = f.cleaned_data['empresacanton']
                    asignacion.empresadireccion = f.cleaned_data['empresadireccion']
                    asignacion.dirigidoa = f.cleaned_data['dirigidoa']
                    asignacion.cargo = f.cleaned_data['cargo']
                    asignacion.telefonos = f.cleaned_data['telefonos']
                    asignacion.email = f.cleaned_data['email']
                    asignacion.ccemail = f.cleaned_data['ccemail']
                    asignacion.estado = 1
                    asignacion.save(request)
                    if 'documentoaceptacion' in request.FILES:
                        nombrepersona = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode((preinscripcion.inscripcion.persona.__str__()).replace(' ', '_')))
                        nombredocumento = '{}_{}'.format(nombrepersona, random.randint(1, 100000).__str__())
                        newfile._name = generar_nombre(nombredocumento, newfile._name)
                        asignacion.archivo = newfile
                        asignacion.fechaarchivo = datetime.now().date()
                        asignacion.horaarchivo = datetime.now().time()
                        asignacion.save(request)
                        preinscripcion.archivo = newfile
                        preinscripcion.fechaarchivo = datetime.now().date()
                        preinscripcion.horaarchivo = datetime.now().time()
                        preinscripcion.save(request)
                    log(u'Edito Solicitud de Asignación Empresa %s - %s' % (persona, asignacion), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editarsolicitudempresa':
            try:
                postar = DatosEmpresaPreInscripcionPracticasPP.objects.get(id=int(request.POST['id']))
                form = SolicitudEmpresaPreinscripcionForm(request.POST)
                if form.is_valid():
                    postar.dirigidoa = form.cleaned_data['dirigidoa']
                    postar.empresa = form.cleaned_data['empresa']
                    postar.cargo = form.cleaned_data['cargo']
                    postar.correo = form.cleaned_data['correo']
                    postar.telefono = form.cleaned_data['telefono']
                    postar.direccion = form.cleaned_data['direccion']
                    postar.save(request)
                    log(u'Edito Solicitud Empresa Preinscripción Practicas : %s %s' % (
                        postar, postar.preinscripcion.inscripcion), request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})

        if action == 'validarsolicitudempresa':
            try:
                data['filtro'] = filtro = DatosEmpresaPreInscripcionPracticasPP.objects.get(id=int(request.POST['id']))
                form = ValidarSolicitudEmpresaForm(request.POST)
                if form.is_valid():
                    filtro.est_empresas = form.cleaned_data['est_empresas']
                    filtro.observacion = form.cleaned_data['observacion']
                    filtro.fecha_revision = datetime.now()
                    filtro.persona_revision = persona
                    filtro.save(request)
                    asunto = u"GENERACIÓN DE SOLICITUD A EMPRESA"
                    para = filtro.preinscripcion.inscripcion.persona
                    notificacion(asunto, filtro.observacion, para, None, '/alu_preinscripcioppp', filtro.pk, 1, 'sga', DatosEmpresaPreInscripcionPracticasPP, request)
                    if filtro.est_empresas == '2':
                        temp = lambda x: remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(x.__str__()))
                        fecha = filtro.fecha_revision
                        data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                        template_pdf = 'alu_preinscripcionppp/solicitudpdf.html'
                        nombrepersona = temp(filtro.preinscripcion.inscripcion.persona.__str__()).replace(' ', '_')
                        nombredocumento = 'SOLICITUD_EMPRESA_{}_{}'.format(nombrepersona, random.randint(1, 100000).__str__())
                        directory = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'solicitudempresas')
                        data['url_qr'] = url_qr = f'{SITE_STORAGE}/media/qrcode/solicitudempresas/qr/{nombredocumento}.png'
                        os.makedirs(f'{directory}/qr/', exist_ok=True)
                        if responsablevinculacion:
                            data['responsablevinculacion'] = responsablevinculacion
                            firma = f'APROBADO POR: {responsablevinculacion.nombres}\nCARGO: {temp(responsablevinculacion.cargo)}\nFECHA APROBACION: {fecha.strftime("%d-%m-%Y %H:%M:%S")}\nSOLICITUD: {filtro.codigodocumento}\nESTUDIANTE:{filtro.preinscripcion.inscripcion.persona.__str__()} \nVALIDADO EN: sga.unemi.edu.ec'
                            url = pyqrcode.create(firma)
                            imageqr = url.png(f'{directory}/qr/{nombredocumento}.png', 16, '#000000')
                        valida = conviert_html_to_pdf_name_save(template_pdf, {'pagesize': 'A4', 'data': data, }, nombredocumento)
                        if valida:
                            filtro.archivodescargar = 'qrcode/solicitudempresas/' + nombredocumento + '.pdf'
                            filtro.save(request)
                    if filtro.est_empresas == '3':
                        filtro.archivodescargar = ''
                        filtro.save(request)
                    log(u'Valido Solicitud Empresa Preinscripción Practicas : %s %s' % (filtro, filtro.preinscripcion.inscripcion), request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})

        if action == 'validarsolicitudasignaciontutor':
            try:
                filtro = SolicitudVinculacionPreInscripcionPracticasPP.objects.get(id=int(request.POST['id']))
                form = ValidarSolicitudAsignacionTutorForm(request.POST)
                if form.is_valid():
                    preins = DetallePreInscripcionPracticasPP.objects.get(status=True, pk=filtro.preinscripcion.pk)
                    estado_solicitud = form.cleaned_data['estado']
                    if estado_solicitud == 3:
                        # ACEPTADO
                        preins.tipo = filtro.tipopracticas
                        preins.fechadesde = form.cleaned_data['fechadesde']
                        preins.fechahasta = form.cleaned_data['fechahasta']
                        preins.numerohora = form.cleaned_data['numerohora']
                        preins.tutorunemi_id = int(request.POST['tutorunemi']) if form.cleaned_data['tutorunemi'] else None
                        preins.supervisor_id = int(request.POST['supervisor']) if form.cleaned_data['supervisor'] else None
                        preins.departamento = form.cleaned_data['departamento']
                        preins.periodoppp = form.cleaned_data['periodoevidencia']
                        if filtro.tipovinculacion == 2:
                            preins.convenio = filtro.convenio
                        elif filtro.tipovinculacion == 1:
                            preins.acuerdo = filtro.acuerdo
                        elif filtro.tipovinculacion == 4:
                            # UNEMI
                            pass
                        preins.estado = 5
                        preins.save(request)
                        recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins, fecha=datetime.now().date(), observacion=form.cleaned_data['observacion'], estado=5)
                        recorrido.save(request)

                        # APROBAR LA PRACTICA
                        practa = PracticasPreprofesionalesInscripcion(preinscripcion=preins,
                                                                      inscripcion=preins.inscripcion,
                                                                      nivelmalla=preins.nivelmalla,
                                                                      itinerariomalla=preins.itinerariomalla if preins.itinerariomalla else None,
                                                                      tipo=preins.tipo,
                                                                      fechadesde=preins.fechadesde,
                                                                      fechahasta=preins.fechahasta,
                                                                      tutorunemi=preins.tutorunemi if preins.tutorunemi else None,
                                                                      supervisor=preins.supervisor if preins.supervisor else None,
                                                                      numerohora=preins.numerohora,
                                                                      tiposolicitud=1,
                                                                      acuerdo=preins.acuerdo,
                                                                      convenio=preins.convenio,
                                                                      lugarpractica=preins.lugarpractica,
                                                                      asignacionempresapractica=form.cleaned_data['asignacionempresapractica'],
                                                                      empresaempleadora=preins.empresaempleadora if preins.empresaempleadora else None,
                                                                      otraempresaempleadora=preins.otraempresaempleadora,
                                                                      tipoinstitucion=preins.tipoinstitucion if preins.tipoinstitucion else None,
                                                                      sectoreconomico=preins.sectoreconomico if preins.sectoreconomico else None,
                                                                      departamento=preins.departamento if preins.departamento else None,
                                                                      periodoppp=preins.periodoppp if preins.periodoppp else None,
                                                                      fechaasigtutor=datetime.now().date(),
                                                                      observacion=form.cleaned_data['observacion'],
                                                                      estadosolicitud=2,
                                                                      fechaasigsupervisor=datetime.now().date())
                        practa.save(request)
                        log(u'Asignación de tutor para %s  a la empresa: %s' % (preins.inscripcion, preins.empresaempleadora if preins.empresaempleadora else preins.otraempresaempleadora), request, "add")
                        # CORREOS
                        emailestudiante = preins.inscripcion.persona.lista_emails_envio()
                        estudiante = preins.inscripcion.persona.nombre_completo_inverso()
                        if form.cleaned_data['tutorunemi']:
                            idprof = int(form.cleaned_data['tutorunemi'].id)
                            profesor1 = Profesor.objects.get(pk=idprof)
                            asunto = u"ASIGNACIÓN TUTOR ACADÉMICO PRÁCTICAS PREPROFESIONALES "
                            para = profesor1.persona
                            observacion = 'Se le comunica que ha sido designado como tutor académico a (el/la) estudiante: {} de la carrera: {}'.format(estudiante, preins.inscripcion.carrera)
                            notificacion(asunto, observacion, para, None, '/pro_cronograma?action=listatutorias', preins.pk, 1, 'sga', DetallePreInscripcionPracticasPP, request)
                        if form.cleaned_data['supervisor']:
                            idprof = int(form.cleaned_data['supervisor'])
                            profesor1 = Profesor.objects.get(pk=idprof)
                            asunto = u"ASIGNACIÓN SUPERVISOR ACADÉMICO PRÁCTICAS PREPROFESIONALES "
                            para = profesor1.persona
                            observacion = 'Se le comunica que ha sido designado como supervisor académico a (el/la) estudiante: {} de la carrera: {}'.format(estudiante, preins.inscripcion.carrera)
                            notificacion(asunto, observacion, para, None, '/pro_cronograma?action=listasupervision', preins.pk, 1, 'sga', DetallePreInscripcionPracticasPP, request)
                        asunto = u"Asignación de cupo para Prácticas Preprofesionales"
                        send_html_mail(asunto, "emails/asignacion_cupo_practica.html", {'sistema': request.session['nombresistema'], 'estudiante': estudiante}, emailestudiante, [], cuenta=CUENTAS_CORREOS[4][1])
                        log(u'Asignó la pre inscripción: %s a la práctica pre profesional: %s' % (preins, preins), request, "add")
                        # CORREOS
                    elif estado_solicitud == 2:
                        recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins, fecha=datetime.now().date(), observacion=form.cleaned_data['observacion'], estado=3)
                        recorrido.save(request)
                        log(u'Solicitud de Asignación Tutor Rechazada: %s' % preins, request, "rech")
                        preins.estado = 3
                    preins.save(request)
                    filtro.estado = estado_solicitud
                    filtro.observacion = form.cleaned_data['observacion']
                    filtro.save(request)
                    log(u'Valido Solicitud Empresa Preinscripción Practicas : %s %s' % (filtro, filtro.preinscripcion.inscripcion), request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})

        if action == 'delsolicitud':
            try:
                with transaction.atomic():
                    instancia = DatosEmpresaPreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Solicitud: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'delsolicitudasignacion':
            try:
                with transaction.atomic():
                    instancia = SolicitudVinculacionPreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Solicitud de Asignación: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addrequisitoscarrera':
            try:
                with transaction.atomic():
                    form = DocumentoRequeridoCarreraForm(request.POST)
                    if form.is_valid():
                        pk = request.POST['id']
                        itinerario = request.POST['itinerario']
                        tipo = request.POST['tipo']
                        carrera = CarreraHomologacion.objects.get(pk=int(pk))
                        for dc in form.cleaned_data['documento']:
                            filtro = CarreraHomologacionRequisitos(carrera=carrera, documento=dc, tipo=tipo,
                                                                   itinerario_id=itinerario)
                            filtro.save(request)
                            log(u'Adiciono Requisito Carrera Homologación: %s' % filtro, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'adddocumento':
            try:
                with transaction.atomic():
                    form = DocumentoRequeridoPracticaForm(request.POST, request.FILES)
                    if form.is_valid():
                        filtro = RequisitosHomologacionPracticas(nombre=form.cleaned_data['nombre'].upper(),
                                                                 leyenda=form.cleaned_data['leyenda'])
                        filtro.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre(filtro.nombre_input(), newfile._name)
                            filtro.archivo = newfile
                            filtro.save(request)
                        log(u'Adiciono Documento de Homologación: %s' % filtro, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editdocumento':
            try:
                with transaction.atomic():
                    filtro = RequisitosHomologacionPracticas.objects.get(pk=request.POST['id'])
                    f = DocumentoRequeridoPracticaForm(request.POST, request.FILES)
                    if f.is_valid():
                        filtro.nombre = f.cleaned_data['nombre'].upper()
                        filtro.leyenda = f.cleaned_data['leyenda']
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre(filtro.nombre_input(), newfile._name)
                            filtro.archivo = newfile
                        filtro.save(request)
                        log(u'Modificó Documento Requerido Homologación: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'deletedocumento':
            try:
                with transaction.atomic():
                    instancia = RequisitosHomologacionPracticas.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Documento Requerido Homologación: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'deletecarrera':
            try:
                with transaction.atomic():
                    instancia = CarreraHomologacion.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Carrera Homologación: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'deletedocumentocarrera':
            try:
                with transaction.atomic():
                    instancia = CarreraHomologacionRequisitos.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Carrera Requisito Documento Homologación: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'eliminarmasivopreinscripcion':
            try:
                with transaction.atomic():
                    id = int(request.POST['id'])
                    carrera_id = int(request.POST['carrera'])
                    estado = int(request.POST['estado'])
                    descripcion = request.POST['descripcion']
                    preinscripcion = PreInscripcionPracticasPP.objects.get(status=True, pk=id)
                    preinscripciones = preinscripcion.detallepreinscripcionpracticaspp_set.filter(status=True,
                                                                                                  estado=estado,
                                                                                                  inscripcion__carrera__id=carrera_id)
                    for ps in preinscripciones:
                        ps.retiradomasivo = True
                        ps.status = False
                        ps.detallemasivo = descripcion
                        ps.usermasivo = request.user
                        ps.fechamasivo = datetime.now()
                        ps.horamasivo = datetime.now().time()
                        ps.save(request)
                        log(u'Elimino de forma masiva pre incripción: %s' % ps, request, "delete")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editcantidad':
            try:
                with transaction.atomic():
                    id = request.POST['id']
                    valoractual = int(request.POST['value'])
                    valoranterior = ActividadDetalleDistributivoCarrera.objects.get(pk=id)
                    bandera = True
                    if valoranterior.alumnosxhoras == valoractual:
                        bandera = False
                        return JsonResponse({'error': True, "message": 'EL valor es el mismo, cambio no aplicado'},
                                            safe=False)
                    if bandera:
                        filtro = ActividadDetalleDistributivoCarrera.objects.get(pk=id)
                        filtro.alumnosxhoras = valoractual
                        filtro.save(request)
                        log(u'Edito cantidad de alumno por hora en distributivo docente: %s' % filtro, request, "edit")
                        icono = '<i class="{} tb" title="{}"></i>'.format(filtro.get_estado_disponibilidad(),
                                                                          filtro.get_estado_disponibilidad_txt())
                        color = '#ffffff'
                        if filtro.get_estado_disponibilidad_int() == 0:
                            color = '#EAFAF1'
                        elif filtro.get_estado_disponibilidad_int() == 2:
                            color = '#FDEDEC'
                        res_json = {"error": False, 'icono': icono, 'totalxhora': filtro.total_alumnos_x_hora(),
                                    'totaldisponible': filtro.get_disponbile(), 'pk': filtro.pk, 'color': color}
            except Exception as ex:
                res_json = {'error': True, "message": str(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'moverevidencia':
            try:
                with transaction.atomic():
                    evidencia_principal = EvidenciaPracticasProfesionales.objects.get(pk=int(request.POST['id']))
                    evidencia_destino = EvidenciaPracticasProfesionales.objects.get(pk=int(request.POST['movera']))
                    documentos_principal = evidencia_principal.lista_archivos()
                    for d in documentos_principal:
                        evidencia_anterior = d.evidencia.pk
                        d.idevidencia_anterior = evidencia_anterior
                        d.evidencia = evidencia_destino
                        d.save(request)
                    log(u'Movio Evidencias de Practicas Preprofesionales %s - %s' % (
                        evidencia_principal, evidencia_destino), request, "add")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'add':
            try:
                f = PracticasPreprofesionalesInscripcionForm(request.POST)
                f.agg_faltantes(request.POST)
                if f.is_valid():
                    if f.cleaned_data['tutorunemi']:
                        tutoruniversidad = f.cleaned_data['tutorunemi'].id
                        fechatutor = datetime.now().date()
                    else:
                        tutoruniversidad = None
                        fechatutor = None
                    if f.cleaned_data['supervisor']:
                        supervisor = int(f.cleaned_data['supervisor'])
                        fechasupervisor = datetime.now().date()
                    else:
                        supervisor = None
                        fechasupervisor = None
                    if f.cleaned_data['rotacion']:
                        rotacion = f.cleaned_data['rotacion']
                    else:
                        rotacion = None
                    if f.cleaned_data['convenio']:
                        convenio = f.cleaned_data['convenio']
                    else:
                        convenio = None
                    if f.cleaned_data['acuerdo']:
                        acuerdo = f.cleaned_data['acuerdo']
                    else:
                        acuerdo = None
                    if f.cleaned_data['lugarpractica']:
                        lugarpractica = f.cleaned_data['lugarpractica']
                    else:
                        lugarpractica = None
                    inscripcion = Inscripcion.objects.get(pk=int(f.cleaned_data['inscripcion']))
                    if int(f.cleaned_data['tipo']) == 1 and int(f.cleaned_data['tiposolicitud']) == 3:
                        fechadesde = None
                        fechahasta = None
                    else:
                        fechahasta = f.cleaned_data['fechahasta']
                        fechadesde = f.cleaned_data['fechadesde']
                    mConvenio = None
                    mAcuerdo = None
                    if convenio:
                        mConvenio = ConvenioEmpresa.objects.get(id=convenio.id)
                    elif acuerdo:
                        mAcuerdo = AcuerdoCompromiso.objects.get(id=acuerdo.id)
                    practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion(inscripcion=inscripcion,
                                                                                                nivelmalla=
                                                                                                f.cleaned_data[
                                                                                                    'nivelmalla'],
                                                                                                tipo=f.cleaned_data[
                                                                                                    'tipo'],
                                                                                                fechadesde=fechadesde,
                                                                                                tiposolicitud=
                                                                                                f.cleaned_data[
                                                                                                    'tiposolicitud'],
                                                                                                acuerdo=mAcuerdo,
                                                                                                convenio=mConvenio,
                                                                                                lugarpractica=lugarpractica,
                                                                                                rotacionmalla=rotacion,
                                                                                                culminada=
                                                                                                f.cleaned_data[
                                                                                                    'culminada'],
                                                                                                fechahasta=fechahasta,
                                                                                                tutorunemi_id=tutoruniversidad,
                                                                                                supervisor_id=supervisor,
                                                                                                tutorempresa=
                                                                                                f.cleaned_data[
                                                                                                    'tutorempresa'],
                                                                                                numerohora=
                                                                                                f.cleaned_data[
                                                                                                    'numerohora'],
                                                                                                horahomologacion=
                                                                                                f.cleaned_data[
                                                                                                    'horahomologacion'],
                                                                                                # institucion=f.cleaned_data['institucion'],
                                                                                                tipoinstitucion=
                                                                                                f.cleaned_data[
                                                                                                    'tipoinstitucion'],
                                                                                                sectoreconomico=
                                                                                                f.cleaned_data[
                                                                                                    'sectoreconomico'],
                                                                                                observacion=
                                                                                                f.cleaned_data[
                                                                                                    'observacion'],
                                                                                                periodoppp=
                                                                                                f.cleaned_data[
                                                                                                    'periodoevidencia'],
                                                                                                fechaasigtutor=fechatutor,
                                                                                                fechaasigsupervisor=fechasupervisor,
                                                                                                departamento=
                                                                                                f.cleaned_data[
                                                                                                    'departamento'],
                                                                                                empresaempleadora=
                                                                                                f.cleaned_data[
                                                                                                    'empresaempleadora'],
                                                                                                otraempresaempleadora=
                                                                                                f.cleaned_data[
                                                                                                    'otraempresaempleadora']
                                                                                                )
                    if f.cleaned_data['culminada']:
                        practicaspreprofesionalesinscripcion.estadosolicitud = 2
                    practicaspreprofesionalesinscripcion.save(request)
                    if int(f.cleaned_data['tipo']) == 1 or int(f.cleaned_data['tipo']) == 2:
                        malla = inscripcion.mi_malla()
                        nivel = inscripcion.mi_nivel().nivel
                        if ItinerariosMalla.objects.values('id').filter(malla=malla, nivel__id__lte=nivel.id,
                                                                        status=True).exists():
                            if not f.cleaned_data['itinerario']:
                                return JsonResponse({"result": "bad", "mensaje": u"Seleccione un itinerario."})
                            itinerario = ItinerariosMalla.objects.filter(pk=f.cleaned_data['itinerario'].id,
                                                                         malla=malla, nivel__id__lte=nivel.id,
                                                                         status=True)
                            if itinerario:
                                practicaspreprofesionalesinscripcion.itinerariomalla = f.cleaned_data['itinerario']
                                practicaspreprofesionalesinscripcion.save(request)
                            else:
                                if nivel.id < 5:
                                    return JsonResponse(
                                        {"result": "bad", "mensaje": u"Para solicitar debes haber pasado el 5 nivel."})
                    if f.cleaned_data['tutorunemi']:
                        practicaspreprofesionalesinscripcion.tutorunemi_id = idprof = int(
                            f.cleaned_data['tutorunemi'].id)
                        profesor1 = Profesor.objects.get(pk=idprof)
                        emailprofesor = profesor1.persona.lista_emails_envio()
                        profesor = profesor1.persona.nombre_completo_inverso()
                        emailestudiante = practicaspreprofesionalesinscripcion.inscripcion.persona.lista_emails_envio()
                        estudiante = practicaspreprofesionalesinscripcion.inscripcion.persona.nombre_completo_inverso()
                        carrera = practicaspreprofesionalesinscripcion.inscripcion.carrera
                        asunto = u"ASIGNACIÓN TUTOR ACADÉMICO"
                        send_html_mail(asunto, "emails/tutor_practicas.html",
                                       {'sistema': request.session['nombresistema'],
                                        'profesor': profesor,
                                        'estudiante': estudiante,
                                        'carrera': carrera}, emailprofesor
                                       , [], cuenta=CUENTAS_CORREOS[4][1])
                        send_html_mail(asunto, "emails/tutor_practicas_alumno.html",
                                       {'sistema': request.session['nombresistema'],
                                        'profesor': profesor,
                                        'estudiante': estudiante}, emailestudiante
                                       , [], cuenta=CUENTAS_CORREOS[4][1])
                    if f.cleaned_data['supervisor']:
                        practicaspreprofesionalesinscripcion.supervisor_id = idprof = int(f.cleaned_data['supervisor'])
                        profesor1 = Profesor.objects.get(pk=idprof)
                        email = profesor1.persona.lista_emails_envio()
                        profesor = profesor1.persona.nombre_completo_inverso()
                        emailestudiante = practicaspreprofesionalesinscripcion.inscripcion.persona.lista_emails_envio()
                        estudiante = practicaspreprofesionalesinscripcion.inscripcion.persona.nombre_completo_inverso()
                        carrera = practicaspreprofesionalesinscripcion.inscripcion.carrera
                        asunto = u"ASIGNACIÓN SUPERVISOR ACADÉMICO"
                        send_html_mail(asunto, "emails/supervisor_practicas.html",
                                       {'sistema': request.session['nombresistema'],
                                        'profesor': profesor,
                                        'estudiante': estudiante,
                                        'carrera': carrera}, email
                                       , [], cuenta=CUENTAS_CORREOS[4][1])
                        send_html_mail(asunto, "emails/supervisor_practicas_alumno.html",
                                       {'sistema': request.session['nombresistema'],
                                        'profesor': profesor,
                                        'estudiante': estudiante}, emailestudiante
                                       , [], cuenta=CUENTAS_CORREOS[4][1])
                    log(u'Adicionado practica preprofesionales inscripcion: %s' % practicaspreprofesionalesinscripcion,
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                practicas = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.POST['id']))
                log(u'Eliminó practica preprofesionales inscripcion: %s' % practicas, request, "del")
                practicas.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'deletetutoracademico':
            try:
                practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.get(
                    pk=request.POST['id'])
                practicaspreprofesionalesinscripcion.tutorunemi_id = None
                practicaspreprofesionalesinscripcion.save(request)
                log(u'Elimino tutor academico: %s %s' % (
                    practicaspreprofesionalesinscripcion.inscripcion, practicaspreprofesionalesinscripcion.id), request,
                    "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'eliminasupervisor':
            try:
                practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.get(
                    pk=request.POST['id'])
                practicaspreprofesionalesinscripcion.supervisor_id = None
                practicaspreprofesionalesinscripcion.save(request)
                log(u'Elimino supervisor académico: %s %s' % (
                    practicaspreprofesionalesinscripcion.inscripcion, practicaspreprofesionalesinscripcion.id), request,
                    "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.get(pk=request.POST['id'])
                f = PracticasPreprofesionalesInscripcionForm(request.POST)
                f.agg_faltantes(request.POST)
                f.desbloquear()
                if f.is_valid():
                    if int(f.cleaned_data['tipo']) == 1 and int(f.cleaned_data['tiposolicitud']) == 3:
                        fechadesde = None
                        fechahasta = None
                    else:
                        fechadesde = f.cleaned_data['fechadesde']
                        fechahasta = f.cleaned_data['fechahasta']
                    mAcuerdo = None
                    mConvenio = None
                    if f.cleaned_data['acuerdo']:
                        mAcuerdo = f.cleaned_data['acuerdo']
                        practicaspreprofesionalesinscripcion.otraempresaempleadora = ''
                        practicaspreprofesionalesinscripcion.empresaempleadora = f.cleaned_data['empresaempleadora']
                    elif f.cleaned_data['convenio']:
                        mConvenio = f.cleaned_data['convenio']
                        practicaspreprofesionalesinscripcion.otraempresaempleadora = ''
                        practicaspreprofesionalesinscripcion.empresaempleadora = f.cleaned_data['empresaempleadora']
                    practicaspreprofesionalesinscripcion.nivelmalla = f.cleaned_data['nivelmalla']
                    practicaspreprofesionalesinscripcion.fechadesde = fechadesde
                    practicaspreprofesionalesinscripcion.fechahasta = fechahasta
                    practicaspreprofesionalesinscripcion.tipo = f.cleaned_data['tipo']
                    practicaspreprofesionalesinscripcion.culminada = f.cleaned_data['culminada']
                    practicaspreprofesionalesinscripcion.acuerdo = mAcuerdo
                    practicaspreprofesionalesinscripcion.convenio = mConvenio
                    practicaspreprofesionalesinscripcion.lugarpractica = f.cleaned_data['lugarpractica']
                    practicaspreprofesionalesinscripcion.departamento = f.cleaned_data['departamento']
                    practicaspreprofesionalesinscripcion.asignacionempresapractica = f.cleaned_data['asignacionempresapractica']
                    practicaspreprofesionalesinscripcion.empresaempleadora = f.cleaned_data['empresaempleadora']
                    practicaspreprofesionalesinscripcion.otraempresaempleadora = f.cleaned_data['otraempresaempleadora']
                    practicaspreprofesionalesinscripcion.horahomologacion = f.cleaned_data['horahomologacion']

                    # ACTUALIZAR EVIDENCIAS PRACTICAS
                    # detalleevidenciapracticas = practicaspreprofesionalesinscripcion.detalleevidenciaspracticaspro_set.all()
                    # evperiodo = EvidenciaPracticasProfesionales.objects.filter(status=True, periodoevidencia=f.cleaned_data['periodoevidencia']).order_by('orden')
                    # for d in detalleevidenciapracticas:
                    #     evidencia = EvidenciaPracticasProfesionales.objects.get(pk=d.evidencia.pk)
                    #     evidencia.periodoevidencia = f.cleaned_data['periodoevidencia']
                    #     evidencia.save(request)

                    practicaspreprofesionalesinscripcion.periodoppp = f.cleaned_data['periodoevidencia']

                    if f.cleaned_data['culminada']:
                        practicaspreprofesionalesinscripcion.estadosolicitud = 2
                    if f.cleaned_data['rotacion']:
                        practicaspreprofesionalesinscripcion.rotacionmalla = f.cleaned_data['rotacion']
                    # if not practicaspreprofesionalesinscripcion.vigente:
                    practicaspreprofesionalesinscripcion.numerohora = f.cleaned_data['numerohora']
                    # else:
                    #     practicaspreprofesionalesinscripcion.numerohora = None
                    practicaspreprofesionalesinscripcion.tiposolicitud = int(f.cleaned_data['tiposolicitud'])
                    # if f.cleaned_data['empresaempleadora']:
                    #     practicaspreprofesionalesinscripcion.empresaempleadora_id = f.cleaned_data['empresaempleadora']
                    # else:
                    #     practicaspreprofesionalesinscripcion.empresaempleadora_id = None
                    #     if f.cleaned_data['otraempresaempleadora']:
                    #         practicaspreprofesionalesinscripcion.otraempresa = True
                    if f.cleaned_data['tutorunemi']:
                        idanterior = practicaspreprofesionalesinscripcion.tutorunemi.id if practicaspreprofesionalesinscripcion.tutorunemi else None
                        if (not idanterior) or (int(f.cleaned_data['tutorunemi'].id) != idanterior):
                            fechatutor = datetime.now().date()
                            practicaspreprofesionalesinscripcion.tutorunemi_id = idprof = int(
                                f.cleaned_data['tutorunemi'].id)
                            profesor1 = Profesor.objects.get(pk=idprof)
                            email = profesor1.persona.lista_emails_envio()
                            profesor = profesor1.persona.nombre_completo_inverso()
                            estudiante = practicaspreprofesionalesinscripcion.inscripcion.persona.nombre_completo_inverso()
                            emailestudiante = practicaspreprofesionalesinscripcion.inscripcion.persona.lista_emails_envio()
                            carrera = practicaspreprofesionalesinscripcion.inscripcion.carrera
                            asunto = u"ASIGNACIÓN TUTOR ACADÉMICO"
                            send_html_mail(asunto, "emails/tutor_practicas.html",
                                           {'sistema': request.session['nombresistema'],
                                            'profesor': profesor,
                                            'estudiante': estudiante,
                                            'carrera': carrera},
                                           email
                                           , [], cuenta=CUENTAS_CORREOS[4][1])
                            send_html_mail(asunto, "emails/tutor_practicas_alumno.html",
                                           {'sistema': request.session['nombresistema'],
                                            'profesor': profesor,
                                            'estudiante': estudiante}, emailestudiante
                                           , [], cuenta=CUENTAS_CORREOS[4][1])

                            idprof = int(f.cleaned_data['tutorunemi'].id)
                            profesor1 = Profesor.objects.get(pk=idprof)
                            asunto = u"ASIGNACIÓN TUTOR ACADÉMICO PRÁCTICAS PREPROFESIONALES"
                            para = profesor1.persona
                            observacion = 'Se le comunica que ha sido designado como tutor académico a (el/la) estudiante: {} de la carrera: {}'.format(
                                estudiante, carrera)
                            notificacion(asunto, observacion, para, None, '/pro_cronograma?action=listatutorias',
                                         practicaspreprofesionalesinscripcion.pk, 1, 'sga',
                                         DetallePreInscripcionPracticasPP, request)
                        else:
                            fechatutor = None
                    else:
                        fechatutor = None
                        practicaspreprofesionalesinscripcion.tutorunemi=None
                    if f.cleaned_data['supervisor']:
                        idanterior = practicaspreprofesionalesinscripcion.supervisor.id if practicaspreprofesionalesinscripcion.supervisor else None
                        if (not idanterior) or (int(f.cleaned_data['supervisor']) != idanterior):
                            practicaspreprofesionalesinscripcion.supervisor_id = idprof = int(
                                f.cleaned_data['supervisor'])
                            fechasupervisor = datetime.now().date()
                            profesor1 = Profesor.objects.get(pk=idprof)
                            email = profesor1.persona.lista_emails_envio()
                            profesor = profesor1.persona.nombre_completo_inverso()
                            estudiante = practicaspreprofesionalesinscripcion.inscripcion.persona.nombre_completo_inverso()
                            emailestudiante = practicaspreprofesionalesinscripcion.inscripcion.persona.lista_emails_envio()
                            carrera = practicaspreprofesionalesinscripcion.inscripcion.carrera
                            asunto = u"ASIGNACIÓN SUPERVISOR ACADÉMICO"
                            send_html_mail(asunto, "emails/supervisor_practicas.html",
                                           {'sistema': request.session['nombresistema'],
                                            'profesor': profesor,
                                            'estudiante': estudiante,
                                            'carrera': carrera}, email
                                           , [], cuenta=CUENTAS_CORREOS[4][1])
                            send_html_mail(asunto, "emails/supervisor_practicas_alumno.html",
                                           {'sistema': request.session['nombresistema'],
                                            'profesor': profesor,
                                            'estudiante': estudiante}, emailestudiante
                                           , [], cuenta=CUENTAS_CORREOS[4][1])
                            idprof = int(f.cleaned_data['supervisor'])
                            profesor1 = Profesor.objects.get(pk=idprof)
                            asunto = u"ASIGNACIÓN SUPERVISOR ACADÉMICO PRÁCTICAS PREPROFESIONALES"
                            para = profesor1.persona
                            observacion = 'Se le comunica que ha sido designado como supervisor académico a (el/la) estudiante: {} de la carrera: {}'.format(
                                estudiante, carrera)
                            notificacion(asunto, observacion, para, None, '/pro_cronograma?action=listasupervision',
                                         practicaspreprofesionalesinscripcion.pk, 1, 'sga',
                                         DetallePreInscripcionPracticasPP, request)



                        else:
                            fechasupervisor = None
                    else:
                        fechasupervisor = None
                    practicaspreprofesionalesinscripcion.tutorempresa = f.cleaned_data['tutorempresa']
                    # practicaspreprofesionalesinscripcion.institucion = f.cleaned_data['institucion']
                    practicaspreprofesionalesinscripcion.tipoinstitucion = f.cleaned_data['tipoinstitucion']
                    practicaspreprofesionalesinscripcion.sectoreconomico = f.cleaned_data['sectoreconomico']
                    practicaspreprofesionalesinscripcion.observacion = f.cleaned_data['observacion']
                    practicaspreprofesionalesinscripcion.fechaasigtutor = fechatutor
                    practicaspreprofesionalesinscripcion.fechaasigsupervisor = fechasupervisor
                    if int(f.cleaned_data['tipo']) == 1 or int(f.cleaned_data['tipo']) == 2:
                        malla = practicaspreprofesionalesinscripcion.inscripcion.mi_malla()
                        nivel = practicaspreprofesionalesinscripcion.inscripcion.mi_nivel().nivel
                        if ItinerariosMalla.objects.values('id').filter(malla=malla, nivel__id__lte=nivel.id,
                                                                        status=True).exists():
                            # if not f.cleaned_data['itinerario']:
                            #     return JsonResponse({"result": "bad", "mensaje": u"Seleccione un itinerario."})
                            # itinerario = ItinerariosMalla.objects.filter(pk=f.cleaned_data['itinerario'].id, malla=malla, nivel__id__lte=nivel.id)
                            # if itinerario:
                            practicaspreprofesionalesinscripcion.itinerariomalla = f.cleaned_data['itinerario']
                            # else:
                            #     if nivel.id <= 5:
                            #         return JsonResponse({"result": "bad", "mensaje": u"Para solicitar debe tener aprobado 5 nivel."})
                    else:
                        practicaspreprofesionalesinscripcion.itinerariomalla = None
                    practicaspreprofesionalesinscripcion.save(request)
                    log(u'Actualizo practica preprofesionales inscripcion: %s %s' % (
                        practicaspreprofesionalesinscripcion.inscripcion, practicaspreprofesionalesinscripcion.id),
                        request,
                        "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError(f.errors)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {ex}"})

        if action == 'editcarrera':
            try:
                practica = PracticasPreprofesionalesInscripcion.objects.get(pk=request.POST['id'])
                f = CambioCarreraPracticaForm(request.POST)
                if f.is_valid():
                    inscripciondestino = Inscripcion.objects.get(persona=practica.inscripcion.persona,
                                                                 status=True,
                                                                 perfilusuario__status=True,
                                                                 perfilusuario__visible=True,
                                                                 carrera=f.cleaned_data['carreradestino'])

                    practica.inscripcionant = practica.inscripcion
                    practica.itinerariomallaant = practica.itinerariomalla
                    practica.itinerariomalla = f.cleaned_data['itinerariodestino']
                    practica.inscripcion = inscripciondestino
                    practica.save(request)

                    log(u'%s cambió carrera e itinerario a la práctica [ %s ] de %s a %s' % (
                        persona, practica, practica.inscripcionant.carrera, practica.inscripcion.carrera), request,
                        "edit")

                    return JsonResponse({"result": "ok"})
                else:
                    errorformulario = f._errors
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editcarrera_actividad':
            try:
                practica = PracticasPreprofesionalesInscripcion.objects.get(pk=request.POST['id'])
                f = CambioCarreraPracticaConActividadForm(request.POST)
                if f.is_valid():
                    inscrip_actividad = InscripcionActividadConvalidacionPPV.objects.get(inscripcion__persona_id=practica.inscripcion.persona.id, actividad_id=practica.actividad.id, status=True)

                    inscripciondestino = Inscripcion.objects.get(persona=practica.inscripcion.persona,
                                                                 status=True,
                                                                 perfilusuario__status=True,
                                                                 perfilusuario__visible=True,
                                                                 carrera=f.cleaned_data['carreradestino'])

                    inscrip_actividad.inscrip_old = inscrip_actividad.inscripcion
                    inscrip_actividad.inscripcion = inscripciondestino

                    practica.inscripcionant = practica.inscripcion
                    practica.itinerariomallaant = practica.itinerariomalla
                    practica.itinerariomalla = f.cleaned_data['itinerariodestino']
                    practica.inscripcion = inscripciondestino

                    inscrip_actividad.save(request)
                    practica.save(request)

                    log(u'%s cambió carrera e itinerario a la práctica [ %s ] de %s a %s' % (
                        persona, practica, practica.inscripcionant.carrera, practica.inscripcion.carrera), request,
                        "edit")

                    return JsonResponse({"result": "ok"})
                else:
                    errorformulario = f._errors
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editfecha':
            try:
                id = request.POST['id']
                valor = request.POST['valor']
                fecha_ = convertirfecha2(valor) + timedelta(days=1)
                practica = PracticasPreprofesionalesInscripcion.objects.get(id=id)
                practica.fechadesde = fecha_
                practica.save(request)
                log(u'Modificó fecha de inicio de practicas : %s' % practica, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as e:
                print(e)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": str(e)})

        if action == 'editfecha2':
            try:
                id = request.POST['id']
                valor = request.POST['valor']
                fecha_ = convertirfecha2(valor) + timedelta(days=1)
                practica = PracticasPreprofesionalesInscripcion.objects.get(id=id)
                practica.fechahasta = fecha_
                practica.save(request)
                log(u'Modificó fecha de inicio de practicas : %s' % practica, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as e:
                print(e)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": str(e)})


        if action == 'editobspracticasupdate':
            try:
                practicas = PracticasPreprofesionalesInscripcion.objects.get(pk=request.POST['idpracticas'],
                                                                             status=True)
                practicas.obseaprueba = request.POST['codigoobservacion']
                practicas.fechaaprueba = datetime.now()
                practicas.estadosolicitud = request.POST['estadoid']
                practicas.personaaprueba = persona
                practicas.save(request)
                mensaje = ''
                if practicas.estadosolicitud == '2':
                    mensaje = u"APROBÓ"
                if practicas.estadosolicitud == '3':
                    mensaje = u"RECHAZÓ"
                if practicas.estadosolicitud == '4':
                    mensaje = u"PENDIENTE"
                asunto = u"NOTIFICACION DE SOLICITUD"
                send_html_mail(asunto, "emails/aprobacion_solicitudpracpreprofesionales.html",
                               {'sistema': request.session['nombresistema'], 'alumno': practicas.inscripcion.persona},
                               practicas.inscripcion.persona.lista_emails_envio(), [],
                               cuenta=CUENTAS_CORREOS[0][1])
                log(
                    u'Actualizo preprofesionales observacion aprueba,rechaza o estado pendiente inscripcion: %s estado: %s %s' % (
                        practicas.id, mensaje, practicas), request, mensaje)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'aprobarrechazarsolicitud':
            try:
                f = AprobarRechazarSolicitudPracticaForm(request.POST)
                if f.is_valid():
                    practicas = PracticasPreprofesionalesInscripcion.objects.get(pk=request.POST['idpracticas'],
                                                                                 status=True)
                    practicas.obseaprueba = f.cleaned_data['observacion']
                    practicas.fechaaprueba = datetime.now()
                    practicas.estadosolicitud = f.cleaned_data['estadosolicitud']
                    practicas.validacion = f.cleaned_data['validacion']
                    practicas.fechavalidacion = f.cleaned_data['fechavalidacion']
                    if f.cleaned_data['retirado'] or practicas.retirado:
                        practicas.fechahastapenalizacionretiro = f.cleaned_data['fechahastapenalizacionretiro']
                        practicas.retirado = f.cleaned_data['retirado']
                        log(
                            u'Actualizo practicas preprofesionales retirado o no de practica: %s fecha de penalizacion: %s en la practica: %s [%s]' % (
                                'retirado' if f.cleaned_data['retirado'] else 'no retirado',
                                practicas.fechahastapenalizacionretiro, practicas, practicas.id), request, 'edit')
                    practicas.personaaprueba = persona
                    practicas.save(request)
                    mensaje = ''
                    mensajeNOTI = ''
                    estadopreins = 1
                    preins = DetallePreInscripcionPracticasPP.objects.get(pk=practicas.preinscripcion.pk)
                    if practicas.estadosolicitud == '2':
                        mensaje = u"APROBÓ"
                        mensajeNOTI = u"APROBADO"
                        preins.estado = 5
                        estadopreins = 5
                    if practicas.estadosolicitud == '3':
                        mensaje = u"RECHAZÓ"
                        mensajeNOTI = u"RECHAZADO"
                        preins.estado = 3
                        estadopreins = 3
                    if practicas.estadosolicitud == '4':
                        mensaje = u"PENDIENTE"
                        mensajeNOTI = u"PENDIENTE"
                        preins.estado = 4
                        estadopreins = 4
                    preins.save()
                    seguimiento = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins, fecha=datetime.now(), estado=estadopreins, observacion=f.cleaned_data['observacion'])
                    seguimiento.save(request)
                    asunto = u"NOTIFICACION DE SOLICITUD"
                    send_html_mail(asunto, "emails/aprobacion_solicitudpracpreprofesionales.html",
                                   {'sistema': request.session['nombresistema'],
                                    'alumno': practicas.inscripcion.persona},
                                   practicas.inscripcion.persona.lista_emails_envio(), [],
                                   cuenta=CUENTAS_CORREOS[0][1])
                    url_noti = '/pro_cronograma?action=listatutorias'
                    url_noti_supervisor = '/pro_cronograma?action=listasupervision'
                    if practicas.estadosolicitud == '3':
                        url_noti = '/notificacion'
                        url_noti_supervisor = '/notificacion'
                    observacion = 'Se le comunica que la solicitud del estudiante {} ha sido asignada como {}'.format(
                        practicas.inscripcion.persona.__str__(), mensaje)
                    if practicas.tutorunemi:
                        notificacion('SOLICITUD DE PRÁCTICAS PREPROFESIONALES {}'.format(mensajeNOTI), observacion,
                                     practicas.tutorunemi.persona, None, url_noti,
                                     practicas.pk, 1, 'sga', PracticasPreprofesionalesInscripcion, request)
                    if practicas.supervisor:
                        notificacion('SOLICITUD DE PRÁCTICAS PREPROFESIONALES {}'.format(mensajeNOTI), observacion,
                                     practicas.supervisor.persona, None, url_noti_supervisor,
                                     practicas.pk, 1, 'sga', PracticasPreprofesionalesInscripcion, request)

                    log(
                        u'Actualizo preprofesionales observacion aprueba,rechaza o estado pendiente inscripcion: %s estado: %s %s' % (
                            practicas.id, mensaje, practicas), request, mensaje)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'aprobarpracticas':
            try:
                praprofesionales = PracticasPreprofesionalesInscripcion.objects.get(
                    pk=request.POST['idencuestapreguntas'])
                return JsonResponse({"result": "ok", "idpracticas": praprofesionales.id,
                                     "nombres": praprofesionales.inscripcion.persona.apellido1 + ' ' + praprofesionales.inscripcion.persona.apellido2 + ' ' + praprofesionales.inscripcion.persona.nombres})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'addevidenciaspracticas':
            try:
                f = EvidenciaPracticasForm(request.POST, request.FILES)
                # 2.5MB - 2621440
                # 5MB - 5242880
                # 10MB - 10485760
                # 20MB - 20971520
                # 50MB - 5242880
                # 100MB 104857600
                # 250MB - 214958080
                # 500MB - 429916160
                d = request.FILES['archivo']
                if d.size > 20971520:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("informespracticas_", newfile._name)
                    if DetalleEvidenciasPracticasPro.objects.filter(evidencia_id=request.POST['idevidencia'],
                                                                    inscripcionpracticas_id=request.POST[
                                                                        'id']).exists():
                        detalle = DetalleEvidenciasPracticasPro.objects.filter(evidencia_id=request.POST['idevidencia'],
                                                                            inscripcionpracticas_id=request.POST['id'])[0]
                        detalle.descripcion = f.cleaned_data['descripcion']
                        detalle.puntaje = f.cleaned_data['puntaje']
                        # detalle.obseaprueba = f.cleaned_data['puntaje']
                        detalle.estadorevision = 1
                        detalle.archivo = newfile
                        detalle.fechaarchivo = datetime.now()
                        detalle.horaarchivo = datetime.now().time()
                        detalle.save(request)
                        log(u'Adiciono evidencia de practicas: %s [%s]' % (detalle, detalle.id), request, "add")
                    else:
                        evidencia = DetalleEvidenciasPracticasPro(evidencia_id=request.POST['idevidencia'],
                                                                  inscripcionpracticas_id=request.POST['id'],
                                                                  descripcion=f.cleaned_data['descripcion'],
                                                                  puntaje=f.cleaned_data['puntaje'],
                                                                  fechaarchivo=datetime.now(),
                                                                  archivo=newfile)
                        evidencia.save(request)
                        log(u'Adiciono evidencia de practicas: %s [%s]' % (evidencia, evidencia.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.%s " % ex})

        if action == 'ponerfechalimite':
            try:
                form = PonerFechaLimiteEvidenciaForm(request.POST)
                # fechamodificacion=None
                if form.is_valid():
                    practica = PracticasPreprofesionalesInscripcion.objects.filter(id=request.POST['id'])[0]
                    practica.asignar_fechas_evidencia(request, request.POST['idevidencia'],
                                                      form.cleaned_data['fechainicio'], form.cleaned_data['fechafin'],
                                                      False)
                    #     if DetalleEvidenciasPracticasPro.objects.filter(evidencia_id=request.POST['idevidencia'], inscripcionpracticas_id=request.POST['id']).exists():
                    #         detalle = DetalleEvidenciasPracticasPro.objects.get(evidencia_id=request.POST['idevidencia'], inscripcionpracticas_id=request.POST['id'])
                    #         detalle.fechainicio = f.cleaned_data['fechainicio']
                    #         detalle.fechafin = f.cleaned_data['fechafin']
                    #         if detalle.fecha_modificacion:
                    #             fechamodificacion = detalle.fecha_modificacion
                    #         detalle.save(request)
                    #         cursor = connection.cursor()
                    #         if fechamodificacion:
                    #             sqlperiodo = "UPDATE sga_detalleevidenciaspracticaspro SET fecha_modificacion = '"+str(fechamodificacion)+"' WHERE sga_detalleevidenciaspracticaspro.id=" + str(detalle.id) + ""
                    #         else:
                    #             sqlperiodo = "UPDATE sga_detalleevidenciaspracticaspro SET fecha_modificacion = null WHERE sga_detalleevidenciaspracticaspro.id=" + str(detalle.id) + ""
                    #         cursor.execute(sqlperiodo)
                    #         log(u'Adiciono Fecha limite y fin para subir evidencia: %s %s %s' % (detalle.id, detalle.fechainicio,detalle.fechafin), request, "add")
                    #     else:
                    #         fechainicio = convertir_fecha(request.POST['fechainicio'])
                    #         fechafin = convertir_fecha(request.POST['fechafin'])
                    #         detalle = DetalleEvidenciasPracticasPro(evidencia_id=request.POST['idevidencia'],
                    #                                                   inscripcionpracticas_id=request.POST['id'],
                    #                                                  fechainicio=fechainicio,
                    #                                                   fechafin=fechafin,
                    #                                                 estadorevision=0,
                    #                                                 estadotutor=0)
                    #         detalle.save(request)
                    #         cursor = connection.cursor()
                    #         sqlperiodo = "UPDATE sga_detalleevidenciaspracticaspro SET fecha_modificacion = null, fecha_creacion = null WHERE sga_detalleevidenciaspracticaspro.id="+ str(detalle.id) +""
                    #         cursor.execute(sqlperiodo)
                    #         log(u'Adiciono Fecha limite y fin apara subir evidencia: %s %s %s' % (detalle.id, detalle.fechainicio, detalle.fechafin),request, "add")
                    #     asunto = u"NOTIFICACION DE FECHAS PARA SUBIR EVIDENCIA"
                    #     send_html_mail(asunto, "emails/notificafechasubirevidencia.html",
                    #                    {'sistema': request.session['nombresistema'],
                    #                     'detalle': detalle,
                    #                     'alumno': detalle.inscripcionpracticas.inscripcion.persona.nombre_completo_inverso()},
                    #                    detalle.inscripcionpracticas.inscripcion.persona.lista_emails_envio(), [],
                    #                    cuenta=CUENTAS_CORREOS[0][1])
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.%s " % ex})

        if action == 'adddepartamento':
            try:
                f = PracticasDepartamentoForm(request.POST)
                if f.is_valid():
                    if not PracticasDepartamento.objects.filter(nombre=f.cleaned_data['nombre']).exists():
                        departamento = PracticasDepartamento(nombre=f.cleaned_data['nombre'])
                        departamento.save(request)
                        log(u'Adiciono departamento en practicas profesionales inscripcion: %s [%s]' % (
                            departamento, departamento.id), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe Departamento de empresa."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editdepartamento':
            try:
                f = PracticasDepartamentoForm(request.POST)
                departamento = PracticasDepartamento.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    departamento.nombre = f.cleaned_data['nombre']
                    departamento.save(request)
                    log(u'Edito departamento en practicas profesionales inscripcion: %s [%s]' % (
                        departamento, departamento.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'listarotacionmalla':
            try:
                tipo = 0
                lista = []
                alumno = Inscripcion.objects.get(pk=request.POST['id'])

                nivelmalla = alumno.inscripcionnivel_set.all()[0]

                if RotacionesMalla.objects.filter(malla__carrera=alumno.carrera).exists():
                    idp = periodo.id
                    rotaciones = RotacionesMalla.objects.filter(malla__carrera=alumno.carrera, pk__lt=13).order_by('id')

                    # SI ES DE NUTRICION FILTRAR LAS NUEVAS ROTACIONES Y EL PERIODO A PARTIR DE SEPTIEMBRE 2019
                    if alumno.carrera.id == 111 or alumno.carrera.id == 3:
                        if idp >= 89:
                            rotaciones = RotacionesMalla.objects.filter(malla__carrera=alumno.carrera,
                                                                        pk__gte=13).order_by('id')

                    tipo = 1
                    for rota in rotaciones:
                        lista.append([rota.id, rota.nombre])
                return JsonResponse({'result': 'ok', 'lista': lista, 'tipo': tipo})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'listaperiodoevidencia':
            try:
                tipo = 0
                lista = []
                alumno = Inscripcion.objects.get(pk=request.POST['id'])
                listaperiodo = PeriodoEvidenciaPracticaProfesionales.objects.filter(status=True,
                                                                                    carrera=alumno.carrera).distinct().order_by(
                    'nombre')
                for lis in listaperiodo:
                    lista.append([lis.id, lis.nombre])
                return JsonResponse({'result': 'ok', 'lista': lista, 'tipo': tipo})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'listaitinerariooferta':
            try:
                carreras = Carrera.objects.filter(pk__in=[int(car) for car in json.loads(request.POST['idc'])])
                malla = Malla.objects.filter(carrera__in=carreras)
                listaitinerarios = []
                existeitinerario = False
                itinerarios = ItinerariosMalla.objects.filter(malla__in=malla, status=True)
                if itinerarios:
                    for itinerario in itinerarios:
                        listaitinerarios.append([itinerario.id, itinerario.__str__()])
                    existeitinerario = True
                return JsonResponse(
                    {'result': 'ok', 'itinerarios': listaitinerarios, 'existeitinerario': existeitinerario})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'listaitinerario':
            try:
                inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))

                # SALUD = 1
                idfacultad = inscripcion.coordinacion_id

                malla = inscripcion.mi_malla()
                nivel = inscripcion.mi_nivel().nivel
                nivelid = nivel.id

                listaitinerarios = []
                puedeadicionar = False
                existeitinerario = False
                mensaje = ''
                itinerarios = ItinerariosMalla.objects.filter(malla=malla, nivel__id__lte=nivel.id, status=True)
                if itinerarios:
                    for itinerario in itinerarios:
                        listaitinerarios.append([itinerario.id, itinerario.__str__()])
                    existeitinerario = True
                    puedeadicionar = True
                else:
                    if nivel.id < 5:
                        mensaje = "Para solicitar Practicas preprofesionales debe tener aprobado 5to nivel"
                    else:
                        puedeadicionar = True
                return JsonResponse({'result': 'ok', 'puedeadicionar': puedeadicionar, 'itinerarios': listaitinerarios,
                                     'mensaje': mensaje, 'existeitinerario': existeitinerario, 'nivelid': nivelid,
                                     'idfacultad': idfacultad})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'deletedepartamento':
            try:
                departamento = PracticasDepartamento.objects.get(pk=request.POST['id'])
                departamento.status = False
                departamento.save(request)
                log(u'Elimino departamento en practicas profesionales inscripcion: %s [%s]' % (
                    departamento, departamento.id), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addevidenciaspracticasnormal':
            try:
                f = EvidenciaPracticasForm(request.POST, request.FILES)
                # 2.5MB - 2621440
                # 5MB - 5242880
                # 10MB - 10485760
                # 20MB - 20971520
                # 50MB - 5242880
                # 100MB 104857600
                # 250MB - 214958080
                # 500MB - 429916160
                d = request.FILES['archivo']
                newfilesd = d._name
                ext = newfilesd[newfilesd.rfind("."):]
                if ext == '.pdf' or ext == '.PDF':
                    a = 1
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if d.size > 20971520:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("informespracticas_", newfile._name)
                    if DetalleEvidenciasPracticasPro.objects.filter(evidencia_id=request.POST['idevidencia'],status=True,
                                                                    inscripcionpracticas_id=request.POST[
                                                                        'id']).exists():
                        detalle = DetalleEvidenciasPracticasPro.objects.filter(evidencia_id=request.POST['idevidencia'],
                                                                            status=True,
                                                                            inscripcionpracticas_id=request.POST['id'])[0]
                        detalle.descripcion = f.cleaned_data['descripcion']
                        detalle.estadorevision = 1
                        detalle.personaaprueba_id = None
                        detalle.obseaprueba = None
                        detalle.fechaaprueba = None
                        detalle.archivo = newfile
                        detalle.fechaarchivo = datetime.now()
                        detalle.save(request)
                    else:
                        detalle = DetalleEvidenciasPracticasPro(evidencia_id=request.POST['idevidencia'],
                                                                inscripcionpracticas_id=request.POST['id'],
                                                                descripcion=f.cleaned_data['descripcion'],
                                                                puntaje=0,
                                                                fechaarchivo=datetime.now(),
                                                                archivo=newfile)
                        detalle.save(request)
                    log(u'Adiciono evidencia de practicas normal en practicas profesionales inscripcion: %s [%s]' % (
                        detalle, detalle.id), request, "edit")
                    asunto = u"NOTIFICACIÓN INGRESO DE DOCUMENTO AL PORTAFOLIO"
                    send_html_mail(asunto, "emails/ingreso_evipracpreprofesionales.html",
                                   {'sistema': request.session['nombresistema'], 'evidencia': detalle.evidencia.nombre,
                                    'alumno': detalle.inscripcionpracticas.inscripcion.persona},
                                   detalle.inscripcionpracticas.inscripcion.persona.lista_emails_envio(), [],
                                   cuenta=CUENTAS_CORREOS[4][1])
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addapruebaevidencias':
            try:
                detallepracticas = DetalleEvidenciasPracticasPro.objects.filter(evidencia_id=request.POST['idevidencia'],
                                                                             inscripcionpracticas_id=request.POST['id'],
                                                                             status=True).order_by('-id')[0]
                f = ArpobarEvidenciaPracticasForm(request.POST)

                if f.is_valid():
                    detallepracticas.estadorevision = f.cleaned_data['tipo']
                    detallepracticas.obseaprueba = f.cleaned_data['observacion']
                    detallepracticas.fechaaprueba = datetime.now()
                    detallepracticas.personaaprueba = persona
                    detallepracticas.aprobosupervisor = False
                    detallepracticas.save(request)
                    # totalaprobadas = DetalleEvidenciasPracticasPro.objects.filter(inscripcionpracticas_id=request.POST['id'], estadorevision=2).count()
                    # totalevidencias = EvidenciaPracticasProfesionales.objects.filter(status=True).count()
                    # if totalaprobadas == totalevidencias:
                    #     practicasins = PracticasPreprofesionalesInscripcion.objects.get(pk=request.POST['id'])
                    #     if practicasins.tiposolicitud != 3:
                    #         practicasins.tiposolicitud = 4
                    #     practicasins.estadosolicitud = 2
                    #     practicasins.culminada = True
                    #     practicasins.save(request)
                    if f.cleaned_data['tipo'] == '3':
                        practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.get(
                            pk=request.POST['idpracins'])
                        practicaspreprofesionalesinscripcion.autorizarevidencia = True
                        practicaspreprofesionalesinscripcion.fechaautorizarevidencia = datetime.now()
                        practicaspreprofesionalesinscripcion.save(request)
                    log(u'Adiciono pruebas de evidencia en practicas profesionales inscripcion: %s [%s]' % (
                        detallepracticas, detallepracticas.id), request, "edit")
                    asunto = u"NOTIFICACION DE CALIFICACIÓN"
                    send_html_mail(asunto, "emails/aprobacion_pracpreprofesionales.html",
                                   {'sistema': request.session['nombresistema'],
                                    'evidencia': detallepracticas.evidencia.nombre,
                                    'alumno': detallepracticas.inscripcionpracticas.inscripcion.persona},
                                   detallepracticas.inscripcionpracticas.inscripcion.persona.lista_emails_envio(), [],
                                   cuenta=CUENTAS_CORREOS[4][1])
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'culminarpracticas':
            try:
                totalaprobadas = DetalleEvidenciasPracticasPro.objects.values("id").filter(
                    inscripcionpracticas_id=request.POST['codigoitem'], estadorevision=2).count()
                cabecera = PracticasPreprofesionalesInscripcion.objects.get(pk=request.POST['codigoitem'])
                # totalevidencias = EvidenciaPracticasProfesionales.objects.filter(status=True).count()
                if totalaprobadas == cabecera.totalevidencias():
                    if cabecera.tiposolicitud != 3:
                        cabecera.tiposolicitud = 4
                    if not cabecera.estadosolicitud == 6:
                        cabecera.estadosolicitud = 2
                    cabecera.culminada = True
                    cabecera.save(request)
                    # asunto = u"NOTIFICACION DE CALIFICACIÓN"
                    # send_html_mail(asunto, "emails/aprobacion_pracpreprofesionales.html",{'sistema': request.session['nombresistema'], 'evidencia': detallepracticas.evidencia.nombre,'alumno': detallepracticas.inscripcionpracticas.inscripcion.persona}, detallepracticas.inscripcionpracticas.inscripcion.persona.lista_emails_envio(), [])
                    log(u'Culmino practicas preprofesionales: %s' % cabecera, request, "edit")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'modificar_nota':
            try:
                if request.POST['id']:
                    detalleevidenciaspracticaspro = \
                        DetalleEvidenciasPracticasPro.objects.filter(pk=int(request.POST['id']))[0]
                else:
                    detalleevidenciaspracticaspro = DetalleEvidenciasPracticasPro(
                        evidencia_id=int(encrypt(request.POST['idev'])),
                        inscripcionpracticas_id=int(encrypt(request.POST['idpr'])))
                    detalleevidenciaspracticaspro.save(request)
                    log(
                        u'Se adiciono detalle evidencia practicas por que va a calificar: evidencia (%s) practica(%s)' % (
                            detalleevidenciaspracticaspro.evidencia,
                            detalleevidenciaspracticaspro.inscripcionpracticas),
                        request, "add")
                detalleevidenciaspracticaspro.puntaje = request.POST['nota']
                detalleevidenciaspracticaspro.save(request)
                log(u'Modifico notas de Evidencias: %s - nota(%s)' % (
                    detalleevidenciaspracticaspro, detalleevidenciaspracticaspro.puntaje), request, "edit")
                detalleevidenciaspracticaspro.inscripcionpracticas.aprobacion_promedio_nota(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'autorizarevidencia':
            try:
                practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.get(
                    pk=request.POST['idprins'])
                practicaspreprofesionalesinscripcion.autorizarevidencia = True
                practicaspreprofesionalesinscripcion.fechaautorizarevidencia = datetime.now()
                practicaspreprofesionalesinscripcion.save(request)
                asunto = u"NOTIFICACION DE AUTORIZACIÓN"
                send_html_mail(asunto, "emails/autorizar_evidenciahrs.html",
                               {'sistema': request.session['nombresistema'],
                                'hora': practicaspreprofesionalesinscripcion.autorizarevidenciasuma24hrs(),
                                'alumno': practicaspreprofesionalesinscripcion.inscripcion.persona.nombre_completo()},
                               practicaspreprofesionalesinscripcion.inscripcion.persona.lista_emails_envio()
                               , [], cuenta=CUENTAS_CORREOS[4][1])
                # , cuenta=variable_valor('CUENTAS_CORREOS')[4]
                #
                log(u'Autorizo subir evidencias: %s %s' % (
                    practicaspreprofesionalesinscripcion.inscripcion, practicaspreprofesionalesinscripcion.id), request,
                    "edit")
                return JsonResponse({"result": "ok", "idpracticas": practicaspreprofesionalesinscripcion.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addoferta':
            mensaje = u"Error al guardar los datos."
            try:
                f = OfertasPracticasForm(request.POST)
                if f.is_valid():
                    oferta = OfertasPracticas(departamento=f.cleaned_data['departamento'],
                                              horario=f.cleaned_data['horario'],
                                              requisito=f.cleaned_data['requisito'],
                                              habilidad=f.cleaned_data['habilidad'],
                                              cupos=f.cleaned_data['cupos'],
                                              inicio=f.cleaned_data['inicio'],
                                              fin=f.cleaned_data['fin'],
                                              iniciopractica=f.cleaned_data['iniciopractica'],
                                              finpractica=f.cleaned_data['finpractica'],
                                              otraempresa=f.cleaned_data['otraempresa'],
                                              tipoinstitucion=f.cleaned_data['tipoinstitucion'],
                                              sectoreconomico=f.cleaned_data['sectoreconomico'],
                                              tipo=f.cleaned_data['tipopractica'],
                                              numerohora=f.cleaned_data['numerohora'])
                    if f.cleaned_data['otraempresa']:
                        oferta.otraempresaempleadora = f.cleaned_data['otraempresaempleadora']
                    else:
                        oferta.empresa = f.cleaned_data['empresa']
                    oferta.save(request)
                    # oferta.carrera = f.cleaned_data['carrera']
                    for carr in f.cleaned_data['carrera']:
                        oferta.carrera.add(carr)
                    if int(f.cleaned_data['tipopractica']) == 1 or int(f.cleaned_data['tipopractica']) == 2:
                        mallas = Malla.objects.filter(carrera__in=f.cleaned_data['carrera'])
                        for malla in mallas:
                            if ItinerariosMalla.objects.values('id').filter(malla=malla, status=True).exists():
                                if not ItinerariosMalla.objects.values('id').filter(
                                        pk__in=f.cleaned_data['itinerarios'], malla=malla, status=True).exists():
                                    mensaje = u"Debe seleccionar al menos un itinerario de la carrera " + malla.carrera.__str__()
                                    raise NameError('Error')
                        if ItinerariosMalla.objects.values('id').filter(malla__in=mallas, status=True).exists():
                            if f.cleaned_data['itinerarios']:
                                # oferta.itinerariosmalla = f.cleaned_data['itinerarios']
                                for itin in f.cleaned_data['itinerarios']:
                                    oferta.itinerariosmalla.add(itin)
                    log(u'Agrego una oferta: %s ' % (oferta), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": mensaje})

        elif action == 'editoferta':
            mensaje = u"Error al guardar los datos."
            try:
                oferta = OfertasPracticas.objects.get(pk=request.POST['id'], status=True)
                f = OfertasPracticasForm(request.POST)
                if f.is_valid():
                    oferta.empresa = f.cleaned_data['empresa']
                    oferta.departamento = f.cleaned_data['departamento']
                    oferta.horario = f.cleaned_data['horario']
                    # oferta.carrera = f.cleaned_data['carrera']
                    oferta.carrera.clear()
                    for carr in f.cleaned_data['carrera']:
                        oferta.carrera.add(carr)
                    oferta.requisito = f.cleaned_data['requisito']
                    oferta.habilidad = f.cleaned_data['habilidad']
                    oferta.cupos = f.cleaned_data['cupos']
                    oferta.inicio = f.cleaned_data['inicio']
                    oferta.fin = f.cleaned_data['fin']
                    oferta.iniciopractica = f.cleaned_data['iniciopractica']
                    oferta.finpractica = f.cleaned_data['finpractica']
                    oferta.tipo = f.cleaned_data['tipopractica']
                    oferta.numerohora = f.cleaned_data['numerohora']
                    if int(f.cleaned_data['tipopractica']) == 1 or int(f.cleaned_data['tipopractica']) == 2:
                        mallas = Malla.objects.filter(carrera__in=f.cleaned_data['carrera'])
                        for malla in mallas:
                            if ItinerariosMalla.objects.values('id').filter(malla=malla, status=True).exists():
                                if not ItinerariosMalla.objects.values('id').filter(
                                        pk__in=f.cleaned_data['itinerarios'], malla=malla, status=True).exists():
                                    mensaje = u"Debe seleccionar al menos un itinerario de la carrera " + malla.carrera
                                    raise NameError('Error')
                        # oferta.itinerariosmalla = f.cleaned_data['itinerarios']
                        oferta.itinerariosmalla.clear()
                        for itin in f.cleaned_data['itinerarios']:
                            oferta.itinerariosmalla.add(itin)
                    if f.cleaned_data['otraempresa']:
                        oferta.otraempresaempleadora = f.cleaned_data['otraempresaempleadora'].upper()
                        oferta.empresa = None
                    else:
                        oferta.empresa = f.cleaned_data['empresa']
                        oferta.otraempresaempleadora = None
                    oferta.otraempresa = f.cleaned_data['otraempresa']
                    oferta.save(request)

                    log(u'Edita una oferta: %s' % oferta, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": mensaje})

        elif action == 'deleoferta':
            try:
                oferta = OfertasPracticas.objects.get(pk=int(request.POST['id']), status=True)
                if not oferta.puede_eliminar():
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No puede eliminar, la oferta esta siendo utilizada."})
                log(u'Elimino una oferta: %s' % oferta, request, "del")
                oferta.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'carrerascoordinacion':
            try:
                lista = []
                carreras = Carrera.objects.filter(coordinacion__id__in=json.loads(request.POST['idc']))
                for carrera in carreras:
                    lista.append([carrera.id, carrera.__str__()])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addaperturasolicitud':
            try:
                f = AperturaPracticaPreProfesionalForm(request.POST)
                if f.is_valid():
                    if not f.cleaned_data['fechaapertura'] <= f.cleaned_data['fechacierre']:
                        return JsonResponse({"result": "bad",
                                             "mensaje": "La fecha de apertura no puede ser mayor a la fecha de cierre."})
                    if AperturaPracticaPreProfesional.objects.filter(fechaapertura=f.cleaned_data['fechaapertura'],
                                                                     fechacierre=f.cleaned_data[
                                                                         'fechacierre']).exists():
                        return JsonResponse(
                            {"result": "bad", "mensaje": "Ya existe un registro con las misma fechas indicadas"})
                    if not f.cleaned_data['mensaje']:
                        return JsonResponse({"result": "bad", "mensaje": "Ingrese un mensaje"})
                    apertura = AperturaPracticaPreProfesional(mensaje=f.cleaned_data['mensaje'],
                                                              fechaapertura=f.cleaned_data['fechaapertura'],
                                                              fechacierre=f.cleaned_data['fechacierre'],
                                                              fechainicioverrequisitos=f.cleaned_data[
                                                                  'fechainicioverrequisitos'],
                                                              fechacierreverrequisitos=f.cleaned_data[
                                                                  'fechacierreverrequisitos'],
                                                              fechainiciovalhoras=f.cleaned_data['fechainiciovalhoras'],
                                                              fechacierrevalhoras=f.cleaned_data['fechacierrevalhoras'],
                                                              fechainicioreghoras=f.cleaned_data['fechainicioreghoras'],
                                                              fechacierrereghoras=f.cleaned_data['fechacierrereghoras'],
                                                              # periodoppp=f.cleaned_data['periodoevidencia'],
                                                              periodo=f.cleaned_data['periodo'],
                                                              motivo=f.cleaned_data['motivo'],
                                                              actualizararchivo=f.cleaned_data['actualizararchivo'],
                                                              homologacion2021=True)
                    apertura.save(request)
                    apertura.validar = f.cleaned_data['validar']
                    # apertura.periodoppp = f.cleaned_data['periodoevidencia']


                    # apertura.coordinacion = f.cleaned_data['coordinacion']
                    for coor in f.cleaned_data['coordinacion']:
                        apertura.coordinacion.add(coor)

                    # apertura.carrera = f.cleaned_data['carrera']
                    apertura.actualizararchivo = f.cleaned_data['actualizararchivo']
                    apertura.publico = f.cleaned_data['publico']
                    apertura.save(request)
                    aperturadetalle = AperturaPracticaPreProfesionalDetalle(aperturapractica_id=apertura.id,
                                                                            tipo=int(1), tiposolicitud=int(3))
                    aperturadetalle.save(request)
                    log(u'Adiciono apertura de practica pre profesional: %s - %s - %s - %s - estudiante(%s) - decano(%s) - directorcarrera (%s)' % (
                        apertura.fechaapertura, apertura.fechacierre, apertura.motivo, apertura.validar,
                        apertura.estudiante, apertura.decano, apertura.directorcarrera), request, "add")
                    # if f.cleaned_data['estudiante'] == True:
                    #     if 'lista_items1' in request.POST:
                    #         for listatipo in json.loads(request.POST['lista_items1']):
                    #             aperturadetalle = AperturaPracticaPreProfesionalDetalle(aperturapractica_id=apertura.id,
                    #                                                                     tipo=int(listatipo['idt']),
                    #                                                                     tiposolicitud=int(
                    #                                                                         listatipo['idts']))
                    #             aperturadetalle.save(request)
                    #             log(u'Adiciono apertura de practica pre profesional detalle: %s - %s - %s' % (
                    #             aperturadetalle.aperturapractica, aperturadetalle.get_tipo_display(),
                    #             aperturadetalle.get_tiposolicitud_display()), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editaperturasolicitud':
            try:
                f = AperturaPracticaPreProfesionalForm(request.POST)
                if f.is_valid():
                    apertura = AperturaPracticaPreProfesional.objects.get(pk=int(request.POST['id']))
                    if not apertura.fechaapertura <= apertura.fechacierre:
                        return JsonResponse({"result": "bad",
                                             "mensaje": "La fecha de apertura no puede ser mayor a la fecha de cierre."})
                    if AperturaPracticaPreProfesional.objects.filter(fechaapertura=f.cleaned_data['fechaapertura'],
                                                                     fechacierre=f.cleaned_data['fechacierre']).exclude(
                        pk=int(request.POST['id'])).exists():
                        return JsonResponse(
                            {"result": "bad", "mensaje": "Ya existe un registro con las misma fechas indicadas"})
                    if not f.cleaned_data['mensaje']:
                        return JsonResponse({"result": "bad", "mensaje": "Ingrese un mensaje"})
                    apertura.mensaje = f.cleaned_data['mensaje']
                    apertura.fechaapertura = f.cleaned_data['fechaapertura']
                    apertura.fechacierre = f.cleaned_data['fechacierre']
                    apertura.fechainicioverrequisitos = f.cleaned_data['fechainicioverrequisitos']
                    apertura.fechacierreverrequisitos = f.cleaned_data['fechacierreverrequisitos']
                    apertura.fechainiciovalhoras = f.cleaned_data['fechainiciovalhoras']
                    apertura.fechacierrevalhoras = f.cleaned_data['fechacierrevalhoras']
                    apertura.fechainicioreghoras = f.cleaned_data['fechainicioreghoras']
                    apertura.fechacierrereghoras = f.cleaned_data['fechacierrereghoras']
                    apertura.periodo = f.cleaned_data['periodo']
                    apertura.motivo = f.cleaned_data['motivo']
                    apertura.actualizararchivo = f.cleaned_data['actualizararchivo']
                    apertura.publico = f.cleaned_data['publico']
                    apertura.validar = f.cleaned_data['validar']

                    # apertura.coordinacion = f.cleaned_data['coordinacion']
                    apertura.coordinacion.clear()
                    for coor in f.cleaned_data['coordinacion']:
                        apertura.coordinacion.add(coor)
                    # apertura.periodoppp = f.cleaned_data['periodoevidencia']
                    # apertura.carrera = f.cleaned_data['carrera']
                    apertura.save(request)
                    log(u'Edito apertura de practica pre profesional: %s - %s - %s - %s' % (
                        apertura.fechaapertura, apertura.fechacierre, apertura.motivo, apertura.validar), request,
                        "edit")
                    # listatipos = []
                    # if 'lista_items1' in request.POST:
                    #     if f.cleaned_data['estudiante'] == True:
                    #         for listatipo in json.loads(request.POST['lista_items1']):
                    #             aperturadetalles = AperturaPracticaPreProfesionalDetalle.objects.values_list('id',
                    #                                                                                          flat=True).filter(
                    #                 aperturapractica__id=apertura.id, tipo=listatipo['idt'],
                    #                 tiposolicitud=listatipo['idts'])
                    #             if not aperturadetalles:
                    #                 aperturadetalle = AperturaPracticaPreProfesionalDetalle(
                    #                     aperturapractica_id=apertura.id, tipo=int(listatipo['idt']),
                    #                     tiposolicitud=int(listatipo['idts']))
                    #                 aperturadetalle.save(request)
                    #                 log(u'Adiciono apertura de practica pre profesional detalle: %s - %s - %s' % (
                    #                 aperturadetalle.aperturapractica, aperturadetalle.get_tipo_display(),
                    #                 aperturadetalle.get_tiposolicitud_display()), request, "add")
                    #                 listatipos.append(aperturadetalle.id)
                    #             listatipos.extend(aperturadetalles)
                    #         aperturadetalles = AperturaPracticaPreProfesionalDetalle.objects.filter(
                    #             aperturapractica_id=apertura.id).exclude(pk__in=listatipos)
                    #     else:
                    #         aperturadetalles = AperturaPracticaPreProfesionalDetalle.objects.filter(
                    #             aperturapractica_id=apertura.id)
                    #     for aperturadetalle in aperturadetalles:
                    #         log(u'elimino apertura de practica pre profesional detalle: %s - %s - %s' % (
                    #         aperturadetalle.aperturapractica, aperturadetalle.get_tipo_display(),
                    #         aperturadetalle.get_tiposolicitud_display()), request, "del")
                    #     aperturadetalles.delete()
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delaperturasolicitud':
            try:
                apertura = AperturaPracticaPreProfesional.objects.get(pk=int(request.POST['id']))
                if not apertura.puede_eliminar():
                    return JsonResponse({"result": "bad", "mensaje": "No puede eliminar registro de apertura."})
                log(
                    u'Elimino apertura de practica pre profesional: %s - %s - %s - %s - estudiante(%s) - decano(%s) - directorcarrera (%s)' % (
                        apertura.fechaapertura, apertura.fechacierre, apertura.motivo, apertura.validar,
                        apertura.estudiante, apertura.decano, apertura.directorcarrera), request, "del")
                apertura.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'adicionarcarrera':
            try:
                postar = AperturaPracticaPreProfesional.objects.get(id=int(request.POST['id']))
                carreraids = request.POST['ids'].split(',')
                for a in carreraids:
                    carrera = Carrera.objects.get(pk=a)
                    if not CarreraHomologacion.objects.filter(status=True, apertura=postar, carrera=carrera).exists():
                        actividad = CarreraHomologacion(apertura=postar, carrera=carrera)
                        actividad.save(request)
                        for itin in actividad.itinerariosmalla():
                            documentosbases = ItinerariosMallaDocumentosBase.objects.filter(status=True,
                                                                                            itinerario=itin)
                            for doc in documentosbases:
                                filtro = CarreraHomologacionRequisitos(carrera=actividad, documento=doc.documento,
                                                                       tipo=doc.tipo, itinerario=itin)
                                filtro.save(request)
                        log(u'Adiciono carrera periodo de homologación: %s %s' % (postar, carrera.nombre), request,
                            "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'validardocumentoshomologacion':
            try:
                postar = DocumentosSolicitudHomologacionPracticas.objects.get(id=int(request.POST['id']))
                postar.estados = request.POST['est']
                postar.observacion = request.POST['obs']
                if int(request.POST['est']) == 3:
                    postar.corregido = False
                else:
                    postar.corregido = True
                postar.save(request)
                if int(request.POST['est']) == 3:
                    soli = SolicitudHomologacionPracticas.objects.get(pk=postar.solicitud.pk)
                    soli.revision_vinculacion = 3
                    soli.fecha_revision_vinculacion = datetime.now()
                    soli.persona_vinculacion = persona
                    soli.save(request)
                    asunto = u"VALIDACIÒN DE DOCUMENTOS DE HOMOLOGACIÒN PRACTICAS "
                    if postar.solicitud.inscripcion:
                        para = postar.solicitud.inscripcion.persona
                        notificacion(asunto, postar.observacion, para, None,
                                     '/alu_practicaspro?action=verproceso&id={}'.format(encrypt(postar.solicitud.pk)),
                                     postar.pk, 1, 'sga', DocumentosSolicitudHomologacionPracticas, request)
                        historial = HistorialDocumentosSolicitudHomologacionPracticas(
                            documento=postar,
                            solicitud=postar.solicitud,
                            fecha=datetime.now(), estados=postar.estados,
                            observacion=postar.observacion)
                        historial.save(request)
                log(u'Modifico documento homologación estudiante: %s %s' % (postar, postar.solicitud.inscripcion),
                    request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'verificacionrequisitoshomologacion':
            try:
                with transaction.atomic():
                    filtro = SolicitudHomologacionPracticas.objects.get(pk=int(request.POST['id']))
                    filtro.revision_vinculacion = request.POST['estado']
                    filtro.horas_sugeridas = request.POST['horas_sugeridas']
                    filtro.observacion_vinculacion = request.POST['observacion'].upper()
                    filtro.fecha_revision_vinculacion = datetime.now()
                    filtro.persona_vinculacion = persona
                    filtro.save(request)
                    accion = 0
                    if filtro.revision_vinculacion == '2':
                        filtro.estados = 6
                        messages.success(request, 'Validación de requisitos Rechazada.')
                    else:
                        filtro.estados = 3
                        messages.success(request, 'Validación de requisitos Aprobada.')
                    asunto = u"VALIDACIÒN DE DOCUMENTOS DE HOMOLOGACIÒN PRACTICAS {}".format(
                        filtro.get_estados_display())
                    para = filtro.inscripcion.persona
                    notificacion(asunto, filtro.observacion_vinculacion, para, None,
                                 '/alu_practicaspro?action=verproceso&id={}'.format(encrypt(filtro.pk)), filtro.pk, 1,
                                 'sga', SolicitudHomologacionPracticas, request)
                    historial = HistoricoRevisionesSolicitudHomologacionPracticas(solicitud=filtro,
                                                                                  ejecutado_por=persona,
                                                                                  accion=int(filtro.revision_vinculacion),
                                                                                  paso=1)
                    historial.save(request)
                    filtro.save(request)
                    log(u'Finalizo verificación de requisitos: {} {}'.format(filtro.inscripcion,
                                                                             filtro.get_revision_vinculacion_display()),
                        request, "add")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'validacionhorashomologar':
            try:
                with transaction.atomic():
                    filtro = SolicitudHomologacionPracticas.objects.get(pk=int(request.POST['id']))
                    filtro.revision_director = request.POST['estado']
                    if 'horas_homologadas' in request.POST:
                        filtro.horas_homologadas = request.POST['horas_homologadas']
                    filtro.observacion_director = request.POST['observacion'].upper()
                    filtro.fecha_revision_director = datetime.now()
                    filtro.persona_director = persona
                    filtro.save(request)
                    if filtro.revision_director == '2':
                        filtro.estados = 7
                        messages.success(request, 'Validación de Horas Homologación Rechazada.')
                    else:
                        filtro.estados = 4
                        messages.success(request, 'Validación de Horas Homologación Aprobada.')
                    historial = HistoricoRevisionesSolicitudHomologacionPracticas(solicitud=filtro,
                                                                                  ejecutado_por=persona,
                                                                                  accion=int(filtro.revision_director),
                                                                                  paso=2)
                    historial.save(request)
                    filtro.save(request)
                    asunto = u"VALIDACIÒN DE HORAS DE HOMOLOGACIÒN PRACTICAS {}".format(filtro.get_estados_display())
                    para = filtro.inscripcion.persona
                    # notificacion(asunto, filtro.observacion_director, para, None,
                    #              '/alu_practicaspro?action=verproceso&id={}'.format(encrypt(filtro.pk)), filtro.pk, 1,
                    #              'sga', SolicitudHomologacionPracticas, request)
                    filtro.save(request)
                    log(u'Finalizo Validación de Horas Homologación: {} {}'.format(filtro.inscripcion,
                                                                                   filtro.get_revision_director_display()),
                        request, "add")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'validarregistrohoras':
            try:
                with transaction.atomic():
                    filtro = SolicitudHomologacionPracticas.objects.get(pk=int(request.POST['id']))
                    filtro.revision_decano = request.POST['estado']
                    filtro.observacion_decano = request.POST['observacion'].upper()
                    filtro.fecha_revision_decano = datetime.now()
                    filtro.persona_decano = persona
                    filtro.save(request)
                    if filtro.revision_decano == '2':
                        filtro.estados = 8
                        messages.success(request, 'Validación de Horas Homologación Rechazada.')
                    else:
                        filtro.estados = 5
                        messages.success(request, 'Validación de Horas Homologación Aprobada.')
                    historial = HistoricoRevisionesSolicitudHomologacionPracticas(solicitud=filtro,
                                                                                  ejecutado_por=persona,
                                                                                  accion=int(filtro.revision_decano),
                                                                                  paso=3)
                    historial.save(request)
                    filtro.save(request)
                    asunto = u"REGISTRO DE HORAS DE HOMOLOGACIÒN PRACTICAS {}".format(filtro.get_estados_display())
                    para = filtro.inscripcion.persona
                    notificacion(asunto, filtro.observacion_decano, para, None,
                                 '/alu_practicaspro?action=verproceso&id={}'.format(encrypt(filtro.pk)), filtro.pk, 1,
                                 'sga', SolicitudHomologacionPracticas, request)
                    log(u'Finalizo Registro de Horas: {} {}'.format(filtro.inscripcion,
                                                                    filtro.get_revision_decano_display()), request,
                        "add")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'finalizarproceso':
            try:
                postar = SolicitudHomologacionPracticas.objects.get(id=int(request.POST['id']))
                if PracticasPreprofesionalesInscripcion.objects.filter(status=True, homologacion=postar).exists():
                    transaction.set_rollback(True)
                    return JsonResponse(
                        {"result": True, "mensaje": u"Ya existe una homologación migrada de esta solicitud."})
                form = FinalizarHomologacionForm(request.POST)
                postar.estados = request.POST['estados']
                postar.observacion = request.POST['observacion']
                postar.save(request)
                if request.POST['estados'] == '1':
                    if not postar.revision_decano == 1:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {"result": True, "mensaje": u"Solicitud aún no ha sido aprobada por el decano."})
                    postar.horas_sugeridas = int(request.POST['horas_sugeridas'])
                    postar.horas_homologadas = int(request.POST['horas_homologadas'])
                    postar.otraempresaempleadora = request.POST['otraempresaempleadora']
                    postar.departamento_id = request.POST['departamento']
                    postar.tipoinstitucion = request.POST['tipoinstitucion']
                    postar.sectoreconomico = request.POST['sectoreconomico']
                    postar.save(request)
                    filtro = SolicitudHomologacionPracticas.objects.get(id=postar.pk)
                    practica_reg = PracticasPreprofesionalesInscripcion(homologacion=filtro,
                                                                        tipo=1,
                                                                        tiposolicitud=3,
                                                                        estadosolicitud=2,
                                                                        observacion=filtro.observacion,
                                                                        inscripcion=filtro.inscripcion,
                                                                        departamento=filtro.departamento,
                                                                        numerohora=filtro.horas_homologadas,
                                                                        horahomologacion=filtro.horas_homologadas,
                                                                        otraempresaempleadora=filtro.otraempresaempleadora,
                                                                        # periodoppp=filtro.apertura.periodoevidencia,
                                                                        culminada=True,
                                                                        aperturapractica=filtro.apertura)
                    if Profesor.objects.filter(status=True, persona=postar.persona_director).exists():
                        practica_reg.tutorunemi = Profesor.objects.filter(status=True,
                                                                          persona=postar.persona_director).first()
                    practica_reg.save(request)
                asunto = u"SOLICITUD DE HOMOLOGACIÓN PRACTICAS APROBADA" if request.POST[
                                                                                'estados'] == '1' else u"SOLICITUD DE HOMOLOGACIÓN PRACTICAS RECHAZADA"
                para = postar.inscripcion.persona
                notificacion(asunto, postar.observacion, para, None,
                             '/alu_practicaspro?action=verproceso&id={}'.format(encrypt(postar.pk)), postar.pk, 1,
                             'sga', SolicitudHomologacionPracticas, request)
                log(u'Homologación %s del estudiante: %s %s' % (postar, postar.get_estados_display, postar.inscripcion),
                    request, "add")
                return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})

        elif action == 'addempresa':
            try:
                if EmpresaEmpleadora.objects.filter(status=True, nombre=request.POST['nombre']).exists():
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": u"Ya existe una empresa con este nombre."})
                if EmpresaEmpleadora.objects.filter(status=True, ruc=request.POST['ruc']).exists():
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": u"Ya existe una empresa con este ruc."})
                form = EmpresaAsignacionTutorForm(request.POST)
                if form.is_valid():
                    empresa = EmpresaEmpleadora(ruc=form.cleaned_data['ruc'], nombre=form.cleaned_data['nombre'],
                                                tipoinstitucion=int(request.POST['tipoinstitucion']),
                                                sectoreconomico=int(request.POST['sectoreconomico']),
                                                representante=form.cleaned_data['representante'],
                                                cargo=form.cleaned_data['cargo'],
                                                pais=form.cleaned_data['pais'],
                                                provincia_id=request.POST['provincia'],
                                                direccion=form.cleaned_data['direccion'],
                                                telefonos=form.cleaned_data['telefonos'],
                                                email=form.cleaned_data['email'],
                                                autorizada=True, )
                    empresa.save(request)
                    log(u'Adiciono Empresa: %s ' % (empresa.nombre), request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})

        elif action == 'generaracuerdo':
            try:
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 10194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                form = AcuerdoCompromisoAsignacionTutorForm(request.POST)
                if form.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivo", newfile._name)
                    empresa = EmpresaEmpleadora.objects.get(pk=request.POST['empresaid'])
                    solicitud = SolicitudVinculacionPreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                    acuerdo = AcuerdoCompromiso(empresa=empresa,
                                                carrera=solicitud.preinscripcion.inscripcion.carrera,
                                                fechaelaboracion=form.cleaned_data['fechaelaboracion'],
                                                coordinador=form.cleaned_data['coordinador'],
                                                nombrefirma=form.cleaned_data['nombrefirma'],
                                                cargofirma=form.cleaned_data['cargofirma'],
                                                financiamiento=form.cleaned_data['financiamiento'],
                                                fechainicio=form.cleaned_data['fechainicio'],
                                                fechafinalizacion=form.cleaned_data['fechafinalizacion'],
                                                tiempocump=form.cleaned_data['tiempocump'],
                                                para_practicas=form.cleaned_data['para_practicas'],
                                                para_pasantias=form.cleaned_data['para_pasantias'],
                                                archivo=newfile)
                    acuerdo.save(request)
                    responsables = request.POST.getlist('responsables')
                    if responsables:
                        responsables = ConfiguracionFirmaPracticasPreprofesionales.objects.filter(pk__in=responsables)
                        for rep in responsables:
                            acuerdo.responsables.add(rep)
                    acuerdo.save(request)
                    solicitud.tipovinculacion = 1
                    solicitud.acuerdo = acuerdo
                    solicitud.save(request)
                    log(u'Adiciono Acuerdo: %s ' % (acuerdo.__str__()), request, "add")
                    return JsonResponse({"result": False, 'mensaje': 'Acuerdo <b>{}</b> generado exitosamente, solicitud para asignación de tutor de <b>{}</b> actualizada.'.format(acuerdo.empresa.nombre, solicitud.preinscripcion.inscripcion.persona.__str__()), 'modalsuccess': True, 'to': '{}?action=asignaciontutor&id={}'.format(request.path, solicitud.preinscripcion.preinscripcion.pk)}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})

        elif action == 'addformatopractica':
            try:
                f = FormatoPracticaPreProfesionalForm(request.POST)
                if f.is_valid():
                    formato = FormatoPracticaPreProfesional(nombre=f.cleaned_data['nombre'],
                                                            vigente=f.cleaned_data['vigente'])
                    formato.save(request)
                    log(u'Adiciono formato de practica pre profesional: %s - %s' % (formato.nombre, formato.vigente),
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editformatopractica':
            try:
                f = FormatoPracticaPreProfesionalForm(request.POST)
                if f.is_valid():
                    formato = FormatoPracticaPreProfesional.objects.get(pk=int(request.POST['id']))
                    formato.nombre = f.cleaned_data['nombre']
                    formato.vigente = f.cleaned_data['vigente']
                    formato.save(request)
                    log(u'Edito formato de practica pre profesional: %s - %s' % (formato.nombre, formato.vigente),
                        request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delformatopractica':
            try:
                formato = FormatoPracticaPreProfesional.objects.get(pk=int(request.POST['id']))
                log(u'Elimino formato de practica pre profesional: %s - %s' % (formato.nombre, formato.vigente),
                    request, "del")
                formato.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'adddetalleformatopractica':
            try:
                f = DetalleFormatoPracticaPreProfesionalForm(request.POST, request.FILES)
                if f.is_valid():
                    formato = FormatoPracticaPreProfesional.objects.get(pk=int(request.POST['id']))
                    detalleformato = DetalleFormatoPracticaPreProfesional(formatopractica=formato,
                                                                          nombre=f.cleaned_data['nombre'],
                                                                          vigente=f.cleaned_data['vigente'])
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("detalle_formato_practica_", newfile._name)
                        detalleformato.archivo = newfile
                    detalleformato.save(request)
                    log(u'Adiciono detalle de formato de practica pre profesional: %s - %s - %s' % (
                        detalleformato.nombre, detalleformato.vigente, detalleformato.archivo), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editdetalleformatopractica':
            try:
                f = DetalleFormatoPracticaPreProfesionalForm(request.POST, request.FILES)
                if f.is_valid():
                    detalleformato = DetalleFormatoPracticaPreProfesional.objects.get(pk=int(request.POST['id']))
                    detalleformato.nombre = f.cleaned_data['nombre']
                    detalleformato.vigente = f.cleaned_data['vigente']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("detalle_formato_practica_", newfile._name)
                        detalleformato.archivo = newfile
                    detalleformato.save(request)
                    log(u'Edito detalle de formato de practica pre profesional: %s - %s - %s' % (
                        detalleformato.nombre, detalleformato.vigente, detalleformato.archivo), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'deldetalleformatopractica':
            try:
                detalleformato = DetalleFormatoPracticaPreProfesional.objects.get(pk=int(request.POST['id']))
                log(u'Elimino formato de practica pre profesional: %s - %s - %s' % (
                    detalleformato.nombre, detalleformato.vigente, detalleformato.archivo), request, "del")
                detalleformato.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'datosconvenio':
            try:
                convenio = ConvenioEmpresa.objects.get(pk=int(request.POST['id']))
                direccion = convenio.empresaempleadora.direccion if convenio.empresaempleadora.direccion else 'No tiene dirección asignada'
                representante = convenio.empresaempleadora.representante
                cargo = convenio.empresaempleadora.cargo
                email = convenio.empresaempleadora.email
                vinculados = DetalleCartaInscripcion.objects.values_list('inscripcion__pk', flat=True).filter(status=True)
                practicantes = PracticasPreprofesionalesInscripcion.objects.filter(status=True, estadosolicitud=2, preinscripcion__preinscripcion__periodo=periodo, convenio=convenio).exclude(id__in=vinculados)
                lista = [{'idP': p.id, 'cedula': p.inscripcion.persona.cedula, 'nombres': p.inscripcion.persona.nombre_completo_inverso(),
                          'carrera': p.inscripcion.carrera.nombre}
                         for p in practicantes]

                return JsonResponse({"result": "ok", "direccion": direccion, "representante": representante, "cargo": cargo, "email": email, 'lista': lista})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error en los datos de la empresa."})

        elif action == 'datosacuerdo':
            try:
                acuerdo = AcuerdoCompromiso.objects.get(pk=int(request.POST['id']))
                direccion = acuerdo.empresa.direccion
                representante = acuerdo.empresa.representante
                cargo = acuerdo.empresa.cargo
                email = acuerdo.empresa.email
                vinculados = DetalleCartaInscripcion.objects.values_list('inscripcion__pk', flat=True).filter(status=True)
                practicantes = PracticasPreprofesionalesInscripcion.objects.filter(status=True,estadosolicitud=2,preinscripcion__preinscripcion__periodo = periodo, acuerdo=acuerdo).exclude(id__in=vinculados)
                lista = [{'idP': p.id, 'cedula': p.inscripcion.persona.cedula, 'nombres': p.inscripcion.persona.nombre_completo_inverso(),
                          'carrera':p.inscripcion.carrera.nombre}
                                      for p in practicantes]

                return JsonResponse({"result": "ok", "direccion": direccion, "representante": representante, "cargo": cargo, "email": email, 'lista':lista})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error en los datos de la empresa."})

        elif action == 'datosempresa':
            try:
                empresa = EmpresaEmpleadora.objects.get(pk=int(request.POST['id']))
                departamento = PracticasDepartamento.objects.get(pk=int(request.POST['dep_id']))
                # direccion = acuerdo.empresa.direccion
                email = empresa.email
                representante = empresa.representante
                cargo = empresa.cargo
                vinculados = DetalleCartaInscripcion.objects.values_list('inscripcion__pk', flat=True).filter(status=True)
                practicantes = PracticasPreprofesionalesInscripcion.objects.filter(status=True,estadosolicitud=2,preinscripcion__preinscripcion__periodo = periodo,
                                                                                   empresaempleadora=empresa, departamento = departamento).exclude(id__in=vinculados)
                lista = [{'idP': p.id, 'cedula': p.inscripcion.persona.cedula, 'nombres': p.inscripcion.persona.nombre_completo_inverso(),
                          'carrera':p.inscripcion.carrera.nombre}
                                      for p in practicantes]

                return JsonResponse({"result": "ok", "representante": representante, "cargo": cargo,  "email": email, 'lista':lista})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error en los datos de la empresa."})

        elif action == 'datosnivel':
            try:
                nivel = NivelMalla.objects.get(pk=int(request.POST['id']))
                orden = nivel.orden
                return JsonResponse({"result": "ok", "orden": orden})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error en los datos de la empresa."})

        elif action == 'duplicarsolicitudpractica':
            try:
                practicapreprofesional = PracticasPreprofesionalesInscripcion.objects.get(
                    pk=int(encrypt(request.POST['id'])))
                practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion(
                    inscripcion=practicapreprofesional.inscripcion,
                    tipo=practicapreprofesional.tipo,
                    fechadesde=practicapreprofesional.fechadesde,
                    tiposolicitud=practicapreprofesional.tiposolicitud,
                    empresaempleadora=practicapreprofesional.empresaempleadora,
                    # rotacionmalla=practicapreprofesional.rotacionmalla,
                    fechahasta=practicapreprofesional.fechahasta,
                    # tutorunemi=practicapreprofesional.tutorunemi,
                    # supervisor=practicapreprofesional.supervisor,
                    tutorempresa=practicapreprofesional.tutorempresa,
                    numerohora=practicapreprofesional.numerohora,
                    horahomologacion=practicapreprofesional.horahomologacion,
                    otraempresaempleadora=practicapreprofesional.otraempresaempleadora,
                    tipoinstitucion=practicapreprofesional.tipoinstitucion,
                    sectoreconomico=practicapreprofesional.sectoreconomico,
                    observacion=practicapreprofesional.observacion,
                    # fechaasigtutor=practicapreprofesional.fechaasigtutor,
                    # fechaasigsupervisor=practicapreprofesional.fechaasigsupervisor,
                    departamento=practicapreprofesional.departamento,
                    # periodoevidencia=practicapreprofesional.periodoevidencia,
                    periodoppp=practicapreprofesional.periodoppp,
                    archivo=practicapreprofesional.archivo)
                practicaspreprofesionalesinscripcion.save(request)
                log(
                    u'Duplico la solicitud de practica preprofesionales [%s (Estudiante: %s)-(%s)] a un nuevo registro de solicitud [%s (Estudiante: %s)-(%s)]' % (
                        practicapreprofesional, practicapreprofesional.inscripcion, practicapreprofesional.id,
                        practicaspreprofesionalesinscripcion, practicaspreprofesionalesinscripcion.inscripcion,
                        practicaspreprofesionalesinscripcion.id), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addperevidenciapractica':
            try:
                f = PeriodoEvidenciaPracticaProfesionalesForm(request.POST)
                if f.is_valid():
                    periodo = CabPeriodoEvidenciaPPP(nombre=f.cleaned_data['nombre'],
                                                     fechainicio=f.cleaned_data['fechainicio'],
                                                     evaluarpromedio=f.cleaned_data['evaluarpromedio'],
                                                     fechafin=f.cleaned_data['fechafin'])
                    periodo.save()
                    for carrera in f.cleaned_data['carrera']:
                        periodoevidencia = PeriodoEvidenciaPracticaProfesionales(periodo=periodo,
                                                                                 carrera=carrera)
                        periodoevidencia.save(request)
                    log(u'Adiciono periodo de evidencia de practica pre profesional: %s' % (periodo), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editperevidenciapractica':
            try:
                f = PeriodoEvidenciaPracticaProfesionalesAuxForm(request.POST)
                if f.is_valid():
                    periodoevidencia = CabPeriodoEvidenciaPPP.objects.get(pk=int(encrypt(request.POST['id'])))
                    periodoevidencia.nombre = f.cleaned_data['nombre']
                    periodoevidencia.fechainicio = f.cleaned_data['fechainicio']
                    periodoevidencia.evaluarpromedio = f.cleaned_data['evaluarpromedio']
                    periodoevidencia.fechafin = f.cleaned_data['fechafin']
                    periodoevidencia.save(request)

                    carreras_original = [c for c in PeriodoEvidenciaPracticaProfesionales.objects.values_list('carrera',
                                                                                                              flat=True).filter(
                        periodo=periodoevidencia, status=True)]
                    carreras_formulario = [carrera.id for carrera in f.cleaned_data['carrera']]
                    excluidas = [c for c in carreras_original if c not in carreras_formulario]
                    carreras_quitar = []

                    if len(excluidas) > 0:
                        for c in excluidas:
                            pevid = PeriodoEvidenciaPracticaProfesionales.objects.get(periodo=periodoevidencia,
                                                                                      status=True, carrera_id=c)
                            if not pevid.puede_excluir_carrera():
                                return JsonResponse({"result": "bad",
                                                     "mensaje": "No se puede excluir la carrera %s del listado de carreras." % (
                                                         pevid.carrera.nombre)})
                            else:
                                carreras_quitar.append(c)

                    for carrera in f.cleaned_data['carrera']:
                        # Si la carrera no existe en la tabla
                        if not PeriodoEvidenciaPracticaProfesionales.objects.filter(status=True,
                                                                                    periodo=periodoevidencia,
                                                                                    carrera=carrera).exists():
                            # Crea el periodo de evidencia con la carrera
                            periodoevidencia_ = PeriodoEvidenciaPracticaProfesionales(periodo=periodoevidencia,
                                                                                     carrera=carrera)
                            periodoevidencia_.save(request)
                        # else:
                        #     # Modificar los datos del periodo con la carrera
                        #     periodoevidencia = PeriodoEvidenciaPracticaProfesionales.objects.get(status=True, nombre=nombre, carrera=carrera)
                        #     periodoevidencia.nombre = f.cleaned_data['nombre']
                        #     periodoevidencia.fechainicio = f.cleaned_data['fechainicio']
                        #     periodoevidencia.evaluarpromedio = f.cleaned_data['evaluarpromedio']
                        #     periodoevidencia.fechafin = f.cleaned_data['fechafin']
                        #     periodoevidencia.save(request)
                        log(u'Edito periodo de evidencia de practica pre profesional: %s' % (periodoevidencia), request,
                            "edit")

                    # En caso que haya quitado carreras del listado en el formulario
                    if len(carreras_quitar) > 0:
                        for c in carreras_quitar:
                            p = PeriodoEvidenciaPracticaProfesionales.objects.get(status=True, periodo=periodoevidencia,
                                                                                  carrera_id=c)
                            p.status = False
                            p.save(request)

                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                linea = 'Error en linea {}'.format(sys.exc_info()[-1].tb_lineno)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {ex} - {linea}"})

        elif action == 'delperevidenciapractica':
            try:
                periodoevidencia = CabPeriodoEvidenciaPPP.objects.get(pk=int(encrypt(request.POST['id'])))
                nombre = periodoevidencia.nombre
                if not periodoevidencia.puede_eliminar():
                    return JsonResponse({"result": "bad", "mensaje": "No puede eliminar porque se esta utilizando."})
                periodoevidencia.status = False
                periodoevidencia.save(request)
                log(u'Elimino periodo de evidencia de practica pre profesional: %s' % (periodoevidencia), request,
                    "del")

                # periodoevidencia.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'addevidenciapractica':
            try:
                f = EvidenciaPracticasPreProfesionalForm(request.POST, request.FILES)
                if f.is_valid():
                    periodoevidencia = CabPeriodoEvidenciaPPP.objects.get(pk=int(encrypt(request.POST['id'])))
                    nombre = periodoevidencia.nombre
                    if f.cleaned_data['fechainicio'] > f.cleaned_data['fechafin']:
                        return JsonResponse(
                            {"result": "bad", "mensaje": "La fecha de inicio no puede ser mayor que la fecha fin."})
                    if f.cleaned_data['fechainicio'] < periodoevidencia.fechainicio or f.cleaned_data[
                        'fechafin'] > periodoevidencia.fechafin:
                        return JsonResponse({"result": "bad",
                                             "mensaje": "La fecha de inicio o fecha de fin no puede ser mayor a las fechas del periodo de evidencia."})
                    evidencia = EvidenciaPracticasProfesionales(nombre=f.cleaned_data['nombre'],
                                                                fechainicio=f.cleaned_data['fechainicio'],
                                                                fechafin=f.cleaned_data['fechafin'],
                                                                orden=f.cleaned_data['orden'],
                                                                nombrearchivo=f.cleaned_data['nombrearchivo'],
                                                                configurarfecha=f.cleaned_data['configurarfecha'],
                                                                periodoppp=periodoevidencia,
                                                                puntaje=f.cleaned_data['puntaje'])
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("formato_evidencia_", newfile._name)
                        evidencia.archivo = newfile
                    evidencia.save(request)
                    log(u'Adiciono evidencia de practica pre profesional: %s - %s [PERIODO DE EVIDENCIA - %s]' % (
                        evidencia, evidencia.id, periodoevidencia), request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editevidenciapractica':
            try:
                f = EvidenciaPracticasPreProfesionalForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 15728640:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 15 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf' or ext == '.PDF' or ext == '.doc' or ext == '.docx':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.doc,docx."})
                if f.is_valid():
                    evidencia = EvidenciaPracticasProfesionales.objects.get(pk=int(encrypt(request.POST['id'])))
                    orden = evidencia.orden
                    nombre = evidencia.nombre
                    nombreperiodo = evidencia.periodoppp.nombre
                    if f.cleaned_data['fechainicio'] > f.cleaned_data['fechafin']:
                        return JsonResponse(
                            {"result": "bad", "mensaje": "La fecha de inicio no puede ser mayor que la fecha fin."})
                    if f.cleaned_data['fechainicio'] < evidencia.periodoppp.fechainicio or f.cleaned_data[
                        'fechafin'] > evidencia.periodoppp.fechafin:
                        return JsonResponse({"result": "bad",
                                             "mensaje": "La fecha de inicio o fecha de fin no puede ser mayor a las fechas del periodo de evidencia."})
                    evidencia.nombre = f.cleaned_data['nombre']
                    evidencia.fechainicio = f.cleaned_data['fechainicio']
                    evidencia.fechafin = f.cleaned_data['fechafin']
                    evidencia.puntaje = f.cleaned_data['puntaje']
                    evidencia.configurarfecha = f.cleaned_data['configurarfecha']
                    evidencia.orden = f.cleaned_data['orden']
                    evidencia.nombrearchivo = f.cleaned_data['nombrearchivo']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("formato_evidencia_", newfile._name)
                        evidencia.archivo = newfile
                    evidencia.save(request)
                    log(u'Edito evidencia de practica pre profesional: %s - %s [PERIODO DE EVIDENCIA - %s]' % (
                        evidencia, evidencia.id, evidencia.periodoppp), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delevidenciapractica':
            try:
                evidencia = EvidenciaPracticasProfesionales.objects.get(pk=int(encrypt(request.POST['id'])))
                nombre = evidencia.nombre
                orden = evidencia.orden
                nombreperiodo = evidencia.periodoppp.nombre
                if not evidencia.puede_eliminar():
                    return JsonResponse({"result": "bad", "mensaje": "No puede eliminar porque se esta utilizando."})
                log(u'Elimino evidencia de practica pre profesional: %s - %s [PERIODO DE EVIDENCIA - %s]' % (
                    evidencia, evidencia.id, evidencia.periodoppp), request, "del")
                evidencia.status = False
                evidencia.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'delarchivoevidenciapractica':
            try:
                evidencia = EvidenciaPracticasProfesionales.objects.get(pk=int(encrypt(request.POST['id'])))
                nombre = evidencia.nombre
                orden = evidencia.orden
                nombreperiodo = evidencia.periodoppp.nombre
                for e in EvidenciaPracticasProfesionales.objects.filter(periodoppp__nombre=nombreperiodo, orden=orden,
                                                                        nombre=nombre):
                    e.archivo = None
                    e.save(request)
                    log(u'Elimino archivo evidencia de practica pre profesional: %s - %s [PERIODO DE EVIDENCIA - %s]' % (
                        e.archivo, e.id, e.periodoppp), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'delarchivodetalleevidencia':
            try:
                evidencia = DetalleEvidenciasPracticasPro.objects.get(pk=int(encrypt(request.POST['id'])))
                evidencia.archivo = None
                evidencia.save(request)
                log(
                    u'Elimino archivo en detalle de evidencia de practica pre profesional: %s - %s [PERIODO DE EVIDENCIA - %s] - estudiante[%s]' % (
                        evidencia.archivo, evidencia.id, evidencia.inscripcionpracticas.periodoppp,
                        evidencia.inscripcionpracticas.inscripcion.persona.nombre_completo_inverso()), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'addinformemensual':
            try:
                form = InformeMensualSupervisorPracticaForm(request.POST, request.FILES)
                if not 'archivo' in request.FILES:
                    return JsonResponse({"result": "bad", "mensaje": u"Falta de subir archivo de informe mensual."})
                d = request.FILES['archivo']
                newfilesd = d._name
                ext = newfilesd[newfilesd.rfind("."):]
                if ext == '.pdf' or ext == '.PDF':
                    a = 1
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if d.size > 20971520:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                if form.is_valid():
                    if not form.cleaned_data['carrera']:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar al menos una carrera"})
                    if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"La fecha inicio no puede ser mayor a fecha fin"})
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("informemensualsupervisor", newfile._name)
                    informe = InformeMensualSupervisorPractica(persona=persona,
                                                               fechainicio=form.cleaned_data['fechainicio'],
                                                               fechafin=form.cleaned_data['fechafin'],
                                                               observacion=form.cleaned_data['observacion'],
                                                               archivo=newfile)
                    informe.save(request)
                    for data in form.cleaned_data['carrera']:
                        informe.carrera.add(data)
                        informe.save()
                    log(
                        u'Adiciono supervisor informe mensual de practicas preprofesionales: fecha inicio(%s) - fecha fin(%s) - observacion(%s) - archivo(%s) id[%s]' % (
                            informe.fechainicio, informe.fechafin, informe.observacion, informe.archivo, informe.id),
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editinformemensual':
            try:
                form = InformeMensualSupervisorPracticaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfilesd = d._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if ext == '.pdf' or ext == '.PDF':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                    if d.size > 20971520:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                if form.is_valid():
                    if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"La fecha inicio no puede ser mayor a fecha fin"})
                    if not form.cleaned_data['carrera']:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar al menos una carrera"})
                    informe = InformeMensualSupervisorPractica.objects.get(pk=int(encrypt(request.POST['id'])),
                                                                           persona=persona)
                    informe.fechainicio = form.cleaned_data['fechainicio']
                    informe.fechafin = form.cleaned_data['fechafin']
                    informe.observacion = form.cleaned_data['observacion']
                    informe.carrera.clear()
                    for data in form.cleaned_data['carrera']:
                        informe.carrera.add(data)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("informemensualsupervisor", newfile._name)
                        informe.archivo = newfile
                    informe.save(request)
                    log(
                        u'Edito supervisor informe mensual de practicas preprofesionales: fecha inicio(%s) - fecha fin(%s) - observacion(%s) - archivo(%s) id[%s]' % (
                            informe.fechainicio, informe.fechafin, informe.observacion, informe.archivo, informe.id),
                        request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delinformemensual':
            try:
                informe = InformeMensualSupervisorPractica.objects.get(pk=int(encrypt(request.POST['id'])),
                                                                       persona=persona)
                log(
                    u'Elimino supervisor informe mensual de practicas preprofesionales: fecha inicio(%s) - fecha fin(%s) - observacion(%s) - archivo(%s) id[%s]' % (
                        informe.fechainicio, informe.fechafin, informe.observacion, informe.archivo, informe.id),
                    request,
                    "del")
                informe.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'inscripcionvisitapractica':
            try:
                listacoordinacion = []
                listacarreras = []
                listainscripciones = []
                ids = int(encrypt(request.POST['ids']))
                idd = int(encrypt(request.POST['idd']))
                idcor = int(encrypt(request.POST['idcor']))
                idcar = int(encrypt(request.POST['idcar']))
                cargcor = request.POST['cargcor']
                cargcar = request.POST['cargcar']
                inscripciones = PracticasPreprofesionalesInscripcion.objects.filter(status=True).distinct().order_by(
                    'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                    'inscripcion__persona__nombres')
                # CARGAR POR SUPERVISOR
                if ids > 0:
                    inscripciones = inscripciones.filter(supervisor__id=ids)
                if idd > 0:
                    inscripciones = inscripciones.filter(tutorunemi__id=idd)
                # CARGAR POR COORDINACION
                if cargcor == 'Si':
                    listaidcoordinacion = []
                    if ids > 0:
                        listaidcoordinacion = inscripciones.values_list(
                            'inscripcion__carrera__coordinacion__id').filter(supervisor__id=ids).distinct(
                            'inscripcion__carrera__coordinacion__id').order_by('inscripcion__carrera__coordinacion__id')
                    if idd > 0:
                        listaidcoordinacion = inscripciones.values_list(
                            'inscripcion__carrera__coordinacion__id').filter(tutorunemi__id=idd).distinct(
                            'inscripcion__carrera__coordinacion__id').order_by('inscripcion__carrera__coordinacion__id')
                    coordinaciones = Coordinacion.objects.filter(pk__in=listaidcoordinacion)
                    for coordinacion in coordinaciones:
                        listacoordinacion.append([encrypt(coordinacion.id).__str__(), coordinacion.__str__()])
                else:
                    if idcor > 0:
                        inscripciones = inscripciones.filter(
                            inscripcion__carrera__coordinacion__id=idcor).distinct().order_by(
                            'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                            'inscripcion__persona__nombres')
                # CARGAR POR CARRERA
                if cargcar == 'Si':
                    listaidcarreras = []
                    if idcor > 0:
                        listaidcarreras = inscripciones.values_list('inscripcion__carrera__id').filter(
                            inscripcion__carrera__coordinacion__id=idcor).distinct('inscripcion__carrera__id').order_by(
                            'inscripcion__carrera__id')
                        inscripciones = inscripciones.filter(
                            inscripcion__carrera__coordinacion__id=idcor).distinct().order_by(
                            'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                            'inscripcion__persona__nombres')
                    carreras = Carrera.objects.filter(pk__in=listaidcarreras)
                    for carrera in carreras:
                        listacarreras.append([encrypt(carrera.id).__str__(), carrera.__str__()])
                else:
                    if idcar > 0:
                        inscripciones = inscripciones.filter(inscripcion__carrera__id=idcar).distinct().order_by(
                            'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                            'inscripcion__persona__nombres')
                # CARGAR INSCRIPCIONES
                for inscripcion in inscripciones.values_list('inscripcion__id', 'inscripcion__persona__apellido1',
                                                             'inscripcion__persona__apellido2',
                                                             'inscripcion__persona__nombres').distinct():
                    listainscripciones.append([encrypt(inscripcion[0]).__str__(),
                                               u'%s %s %s' % (inscripcion[1], inscripcion[2], inscripcion[3])])
                return JsonResponse({'result': 'ok', 'coordinacion': listacoordinacion, 'carreras': listacarreras,
                                     'inscripciones': listainscripciones})
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

        elif action == 'addarchivogeneral':
            try:
                form = ArchivoGeneralPracticaPreProfesionalesFrom(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfile = d._name
                    ext = newfile[newfile.rfind("."):]
                    if ext == '.pdf' or ext == '.PDF' or ext == '.doc' or ext == '.docx':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf, .doc, .docx."})
                    if d.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                if form.is_valid():
                    archivogeneral = ArchivoGeneralPracticaPreProfesionales(nombre=form.cleaned_data['nombre'],visible=form.cleaned_data['visible'])
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivogeneralpractica", newfile._name)
                        archivogeneral.archivo = newfile
                    archivogeneral.save(request)
                    archivogeneral.carrera.clear()
                    for carrera in form.cleaned_data['carrera']:
                        archivogeneral.carrera.add(carrera)
                    log(u'Adiciono archivo general de practica pre profesional: %s [%s] - archivo:(%s)' % (
                        archivogeneral, archivogeneral.id, archivogeneral.archivo), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editarchivogeneral':
            try:
                form = ArchivoGeneralPracticaPreProfesionalesFrom(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfile = d._name
                    ext = newfile[newfile.rfind("."):]
                    if ext == '.pdf' or ext == '.PDF' or ext == '.doc' or ext == '.docx':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf, .doc, .docx."})
                    if d.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                if form.is_valid():
                    archivogeneral = ArchivoGeneralPracticaPreProfesionales.objects.get(
                        pk=int(encrypt(request.POST['id'])))
                    archivogeneral.nombre = form.cleaned_data['nombre']
                    archivogeneral.visible = form.cleaned_data['visible']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivogeneralpractica", newfile._name)
                        archivogeneral.archivo = newfile
                    archivogeneral.save(request)
                    archivogeneral.carrera.clear()
                    for carrera in form.cleaned_data['carrera']:
                        archivogeneral.carrera.add(carrera)
                    log(u'Edito archivo general de practica pre profesional: %s [%s] - archivo:(%s)' % (
                        archivogeneral, archivogeneral.id, archivogeneral.archivo), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delarchivogeneral':
            try:
                archivogeneral = ArchivoGeneralPracticaPreProfesionales.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Elimino archivo general de practica pre profesional: %s [%s] - archivo:(%s)' % (
                    archivogeneral, archivogeneral.id, archivogeneral.archivo), request, "del")
                archivogeneral.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'addconfpreinscripcion':
            try:
                f = PreInscripcionPracticasPPForm(request.POST)
                if f.is_valid():
                    if not f.cleaned_data['fechainicio'] <= f.cleaned_data['fechafin']:
                        return JsonResponse(
                            {"result": "bad", "mensaje": "La fecha de inicio no puede ser mayor a la fecha de fin."})
                    if PreInscripcionPracticasPP.objects.filter(fechainicio=f.cleaned_data['fechainicio'], fechafin=f.cleaned_data['fechainicio'], status=True).exclude(coordinacion__in=[1]).exists():
                        return JsonResponse(
                            {"result": "bad", "mensaje": "Ya existe un registro con las misma fechas indicadas"})
                    if not f.cleaned_data['mensaje']:
                        return JsonResponse({"result": "bad", "mensaje": "Ingrese un mensaje"})
                    conf = PreInscripcionPracticasPP(mensaje=f.cleaned_data['mensaje'],
                                                     periodo=f.cleaned_data['periodo'],
                                                     fechainicio=f.cleaned_data['fechainicio'],
                                                     fechafin=f.cleaned_data['fechafin'],
                                                     motivo=f.cleaned_data['motivo'],
                                                     actualizararchivo=f.cleaned_data['actualizararchivo'],
                                                     puede_solicitar=f.cleaned_data['puede_solicitar'],
                                                     puede_asignar=f.cleaned_data['puede_asignar'],
                                                     subirarchivo=f.cleaned_data['subirarchivo'],
                                                     agendatutoria=f.cleaned_data['agendatutoria'],
                                                     fechamaximoagendatutoria=f.cleaned_data['fechamaximoagendatutoria'],
                                                     inglesaprobado = f.cleaned_data['inglesaprobado'],
                                                     computacionaprobado = f.cleaned_data['computacionaprobado']
                                                     )
                    conf.save()
                    # conf.coordinacion = f.cleaned_data['coordinacion']
                    # conf.carrera = f.cleaned_data['carrera']
                    # conf.pregunta = f.cleaned_data['pregunta']
                    if confextra := conf.extrapreinscripcionpracticaspp_set.filter(status=True).first():
                        confextra.enlinea = f.cleaned_data['enlinea']
                    else:
                        confextra = ExtraPreInscripcionPracticasPP(preinscripcion=conf, enlinea=f.cleaned_data['enlinea'])
                        log(u'Adicionó configuaración de pre-inscripción de practicas preprofecionales extra: %s' % (confextra), request, "add")
                    confextra.save(request)
                    for coor in f.cleaned_data['coordinacion']:
                        conf.coordinacion.add(coor)
                    for carr in f.cleaned_data['carrera']:
                        conf.carrera.add(carr)
                    for preg in f.cleaned_data['pregunta']:
                        conf.pregunta.add(preg)
                    conf.save(request)
                    log(u'Adicionó configuaracion de pre-inscripción de practicas preprofecionales: %s' % (conf),
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editconfpreinscripcion':
            try:
                f = PreInscripcionPracticasPPForm(request.POST)
                if f.is_valid():
                    if not f.cleaned_data['fechainicio'] <= f.cleaned_data['fechafin']:
                        return JsonResponse(
                            {"result": "bad", "mensaje": "La fecha de inicio no puede ser mayor a la fecha de fin."})
                    conf = PreInscripcionPracticasPP.objects.get(pk=int(encrypt(request.POST['id'])))
                    if PreInscripcionPracticasPP.objects.filter(fechainicio=f.cleaned_data['fechainicio'],
                                                                fechafin=f.cleaned_data['fechainicio']).exclude(
                        id=conf.id).exists():
                        return JsonResponse(
                            {"result": "bad", "mensaje": "Ya existe un registro con las misma fechas indicadas"})
                    if not f.cleaned_data['mensaje']:
                        return JsonResponse({"result": "bad", "mensaje": "Ingrese un mensaje"})
                    conf.mensaje = f.cleaned_data['mensaje']
                    conf.periodo = f.cleaned_data['periodo']
                    conf.fechainicio = f.cleaned_data['fechainicio']
                    conf.fechafin = f.cleaned_data['fechafin']

                    # conf.coordinacion = f.cleaned_data['coordinacion']
                    conf.coordinacion.clear()
                    for coor in f.cleaned_data['coordinacion']:
                        conf.coordinacion.add(coor)

                    # conf.carrera = f.cleaned_data['carrera']
                    conf.carrera.clear()
                    for carr in f.cleaned_data['carrera']:
                        conf.carrera.add(carr)

                    conf.motivo = f.cleaned_data['motivo']
                    conf.actualizararchivo = f.cleaned_data['actualizararchivo']
                    conf.subirarchivo = f.cleaned_data['subirarchivo']
                    conf.puede_solicitar = f.cleaned_data['puede_solicitar']
                    conf.puede_asignar = f.cleaned_data['puede_asignar']
                    conf.agendatutoria = f.cleaned_data['agendatutoria']
                    if confextra := conf.extrapreinscripcionpracticaspp_set.filter(status=True).first():
                        confextra.enlinea = f.cleaned_data['enlinea']
                        log(u'Editó configuaración de pre-inscripción de practicas preprofecionales extra: %s' % (confextra), request, "edit")
                    else:
                        confextra = ExtraPreInscripcionPracticasPP(preinscripcion=conf, enlinea=f.cleaned_data['enlinea'])
                    confextra.save(request)

                    # conf.pregunta = f.cleaned_data['pregunta']
                    conf.pregunta.clear()
                    for preg in f.cleaned_data['pregunta']:
                        conf.pregunta.add(preg)

                    conf.fechamaximoagendatutoria = f.cleaned_data['fechamaximoagendatutoria']
                    conf.inglesaprobado = f.cleaned_data['inglesaprobado']
                    conf.computacionaprobado = f.cleaned_data['computacionaprobado']
                    conf.save(request)
                    log(u'Editó configuaración de pre-inscripción de practicas preprofecionales: %s' % (conf), request,
                        "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delconfpreinscripcion':
            try:
                conf = PreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                if not conf.puede_eliminar():
                    log(u'Elimino configuaración de pre-inscripción de practicas preprofecionales: %s' % (conf),
                        request, "del")
                    conf.delete()
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'adddetallepreinscripcion':
            try:
                f = DetallePreInscripcionPracticasPPForm(request.POST)
                preinscripcion = PreInscripcionPracticasPP.objects.get(pk=int(encrypt(request.POST['idp'])))

                if int(request.POST['inscripcion']) == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar un alumno."})

                inscripcion = Inscripcion.objects.get(pk=int(request.POST['inscripcion']))
                if not inscripcion.inscripcionmalla_set.filter(status=True):
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"Debe tener mallas asociada para poder inscribirse."})

                # if not inscripcion.puede_preinscribirseppp():

                if inscripcion.cumple_total_parcticapp():
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"Estudiante ya cumplio con las horas requeridas de practicas."})

                if not inscripcion.puede_preinscribirsepppitinerariomalla(request.POST['itinerariomalla']):
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No cumple con todos los requisitos para poder inscribirse."})

                if f.is_valid():
                    inscripcion = Inscripcion.objects.get(pk=f.cleaned_data['inscripcion'])
                    respuestas_id = request.POST.getlist('respuestas')
                    respuestas = RespuestaPreInscripcionPracticasPP.objects.filter(status=True, id__in=respuestas_id)
                    detallerespuesta = DetalleRespuestaPreInscripcionPPP(preinscripcion=preinscripcion,
                                                                         inscripcion=inscripcion)
                    detallerespuesta.save(request)
                    # detallerespuesta.respuesta = respuestas
                    for resp in respuestas:
                        detallerespuesta.respuesta.add(resp)
                    detallerespuesta.save(request)
                    detallepreinscripcion = DetallePreInscripcionPracticasPP(
                        inscripcion=inscripcion,
                        nivelmalla=f.cleaned_data['nivelmalla'],
                        preinscripcion=preinscripcion,
                        fecha=datetime.now(),
                        itinerariomalla_id=f.cleaned_data[
                            'itinerariomalla'] if 'itinerariomalla' in request.POST else None,
                        estado=f.cleaned_data['estado'],
                    )
                    detallepreinscripcion.save(request)
                    log(u'Adicionó detalle de preinscripción prácticas PP: %s' % (detallepreinscripcion),
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'addpreguntapreinscripcion':
            try:
                f = PreguntaPreInscripcionPracticasPPForm(request.POST)
                if f.is_valid():
                    if PreguntaPreInscripcionPracticasPP.objects.filter(status=True, descripcion=f.cleaned_data[
                        'descripcion']).exists():
                        return JsonResponse({"result": "bad", "mensaje": "La pregunta ya existe."})
                    pre = PreguntaPreInscripcionPracticasPP(descripcion=f.cleaned_data['descripcion'],
                                                            activo=f.cleaned_data['activo'])
                    pre.save(request)
                    if 'lista_items1' in request.POST:
                        for lista in json.loads(request.POST['lista_items1']):
                            res = RespuestaPreInscripcionPracticasPP(pregunta=pre, descripcion=lista['resp'],
                                                                     activo=True)
                            res.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editpreguntapreinscripcion':
            try:
                f = PreguntaPreInscripcionPracticasPPForm(request.POST)
                if f.is_valid():
                    pre = PreguntaPreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                    if PreguntaPreInscripcionPracticasPP.objects.filter(status=True, descripcion=f.cleaned_data[
                        'descripcion']).exclude(id=pre.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": "La pregunta ya existe."})
                    pre.descripcion = f.cleaned_data['descripcion']
                    pre.activo = f.cleaned_data['activo']
                    pre.save(request)
                    if 'lista_items1' in request.POST:
                        res = pre.respuestapreinscripcionpracticaspp_set.filter(status=True).exclude(
                            descripcion__in=[(x['resp']) for x in json.loads(request.POST['lista_items1'])])
                        if res:
                            res.delete()
                        for lista in json.loads(request.POST['lista_items1']):
                            if not pre.respuestapreinscripcionpracticaspp_set.filter(status=True, descripcion=lista[
                                'resp']).exists():
                                res = RespuestaPreInscripcionPracticasPP(pregunta=pre, descripcion=lista['resp'],
                                                                         activo=True)
                                res.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delpreguntapreinscripcion':
            try:
                pre = PreguntaPreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                if not pre.puede_eliminar():
                    log(u'Elimino Pregunta para la pre-inscripción de practicas preprofecionales: %s' % pre, request,
                        "del")
                    pre.delete()
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'listarespuestas':
            try:
                lista = []
                pre = PreguntaPreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                for r in pre.respuestas():
                    lista.append([r.descripcion])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'estado_respuesta':
            try:
                res = RespuestaPreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                if res.activo:
                    res.activo = False
                else:
                    res.activo = True
                res.save(request)
                log(u'Edito el estado de la respuesta : %s' % res, request, "edit")
                return JsonResponse({"result": "ok", "activo": res.activo})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'eliminarrespuesta':
            try:
                res = RespuestaPreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                if not res.esta_activa_pregunta():
                    res.delete()
                    log(u'Eliminó la respuesta : %s' % res, request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "La pregunta se encuentra activa."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'preinscriptos_excel':
            try:
                idpre = int(request.POST['id'])
                idcar = int(request.POST['carrera'])
                idfac = int(request.POST['idfac'])
                idest = int(request.POST['estados'])
                docu = int(request.POST['docu'])
                search = request.POST['search']
                if 'id' in request.POST:
                    pre = PreInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
                    if not pre.detallepreinscripcionpracticaspp_set.filter(status=True).exists():
                        return JsonResponse({"result": False, "mensaje": f"No existe datos para generar el reporte"})

                    notifi = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                          titulo='Reporte de Pre-Inscritos de practicas profesionales',
                                          destinatario=persona,
                                          url='',
                                          prioridad=1, app_label='SGA',
                                          fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                          en_proceso=True)
                    notifi.save(request)
                    reporte_preinscriptosexcel(request=request, notiid=notifi.id, idpre=idpre, idcar=idcar, idfac=idfac,idest=idest, docu=docu, search=search).start()
                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte de Preinscritos en (Practicas Pre Profesionales) se está generando. Por favor, verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Hubo un error al obtener datos."})
            except Exception as ex:
                print('Error on line {}, {}'.format(sys.exc_info()[-1].tb_lineno, str(ex)))
                return JsonResponse({"result": "bad", "mensaje": 'Error on line {}, {}'.format(sys.exc_info()[-1].tb_lineno, str(ex))})

        elif action == 'delpreinscripcion':
            try:
                detalle = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                if detalle:
                    if detalle.puede_eliminar_todo(detalle.inscripcion):
                        respuestas = DetalleRespuestaPreInscripcionPPP.objects.filter(inscripcion=detalle.inscripcion,
                                                                                      preinscripcion=detalle.preinscripcion)
                        if respuestas:
                            for r in respuestas:
                                r.delete()
                        detalle.delete()
                    else:
                        detalle.delete()
                    log(u'Eliminó la pre-inscripción de practicas preprofecionales: %s' % detalle, request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'gestionar_preins_masivo':
            try:
                form = PracticasPreprofesionalesInscripcionMasivoEstudianteForm(request.POST)
                if form.is_valid():
                    periodopractica = PreInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
                    idinscritos = request.POST.getlist('inscripciones')
                    cabmasivo = PreinscribirMasivoHistorial(preinscripcion=periodopractica)
                    cabmasivo.save()
                    for idin in idinscritos:
                        preins = DetallePreInscripcionPracticasPP.objects.get(status=True, pk=int(idin))
                        cabmasivo.inscripcion.add(preins)
                        if 'archivo' in request.FILES:
                            arch = request.FILES['archivo']
                            extension = arch._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if arch.size > 4194304:
                                transaction.set_rollback(True)
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                            if not exte.lower() == 'pdf':
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                            preins.archivo = arch
                            preins.fechaarchivo = datetime.now().date()
                            preins.horaarchivo = datetime.now().time()
                            preins.save(request)
                        if int(form.cleaned_data['estadopreinscripcion']) == 2:
                            preins.tipo = form.cleaned_data['tipo']
                            preins.fechadesde = form.cleaned_data['fechadesde']
                            preins.nivelmalla = preins.inscripcion.mi_nivel().nivel
                            preins.itinerariomalla = form.cleaned_data['itinerario']
                            preins.fechahasta = form.cleaned_data['fechahasta']
                            preins.empresaempleadora_id = int(request.POST['empresaempleadora']) if form.cleaned_data['empresaempleadora'] else None
                            preins.otraempresaempleadora = form.cleaned_data['otraempresaempleadora']
                            preins.tutorunemi_id = int(request.POST['tutorunemi']) if form.cleaned_data['tutorunemi'] else None
                            preins.supervisor_id = int(request.POST['supervisor']) if form.cleaned_data['supervisor'] else None
                            preins.numerohora = form.cleaned_data['numerohora']
                            preins.tipoinstitucion = form.cleaned_data['tipoinstitucion']
                            preins.sectoreconomico = form.cleaned_data['sectoreconomico']
                            preins.departamento = form.cleaned_data['departamento']
                            preins.periodoppp = form.cleaned_data['periodoevidencia']
                            preins.convenio = form.cleaned_data['convenio']
                            preins.lugarpractica = form.cleaned_data['lugarpractica']
                            preins.acuerdo = form.cleaned_data['acuerdo']
                            preins.save(request)
                            if preins.recorrido():
                                if not preins.recorrido().estado == int(form.cleaned_data['estadopreinscripcion']):
                                    recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                         fecha=datetime.now().date(),
                                                                                         observacion=form.cleaned_data['observacion'],
                                                                                         estado=form.cleaned_data['estadopreinscripcion'])
                                else:
                                    recorrido = preins.recorrido()
                                    recorrido.observacion = form.cleaned_data['observacion']
                                recorrido.save(request)
                            else:
                                recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                     fecha=datetime.now().date(),
                                                                                     observacion=form.cleaned_data['observacion'],
                                                                                     estado=form.cleaned_data['estadopreinscripcion'])
                                recorrido.save(request)
                            emailestudiante = preins.inscripcion.persona.lista_emails_envio()
                            estudiante = preins.inscripcion.persona.nombre_completo_inverso()

                            if form.cleaned_data['tutorunemi']:
                                idprof = int(form.cleaned_data['tutorunemi'].id)
                                profesor1 = Profesor.objects.get(pk=idprof)
                                asunto = u"ASIGNACIÓN TUTOR ACADÉMICO PRÁCTICAS PREPROFESIONALES "
                                para = profesor1.persona
                                observacion = 'Se le comunica que ha sido designado como tutor académico a (el/la) estudiante: {} de la carrera: {}'.format(
                                    estudiante, preins.inscripcion.carrera)
                                notificacion(asunto, observacion, para, None, '/pro_cronograma?action=listatutorias',
                                             preins.pk, 1, 'sga', DetallePreInscripcionPracticasPP, request)
                            if form.cleaned_data['supervisor']:
                                idprof = int(form.cleaned_data['supervisor'])
                                profesor1 = Profesor.objects.get(pk=idprof)
                                asunto = u"ASIGNACIÓN SUPERVISOR ACADÉMICO PRÁCTICAS PREPROFESIONALES "
                                para = profesor1.persona
                                observacion = 'Se le comunica que ha sido designado como supervisor académico a (el/la) estudiante: {} de la carrera: {}'.format(
                                    estudiante, preins.inscripcion.carrera)
                                notificacion(asunto, observacion, para, None, '/pro_cronograma?action=listasupervision',
                                             preins.pk, 1, 'sga', DetallePreInscripcionPracticasPP, request)

                            asunto = u"Asignación de cupo para Prácticas Preprofesionales"
                            send_html_mail(asunto, "emails/asignacion_cupo_practica.html",
                                           {'sistema': request.session['nombresistema'],
                                            'estudiante': estudiante}, emailestudiante, [],
                                           cuenta=CUENTAS_CORREOS[4][1])
                            log(u'Asignó la pre inscripción: %s a la práctica pre profesional: %s' % (preins, preins),
                                request, "asig")

                            ################ APROBAR LA PRACTICA ################################################
                            practa = PracticasPreprofesionalesInscripcion(preinscripcion=preins,
                                                                          inscripcion=preins.inscripcion,
                                                                          nivelmalla=preins.nivelmatriculamallaid(),
                                                                          itinerariomalla=preins.itinerariomalla if preins.itinerariomalla else None,
                                                                          tipo=preins.tipo,
                                                                          fechadesde=preins.fechadesde,
                                                                          fechahasta=preins.fechahasta,
                                                                          tutorunemi=preins.tutorunemi if preins.tutorunemi else None,
                                                                          supervisor=preins.supervisor if preins.supervisor else None,
                                                                          numerohora=preins.numerohora,
                                                                          tiposolicitud=1,
                                                                          acuerdo=preins.acuerdo,
                                                                          convenio=preins.convenio,
                                                                          lugarpractica=preins.lugarpractica,
                                                                          asignacionempresapractica=form.cleaned_data['asignacionempresapractica'],
                                                                          empresaempleadora=preins.empresaempleadora if preins.empresaempleadora else None,
                                                                          otraempresaempleadora=preins.otraempresaempleadora,
                                                                          tipoinstitucion=preins.tipoinstitucion if preins.tipoinstitucion else None,
                                                                          sectoreconomico=preins.sectoreconomico if preins.sectoreconomico else None,
                                                                          departamento=preins.departamento if preins.departamento else None,
                                                                          periodoppp=preins.periodoppp if preins.periodoppp else None,
                                                                          fechaasigtutor=datetime.now().date(),
                                                                          observacion=form.cleaned_data['observacion'], estadosolicitud=2,
                                                                          fechaasigsupervisor=datetime.now().date())
                            practa.save(request)
                            log(u'El estudiante %s acepto la asignacion de práctica preprofesionales a la empresa: %s' % (
                                preins.inscripcion,
                                preins.empresaempleadora if preins.empresaempleadora else preins.otraempresaempleadora),
                                request,
                                "add")
                            if preins.estado == 2:
                                if not preins.detallerecoridopreinscripcionpracticaspp_set.filter(status=True).exists():
                                    recorridoa = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                          fecha=preins.fecha,
                                                                                          observacion=u'Asignado',
                                                                                          estado=2)
                                    recorridoa.save(request)
                            recorridoa = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                  fecha=datetime.now().date(),
                                                                                  observacion=u'Acepto la asignacion de práctica preprofesionales',
                                                                                  estado=5,
                                                                                  esestudiante=True)
                            recorridoa.save(request)
                            preins.estado = 5
                            preins.save(request)
                        elif int(form.cleaned_data['estadopreinscripcion']) == 3 or int(form.cleaned_data['estadopreinscripcion']) == 4 or int(form.cleaned_data['estadopreinscripcion']) == 6:
                            if preins.recorrido():
                                if not preins.recorrido().estado == int(form.cleaned_data['estadopreinscripcion']):
                                    recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                         fecha=datetime.now().date(),
                                                                                         observacion=form.cleaned_data[
                                                                                             'observacion'],
                                                                                         estado=form.cleaned_data[
                                                                                             'estadopreinscripcion'])
                                    if int(form.cleaned_data['estadopreinscripcion']) == 3:
                                        log(u'Rechazo la pre-inscripción: %s' % preins, request, "rech")
                                    log(u'La puso pendiente la pre-inscripción: %s' % preins, request, "pend")
                                else:
                                    recorrido = preins.recorrido()
                                    recorrido.observacion = form.cleaned_data['observacion']
                                    log(u'La puso pendiente la pre-inscripción: %s' % preins, request, "pend")
                                recorrido.save(request)
                            else:
                                recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                     fecha=datetime.now().date(),
                                                                                     observacion=form.cleaned_data[
                                                                                         'observacion'],
                                                                                     estado=form.cleaned_data[
                                                                                         'estadopreinscripcion'])
                                recorrido.save(request)
                                if int(form.cleaned_data['estadopreinscripcion']) == 3:
                                    log(u'Rechazo la pre-inscripción: %s' % preins, request, "rech")
                                log(u'La puso pendiente la pre-inscripción: %s' % preins, request, "pend")
                        preins.estado = int(form.cleaned_data['estadopreinscripcion'])
                        preins.save(request)
                    cabmasivo.save()
                    return JsonResponse({"result": "ok"})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': "bad", "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                print(ex)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"{str(ex)} Error al guardar los datos."})

        if action == 'gestionar_preins_ind':
            try:
                preins = DetallePreInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
                estadopre = int(request.POST['estadopreinscripcion'])
                if estadopre in [1, 2, 5]:
                    tutor = int(request.POST['tutorunemi']) if 'tutorunemi' in request.POST and not request.POST['tutorunemi'] in [0, '', '0', None] else None
                    if not tutor:
                        raise NameError('Debe seleccionar un tutor')
                    convenio = int(request.POST['convenio'])  if 'convenio' in request.POST and not request.POST['convenio'] in [0, '', '0', None] else None
                    acuerdo = int(request.POST['acuerdo'])  if 'acuerdo' in request.POST and not request.POST['acuerdo'] in [0, '', '0', None] else None
                    empresaempleadora = int(request.POST['empresaempleadora']) if 'empresaempleadora' in request.POST and not request.POST['empresaempleadora'] in [0, '', '0', None] else None
                    if not convenio and not acuerdo and not empresaempleadora:
                        raise NameError('Debe seleccionar entre convenio, acuerdo o empresa empleadora')
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        raise NameError('Error, el tamaño del archivo es mayor a 4 Mb.')
                    if not exte.lower() == 'pdf':
                        raise NameError('Solo se permiten archivos .pdf')
                    preins.archivo = arch
                    preins.fechaarchivo = datetime.now().date()
                    preins.horaarchivo = datetime.now().time()
                    preins.save(request)
                if estadopre == 2:
                    preins.tipo = request.POST['tipo']
                    preins.fechadesde = convertir_fecha(request.POST['fechadesde'])
                    preins.nivelmalla_id = request.POST['nivelmalla']
                    preins.itinerariomalla_id = request.POST['itinerario']
                    preins.fechahasta = convertir_fecha(request.POST['fechahasta'])
                    preins.empresaempleadora_id = int(request.POST['empresaempleadora']) if 'empresaempleadora' in request.POST and not request.POST['empresaempleadora']=='' else None
                    preins.otraempresaempleadora = request.POST['otraempresaempleadora'] if 'otraempresaempleadora' in request.POST else ''
                    preins.tutorunemi_id = int(request.POST['tutorunemi']) if 'tutorunemi' in request.POST and not request.POST['tutorunemi'] in [0, '', '0', None] else None
                    preins.supervisor_id = int(request.POST['supervisor']) if 'supervisor' in request.POST and not request.POST['supervisor'] in [0, '', '0', None] else None
                    preins.numerohora = request.POST['numerohora']
                    preins.tipoinstitucion = int(request.POST['tipoinstitucion']) if 'tipoinstitucion' in request.POST and not request.POST['tipoinstitucion'] == '' else None
                    preins.sectoreconomico = int(request.POST['sectoreconomico']) if 'sectoreconomico' in request.POST and not request.POST['sectoreconomico'] == '' else None
                    preins.departamento_id = int(request.POST['departamento']) if 'departamento' in request.POST and not request.POST['departamento'] == '' else None
                    preins.periodoppp_id = int(request.POST['periodoevidencia']) if 'periodoevidencia' in request.POST and not request.POST['periodoevidencia'] == '' else None
                    preins.convenioempresa_id = int(request.POST['convenio']) if 'convenio' in request.POST and not request.POST['convenio'] == '' else None
                    preins.canton_id = int(request.POST['lugarpractica']) if 'lugarpractica' in request.POST and not request.POST['lugarpractica'] == '' else None
                    preins.save(request)
                    if preins.recorrido():
                        if not preins.recorrido().estado == int(request.POST['estadopreinscripcion']):
                            recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                 fecha=datetime.now().date(),
                                                                                 observacion=request.POST['observacion'],
                                                                                 estado=request.POST['estadopreinscripcion'])
                        else:
                            recorrido = preins.recorrido()
                            recorrido.observacion = request.POST['observacion']
                        recorrido.save(request)
                    else:
                        recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                             fecha=datetime.now().date(),
                                                                             observacion=request.POST['observacion'],
                                                                             estado=request.POST['estadopreinscripcion'])
                        recorrido.save(request)
                    emailestudiante = preins.inscripcion.persona.lista_emails_envio()
                    estudiante = preins.inscripcion.persona.nombre_completo_inverso()

                    if request.POST['tutorunemi']:
                        idprof = int(request.POST['tutorunemi'])
                        profesor1 = Profesor.objects.get(pk=idprof)
                        asunto = u"ASIGNACIÓN TUTOR ACADÉMICO PRÁCTICAS PREPROFESIONALES "
                        para = profesor1.persona
                        observacion = 'Se le comunica que ha sido designado como tutor académico a (el/la) estudiante: {} de la carrera: {}'.format(
                            estudiante, preins.inscripcion.carrera)
                        notificacion(asunto, observacion, para, None, '/pro_cronograma?action=listatutorias',
                                     preins.pk, 1, 'sga', DetallePreInscripcionPracticasPP, request)
                    if request.POST['supervisor']:
                        idprof = int(request.POST['supervisor'])
                        profesor1 = Profesor.objects.filter(pk=idprof).first()
                        if profesor1:
                            asunto = u"ASIGNACIÓN SUPERVISOR ACADÉMICO PRÁCTICAS PREPROFESIONALES "
                            para = profesor1.persona
                            observacion = 'Se le comunica que ha sido designado como supervisor académico a (el/la) estudiante: {} de la carrera: {}'.format(
                                estudiante, preins.inscripcion.carrera)
                            notificacion(asunto, observacion, para, None, '/pro_cronograma?action=listasupervision',
                                         preins.pk, 1, 'sga', DetallePreInscripcionPracticasPP, request)

                    asunto = u"Asignación de cupo para Prácticas Preprofesionales"
                    send_html_mail(asunto, "emails/asignacion_cupo_practica.html",
                                   {'sistema': request.session['nombresistema'],
                                    'estudiante': estudiante}, emailestudiante, [],
                                   cuenta=CUENTAS_CORREOS[4][1])
                    log(u'Asignó la pre inscripción: %s a la práctica pre profesional: %s' % (preins, preins),
                        request, "asig")

                    ################ APROBAR LA PRACTICA ################################################
                    practa = PracticasPreprofesionalesInscripcion(preinscripcion=preins,
                                                                  inscripcion=preins.inscripcion,
                                                                  nivelmalla=preins.nivelmalla,
                                                                  itinerariomalla=preins.itinerariomalla if preins.itinerariomalla else None,
                                                                  tipo=preins.tipo,
                                                                  fechadesde=preins.fechadesde,
                                                                  fechahasta=preins.fechahasta,
                                                                  tutorunemi=preins.tutorunemi,
                                                                  supervisor=preins.supervisor if preins.supervisor else None,
                                                                  numerohora=preins.numerohora,
                                                                  tiposolicitud=1,
                                                                  acuerdo_id=request.POST['acuerdo'] if 'acuerdo' in request.POST and not request.POST['acuerdo'] == '' else None,
                                                                  convenio=preins.convenioempresa,
                                                                  lugarpractica=preins.canton,
                                                                  asignacionempresapractica_id=int(request.POST['asignacionempresapractica']) if 'asignacionempresapractica' in request.POST and not request.POST['asignacionempresapractica'] == '' else None,
                                                                  empresaempleadora=preins.empresaempleadora,
                                                                  otraempresaempleadora=preins.otraempresaempleadora,
                                                                  tipoinstitucion=preins.tipoinstitucion,
                                                                  sectoreconomico=preins.sectoreconomico,
                                                                  departamento=preins.departamento,
                                                                  periodoppp=preins.periodoppp,
                                                                  fechaasigtutor=datetime.now().date(),
                                                                  observacion=request.POST['observacion'], estadosolicitud=2,
                                                                  fechaasigsupervisor=datetime.now().date())
                    practa.save(request)
                    log(u'El estudiante %s acepto la asignacion de práctica preprofesionales a la empresa: %s' % (
                        preins.inscripcion,
                        preins.empresaempleadora if preins.empresaempleadora else preins.otraempresaempleadora),
                        request,
                        "add")
                    if preins.estado == 2:
                        if not preins.detallerecoridopreinscripcionpracticaspp_set.filter(status=True).exists():
                            recorridoa = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                  fecha=preins.fecha,
                                                                                  observacion=u'Asignado',
                                                                                  estado=2)
                            recorridoa.save(request)
                    recorridoa = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                          fecha=datetime.now().date(),
                                                                          observacion=u'Acepto la asignacion de práctica preprofesionales',
                                                                          estado=5,
                                                                          esestudiante=True)
                    recorridoa.save(request)
                    preins.estado = 5
                    preins.save(request)
                elif estadopre in [3, 4, 6, 9, 10]:
                    if preins.recorrido():
                        if not preins.recorrido().estado == int(request.POST['estadopreinscripcion']):
                            recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                 fecha=datetime.now().date(),
                                                                                 observacion=request.POST[
                                                                                     'observacion'],
                                                                                 estado=request.POST[
                                                                                     'estadopreinscripcion'])
                            if estadopre == 3:
                                log(u'Rechazo la pre-inscripción: %s' % preins, request, "rech")
                            elif estadopre == 4:
                                log(u'La puso pendiente la pre-inscripción: %s' % preins, request, "pend")
                            elif estadopre == 9:
                                log(u'La puso En Tramite la pre-inscripción: %s' % preins, request, "tramit")
                            elif estadopre == 10:
                                log(u'La puso Retirado práctica la pre-inscripción: %s' % preins, request, "reti")
                        else:
                            recorrido = preins.recorrido()
                            recorrido.observacion = request.POST['observacion']
                            log(u'La puso pendiente la pre-inscripción: %s' % preins, request, "pend")
                        recorrido.save(request)
                    else:
                        recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                             fecha=datetime.now().date(),
                                                                             observacion=request.POST['observacion'],
                                                                             estado=request.POST['estadopreinscripcion'])
                        recorrido.save(request)
                        if int(request.POST['estadopreinscripcion']) == 3:
                            log(u'Rechazo la pre-inscripción: %s' % preins, request, "rech")
                        log(u'La puso pendiente la pre-inscripción: %s' % preins, request, "pend")
                preins.estado = int(request.POST['estadopreinscripcion'])
                preins.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                print(ex)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {ex}"})

        elif action == 'detalleobservacion':
            try:
                data['pre'] = pre = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                data['detalles'] = pre.detallerecoridopreinscripcionpracticaspp_set.filter(status=True).order_by(
                    '-fecha')
                template = get_template("alu_practicaspreprofesionalesinscripcion/detalleobservacion.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'detalleobservacionempresas':
            try:
                data['pre'] = pre = DatosEmpresaPreInscripcionPracticasPP.objects.get(id=int(request.POST['id']))
                data['detalles'] = pre.preinscripcion.detallerecoridopreinscripcionpracticaspp_set.filter(status=True).order_by(
                    '-fecha')
                template = get_template("alu_practicaspreprofesionalesinscripcion/detalleobsempresas.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'gestionar_preins_indmasivo':
            try:
                form = PracticasPreprofesionalesInscripcionForm(request.POST)
                if form.is_valid():
                    cadena = request.POST['id'].split("_")
                    preinscripcion = PreInscripcionPracticasPP.objects.get(status=True, pk=cadena[0])
                    preinscripciones = preinscripcion.detallepreinscripcionpracticaspp_set.filter(
                        inscripcion__carrera__id=cadena[1], estado=cadena[2], status=True).order_by(
                        'inscripcion__persona__nombres', 'inscripcion__persona__apellido1')
                    if int(form.cleaned_data['estadopreinscripcion']) == 2:
                        for preins in preinscripciones:
                            d = preins.id
                            preins.tipo = form.cleaned_data['tipo']
                            preins.fechadesde = form.cleaned_data['fechadesde']
                            preins.fechahasta = form.cleaned_data['fechahasta']
                            preins.empresaempleadora_id = int(request.POST['empresaempleadora']) if form.cleaned_data[
                                'empresaempleadora'] else None
                            preins.otraempresaempleadora = form.cleaned_data['otraempresaempleadora']
                            if preins.itinerariomalla:
                                preins.numerohora = preins.itinerariomalla.horas_practicas
                            else:
                                preins.numerohora = 0
                            preins.tipoinstitucion = form.cleaned_data['tipoinstitucion']
                            preins.sectoreconomico = form.cleaned_data['sectoreconomico']
                            preins.periodoppp = form.cleaned_data['periodoevidencia']
                            preins.acuerdo = form.cleaned_data['acuerdo']
                            preins.convenio = form.cleaned_data['convenio']
                            preins.lugarpractica = form.cleaned_data['lugarpractica']
                            preins.save(request)
                            if preins.recorrido():
                                if not preins.recorrido().estado == int(form.cleaned_data['estadopreinscripcion']):
                                    recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                         fecha=datetime.now().date(),
                                                                                         observacion='',
                                                                                         estado=form.cleaned_data[
                                                                                             'estadopreinscripcion'])
                                else:
                                    recorrido = preins.recorrido()
                                    recorrido.observacion = form.cleaned_data['observacion']
                                recorrido.save(request)
                            else:
                                recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                     fecha=datetime.now().date(),
                                                                                     observacion='',
                                                                                     estado=form.cleaned_data[
                                                                                         'estadopreinscripcion'])
                                recorrido.save(request)
                            preins.estado = int(form.cleaned_data['estadopreinscripcion'])
                            preins.save(request)
                            pract = PracticasPreprofesionalesInscripcion(preinscripcion=preins,
                                                                         inscripcion=preins.inscripcion,
                                                                         itinerariomalla=preins.itinerariomalla if preins.itinerariomalla else None,
                                                                         tipo=preins.tipo,
                                                                         fechadesde=preins.fechadesde,
                                                                         fechahasta=preins.fechahasta,
                                                                         tutorunemi=preins.tutorunemi if preins.tutorunemi else None,
                                                                         supervisor=preins.supervisor if preins.supervisor else None,
                                                                         numerohora=preins.numerohora,
                                                                         tiposolicitud=1,
                                                                         acuerdo=preins.acuerdo,
                                                                         convenio=preins.convenio,
                                                                         lugarpractica=preins.lugarpractica,
                                                                         empresaempleadora=preins.empresaempleadora if preins.empresaempleadora else None,
                                                                         otraempresaempleadora=preins.otraempresaempleadora,
                                                                         tipoinstitucion=preins.tipoinstitucion if preins.tipoinstitucion else None,
                                                                         sectoreconomico=preins.sectoreconomico if preins.sectoreconomico else None,
                                                                         departamento=preins.departamento if preins.departamento else None,
                                                                         periodoppp=preins.periodoppp if preins.periodoppp else None,
                                                                         fechaasigtutor=datetime.now().date(),
                                                                         fechaasigsupervisor=datetime.now().date())
                            pract.save(request)
                            if preins.estado == 2:
                                if not preins.detallerecoridopreinscripcionpracticaspp_set.filter(status=True).exists():
                                    recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                         fecha=preins.fecha,
                                                                                         observacion=u'Asignado',
                                                                                         estado=2)
                                    recorrido.save(request)
                            recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                 fecha=datetime.now().date(),
                                                                                 observacion=u'Acepto la asignacion de práctica preprofesionales',
                                                                                 estado=5,
                                                                                 esestudiante=True)
                            recorrido.save(request)
                            preins.estado = 5
                            preins.save(request)

                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'datacargodirector':
            try:
                from sagest.models import Departamento, DistributivoPersona, DenominacionPuesto
                lista = []
                # carreras = Carrera.objects.filter(coordinacion__id__in=json.loads(request.POST['idc']))
                # departamento = Departamento.objects.filter(responsable_id=json.loads(request.POST['id_director']))
                distributivo = DistributivoPersona.objects.filter(persona__id=json.loads(request.POST['id_director']))[
                    0]
                cargo = distributivo.denominacionpuesto
                lista.append([cargo.id, cargo.__str__()])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'adddirectorvinculacion':
            try:
                form = DirectorVinculacionFirmaForm(request.POST)
                if form.is_valid():

                    if 'archivo' in request.FILES:
                        d = request.FILES['archivo']
                        newfile = d._name
                        ext = newfile[newfile.rfind("."):]
                        if ext == '.png' or ext == '.PNG':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .png .PNG"})
                        if d.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                    if form.cleaned_data['desde'] > form.cleaned_data['hasta']:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, La fecha desde debe ser menor de la fecha hasta ."})
                    if form.cleaned_data['esprincipal']:
                        if ConfiguracionFirmaPracticasPreprofesionales.objects.filter(status=True, esprincipal=True).exists():
                            dir = ConfiguracionFirmaPracticasPreprofesionales.objects.filter(status=True, esprincipal=True).first()
                            dir.esprincipal = False
                            dir.save()
                    add = ConfiguracionFirmaPracticasPreprofesionales(nombres=form.cleaned_data['nombres'],
                                                                      cargo=form.cleaned_data['cargo'],
                                                                      activo=form.cleaned_data['activo'],
                                                                      desde=form.cleaned_data['desde'],
                                                                      hasta=form.cleaned_data['hasta'],
                                                                      esprincipal=form.cleaned_data['esprincipal'])
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivofirmadirector", newfile._name)
                        add.archivo = newfile

                    add.save(request)
                    log(u'Adicionó Firmas del Personal de Vinculacion : %s' % (add), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editdirectorvinculacion':
            try:
                form = DirectorVinculacionFirmaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfile = d._name
                    ext = newfile[newfile.rfind("."):]
                    if ext == '.png' or ext == '.PNG':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .png .PNG"})
                    if d.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})

                if form.is_valid():
                    if form.cleaned_data['desde'] > form.cleaned_data['hasta']:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, La fecha desde debe ser menor de la fecha hasta ."})
                    edit = ConfiguracionFirmaPracticasPreprofesionales.objects.get(pk=int(encrypt(request.POST['id'])))
                    edit.nombres = form.cleaned_data['nombres']
                    edit.cargo = form.cleaned_data['cargo']
                    edit.desde = form.cleaned_data['desde']
                    edit.hasta = form.cleaned_data['hasta']
                    edit.activo = form.cleaned_data['activo']
                    if form.cleaned_data['esprincipal']:
                        if ConfiguracionFirmaPracticasPreprofesionales.objects.filter(status=True, esprincipal=True).exists():
                            dir = ConfiguracionFirmaPracticasPreprofesionales.objects.filter(status=True, esprincipal=True).first()
                            dir.esprincipal = False
                            dir.save()
                    edit.esprincipal = form.cleaned_data['esprincipal']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivofirmadirector", newfile._name)
                        edit.archivo = newfile
                    edit.save(request)
                    log(u'Edito Firmas del Personal Vinculación: (%s)' % (edit), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'deletedirectorvinculacion':
            try:
                firma = ConfiguracionFirmaPracticasPreprofesionales.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Eliminó Firmas del personal de vinculacion: %s' % firma, request, "del")
                firma.status = False
                firma.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})


        elif action == 'addcartavinculacion':

            try:

                if not json.loads(request.POST['lista_items1']):
                    return JsonResponse({"result": "bad", "mensaje": u"Debe tener al menos un estudiante"})
                else:
                    estudiantes = json.loads(request.POST['lista_items1'])

                if not (request.POST['convenio'] or request.POST['acuerdo'] or request.POST['empresaempleadora']):
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"Debe indicar hacia quien va dirigido el documento"})

                form = CartaVinculacionForm(request.POST)
                if form.is_valid():
                    year = datetime.now().strftime('%Y')
                    if form.cleaned_data['memorandum']:
                        numsolicitudporanio = CartaVinculacionPracticasPreprofesionales.objects.filter(memorandum=True, fecha_creacion__year=year).count() + 1
                        nomenclatura = '-MEM'

                    else:
                        numsolicitudporanio = CartaVinculacionPracticasPreprofesionales.objects.filter(memorandum=False, fecha_creacion__year=year).count() + 1
                        nomenclatura = '-OF'

                    codsolicitud = generar_codigo(numsolicitudporanio, PREFIX, SUFFIX)

                    email = form.cleaned_data['email']
                    if email:
                        emailnue = EmpresaEmpleadora.objects.filter(email=email).first()
                        if emailnue:
                            emailnue.email = form.cleaned_data['email']
                            emailnue.save(request)
                        else:
                            emailnue = EmpresaEmpleadora(email=form.cleaned_data['email'])
                            emailnue.save(request)

                    cartavinculacion = CartaVinculacionPracticasPreprofesionales(

                        memo=codsolicitud + nomenclatura,
                        fecha=form.cleaned_data['fecha'],
                        convenio=form.cleaned_data['convenio'],
                        acuerdo=form.cleaned_data['acuerdo'],
                        empresa=form.cleaned_data['empresaempleadora'],
                        departamento=form.cleaned_data['departamento'],
                        representante=form.cleaned_data['representante'],
                        cargo=form.cleaned_data['cargo'],
                        director=form.cleaned_data['director'],
                        memorandum=form.cleaned_data['memorandum'],
                        email=emailnue.email,
                        email1=form.cleaned_data['email1'],
                        email2=form.cleaned_data['email2'],
                        email3=form.cleaned_data['email3']
                    )

                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("cartavinculacion", newfile._name)
                        cartavinculacion.archivo = newfile

                    cartavinculacion.save(request)

                    # listadoinscripciones = PracticasPreprofesionalesInscripcion.objects.filter(
                    #     id__in=[idP for idP in estudiantes])
                    # listadoitinerarios = ItinerariosMalla.objects.filter(
                    #     id__in=[int(datos['id']) for datos in itinerarios])

                    for inscripcion in estudiantes:
                        detalle = DetalleCartaInscripcion(
                            carta=cartavinculacion,
                            inscripcion=PracticasPreprofesionalesInscripcion.objects.get(pk=inscripcion)
                        )
                        detalle.save()

                    # for itinenario in listadoitinerarios:
                    #     detalle = DetalleCartaItinerario(
                    #         carta=cartavinculacion,
                    #         itinerariomalla=itinenario
                    #     )
                    #     detalle.save()

                    log(u'Adiciono carta de vinculacion: %s [%s] - archivo:(%s)' % (

                        cartavinculacion, cartavinculacion.id, cartavinculacion.archivo), request, "add")

                    return JsonResponse({"result": "ok"})

                else:

                    raise NameError('Error')

            except Exception as ex:

                error_str = f'{str(ex)} - Error on line {sys.exc_info()[-1].tb_lineno}'

                transaction.set_rollback(True)

                return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {error_str}"})

        elif action == 'editcartavinculacion':
            try:
                if not json.loads(request.POST['lista_items1']):
                    return JsonResponse({"result": "bad", "mensaje": u"Debe tener al menos un estudiante"})
                else:
                    estudiantes = json.loads(request.POST['lista_items1'])

                if not (request.POST['convenio'] or request.POST['acuerdo']):
                    return JsonResponse({"result": "bad", "mensaje": u"Debe tener al menos un convenio o acuerdo."})

                form = CartaVinculacionForm(request.POST)
                if form.is_valid():
                    cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.get(pk=int(encrypt(request.POST['id'])))
                    cartavinculacion.fecha = form.cleaned_data['fecha']
                    cartavinculacion.director = form.cleaned_data['director']
                    cartavinculacion.representante = form.cleaned_data['representante']
                    cartavinculacion.cargo = form.cleaned_data['cargo']
                    cartavinculacion.email = form.cleaned_data['email']
                    cartavinculacion.email1 = form.cleaned_data['email1']
                    cartavinculacion.email2 = form.cleaned_data['email2']
                    cartavinculacion.email3 = form.cleaned_data['email3']
                    cartavinculacion.save(request)
                    cartavinculacion.detallecartainscripcion_set.all().delete()
                    listadoinscripciones = PracticasPreprofesionalesInscripcion.objects.filter(
                        id__in=[int(datos['id']) for datos in estudiantes])
                    for inscripcion in listadoinscripciones:
                        detalle = DetalleCartaInscripcion(
                            carta=cartavinculacion,
                            inscripcion=inscripcion)
                        detalle.save()

                    log(u'Modificó carta de vinculacion: %s [%s]' % (cartavinculacion, cartavinculacion.id), request, "edit")

                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delcartavinculacion':
            try:
                cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.get(pk=int(request.POST['id']))
                cartavinculacion.status = False
                cartavinculacion.save()
                cartavinculacion.detallecartainscripcion_set.all().update(status=False)
                cartavinculacion.detallecartaitinerario_set.all().update(status=False)
                log(u'Cambió estado [status=False] de carta de vinculación : %s' % cartavinculacion, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'gestionar_preins_indmasivosalud':
            try:
                form = PracticasPreprofesionalesInscripcionForm(request.POST)
                if form.is_valid():
                    preins = DetallePreInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
                    if 'archivo' in request.FILES:
                        arch = request.FILES['archivo']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 4194304:
                            transaction.set_rollback(True)
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                        if not exte.lower() == 'pdf':
                            transaction.set_rollback(True)
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                        preins.archivo = arch
                        preins.fechaarchivo = datetime.now().date()
                        preins.horaarchivo = datetime.now().time()
                        preins.save(request)
                    if int(form.cleaned_data['estadopreinscripcion']) == 2:
                        preins.tipo = form.cleaned_data['tipo']
                        preins.fechadesde = form.cleaned_data['fechadesde']
                        preins.nivelmalla = form.cleaned_data['nivelmalla']
                        preins.itinerariomalla = form.cleaned_data['itinerario']
                        preins.fechahasta = form.cleaned_data['fechahasta']
                        preins.empresaempleadora_id = int(request.POST['empresaempleadora']) if form.cleaned_data['empresaempleadora'] else None
                        preins.otraempresaempleadora = form.cleaned_data['otraempresaempleadora']
                        preins.tutorunemi_id = int(request.POST['tutorunemi']) if form.cleaned_data['tutorunemi'] else None
                        preins.supervisor_id = int(request.POST['supervisor']) if form.cleaned_data['supervisor'] else None
                        preins.numerohora = form.cleaned_data['numerohora']
                        preins.tipoinstitucion = form.cleaned_data['tipoinstitucion']
                        preins.sectoreconomico = form.cleaned_data['sectoreconomico']
                        preins.departamento = form.cleaned_data['departamento']
                        preins.periodoppp = form.cleaned_data['periodoevidencia']
                        preins.convenio = form.cleaned_data['convenio']
                        preins.lugarpractica = form.cleaned_data['lugarpractica']
                        preins.acuerdo = form.cleaned_data['acuerdo']
                        preins.save(request)
                        if preins.recorrido():
                            if not preins.recorrido().estado == int(form.cleaned_data['estadopreinscripcion']):
                                recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                     fecha=datetime.now().date(),
                                                                                     observacion=form.cleaned_data['observacion'],
                                                                                     estado=form.cleaned_data['estadopreinscripcion'])
                            else:
                                recorrido = preins.recorrido()
                                recorrido.observacion = form.cleaned_data['observacion']
                            recorrido.save(request)
                        else:
                            recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                 fecha=datetime.now().date(),
                                                                                 observacion=form.cleaned_data['observacion'],
                                                                                 estado=form.cleaned_data['estadopreinscripcion'])
                            recorrido.save(request)
                        emailestudiante = preins.inscripcion.persona.lista_emails_envio()
                        estudiante = preins.inscripcion.persona.nombre_completo_inverso()

                        if form.cleaned_data['tutorunemi']:
                            idprof = int(form.cleaned_data['tutorunemi'].id)
                            profesor1 = Profesor.objects.get(pk=idprof)
                            asunto = u"ASIGNACIÓN TUTOR ACADÉMICO PRÁCTICAS PREPROFESIONALES "
                            para = profesor1.persona
                            observacion = 'Se le comunica que ha sido designado como tutor académico a (el/la) estudiante: {} de la carrera: {}'.format(
                                estudiante, preins.inscripcion.carrera)
                            notificacion(asunto, observacion, para, None, '/pro_cronograma?action=listatutorias',
                                         preins.pk, 1, 'sga', DetallePreInscripcionPracticasPP, request)
                        if form.cleaned_data['supervisor']:
                            idprof = int(form.cleaned_data['supervisor'])
                            profesor1 = Profesor.objects.get(pk=idprof)
                            asunto = u"ASIGNACIÓN SUPERVISOR ACADÉMICO PRÁCTICAS PREPROFESIONALES "
                            para = profesor1.persona
                            observacion = 'Se le comunica que ha sido designado como supervisor académico a (el/la) estudiante: {} de la carrera: {}'.format(
                                estudiante, preins.inscripcion.carrera)
                            notificacion(asunto, observacion, para, None, '/pro_cronograma?action=listasupervision',
                                         preins.pk, 1, 'sga', DetallePreInscripcionPracticasPP, request)

                        asunto = u"Asignación de cupo para Prácticas Preprofesionales"
                        send_html_mail(asunto, "emails/asignacion_cupo_practica.html",
                                       {'sistema': request.session['nombresistema'],
                                        'estudiante': estudiante}, emailestudiante, [],
                                       cuenta=CUENTAS_CORREOS[4][1])
                        log(u'Asignó la pre inscripción: %s a la práctica pre profesional: %s' % (preins, preins),
                            request, "asig")

                        ################ APROBAR LA PRACTICA ################################################
                        practa = PracticasPreprofesionalesInscripcion(preinscripcion=preins,
                                                                      inscripcion=preins.inscripcion,
                                                                      nivelmalla=preins.nivelmalla,
                                                                      itinerariomalla=preins.itinerariomalla if preins.itinerariomalla else None,
                                                                      tipo=preins.tipo,
                                                                      fechadesde=preins.fechadesde,
                                                                      fechahasta=preins.fechahasta,
                                                                      tutorunemi=preins.tutorunemi if preins.tutorunemi else None,
                                                                      supervisor=preins.supervisor if preins.supervisor else None,
                                                                      numerohora=preins.numerohora,
                                                                      tiposolicitud=1,
                                                                      acuerdo=preins.acuerdo,
                                                                      convenio=preins.convenio,
                                                                      lugarpractica=preins.lugarpractica,
                                                                      asignacionempresapractica=form.cleaned_data['asignacionempresapractica'],
                                                                      empresaempleadora=preins.empresaempleadora if preins.empresaempleadora else None,
                                                                      otraempresaempleadora=preins.otraempresaempleadora,
                                                                      tipoinstitucion=preins.tipoinstitucion if preins.tipoinstitucion else None,
                                                                      sectoreconomico=preins.sectoreconomico if preins.sectoreconomico else None,
                                                                      departamento=preins.departamento if preins.departamento else None,
                                                                      periodoppp=preins.periodoppp if preins.periodoppp else None,
                                                                      fechaasigtutor=datetime.now().date(),
                                                                      observacion=form.cleaned_data['observacion'], estadosolicitud=2,
                                                                      fechaasigsupervisor=datetime.now().date())
                        practa.save(request)
                        log(u'El estudiante %s acepto la asignacion de práctica preprofesionales a la empresa: %s' % (
                            preins.inscripcion,
                            preins.empresaempleadora if preins.empresaempleadora else preins.otraempresaempleadora),
                            request,
                            "add")
                        if preins.estado == 2:
                            if not preins.detallerecoridopreinscripcionpracticaspp_set.filter(status=True).exists():
                                recorridoa = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                      fecha=preins.fecha,
                                                                                      observacion=u'Asignado',
                                                                                      estado=2)
                                recorridoa.save(request)
                        recorridoa = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                              fecha=datetime.now().date(),
                                                                              observacion=u'Acepto la asignacion de práctica preprofesionales',
                                                                              estado=5,
                                                                              esestudiante=True)
                        recorridoa.save(request)
                        preins.estado = 5
                        preins.save(request)
                    elif int(form.cleaned_data['estadopreinscripcion']) == 3 or int(form.cleaned_data['estadopreinscripcion']) == 4:
                        if preins.recorrido():
                            if not preins.recorrido().estado == int(form.cleaned_data['estadopreinscripcion']):
                                recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                     fecha=datetime.now().date(),
                                                                                     observacion=form.cleaned_data[
                                                                                         'observacion'],
                                                                                     estado=form.cleaned_data[
                                                                                         'estadopreinscripcion'])
                                if int(form.cleaned_data['estadopreinscripcion']) == 3:
                                    log(u'Rechazo la pre-inscripción: %s' % preins, request, "rech")
                                log(u'La puso pendiente la pre-inscripción: %s' % preins, request, "pend")
                            else:
                                recorrido = preins.recorrido()
                                recorrido.observacion = form.cleaned_data['observacion']
                                log(u'La puso pendiente la pre-inscripción: %s' % preins, request, "pend")
                            recorrido.save(request)
                        else:
                            recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                 fecha=datetime.now().date(),
                                                                                 observacion=form.cleaned_data[
                                                                                     'observacion'],
                                                                                 estado=form.cleaned_data[
                                                                                     'estadopreinscripcion'])
                            recorrido.save(request)
                            if int(form.cleaned_data['estadopreinscripcion']) == 3:
                                log(u'Rechazo la pre-inscripción: %s' % preins, request, "rech")
                            log(u'La puso pendiente la pre-inscripción: %s' % preins, request, "pend")
                    preins.estado = int(form.cleaned_data['estadopreinscripcion'])
                    preins.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                print(ex)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})



        elif action == 'addconfevidenciahomologacion':
            try:
                form = ConfiguracionEvidenciaHomologacionPracticaForm(request.POST)
                if form.is_valid():
                    configuracionevidencia = ConfiguracionEvidenciaHomologacionPractica(
                        nombre=form.cleaned_data['nombre']
                    )
                    configuracionevidencia.save(request)
                    configuracionevidencia.carrera = form.cleaned_data['carrera']
                    configuracionevidencia.save(request)
                    log(u'Adiciono configuración de evidencia: %s [%s]' % (configuracionevidencia, configuracionevidencia.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editconfevidenciahomologacion':
            try:
                form = ConfiguracionEvidenciaHomologacionPracticaForm(request.POST)
                if form.is_valid():
                    configuracionevidencia = ConfiguracionEvidenciaHomologacionPractica.objects.get(
                        pk=int(encrypt(request.POST['id'])))
                    configuracionevidencia.nombre = form.cleaned_data['nombre']
                    configuracionevidencia.save(request)
                    configuracionevidencia.carrera = form.cleaned_data['carrera']
                    configuracionevidencia.save(request)
                    log(u'Modificó configuración de evidencia homologación: %s [%s]' % (
                        configuracionevidencia, configuracionevidencia.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delconfevidenciahomologacion':
            try:
                configuracionevidencia = ConfiguracionEvidenciaHomologacionPractica.objects.get(
                    pk=int(encrypt(request.POST['id'])))
                configuracionevidencia.status = False
                configuracionevidencia.evidenciahomologacionpractica_set.update(status=False)
                configuracionevidencia.save()
                log(u'Cambió estado [status=False] de configuración de evidencia homologación : %s' % configuracionevidencia,
                    request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'addevidenciahomologacion':
            try:
                f = EvidenciaHomologacionPracticaForm(request.POST, request.FILES)
                if f.is_valid():
                    configuracionevidencia = ConfiguracionEvidenciaHomologacionPractica.objects.get(
                        pk=int(encrypt(request.POST['id'])))
                    if f.cleaned_data['fechainicio'] > f.cleaned_data['fechafin']:
                        return JsonResponse(
                            {"result": "bad", "mensaje": "La fecha de inicio no puede ser mayor que la fecha fin."})
                    evidencia = EvidenciaHomologacionPractica(nombre=f.cleaned_data['nombre'],
                                                              fechainicio=f.cleaned_data['fechainicio'],
                                                              fechafin=f.cleaned_data['fechafin'],
                                                              orden=f.cleaned_data['orden'],
                                                              nombrearchivo=f.cleaned_data['nombrearchivo'],
                                                              configurarfecha=f.cleaned_data['configurarfecha'],
                                                              configuracionevidencia=configuracionevidencia
                                                              )
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("formato_evidencia_", newfile._name)
                        evidencia.archivo = newfile
                    evidencia.save(request)
                    log(u'Adiciono evidencia de homologación para practica pre profesional: %s - %s [CONFIGURACIÓN DE EVIDENCIA - %s]' % (
                        evidencia, evidencia.id, configuracionevidencia), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editevidenciahomologacion':
            try:
                f = EvidenciaHomologacionPracticaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 15728640:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 15 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf' or ext == '.PDF' or ext == '.doc' or ext == '.docx':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.doc,docx."})
                if f.is_valid():
                    evidencia = EvidenciaHomologacionPractica.objects.get(pk=int(encrypt(request.POST['id'])))
                    if f.cleaned_data['fechainicio'] > f.cleaned_data['fechafin']:
                        return JsonResponse(
                            {"result": "bad", "mensaje": "La fecha de inicio no puede ser mayor que la fecha fin."})
                    evidencia.nombre = f.cleaned_data['nombre']
                    evidencia.fechainicio = f.cleaned_data['fechainicio']
                    evidencia.fechafin = f.cleaned_data['fechafin']
                    evidencia.configurarfecha = f.cleaned_data['configurarfecha']
                    evidencia.orden = f.cleaned_data['orden']
                    evidencia.nombrearchivo = f.cleaned_data['nombrearchivo']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("formato_evidencia_", newfile._name)
                        evidencia.archivo = newfile
                    else:
                        if 'archivo-clear' in request.POST:
                            evidencia.archivo.delete()
                    evidencia.save(request)
                    log(u'Modificó evidencia de homologación para practica pre profesional: %s - %s [CONFIGURACIÓN DE EVIDENCIA - %s]' % (
                        evidencia, evidencia.id, evidencia.configuracionevidencia), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delevidenciahomologacion':
            try:
                evidencia = EvidenciaHomologacionPractica.objects.get(pk=int(encrypt(request.POST['id'])))
                evidencia.status = False
                evidencia.save()
                log(u'Cambió estado [status=False] de  evidencia de homologación para practica pre profesional: %s - %s [CONFIGURACIÓN DE EVIDENCIA - %s]' % (
                    evidencia, evidencia.id, evidencia.configuracionevidencia), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delarchivoevidenciahomologacion':
            try:
                evidencia = EvidenciaHomologacionPractica.objects.get(pk=int(encrypt(request.POST['id'])))
                evidencia.archivo.delete()
                evidencia.save(request)
                log(u'Elimino archivo evidencia de homologación para practica pre profesional: %s - %s [CONFIGURACIÓN DE EVIDENCIA - %s]' % (
                    evidencia.archivo, evidencia.id, evidencia.configuracionevidencia), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'cargararchivoinforme':
            try:
                carrera = Carrera.objects.get(pk=int(encrypt(request.POST['idcarrera'])))
                aperturapractica = AperturaPracticaPreProfesional.objects.get(
                    pk=int(encrypt(request.POST['idapertura'])))
                f = ArchivoHomologacionPracticaForm(request.POST, request.FILES)
                d = request.FILES['archivo']
                newfilesd = d._name
                ext = newfilesd[newfilesd.rfind("."):]
                if ext == '.pdf' or ext == '.PDF':
                    a = 1
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if d.size > 20971520:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                if f.is_valid():
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("informehomologacion", newfile._name)
                    if InformeHomologacionCarrera.objects.filter(carrera=carrera,
                                                                 aperturapractica=aperturapractica).exists():
                        informehomologacion = InformeHomologacionCarrera.objects.get(carrera=carrera,
                                                                                     aperturapractica=aperturapractica)
                        informehomologacion.descripcioninforme = f.cleaned_data['descripcion']
                        informehomologacion.informe = newfile
                        informehomologacion.save(request)
                    else:
                        informehomologacion = InformeHomologacionCarrera(carrera=carrera,
                                                                         aperturapractica=aperturapractica,
                                                                         descripcioninforme=f.cleaned_data[
                                                                             'descripcion'], informe=newfile)
                        informehomologacion.save(request)
                    log(u'Adiciono archivo de informe de práctica profesionales: %s [%s]' % (
                        informehomologacion, informehomologacion.id), request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cargararchivoresolucion':
            try:
                carrera = Carrera.objects.get(pk=int(encrypt(request.POST['idcarrera'])))
                aperturapractica = AperturaPracticaPreProfesional.objects.get(
                    pk=int(encrypt(request.POST['idapertura'])))
                f = ArchivoHomologacionPracticaForm(request.POST, request.FILES)
                d = request.FILES['archivo']
                newfilesd = d._name
                ext = newfilesd[newfilesd.rfind("."):]
                if ext == '.pdf' or ext == '.PDF':
                    a = 1
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if d.size > 20971520:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                if f.is_valid():
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("resolucionhomologacion", newfile._name)
                    if InformeHomologacionCarrera.objects.filter(carrera=carrera,
                                                                 aperturapractica=aperturapractica).exists():
                        informehomologacion = InformeHomologacionCarrera.objects.get(carrera=carrera,
                                                                                     aperturapractica=aperturapractica)
                        informehomologacion.descripcionresolucion = f.cleaned_data['descripcion']
                        informehomologacion.resolucion = newfile
                        informehomologacion.save(request)
                    else:
                        informehomologacion = InformeHomologacionCarrera(carrera=carrera,
                                                                         aperturapractica=aperturapractica,
                                                                         descripcionresolucion=f.cleaned_data[
                                                                             'descripcion'], resolucion=newfile)
                        informehomologacion.save(request)
                    log(u'Adiciono archivo de informe de práctica profesionales: %s [%s]' % (
                        informehomologacion, informehomologacion.id), request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'registrarhoras':
            try:
                data['practicainscripcion'] = practicainscripcion = PracticasPreprofesionalesInscripcion.objects.get(
                    pk=int(encrypt(request.POST['id'])))
                practicainscripcion.horahomologacion = int(request.POST['horas'])
                practicainscripcion.estadosolicitud = 2
                practicainscripcion.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass

        elif action == 'addasignacionempresa':
            try:
                form = AsignacionEmpresaPracticaForm(request.POST)
                if form.is_valid():
                    asignacionempresa = AsignacionEmpresaPractica(
                        nombre=form.cleaned_data['nombre'],
                        canton=form.cleaned_data['canton']
                    )
                    asignacionempresa.save(request)
                    log(u'Adiciono asignacion empresa: %s [%s]' % (asignacionempresa, asignacionempresa.id), request,
                        "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editasignacionempresa':
            try:
                form = AsignacionEmpresaPracticaForm(request.POST)
                if form.is_valid():
                    asignacionempresa = AsignacionEmpresaPractica.objects.get(pk=int(encrypt(request.POST['id'])))
                    asignacionempresa.nombre = form.cleaned_data['nombre']
                    asignacionempresa.canton_id = request.POST['canton']
                    asignacionempresa.save(request)
                    log(u'Modificó asignación empresa: %s [%s]' % (asignacionempresa, asignacionempresa.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delasignacionempresa':
            try:
                asignacionempresa = AsignacionEmpresaPractica.objects.get(pk=int(encrypt(request.POST['id'])))
                asignacionempresa.status = False
                asignacionempresa.save(request)
                log(u'Cambió estado [status=False] de asignación de empresa: %s' % asignacionempresa, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'culminartutoria':
            try:
                practica = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.POST['id']))
                if practica.culminatutoria:
                    practica.culminatutoria = False
                else:
                    practica.culminatutoria = True
                if 'observacion' in request.POST:
                    practica.obsculminatutoria = request.POST['observacion']
                practica.fechaculminacion = datetime.now()
                practica.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        elif action == 'culminarpractica':
            try:
                practica = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.POST['id']))
                if practica.culminada:
                    practica.culminada = False
                else:
                    practica.culminada = True
                practica.fechaculminacionpracticas = datetime.now()
                practica.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        elif action == 'notidirector':
            try:
                soli = SolicitudHomologacionPracticas.objects.get(pk=request.POST['id'])
                soli.fecha_notificacion_director = datetime.now()
                soli.save(request)
                subject = 'DIRECTOR(A) SOLICITUD DE HOMOLOGACIÓN PENDIENTE DE REVISIÓN {}'.format(
                    soli.inscripcion.persona.__str__())
                template = 'emails/homologacion_director.html'
                datos_email = {'sistema': 'SGA UNEMI', 'filtro': soli}
                dir_carrera = CoordinadorCarrera.objects.filter(carrera=soli.inscripcion.carrera, periodo=periodo,
                                                                tipo=3).first()
                email_director = dir_carrera.persona.emailinst if dir_carrera else ''
                lista_email = [email_director, ]
                # lista_email = ['hllerenaa@unemi.edu.ec',]
                send_html_mail(subject, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[4][1])
                response = JsonResponse({'resp': True})
            except Exception as ex:
                response = JsonResponse({'resp': False, 'mensaje': ex})
            return HttpResponse(response.content)

        elif action == 'notidecano':
            try:
                soli = SolicitudHomologacionPracticas.objects.get(pk=request.POST['id'])
                soli.fecha_notificacion_decano = datetime.now()
                soli.save(request)
                subject = 'DECANO(A) SOLICITUD DE HOMOLOGACIÓN PENDIENTE DE REVISIÓN {}'.format(
                    soli.inscripcion.persona.__str__())
                template = 'emails/homologacion_decano.html'
                datos_email = {'sistema': 'SGA UNEMI', 'filtro': soli}
                decano = ResponsableCoordinacion.objects.filter(
                    coordinacion=soli.inscripcion.carrera.coordinacion_carrera(), periodo=periodo, tipo=1).first()
                email_decano = decano.persona.emailinst if decano else ''
                lista_email = [email_decano, ]
                # lista_email = ['hllerenaa@unemi.edu.ec',]
                send_html_mail(subject, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[4][1])
                response = JsonResponse({'resp': True})
            except Exception as ex:
                response = JsonResponse({'resp': False, 'mensaje': ex})
            return HttpResponse(response.content)

        elif action == 'notiempresa':
            try:
                data['filtro'] = filtro = DatosEmpresaPreInscripcionPracticasPP.objects.get(pk=request.POST['id'])
                filtro.fecha_notificacion = datetime.now()
                filtro.persona_notificacion = persona
                filtro.empresa_notificado = True
                filtro.save(request)
                subject = 'SOLICITUD DE PRÁCTICAS O PASANTÍAS'
                template = 'emails/vinculacion_empresa.html'
                datos_email = {'sistema': 'SGA UNEMI', 'filtro': filtro}
                lista_email = [filtro.correo]
                documentolista = [filtro.archivodescargar] if filtro.archivodescargar else ''
                send_html_mail(subject, template, datos_email, lista_email, [], documentolista, cuenta=CUENTAS_CORREOS[4][1])
                response = JsonResponse({'resp': True})
            except Exception as ex:
                response = JsonResponse({'resp': False, 'mensaje': ex})
            return HttpResponse(response.content)

        elif action == 'notiempresacartavinculacion':
            try:
                cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.get(pk=request.POST['id'])
                cartavinculacion.fecha_notificacion = datetime.now()
                cartavinculacion.persona_notificacion = persona
                cartavinculacion.empresa_notificado = True
                cartavinculacion.save(request)
                datos_email = {'sistema': 'SGA UNEMI', 'filtro': cartavinculacion}

                lista_email = []
                if cartavinculacion.email: lista_email.append(cartavinculacion.email)
                if cartavinculacion.email1: lista_email.append(cartavinculacion.email1)
                if cartavinculacion.email2: lista_email.append(cartavinculacion.email2)
                if cartavinculacion.email3: lista_email.append(cartavinculacion.email3)

                data['carta'] = cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.get(pk=request.POST['id'])
                carreras = DetalleCartaInscripcion.objects.filter(status=True, carta=cartavinculacion).values_list(
                    'inscripcion__inscripcion__carrera', flat=True).distinct()
                data['carreras'] = Carrera.objects.filter(id__in=carreras).order_by('nombre')
                template_pdf = 'alu_practicaspreprofesionalesinscripcion/informe_carta_vinculacion.html'
                nombredocumento = 'CARTA_DE_VINCULACION_{}_{}'.format(cartavinculacion.memo, random.randint(1, 100000).__str__())

                directory = os.path.join(SITE_STORAGE, 'media', 'qrcode')
                os.makedirs(directory, exist_ok=True)

                directory = os.path.join(directory, 'solicitudempresascarta')
                os.makedirs(directory, exist_ok=True)

                conviert_html_to_pdf_name_savecartavinc(template_pdf, {'pagesize': 'A4', 'data': data}, nombredocumento)
                cartavinculacion.archivo = 'qrcode/solicitudempresascarta/' + nombredocumento + '.pdf'
                cartavinculacion.save(request)

                emails = list(cartavinculacion.inscripciones().values_list('inscripcion__inscripcion__persona__emailinst', 'inscripcion__tutorunemi__persona__emailinst', 'inscripcion__supervisor__persona__emailinst'))
                newList = []
                for x in emails:
                    for y in x:
                        newList.append(y)
                lista_email += newList
                documentolista = [cartavinculacion.archivo]
                asunto = u"NOTIFICACIÓN"
                send_html_mail(asunto, 'emails/vinculacion_carta_empresa.html',datos_email, lista_email, [], adjuntos=documentolista, cuenta=CUENTAS_CORREOS[1][1])

                return JsonResponse({'result':True})
            except Exception as ex:
                return JsonResponse({'result':False, 'mensaje': f'Error de conexión. {ex.__str__()}'})


        elif action == 'addobservacion':
            try:
                with transaction.atomic():
                    filtro = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                    form = SeguimientoPreProfesionalInscripcionForm(request.POST)
                    if form.is_valid():
                        filtro.accion = form.cleaned_data['accion']
                        filtro.save()
                        soli = SeguimientoPreProfesionalesInscripcion(cab=filtro,
                                                                      detalle=form.cleaned_data['detalle'].upper(),
                                                                      accion=form.cleaned_data['accion'],
                                                                      fecha_llamada=form.cleaned_data['fecha_llamada'],
                                                                      hora_llamada=form.cleaned_data['hora_llamada']
                                                                      )
                        soli.save(request)
                        log(u'Adiciono Observación en Seguimiento a Prácticas Pre-Profesionales: %s' % soli, request,
                            "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'addanilladoobservacion':
            try:
                with transaction.atomic():
                    filtro = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.POST['id']))
                    form = AnilladoPreProfesionalInscripcionForm(request.POST)
                    if form.is_valid():
                        filtro.accion_anillado = form.cleaned_data['accion']
                        filtro.save()
                        soli = AnilladoPracticasPreprofesionalesInscripcion(cab=filtro,
                                                                            detalle=form.cleaned_data[
                                                                                'detalle'].upper(),
                                                                            accion=form.cleaned_data['accion'],
                                                                            fecha=form.cleaned_data['fecha'],
                                                                            hora=form.cleaned_data['hora']
                                                                            )
                        soli.save(request)
                        log(u'Adiciono Observación en Seguimiento Anillados de Practicas Pre-Profesionales: %s' % soli,
                            request,
                            "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)


        elif action == 'additinerariodocente':
            try:
                postar = ActividadDetalleDistributivoCarrera.objects.get(id=int(request.POST['id']))
                form = ItinerarioMallaDocenteDistributivoForm(request.POST)
                if form.is_valid():
                    listaExcluidos = ItinerariosActividadDetalleDistributivoCarrera.objects.filter(actividad=postar, status=True).exclude(itinerario__in=form.cleaned_data['itinerario'].values_list('pk', flat=True))
                    for itix in listaExcluidos:
                        itix.status = False
                        itix.save(request)
                    for iti in form.cleaned_data['itinerario']:
                        if not ItinerariosActividadDetalleDistributivoCarrera.objects.filter(actividad=postar, itinerario=iti, status=True).exists():
                            itinerario = ItinerariosActividadDetalleDistributivoCarrera(actividad=postar, itinerario=iti)
                            itinerario.save(request)
                            log(u'Adiciono Itinerario a Distributivo Docente : %s' % (itinerario), request, "add")
                    return JsonResponse({"result": False, }, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})


        if action == 'revertiraprobaciondirector':
            try:
                f = ObservacionDecanoForm(request.POST)
                if f.is_valid():
                    solicitud = SolicitudHomologacionPracticas.objects.get(pk=int(request.POST['id']))
                    solicitud.revision_director = 0
                    solicitud.estados = 3
                    historial = HistoricoRevisionesSolicitudHomologacionPracticas(solicitud=solicitud,
                                                                                  ejecutado_por=persona,
                                                                                  accion=3,
                                                                                  paso=3,
                                                                                  observacion=f.cleaned_data['observacion'])
                    historial.save(request)
                    solicitud.save(request)
                    log(u'Cerro la materia: %s' % solicitud, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        if action == 'revertiraprobacionvinculacion':
            try:
                f = ObservacionDirectorForm(request.POST)
                if f.is_valid():
                    solicitud = SolicitudHomologacionPracticas.objects.get(pk=int(request.POST['id']))
                    solicitud.revision_vinculacion = 0
                    solicitud.estados = 0
                    historial = HistoricoRevisionesSolicitudHomologacionPracticas(solicitud=solicitud,
                                                                                  ejecutado_por=persona,
                                                                                  accion=3,
                                                                                  paso=2,
                                                                                  observacion=f.cleaned_data['observacion'])
                    historial.save(request)
                    solicitud.save(request)
                    log(u'Cerro la materia: %s' % solicitud, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        if action == 'cambiaritinerario':
            try:
                if not request.POST['itinerario']:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Seleccione un Itineraario"})
                actividad = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.POST['id'])))
                actividad.itinerariomalla_id=int(request.POST['itinerario'])
                actividad.save(request)
                log('Se modifica el itinerario de Actividad Extracurricular %s' % actividad, request, 'cambiaritinerario')
                return JsonResponse({"result": False})
            except Exception as ex:
                sg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % sg})

        elif action == 'actaaceptacion_excel':
            try:
                idcar,idest,docu,seacrh = request.POST.get('carrera',''),request.POST.get('estados',''),request.POST.get('docu',''),request.POST.get('search','')
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar el reporte"})
                pre = PreInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
                preinscripciones = pre.detallepreinscripcionpracticaspp_set.filter(status=True,archivo__isnull=False).order_by(
                    'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                    'inscripcion__persona__nombres')
                if 'estados' in request.POST:
                    idest = int(request.POST['estados'])
                    if idest > 0 and idest < 7:
                        preinscripciones = preinscripciones.filter(estado=idest)
                    if idest == 7:
                        lista_solicitantes = DatosEmpresaPreInscripcionPracticasPP.objects.filter(status=True, preinscripcion__in=preinscripciones.values_list('pk', flat=True))
                        preinscripciones = pre.filter(
                            pk__in=lista_solicitantes.values_list('preinscripcion__pk', flat=True))
                    if idest == 8:
                        lista_solicitantes = SolicitudVinculacionPreInscripcionPracticasPP.objects.filter(status=True, preinscripcion__in=preinscripciones.values_list('pk', flat=True))
                        preinscripciones = preinscripciones.filter(pk__in=lista_solicitantes.values_list('preinscripcion__pk', flat=True))
                if 'idfac' in request.POST:
                    idfac = int(request.POST['idfac'])
                    if idfac > 0:
                        preinscripciones = preinscripciones.filter(inscripcion__coordinacion__id=idfac)
                if 'carrera' in request.POST:
                    idcar = int(request.POST['carrera'])
                    if idcar > 0:
                        preinscripciones = preinscripciones.filter(inscripcion__carrera__id=idcar)
                if 'docu' in request.POST:
                    data['docu'] = docu = request.POST['docu']
                    if docu == '1':
                        preinscripciones = preinscripciones.exclude(archivo='')
                    elif docu == '2':
                        preinscripciones = preinscripciones.filter(archivo='')
                if 'search' in request.POST:
                    search = request.POST['search']
                    s = search.split(" ")
                    if len(s) == 1:
                        preinscripciones = preinscripciones.filter(
                            Q(inscripcion__persona__nombres__icontains=search) | Q(
                                inscripcion__persona__apellido1__icontains=search) | Q(
                                inscripcion__persona__cedula__icontains=search) | Q(
                                inscripcion__persona__apellido2__icontains=search))
                    elif len(s) == 2:
                        preinscripciones = preinscripciones.filter(
                            (Q(inscripcion__persona__nombres__icontains=s[0]) & Q(
                                inscripcion__persona__nombres__icontains=s[1])) |
                            (Q(inscripcion__persona__apellido1__icontains=s[0]) & Q(
                                inscripcion__persona__apellido2__icontains=s[1]))
                        )
                __author__ = 'Unemi'
                style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                  num_format_str='#,##0.00')
                style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                title = easyxf(
                    'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                style1 = easyxf(num_format_str='D-MMM-YY')
                date_format = xlwt.XFStyle()
                date_format.num_format_str = 'yyyy/mm/dd'
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('practicas')
                ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=Listas_PreInscritos_Actas' + random.randint(1,
                                                                                                              10000).__str__() + '.xls'
                columnas = [
                    (u"MALLA", 10000),
                    (u"FACULTAD", 10000),
                    (u"CARRERA", 10000),
                    (u"NIVEL", 3000),
                    (u"JORNADA", 5000),
                    (u"PARALELO", 5000),
                    (u"CÉDULA", 3000),
                    (u"ESTUDIANTE", 10000),
                    (u"CELULAR", 5000),
                    (u"CONVENCIONAL", 3000),
                    (u"ITINERARIO", 10000),
                    (u"DOCENTE", 10000),
                    (u"EMPRESA", 10000),
                    (u"EMAIL EMPRESA", 10000),
                    (u"TELEFONO EMPRESA", 10000),
                    (u"TIPO INSTITUCION", 10000),
                    (u"PAIS", 10000),
                    (u"PROVINCIA", 10000),
                    (u"CANTON", 10000),
                    (u"DIRECCION", 10000),
                    (u"FECHA", 10000),
                    (u"ESTADO", 10000),
                ]
                row_num = 1
                for col_num in range(len(columnas)):
                    ws.write(row_num, col_num, columnas[col_num][0], font_style)
                    ws.col(col_num).width = columnas[col_num][1]
                col_num = len(columnas)
                row_num = 3
                for pi in preinscripciones.exclude(archivo='',archivo__isnull=False).distinct():
                    ws.write(row_num, 0, '%s' % pi.inscripcion.mi_malla() if pi.inscripcion.mi_malla() else '', font_style2)
                    ws.write(row_num, 1, '%s' % pi.inscripcion.mi_coordinacion().nombre if pi.inscripcion.mi_coordinacion() else '', font_style2)
                    ws.write(row_num, 2, '%s' % pi.inscripcion.carrera.nombre if pi.inscripcion.carrera else '', font_style2)
                    ws.write(row_num, 3, '%s' % pi.inscripcion.mi_nivel() if pi.inscripcion.mi_nivel() else '', font_style2)
                    ws.write(row_num, 4, '%s' % pi.inscripcion.nivelperiodo(periodo).nivel.sesion.nombre if pi.inscripcion.nivelperiodo(periodo) else '', font_style2)
                    if pi.inscripcion.matricula_periodo(periodo):
                        ws.write(row_num, 5, '%s' % pi.inscripcion.matricula_periodo(
                            periodo).paralelo.nombre if pi.inscripcion.matricula_periodo(periodo).paralelo else '',
                                 font_style2)
                    else:
                        ws.write(row_num, 5, '%s' % '', font_style2)
                    ws.write(row_num, 6, '%s' % pi.inscripcion.persona.cedula if pi.inscripcion.persona.cedula else '', font_style2)
                    ws.write(row_num, 7, '%s' % pi.inscripcion.persona.nombre_completo_inverso() if pi.inscripcion.persona else '', font_style2)
                    ws.write(row_num, 8, '%s' % pi.inscripcion.persona.telefono if pi.inscripcion.persona.telefono else '', font_style2)
                    ws.write(row_num, 9, '%s' % pi.inscripcion.persona.telefono_conv if pi.inscripcion.persona.telefono_conv else '', font_style2)
                    ws.write(row_num, 10, '%s' % pi.itinerariomalla.nombre if pi.itinerariomalla else "",font_style2)
                    ws.write(row_num, 11,'%s' % docentes_practicas_estudiantes(pi.inscripcion, pi.preinscripcion.periodo.id,pi.itinerariomalla) if docentes_practicas_estudiantes(pi.inscripcion, pi.preinscripcion.periodo.id, pi.itinerariomalla) else "", font_style2)
                    ws.write(row_num,12,'%s' % pi.convenioempresa if pi.convenioempresa else pi.otraempresaempleadora,font_style2)
                    ws.write(row_num,13,'%s' % pi.email if pi.email else "",font_style2)
                    ws.write(row_num,14,'%s' % pi.telefonoempresa if pi.telefonoempresa else "",font_style2)
                    ws.write(row_num,15,'%s' % pi.tipoinstitucion if pi.tipoinstitucion else "",font_style2)
                    ws.write(row_num,16,'%s' % pi.pais if pi.pais else "",font_style2)
                    ws.write(row_num,17,'%s' % pi.provincia if pi.provincia else "",font_style2)
                    ws.write(row_num,18,'%s' % pi.canton if pi.canton else "",font_style2)
                    ws.write(row_num,19,'%s' % pi.direccion if pi.direccion else "",font_style2)
                    ws.write(row_num,20,'%s' % pi.fecha_modificacion,font_style2)
                    ws.write(row_num,21,'%s' % pi.get_estado_display(),font_style2)
                    row_num += 1
                wb.save(response)
                return response
            except Exception as ex:
                pass

        elif action == 'importapreinscrito':
                try:
                    f = ImportarPreinscritoPPForm(request.POST, request.FILES)
                    archivo_ = request.FILES['archivo']
                    periodoppp = f.data['periodop']
                    periodoevidencia = f.data['periodoevidencia']
                    nombres_hojas = pd.ExcelFile(archivo_).sheet_names
                    cabecera = ['cedula', 'carrera',
                                'asignatura', 'nivel_asignatura',
                                'itinerario', 'nivel_actual','documento_profesor',
                                'tutoracadémico','fechainicio','fechafin','horasprácticas']
                    total_registros=0
                    total_sistema=0
                    for name in nombres_hojas:
                        df = pd.read_excel(archivo_, sheet_name=name)
                        df.columns = formatear_cabecera_pd(df)
                        cont=0
                        contn=0
                        for c in cabecera:
                            if not c in df.columns:
                                raise NameError(f'Formato de archivo erróneo: La columna {c} no se encuentra en el documento.')

                        for index, row in df.iterrows():
                                total_registros+=1
                                cedula = str(row['cedula']).strip().split('.')[0]
                                carrera = str(row['carrera']).strip()
                                asignatura = str(row['asignatura']).strip()
                                nivel_asignatura = str(row['nivel_asignatura']).strip()
                                itinerario = str(row['itinerario']).strip()
                                nivel_actual = str(row['nivel_actual']).strip()
                                documento_profesor = str(row['documento_profesor']).strip()
                                profesor_supervisor = Profesor.objects.filter(persona__cedula__icontains=documento_profesor,status=True,activo=True)
                                tutor_academico = str(row['tutoracadémico']).strip().split()
                                profesor_tutor= Profesor.objects.filter(persona__apellido1=tutor_academico[0],
                                                                        persona__apellido2=tutor_academico[1],
                                                                        persona__nombres=join(tutor_academico[2:]),status=True)
                                nivel_actual = str(row['nivel_actual']).strip()
                                fecha_inicio = row['fechainicio']
                                fecha_fin = row['fechafin']
                                horas_practicas = int(row['horasprácticas'])
                                nivelmalla_=NivelMalla.objects.filter(nombre=nivel_asignatura,status=True)
                                nivelmalla_=nivelmalla_[0] if nivelmalla_ else None
                                inscripcion = Inscripcion.objects.filter(status=True,persona__cedula__icontains=cedula,carrera__nombre=carrera)

                                if inscripcion:
                                    total_sistema += 1
                                    inscripcion=inscripcion[0]
                                    itinerario_ = ItinerariosMalla.objects.filter(status=True, nombre=itinerario,nivel=nivelmalla_, malla=inscripcion.mi_malla())
                                    itinerario_ = itinerario_[0] if itinerario_ else None

                                    preinscripcion = DetallePreInscripcionPracticasPP.objects.filter(status=True,inscripcion=inscripcion,
                                                                                                     nivelmalla__nombre=nivelmalla_,
                                                                                                     itinerariomalla=itinerario_,
                                                                                                     preinscripcion_id=periodoppp)
                                    if not preinscripcion:
                                        preinscripcion = DetallePreInscripcionPracticasPP(inscripcion=inscripcion,
                                                                                                     nivelmalla=nivelmalla_,
                                                                                                     itinerariomalla=itinerario_,
                                                                                                     preinscripcion_id=periodoppp)
                                        preinscripcion.save()
                                        cont+=1
                                        print(cont,'nueva')

                                    else:
                                        preinscripcion=preinscripcion[0]
                                        contn += 1
                                        print(contn, 'renovacion')
                                    preinscripcion.fecha=datetime.now().date()
                                    preinscripcion.fechadesde=fecha_inicio
                                    preinscripcion.fechahasta=fecha_fin
                                    if profesor_tutor:
                                        preinscripcion.tutorunemi=profesor_tutor[0]
                                    preinscripcion.supervisor=profesor_supervisor[0] if profesor_supervisor else None
                                    preinscripcion.numerohora=horas_practicas
                                    preinscripcion.estado=2
                                    preinscripcion.empresaempleadora_id=3
                                    preinscripcion.pais_id=1
                                    preinscripcion.provincia_id=10
                                    preinscripcion.canton_id=2
                                    preinscripcion.sectoreconomico=6
                                    preinscripcion.tipoinstitucion=1
                                    preinscripcion.save()

                                    insppp = PracticasPreprofesionalesInscripcion.objects.filter(status=True,preinscripcion=preinscripcion)
                                    if not insppp:
                                        insppp = PracticasPreprofesionalesInscripcion(preinscripcion=preinscripcion,
                                                                             inscripcion=inscripcion,
                                                                             nivelmalla=preinscripcion.nivelmalla,
                                                                             tutorunemi=preinscripcion.tutorunemi,
                                                                             fechadesde=preinscripcion.fechadesde,
                                                                             itinerariomalla=preinscripcion.itinerariomalla,
                                                                             vigente=True,
                                                                             fechahasta=preinscripcion.fechahasta,
                                                                             numerohora=preinscripcion.numerohora,
                                                                             tipoinstitucion=preinscripcion.tipoinstitucion,
                                                                             empresaempleadora=preinscripcion.empresaempleadora,
                                                                             tiposolicitud=1,
                                                                             estadosolicitud=2,
                                                                             sectoreconomico=6,
                                                                             supervisor=preinscripcion.supervisor,
                                                                             fechaasigtutor=datetime.now().date(),
                                                                             fechaasigsupervisor=datetime.now().date(),
                                                                             periodoevidencia_id=periodoevidencia,
                                                                             tipo=1
                                                                             )
                                        insppp.save()
                                    else:
                                        insppp=insppp[0]
                                        insppp.inscripcion = preinscripcion.inscripcion
                                        insppp.nivelmalla = preinscripcion.nivelmalla
                                        insppp.tutorunemi = preinscripcion.tutorunemi
                                        insppp.fechadesde = preinscripcion.fechadesde
                                        insppp.itinerariomalla = preinscripcion.itinerariomalla
                                        insppp.vigente = True
                                        insppp.fechahasta = preinscripcion.fechahasta
                                        insppp.numerohora = preinscripcion.numerohora
                                        insppp.tipoinstitucion = preinscripcion.tipoinstitucion
                                        insppp.empresaempleadora = preinscripcion.empresaempleadora
                                        insppp.tiposolicitud = 1
                                        insppp.estadosolicitud = 2
                                        insppp.sectoreconomico = 6
                                        insppp.supervisor = preinscripcion.supervisor
                                        insppp.fechaasigtutor = datetime.now().date()
                                        insppp.fechaasigsupervisor = datetime.now().date()
                                        insppp.periodoevidencia_id = periodoevidencia
                                        insppp.save()

                            # return JsonResponse({"result": True, 'data': template.render(data)})
                    messages.success(request, f'Se migraron {total_sistema} de {total_registros}')
                    return JsonResponse({"result": False, 'mensaje': 'Importado correctamente'})
                except Exception as ex:
                    transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Error: {ex}"})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        # fin get
        adduserdata(request, data)
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'consultaeliminar':
                try:
                    with transaction.atomic():
                        id = int(request.GET['id'])
                        carrera_id = int(request.GET['carrera'])
                        estado = int(request.GET['estado'])
                        preinscripcion = PreInscripcionPracticasPP.objects.get(status=True, pk=id)
                        preinscripciones = preinscripcion.detallepreinscripcionpracticaspp_set.filter(status=True,
                                                                                                      estado=estado,
                                                                                                      inscripcion__carrera__id=carrera_id)
                        res_json = {"error": False, 'qscount': preinscripciones.count()}
                except Exception as ex:
                    res_json = {'error': True, "message": str(ex)}
                return JsonResponse(res_json, safe=False)

            elif action == 'importapreinscrito':
                try:
                    data['title'] = u'Importar preinscritos'
                    form = ImportarPreinscritoPPForm()
                    data['form'] = form
                    template = get_template("ajaxformmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    data['title'] = u'Nuevo Prácticas Preprofesionales'
                    data['coordinacion'] = coordinacion
                    form = PracticasPreprofesionalesInscripcionForm(initial={'fechadesde': datetime.now().date(),
                                                                             'fechahasta': datetime.now().date()})
                    form.fields['periodoevidencia'].queryset = CabPeriodoEvidenciaPPP.objects.filter(status=True)
                    # form.tiposolicitudcho()
                    form.cargartipopractica()
                    form.cargaritinerario()

                    # form.eliminarempresaempleadora()

                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/add.html", data)
                except Exception as ex:
                    pass

            if action == 'deletepracticas':
                try:
                    practicas = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                    practicas.delete()
                    log(u'Elimino practica preprofesionales inscripcion: %s' % practicas, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

            if action == 'excelpracticas':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('practicas')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Listas_Practicas' + random.randint(1,
                                                                                                          10000).__str__() + '.xls'
                    columns = [
                        (u"MALLA", 10000),
                        (u"FACULTAD", 10000),
                        (u"CARRERA", 10000),
                        (u"NIVEL", 3000),
                        (u"PERIODO ACADEMICO", 4500),
                        (u"CEDULA", 3000),
                        (u"ESTUDIANTE", 10000),
                        (u"SEXO", 3000),
                        (u"CELULAR", 3000),
                        (u"CONVENCIONAL", 3000),
                        (u"EMAIL", 10000),
                        (u"EMAIL INSTITUCIONAL", 10000),
                        (u"DIRECCION DOMICILIARIA", 10000),
                        (u"CANTON", 10000),
                        (u"EGRESADO", 2000),
                        (u"TIPO PRACTICAS", 3000),
                        (u"TUTOR ACADÉMICO", 3000),
                        (u"CORREO DEL TUTOR", 10000),
                        (u"TUTOR PROFESIONAL", 3000),
                        (u"SUPERVISOR", 3000),
                        (u"FECHA DESDE", 3000),
                        (u"FECHA HASTA", 3000),
                        (u"HORAS PRACTICAS", 2000),
                        (u"HORAS HOMOLOGACIÓN", 2000),
                        (u"INSTITUCION", 13000),
                        (u"OTRA EMPRESA", 13000),
                        (u"TIPO INSTITUCION", 3000),
                        (u"DEPARTAMENTO", 3000),
                        (u"SECTOR ECONOMICO", 6500),
                        (u"USUARIO", 4000),
                        (u"FECHA REGISTRO", 4000),
                        (u"INSCRIPCION", 4000),
                        (u"TIPO SOLICITUD", 4000),
                        (u"ARCHIVO DE SOLICITUD", 4000),
                        (u"ESTADO SOLICITUD", 4000),
                        (u"PRACTICAS CULMINADAS", 2000),
                        (u"EVIDENCIAS APROBADAS / TOTAL ", 2000),
                        (u"EVIDENCIAS RECHAZADAS", 2000),
                        (u"EVIDENCIAS SOLICITADAS", 2000),
                        (u"EVIDENCIAS COMPLETAS", 2000),
                        (u"FECHA EVIDENCIA", 3000),
                        (u"FECHA ACTUALIZACION EVIDENCIA", 3000),
                        (u"APROBACIÓN SOLICITUD", 3000),
                        (u"OBSERVACIÓN", 6000),
                        (u"VALIDACIÓN", 6000),
                        (u"FECHA VALIDACIÓN", 6000),
                        (u"ROTACION", 6000),
                        (u"SESION", 6000),
                        (u"EVALUA PROMEDIO PRÁCTICA", 6000),
                        (u"PROMEDIO PRÁCTICA", 6000),
                        (u"CONVENIO/ACUERDO", 6000),
                        (u"EMPRESA CONVENIO/ACUERDO", 10000),
                        (u"ASIGNACIÓN EMPRESA", 10000),
                        (u"LUGAR", 10000),
                        (u"ITINERARIO", 10000),
                        (u"NIVEL PRÁCTICA", 10000),
                        (u"PERIODO DE EVIDENCIA", 20000),
                        (u"TOTAL TUTORIAS", 10000),
                        (u"ESTADO", 10000),
                        (u"FECHA CULMINACIÓN TUTORIA", 10000),
                    ]

                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    # totalevidencias = EvidenciaPracticasProfesionales.objects.filter(status=True).count()
                    if persona.es_profesor():
                        if persona.id in [17579, 818, 5194, 23532, 169, 12130, 16630, 1652, 21604, 30751, 30802, 27946,
                                          16781]:
                            listapracticas = PracticasPreprofesionalesInscripcion.objects.filter(culminada=False,
                                                                                                 status=True).order_by(
                                '-fecha_creacion')
                        else:
                            listapracticas = PracticasPreprofesionalesInscripcion.objects.filter(
                                inscripcion__carrera__coordinacion=coordinacion, status=True).order_by(
                                'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                                'inscripcion__persona__nombres')
                    else:
                        opc = int(request.GET['opc'])
                        if opc == 0:
                            listapracticas = PracticasPreprofesionalesInscripcion.objects.select_related().filter(
                                status=True).order_by(
                                'inscripcion__persona__apellido1')
                            if 'fecinicio' in request.GET and 'fecfin' in request.GET:
                                fecinicio = (request.GET['fecinicio'])
                                fecfin = (request.GET['fecfin'])
                                listapracticas = listapracticas.filter(fecha_creacion__gte=fecinicio,
                                                                       fecha_creacion__lte=fecfin)

                        else:
                            if opc == 10:
                                listapracticas = PracticasPreprofesionalesInscripcion.objects.filter(culminada=True,
                                                                                                     status=True).order_by(
                                    'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                                    'inscripcion__persona__nombres')
                            else:
                                if opc == 11:
                                    llenardocentes = []
                                    cursor = connection.cursor()
                                    sql = "select id , numevid from (select ins.id,count(evid.id) as numevid from sga_practicaspreprofesionalesinscripcion ins,sga_detalleevidenciaspracticaspro evid where ins.id=evid.inscripcionpracticas_id and ins.status=true and evid.status=True and ins.culminada=False and evid.estadorevision=2 group by ins.id) as d where numevid>6"
                                    cursor.execute(sql)
                                    results = cursor.fetchall()
                                    for r in results:
                                        llenardocentes.append(r[0])
                                        listapracticas = PracticasPreprofesionalesInscripcion.objects.filter(
                                            pk__in=llenardocentes, status=True).order_by(
                                            'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                                            'inscripcion__persona__nombres')
                                else:
                                    if opc == 12:
                                        listapracticas = PracticasPreprofesionalesInscripcion.objects.filter(
                                            estadosolicitud=4, culminada=False, status=True).order_by(
                                            'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                                            'inscripcion__persona__nombres')
                                    else:
                                        if opc == 13:
                                            llenardocentes = []
                                            cursor = connection.cursor()
                                            sql = "select id , numevid from (select ins.id,count(evid.id) as numevid from sga_practicaspreprofesionalesinscripcion ins,sga_detalleevidenciaspracticaspro evid where ins.id=evid.inscripcionpracticas_id and ins.status=true and evid.status=True and ins.culminada=False and evid.estadorevision=1 group by ins.id) as d where numevid>6"
                                            cursor.execute(sql)
                                            results = cursor.fetchall()
                                            for r in results:
                                                llenardocentes.append(r[0])
                                                listapracticas = PracticasPreprofesionalesInscripcion.objects.filter(
                                                    pk__in=llenardocentes, status=True).order_by(
                                                    'inscripcion__persona__apellido1',
                                                    'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                                        elif opc == 14:
                                            listapracticas = PracticasPreprofesionalesInscripcion.objects.filter(
                                                estadosolicitud=1, culminada=False, status=True).order_by(
                                                'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                                                'inscripcion__persona__nombres')
                                        elif opc == 15:
                                            listapracticas = PracticasPreprofesionalesInscripcion.objects.filter(
                                                estadosolicitud=2, culminada=False, status=True).order_by(
                                                'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                                                'inscripcion__persona__nombres')
                                        elif opc == 16:
                                            listapracticas = PracticasPreprofesionalesInscripcion.objects.filter(
                                                estadosolicitud=3, culminada=False, status=True).order_by(
                                                'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                                                'inscripcion__persona__nombres')
                                        else:
                                            listapracticas = PracticasPreprofesionalesInscripcion.objects.filter(
                                                tiposolicitud=opc, culminada=False, status=True).order_by(
                                                'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                                                'inscripcion__persona__nombres')

                    row_num = 4
                    i = 0
                    for practicas in listapracticas:
                        # i = i+1
                        # if i == 247:
                        #     o = 0
                        campo52 = ''
                        campo3 = ''
                        campo4 = ''
                        campo47 = ''
                        campo56 = ''
                        if practicas.inscripcion.nivelperiodo(periodo):
                            matriculado = practicas.inscripcion.nivelperiodo(periodo)
                            campo3 = matriculado.nivelmalla.nombre
                            campo4 = matriculado.nivel.periodo.nombre
                            campo47 = matriculado.nivel.sesion.nombre.__str__()
                        campo1 = practicas.inscripcion.coordinacion.nombre
                        campo2 = practicas.inscripcion.carrera.nombre_completo()
                        campo5 = practicas.inscripcion.persona.cedula
                        campo6 = practicas.inscripcion.persona.telefono
                        campo7 = practicas.inscripcion.persona.telefono_conv
                        campo8 = practicas.inscripcion.persona.email
                        campo35 = practicas.inscripcion.persona.emailinst
                        campo36 = ''
                        if practicas.rotacionmalla:
                            campo36 = practicas.rotacionmalla.nombre
                        if practicas.inscripcion.egresado():
                            campo9 = 'SI'
                        else:
                            campo9 = 'NO'
                        campo10 = practicas.get_tipo_display()
                        campo15 = practicas.tutorunemi.persona.nombre_completo_inverso() if practicas.tutorunemi else ""
                        campo37 = practicas.tutorempresa if practicas.tutorempresa else ""
                        campo41 = practicas.supervisor.persona.nombre_completo_inverso() if practicas.supervisor else ""
                        campo11 = practicas.fechadesde if practicas.fechadesde else ""
                        campo12 = practicas.fechahasta if practicas.fechahasta else ""
                        campo13 = practicas.numerohora
                        campo14 = practicas.empresaempleadora.nombre if practicas.empresaempleadora else ""
                        campo16 = practicas.get_tipoinstitucion_display()
                        campo17 = practicas.get_sectoreconomico_display()
                        if practicas.usuario_creacion:
                            campo18 = practicas.usuario_creacion.username
                        else:
                            campo18 = ''
                        campo19 = practicas.fecha_creacion
                        campo20 = practicas.inscripcion.id
                        campo21 = practicas.get_tiposolicitud_display()
                        campo22 = practicas.get_estadosolicitud_display()
                        campo23 = ''
                        if InscripcionMalla.objects.filter(inscripcion=practicas.inscripcion, status=True).exists():
                            insmalla = \
                                InscripcionMalla.objects.select_related().filter(inscripcion=practicas.inscripcion, status=True)[0]
                            nommalla = 'HISTORICA'
                            mallamodalidad = ''
                            if insmalla.malla.vigente:
                                nommalla = 'VIGENTE'
                            if insmalla.malla.modalidad:
                                mallamodalidad = insmalla.malla.modalidad.nombre
                            campo23 = insmalla.malla.carrera.nombre + ' ' + MONTH_NAMES[
                                insmalla.malla.inicio.month - 1] + ' ' + str(
                                insmalla.malla.inicio.year) + ' ' + nommalla + ' ' + mallamodalidad
                        if practicas.culminada:
                            campo24 = 'SI'
                        else:
                            campo24 = 'NO'
                        ultimafechaevidencia = DetalleEvidenciasPracticasPro.objects.select_related().filter(
                            inscripcionpracticas=practicas, status=True).order_by('-id')
                        ultimafechaevidenciaact = DetalleEvidenciasPracticasPro.objects.select_related().filter(
                            inscripcionpracticas=practicas, status=True).order_by('-fecha_modificacion')
                        if practicas.fechadesde:
                            campo25 = str(practicas.evidenciasaprobadas()) + ' / ' + str(practicas.totalevidencias())
                            if str(practicas.evidenciasaprobadas()) == str(practicas.totalevidencias()):
                                campo26 = 'SI'
                            else:
                                campo26 = 'NO'
                        else:
                            campo25 = "0/0"
                            campo26 = ""
                        campo27 = ''
                        campo33 = ''
                        if ultimafechaevidencia:
                            campo27 = ultimafechaevidencia[0].fecha_creacion if ultimafechaevidencia[
                                0].fecha_creacion else ''
                            campo33 = ultimafechaevidenciaact[0].fecha_modificacion if ultimafechaevidenciaact[
                                0].fecha_modificacion else ''
                        campo28 = practicas.evidenciasreprobadas()
                        campo29 = practicas.evidenciassolicitadas()
                        campo30 = practicas.fechaaprueba if practicas.fechaaprueba else ""
                        campo31 = practicas.horahomologacion if practicas.horahomologacion else ""
                        campo32 = practicas.otraempresaempleadora if practicas.otraempresaempleadora else ""
                        campo34 = practicas.observacion if practicas.observacion else ""
                        campo38 = practicas.inscripcion.persona.sexo.nombre if practicas.inscripcion.persona.sexo else ""
                        campo39 = practicas.validacion if practicas.validacion else " - "
                        campo40 = practicas.fechavalidacion if practicas.fechavalidacion else "-"
                        campo42 = practicas.inscripcion.persona.direccion_corta()
                        campo43 = u'%s' % practicas.inscripcion.persona.canton.nombre if practicas.inscripcion.persona.canton else ''
                        campo44 = ""
                        if practicas.tutorunemi:
                            if practicas.tutorunemi.persona.emailinst:
                                campo44 = u'%s' % practicas.tutorunemi.persona.emailinst
                        campo45 = ""
                        if practicas.departamento:
                            campo45 = u'%s' % practicas.departamento
                        if practicas.archivo:
                            campo46 = "SI"
                        else:
                            campo46 = "NO"
                        campo48 = ""
                        if practicas.periodoppp:
                            if practicas.periodoppp.evaluarpromedio:
                                campo48 = u'%s' % practicas.total_promedio_nota_evidencia()
                        campo49 = ""
                        if practicas.periodoppp:
                            campo49 = "SI" if practicas.periodoppp.evaluarpromedio else "NO"
                        if practicas.convenio:
                            campo50 = "CONVENIO"
                            campo52 = practicas.convenio.empresaempleadora.nombre
                        elif practicas.acuerdo:
                            campo50 = "ACUERDO"
                            campo52 = practicas.acuerdo.empresa.nombre
                        else:
                            campo50 = "NINGUNO"
                            campo52 = "NINGUNO"
                        if practicas.asignacionempresapractica:
                            campo51 = practicas.asignacionempresapractica.nombre
                        else:
                            campo51 = "SIN ASIGNAR"

                        lugarpractica = ""
                        if practicas.lugarpractica:
                            lugarpractica = practicas.lugarpractica.nombre

                        campo53 = ''
                        if practicas.itinerariomalla:
                            campo53 = str(practicas.itinerariomalla.nombreitinerario())

                        campo56 = ''
                        periodoevidencia = ''
                        if practicas.itinerariomalla:
                            periodoevidencia = str(practicas.periodoppp)
                        if practicas.periodoppp:
                            periodoevidencia = str(practicas.periodoppp)

                        ws.write(row_num, 0, campo23, font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, campo3, font_style2)
                        ws.write(row_num, 4, campo4, font_style2)
                        ws.write(row_num, 5, campo5, font_style2)
                        ws.write(row_num, 6,
                                 practicas.inscripcion.persona.apellido1 + ' ' + practicas.inscripcion.persona.apellido2 + ' ' + practicas.inscripcion.persona.nombres,
                                 font_style2)
                        ws.write(row_num, 7, campo38, font_style2)
                        ws.write(row_num, 8, campo6, font_style2)
                        ws.write(row_num, 9, campo7, font_style2)
                        ws.write(row_num, 10, campo8, font_style2)
                        ws.write(row_num, 11, campo35, font_style2)
                        ws.write(row_num, 12, campo42, font_style2)
                        ws.write(row_num, 13, campo43, font_style2)
                        ws.write(row_num, 14, campo9, font_style2)
                        ws.write(row_num, 15, campo10, font_style2)
                        ws.write(row_num, 16, campo15, font_style2)
                        ws.write(row_num, 17, campo44, font_style2)
                        ws.write(row_num, 18, campo37, font_style2)
                        ws.write(row_num, 19, campo41, font_style2)
                        ws.write(row_num, 20, campo11, date_format)
                        ws.write(row_num, 21, campo12, date_format)
                        ws.write(row_num, 22, campo13, font_style2)
                        ws.write(row_num, 23, campo31, font_style2)
                        ws.write(row_num, 24, campo14, font_style2)
                        ws.write(row_num, 25, campo32, font_style2)
                        ws.write(row_num, 26, campo16, font_style2)
                        ws.write(row_num, 27, campo45, font_style2)
                        ws.write(row_num, 28, campo17, font_style2)
                        ws.write(row_num, 29, campo18, font_style2)
                        ws.write(row_num, 30, campo19, date_format)
                        ws.write(row_num, 31, campo20, font_style2)
                        ws.write(row_num, 32, campo21, font_style2)
                        ws.write(row_num, 33, campo46, font_style2)
                        ws.write(row_num, 34, campo22, font_style2)
                        ws.write(row_num, 35, campo24, font_style2)
                        ws.write(row_num, 36, campo25, font_style2)
                        ws.write(row_num, 37, campo28, font_style2)
                        ws.write(row_num, 38, campo29, font_style2)
                        ws.write(row_num, 39, campo26, font_style2)
                        ws.write(row_num, 40, campo27, date_format)
                        ws.write(row_num, 41, campo33, date_format)
                        ws.write(row_num, 42, campo30, date_format)
                        ws.write(row_num, 43, campo34, font_style2)
                        ws.write(row_num, 44, campo39, font_style2)
                        ws.write(row_num, 45, campo40, date_format)
                        ws.write(row_num, 46, campo36, font_style2)
                        ws.write(row_num, 47, campo47, font_style2)
                        ws.write(row_num, 48, campo49, font_style2)
                        ws.write(row_num, 49, campo48, font_style2)
                        ws.write(row_num, 50, campo50, font_style2)
                        ws.write(row_num, 51, campo52, font_style2)
                        ws.write(row_num, 52, campo51, font_style2)
                        ws.write(row_num, 53, lugarpractica, font_style2)
                        ws.write(row_num, 54, campo53, font_style2)
                        ws.write(row_num, 55, practicas.nivelmalla.nombre if practicas.nivelmalla else '', font_style2)
                        ws.write(row_num, 56, periodoevidencia, font_style2)
                        ws.write(row_num, 57, practicas.cuenta_tutorias(), font_style2)
                        estadopractica = 'NO OBLIGATORIAS'
                        if practicas.tipo == 1 or practicas.tipo == 2:
                            if practicas.aplicatutoria:
                                if practicas.culminatutoria:
                                    estadopractica = 'CULMINADA'
                                else:
                                    estadopractica = 'PENDIENTE'
                        ws.write(row_num, 58, estadopractica, font_style2)
                        if practicas.fechaculminacion:
                            ws.write(row_num, 59, str(practicas.fechaculminacion), font_style2)
                        print(row_num - 3)

                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    print(ex)

            elif action == 'excelgestioncartas':
                try:
                    inicio = request.GET['fecinicio']
                    fin = request.GET['fecfin']
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Reporte de vinculaciones' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"NUM", 2000),
                        (u"FECHA", 10000),
                        (u"USUARIO", 10000),
                        (u"EMPRESA", 10000),
                        (u"CANT ESTUDIANTES", 10000),

                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listacartas = CartaVinculacionPracticasPreprofesionales.objects.filter(status=True, fecha_creacion__gte = inicio, fecha_creacion__lte=fin)
                    row_num = 4
                    i = 0
                    for carta in listacartas:


                        if carta.convenio:
                            empresa = carta.convenio.empresaempleadora.nombre
                        elif carta.acuerdo:
                            empresa = carta.acuerdo.empresa.nombre
                        else:
                            empresa = carta.empresa.nombre

                        ws.write(row_num, 0, i, font_style2)
                        ws.write(row_num, 1, carta.fecha_creacion, date_format)
                        ws.write(row_num, 2, str(carta.usuario_creacion), font_style2)
                        ws.write(row_num, 3, empresa, font_style2)
                        ws.write(row_num, 4, carta.cantVinculados(), font_style2)
                        
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'exceltotoriaspracticasdocentes':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('practicas')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Listas_Practicas' + random.randint(1,
                                                                                                          10000).__str__() + '.xls'
                    columns = [
                        (u"CEDULA", 4000),
                        (u"DOCENTE", 12000),
                        (u"CARRERA", 15000),
                        (u"HORA", 2000),
                        (u"FECHA", 3000),
                        (u"PERIODO ACADEMICO", 16000),
                        (u"ACTIVIDAD", 16000),
                        (u"CORREO", 6000),
                        (u"TELEFONO", 6000),
                    ]

                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listatutorias = ActividadDetalleDistributivoCarrera.objects.filter(
                        actividaddetalle__criterio__criteriodocenciaperiodo__criterio__id__in=[6, 154],
                        actividaddetalle__criterio__distributivo__periodo=periodo,
                        actividaddetalle__criterio__distributivo__status=True, status=True).order_by(
                        'actividaddetalle__criterio__distributivo__profesor__persona__apellido1')
                    row_num = 4
                    i = 0
                    for lista in listatutorias:
                        campo1 = lista.actividaddetalle.criterio.distributivo.profesor.persona.cedula
                        campo2 = lista.actividaddetalle.criterio.distributivo.profesor.persona.nombre_completo().__str__()
                        campo3 = lista.carrera.__str__()
                        campo4 = lista.horas
                        campo5 = lista.fecha_creacion
                        correo_ins = lista.actividaddetalle.criterio.distributivo.profesor.persona.emailinst if lista.actividaddetalle.criterio.distributivo.profesor.persona.emailinst else ''
                        telefono = lista.actividaddetalle.criterio.distributivo.profesor.persona.telefono if lista.actividaddetalle.criterio.distributivo.profesor.persona.telefono else ''
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, date_format)
                        ws.write(row_num, 5, periodo.__str__(), font_style2)
                        ws.write(row_num, 6,
                                 lista.actividaddetalle.criterio.criteriodocenciaperiodo.criterio.nombre.__str__(),
                                 font_style2)
                        ws.write(row_num, 7, correo_ins, date_format)
                        ws.write(row_num, 8, telefono, date_format)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'excelcartasvinculacion':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('practicas')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Lista_CartasVinculacion' + random.randint(1,
                                                                                                                 10000).__str__() + '.xls'
                    columns = [
                        (u"N°", 2000),
                        (u"EMPRESA/INSTITUCION", 16000),
                        (u"FECHA", 6000),
                        (u"CARRERA", 16000)
                    ]

                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listacartas = CartaVinculacionPracticasPreprofesionales.objects.filter(status=True).order_by(
                        'carrera__nombre')
                    row_num = 4
                    i = 0
                    for index, carta in enumerate(listacartas):
                        if carta.convenio:
                            campo1 = carta.convenio.empresaempleadora.nombre
                        else:
                            campo1 = carta.acuerdo.empresa.nombre
                        campo2 = carta.fecha
                        campo3 = carta.carrera.__str__()
                        ws.write(row_num, 0, (index + 1), font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, date_format)
                        ws.write(row_num, 3, campo3, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar Prácticas Preprofesionales'
                    data['practicaspreprofesionalesinscripcion'] = practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.get(pk=request.GET['id'])
                    form = PracticasPreprofesionalesInscripcionForm(initial={'inscripcion': practicaspreprofesionalesinscripcion.inscripcion.id,
                                                                             'nivelmalla': practicaspreprofesionalesinscripcion.nivelmalla,
                                                                             'tipo': practicaspreprofesionalesinscripcion.tipo,
                                                                             'fechadesde': practicaspreprofesionalesinscripcion.fechadesde,
                                                                             'culminada': practicaspreprofesionalesinscripcion.culminada,
                                                                             'fechahasta': practicaspreprofesionalesinscripcion.fechahasta,
                                                                             'tiposolicitud': practicaspreprofesionalesinscripcion.tiposolicitud,
                                                                             'empresaempleadora': practicaspreprofesionalesinscripcion.empresaempleadora.id if practicaspreprofesionalesinscripcion.empresaempleadora else "",
                                                                             'tutorempresa': practicaspreprofesionalesinscripcion.tutorempresa,
                                                                             'tutorunemi': practicaspreprofesionalesinscripcion.tutorunemi.id if practicaspreprofesionalesinscripcion.tutorunemi else "",
                                                                             'supervisor': practicaspreprofesionalesinscripcion.supervisor.id if practicaspreprofesionalesinscripcion.supervisor else "",
                                                                             'numerohora': practicaspreprofesionalesinscripcion.numerohora,
                                                                             'horahomologacion': practicaspreprofesionalesinscripcion.horahomologacion,
                                                                             # 'rotacion': practicaspreprofesionalesinscripcion.rotacion,
                                                                             'departamento': practicaspreprofesionalesinscripcion.departamento,
                                                                             'direccionempresa': practicaspreprofesionalesinscripcion.convenio.empresaempleadora.direccion if practicaspreprofesionalesinscripcion.convenio else practicaspreprofesionalesinscripcion.acuerdo.empresa.direccion if practicaspreprofesionalesinscripcion.acuerdo else "",
                                                                             'rotacion': practicaspreprofesionalesinscripcion.rotacionmalla,
                                                                             'paispractica': practicaspreprofesionalesinscripcion.lugarpractica.provincia.pais if practicaspreprofesionalesinscripcion.lugarpractica else "",
                                                                             'provinciapractica': practicaspreprofesionalesinscripcion.lugarpractica.provincia if practicaspreprofesionalesinscripcion.lugarpractica else "",
                                                                             'lugarpractica': practicaspreprofesionalesinscripcion.lugarpractica if practicaspreprofesionalesinscripcion.lugarpractica else "",
                                                                             # 'asignacionempresapractica': practicaspreprofesionalesinscripcion.asignacionempresapractica.nombre if practicaspreprofesionalesinscripcion.asignacionempresapractica else "",
                                                                             # 'institucion': practicaspreprofesionalesinscripcion.institucion,
                                                                             'tipoinstitucion': practicaspreprofesionalesinscripcion.tipoinstitucion,
                                                                             'sectoreconomico': practicaspreprofesionalesinscripcion.sectoreconomico,
                                                                             'otraempresaempleadora': practicaspreprofesionalesinscripcion.otraempresaempleadora,
                                                                             # 'observacion': practicaspreprofesionalesinscripcion.observacion,
                                                                             'periodoevidencia': practicaspreprofesionalesinscripcion.periodoppp,
                                                                             'acuerdo': practicaspreprofesionalesinscripcion.acuerdo,
                                                                             'convenio': practicaspreprofesionalesinscripcion.convenio,
                                                                             'asignacionempresapractica': practicaspreprofesionalesinscripcion.asignacionempresapractica,
                                                                             'observacion': practicaspreprofesionalesinscripcion.observacion,
                                                                             'itinerario': practicaspreprofesionalesinscripcion.itinerariomalla,
                                                                             'campo_especifico': practicaspreprofesionalesinscripcion.inscripcion.malla_inscripcion().malla.campo_especifico if practicaspreprofesionalesinscripcion.inscripcion.malla_inscripcion() else None})
                    form.fields['periodoevidencia'].queryset = CabPeriodoEvidenciaPPP.objects.filter(status=True)
                    # form.fields['itinerario'].queryset = ItinerariosMalla.objects.filter(status=True, malla__carrera=practicaspreprofesionalesinscripcion.preinscripcion.inscripcion.carrera).order_by('pk')
                    form.editar(practicaspreprofesionalesinscripcion)
                    malla = practicaspreprofesionalesinscripcion.inscripcion.mi_malla()
                    nivel = practicaspreprofesionalesinscripcion.inscripcion.mi_nivel().nivel
                    form.cargaritinerario(malla, nivel)
                    form.vaciartutorunemi()
                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/edit.html", data)
                except Exception as ex:
                    print(ex)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            if action == 'cambiacarrerapractica':
                try:
                    data['title'] = u'Cambiar Carrera de la Práctica'
                    data['practica'] = practica = PracticasPreprofesionalesInscripcion.objects.get(pk=request.GET['id'])

                    if practica.tipo == 7:
                        empresa = practica.actividad.titulo
                    else:
                        if practica.institucion:
                            empresa = practica.institucion
                        else:
                            if not practica.convenio and not practica.acuerdo:
                                if not practica.empresaempleadora:
                                    empresa = practica.otraempresaempleadora if practica.otraempresaempleadora else ''
                                else:
                                    empresa = practica.empresaempleadora.nombre
                            else:
                                if practica.convenio:
                                    empresa = practica.convenio.empresaempleadora if practica.convenio.empresaempleadora else ''
                                elif practica.acuerdo.empresa:
                                    empresa = practica.acuerdo.empresa.nombre if practica.acuerdo.empresa else ''
                                else:
                                    empresa = ''

                    form = CambioCarreraPracticaForm(initial={
                        'alumno': practica.inscripcion.persona.nombre_completo_inverso(),
                        'empresa': empresa,
                        'fechainicio': practica.fechadesde,
                        'fechahasta': practica.fechahasta,
                        'horas': practica.numerohora,
                        'carreraactual': practica.inscripcion.carrera.nombre,
                        'itinerarioactual': practica.itinerariomalla
                    })

                    form.cargar_otra_carrera(practica)

                    data['validaitinerario'] = 'S' if practica.itinerariomalla else 'N'

                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editcarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiacarrerapractica_actividad':
                try:
                    data['title'] = u'Cambiar Carrera de la Práctica y la Actividad'
                    data['practica'] = practica = PracticasPreprofesionalesInscripcion.objects.get(pk=request.GET['id'])

                    if practica.tipo == 7:
                        empresa = practica.actividad.titulo
                    else:
                        if practica.institucion:
                            empresa = practica.institucion
                        else:
                            if not practica.convenio and not practica.acuerdo:
                                if not practica.empresaempleadora:
                                    empresa = practica.otraempresaempleadora if practica.otraempresaempleadora else ''
                                else:
                                    empresa = practica.empresaempleadora.nombre
                            else:
                                if practica.convenio:
                                    empresa = practica.convenio.empresaempleadora if practica.convenio.empresaempleadora else ''
                                elif practica.acuerdo.empresa:
                                    empresa = practica.acuerdo.empresa.nombre if practica.acuerdo.empresa else ''
                                else:
                                    empresa = ''

                    form = CambioCarreraPracticaConActividadForm(initial={
                        'alumno': practica.inscripcion.persona.nombre_completo_inverso(),
                        'empresa': empresa,
                        'fechainicio': practica.fechadesde,
                        'fechahasta': practica.fechahasta,
                        'horas': practica.numerohora,
                        'carreraactual': practica.inscripcion.carrera.nombre,
                        'itinerarioactual': practica.itinerariomalla,
                        'activiades_cargadas': practica.actividad

                    })

                    form.cargar_otra_carrera(practica)
                    # form.cargar_actividades(practica)

                    data['validaitinerario'] = 'S' if practica.itinerariomalla else 'N'

                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editcarrera_actividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirarchivos':
                try:
                    data['title'] = u'Carga de evidencias de Prácticas Preprofesionales'
                    data['practicas'] = practicas = PracticasPreprofesionalesInscripcion.objects.filter(
                        pk=request.GET['id'])[0]

                    data[
                        'evidencias'] = practicas.periodoppp.evidencias_practica() if practicas.tipo != 7 else practicas.detalleevidenciaspracticaspro_set.filter(
                        status=True)

                    data['periodopractica'] = practicas.periodoppp
                    data['formevidencias'] = EvidenciaPracticasForm()
                    data['nevidencias'] = practicas.formatoevidenciaalumno()
                    return render(request, "alu_practicaspreprofesionalesinscripcion/evidenciaspracticas.html", data)
                except Exception as ex:
                    pass

            elif action == 'addevidenciaspracticasnormal':
                try:
                    data['title'] = u'Evidencia Practicas'
                    data['form'] = EvidenciaPracticasNormalForm
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    template = get_template(
                        "alu_practicaspreprofesionalesinscripcion/add_evidenciaspracticasnormal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'addevidenciaspracticas':
                try:
                    data['title'] = u'Subir Evidencia'
                    data['form'] = EvidenciaPracticasForm
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    template = get_template("alu_practicaspreprofesionalesinscripcion/add_evidenciaspracticas.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'ponerfechalimite':
                try:
                    data['title'] = u'Asignar fechas para subir evidencia'
                    data['form'] = PonerFechaLimiteEvidenciaForm()
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    template = get_template("alu_practicaspreprofesionalesinscripcion/ponerfechalimite.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'addapruebaevidencias':
                try:
                    data['title'] = u'Aprobar o rechazar'
                    data['form'] = ArpobarEvidenciaPracticasForm
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    data['idpracins'] = request.GET['idpracins']
                    template = get_template(
                        "alu_practicaspreprofesionalesinscripcion/add_aprobarevidenciaspracticas.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    data['title'] = u'Eliminar Practicas PreProfesionales'
                    data['campo'] = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/delete.html", data)
                except:
                    pass

            elif action == 'deletetutoracademico':
                try:
                    data['title'] = u'Eliminar Tutor Académico de Practicas PreProfesionales'
                    data['campo'] = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/deletetutor.html", data)
                except:
                    pass

            elif action == 'eliminasupervisor':
                try:
                    data['title'] = u'Eliminar Supervisor Académico de Practicas PreProfesionales'
                    data['campo'] = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/deletesupervisor.html", data)
                except:
                    pass

            elif action == 'listadepartamentos':
                try:
                    data['title'] = u'Listado de Departamentos'
                    search = None
                    ids = None
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        departamentos = PracticasDepartamento.objects.select_related().filter(pk=ids,
                                                                                              status=True).order_by(
                            'nombre')
                    elif 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            departamentos = PracticasDepartamento.objects.select_related().filter(pk=search,
                                                                                                  status=True)
                        else:
                            departamentos = PracticasDepartamento.objects.select_related().filter(
                                Q(nombre__icontains=search), status=True)
                    else:
                        departamentos = PracticasDepartamento.objects.select_related().filter(status=True).order_by(
                            'nombre')
                    paging = MiPaginador(departamentos, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listadepartamentos'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewdepartamentos.html", data)
                except Exception as ex:
                    pass

            elif action == 'adddepartamento':
                try:
                    data['title'] = u'Adicionar Departamento Empresa'
                    form = PracticasDepartamentoForm()
                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/adddepartamento.html", data)
                except Exception as ex:
                    pass

            elif action == 'editdepartamento':
                try:
                    data['title'] = u'Editar Departamento'
                    data['departamento'] = departamento = PracticasDepartamento.objects.get(pk=request.GET['id'])
                    form = PracticasDepartamentoForm(initial={'nombre': departamento.nombre})
                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editardepartamento.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletedepartamento':
                try:
                    data['title'] = u'Eliminar Departamento'
                    data['departamento'] = PracticasDepartamento.objects.get(pk=request.GET['iddepartamento'])
                    return render(request, "alu_practicaspreprofesionalesinscripcion/deletedepartamento.html", data)
                except Exception as ex:
                    pass

            elif action == 'ver_observacion':
                try:
                    solicitud = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['idsolicitud']))
                    return JsonResponse({"result": "ok", 'data': solicitud.obseaprueba})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'aprobarrechazarsolicitud':
                try:
                    data['title'] = u'Aprobar o Rechazar Solicitud'
                    praprofesionales = PracticasPreprofesionalesInscripcion.objects.get(
                        pk=request.GET['idencuestapreguntas'])
                    form = AprobarRechazarSolicitudPracticaForm(initial={
                        'estadosolicitud': praprofesionales.estadosolicitud if praprofesionales.estadosolicitud else 0,
                        'observacion': praprofesionales.obseaprueba,
                        'validacion': praprofesionales.validacion,
                        'fechavalidacion': praprofesionales.fechavalidacion if praprofesionales.fechavalidacion else datetime.now(),
                        'retirado': praprofesionales.retirado,
                        'fechahastapenalizacionretiro': praprofesionales.fechahastapenalizacionretiro if praprofesionales.fechahastapenalizacionretiro else None
                    })
                    data['form'] = form
                    data['idpracticas'] = praprofesionales.id
                    template = get_template("alu_practicaspreprofesionalesinscripcion/aprobarrechazarsolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'verdetalles':
                try:
                    data['form'] = PonerFechaLimiteEvidenciaForm
                    data['id'] = id = int(request.GET['id'])
                    data['iddetalle'] = iddetalle = int(request.GET['iddetalle'])
                    data['detalles'] = detalle = DetalleEvidenciasPracticasPro.objects.get(pk=iddetalle)
                    template = get_template("alu_practicaspreprofesionalesinscripcion/detalles.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'notificarcompletoevidencias':
                try:
                    asunto = u"NOTIFICACION DE ENTREGA DE DOCUMENTOS"
                    id = int(request.GET['id'])
                    solicitud = PracticasPreprofesionalesInscripcion.objects.get(pk=id)
                    send_html_mail(asunto, "emails/notificacompletoevidencia.html",
                                   {'sistema': request.session['nombresistema'],
                                    'coordinacion': solicitud.inscripcion.coordinacion.id,
                                    'alumno': solicitud.inscripcion.persona.nombre_completo_inverso()},
                                   solicitud.inscripcion.persona.lista_emails_envio(), [],
                                   cuenta=CUENTAS_CORREOS[0][1])
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    pass

            elif action == 'ofertaspracticas':
                try:
                    data['title'] = u'Listado de ofertas Prácticas Pre Profesional'
                    search = None
                    ids = None
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        ofertas = OfertasPracticas.objects.filter(pk=ids, status=True).order_by('-fecha_creacion')
                    elif 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if search.isdigit():
                            ofertas = OfertasPracticas.objects.filter(cupos=search, status=True).order_by(
                                '-fecha_creacion')
                        elif len(ss) > 2:
                            ofertas = OfertasPracticas.objects.filter(
                                (Q(empresa__nombre__icontains=ss[0]) & Q(empresa__nombre__icontains=ss[1])) |
                                (Q(departamento__nombre__icontains=ss[0]) & Q(departamento__nombre__icontains=ss[1])) |
                                (Q(otraempresaempleadora__icontains=ss[0]) & Q(
                                    otraempresaempleadora__icontains=ss[1])) & Q(status=True)).order_by(
                                '-fecha_creacion')
                        else:
                            ofertas = OfertasPracticas.objects.filter(
                                Q(empresa__nombre__icontains=search) | Q(departamento__nombre__icontains=search) | Q(
                                    otraempresaempleadora__icontains=search), status=True).order_by('-fecha_creacion')
                    else:
                        ofertas = OfertasPracticas.objects.filter(status=True).order_by('-fecha_creacion')
                    paging = MiPaginador(ofertas, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['ofertas'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "alu_practicaspreprofesionalesinscripcion/ofertaspracticas.html", data)
                except Exception as ex:
                    pass

            elif action == 'addoferta':
                try:
                    data['title'] = u'Agregar Oferta'
                    form = OfertasPracticasForm()
                    form.cargar_itinerario()
                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/addoferta.html", data)
                except Exception as ex:
                    pass

            elif action == 'editoferta':
                try:
                    data['title'] = u'Editar Oferta'
                    data['oferta'] = oferta = OfertasPracticas.objects.get(pk=int(request.GET['id']), status=True)
                    form = OfertasPracticasForm(initial={'empresa': oferta.empresa,
                                                         'departamento': oferta.departamento if oferta.departamento else "",
                                                         'horario': oferta.horario,
                                                         'carrera': oferta.carrera.all(),
                                                         'requisito': oferta.requisito,
                                                         'habilidad': oferta.habilidad if oferta.habilidad else "",
                                                         'cupos': oferta.cupos,
                                                         'inicio': oferta.inicio,
                                                         'fin': oferta.fin,
                                                         'iniciopractica': oferta.iniciopractica,
                                                         'finpractica': oferta.finpractica,
                                                         'otraempresa': oferta.otraempresa,
                                                         'otraempresaempleadora': oferta.otraempresaempleadora,
                                                         'tipo': oferta.tipo,
                                                         'numerohora': oferta.numerohora,
                                                         'tipoinstitucion': oferta.tipoinstitucion,
                                                         'sectoreconomico': oferta.sectoreconomico,
                                                         'itinerarios': oferta.itinerariosmalla.all(),
                                                         })
                    form.cargar_itinerario(oferta.carrera.all())
                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editoferta.html", data)
                except Exception as ex:
                    pass

            elif action == 'deloferta':
                try:
                    data['title'] = u'Eliminar Oferta'
                    data['oferta'] = OfertasPracticas.objects.get(pk=int(request.GET['id']), status=True)
                    return render(request, "alu_practicaspreprofesionalesinscripcion/deleoferta.html", data)
                except Exception as ex:
                    pass

            elif action == 'alumalla':
                try:
                    data['title'] = u'MALLA DEL ALUMNO'
                    listas_asignaturasmallas = []
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['inscripcion_malla'] = inscripcionmalla = inscripcion.malla_inscripcion()
                    data['malla'] = malla = inscripcionmalla.malla
                    data['nivelesdemallas'] = NivelMalla.objects.all().order_by('id')
                    data['ejesformativos'] = EjeFormativo.objects.all().order_by('nombre')
                    # data['asignaturasmallas'] = [(x, inscripcion.aprobadaasignatura(x)) for x in
                    #                              AsignaturaMalla.objects.filter(malla=malla)]

                    listadoasignaturamalla = AsignaturaMalla.objects.filter(malla=malla, status=True).exclude(tipomateria_id=3)
                    xyz = [1, 2, 3]
                    if inscripcion.itinerario and inscripcion.itinerario > 0:
                        xyz.remove(inscripcion.itinerario)
                        listadoasignaturamalla = listadoasignaturamalla.exclude(itinerario__in=xyz)
                    for x in listadoasignaturamalla.exclude(ejeformativo_id=4):
                        listas_asignaturasmallas.append([x, inscripcion.aprobadaasignatura(x)])

                    data['asignaturasmallas'] = listas_asignaturasmallas

                    resumenniveles = [{'id': x.id, 'horas': x.total_horas(malla), 'creditos': x.total_creditos(malla)}
                                      for x in NivelMalla.objects.all().order_by('id')]
                    data['resumenes'] = resumenniveles
                    template = get_template("alu_practicaspreprofesionalesinscripcion/alumalla.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'listaprofesordistributivo':
                try:
                    # listaidcriterio = [6, 23, 31]
                    listaidcriterio, listaprofesor, practicasprofesionales, inscripcion, iditinerario, id = [6, 154, 144], [], None, None, request.GET.get('iditinerario', ''), request.GET.get('id', '')
                    fechadesde = convertir_fecha(request.GET['fd'])
                    fechahasta = convertir_fecha(request.GET['fh'])
                    if id:
                        # EDITAR PRACTICA PREPROFESIONALES
                        practicasprofesionales = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                        carrera = practicasprofesionales.inscripcion.carrera
                        carrera_id = carrera.id
                        #preinscripcionid = practicasprofesionales.preinscripcion.id
                        # preinsc = practicasprofesionales.preinscripcion
                    else:
                        # ADICIONAR PRACTICA PREPROFESIONALES
                        inscripcion = Inscripcion.objects.get(pk=int(request.GET['idi']))
                        carrera = inscripcion.carrera
                        carrera_id = carrera.id   #request.GET['carrera']
                        #preinscripcionid = request.GET['preinscripcion']
                        # preinsc = DetallePreInscripcionPracticasPP.objects.get(pk=preinscripcionid)
                    periodo = request.session['periodo']
                    profesoresdistributivo = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo).distinct()
                    if inscripcion:
                        if not inscripcion.carrera.modalidad == 3:
                            profesoresdistributivo = profesoresdistributivo.filter(detalledistributivo__criteriodocenciaperiodo__criterio__id__in=listaidcriterio,
                                                                                    detalledistributivo__actividaddetalledistributivo__actividaddetalledistributivocarrera__carrera=carrera).distinct()
                    else:
                        if not practicasprofesionales.inscripcion.carrera.modalidad == 3:
                            profesoresdistributivo = profesoresdistributivo.filter(detalledistributivo__criteriodocenciaperiodo__criterio__id__in=listaidcriterio, detalledistributivo__actividaddetalledistributivo__actividaddetalledistributivocarrera__carrera=carrera).distinct()
                    if profesoresdistributivo and iditinerario:
                        profesoresdistributivo = profesoresdistributivo.filter(detalledistributivo__actividaddetalledistributivo__actividaddetalledistributivocarrera__itinerariosactividaddetalledistributivocarrera__itinerario_id=iditinerario)
                    #llenar lista de profesores
                    listaprofesor = [[x.profesor_id, f"{x.profesor.persona.cedula} - {x.profesor.persona.nombre_completo_inverso()} ({x.periodo.nombre}) - hor.({x.horas_docencia_segun_criterio_carrera(listaidcriterio, carrera_id)}) - asig.({x.profesor.contar_practicaspreprofesionales_asignadas_carrera(periodo, carrera_id)})"] for x in profesoresdistributivo]
                    periodoevidencia = CabPeriodoEvidenciaPPP.objects.filter((Q(fechainicio__lte=fechadesde) & Q(fechafin__gte=fechadesde)) | (Q(fechafin__lte=fechahasta) & Q(fechafin__gte=fechahasta))).distinct().first()
                    listape = list(CabPeriodoEvidenciaPPP.objects.filter(status=True).order_by('-fechainicio').values_list('id', 'nombre'))
                    # Acuerdo Compromiso
                    listaacuerdo = list(AcuerdoCompromiso.objects.filter(status=True, fechafinalizacion__gte=fechadesde).order_by('-fechaelaboracion').values_list('id', 'empresa__nombre', 'carrera__nombre', 'fechaelaboracion'))
                    listaacuerdo = [[a[0], f"{a[1]} - {a[2]} - {a[3]}"] for a in listaacuerdo]
                    # Convenio Empresa
                    listaconvenio = [[c.id, f"{c}"] for c in ConvenioEmpresa.objects.filter(fechafinalizacion__gte=fechadesde, status=True).order_by('fechafinalizacion')]

                    # MUESTRA EL MENSAJE DEL PERIODO
                    data = {"result": "ok", "results": listaprofesor, "mensaje": u'%s %s' % (
                        "Según las fechas de la Práctica Preprofesionales está en el periodo", periodo),
                            'periodoevidencias': listape, 'listaacuerdo': listaacuerdo, 'listaconvenio': listaconvenio,
                            'perevid': periodoevidencia.id if periodoevidencia else 0}

                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

            elif action == 'listaprofesordistributivomasivo':
                try:
                    # listaidcriterio = [6, 23, 31]
                    listaidcriterio, listaprofesor, practicasprofesionales, inscripcion, iditinerario, id = [6, 154, 144], [], None, None, request.GET.get('iditinerario', ''), request.GET.get('id', '')

                    # ADICIONAR PRACTICA PREPROFESIONALES
                    carrera = Carrera.objects.get(pk=int(request.GET['idcarr']))
                    # fechadesde = convertir_fecha(request.GET['fd'])
                    # fechahasta = convertir_fecha(request.GET['fh'])
                    fechadesde = request.GET['fd']
                    fechahasta = request.GET['fh']
                    carrera_id = request.GET['idcarr']
                    periodo = request.session['periodo']
                    if carrera.modalidad == 3:
                        profesoresdistributivo = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo).distinct()
                    else:
                        profesoresdistributivo = ProfesorDistributivoHoras.objects.filter(detalledistributivo__criteriodocenciaperiodo__criterio__id__in=listaidcriterio,
                                                                                          detalledistributivo__actividaddetalledistributivo__actividaddetalledistributivocarrera__carrera=carrera, status=True, periodo=periodo).distinct()

                    if profesoresdistributivo and iditinerario:
                        profesoresdistributivo = profesoresdistributivo.filter(detalledistributivo__actividaddetalledistributivo__actividaddetalledistributivocarrera__itinerariosactividaddetalledistributivocarrera__itinerario_id=iditinerario)
                    for x in profesoresdistributivo:
                        listaprofesor.append([u'%s' % x.profesor.id, u'%s - (%s) - hor.(%s)' % (
                            x.profesor.persona.nombre_completo_inverso(), x.periodo.nombre,
                            x.horas_docencia_segun_criterio_carrera(listaidcriterio, carrera_id))])

                    periodoevidencia = CabPeriodoEvidenciaPPP.objects.filter(
                        (Q(fechainicio__lte=fechadesde) & Q(fechafin__gte=fechadesde)) | (
                                Q(fechafin__lte=fechahasta) & Q(fechafin__gte=fechahasta))).distinct()
                    listape = []
                    for p in CabPeriodoEvidenciaPPP.objects.filter(status=True).order_by('-fechainicio'):
                        listape.append([p.id, p.nombre])

                    # Acuerdo Compromiso
                    listaacuerdo = []
                    # , carrera=carrera
                    for a in AcuerdoCompromiso.objects.filter(status=True).order_by('-fechaelaboracion'):
                        # acuerdo1 = a.empresa.nombre +" - "+ a.carrera.nombre +" - "+ str(a.fechaelaboracion)
                        acuerdo1 = str(a)
                        listaacuerdo.append([a.id, acuerdo1])

                    # Convenio Empresa
                    listaconvenio = []
                    for c in ConvenioEmpresa.objects.filter(fechafinalizacion__gte=fechadesde, status=True).order_by('fechafinalizacion'):
                        # for c in ConvenioEmpresa.objects.filter(fechainicio__gte=fechadesde, fechainicio__lte=fechahasta ,status=True).order_by('-fechainicio'):
                        # for c in ConvenioEmpresa.objects.filter(fechafinalizacion__lte=fechadesde,status=True).order_by('-fechainicio'):
                        # convenio1 = c.objetivo + " - " + c.empresaempleadora.nombre +" - "+ str(c.fechainicio) +" - "+ str(c.fechafinalizacion)
                        convenio1 = "{}".format(str(c))
                        listaconvenio.append([c.id, convenio1])

                    # MUESTRA EL MENSAJE DEL PERIODO
                    data = {"result": "ok", "results": listaprofesor, "mensaje": u'%s %s' % (
                        "Según las fechas de la Práctica Preprofesionales está en el periodo", periodo),
                            'periodoevidencias': listape, 'listaacuerdo': listaacuerdo, 'listaconvenio': listaconvenio,
                            'perevid': periodoevidencia[0].id if periodoevidencia else 0}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

            elif action == 'listadirectorescarrera':
                try:
                    listaidcriterio = [6, 23, 31, 154]
                    listaprofesor = []
                    practicasprofesionales = None
                    if 'id' in request.GET:
                        # EDITAR PRACTICA PREPROFESIONALES
                        practicasprofesionales = PracticasPreprofesionalesInscripcion.objects.get(
                            pk=int(request.GET['id']))
                        carrera = practicasprofesionales.inscripcion.carrera
                    else:
                        # ADICIONAR PRACTICA PREPROFESIONALES
                        inscripcion = Inscripcion.objects.get(pk=int(request.GET['idi']))
                        carrera = inscripcion.carrera
                    coordinadorcarrera = CoordinadorCarrera.objects.filter(carrera=carrera, periodo=periodo)
                    if practicasprofesionales:
                        if practicasprofesionales.tutorunemi:
                            coordinadorcarrera = coordinadorcarrera.exclude(
                                persona=practicasprofesionales.tutorunemi.persona)
                            listaprofesor.append([u'%s' % practicasprofesionales.tutorunemi.id,
                                                  u'%s - (%s) - asig.(%s) - %s' % (
                                                      practicasprofesionales.tutorunemi.persona.nombre_completo_inverso(),
                                                      periodo.nombre,
                                                      practicasprofesionales.tutorunemi.contar_practicaspreprofesionales_asignadas(
                                                          periodo), 'Director(a) de carrera')])
                    for x in coordinadorcarrera:
                        if x.persona.profesor():
                            profe = x.persona.profesor()
                            listaprofesor.append([u'%s' % profe.id, u'%s - (%s) - asig.(%s) - %s' % (
                                profe.persona.nombre_completo_inverso(), x.periodo.nombre,
                                profe.contar_practicaspreprofesionales_asignadas(periodo), 'Director(a) de carrera')])
                    # MUESTRA EL MENSAJE DEL PERIODO
                    data = {"result": "ok", "results": listaprofesor,
                            "mensaje": u'%s %s' % ("Listado de directores de carrera esta en el periodo", periodo)}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

            elif action == 'documentosrequeridos':
                try:
                    data['title'] = u'Documentos Requeridos'
                    data['evento'] = RequisitosHomologacionPracticas.objects.filter(status=True).order_by('nombre')
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewdocumento.html", data)
                except Exception as ex:
                    pass

            elif action == 'addrequisitoscarrera':
                try:
                    data['id'] = id = request.GET['id']
                    data['itinerarioid'] = itinerarioid = request.GET['itinerario']
                    data['tipoid'] = tipoid = request.GET['tipo']
                    data['filtro'] = filtro = CarreraHomologacion.objects.get(pk=id)
                    data['itinerario'] = itinerario = ItinerariosMalla.objects.get(pk=itinerarioid)
                    excluir = CarreraHomologacionRequisitos.objects.filter(carrera=filtro, itinerario=itinerario,
                                                                           tipo=tipoid, status=True).values_list(
                        'documento_id', flat=True)
                    form = DocumentoRequeridoCarreraForm()
                    form.fields['documento'].queryset = RequisitosHomologacionPracticas.objects.filter(
                        status=True).exclude(id__in=excluir)
                    data['form2'] = form
                    template = get_template(
                        "alu_practicaspreprofesionalesinscripcion/modal/formdocumentositinerarios_apertura.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'adddocumento':
                try:
                    data['form2'] = DocumentoRequeridoPracticaForm()
                    template = get_template("alu_practicaspreprofesionalesinscripcion/modal/formdocumentos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editdocumento':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = RequisitosHomologacionPracticas.objects.get(pk=request.GET['id'])
                    data['form2'] = DocumentoRequeridoPracticaForm(initial=model_to_dict(filtro))
                    template = get_template("alu_practicaspreprofesionalesinscripcion/modal/formdocumentos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'aperturasolicitud':
                try:
                    data['title'] = u'Aperturas de solicitud en Práctica Pre-Profesionales'
                    search = None
                    ids = None
                    aperturadas = None
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        aperturadas = AperturaPracticaPreProfesional.objects.filter(pk=ids, status=True).order_by(
                            '-fechaapertura')
                    elif 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            aperturadas = AperturaPracticaPreProfesional.objects.filter(pk=search,
                                                                                        status=True).order_by(
                                '-fechaapertura')
                        else:
                            if ' ' in search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    aperturadas = AperturaPracticaPreProfesional.objects.filter(
                                        (Q(motivo__icontains=s[0])) | (Q(mensaje__icontains=s[0])),
                                        Q(status=True)).order_by('-fechaapertura')
                                elif len(s) == 2:
                                    aperturadas = AperturaPracticaPreProfesional.objects.filter(((Q(
                                        motivo__icontains=s[0]) & Q(motivo__icontains=s[1])) | (Q(
                                        mensaje__icontains=s[0]) & Q(mensaje__icontains=s[1]))), Q(
                                        status=True)).order_by('-fechaapertura')
                                elif len(s) == 3:
                                    aperturadas = AperturaPracticaPreProfesional.objects.filter(((Q(
                                        motivo__icontains=s[0]) & Q(motivo__icontains=s[1]) & Q(
                                        motivo__icontains=s[2])) | (Q(mensaje__icontains=s[0]) & Q(
                                        mensaje__icontains=s[1]) & Q(mensaje__icontains=s[2]))), Q(
                                        status=True)).order_by('-fechaapertura')
                            else:
                                aperturadas = AperturaPracticaPreProfesional.objects.filter(status=True).order_by(
                                    '-fechaapertura')
                    else:
                        aperturadas = AperturaPracticaPreProfesional.objects.filter(status=True).order_by(
                            '-fechaapertura')
                    paging = MiPaginador(aperturadas, 10)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listasapertura'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request,
                                  "alu_practicaspreprofesionalesinscripcion/viewaperturasolicitudpractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'addaperturasolicitud':
                try:
                    data['title'] = u'Adicionar apertura de solicitud en Práctica Pre-Profesionales'
                    form = AperturaPracticaPreProfesionalForm(initial={'periodo': periodo})
                    form.adicionar()
                    data['form'] = form
                    data['TIPO_PRACTICA_PP'] = TIPO_PRACTICA_PP
                    data['TIPO_SOLICITUD_PRACTICAPRO'] = TIPO_SOLICITUD_PRACTICAPRO
                    return render(request, "alu_practicaspreprofesionalesinscripcion/addaperturasolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'editaperturasolicitud':
                try:
                    data['title'] = u'Editar apertura de solicitud en Práctica Pre-Profesionales'
                    data['apertura'] = apertura = AperturaPracticaPreProfesional.objects.get(pk=int(request.GET['id']))
                    form = AperturaPracticaPreProfesionalForm(initial=model_to_dict(apertura))
                    form.cargar_carrera(apertura)
                    data['form'] = form
                    data['TIPO_PRACTICA_PP'] = TIPO_PRACTICA_PP
                    data['TIPO_SOLICITUD_PRACTICAPRO'] = TIPO_SOLICITUD_PRACTICAPRO
                    return render(request,
                                  "alu_practicaspreprofesionalesinscripcion/editaperturasolicitudpractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delaperturasolicitud':
                try:
                    data['title'] = u'Eliminar apertura de solicitud en Práctica Pre-Profesionales'
                    data['apertura'] = AperturaPracticaPreProfesional.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/delaperturasolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'formatopractica':
                try:
                    data['title'] = u'Formatos de Práctica Pre-Profesionales'
                    search = None
                    ids = None
                    formatos = None
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        formatos = FormatoPracticaPreProfesional.objects.filter(pk=ids, status=True)
                    elif 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            formatos = FormatoPracticaPreProfesional.objects.filter(pk=search, status=True)
                        else:
                            if search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    formatos = FormatoPracticaPreProfesional.objects.filter(Q(nombre__icontains=s[0]),
                                                                                            Q(status=True))
                                elif len(s) == 2:
                                    formatos = FormatoPracticaPreProfesional.objects.filter(Q(nombre__icontains=s[0]),
                                                                                            Q(nombre__icontains=s[1]),
                                                                                            Q(status=True))
                                elif len(s) == 3:
                                    formatos = FormatoPracticaPreProfesional.objects.filter(Q(nombre__icontains=s[0]),
                                                                                            Q(nombre__icontains=s[1]),
                                                                                            Q(nombre__icontains=s[2]),
                                                                                            Q(status=True))
                            else:
                                formatos = FormatoPracticaPreProfesional.objects.filter(status=True)
                    else:
                        formatos = FormatoPracticaPreProfesional.objects.filter(status=True)
                    paging = MiPaginador(formatos, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listasformatos'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewformatospractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'addformatopractica':
                try:
                    data['title'] = u'Adicionar Formatos de Práctica Pre-Profesionales'
                    data['form'] = FormatoPracticaPreProfesionalForm()
                    return render(request, "alu_practicaspreprofesionalesinscripcion/addformatopractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'editformatopractica':
                try:
                    data['title'] = u'Editar formato de Práctica Pre-Profesionales'
                    data['formato'] = formato = FormatoPracticaPreProfesional.objects.get(pk=int(request.GET['id']))
                    data['form'] = FormatoPracticaPreProfesionalForm(
                        initial={'nombre': formato.nombre, 'vigente': formato.vigente})
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editformatopractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delformatopractica':
                try:
                    data['title'] = u'Eliminar formato de Práctica Pre-Profesionales'
                    data['formato'] = FormatoPracticaPreProfesional.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/delformatopractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalleformatopractica':
                try:
                    data['title'] = u'Detalles de formatos de Práctica Pre-Profesionales'
                    search = None
                    ids = None
                    detalleformatos = None
                    data['formato'] = formatos = FormatoPracticaPreProfesional.objects.get(pk=int(request.GET['id']),
                                                                                           status=True)
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            detalleformatos = formatos.detalleformatopracticapreprofesional_set.objects.filter(
                                pk=search, status=True)
                        else:
                            if search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    detalleformatos = formatos.detalleformatopracticapreprofesional_set.objects.filter(
                                        Q(nombre__icontains=s[0]), Q(status=True))
                                elif len(s) == 2:
                                    detalleformatos = formatos.detalleformatopracticapreprofesional_set.objects.filter(
                                        Q(nombre__icontains=s[0]), Q(nombre__icontains=s[1]), Q(status=True))
                                elif len(s) == 3:
                                    detalleformatos = formatos.detalleformatopracticapreprofesional_set.objects.filter(
                                        Q(nombre__icontains=s[0]), Q(nombre__icontains=s[1]), Q(nombre__icontains=s[2]),
                                        Q(status=True))
                            else:
                                detalleformatos = formatos.detalleformatopracticapreprofesional_set.objects.filter(
                                    status=True)
                    else:
                        detalleformatos = formatos.detalleformatopracticapreprofesional_set.filter(status=True)
                    paging = MiPaginador(detalleformatos, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listasdetallesformato'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewdetalleformatospractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'adddetalleformatopractica':
                try:
                    data['title'] = u'Adicionar detalle formatos de Práctica Pre-Profesionales'
                    data['form'] = DetalleFormatoPracticaPreProfesionalForm()
                    data['formato'] = FormatoPracticaPreProfesional.objects.get(pk=int(request.GET['id']), status=True)
                    return render(request, "alu_practicaspreprofesionalesinscripcion/adddetalleformatopractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'editdetalleformatopractica':
                try:
                    data['title'] = u'Editar detalle formato de Práctica Pre-Profesionales'
                    data['detalleformato'] = detalleformato = DetalleFormatoPracticaPreProfesional.objects.get(
                        pk=int(request.GET['id']), status=True)
                    data['form'] = DetalleFormatoPracticaPreProfesionalForm(
                        initial={'nombre': detalleformato.nombre, 'vigente': detalleformato.vigente})
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editdetalleformatopractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'deldetalleformatopractica':
                try:
                    data['title'] = u'Eliminar detalle de formato de Práctica Pre-Profesionales'
                    data['detalleformato'] = DetalleFormatoPracticaPreProfesional.objects.get(pk=int(request.GET['id']),
                                                                                              status=True)
                    return render(request, "alu_practicaspreprofesionalesinscripcion/deldetalleformatopractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'duplicarsolicitudpractica':
                try:
                    data['title'] = u'Duplicar solicitud de práctica pre profesional'
                    data['practicapreprofesional'] = PracticasPreprofesionalesInscripcion.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    return render(request,
                                  "alu_practicaspreprofesionalesinscripcion/confirmarduplicarsolicitudpractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'perevidenciapractica':
                try:
                    data['title'] = u'Periodo de evidencia de Práctica Pre-Profesionales'
                    search = None
                    periodoevidencia = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            periodoevidencia = CabPeriodoEvidenciaPPP.objects.filter(pk=search, status=True).order_by(
                                'fechainicio')
                        else:
                            if ' ' in search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    periodoevidencia = CabPeriodoEvidenciaPPP.objects.filter(Q(nombre__icontains=s[0]),
                                                                                             Q(status=True)).order_by(
                                        'fechainicio')
                                elif len(s) == 2:
                                    periodoevidencia = CabPeriodoEvidenciaPPP.objects.filter(
                                        Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(
                                            status=True)).order_by('fechainicio')
                                elif len(s) == 3:
                                    periodoevidencia = CabPeriodoEvidenciaPPP.objects.filter(
                                        Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(
                                            nombre__icontains=s[2]), Q(status=True)).order_by('fechainicio')
                            else:
                                periodoevidencia = CabPeriodoEvidenciaPPP.objects.filter(status=True).order_by(
                                    'fechainicio')
                    else:
                        periodoevidencia = CabPeriodoEvidenciaPPP.objects.filter(status=True).order_by('fechainicio')
                    paging = MiPaginador(periodoevidencia, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['periodoevidencias'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewperiodoevidenciapractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'addperevidenciapractica':
                try:
                    data['title'] = u'Adicionar periodo de evidencias de Práctica Pre-Profesionales'
                    data['form'] = PeriodoEvidenciaPracticaProfesionalesForm()
                    return render(request, "alu_practicaspreprofesionalesinscripcion/addperevidenciapractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'editperevidenciapractica':
                try:
                    data['title'] = u'Editar periodo de evidencias de Práctica Pre-Profesionales'
                    data['periodoevidencia'] = periodoevidencia = CabPeriodoEvidenciaPPP.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    idcarreras = PeriodoEvidenciaPracticaProfesionales.objects.values_list('carrera_id',
                                                                                           flat=True).filter(
                        status=True, periodo=periodoevidencia)
                    carreras = Carrera.objects.filter(id__in=idcarreras)
                    data['form'] = PeriodoEvidenciaPracticaProfesionalesAuxForm(
                        initial={'nombre': periodoevidencia.nombre,
                                 'carrera': carreras,
                                 'fechainicio': periodoevidencia.fechainicio,
                                 'evaluarpromedio': periodoevidencia.evaluarpromedio,
                                 'fechafin': periodoevidencia.fechafin})
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editperevidenciapractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'delperevidenciapractica':
                try:
                    data['title'] = u'Eliminar periodo de evidencias de Práctica Pre-Profesionales'
                    data['periodoevidencia'] = CabPeriodoEvidenciaPPP.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/delperevidenciapractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'evidenciapractica':
                try:
                    data['title'] = u'Evidencia de Práctica Pre-Profesionales'
                    search = None
                    evidencia = None
                    data['periodoevidencia'] = periodoevidencia = CabPeriodoEvidenciaPPP.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            evidencia = periodoevidencia.evidenciapracticasprofesionales_set.filter(pk=search,
                                                                                                    status=True)
                        else:
                            if ' ' in search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    evidencia = periodoevidencia.evidenciapracticasprofesionales_set.filter(
                                        Q(nombre__icontains=s[0]), Q(status=True))
                                elif len(s) == 2:
                                    evidencia = periodoevidencia.evidenciapracticasprofesionales_set.filter(
                                        Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(status=True))
                                elif len(s) == 3:
                                    evidencia = periodoevidencia.evidenciapracticasprofesionales_set.filter(
                                        Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(
                                            nombre__icontains=s[2]), Q(status=True))
                            else:
                                evidencia = periodoevidencia.evidenciapracticasprofesionales_set.filter(status=True)
                    else:
                        evidencia = periodoevidencia.evidenciapracticasprofesionales_set.filter(status=True)
                    paging = MiPaginador(evidencia, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['evidencias'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewevidenciapractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'addevidenciapractica':
                try:
                    data['title'] = u'Adicionar periodo de evidencias de Práctica Pre-Profesionales'
                    data['periodoevidencia'] = periodoevidencia = CabPeriodoEvidenciaPPP.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['form'] = EvidenciaPracticasPreProfesionalForm(
                        initial={'fechainicio': periodoevidencia.fechainicio, 'fechafin': periodoevidencia.fechafin})
                    return render(request, "alu_practicaspreprofesionalesinscripcion/addevidenciapractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'editevidenciapractica':
                try:
                    data['title'] = u'Editar periodo de evidencias de Práctica Pre-Profesionales'
                    data['evidencia'] = evidencia = EvidenciaPracticasProfesionales.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['form'] = EvidenciaPracticasPreProfesionalForm(initial={'nombre': evidencia.nombre,
                                                                                 'fechainicio': evidencia.fechainicio,
                                                                                 'fechafin': evidencia.fechafin,
                                                                                 'nombrearchivo': evidencia.nombrearchivo,
                                                                                 'configurarfecha': evidencia.configurarfecha,
                                                                                 'orden': evidencia.orden,
                                                                                 'puntaje': evidencia.puntaje})
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editevidenciapractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'fechasevidenciapractica':
                try:
                    data['title'] = u'Asignar fechas de subida evidencias de Práctica Pre-Profesionales'
                    data['evidencia'] = evidencia = EvidenciaPracticasProfesionales.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['form'] = EvidenciaPracticasPreProfesionalForm(initial={'nombre': evidencia.nombre,
                                                                                 'fechainicio': evidencia.fechainicio,
                                                                                 'fechafin': evidencia.fechafin,
                                                                                 'nombrearchivo': evidencia.nombrearchivo,
                                                                                 'configurarfecha': evidencia.configurarfecha,
                                                                                 'orden': evidencia.orden,
                                                                                 'puntaje': evidencia.puntaje})
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editevidenciapractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delevidenciapractica':
                try:
                    data['title'] = u'Eliminar periodo de evidencias de Práctica Pre-Profesionales'
                    data['evidencia'] = EvidenciaPracticasProfesionales.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/delevidenciapractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delarchivoevidenciapractica':
                try:
                    data['title'] = u'Eliminar archivo de evidencias de Práctica Pre-Profesionales '
                    data['evidencia'] = EvidenciaPracticasProfesionales.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/delarchivoevidenciapractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'delarchivodetalleevidencia':
                try:
                    data['title'] = u'Eliminar archivo de evidencias del estudiante'
                    data['evidencia'] = DetalleEvidenciasPracticasPro.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/delarchivodetalleevidencia.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'inscripcionoferta':
                try:
                    data['title'] = u'Inscritos en oferta de Prácticas Preprofesionales'
                    data['oferta'] = oferta = OfertasPracticas.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['practicaspreprofesionales'] = PracticasPreprofesionalesInscripcion.objects.filter(
                        oferta=oferta, status=True).order_by('-fecha_creacion')
                    return render(request, "alu_practicaspreprofesionalesinscripcion/inscripcionoferta.html", data)
                except Exception as ex:
                    pass

            elif action == 'informemensualsupervisor':
                try:
                    data['title'] = u'Informe mensual de Prácticas Preprofesionales'
                    search = None
                    ids = None
                    informe = None
                    carreras = Carrera.objects.filter(status=True)
                    distributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor__persona=persona)
                    if distributivo.exists():
                        distributivo = distributivo[0]
                        coordinador = distributivo.coordinacion.responsable_periododos(periodo, 1)
                        directorcarrera = distributivo.carrera.coordinador(periodo,
                                                                           distributivo.coordinacion.sede) if distributivo.carrera else None
                        if coordinador:
                            carreras = carreras.filter(pk__in=coordinador.coordinacion.carreras().values_list('id'))
                        if directorcarrera:
                            carreras = carreras.filter(pk=directorcarrera.carrera.id)
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search:
                            s = search.split(" ")
                            if len(s) == 1:
                                informe = InformeMensualSupervisorPractica.objects.filter(
                                    (Q(persona__apellido1__icontains=s[0]) |
                                     Q(persona__apellido2__icontains=s[0]) |
                                     Q(persona__nombres__icontains=s[0])) &
                                    Q(status=True) & Q(carrera__in=carreras)).distinct()
                            elif len(s) == 2:
                                informe = InformeMensualSupervisorPractica.objects.filter(
                                    ((Q(persona__apellido1__icontains=s[0]) &
                                      Q(persona__apellido2__icontains=s[1])) |
                                     Q(persona__nombres__icontains=s[0]) &
                                     Q(persona__nombres__icontains=s[1])) &
                                    Q(status=True) & Q(carrera__in=carreras)).distinct()
                            elif len(s) == 3:
                                informe = InformeMensualSupervisorPractica.objects.filter(
                                    Q(persona__apellido1__icontains=s[0]) &
                                    Q(persona__apellido2__icontains=s[1]) &
                                    Q(persona__nombres__icontains=s[2]) &
                                    Q(status=True) & Q(carrera__in=carreras)).distinct()
                            elif len(s) == 4:
                                informe = InformeMensualSupervisorPractica.objects.filter(
                                    Q(persona__apellido1__icontains=s[0]) &
                                    Q(persona__apellido2__icontains=s[1]) &
                                    Q(persona__nombres__icontains=s[2]) &
                                    Q(persona__nombres__icontains=s[3]) &
                                    Q(status=True) & Q(carrera__in=carreras)).distinct()
                        else:
                            informe = InformeMensualSupervisorPractica.objects.filter(status=True,
                                                                                      carrera__in=carreras).distinct()
                    else:
                        informe = InformeMensualSupervisorPractica.objects.filter(status=True,
                                                                                  carrera__in=carreras).distinct()
                    paging = MiPaginador(informe, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['informesupervisor'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewinformemensualsupervisor.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'informemensual':
                try:
                    data['title'] = u'Informe mensual de Prácticas Preprofesionales'
                    search = None
                    ids = None
                    informe = None
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        informe = InformeMensualSupervisorPractica.objects.filter(pk=ids, persona=persona, status=True)
                    elif 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            informe = InformeMensualSupervisorPractica.objects.filter(pk=search, status=True,
                                                                                      persona=persona)
                        else:
                            if search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    informe = InformeMensualSupervisorPractica.objects.filter(
                                        Q(observacion__icontains=s[0]), Q(status=True), Q(persona=persona))
                                elif len(s) == 2:
                                    informe = InformeMensualSupervisorPractica.objects.filter(
                                        Q(observacion__icontains=s[0]), Q(observacion__icontains=s[1]), Q(status=True),
                                        Q(persona=persona))
                                elif len(s) == 3:
                                    informe = InformeMensualSupervisorPractica.objects.filter(
                                        Q(observacion__icontains=s[0]), Q(observacion__icontains=s[1]),
                                        Q(observacion__icontains=s[2]), Q(status=True), Q(persona=persona))
                            else:
                                informe = InformeMensualSupervisorPractica.objects.filter(status=True, persona=persona)
                    else:
                        informe = InformeMensualSupervisorPractica.objects.filter(status=True, persona=persona)
                    paging = MiPaginador(informe, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['informesupervisor'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewinformemensual.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinformemensual':
                try:
                    data['title'] = u'Adicionar informe mensual de Prácticas Preprofesionales'
                    form = InformeMensualSupervisorPracticaForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/addinformemensual.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinformemensual':
                try:
                    data['title'] = u'Editar informe mensual de Prácticas Preprofesionales'
                    data['informesupervisor'] = informe = InformeMensualSupervisorPractica.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['form'] = InformeMensualSupervisorPracticaForm(initial={'fechainicio': informe.fechainicio,
                                                                                 'fechafin': informe.fechafin,
                                                                                 'observacion': informe.observacion,
                                                                                 'carrera': informe.carreras()})
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editinformemensual.html", data)
                except Exception as ex:
                    pass

            elif action == 'delinformemensual':
                try:
                    data['title'] = u'Eliminar informe mensual de Prácticas Preprofesionales'
                    data['informesupervisor'] = InformeMensualSupervisorPractica.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/delinformemensual.html", data)
                except Exception as ex:
                    pass

            elif action == 'practicastutorias':
                try:
                    data['title'] = u'Vinculación y seguimiento de Prácticas Preprofesionales (Tutorías)'
                    empezarbuscar = True
                    fechainicio, fechafin, idi, idt, ide, ids, idd, idcor, idcar, filtro, url_vars = request.GET.get(
                        'fi', ''), request.GET.get('ff', ''), request.GET.get('idi', ''), request.GET.get('idt',
                                                                                                          ''), request.GET.get(
                        'ide', ''), request.GET.get('ids', ''), request.GET.get('idd', ''), request.GET.get('idcor',
                                                                                                            ''), request.GET.get(
                        'idcar', ''), Q(status=True), ''
                    detallevisitas = PracticasTutoria.objects.select_related('practica').filter(status=True)
                    if ids:
                        empezarbuscar = False
                        ids = int(encrypt(request.GET['ids']))
                        if ids > 0:
                            detallevisitas = detallevisitas.filter(practica__supervisor__id=ids)
                    if idd:
                        empezarbuscar = False
                        idd = int(encrypt(request.GET['idd']))
                        if idd > 0:
                            detallevisitas = detallevisitas.filter(practica__tutorunemi__id=idd)
                    if idcor:
                        idcor = int(encrypt(request.GET['idcor']))
                        if idcor > 0:
                            detallevisitas = detallevisitas.filter(
                                practica__inscripcion__carrera__coordinacion__id=idcor)
                    if idcar:
                        idcar = int(encrypt(request.GET['idcar']))
                        if idcar > 0:
                            detallevisitas = detallevisitas.filter(practica__inscripcion__carrera__id=idcar)
                        else:
                            idcar = None
                    if idi:
                        idi = int(encrypt(request.GET['idi']))
                        if idi > 0:
                            detallevisitas = detallevisitas.filter(practica__inscripcion__id=idi)
                        else:
                            idi = None
                    if fechainicio and fechafin:
                        fechainicio = request.GET['fi']
                        fechafin = request.GET['ff']
                        detallevisitas = detallevisitas.filter(fechainicio__range=(fechainicio, fechafin))
                    if idt:
                        idt = int(encrypt(request.GET['idt']))
                        detallevisitas = detallevisitas.filter(visitapractica__tipo=idt)
                    if ide:
                        ide = int(encrypt(request.GET['ide']))
                        detallevisitas = detallevisitas.filter(estado=ide)
                    detallevisitas = detallevisitas.order_by('-pk')
                    if 'export_to_excel' in request.GET:
                        columns = [
                            ('Fecha Creación', 10000),
                            ('Supervisor', 10000),
                            ('Docentes', 10000),
                            ('Estudiante', 10000),
                            ('Carrera', 10000),
                            ('Institución', 10000),
                            # ('Tutorias', 5000),
                            ('Fecha', 6000),
                            ('Observación', 20000),
                            ('Sugerencia', 20000),
                        ]
                        response = HttpResponse(content_type='application/ms-excel')
                        response['Content-Disposition'] = 'attachment; filename="reporte_practicas.xls"'
                        wb = xlwt.Workbook(encoding='utf-8')
                        ws = wb.add_sheet('HOJA_1')
                        row_num = 0
                        font_style = xlwt.XFStyle()
                        font_style.font.bold = True
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        font_style = xlwt.XFStyle()
                        for det in detallevisitas:
                            row_num += 1
                            ws.write(row_num, 0, str(det.fecha_creacion), font_style)
                            ws.write(row_num, 1, det.practica.supervisor.persona.nombre_completo_inverso(), font_style)
                            ws.write(row_num, 2, det.practica.tutorunemi.persona.nombre_completo_inverso(), font_style)
                            ws.write(row_num, 3, det.practica.inscripcion.persona.nombre_completo_inverso(), font_style)
                            ws.write(row_num, 4, det.practica.inscripcion.carrera.nombre, font_style)
                            institucion = ''
                            if det.practica.institucion:
                                institucion = det.practica.institucion.upper()
                            else:
                                if det.practica.empresaempleadora:
                                    institucion = det.practica.empresaempleadora.nombre
                                else:
                                    institucion = det.practica.otraempresaempleadora.upper()
                            # tutorias = 'NO OBLIGATORIAS'
                            # if  det.practica.tipo == 1 or  det.practica.tipo == 2 :
                            #     if det.practica.aplicatutoria:
                            #         if det.practica.culminatutoria:
                            #             tutorias = 'CULMINADA'
                            #         else:
                            #             tutorias = 'PENDIENTE'

                            ws.write(row_num, 5, institucion, font_style)
                            # ws.write(row_num, 6, tutorias, font_style)
                            ws.write(row_num, 6, str(det.fechainicio), font_style)
                            ws.write(row_num, 7, det.observacion, font_style)
                            ws.write(row_num, 8, det.sugerencia, font_style)
                        wb.save(response)
                        return response
                    paging = MiPaginador(detallevisitas, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['detallesvisitas'] = page.object_list
                    data['fechainicio'] = str(fechainicio)
                    data['fechafin'] = str(fechafin)
                    data['fechainiciostr'] = fechainicio
                    data['fechafinstr'] = fechafin
                    data['ESTADO_TIPO_VISITA'] = ESTADO_TIPO_VISITA
                    data['ESTADO_VISITA_PRACTICA'] = ESTADO_VISITA_PRACTICA
                    data['idi'] = idi
                    data['idt'] = idt
                    data['ide'] = ide
                    data['ids'] = ids
                    data['idd'] = idd
                    data['idcor'] = idcor
                    data['idcar'] = idcar
                    data['if_idt'] = True if 'idt' in request.GET else False
                    data['if_ide'] = True if 'ide' in request.GET else False
                    data['supervisores'] = PracticasPreprofesionalesInscripcion.objects.values_list('supervisor__id',
                                                                                                    'supervisor__persona__apellido1',
                                                                                                    'supervisor__persona__apellido2',
                                                                                                    'supervisor__persona__nombres').filter(
                        status=True, supervisor__isnull=False).distinct().order_by('supervisor__id',
                                                                                   'supervisor__persona__apellido1',
                                                                                   'supervisor__persona__apellido2',
                                                                                   'supervisor__persona__nombres')
                    data['docentes'] = PracticasPreprofesionalesInscripcion.objects.values_list('tutorunemi__id',
                                                                                                'tutorunemi__persona__apellido1',
                                                                                                'tutorunemi__persona__apellido2',
                                                                                                'tutorunemi__persona__nombres').filter(
                        status=True, tutorunemi__isnull=False).distinct('tutorunemi').order_by('tutorunemi__id',
                                                                                               'tutorunemi__persona__apellido1',
                                                                                               'tutorunemi__persona__apellido2',
                                                                                               'tutorunemi__persona__nombres')
                    if ids:
                        inscripciones = PracticasPreprofesionalesInscripcion.objects.values_list('inscripcion__id',
                                                                                                 'inscripcion__persona__apellido1',
                                                                                                 'inscripcion__persona__apellido2',
                                                                                                 'inscripcion__persona__nombres').filter(
                            status=True, supervisor__id=ids).distinct().order_by('inscripcion__persona__apellido1',
                                                                                 'inscripcion__persona__apellido2',
                                                                                 'inscripcion__persona__nombres')
                    else:
                        inscripciones = PracticasPreprofesionalesInscripcion.objects.values_list('inscripcion__id',
                                                                                                 'inscripcion__persona__apellido1',
                                                                                                 'inscripcion__persona__apellido2',
                                                                                                 'inscripcion__persona__nombres').filter(
                            status=True).distinct().order_by('inscripcion__persona__apellido1',
                                                             'inscripcion__persona__apellido2',
                                                             'inscripcion__persona__nombres')

                    if idd:
                        inscripciones = PracticasPreprofesionalesInscripcion.objects.values_list('inscripcion__id',
                                                                                                 'inscripcion__persona__apellido1',
                                                                                                 'inscripcion__persona__apellido2',
                                                                                                 'inscripcion__persona__nombres').filter(
                            status=True, tutorunemi__id=idd).distinct().order_by('inscripcion__persona__apellido1',
                                                                                 'inscripcion__persona__apellido2',
                                                                                 'inscripcion__persona__nombres')
                    else:
                        inscripciones = PracticasPreprofesionalesInscripcion.objects.values_list('inscripcion__id',
                                                                                                 'inscripcion__persona__apellido1',
                                                                                                 'inscripcion__persona__apellido2',
                                                                                                 'inscripcion__persona__nombres').filter(
                            status=True).distinct().order_by('inscripcion__persona__apellido1',
                                                             'inscripcion__persona__apellido2',
                                                             'inscripcion__persona__nombres')

                    listacarreras = inscripciones.values_list('inscripcion__carrera__id').distinct(
                        'inscripcion__carrera__id').order_by('inscripcion__carrera__id')
                    carreras = []
                    if not empezarbuscar:
                        carreras = Carrera.objects.filter(pk__in=listacarreras).distinct()
                    data['carreras'] = carreras
                    data['coordinaciones'] = Coordinacion.objects.filter(carrera__id__in=listacarreras).distinct()
                    data['inscripciones'] = inscripciones
                    data['empezarbuscar'] = empezarbuscar
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewdetallepractica.html", data)
                except Exception as ex:
                    print(ex)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'practicasvisitada':
                try:
                    data['title'] = u'Vinculación y seguimiento de Prácticas Preprofesionales (Visitas) '
                    empezarbuscar = True
                    fechainicio, fechafin, idi, idt, ide, ids, idd, idcor, idcar, filtro, url_vars = request.GET.get(
                        'fi', ''), request.GET.get('ff', ''), request.GET.get('idi', ''), request.GET.get('idt',
                                                                                                          ''), request.GET.get(
                        'ide', ''), request.GET.get('ids', ''), request.GET.get('idd', ''), request.GET.get('idcor',
                                                                                                            ''), request.GET.get(
                        'idcar', ''), Q(status=True), ''
                    detallevisitas = VisitaPractica_Detalle.objects.filter(status=True)
                    if ids:
                        empezarbuscar = False
                        ids = int(encrypt(request.GET['ids']))
                        if ids > 0:
                            detallevisitas = detallevisitas.filter(practica__supervisor__id=ids, )
                    if idd:
                        empezarbuscar = False
                        idd = int(encrypt(request.GET['idd']))
                        if idd > 0:
                            detallevisitas = detallevisitas.filter(practica__tutorunemi__id=idd)
                    if idcor:
                        idcor = int(encrypt(request.GET['idcor']))
                        if idcor > 0:
                            detallevisitas = detallevisitas.filter(
                                practica__inscripcion__carrera__coordinacion__id=idcor)
                    if idcar:
                        idcar = int(encrypt(request.GET['idcar']))
                        if idcar > 0:
                            detallevisitas = detallevisitas.filter(practica__inscripcion__carrera__id=idcar)
                    if idi:
                        idi = int(encrypt(request.GET['idi']))
                        if idi > 0:
                            detallevisitas = detallevisitas.filter(practica__inscripcion__id=idi)
                    if fechainicio and fechafin:
                        fechainicio = request.GET['fi']
                        fechafin = request.GET['ff']
                        detallevisitas = detallevisitas.filter(visitapractica__fecha__range=(fechainicio, fechafin),
                                                               status=True)
                    if idt:
                        idt = int(encrypt(request.GET['idt']))
                        detallevisitas = detallevisitas.filter(tipo=idt, status=True)
                    if ide:
                        ide = int(encrypt(request.GET['ide']))
                        detallevisitas = detallevisitas.filter(estado=ide, status=True)
                    detallevisitas = detallevisitas.order_by('-pk')
                    if 'export_to_excel' in request.GET:
                        columns = [
                            ('Supervisor', 10000),
                            ('Docentes', 10000),
                            ('Estudiante', 10000),
                            ('Carrera', 10000),
                            ('Visitas Realizadas', 6000),
                            ('Fecha', 6000),
                            ('Tipo', 6000),
                            ('Estado', 6000),
                            ('Observación', 6000),
                        ]
                        response = HttpResponse(content_type='application/ms-excel')
                        response['Content-Disposition'] = 'attachment; filename="reporte_visitas.xls"'
                        wb = xlwt.Workbook(encoding='utf-8')
                        ws = wb.add_sheet('HOJA_1')
                        row_num = 0
                        font_style = xlwt.XFStyle()
                        font_style.font.bold = True
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        font_style = xlwt.XFStyle()
                        for det in detallevisitas:
                            row_num += 1
                            ws.write(row_num, 0, det.practica.supervisor.persona.nombre_completo_inverso(), font_style)
                            ws.write(row_num, 1, det.practica.tutorunemi.persona.nombre_completo_inverso(), font_style)
                            ws.write(row_num, 2, det.practica.inscripcion.persona.nombre_completo_inverso(), font_style)
                            ws.write(row_num, 3, det.practica.inscripcion.carrera.nombre, font_style)
                            ws.write(row_num, 4, det.practica.total_visita_realizada(), font_style)
                            ws.write(row_num, 5, str(det.visitapractica.fecha), font_style)
                            ws.write(row_num, 6, det.get_tipo_display(), font_style)
                            ws.write(row_num, 7, det.get_estado_display(), font_style)
                            ws.write(row_num, 8, det.observacion, font_style)
                        wb.save(response)
                        return response
                    paging = MiPaginador(detallevisitas, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['detallesvisitas'] = page.object_list
                    data['fechainicio'] = str(fechainicio)
                    data['fechafin'] = str(fechafin)
                    data['ESTADO_TIPO_VISITA'] = ESTADO_TIPO_VISITA
                    data['ESTADO_VISITA_PRACTICA'] = ESTADO_VISITA_PRACTICA
                    data['idi'] = idi
                    data['idt'] = idt
                    data['ide'] = ide
                    data['ids'] = ids
                    data['idd'] = idd
                    data['idcor'] = idcor
                    data['idcar'] = idcar
                    data['if_idt'] = True if 'idt' in request.GET else False
                    data['if_ide'] = True if 'ide' in request.GET else False
                    data['supervisores'] = PracticasPreprofesionalesInscripcion.objects.values_list('supervisor__id',
                                                                                                    'supervisor__persona__apellido1',
                                                                                                    'supervisor__persona__apellido2',
                                                                                                    'supervisor__persona__nombres').filter(
                        status=True, supervisor__isnull=False).distinct().order_by('supervisor__id',
                                                                                   'supervisor__persona__apellido1',
                                                                                   'supervisor__persona__apellido2',
                                                                                   'supervisor__persona__nombres')
                    data['docentes'] = PracticasPreprofesionalesInscripcion.objects.values_list('tutorunemi__id',
                                                                                                'tutorunemi__persona__apellido1',
                                                                                                'tutorunemi__persona__apellido2',
                                                                                                'tutorunemi__persona__nombres').filter(
                        status=True, tutorunemi__isnull=False).distinct('tutorunemi').order_by('tutorunemi__id',
                                                                                               'tutorunemi__persona__apellido1',
                                                                                               'tutorunemi__persona__apellido2',
                                                                                               'tutorunemi__persona__nombres')
                    if ids:
                        inscripciones = PracticasPreprofesionalesInscripcion.objects.values_list('inscripcion__id',
                                                                                                 'inscripcion__persona__apellido1',
                                                                                                 'inscripcion__persona__apellido2',
                                                                                                 'inscripcion__persona__nombres').filter(
                            status=True, supervisor__id=ids).distinct().order_by('inscripcion__persona__apellido1',
                                                                                 'inscripcion__persona__apellido2',
                                                                                 'inscripcion__persona__nombres')
                    else:
                        inscripciones = PracticasPreprofesionalesInscripcion.objects.values_list('inscripcion__id',
                                                                                                 'inscripcion__persona__apellido1',
                                                                                                 'inscripcion__persona__apellido2',
                                                                                                 'inscripcion__persona__nombres').filter(
                            status=True).distinct().order_by('inscripcion__persona__apellido1',
                                                             'inscripcion__persona__apellido2',
                                                             'inscripcion__persona__nombres')

                    if idd:
                        inscripciones = PracticasPreprofesionalesInscripcion.objects.values_list('inscripcion__id',
                                                                                                 'inscripcion__persona__apellido1',
                                                                                                 'inscripcion__persona__apellido2',
                                                                                                 'inscripcion__persona__nombres').filter(
                            status=True, tutorunemi__id=idd).distinct().order_by('inscripcion__persona__apellido1',
                                                                                 'inscripcion__persona__apellido2',
                                                                                 'inscripcion__persona__nombres')
                    else:
                        inscripciones = PracticasPreprofesionalesInscripcion.objects.values_list('inscripcion__id',
                                                                                                 'inscripcion__persona__apellido1',
                                                                                                 'inscripcion__persona__apellido2',
                                                                                                 'inscripcion__persona__nombres').filter(
                            status=True).distinct().order_by('inscripcion__persona__apellido1',
                                                             'inscripcion__persona__apellido2',
                                                             'inscripcion__persona__nombres')

                    listacarreras = inscripciones.values_list('inscripcion__carrera__id').distinct(
                        'inscripcion__carrera__id').order_by('inscripcion__carrera__id')
                    carreras = []
                    if not empezarbuscar:
                        carreras = Carrera.objects.filter(pk__in=listacarreras).distinct()
                    data['carreras'] = carreras
                    data['coordinaciones'] = Coordinacion.objects.filter(carrera__id__in=listacarreras).distinct()
                    data['inscripciones'] = inscripciones
                    data['empezarbuscar'] = empezarbuscar
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewdetallevisita.html", data)
                except Exception as ex:
                    print(ex)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'archivogeneral':
                try:
                    data['title'] = u'Archivos generales'
                    search = None
                    archivogeneral = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            archivogeneral = ArchivoGeneralPracticaPreProfesionales.objects.filter(pk=search,
                                                                                                   status=True)
                        else:
                            if ' ' in search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    archivogeneral = ArchivoGeneralPracticaPreProfesionales.objects.filter(
                                        Q(nombre__icontains=s[0]), Q(status=True))
                                elif len(s) == 2:
                                    archivogeneral = ArchivoGeneralPracticaPreProfesionales.objects.filter(
                                        Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(status=True))
                                elif len(s) == 3:
                                    archivogeneral = ArchivoGeneralPracticaPreProfesionales.objects.filter(
                                        Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(
                                            nombre__icontains=s[2]), Q(status=True))
                            else:
                                archivogeneral = ArchivoGeneralPracticaPreProfesionales.objects.filter(status=True)
                    else:
                        archivogeneral = ArchivoGeneralPracticaPreProfesionales.objects.filter(status=True)
                    paging = MiPaginador(archivogeneral, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['archivogenerales'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewarchivogeneral.html", data)
                except Exception as ex:
                    pass

            elif action == 'addarchivogeneral':
                try:
                    data['title'] = u'Adicionar archivos generales'
                    data['form'] = ArchivoGeneralPracticaPreProfesionalesFrom()
                    return render(request, "alu_practicaspreprofesionalesinscripcion/addarchivogeneral.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarchivogeneral':
                try:
                    data['title'] = u'Editar archivos generales'
                    data['archivogeneral'] = archivogeneral = ArchivoGeneralPracticaPreProfesionales.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['form'] = ArchivoGeneralPracticaPreProfesionalesFrom(
                        initial={'nombre': archivogeneral.nombre, 'visible': archivogeneral.visible,'carrera': archivogeneral.carreras()})
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editarchivogeneral.html", data)
                except Exception as ex:
                    pass

            elif action == 'delarchivogeneral':
                try:
                    data['title'] = u'Eliminar archivos generales'
                    data['archivogeneral'] = ArchivoGeneralPracticaPreProfesionales.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/delarchivogeneral.html", data)
                except Exception as ex:
                    pass

            elif action == 'addconfpreinscripcion':
                try:
                    data['title'] = u'Adicionar configuración de pre-inscripciones'
                    form = PreInscripcionPracticasPPForm(initial={'periodo': periodo})
                    if practicasalud:
                        coordsalud = Coordinacion.objects.filter(id=1)
                        form.fields['coordinacion'].queryset = coordsalud
                        form.fields['coordinacion'].initial = coordsalud
                        form.fields['carrera'].queryset = Carrera.objects.filter(status=True, coordinacion=coordsalud[0])
                        form.fields['subirarchivo'].label = u'Permite subir archivo de prioridad (Estudiante)?'
                        form.fields['actualizararchivo'].label = u'Actualizar archivo prioriodad (Estudiante)?'
                        del form.fields['puede_solicitar']
                        del form.fields['puede_asignar']
                        del form.fields['fechamaximoagendatutoria']
                        del form.fields['agendatutoria']
                    else:
                        del form.fields['inglesaprobado']
                        del form.fields['computacionaprobado']
                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/addconfpreinscripcion.html", data)
                except Exception as ex:
                    print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, ex))
                    pass

            elif action == 'editconfpreinscripcion':
                try:
                    data['title'] = u'Editar configuración de pre-inscripciones'
                    data['conf'] = conf = PreInscripcionPracticasPP.objects.get(status=True,
                                                                                pk=int(encrypt(request.GET['id'])))
                    form = PreInscripcionPracticasPPForm(initial=model_to_dict(conf))
                    if confextra := conf.extrapreinscripcionpracticaspp_set.filter(status=True).first():
                        form.fields['enlinea'].initial = confextra.enlinea
                    form.cargar_carrera(conf)
                    if practicasalud or conf.coordinaciones().first().id == 1:
                        coordsalud = Coordinacion.objects.filter(id=1)
                        form.fields['coordinacion'].queryset = coordsalud
                        form.fields['carrera'].queryset = Carrera.objects.filter(status=True, coordinacion=coordsalud.first())
                        form.fields['subirarchivo'].label = u'Permite subir archivo de prioridad (Estudiante)?'
                        form.fields['actualizararchivo'].label = u'Actualizar archivo prioriodad (Estudiante)?'
                        del form.fields['puede_solicitar']
                        del form.fields['puede_asignar']
                        del form.fields['fechamaximoagendatutoria']
                        del form.fields['agendatutoria']
                    else:
                        del form.fields['inglesaprobado']
                        del form.fields['computacionaprobado']
                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editconfpreinscripcion.html", data)
                except Exception as ex:
                    pass

            if action == 'delconfpreinscripcion':
                try:
                    data['title'] = u'Eliminar configuración de pre-inscripciones'
                    data['conf'] = PreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/delconfpreinscripcion.html", data)
                except Exception as ex:
                    pass

            elif action == 'confpreinscripciones':
                try:
                    # data['title'] = u'Pre-Inscripciones de practicas pre-profesionales' if not practicasalud else u'Pre-Inscripciones de practicas pre-profesionales de Salud'
                    data['title'] = u'Pre-Inscripciones de practicas pre-profesionales'
                    search = None
                    ids = None
                    if 'id' in request.GET:
                        ids = int(encrypt(request.GET['id']))
                        preinscripciones = PreInscripcionPracticasPP.objects.filter(pk=ids, status=True).order_by(
                            '-fechainicio')
                    else:
                        preinscripciones = PreInscripcionPracticasPP.objects.filter(status=True).order_by(
                            '-fechainicio')
                    # if practicasalud:
                    #     preinscripciones = preinscripciones.filter(coordinacion__in=[1])
                    if 's' in request.GET:
                        search = request.GET['s']
                        s = search.split(" ")
                        if len(s) == 1:
                            preinscripciones = preinscripciones.filter(Q(mensaje__icontains=s[0]), Q(status=True))
                        elif len(s) == 2:
                            preinscripciones = preinscripciones.filter(
                                ((Q(mensaje__icontains=s[0]) & Q(mensaje__icontains=s[1]))), Q(status=True))
                        elif len(s) == 3:
                            preinscripciones = preinscripciones.filter(((
                                    Q(mensaje__icontains=s[0]) & Q(mensaje__icontains=s[1]) & Q(
                                mensaje__icontains=s[2]))), Q(status=True))
                    paging = MiPaginador(preinscripciones, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['configuraciones'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "alu_practicaspreprofesionalesinscripcion/confpreinscripcionppp.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpreguntapreinscripcion':
                try:
                    data['title'] = u'Adicionar Pregunta para pre-inscripción'
                    data['form'] = PreguntaPreInscripcionPracticasPPForm()
                    return render(request, "alu_practicaspreprofesionalesinscripcion/addpreguntapreinscripcion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'editpreguntapreinscripcion':
                try:
                    data['title'] = u'Editar Pregunta para pre-inscripción'
                    data['pre'] = pre = PreguntaPreInscripcionPracticasPP.objects.get(
                        id=int(encrypt(request.GET['id'])))
                    data['form'] = PreguntaPreInscripcionPracticasPPForm(
                        initial={'descripcion': pre.descripcion, 'activo': pre.activo})
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editpreguntapreinscripcion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'delpreguntapreinscripcion':
                try:
                    data['title'] = u'Eliminar pregunta para pre-inscripción'
                    data['pre'] = PreguntaPreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/delpreguntapreinscripcion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'preguntaspreinscripcion':
                try:
                    data['title'] = u'Preguntas para Pre-Inscripciones de practicas pre-profesionales'
                    search = None
                    ids = None
                    if 'id' in request.GET:
                        ids = int(encrypt(request.GET['id']))
                        preguntas = PreguntaPreInscripcionPracticasPP.objects.filter(pk=ids, status=True)
                    else:
                        preguntas = PreguntaPreInscripcionPracticasPP.objects.filter(status=True).order_by(
                            'descripcion')
                    if 's' in request.GET:
                        search = request.GET['s']
                        s = search.split(" ")
                        if len(s) == 1:
                            preguntas = preguntas.filter(Q(descripcion__icontains=s[0]), Q(status=True))
                        elif len(s) == 2:
                            preguntas = preguntas.filter(
                                ((Q(descripcion__icontains=s[0]) & Q(descripcion__icontains=s[1]))), Q(status=True))
                        elif len(s) == 3:
                            preguntas = preguntas.filter(((
                                    Q(descripcion__icontains=s[0]) & Q(descripcion__icontains=s[1]) & Q(
                                descripcion__icontains=s[2]))), Q(status=True))
                    paging = MiPaginador(preguntas, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['preguntas'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "alu_practicaspreprofesionalesinscripcion/preguntas.html", data)
                except Exception as ex:
                    pass

            elif action == 'listapreinscritos':
                try:
                    data['title'] = u'Listado de estudiantes Pre-Inscritos'
                    search = None
                    ids = None
                    idest = 0
                    idcar = 0
                    idfac = 0
                    facu = []
                    docu = None
                    data['preinscripcion'] = preinscripcion = PreInscripcionPracticasPP.objects.get(status=True, pk=int(
                        encrypt(request.GET['id'])))
                    carreras = []
                    if preinscripcion.carreras():
                        carreras = preinscripcion.carreras().values_list('id', 'nombre', flat=False)
                    else:
                        if preinscripcion.coordinaciones():
                            carreras = Carrera.objects.values_list('id', 'nombre', flat=False).filter(coordinacion__id__in=preinscripcion.coordinaciones().values_list('id', flat=False))
                            facu = preinscripcion.coordinaciones().values_list('id', 'nombre', flat=False)
                    data['carreras'] = carreras
                    data['facultad'] = facu
                    preinscripciones = preinscripcion.detallepreinscripcionpracticaspp_set.filter(status=True).order_by(
                        'inscripcion__persona__nombres', 'inscripcion__persona__apellido1')
                    # for pr in preinscripciones:
                    #     pr.recorrido1(request)
                    if 'idfac' in request.GET:
                        idfac=int(request.GET['idfac'])
                        if idfac > 0:
                            preinscripciones = preinscripciones.filter(inscripcion__coordinacion__id=idfac)
                            data['carreras']= carreras = preinscripcion.carreras().filter(coordinacion__id=idfac).values_list('id', 'nombre', flat=False)
                    if 'idest' in request.GET:
                        idest = int(request.GET['idest'])
                        if idest > 0 and idest < 7:
                            preinscripciones = preinscripciones.filter(estado=idest)
                        if idest == 9:
                            preinscripciones = preinscripciones.filter(estado=idest)
                        if idest == 7:
                            lista_solicitantes = DatosEmpresaPreInscripcionPracticasPP.objects.filter(status=True, preinscripcion__in=preinscripciones.values_list('pk', flat=True))
                            preinscripciones = preinscripciones.filter(
                                pk__in=lista_solicitantes.values_list('preinscripcion__pk', flat=True))
                        if idest == 8:
                            lista_solicitantes = SolicitudVinculacionPreInscripcionPracticasPP.objects.filter(status=True, preinscripcion__in=preinscripciones.values_list('pk', flat=True))
                            preinscripciones = preinscripciones.filter(pk__in=lista_solicitantes.values_list('preinscripcion__pk', flat=True))
                    if 'idcar' in request.GET:
                        idcar = int(request.GET['idcar'])
                        if idcar > 0:
                            preinscripciones = preinscripciones.filter(inscripcion__carrera__id=idcar)
                            data['facultad']=facu = preinscripcion.coordinaciones().filter(carrera__id__in=[idcar]).values_list('id', 'nombre', flat=False)
                    if 'docu' in request.GET:
                        data['docu'] = docu = request.GET['docu']
                        if docu == '1':
                            preinscripciones = preinscripciones.exclude(archivo='')
                        elif docu == '2':
                            preinscripciones = preinscripciones.filter(archivo='')
                    if 's' in request.GET:
                        search = request.GET['s']
                        s = search.split(" ")
                        if len(s) == 1:
                            preinscripciones = preinscripciones.filter(
                                Q(inscripcion__persona__nombres__icontains=search) | Q(
                                    inscripcion__persona__apellido1__icontains=search) | Q(
                                    inscripcion__persona__cedula__icontains=search) | Q(
                                    inscripcion__persona__apellido2__icontains=search))
                        elif len(s) == 2:
                            preinscripciones = preinscripciones.filter(
                                (Q(inscripcion__persona__nombres__icontains=s[0]) & Q(
                                    inscripcion__persona__nombres__icontains=s[1])) |
                                (Q(inscripcion__persona__apellido1__icontains=s[0]) & Q(
                                    inscripcion__persona__apellido2__icontains=s[1]))
                            )
                    # DATAREPORTES
                    data['listado_practicas'] = listado_practicas_query = PracticasPreprofesionalesInscripcion.objects.filter(status=True, preinscripcion__in=preinscripciones.values_list('id', flat=True))
                    meses_totales = listado_practicas_query.annotate(month=ExtractMonth('fecha_creacion'), year=ExtractYear('fecha_creacion')).values('month', 'year').annotate(count=Count('month')).values('month', 'year', 'count').order_by('year', 'month')
                    listado_practicas = list(listado_practicas_query.distinct().order_by('fecha_creacion').values_list('fecha_creacion', flat=True))
                    data['totalconpracticas'] = listado_practicas_query.count()
                    data['meses_totales'] = meses_totales
                    data['totalpreinscritos'] = preinscripciones.count()
                    data['ins_solicitados'] = preinscripciones.filter(estado=1).count()
                    data['ins_asignados'] = preinscripciones.filter(estado=2).count()
                    data['ins_rechazados'] = preinscripciones.filter(estado=3).count()
                    data['ins_pendiente'] = preinscripciones.filter(estado=4).count()
                    data['ins_aceptados'] = preinscripciones.filter(estado=5).count()
                    data['insinscritoscount0'] = Inscripcion.objects.values('id').filter(status=True, id__in=preinscripciones.values_list('inscripcion__id', flat=True)).count()
                    data['porcarreras'] = preinscripciones.values('inscripcion__carrera__nombre').annotate(total=Count('inscripcion__carrera__nombre')).values('inscripcion__carrera__nombre', 'inscripcion__carrera__id', 'total').order_by('inscripcion__carrera__nombre')
                    # DATAREPORTES
                    paging = MiPaginador(preinscripciones.order_by('fechaarchivo'), 15)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['preinscripciones'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['idest'] = idest
                    data['idcar'] = idcar
                    data['idfac'] = idfac
                    data['estados'] = ESTADO_PREINSCRIPCIONPPP
                    data['cant_inscritos_busqueda'] = preinscripciones.values('id').count()
                    data['inssolicitudcount'] = preinscripciones.exclude(archivo='').count()
                    data['inspendsolicitudcount'] = preinscripciones.filter(archivo='').count()
                    data['cant_llamadas__pendientes'] = preinscripciones.filter(accion=1).count()
                    data['cant_llamadas_contestadas'] = preinscripciones.filter(accion=2).count()
                    data['cant_llamadas__no_contestadas'] = preinscripciones.filter(accion=3).count()
                    data['cant_llamadas_no_interesados'] = preinscripciones.filter(accion=4).count()
                    data['cant_llamadas_confirmar_participacion'] = preinscripciones.filter(accion=5).count()
                    data['DEBUG'] = DEBUG
                    return render(request, "alu_practicaspreprofesionalesinscripcion/listapreinscripciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'verobservaciones':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = DetallePreInscripcionPracticasPP.objects.get(pk=request.GET['id'])
                    data['detalle'] = detalle = filtro.seguimientopreprofesionalesinscripcion_set.filter(status=True).order_by('pk')
                    template = get_template("alu_practicaspreprofesionalesinscripcion/modal/detalleobs.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addobservacion':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = DetallePreInscripcionPracticasPP.objects.get(pk=request.GET['id'])
                    data['detalle'] = detalle = filtro.seguimientopreprofesionalesinscripcion_set.filter(status=True).order_by('pk')
                    form = SeguimientoPreProfesionalInscripcionForm()
                    HISTORIAL_CHOICES_OBSER = (
                        (2, "EL ESTUDIANTE CONTESTÓ"),
                        (3, "EL ESTUDIANTE NO CONTESTÓ"),
                        (4, "EL ESTUDIANTE NO ESTÁ INTERESADO"),
                        (5, "EL ESTUDIANTE CONFIRMO SU PARTICIPACIÓN"),
                    )
                    form.fields['accion'].choices = HISTORIAL_CHOICES_OBSER
                    data['form2'] = form
                    template = get_template("alu_practicaspreprofesionalesinscripcion/modal/formobservacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'excelseguimiento':
                try:
                    fecha_actual = datetime.now().date()
                    filtro = Q(status=True)
                    id = request.GET.get('id')
                    desde = request.GET.get('desde')
                    hasta = request.GET.get('hasta')

                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = easyxf(
                        'font: name Calibri, color-index black, bold on, height 200; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style.font.bold = True
                    font_style2 = easyxf(
                        'font: name Calibri, color-index black, height 200; borders: left thin, right thin, top thin, bottom thin')
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('SeguimientoLlamadasEstudiantes')
                    ws.write_merge(0, 0, 0, 10,
                                   'REPORTE DE SEGUIMIENTO DE LLAMADAS A ESTUDIANTES PREINSCRITOS EN PRÁCTICAS PREPROFESIONALES DESDE {} HASTA {}'.format(
                                       desde, hasta), title)
                    font_style.font.bold = True

                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=listado_seguimiento_llamadas' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"ESTUDIANTE", 10000),
                        (u"CEDULA", 5000),
                        (u"TELEFONO", 5000),
                        (u"CORREO", 10000),
                        (u"CARRERA", 25000),
                        (u"NIVEL", 5000),
                        (u"ITINERARIO", 10000),
                        (u"FECHA LLAMADA", 4500),
                        (u"HORA LLAMADA", 4500),
                        (u"OSERVACIÓN", 25000),
                        (u"ESTADO", 25000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listado = SeguimientoPreProfesionalesInscripcion.objects.filter(cab__preinscripcion__id=id,
                                                                                    fecha_creacion__range=[desde,
                                                                                                           hasta]).order_by(
                        'fecha_creacion')
                    row_num = 4
                    i = 0
                    for lista in listado:
                        campo1 = lista.cab.inscripcion.persona.__str__()
                        campo2 = lista.cab.inscripcion.persona.cedula
                        campo3 = lista.cab.inscripcion.persona.telefono
                        campo4 = lista.cab.inscripcion.persona.emailinst
                        campo5 = lista.cab.inscripcion.carrera.nombre if lista.cab.inscripcion.carrera else 'SIN CARRERA'
                        campo6 = lista.cab.nivelmalla.nombre if lista.cab.nivelmalla else 'SIN NIVEL'
                        campo7 = lista.cab.itinerariomalla.nombre if lista.cab.itinerariomalla else 'No tiene Itinerario'
                        campo8 = lista.fecha_llamada.strftime('%d-%m-%Y')
                        campo9 = lista.hora_llamada.strftime('%H:%M:%S')
                        campo10 = lista.detalle
                        campo11 = lista.get_accion()

                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8, font_style2)
                        ws.write(row_num, 8, campo9, font_style2)
                        ws.write(row_num, 9, campo10, font_style2)
                        ws.write(row_num, 10, campo11, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'addanilladoobservacion':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = PracticasPreprofesionalesInscripcion.objects.get(pk=request.GET['id'])
                    data['detalle'] = detalle = filtro.anilladopracticaspreprofesionalesinscripcion_set.filter(
                        status=True).order_by('pk')
                    form = AnilladoPreProfesionalInscripcionForm()
                    HISTORIAL_CHOICES_OBSER = (
                        (2, "ANILLADO RECIBIDO"),
                        (3, "ANILLADO ENTREGADO PARA MODIFICACIÓN"),
                    )
                    form.fields['accion'].choices = HISTORIAL_CHOICES_OBSER
                    data['form2'] = form
                    template = get_template(
                        "alu_practicaspreprofesionalesinscripcion/modal/formanilladoobservacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'veranilladoobservaciones':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = PracticasPreprofesionalesInscripcion.objects.get(pk=request.GET['id'])
                    data['detalle'] = detalle = filtro.anilladopracticaspreprofesionalesinscripcion_set.filter(
                        status=True).order_by('pk')
                    template = get_template("alu_practicaspreprofesionalesinscripcion/modal/detalleanilladodobs.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'missolicitudesempresa':
                try:
                    data['filtro'] = filtro = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    template = get_template(
                        "alu_practicaspreprofesionalesinscripcion/modal/missolicitudesempresas.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'adddetallepreinscripcion':
                try:
                    data['title'] = u'Adicionar Pre Inscripción'
                    data['preinscripcion'] = pre = PreInscripcionPracticasPP.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    form = DetallePreInscripcionPracticasPPForm()
                    data['form'] = form
                    data['preguntas'] = pre.preguntas()
                    return render(request, "alu_practicaspreprofesionalesinscripcion/adddetallepreinscripcion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'delpreinscripcion':
                try:
                    data['title'] = u'Eliminar pre-inscripción de Práctica Pre-Profesional'
                    data['pre'] = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/delpreinscripcion.html", data)
                except Exception as ex:
                    pass

            elif action == 'itinerariosmalla':
                try:
                    inscripcion = Inscripcion.objects.get(pk=int(request.GET['idinscripcion']))
                    facultadid = inscripcion.coordinacion.id
                    nivelid = inscripcion.mi_nivel().nivel.id
                    carrera_id = request.GET['carrera_id']
                    orden_nivel = request.GET['orden_nivel']
                    itinerariosvalidosid = []

                    for it in inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.filter(status=True):
                        nivelhasta = it.nivel.orden
                        if inscripcion.todas_materias_aprobadas_rango_nivel(1, nivelhasta):
                            itinerariosvalidosid.append(it.pk)

                    # itinerarios = list(ItinerariosMalla.objects.filter(status=True, malla__carrera_id=carrera_id,
                    #                                                    nivel__orden__lte=orden_nivel).values('id',
                    #                                                                                          'nombre',
                    #                                                                                          'horas_practicas',
                    #                                                                                          'nivel__nombre'))

                    itinerarios = list(ItinerariosMalla.objects.filter(status=True, pk__in=itinerariosvalidosid).values('id',
                                                                                                             'nombre',
                                                                                                             'horas_practicas',
                                                                                                             'nivel__nombre'))
                    return JsonResponse(
                        {"result": "ok", 'data': itinerarios, 'nivelid': nivelid, 'facultadid': facultadid})
                except Exception as ex:
                    pass

            elif action == 'itinerariosmallanivel':
                try:
                    id_carrera = request.GET['id_carrera']
                    id_nivel = request.GET['id_nivel']
                    itinerarios = list([])
                    if Carrera.objects.filter(id=id_carrera).exists() and NivelMalla.objects.filter(
                            id=id_nivel).exists():
                        nivel = NivelMalla.objects.get(id=id_nivel)
                        itinerarios = list(ItinerariosMalla.objects.filter(malla__carrera_id=id_carrera,
                                                                           nivel__orden__lte=nivel.orden).values('id',
                                                                                                                 'nombre',
                                                                                                                 'horas_practicas',
                                                                                                                 'nivel__nombre'))
                    return JsonResponse({"result": "ok", 'data': itinerarios})
                except Exception as ex:
                    pass

            elif action == 'itinerariosmallanivel':
                try:
                    id_carrera = request.GET['id_carrera']
                    id_nivel = request.GET['id_nivel']
                    itinerarios = list([])
                    if Carrera.objects.filter(id=id_carrera).exists() and NivelMalla.objects.filter(
                            id=id_nivel).exists():
                        nivel = NivelMalla.objects.get(id=id_nivel)
                        itinerarios = list(ItinerariosMalla.objects.filter(malla__carrera_id=id_carrera,
                                                                           nivel__orden__lte=nivel.orden).values('id',
                                                                                                                 'nombre',
                                                                                                                 'horas_practicas',
                                                                                                                 'nivel__nombre'))
                    return JsonResponse({"result": "ok", 'data': itinerarios})
                except Exception as ex:
                    pass

            elif action == 'gestionar_preins_ind':
                try:
                    data['title'] = u'Gestionar practicas preprofesionales'
                    data['preinscripcion'] = pre = DetallePreInscripcionPracticasPP.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = PracticasPreprofesionalesInscripcionForm(initial={'inscripcion': pre.inscripcion.id,
                                                                             'nivelmalla': pre.nivelmalla,
                                                                             'itinerario': pre.itinerariomalla if pre.itinerariomalla else None,
                                                                             'numerohora': pre.itinerariomalla.horas_practicas if pre.itinerariomalla else None, })
                    form.fields['itinerario'].queryset = ItinerariosMalla.objects.filter(status=True, malla__carrera=pre.inscripcion.carrera).order_by('pk')
                    form.vaciartutorunemi()
                    form.gestionar_prein_ind(pre)
                    form.tiene_itinerario(pre)
                    form.cargar_estado()
                    form.cargar_tipo()
                    data['carrerains'] = carrerains = pre.inscripcion.carrera
                    form.fields['periodoevidencia'].queryset = CabPeriodoEvidenciaPPP.objects.filter(status=True)
                    form.fields['provinciapractica'].queryset = Provincia.objects.none()
                    form.fields['lugarpractica'].queryset = Canton.objects.none()
                    # form.eliminarempresaempleadora()
                    if pre.itinerariomalla:
                        data['numhora'] = pre.itinerariomalla if pre.itinerariomalla else None
                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/gestionar_preins_ind.html", data)
                except Exception as ex:
                    pass

            elif action == 'gestionar_preins_masivo':
                try:
                    data['title'] = u'Inscripción Masiva Practicas Preprofesionales'
                    data['preinscripcion'] = pre = PreInscripcionPracticasPP.objects.get(pk=int(encrypt(request.GET['id'])))
                    qscarreras = DetallePreInscripcionPracticasPP.objects.values('inscripcion').filter(status=True, preinscripcion=pre).values_list('inscripcion__carrera__id', flat=True).distinct()
                    form = PracticasPreprofesionalesInscripcionMasivoEstudianteForm()
                    form.fields['carrera'].queryset = Carrera.objects.filter(status=True, id__in=qscarreras).order_by('nombre')
                    form.fields['inscripciones'].queryset = DetallePreInscripcionPracticasPP.objects.none()
                    form.fields['tutorunemi'].queryset = Profesor.objects.none()
                    form.fields['convenio'].queryset = ConvenioEmpresa.objects.filter(status=True, fechafinalizacion__gte=datetime.now().date()).order_by('fechafinalizacion')
                    form.fields['acuerdo'].queryset = AcuerdoCompromiso.objects.filter(status=True, fechafinalizacion__gte=datetime.now().date()).order_by('fechafinalizacion')
                    form.fields['paispractica'].queryset = Pais.objects.filter(status=True, provincia__isnull=False).distinct().order_by('nombre')
                    form.fields['provinciapractica'].queryset = Provincia.objects.none()
                    form.fields['lugarpractica'].queryset = Canton.objects.none()
                    form.fields['itinerario'].queryset = ItinerariosMalla.objects.none()
                    # form.fields['itinerario'].queryset = ItinerariosMalla.objects.filter(status=True, malla__carrera__in=qscarreras.values_list('id', flat=True)).order_by('pk')
                    form.vaciartutorunemi()
                    form.cargar_estado()
                    form.cargar_tipo()
                    # data['carrerains'] = carrerains = pre.inscripcion.carrera
                    form.fields['periodoevidencia'].queryset = CabPeriodoEvidenciaPPP.objects.filter(status=True)
                    # form.eliminarempresaempleadora()
                    # if pre.itinerariomalla:
                    #     data['numhora'] = pre.itinerariomalla if pre.itinerariomalla else None
                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/gestionar_preins_masivo.html", data)
                except Exception as ex:
                    pass

            if action == 'buscaritinerario':
                try:
                    idcar = request.GET['idcar']
                    # idnivel = request.GET['idnivel']
                    qsbase = ItinerariosMalla.objects.filter(status=True, malla__carrera__id=idcar)
                    if 'search' in request.GET:
                        qsbase = qsbase.filter(nombre__icontains=request.GET['search'])
                    resp = [{'id': cr.pk, 'text': cr.__str__()} for cr in qsbase.order_by('nombre')]
                    return HttpResponse(json.dumps({'state': True, 'result': resp}))
                except Exception as ex:
                    pass

            if action == 'buscarestudiantes':
                try:
                    iditinerario = request.GET['itinerario']
                    idperiodopractica = request.GET['idperiodopractica']
                    periodopractica = PreInscripcionPracticasPP.objects.get(id=idperiodopractica)
                    itinerario = ItinerariosMalla.objects.get(id=iditinerario)
                    qsbase = periodopractica.detallepreinscripcionpracticaspp_set.filter(status=True, estado__in=[1,3,4], itinerariomalla=itinerario)
                    if 'search' in request.GET:
                        search = request.GET['search']
                        s = search.split(" ")
                        if len(s) == 1:
                            qsbase = qsbase.filter(
                                Q(inscripcion__persona__nombres__icontains=search) | Q(
                                    inscripcion__persona__apellido1__icontains=search) | Q(
                                    inscripcion__persona__cedula__icontains=search) | Q(
                                    inscripcion__persona__apellido2__icontains=search))
                        elif len(s) == 2:
                            qsbase = qsbase.filter(
                                (Q(inscripcion__persona__nombres__icontains=s[0]) & Q(
                                    inscripcion__persona__nombres__icontains=s[1])) |
                                (Q(inscripcion__persona__apellido1__icontains=s[0]) & Q(
                                    inscripcion__persona__apellido2__icontains=s[1]))
                            )
                    resp = [{'id': cr.pk, 'text': f'{cr.get_estado_display()}: {cr.inscripcion.persona.cedula} {cr.inscripcion.__str__()} | {cr.nivelmatriculamalla()} | {str(cr.fecha_creacion.date())}'} for cr in qsbase.order_by('inscripcion__persona__nombres', 'inscripcion__persona__apellido1')]
                    return HttpResponse(json.dumps({'state': True, 'result': resp}))
                except Exception as ex:
                    pass

            elif action == 'consultatotalinformes':
                mes = int(request.GET['mesinforme'])
                anio = int(request.GET['anio'])
                informes = InformeMensualDocentesPPP.objects.filter(status=True, mes=mes, anio=anio)
                response = JsonResponse({'state': True, 'totinformes': informes.count(), })
                return HttpResponse(response.content)

            elif action == 'viewinformemensual':
                try:
                    docente_id = int(request.GET['docente'])
                    carrera_id = int(request.GET['carrera'])
                    data['profe'] = profe = Profesor.objects.get(pk=docente_id)
                    data['carr'] = carr = Carrera.objects.get(pk=carrera_id)
                    data['listado'] = listado = InformeMensualDocentesPPP.objects.filter(status=True,
                                                                                         persona_id=docente_id,
                                                                                         carrera_id=carrera_id).order_by(
                        '-fechageneracion')
                    data['liscount'] = listado.count()
                    template = get_template("alu_practicaspreprofesionalesinscripcion/informesmensualesdocentes.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verinscritos':
                try:
                    actividad = int(request.GET['actividad'])
                    data['actividad'] = actividad = ActividadDetalleDistributivoCarrera.objects.get(pk=actividad)
                    data['listado'] = listado = actividad.tutoriasdocentes_inscrito()
                    data['liscount'] = listado.count()
                    template = get_template("alu_practicaspreprofesionalesinscripcion/listadoinscritosactividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verinscritossupervisor':
                try:
                    supervisor = int(request.GET['supervisor_id'])
                    carrera = int(request.GET['carrera_id'])
                    data['listado'] = listado = PracticasPreprofesionalesInscripcion.objects.filter(
                        supervisor__id=supervisor,
                        inscripcion__carrera_id=carrera,
                        preinscripcion__preinscripcion__periodo=periodo
                    )
                    data['liscount'] = listado.count()
                    template = get_template("alu_practicaspreprofesionalesinscripcion/listadoinscritossupervisor.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'veragenda':
                try:
                    actividad = int(request.GET['actividad'])
                    data['actividad'] = actividad = ActividadDetalleDistributivoCarrera.objects.get(pk=actividad)
                    data['docente'] = profesor = actividad.actividaddetalle.criterio.distributivo.profesor
                    baseestudiantes = PracticasPreprofesionalesInscripcion.objects.select_related('tutorunemi').filter(status=True, inscripcion__carrera=actividad.carrera, tutorunemi=profesor, culminada=False,
                                                                                                                       preinscripcion__preinscripcion__periodo=periodo).distinct().exclude(estadosolicitud=3).order_by(
                        '-fecha_creacion').distinct()
                    data['totalestudiantesasignados'] = baseestudiantes.count()
                    baseperiodoagendaestudiantes = EstudiantesAgendaPracticasTutoria.objects.filter(status=True,
                                                                                                    cab__status=True,
                                                                                                    estudiante__in=baseestudiantes.values_list(
                                                                                                        'pk',
                                                                                                        flat=True))
                    baseperiodoagenda = AgendaPracticasTutoria.objects.filter(
                        pk__in=baseperiodoagendaestudiantes.values_list('cab__id', flat=True))
                    data['totalestudiantesconagendames'] = baseestudiantes.filter(
                        pk__in=baseperiodoagendaestudiantes.values_list('estudiante__id', flat=True)).count()
                    data['totalagendaperiodo'] = baseperiodoagenda.count()
                    data['listado'] = baseperiodoagenda
                    listacab = baseperiodoagenda.distinct('fecha').values_list('fecha', flat=True)
                    listfechas = list(listacab)
                    data['meses'] = MESES_CHOICES
                    data['anios'] = list_anios = sorted(set([l2[0] for l2 in [str(l).split('-') for l in listfechas]]))
                    data['mesesincab'] = list_meses = sorted(
                        set([int(l2[1]) for l2 in [str(l).split('-') for l in listfechas]]))
                    template = get_template("alu_practicaspreprofesionalesinscripcion/listadoagendadocente.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'veragendaconvocados':
                try:
                    data['id'] = id = int(request.GET['id'])
                    data['instancia'] = instancia = AgendaPracticasTutoria.objects.get(pk=id)
                    template = get_template("alu_practicaspreprofesionalesinscripcion/modal/verconvocados.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'viewdocentes':

                data['title'] = u'Gestionar Docentes por periodo'
                search, carreras, filtros, url_vars = request.GET.get('search', ''), request.GET.get('carreras', ''), Q(
                    status=True), ''
                qsfiltro = ActividadDetalleDistributivoCarrera.objects.filter(
                    actividaddetalle__criterio__criteriodocenciaperiodo__criterio__id__in=[6, 154, 144],
                    actividaddetalle__criterio__distributivo__periodo=periodo,
                    actividaddetalle__criterio__distributivo__status=True, status=True)
                idscarreras = qsfiltro.values_list('carrera__id', flat=True).distinct('carrera')
                data['lista_carreras'] = Carrera.objects.filter(pk__in=idscarreras).order_by('nombre')
                if carreras:
                    data['carreras'] = int(carreras)
                    filtros = filtros & (Q(carrera_id=carreras))
                    url_vars += '&carreras={}'.format(carreras)
                if search:
                    data['search'] = search
                    s = search.split()
                    if len(s) == 1:
                        filtros = filtros & (
                                Q(actividaddetalle__criterio__distributivo__profesor__persona__apellido2__icontains=search) | Q(
                            actividaddetalle__criterio__distributivo__profesor__persona__cedula__icontains=search) | Q(
                            actividaddetalle__criterio__distributivo__profesor__persona__apellido1__icontains=search))
                    else:
                        filtros = filtros & (
                                Q(actividaddetalle__criterio__distributivo__profesor__persona__apellido1__icontains=
                                  s[0]) & Q(
                            actividaddetalle__criterio__distributivo__profesor__persona__apellido2__icontains=s[1]))
                    url_vars += '&search={}'.format(search)
                qsfiltro = qsfiltro.filter(filtros).order_by(
                    'actividaddetalle__criterio__distributivo__profesor__persona__apellido1')
                url_vars += '&action={}'.format(action)
                data["url_vars"] = url_vars
                data['listcount'] = qsfiltro.count()
                data['meses'] = MESES_CHOICES
                paging = MiPaginador(qsfiltro, 15)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                    else:
                        p = paginasesion
                    try:
                        page = paging.page(p)
                    except:
                        p = 1
                    page = paging.page(p)
                except:
                    page = paging.page(p)
                request.session['paginador'] = p
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['lista'] = page.object_list

                if 'export_to_excel_docentes_inscritos' in request.GET:
                    __author__ = 'Unemi'

                    title = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')

                    fuentecabecera = easyxf(
                        'font: name Calibri, color-index black, bold on, height 200; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Calibri, color-index black, height 200; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('SeguimientoDocentes')
                    ws.write_merge(0, 0, 0, 10, 'CONTROL DE PRÁCTICAS PRE-PROFESIONALES  DE DOCENTES', title)

                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=listado_docentes_inscritos' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"FECHA", 5000),
                        (u"HORA", 5000),
                        (u"DOCENTE", 10000),
                        (u"CEDULA ", 5000),
                        (u"CORREO ", 8000),
                        (u"TELEFONO ", 5000),
                        (u"CARRERA", 10000),
                        (u"HORAS DISTRIBUTIVO", 8000),
                        (u"ALUMNOS POR HORAS", 8000),
                        (u"MÁXIMO VINCULAR", 4500),
                        (u"CUPOS DISPONIBLES", 4500),
                        (u"TOTAL ASIGNADOS", 4500),
                        (u"TOTAL EN CURSO", 4500),
                        (u"TOTAL TUTORIAS FINALIZADAS", 10000),
                        (u"¿DISPONIBILIDAD?", 13000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listado = qsfiltro
                    row_num = 4
                    i = 0
                    for lista in listado:
                        campo1 = lista.actividaddetalle.criterio.distributivo.profesor.persona.nombre_completo()
                        campo2 = lista.actividaddetalle.criterio.distributivo.profesor.persona.cedula
                        campo3 = lista.actividaddetalle.criterio.distributivo.profesor.persona.emailinst
                        campo4 = lista.actividaddetalle.criterio.distributivo.profesor.persona.telefono
                        campo5 = lista.carrera.nombre if lista.carrera else 'SIN CARRERA'
                        campo6 = lista.horas
                        campo7 = lista.alumnosxhoras
                        campo8 = lista.total_alumnos_x_hora()
                        campo9 = lista.get_disponbile()
                        campo10 = lista.tutoriasdocentes_count()
                        campo11 = lista.tutoriasdocentes__aprobadas_count()
                        campo12 = lista.tutoriasdocentes__finalizadas_count()
                        campo13 = lista.get_estado_disponibilidad_txt()
                        ws.write(row_num, 0, str(lista.fecha_creacion.date()), fuentenormal)
                        ws.write(row_num, 1, str(lista.fecha_creacion.time()), fuentenormal)
                        ws.write(row_num, 2, campo1, fuentenormal)
                        ws.write(row_num, 3, campo2, fuentenormal)
                        ws.write(row_num, 4, campo3, fuentenormal)
                        ws.write(row_num, 5, campo4, fuentenormal)
                        ws.write(row_num, 6, campo5, fuentenormal)
                        ws.write(row_num, 7, campo6, fuentenormal)
                        ws.write(row_num, 8, campo7, fuentenormal)
                        ws.write(row_num, 9, campo8, fuentenormal)
                        ws.write(row_num, 10, campo9, fuentenormal)
                        ws.write(row_num, 11, campo10, fuentenormal)
                        ws.write(row_num, 12, campo11, fuentenormal)
                        ws.write(row_num, 13, campo12, fuentenormal)
                        ws.write(row_num, 14, campo13, fuentenormal)
                        row_num += 1
                    wb.save(response)
                    return response
                return render(request, "alu_practicaspreprofesionalesinscripcion/viewdocentes.html", data)

            elif action == 'viewdocentessincarrera':
                try:
                    data['title'] = u'Gestionar Docentes sin Carrera por periodo'
                    search, carreras, filtros, url_vars = request.GET.get('search', ''), request.GET.get('carreras',
                                                                                                         ''), Q(
                        status=True), ''
                    qsfiltroconcarreras = ActividadDetalleDistributivoCarrera.objects.select_related(
                        'actividaddetalle').filter(actividaddetalle__criterio__criteriodocenciaperiodo__criterio__id__in=[6, 154],
                                                   actividaddetalle__criterio__distributivo__periodo=periodo,
                                                   actividaddetalle__criterio__distributivo__status=True, status=True)
                    idsexcluir = qsfiltroconcarreras.values_list('actividaddetalle__criterio__pk', flat=True)
                    qsfiltro = DetalleDistributivo.objects.select_related().filter(
                        criteriodocenciaperiodo__criterio__id__in=[6, 154], distributivo__periodo=periodo,
                        distributivo__status=True, status=True).exclude(pk__in=idsexcluir)
                    idscarreras = qsfiltro.values_list('distributivo__carrera__id', flat=True)
                    data['lista_carreras'] = Carrera.objects.filter(pk__in=idscarreras).order_by('nombre')
                    if carreras:
                        data['carreras'] = int(carreras)
                        filtros = filtros & (Q(distributivo__carrera_id=carreras))
                        url_vars += '&carreras={}'.format(carreras)
                    if search:
                        data['search'] = search
                        s = search.split()
                        if len(s) == 1:
                            filtros = filtros & (Q(distributivo__profesor__persona__apellido2__icontains=search) | Q(distributivo__profesor__persona__cedula__icontains=search) | Q(distributivo__profesor__persona__apellido1__icontains=search))
                        else:
                            filtros = filtros & (Q(distributivo__profesor__persona__apellido1__icontains=s[0]) & Q(distributivo__profesor__persona__apellido2__icontains=s[1]))
                        url_vars += '&search={}'.format(search)
                    qsfiltro = qsfiltro.filter(filtros).order_by('distributivo__profesor__persona__apellido1')
                    url_vars += '&action={}'.format(action)
                    data["url_vars"] = url_vars
                    data['listcount'] = qsfiltro.count()
                    data['meses'] = MESES_CHOICES
                    paging = MiPaginador(qsfiltro, 15)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['lista'] = page.object_list
                    if 'export_to_excel_docentes_sin_carreras' in request.GET:
                        __author__ = 'Unemi'

                        title = easyxf(
                            'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')

                        fuentecabecera = easyxf(
                            'font: name Calibri, color-index black, bold on, height 200; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                        fuentenormal = easyxf(
                            'font: name Calibri, color-index black, height 200; borders: left thin, right thin, top thin, bottom thin')
                        font_style = XFStyle()
                        font_style.font.bold = True
                        font_style2 = XFStyle()
                        font_style2.font.bold = False
                        wb = Workbook(encoding='utf-8')
                        ws = wb.add_sheet('SeguimientoDocentes')
                        ws.write_merge(0, 0, 0, 10, 'DOCENTES SIN CARRERA', title)
                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename=listado_docentes_inscritos' + random.randint(1, 10000).__str__() + '.xls'
                        columns = [
                            (u"DOCENTE", 10000),
                            (u"CEDULA ", 5000),
                            (u"CORREO ", 8000),
                            (u"TELEFONO ", 5000),
                            (u"FACULTAD", 10000),
                            (u"CRITERIO", 10000),
                            (u"HORAS", 8000),
                        ]
                        row_num = 3
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                            ws.col(col_num).width = columns[col_num][1]
                        date_format = xlwt.XFStyle()
                        date_format.num_format_str = 'yyyy/mm/dd'
                        listado = qsfiltro
                        row_num = 4
                        i = 0
                        for lista in listado:
                            campo1 = lista.distributivo.profesor.persona.nombre_completo()
                            campo2 = lista.distributivo.profesor.persona.cedula
                            campo3 = lista.distributivo.profesor.persona.emailinst
                            campo4 = lista.distributivo.profesor.persona.telefono
                            campo5 = lista.distributivo.coordinacion.nombre if lista.distributivo.coordinacion else 'SIN FACULTAD'
                            campo6 = lista.criteriodocenciaperiodo.criterio.nombre if lista.criteriodocenciaperiodo.criterio else 'SIN CRITERIO'
                            campo7 = lista.horas
                            ws.write(row_num, 0, campo1, fuentenormal)
                            ws.write(row_num, 1, campo2, fuentenormal)
                            ws.write(row_num, 2, campo3, fuentenormal)
                            ws.write(row_num, 3, campo4, fuentenormal)
                            ws.write(row_num, 4, campo5, fuentenormal)
                            ws.write(row_num, 5, campo6, fuentenormal)
                            ws.write(row_num, 6, campo7, fuentenormal)
                            row_num += 1
                        wb.save(response)
                        return response
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewdocentessincarrera.html", data)
                except Exception as ex:
                    pass

            elif action == 'additinerariodocente':
                try:
                    data['filtro'] = filtro = ActividadDetalleDistributivoCarrera.objects.get(pk=int(request.GET['id']))
                    listaitinerarios = ItinerariosActividadDetalleDistributivoCarrera.objects.filter(status=True, actividad=filtro)
                    form = ItinerarioMallaDocenteDistributivoForm(initial={'itinerario': listaitinerarios.values_list('itinerario__id', flat=True)})
                    form.fields['itinerario'].queryset = ItinerariosMalla.objects.filter(status=True, malla__carrera=filtro.carrera).distinct()
                    data['form2'] = form
                    template = get_template("alu_practicaspreprofesionalesinscripcion/modal/formitinerarios.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'viewsupervisores':
                data['title'] = u'Gestionar Supervisores por periodo'
                search, carreras, filtros, url_vars = request.GET.get('search', ''), request.GET.get('carreras', ''), Q(
                    status=True), ''

                supervisores = PracticasPreprofesionalesInscripcion.objects.filter(
                    preinscripcion__preinscripcion__periodo=periodo).values_list('supervisor__id', flat=True).filter(
                    status=True, supervisor__isnull=False).distinct('supervisor_id').order_by('supervisor__id')

                qsfiltro = PracticasPreprofesionalesInscripcion.objects.filter(
                    preinscripcion__preinscripcion__periodo=periodo,
                    supervisor__id__in=supervisores, status=True)

                idscarreras = qsfiltro.values_list('inscripcion__carrera__id', flat=True).distinct('inscripcion__carrera__id')
                data['lista_carreras'] = Carrera.objects.filter(pk__in=idscarreras).order_by('nombre')

                if carreras:
                    data['carreras'] = int(carreras)
                    filtros = filtros & (Q(inscripcion__carrera_id=carreras))
                    url_vars += '&carreras={}'.format(carreras)
                if search:
                    data['search'] = search
                    s = search.split()
                    if len(s) == 1:
                        filtros = filtros & (Q(supervisor__persona__apellido2__icontains=search) | Q(supervisor__persona__cedula__icontains=search) | Q(supervisor__persona__apellido1__icontains=search))
                    else:
                        filtros = filtros & (Q(supervisor__persona__apellido1__icontains=s[0]) & Q(supervisor__persona__apellido2__icontains=s[1]))
                    url_vars += '&search={}'.format(search)
                qsfiltro = qsfiltro.filter(filtros)  # .order_by('inscripcion__carrera__nombre')
                qsfiltro = qsfiltro.distinct('inscripcion__carrera__id', 'supervisor_id')
                url_vars += '&action={}'.format(action)
                data["url_vars"] = url_vars
                data['listcount'] = qsfiltro.count()
                data['meses'] = MESES_CHOICES
                paging = MiPaginador(qsfiltro, 15)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                    else:
                        p = paginasesion
                    try:
                        page = paging.page(p)
                    except:
                        p = 1
                    page = paging.page(p)
                except:
                    page = paging.page(p)
                request.session['paginador'] = p
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['lista'] = page.object_list

                if 'export_to_excel_supervisores_inscritos' in request.GET:
                    __author__ = 'Unemi'

                    title = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')

                    fuentecabecera = easyxf(
                        'font: name Calibri, color-index black, bold on, height 200; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Calibri, color-index black, height 200; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('SeguimientoSupervisores')
                    ws.write_merge(0, 0, 0, 10, 'CONTROL DE PRÁCTICAS PRE-PROFESIONALES  DE SUPERVISORES', title)

                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=listado_supervisores_inscritos' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"SUPERVISOR", 10000),
                        (u"CEDULA ", 5000),
                        (u"CORREO ", 8000),
                        (u"TELEFONO ", 5000),
                        (u"CARRERA", 10000),
                        (u"TOTAL SOLICITADO", 4500),
                        (u"TOTAL PENDIENTE", 4500),
                        (u"TOTAL RETIRADO", 4500),
                        (u"TOTAL RECHAZADO", 4500),
                        (u"TOTAL REPROBADO", 4500),
                        (u"TOTAL ASIGNADOS", 4500),
                        (u"TOTAL CULMINADAS", 4500),
                        (u"TOTAL NO CULMINADAS", 6000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listado = qsfiltro
                    row_num = 4
                    i = 0
                    for lista in listado:
                        campo1 = lista.supervisor.persona.nombre_completo()
                        campo2 = lista.supervisor.persona.cedula
                        campo3 = lista.supervisor.persona.emailinst
                        campo4 = lista.supervisor.persona.telefono
                        campo5 = lista.inscripcion.carrera.nombre if lista.inscripcion.carrera else 'SIN CARRERA'
                        campo6 = lista.contar_estado_solicitud(1)
                        campo7 = lista.contar_estado_solicitud(4)
                        campo8 = lista.contar_estado_solicitud(5)
                        campo9 = lista.contar_estado_solicitud(3)
                        campo10 = lista.contar_estado_solicitud(6)
                        campo11 = lista.contar_estado_solicitud(2)
                        campo12 = lista.contar_estado_supervisor_culminado()
                        campo13 = lista.contar_estado_supervisor_noculminado()
                        ws.write(row_num, 0, campo1, fuentenormal)
                        ws.write(row_num, 1, campo2, fuentenormal)
                        ws.write(row_num, 2, campo3, fuentenormal)
                        ws.write(row_num, 3, campo4, fuentenormal)
                        ws.write(row_num, 4, campo5, fuentenormal)
                        ws.write(row_num, 5, campo6, fuentenormal)
                        ws.write(row_num, 6, campo7, fuentenormal)
                        ws.write(row_num, 7, campo8, fuentenormal)
                        ws.write(row_num, 8, campo9, fuentenormal)
                        ws.write(row_num, 9, campo10, fuentenormal)
                        ws.write(row_num, 10, campo11, fuentenormal)
                        ws.write(row_num, 11, campo12, fuentenormal)
                        ws.write(row_num, 12, campo13, fuentenormal)
                        row_num += 1
                    wb.save(response)
                    return response
                return render(request, "alu_practicaspreprofesionalesinscripcion/viewsupervisores.html", data)

            elif action == 'bajarinformemensualzip':
                try:
                    dominiosistema = request.build_absolute_uri('/')[:-1].strip("/")
                    mes = int(request.GET['mesinforme'])
                    anio = int(request.GET['anio'])
                    informes = InformeMensualDocentesPPP.objects.filter(status=True, mes=mes, anio=anio).distinct()

                    archivos_lista = []

                    directory = os.path.join(SITE_STORAGE, 'zipav')
                    try:
                        os.stat(directory)
                    except:
                        os.mkdir(directory)

                    url = os.path.join(SITE_STORAGE, 'media', 'zipav',
                                       'informesmensuales_{}_{}_{}.zip'.format(mes, anio,
                                                                               random.randint(1, 10000).__str__()))
                    url_zip = url
                    fantasy_zip = zipfile.ZipFile(url, 'w')
                    nombredocente = ''
                    for inf in informes:
                        if inf.archivodescargar:
                            nombre = remover_caracteres_especiales_unicode(
                                inf.persona.persona.__str__().lower().replace(' ', '_')).lower().replace(' ', '_')
                            nombredocente = remover_caracteres_especiales_unicode(
                                inf.persona.persona.__str__().lower().replace(' ', '_')).lower().replace(' ', '_')
                            carrera = remover_caracteres_especiales_unicode(
                                inf.carrera.nombre.lower().replace(' ', '_')).lower().replace(' ', '_')
                            fantasy_zip.write(inf.archivodescargar.path,
                                              '{}_{}_{}_{}.pdf'.format(nombre, carrera, mes, anio))
                    fantasy_zip.close()
                    response = HttpResponse(open(url_zip, 'rb'), content_type='application/zip')
                    response['Content-Disposition'] = 'attachment; filename=informesmensuales_{}_{}_{}.zip'.format(mes,
                                                                                                                   anio,
                                                                                                                   random.randint(
                                                                                                                       1,
                                                                                                                       10000).__str__())
                    return response
                except Exception as ex:
                    print(ex)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    messages.error(request, nombredocente)
                    return redirect('{}?action=viewdocentes&info={}&linea={}'.format(request.path, ex,
                                                                                     sys.exc_info()[-1].tb_lineno))

            elif action == 'gestionar_preins_indmasivo':
                try:
                    data['title'] = u'Gestionar Practicas Preprofesionales masivo'
                    data['preinscripcion'] = pre = PreInscripcionPracticasPP.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['idcar'] = request.GET['idcar']
                    data['idest'] = request.GET['idest']
                    form = PracticasPreprofesionalesInscripcionMasivoForm(initial={})
                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/gestionar_preins_indmasivo.html",
                                  data)
                except Exception as ex:
                    print(ex)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'editgestionar_preins_ind':
                try:
                    data['title'] = u'Gestionar Practicas Pre Profesionales'
                    data['preinscripcion'] = pre = DetallePreInscripcionPracticasPP.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    form = PracticasPreprofesionalesInscripcionForm(initial={'inscripcion': pre.inscripcion.id,
                                                                             'itinerario': pre.itinerariomalla if pre.itinerariomalla else None,
                                                                             'numerohora': pre.itinerariomalla.horas_practicas if pre.itinerariomalla else None,
                                                                             'estadopreinscripcion': pre.recorrido().estado if pre.recorrido() else None,
                                                                             'fechadesde': pre.fechadesde,
                                                                             'fechahasta': pre.fechahasta,
                                                                             'tipo': pre.tipo,
                                                                             'tutorunemi': pre.tutorunemi,
                                                                             'supervisor': pre.supervisor.id if pre.supervisor else "",
                                                                             'tipoinstitucion': pre.tipoinstitucion,
                                                                             'sectoreconomico': pre.sectoreconomico,
                                                                             'convenio': pre.convenio,
                                                                             'lugarpractica': pre.lugarpractica,
                                                                             'acuerdo': pre.acuerdo,
                                                                             'empresaempleadora': pre.empresaempleadora,
                                                                             'otraempresaempleadora': pre.otraempresaempleadora,
                                                                             'departamento': pre.departamento,
                                                                             'periodoevidencia': pre.periodoppp
                                                                             })
                    # form.vaciartutorunemi()
                    form.editgestionar_prein_ind(pre)
                    form.tiene_itinerario(pre)
                    form.cargar_estado()
                    form.cargar_tipo()
                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editgestion_preins_ind.html", data)
                except Exception as ex:
                    pass

            elif action == 'conffirmadirectorvinculacion':
                try:
                    data['title'] = u'Personal Vinculación'
                    # data['nopermitido'] = ConfiguracionFirmaPracticasPreprofesionales.objects.filter(status=True, activo=True).exists()
                    data['directores'] = ConfiguracionFirmaPracticasPreprofesionales.objects.filter(
                        status=True).order_by('id')
                    return render(request, "alu_practicaspreprofesionalesinscripcion/directoresvinculacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'adddirectorvinculacion':
                try:
                    data['title'] = u'Adicionar Personal de Vinculación'
                    form = DirectorVinculacionFirmaForm()
                    data['form'] = form
                    # form.editar()
                    return render(request, "alu_practicaspreprofesionalesinscripcion/adddirectorvinculalacion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'editdirectorvinculacion':
                try:
                    data['title'] = u'Editar Director de Vinculación'
                    data['firma'] = firma = ConfiguracionFirmaPracticasPreprofesionales.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    form = DirectorVinculacionFirmaForm(initial=model_to_dict(firma))
                    # form.editar()
                    # form.editarselecccioncombos(firma.persona)
                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editdirectorvinculacion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'deletedirectorvinculacion':
                try:
                    data['title'] = u'Eliminar Director de Vinculación'
                    data['firma'] = ConfiguracionFirmaPracticasPreprofesionales.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/deletedirectorvinculacion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'informecartavinculacion':
                try:
                    data['title'] = u'Carta de Vinculacion'
                    data['fechaimpresion'] = datetime.now().date()
                    data['carta'] = CartaVinculacionPracticasPreprofesionales.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    # data['firma'] = ConfiguracionFirmaPracticasPreprofesionales.objects.get(pk=int(encrypt(request.GET['id'])))
                    # return render(request, "", data)
                    return conviert_html_to_pdf(
                        'alu_practicaspreprofesionalesinscripcion/informe_carta_vinculacion.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'excelinquietudconsultaestudiante':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('practicas')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Listas_Inquietudes' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"N°", 1000),
                        (u"FECHA", 2700),
                        (u"TUTOR", 11000),
                        (u"ESTUDIANTE", 11000),
                        (u"CARRERA", 11000),
                        (u"INQUIETUD DEL ESTUDIANTE", 11000),
                        (u"RESPUESTA DEL TUTOR", 11000),
                        (u"OBSERVACIÓN", 11000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'

                    lista_data = PracticasPreprofesionalesInscripcion.objects.filter(culminada=False,
                                                                                     status=True).order_by(
                        '-fecha_creacion')

                    row_num = 4
                    i = 0
                    for practicaspreprofesional in lista_data:
                        for index, inquietud in enumerate(practicaspreprofesional.inquietudes()):
                            campo1 = index + 1
                            campo2 = inquietud.fechaingreso
                            campo3 = practicaspreprofesional.tutorunemi.__str__()
                            campo4 = practicaspreprofesional.inscripcion.persona.__str__()
                            campo5 = practicaspreprofesional.inscripcion.carrera.__str__()

                            campo6 = inquietud.inquietud
                            if inquietud.respuestas():
                                campo7 = inquietud.respuestas()[0].respuesta
                            else:
                                campo7 = 'Sin Respuesta'
                            if inquietud.observacion:
                                campo8 = inquietud.observacion
                            else:
                                campo8 = 'Sin Obersvacion'
                            ws.write(row_num, 0, campo1, font_style2)
                            ws.write(row_num, 1, campo2, date_format)
                            ws.write(row_num, 2, campo3, font_style2)
                            ws.write(row_num, 3, campo4, font_style2)
                            ws.write(row_num, 4, campo5, font_style2)
                            ws.write(row_num, 5, campo6, font_style2)
                            ws.write(row_num, 6, campo7, font_style2)
                            ws.write(row_num, 7, campo8, font_style2)

                            row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'excelestudiantessintutorias':
                try:
                    fechaactual = datetime.now().date()
                    carreraid = int(request.GET['carrerasid'])
                    qsbase = PracticasPreprofesionalesInscripcion.objects.select_related('inscripcion').filter(status=True, culminada=False, preinscripcion__preinscripcion__periodo=periodo).distinct().exclude(estadosolicitud=3)
                    if carreraid > 0:
                        carreraqs = Carrera.objects.get(pk=carreraid)
                        qsbase = qsbase.filter(inscripcion__carrera=carreraqs)

                    __author__ = 'UNIVERSIDAD ESTATAL DE MILAGRO'
                    title = easyxf(
                        'font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    fuentecabecera = easyxf(
                        'font: name Calibri, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentetexto = easyxf(
                        'font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    borders = Borders()
                    borders.left = Borders.THIN
                    borders.right = Borders.THIN
                    borders.top = Borders.THIN
                    borders.bottom = Borders.THIN
                    align = Alignment()
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style.borders = borders
                    font_style.alignment = align
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    font_style2.borders = borders
                    font_style2.alignment = align
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('ESTUDIANTES_SIN_TUTORIAS')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_sin_tutorias_' + random.randint(1, 10000).__str__() + '.xls'
                    ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    if carreraid > 0:
                        carreraqs = Carrera.objects.get(pk=carreraid)
                        ws.write_merge(1, 1, 0, 6, 'ESTUDIANTES SIN TUTORÌAS {}'.format(carreraqs.nombre), fuentenormal)
                    else:
                        ws.write_merge(1, 1, 0, 6, 'ESTUDIANTES SIN TUTORÌAS', fuentenormal)
                    columns = [
                        (u"DOCENTE", 15000),
                        (u"NOMBRES ESTUDIANTE", 6000),
                        (u"DOCUMENTO ESTUDIANTES", 6000),
                        (u"TELEFONO ESTUDIANTES", 6000),
                        (u"EMAIL PERSONAL", 6000),
                        (u"EMAIL INSTITUCIONAL", 6000),
                        (u"CARRERA", 6000),
                        (u"ITINERARIO", 6000),
                        (u"NIVEL", 6000),
                        (u"TUTOR EMPRESA", 6000),
                        (u"EMPRESA EMPLEADORA", 6000),
                        (u"PAIS", 6000),
                        (u"PROVINCIA", 6000),
                        (u"CIUDAD", 6000),
                    ]
                    row_num = 4
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 5
                    for i in qsbase.order_by('-fecha_creacion').distinct():
                        ws.write_merge(row_num, row_num, 0, 0, i.tutorunemi.__str__(), font_style2)
                        ws.write_merge(row_num, row_num, 1, 1, i.inscripcion.persona.nombre_completo(), font_style2)
                        ws.write_merge(row_num, row_num, 2, 2, i.inscripcion.persona.documento(), font_style2)
                        ws.write_merge(row_num, row_num, 3, 3, i.inscripcion.persona.telefono, font_style2)
                        ws.write_merge(row_num, row_num, 4, 4, i.inscripcion.persona.email, font_style2)
                        ws.write_merge(row_num, row_num, 5, 5, i.inscripcion.persona.emailinst, font_style2)
                        ws.write_merge(row_num, row_num, 6, 6, i.inscripcion.carrera.nombre if i.inscripcion.carrera else '', font_style2)
                        ws.write_merge(row_num, row_num, 7, 7, i.preinscripcion.itinerariomalla.__str__() if i.preinscripcion.itinerariomalla else '', font_style2)
                        ws.write_merge(row_num, row_num, 8, 8, i.nivelmalla.nombre if i.nivelmalla else '', font_style2)
                        ws.write_merge(row_num, row_num, 9, 9, i.tutorempresa, font_style2)
                        ws.write_merge(row_num, row_num, 10, 10, i.empresaempleadora_nombre(), font_style2)
                        ws.write_merge(row_num, row_num, 11, 11, i.inscripcion.persona.pais.nombre if i.inscripcion.persona.pais else '', font_style2)
                        ws.write_merge(row_num, row_num, 12, 12, i.inscripcion.persona.provincia.nombre if i.inscripcion.persona.provincia else '', font_style2)
                        ws.write_merge(row_num, row_num, 13, 13, i.inscripcion.persona.canton.nombre if i.inscripcion.persona.canton else '', font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    print(ex)

            elif action == 'cartavinculacion':
                try:
                    data['title'] = u'Gestión de cartas de vinculación'
                    search = None
                    cartavinculacion = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.filter(pk=search,
                                                                                                        status=True)
                        else:
                            if search:
                                cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.filter((
                                        Q(memo__icontains=search) |
                                        Q(representante__icontains=search) |
                                        Q(acuerdo__empresa__nombre__icontains=search) |
                                        Q(convenio__empresaempleadora__nombre__icontains=search) |
                                        Q(empresa__nombre__icontains=search)
                                        ),Q(status=True))
                            else:
                                cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.filter(status=True)
                    else:
                        cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.filter(status=True)
                    paging = MiPaginador(cartavinculacion.order_by('-id'), 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['cartasvinculacion'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewcartavinculacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcartavinculacion':
                try:
                    data['title'] = u'Adicionar Nueva Carta de Vinculación'
                    form = CartaVinculacionForm(initial={'fecha': datetime.now()})
                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/addcartavinculacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcartavinculacion':
                try:
                    data['title'] = u'Editar Carta de Vinculación'
                    data['cartavinculacion'] = cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = CartaVinculacionForm(initial={
                        'fecha': cartavinculacion.fecha,
                        'memorandum': cartavinculacion.memorandum,
                        'convenio': cartavinculacion.convenio,
                        'acuerdo': cartavinculacion.acuerdo,
                        'empresaempleadora': cartavinculacion.empresa,
                        'departamento': cartavinculacion.departamento,
                        'representante': cartavinculacion.representante,
                        'cargo': cartavinculacion.cargo,
                        'director': cartavinculacion.director,
                        'archivo': cartavinculacion.archivo,
                        'email': cartavinculacion.email,
                        'email1': cartavinculacion.email1,
                        'email2': cartavinculacion.email2,
                        'email3': cartavinculacion.email3,
                    })
                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editcartavinculacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'delcartavinculacion':
                try:
                    data['title'] = u'Eliminar carta de vinculación'
                    data['cartavinculacion'] = CartaVinculacionPracticasPreprofesionales.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/delcartavinculacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'vercartavinculacion':
                try:
                    data['cartavinculacion'] = cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['inscripciones'] = cartavinculacion.detallecartainscripcion_set.filter(status=True)
                    # data['itinerarios'] = cartavinculacion.detallecartaitinerario_set.filter(status=True)

                    return render(request, "alu_practicaspreprofesionalesinscripcion/modalvercartavinculacion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'informecartavinculacion':
                try:
                    data['title'] = u'Carta de Vinculacion'
                    data['fechaimpresion'] = datetime.now().date()
                    # data['carta'] = CartaVinculacionPracticasPreprofesionales.objects.get(
                    #     pk=int(encrypt(request.GET['id'])))
                    data['carta'] = CartaVinculacionPracticasPreprofesionales.objects.get(
                        pk=int(request.GET['id']))
                    # data['firma'] = ConfiguracionFirmaPracticasPreprofesionales.objects.get(pk=int(encrypt(request.GET['id'])))
                    # return render(request, "", data)

                    return conviert_html_to_pdf(
                        'alu_practicaspreprofesionalesinscripcion/informe_carta_vinculacion.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'confevidenciahomologacion':
                try:
                    data['title'] = u'Configuración de las evidencias para homologación de horas'
                    search = None
                    configuracionevidencia = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            configuracionevidencia = ConfiguracionEvidenciaHomologacionPractica.objects.filter(
                                pk=search,
                                status=True)
                        else:
                            if ' ' in search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    configuracionevidencia = ConfiguracionEvidenciaHomologacionPractica.objects.filter(
                                        Q(nombre__icontains=s[0]), Q(status=True))
                                elif len(s) == 2:
                                    configuracionevidencia = ConfiguracionEvidenciaHomologacionPractica.objects.filter(
                                        Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(status=True))
                                elif len(s) == 3:
                                    configuracionevidencia = ConfiguracionEvidenciaHomologacionPractica.objects.filter(
                                        Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(
                                            nombre__icontains=s[2]), Q(status=True))
                            else:
                                configuracionevidencia = ConfiguracionEvidenciaHomologacionPractica.objects.filter(
                                    status=True)
                    else:
                        configuracionevidencia = ConfiguracionEvidenciaHomologacionPractica.objects.filter(status=True)
                    paging = MiPaginador(configuracionevidencia, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['configuracionevidencias'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request,
                                  "alu_practicaspreprofesionalesinscripcion/viewconfiguracionevidenciapractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'addconfevidenciahomologacion':
                try:
                    data[
                        'title'] = u'Adicionar configuración de evidencias para homologación de Práctica Pre-Profesionales'
                    data['form'] = ConfiguracionEvidenciaHomologacionPracticaForm()
                    return render(request, "alu_practicaspreprofesionalesinscripcion/addconfevidenciahomologacion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'editconfevidenciahomologacion':
                try:
                    data[
                        'title'] = u'Editar configuración de evidencias para homologación de Práctica Pre-Profesionales'
                    data[
                        'configuracionevidencia'] = configuracionevidencia = ConfiguracionEvidenciaHomologacionPractica.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['form'] = ConfiguracionEvidenciaHomologacionPracticaForm(
                        initial={'nombre': configuracionevidencia.nombre,
                                 'carrera': configuracionevidencia.carreras()})
                    return render(request,
                                  "alu_practicaspreprofesionalesinscripcion/editconfevidenciahomologacion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'delconfevidenciahomologacion':
                try:
                    data[
                        'title'] = u'Eliminar configuración de evidencias para homologación de Práctica Pre-Profesionales '
                    data['configuracionevidencia'] = ConfiguracionEvidenciaHomologacionPractica.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/delconfevidenciahomologacion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'evidenciahomologacion':
                try:
                    data['title'] = u'Evidencia para la Homologación de Práctica Pre-Profesionales'
                    search = None
                    evidencia = None
                    data[
                        'configuracionevidencia'] = configuracionevidencia = ConfiguracionEvidenciaHomologacionPractica.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            evidencia = configuracionevidencia.evidenciahomologacionpractica_set.filter(pk=search,
                                                                                                        status=True)
                        else:
                            if ' ' in search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    evidencia = configuracionevidencia.evidenciahomologacionpractica_set.filter(
                                        Q(nombre__icontains=s[0]), Q(status=True))
                                elif len(s) == 2:
                                    evidencia = configuracionevidencia.evidenciahomologacionpractica_set.filter(
                                        Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(status=True))
                                elif len(s) == 3:
                                    evidencia = configuracionevidencia.evidenciahomologacionpractica_set.filter(
                                        Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(
                                            nombre__icontains=s[2]), Q(status=True))
                            else:
                                evidencia = configuracionevidencia.evidenciahomologacionpractica_set.filter(status=True)
                    else:
                        evidencia = configuracionevidencia.evidenciahomologacionpractica_set.filter(status=True)
                    paging = MiPaginador(evidencia, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['evidencias'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewevidenciahomologacion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'addevidenciahomologacion':
                try:
                    data[
                        'configuracionevidencia'] = configuracionevidencia = ConfiguracionEvidenciaHomologacionPractica.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Adicionar evidencia para homologación | %s' % (configuracionevidencia.nombre)
                    data['form'] = EvidenciaHomologacionPracticaForm()
                    return render(request, "alu_practicaspreprofesionalesinscripcion/addevidenciahomologacion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'editevidenciahomologacion':
                try:
                    data['evidencia'] = evidencia = EvidenciaHomologacionPractica.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Editar evidencia para homologación | %s' % (
                        evidencia.configuracionevidencia.nombre)
                    data['form'] = EvidenciaHomologacionPracticaForm(initial={'nombre': evidencia.nombre,
                                                                              'fechainicio': evidencia.fechainicio,
                                                                              'fechafin': evidencia.fechafin,
                                                                              'nombrearchivo': evidencia.nombrearchivo,
                                                                              'configurarfecha': evidencia.configurarfecha,
                                                                              'orden': evidencia.orden,
                                                                              'archivo': evidencia.archivo})
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editevidenciahomologacion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'delevidenciahomologacion':
                try:
                    data['title'] = u'Eliminar evidencia para homologación'
                    data['evidencia'] = evidencia = EvidenciaHomologacionPractica.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/delevidenciahomologacion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'delarchivoevidenciahomologacion':
                try:
                    data['title'] = u'Eliminar archivo de evidencias para homologación'
                    data['evidencia'] = EvidenciaHomologacionPractica.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request,
                                  "alu_practicaspreprofesionalesinscripcion/delarchivoevidenciahomologacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'informehomologacion':
                try:
                    data['title'] = u'Informes para la Homologación'
                    data['apertura'] = apertura = AperturaPracticaPreProfesional.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['carreras'] = carreras = apertura.carreras_todo()
                    data['cantidad_carreras'] = len(carreras)
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewinformehomologacion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'carrerashomologacion':
                try:
                    data['title'] = u'Carrera para la Homologación'
                    data['apertura'] = apertura = AperturaPracticaPreProfesional.objects.get(pk=int(request.GET['id']))
                    data['carreras'] = carreras = apertura.carrerahomologacion_set.filter(status=True).order_by(
                        'carrera__nombre')
                    data['cantidad_carreras'] = len(carreras)
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewdocumentorequerido.html", data)
                except Exception as ex:
                    pass

            elif action == 'solicitantes':
                data['title'] = u'Solicitantes Homologación'
                data['id'] = id = int(request.GET['id'])
                data['apertura'] = apertura = AperturaPracticaPreProfesional.objects.get(pk=id)
                carreras = apertura.carrerahomologacion_set.filter(status=True)
                valcarreras = False
                if es_decano:
                    carrerasids = []
                    for i in querydecano:
                        cordecano = i.coordinacion
                        coordinacion_carreras = cordecano.carreras().values_list('id', flat=True)
                        carrerasids += list(coordinacion_carreras)
                    carreras = carreras.filter(carrera__in=carrerasids)
                    valcarreras = True
                if es_director_carr:
                    carreras = carreras.filter(carrera__in=miscarreras.values_list('id', flat=True))
                    valcarreras = True
                data['carreras'] = carreras.order_by('carrera__nombre')
                data['cantidad_carreras'] = len(carreras)
                data['estado_solicitud'] = ESTADO_SOLICITUD_HOMOLOGACION
                data['estado_pasos'] = ESTADOS_PASOS_SOLICITUD
                querybase = SolicitudHomologacionPracticas.objects.filter(apertura=apertura)
                estsolicitud, carreraid, desde, hasta, search, filtros, url_vars = request.GET.get('estsolicitud',
                                                                                                   ''), request.GET.get(
                    'carreraid', ''), request.GET.get('desde', ''), request.GET.get('hasta', ''), request.GET.get(
                    'search', ''), Q(status=True), ''

                if estsolicitud:
                    data['estsolicitud'] = estsolicitud = int(estsolicitud)
                    url_vars += "&estsolicitud={}".format(estsolicitud)
                    filtros = filtros & Q(estados=estsolicitud)
                if carreraid:
                    data['carreraid'] = int(carreraid)
                    url_vars += "&carreraid={}".format(carreraid)
                    filtros = filtros & Q(inscripcion__carrera__id=carreraid)
                if desde:
                    data['desde'] = desde
                    url_vars += "&desde={}".format(desde)
                    filtros = filtros & Q(fecha_creacion__gte=desde)
                if hasta:
                    data['hasta'] = hasta
                    url_vars += "&hasta={}".format(hasta)
                    filtros = filtros & Q(fecha_creacion__lte=hasta)
                if search:
                    data['search'] = search
                    s = search.split()
                    if len(s) == 1:
                        filtros = filtros & (Q(inscripcion__persona__apellido2__icontains=search) | Q(
                            inscripcion__persona__cedula__icontains=search) | Q(
                            inscripcion__persona__apellido1__icontains=search))
                    else:
                        filtros = filtros & (Q(inscripcion__persona__apellido1__icontains=s[0]) & Q(
                            inscripcion__persona__apellido2__icontains=s[1]))
                    url_vars += '&search={}'.format(search)
                url_vars += '&id={}'.format(id)
                data["url_vars"] = url_vars
                if valcarreras:
                    query = querybase.filter(filtros).select_related('inscripcion').filter(
                        inscripcion__carrera__in=carreras.values_list('carrera_id', flat=True)).order_by('-pk')
                else:
                    query = querybase.select_related('inscripcion').filter(filtros).order_by('-pk')
                if 'reporte' in request.GET:
                    try:
                        __author__ = 'Unemi'

                        title = easyxf(
                            'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')

                        fuentecabecera = easyxf(
                            'font: name Calibri, color-index black, bold on, height 200; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                        fuentenormal = easyxf(
                            'font: name Calibri, color-index black, height 200; borders: left thin, right thin, top thin, bottom thin')
                        font_style = XFStyle()
                        font_style.font.bold = True
                        font_style2 = XFStyle()
                        font_style2.font.bold = False
                        wb = Workbook(encoding='utf-8')
                        ws = wb.add_sheet('Solicitudhomologacion')
                        ws.write_merge(0, 0, 0, 10, 'SOLICITUDES DE HOMOLOGACIÓN DE PRÁCTICAS', title)

                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename=listado_solicitudes_homologacion' + random.randint(1, 10000).__str__() + '.xls'

                        columns = [
                            (u"CEDULA", 5000),
                            (u"ESTUDIANTE", 11000),
                            (u"TELEFONO", 5000),
                            (u"CORREO", 7500),
                            (u"CARRERA", 15500),
                            (u"NIVEL", 5000),
                            (u"EMPRESA", 15500),
                            (u"ITINERARIO", 15000),
                            (u"N° HORAS", 3000),
                            (u"N° HORAS HOMOLOGADAS", 5000),
                            (u"DOCUMENTOS SUBIDOS", 3000),
                            (u"VERIFICACION DE REQUISITOS", 5500),
                            (u"FECHA VERFICACIÓN DE REQUISITOS", 7500),
                            (u"VALIDACIÓN DE HORAS", 7500),
                            (u"FECHA VALIDACIÓN DE HORAS", 7500),
                            (u"REGISTRO DE HORAS (DECANO)", 7500),
                            (u"FECHA DE REGISTRO DE HORAS", 7500),
                            (u"ESTADO SOLICITUD", 7500),
                        ]

                        row_num = 3
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]

                        date_format = xlwt.XFStyle()
                        date_format.num_format_str = 'yyyy/mm/dd'

                        # listado = AnilladoPracticasPreprofesionalesInscripcion.objects.filter(cab__in=practicaspreprofesionalesinscripcion).order_by('fecha_creacion')
                        row_num = 4
                        i = 0
                        for lista in query:
                            campo1 = str(lista.inscripcion.persona.identificacion())
                            campo2 = str(lista.inscripcion.persona.nombre_completo_inverso())
                            campo3 = str(lista.inscripcion.persona.telefono)
                            campo4 = str(lista.inscripcion.persona.emailinst)
                            campo5 = str(lista.inscripcion.carrera.nombre)
                            campo6 = str(lista.itinerario.nivel)
                            campo7 = str(lista.otraempresaempleadora)
                            campo8 = str(lista.itinerario.nombre)
                            campo9 = str(lista.itinerario.horas_practicas)
                            campo10 = str(lista.horas_homologadas)
                            campo11 = str(lista.documentoscargados().count())
                            campo12 = str(lista.get_revision_vinculacion_display())
                            campo13 = lista.fecha_revision_vinculacion.strftime("%d-%m-%Y %H:%M:%S") if lista.fecha_revision_vinculacion else ''
                            campo14 = str(lista.get_revision_director_display())
                            campo15 = lista.fecha_revision_director.strftime('%d-%m-%Y %H:%M:%S') if lista.fecha_revision_director else ''
                            campo16 = str(lista.get_revision_decano_display())
                            campo17 = lista.fecha_revision_decano.strftime('%d-%m-%Y %H:%M:%S') if lista.fecha_revision_decano else ''
                            campo18 = str(lista.get_estados_display())

                            ws.write(row_num, 0, campo1, font_style2)
                            ws.write(row_num, 1, campo2, font_style2)
                            ws.write(row_num, 2, campo3, font_style2)
                            ws.write(row_num, 3, campo4, font_style2)
                            ws.write(row_num, 4, campo5, font_style2)
                            ws.write(row_num, 5, campo6, font_style2)
                            ws.write(row_num, 6, campo7, font_style2)
                            ws.write(row_num, 7, campo8, font_style2)
                            ws.write(row_num, 8, campo9, font_style2)
                            ws.write(row_num, 9, campo10, font_style2)
                            ws.write(row_num, 10, campo11, font_style2)
                            ws.write(row_num, 11, campo12, font_style2)
                            ws.write(row_num, 12, campo13, font_style2)
                            ws.write(row_num, 13, campo14, font_style2)
                            ws.write(row_num, 14, campo15, font_style2)
                            ws.write(row_num, 15, campo16, font_style2)
                            ws.write(row_num, 16, campo15, font_style2)
                            ws.write(row_num, 17, campo16, font_style2)
                            row_num += 1
                        wb.save(response)
                        return response
                    except Exception as ex:
                        pass
                data['listcount'] = query.count()
                paging = MiPaginador(query, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                    else:
                        p = paginasesion
                    try:
                        page = paging.page(p)
                    except:
                        p = 1
                    page = paging.page(p)
                except:
                    page = paging.page(p)
                request.session['paginador'] = p
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['lista'] = page.object_list
                return render(request, "alu_practicaspreprofesionalesinscripcion/solicitanteshomologacion.html", data)

            elif action == 'editarsolicitudempresa':
                try:
                    data['filtro'] = filtro = DatosEmpresaPreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    form = SolicitudEmpresaPreinscripcionForm(initial=model_to_dict(filtro))
                    data['form2'] = form
                    template = get_template("alu_practicaspreprofesionalesinscripcion/modal/formsolicitudempresa.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'validarsolicitudempresa':
                try:
                    data['filtro'] = filtro = DatosEmpresaPreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    form = ValidarSolicitudEmpresaForm()
                    data['form2'] = form
                    template = get_template(
                        "alu_practicaspreprofesionalesinscripcion/modal/validarsolicitudempresa.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'validarsolicitudasignaciontutor':
                try:
                    data['filtro'] = filtro = SolicitudVinculacionPreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    form = ValidarSolicitudAsignacionTutorForm()
                    iditinerario = filtro.preinscripcion.itinerariomalla.pk if filtro.preinscripcion.itinerariomalla else None
                    listaidcriterio = [6, 154]
                    if iditinerario:
                        qsbasedistributivo = ProfesorDistributivoHoras.objects.filter(detalledistributivo__criteriodocenciaperiodo__criterio__id__in=listaidcriterio, detalledistributivo__actividaddetalledistributivo__actividaddetalledistributivocarrera__carrera=filtro.preinscripcion.inscripcion.carrera, status=True, periodo=filtro.preinscripcion.preinscripcion.periodo).distinct()
                        tutoresitinerario = qsbasedistributivo.filter(detalledistributivo__actividaddetalledistributivo__actividaddetalledistributivocarrera__itinerariosactividaddetalledistributivocarrera__itinerario_id=iditinerario)
                        listaprofesor = []
                        for x in tutoresitinerario:
                            listaprofesor.append([u'%s' % x.profesor.id, u'%s - (%s) - hor.(%s) - asig.(%s)' % (x.profesor.persona.nombre_completo_inverso(), x.periodo.nombre, x.horas_docencia_segun_criterio_carrera(listaidcriterio, filtro.preinscripcion.inscripcion.carrera.pk), x.profesor.contar_practicaspreprofesionales_asignadas_carrera(filtro.preinscripcion.preinscripcion.periodo, filtro.preinscripcion.inscripcion.carrera.pk, filtro.preinscripcion.pk))])
                        data['listaprofesor'] = listaprofesor
                    form.fields['tutorunemi'].queryset = Profesor.objects.none()
                    form.fields['supervisor'].queryset = Profesor.objects.none()
                    data['form2'] = form
                    template = get_template("alu_practicaspreprofesionalesinscripcion/modal/validarsolicitudasignaciontutor.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'solicitudpdf':
                try:
                    data['title'] = 'SOLICITUD EMPRESA'
                    temp = lambda x : remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(x.__str__()))
                    data['hoy'] = datetime.now()
                    data['filtro'] = filtro = DatosEmpresaPreInscripcionPracticasPP.objects.get(pk=encrypt(request.GET['pk']))
                    fecha = filtro.fecha_revision
                    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                    # if responsablevinculacion:
                    #     data['responsablevinculacion'] = responsablevinculacion
                    #     # firma = FirmaPersona.objects.filter(persona=responsablevinculacion, tipofirma=2, status=True).first()
                    #     firma = responsablevinculacion.archivo.url if responsablevinculacion.archivo else None
                    #     data['firmaimg'] = firma if firma else None
                    template_pdf = 'alu_preinscripcionppp/solicitudpdf.html'
                    nombrepersona = temp(filtro.preinscripcion.inscripcion.persona.__str__()).replace(' ', '_')
                    nombredocumento = 'SOLICITUD_EMPRESA_{}_{}'.format(nombrepersona, random.randint(1, 100000).__str__())
                    directory = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'solicitudempresas')
                    data['url_qr'] = url_qr = f'{SITE_STORAGE}/media/qrcode/solicitudempresas/qr/{nombredocumento}.png'
                    os.makedirs(f'{directory}/qr/', exist_ok=True)
                    if responsablevinculacion:
                        data['responsablevinculacion'] = responsablevinculacion
                        firma = f'APROBADO POR: {responsablevinculacion.nombres}\nCARGO: {temp(responsablevinculacion.cargo)}\nFECHA APROBACION: {fecha.strftime("%d-%m-%Y %H:%M:%S")}\nSOLICITUD: {filtro.codigodocumento}\nESTUDIANTE:{filtro.preinscripcion.inscripcion.persona.__str__()} \nVALIDADO EN: sga.unemi.edu.ec'
                        url = pyqrcode.create(firma)
                        imageqr = url.png(f'{directory}/qr/{nombredocumento}.png', 16, '#000000')
                    try:
                        os.stat(directory)
                    except:
                        os.mkdir(directory)
                    valida = conviert_html_to_pdf_name_save(template_pdf, {'pagesize': 'A4', 'data': data, }, nombredocumento)
                    if valida:
                        # if filtro.archivodescargar:
                        #     filtro.archivodescargar.delete()
                        #     filtro.save(request)
                        filtro.archivodescargar = 'qrcode/solicitudempresas/' + nombredocumento + '.pdf'
                        filtro.save(request)
                    # return conviert_html_to_pdf_name(
                    #     template_pdf,
                    #     {
                    #         'pagesize': 'A4',
                    #         'data': data,
                    #     },
                    #     nombredocumento
                    # )
                    return JsonResponse({"result":'ok', 'url':f"{filtro.archivodescargar.url}"})
                except Exception as ex:
                    lineaerror = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. {} {}".format(str(ex), lineaerror)})

            elif action == 'asignaciontutor':
                data['title'] = u'Solicitud de Asignación Tutor'
                data['id'] = id = int(request.GET['id'])
                data['apertura'] = apertura = PreInscripcionPracticasPP.objects.get(pk=id)
                data['estado_solicitud'] = ESTADO_SOLICITUD_VINCULACION_TUTOR
                querybase = SolicitudVinculacionPreInscripcionPracticasPP.objects.filter(preinscripcion__preinscripcion=apertura)
                carreras = Carrera.objects.filter(status=True, pk__in=querybase.values_list('preinscripcion__inscripcion__carrera__id', flat=True))
                data['carreras'] = carreras.order_by('nombre')
                data['cantidad_carreras'] = len(carreras)
                empresa, dirigidoa, carreraid, estsolicitud, desde, hasta, search, filtros, url_vars = request.GET.get('empresa', ''), request.GET.get('dirigidoa', ''), request.GET.get('carreraid', ''), request.GET.get('estsolicitud', ''), request.GET.get('desde', ''), request.GET.get('hasta', ''), request.GET.get('search', ''), Q(status=True), ''
                if estsolicitud:
                    data['estsolicitud'] = int(estsolicitud)
                    url_vars += "&estsolicitud={}".format(estsolicitud)
                    filtros = filtros & Q(est_empresas=estsolicitud)
                if carreraid:
                    data['carreraid'] = int(carreraid)
                    url_vars += "&carreraid={}".format(carreraid)
                    filtros = filtros & Q(preinscripcion__inscripcion__carrera__id=carreraid)
                if desde:
                    data['desde'] = desde
                    url_vars += "&desde={}".format(desde)
                    filtros = filtros & Q(fecha_creacion__gte=desde)
                if hasta:
                    data['hasta'] = hasta
                    url_vars += "&hasta={}".format(hasta)
                    filtros = filtros & Q(fecha_creacion__lte=hasta)
                if empresa:
                    data['empresa'] = empresa
                    url_vars += "&empresa={}".format(empresa)
                    filtros = filtros & (Q(empresanombre__icontains=empresa) | Q(acuerdo__empresa__nombre__icontains=empresa) | Q(convenio__empresaempleadora__nombre__icontains=empresa))
                if dirigidoa:
                    data['dirigidoa'] = dirigidoa
                    url_vars += "&dirigidoa={}".format(dirigidoa)
                    filtros = filtros & Q(dirigidoa__icontains=dirigidoa)
                if search:
                    data['search'] = search
                    s = search.split()
                    if len(s) == 1:
                        filtros = filtros & (Q(preinscripcion__inscripcion__persona__apellido2__icontains=search) | Q(preinscripcion__inscripcion__persona__cedula__icontains=search) | Q(preinscripcion__inscripcion__persona__apellido1__icontains=search))
                    else:
                        filtros = filtros & (Q(preinscripcion__inscripcion__persona__apellido1__icontains=s[0]) & Q(preinscripcion__inscripcion__persona__apellido2__icontains=s[1]))
                    url_vars += '&search={}'.format(search)
                url_vars += '&action={}&id={}'.format(action, id)
                data["url_vars"] = url_vars
                query = querybase.filter(filtros).order_by('-pk')
                data['listcount'] = query.count()
                paging = MiPaginador(query, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                    else:
                        p = paginasesion
                    try:
                        page = paging.page(p)
                    except:
                        p = 1
                    page = paging.page(p)
                except:
                    page = paging.page(p)
                request.session['paginador'] = p
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['lista'] = page.object_list
                return render(request, "alu_practicaspreprofesionalesinscripcion/asignaciontutor/viewasignacion.html", data)

            elif action == 'generaracuerdo':
                data['title'] = u'Generar Acuerdo'
                data['filtro'] = filtro = SolicitudVinculacionPreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                data['nombre_empresa'] = nombre_empresa = filtro.empresanombre
                data['form'] = AcuerdoCompromisoAsignacionTutorForm()
                data['empresas_coincidencias'] = lista_empresas = EmpresaEmpleadora.objects.filter(status=True, nombre__unaccent__icontains=nombre_empresa).order_by('-pk')
                data['primer_elemento'] = lista_empresas.first()
                return render(request, "alu_practicaspreprofesionalesinscripcion/asignaciontutor/generaracuerdo.html", data)

            elif action == 'validarsolicitud':
                data['title'] = u'Validar Solicitud'
                data['filtro'] = filtro = SolicitudVinculacionPreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                data['form'] = AcuerdoCompromisoAsignacionTutorForm()
                return render(request, "alu_practicaspreprofesionalesinscripcion/asignaciontutor/validarsolicitud.html", data)

            elif action == 'addempresa':
                try:
                    data['solicitud'] = solicitud = SolicitudVinculacionPreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    form = EmpresaAsignacionTutorForm(initial={'ruc': solicitud.empresaruc,
                                                               'nombre': solicitud.empresanombre,
                                                               'tipoinstitucion': solicitud.tipoinstitucion,
                                                               'sectoreconomico': solicitud.sectoreconomico,
                                                               'telefonos': solicitud.telefonos,
                                                               'email': solicitud.email,
                                                               'direccion': solicitud.empresadireccion,
                                                               'representante': solicitud.dirigidoa,
                                                               'pais': solicitud.empresacanton.provincia.pais,
                                                               'cargo': solicitud.cargo, })
                    form.adicionar()
                    data['form'] = form
                    template = get_template('alu_practicaspreprofesionalesinscripcion/asignaciontutor/formempresa.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": str(ex)})


            elif action == 'editarasignaciontutor':
                try:
                    data['title'] = u'Solicitud de vinculación a practicas pre profesionales'
                    data['filtro'] = filtro = SolicitudVinculacionPreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    fechaactual, filtroacuerdoconvenio, preinscripcion = datetime.now().date(), Q(para_practicas=True), filtro.preinscripcion
                    acuerdoqs = AcuerdoCompromiso.objects.filter(status=True, fechafinalizacion__gte=fechaactual, carrera=preinscripcion.inscripcion.carrera).order_by('empresa__nombre')
                    convenioqs = ConvenioEmpresa.objects.filter(status=True, fechafinalizacion__gte=fechaactual, conveniocarrera__carrera=preinscripcion.inscripcion.carrera).order_by('empresaempleadora__nombre')
                    form = AsignacionTutorForm(initial=model_to_dict(filtro))
                    if filtro.tipovinculacion == 2:
                        filtroacuerdoconvenio = Q(para_pasantias=True)
                    form.fields['acuerdo'].queryset = acuerdoqs.filter(filtroacuerdoconvenio)
                    form.fields['convenio'].queryset = convenioqs.filter(filtroacuerdoconvenio)
                    form.fields['empresapais'].queryset = Pais.objects.none()
                    form.fields['empresaprovincia'].queryset = Provincia.objects.none()
                    form.fields['empresacanton'].queryset = Canton.objects.none()
                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/asignaciontutor/formasignacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'traerconvenios':
                try:
                    lista = []
                    filtro, id, tipo = Q(status=True), request.GET['id'], int(request.GET['tipo'])
                    if tipo:
                        if tipo == 1:
                            filtro = filtro & Q(para_practicas=True)
                        if tipo == 2:
                            filtro = filtro & Q(para_pasantias=True)
                    fechaactual = datetime.now().date()
                    inscrip = DetallePreInscripcionPracticasPP.objects.get(pk=int(id))
                    listado = ConvenioEmpresa.objects.filter(filtro).filter(fechafinalizacion__gte=fechaactual, conveniocarrera__carrera=inscrip.inscripcion.carrera)
                    # listado = ConvenioEmpresa.objects.filter(filtro).filter(conveniocarrera__carrera=inscrip.inscripcion.carrera)
                    for p in listado.distinct():
                        lista.append([p.id, p.__str__()])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'traeracuerdos':
                try:
                    lista = []
                    filtro, id, tipo = Q(status=True), request.GET['id'], int(request.GET['tipo'])
                    if tipo:
                        if tipo == 1:
                            filtro = filtro & Q(para_practicas=True)
                        if tipo == 2:
                            filtro = filtro & Q(para_pasantias=True)
                    inscrip = DetallePreInscripcionPracticasPP.objects.get(pk=int(id))
                    fechaactual = datetime.now().date()
                    listado = AcuerdoCompromiso.objects.filter(filtro).filter(carrera=inscrip.inscripcion.carrera, fechafinalizacion__gte=fechaactual, anulado=False)
                    # listado = AcuerdoCompromiso.objects.filter(filtro).filter(carrera=inscrip.inscripcion.carrera)
                    for p in listado.distinct():
                        lista.append([p.id, p.__str__()])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'solicitudaempresas':
                data['title'] = u'Solicitudes a Empresas'
                data['id'] = id = int(request.GET['id'])
                data['apertura'] = apertura = PreInscripcionPracticasPP.objects.get(pk=id)
                data['estado_solicitud'] = ESTADO_SOLICITUD_EMPRESA
                querybase = DatosEmpresaPreInscripcionPracticasPP.objects.filter(preinscripcion__preinscripcion=apertura)
                carreras = Carrera.objects.filter(status=True, pk__in=querybase.values_list('preinscripcion__inscripcion__carrera__id', flat=True))
                data['carreras'] = carreras.order_by('nombre')
                data['cantidad_carreras'] = len(carreras)
                empresa, dirigidoa, codigo, carreraid, estsolicitud, desde, hasta, search, filtros, url_vars = request.GET.get('empresa', ''), request.GET.get('dirigidoa', ''), request.GET.get('codigo', ''), request.GET.get('carreraid', ''), request.GET.get('estsolicitud', ''), request.GET.get('desde', ''), request.GET.get('hasta', ''), request.GET.get('search', ''), Q(status=True), ''
                if estsolicitud:
                    data['estsolicitud'] = int(estsolicitud)
                    url_vars += "&estsolicitud={}".format(estsolicitud)
                    filtros = filtros & Q(est_empresas=estsolicitud)
                if carreraid:
                    data['carreraid'] = int(carreraid)
                    url_vars += "&carreraid={}".format(carreraid)
                    filtros = filtros & Q(preinscripcion__inscripcion__carrera__id=carreraid)
                if desde:
                    data['desde'] = desde
                    url_vars += "&desde={}".format(desde)
                    filtros = filtros & Q(fecha_creacion__gte=desde)
                if hasta:
                    data['hasta'] = hasta
                    url_vars += "&hasta={}".format(hasta)
                    filtros = filtros & Q(fecha_creacion__lte=hasta)
                if codigo:
                    data['codigo'] = codigo
                    url_vars += "&codigo={}".format(codigo)
                    filtros = filtros & Q(codigodocumento__icontains=codigo)
                if empresa:
                    data['empresa'] = empresa
                    url_vars += "&empresa={}".format(empresa)
                    filtros = filtros & Q(empresa__icontains=empresa)
                if dirigidoa:
                    data['dirigidoa'] = dirigidoa
                    url_vars += "&dirigidoa={}".format(dirigidoa)
                    filtros = filtros & Q(dirigidoa__icontains=dirigidoa)
                if search:
                    data['search'] = search
                    s = search.split()
                    if len(s) == 1:
                        filtros = filtros & (Q(preinscripcion__inscripcion__persona__apellido2__icontains=search) | Q(preinscripcion__inscripcion__persona__cedula__icontains=search) | Q(preinscripcion__inscripcion__persona__apellido1__icontains=search))
                    else:
                        filtros = filtros & (Q(preinscripcion__inscripcion__persona__apellido1__icontains=s[0]) & Q(preinscripcion__inscripcion__persona__apellido2__icontains=s[1]))
                    url_vars += '&search={}'.format(search)
                url_vars += '&action={}&id={}'.format(action, id)
                data["url_vars"] = url_vars
                query = querybase.filter(filtros).order_by('-pk')
                data['listcount'] = query.count()
                paging = MiPaginador(query, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                    else:
                        p = paginasesion
                    try:
                        page = paging.page(p)
                    except:
                        p = 1
                    page = paging.page(p)
                except:
                    page = paging.page(p)
                request.session['paginador'] = p
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['lista'] = page.object_list
                return render(request, "alu_practicaspreprofesionalesinscripcion/viewsolicitudempresas.html", data)

            elif action == 'xlsxsoliemp':
                try:
                    id = int(request.GET['id'])
                    data['apertura'] = apertura = PreInscripcionPracticasPP.objects.get(pk=id)
                    querybase = DatosEmpresaPreInscripcionPracticasPP.objects.filter(preinscripcion__preinscripcion=apertura)
                    #carreras = Carrera.objects.filter(status=True, pk__in=querybase.values_list('preinscripcion__inscripcion__carrera__id', flat=True))
                    empresa, dirigidoa, codigo, carreraid, estsolicitud, desde, hasta, search, filtros, url_vars = request.GET.get('empresa', ''), request.GET.get('dirigidoa', ''), request.GET.get('codigo', ''), request.GET.get('carreraid', ''), request.GET.get('estsolicitud', ''), request.GET.get('desde', ''), request.GET.get('hasta', ''), request.GET.get('search', ''), Q(status=True), ''
                    __autor__ = 'unemi'
                    if estsolicitud:
                        data['estsolicitud'] = int(estsolicitud)
                        url_vars += "&estsolicitud={}".format(estsolicitud)
                        filtros = filtros & Q(est_empresas=estsolicitud)
                    if carreraid:
                        data['carreraid'] = int(carreraid)
                        url_vars += "&carreraid={}".format(carreraid)
                        filtros = filtros & Q(preinscripcion__inscripcion__carrera__id=carreraid)
                    if desde:
                        data['desde'] = desde
                        url_vars += "&desde={}".format(desde)
                        filtros = filtros & Q(fecha_creacion__gte=desde)
                    if hasta:
                        data['hasta'] = hasta
                        url_vars += "&hasta={}".format(hasta)
                        filtros = filtros & Q(fecha_creacion__lte=hasta)
                    if codigo:
                        data['codigo'] = codigo
                        url_vars += "&codigo={}".format(codigo)
                        filtros = filtros & Q(codigodocumento__icontains=codigo)
                    if empresa:
                        data['empresa'] = empresa
                        url_vars += "&empresa={}".format(empresa)
                        filtros = filtros & Q(empresa__icontains=empresa)
                    if dirigidoa:
                        data['dirigidoa'] = dirigidoa
                        url_vars += "&dirigidoa={}".format(dirigidoa)
                        filtros = filtros & Q(dirigidoa__icontains=dirigidoa)
                    if search:
                        data['search'] = search
                        s = search.split()
                        if len(s) == 1:
                            filtros = filtros & (Q(preinscripcion__inscripcion__persona__apellido2__icontains=search) | Q(preinscripcion__inscripcion__persona__cedula__icontains=search) | Q(preinscripcion__inscripcion__persona__apellido1__icontains=search))
                        else:
                            filtros = filtros & (Q(preinscripcion__inscripcion__persona__apellido1__icontains=s[0]) & Q(preinscripcion__inscripcion__persona__apellido2__icontains=s[1]))
                        url_vars += '&search={}'.format(search)
                    url_vars += '&action={}&id={}'.format(action, id)
                    data["url_vars"] = url_vars
                    query = querybase.filter(filtros).order_by('-pk')
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('solicitudes')
                    titulo = workbook.add_format({'font_name': 'Calibri', 'border': 1, 'align': 'center', 'font_size': 12, 'valign': 'vcenter', 'bg_color': '#E4E5DF'})
                    style2 = workbook.add_format({'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'align': 'center', 'font_size': 12, 'valign': 'vcenter'})
                    money = workbook.add_format({'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'align': 'center', 'font_size': 12, 'valign': 'vcenter', 'num_format': '$#,##0.00'})
                    row_num = 1
                    columns =[
                        ('Cod.',50),
                        ('Revisado por',40),
                        ('Fecha Revision',40),
                        ('Fecha Creación',40),
                        ('Estado',17),
                        ('Estudiante',70),
                        ('Cedula',15),
                        ('Carrera',70),
                        ('Itinerario',100),
                        ('Dirigido',30),
                        ('Cargo',70),
                        ('Empresa',80)
                        ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], titulo)
                        ws.set_column(col_num, col_num, columns[col_num][1])
                    row_num +=1
                    for soli in query:
                        ws.write(row_num,0,soli.codigodocumento,style2)
                        ws.write(row_num,1,soli.persona_revision.__str__() if soli.persona_revision else 'N/A',style2)
                        ws.write(row_num,2,str(soli.fecha_revision) if soli.fecha_revision else 'S/F',style2)
                        ws.write(row_num, 3, str(soli.fecha_creacion) if soli.fecha_creacion else 'S/F', style2)
                        ws.write(row_num,4,soli.get_est_empresas_display(),style2)
                        ws.write(row_num,5,soli.preinscripcion.inscripcion.__str__(),style2)
                        ws.write(row_num,6,soli.preinscripcion.inscripcion.persona.cedula,style2)
                        ws.write(row_num,7,soli.preinscripcion.inscripcion.carrera.nombre,style2)
                        ws.write(row_num,8,soli.preinscripcion.itinerariomalla.__str__(),style2)
                        ws.write(row_num,9,soli.dirigidoa,style2)
                        ws.write(row_num,10,soli.cargo,style2)
                        ws.write(row_num,11,soli.empresa,style2)
                        row_num +=1
                    workbook.close()
                    output.seek(0)
                    filename = 'solicitudes_empresas' + random.randint(1, 10000).__str__() + '.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'xlsxsoliemp':
                try:
                    id = int(request.GET['id'])
                    data['apertura'] = apertura = PreInscripcionPracticasPP.objects.get(pk=id)
                    querybase = DatosEmpresaPreInscripcionPracticasPP.objects.filter(preinscripcion__preinscripcion=apertura)
                    #carreras = Carrera.objects.filter(status=True, pk__in=querybase.values_list('preinscripcion__inscripcion__carrera__id', flat=True))
                    empresa, dirigidoa, codigo, carreraid, estsolicitud, desde, hasta, search, filtros, url_vars = request.GET.get('empresa', ''), request.GET.get('dirigidoa', ''), request.GET.get('codigo', ''), request.GET.get('carreraid', ''), request.GET.get('estsolicitud', ''), request.GET.get('desde', ''), request.GET.get('hasta', ''), request.GET.get('search', ''), Q(status=True), ''
                    __autor__ = 'unemi'
                    if estsolicitud:
                        data['estsolicitud'] = int(estsolicitud)
                        url_vars += "&estsolicitud={}".format(estsolicitud)
                        filtros = filtros & Q(est_empresas=estsolicitud)
                    if carreraid:
                        data['carreraid'] = int(carreraid)
                        url_vars += "&carreraid={}".format(carreraid)
                        filtros = filtros & Q(preinscripcion__inscripcion__carrera__id=carreraid)
                    if desde:
                        data['desde'] = desde
                        url_vars += "&desde={}".format(desde)
                        filtros = filtros & Q(fecha_creacion__gte=desde)
                    if hasta:
                        data['hasta'] = hasta
                        url_vars += "&hasta={}".format(hasta)
                        filtros = filtros & Q(fecha_creacion__lte=hasta)
                    if codigo:
                        data['codigo'] = codigo
                        url_vars += "&codigo={}".format(codigo)
                        filtros = filtros & Q(codigodocumento__icontains=codigo)
                    if empresa:
                        data['empresa'] = empresa
                        url_vars += "&empresa={}".format(empresa)
                        filtros = filtros & Q(empresa__icontains=empresa)
                    if dirigidoa:
                        data['dirigidoa'] = dirigidoa
                        url_vars += "&dirigidoa={}".format(dirigidoa)
                        filtros = filtros & Q(dirigidoa__icontains=dirigidoa)
                    if search:
                        data['search'] = search
                        s = search.split()
                        if len(s) == 1:
                            filtros = filtros & (Q(preinscripcion__inscripcion__persona__apellido2__icontains=search) | Q(preinscripcion__inscripcion__persona__cedula__icontains=search) | Q(preinscripcion__inscripcion__persona__apellido1__icontains=search))
                        else:
                            filtros = filtros & (Q(preinscripcion__inscripcion__persona__apellido1__icontains=s[0]) & Q(preinscripcion__inscripcion__persona__apellido2__icontains=s[1]))
                        url_vars += '&search={}'.format(search)
                    url_vars += '&action={}&id={}'.format(action, id)
                    data["url_vars"] = url_vars
                    query = querybase.filter(filtros).order_by('-pk')
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('solicitudes')
                    titulo = workbook.add_format({'font_name': 'Calibri', 'border': 1, 'align': 'center', 'font_size': 12, 'valign': 'vcenter', 'bg_color': '#E4E5DF'})
                    style2 = workbook.add_format({'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'align': 'center', 'font_size': 12, 'valign': 'vcenter'})
                    money = workbook.add_format({'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'align': 'center', 'font_size': 12, 'valign': 'vcenter', 'num_format': '$#,##0.00'})
                    row_num = 1
                    columns =[
                        ('Cod.',50),
                        ('Revisado por',40),
                        ('Fecha Revision',40),
                        ('Estado',17),
                        ('Estudiante',70),
                        ('Cedula',15),
                        ('Carrera',70),
                        ('Itinerario',100),
                        ('Dirigido',30),
                        ('Cargo',70),
                        ('Empresa',80)
                        ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], titulo)
                        ws.set_column(col_num, col_num, columns[col_num][1])
                    row_num +=1
                    for soli in query:
                        ws.write(row_num,0,soli.codigodocumento,style2)
                        ws.write(row_num,1,soli.persona_revision.__str__() if soli.persona_revision else '',style2)
                        ws.write(row_num,2,soli.fecha_revision,style2)
                        ws.write(row_num,3,soli.get_est_empresas_display(),style2)
                        ws.write(row_num,4,soli.preinscripcion.inscripcion.__str__(),style2)
                        ws.write(row_num,5,soli.preinscripcion.inscripcion.persona.cedula,style2)
                        ws.write(row_num,6,soli.preinscripcion.inscripcion.carrera.nombre,style2)
                        ws.write(row_num,7,soli.preinscripcion.itinerariomalla.__str__(),style2)
                        ws.write(row_num,8,soli.dirigidoa,style2)
                        ws.write(row_num,9,soli.cargo,style2)
                        ws.write(row_num,10,soli.empresa,style2)
                        row_num +=1
                    workbook.close()
                    output.seek(0)
                    filename = 'solicitudes_empresas' + random.randint(1, 10000).__str__() + '.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'requisitoscarrera':
                try:
                    data['title'] = u'Documentos por Carrera para la Homologación'
                    data['tipos'] = TIPO_DOCUMENTO_HOMOLOGACION
                    data['carrera'] = carrera = CarreraHomologacion.objects.get(pk=int(request.GET['id']))
                    totalactualizado = 0
                    if carrera.apertura.esta_en_fechas():
                        for itin in carrera.itinerariosmalla():
                            documentosbases = ItinerariosMallaDocumentosBase.objects.filter(status=True,
                                                                                            itinerario=itin)
                            for doc in documentosbases:
                                if not CarreraHomologacionRequisitos.objects.filter(status=True, carrera=carrera,
                                                                                    documento=doc.documento,
                                                                                    tipo=doc.tipo,
                                                                                    itinerario=itin).exists():
                                    filtro = CarreraHomologacionRequisitos(carrera=carrera, documento=doc.documento,
                                                                           tipo=doc.tipo, itinerario=itin)
                                    filtro.save(request)
                                    totalactualizado += 1
                    data['totalactualizada'] = totalactualizado
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewdocumentositinerarios.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'addcarrera':
                try:
                    data['postar'] = apertura = AperturaPracticaPreProfesional.objects.get(pk=request.GET['id'])
                    data['yaasignadas'] = detalle = apertura.carrerahomologacion_set.filter(status=True).order_by(
                        'carrera__nombre')
                    data['carreras'] = Carrera.objects.filter(status=True,
                                                              coordinacion__in=apertura.coordinaciones()).exclude(
                        pk__in=detalle.values_list('carrera_id')).order_by('nombre')
                    template = get_template('alu_practicaspreprofesionalesinscripcion/modal/addcarreras.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            elif action == 'veritinierarios':
                try:
                    data['carrera'] = apertura = CarreraHomologacion.objects.get(pk=int(request.GET['id']))
                    data['tipos'] = TIPO_DOCUMENTO_HOMOLOGACION
                    data['listacampos'] = ItinerariosMalla.objects.filter(malla__carrera=apertura.carrera, status=True,
                                                                          malla__carrera__status=True).order_by('id')
                    template = get_template('alu_practicaspreprofesionalesinscripcion/modal/itinerarios.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            elif action == 'estverificacionrequisitos':
                id, ESTADOS_PASOS_SOLICITUD_1, resp = int(request.GET['id']), (), []
                filtro = SolicitudHomologacionPracticas.objects.get(pk=id)
                totaldocumentos = DocumentosSolicitudHomologacionPracticas.objects.filter(status=True, solicitud=filtro).exists()
                totalaprobados = DocumentosSolicitudHomologacionPracticas.objects.filter(status=True, solicitud=filtro, estados=1).exists()
                totalpendientes = DocumentosSolicitudHomologacionPracticas.objects.filter(status=True, solicitud=filtro, estados=0).exists()
                if DocumentosSolicitudHomologacionPracticas.objects.filter(status=True, solicitud=filtro, estados=3).exists():
                    resp = [{'id': 2, 'text': 'RECHAZADO'}]
                else:
                    if totaldocumentos == totalpendientes:
                        resp = [{'id': 2, 'text': 'RECHAZADO'}]
                    if totaldocumentos == totalaprobados:
                        ESTADOS_PASOS_SOLICITUD_1 = ((1, u'APROBADO'), (2, u'RECHAZADO'))
                        resp = [{'id': cr[0], 'text': cr[1]} for cr in ESTADOS_PASOS_SOLICITUD_1]
                return HttpResponse(json.dumps({'state': True, 'result': resp}))

            elif action == 'verdocumentos':
                try:
                    data['solicitud'] = solicitud = SolicitudHomologacionPracticas.objects.get(
                        pk=int(request.GET['id']))
                    ESTADOS_PASOS_SOLICITUD_1 = (
                        (1, u'APROBADO'),
                        (2, u'RECHAZADO')
                    )
                    data['estados'] = ESTADOS_PASOS_SOLICITUD_1
                    ESTADOS_DOCUMENTOS = (
                        (1, u'APROBADO'),
                        (3, u'CORREGIR')
                    )
                    data['estados_documentos'] = ESTADOS_DOCUMENTOS
                    data['documentos'] = documentos = DocumentosSolicitudHomologacionPracticas.objects.filter(solicitud=solicitud,
                                                                                                              status=True).order_by('documento__documento__nombre')
                    template = get_template(
                        'alu_practicaspreprofesionalesinscripcion/modal/documentoshomologacionsolicitud.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            elif action == 'verproceso':
                try:
                    data['solicitud'] = solicitud = SolicitudHomologacionPracticas.objects.get(
                        pk=int(request.GET['id']))
                    data['documentos'] = documentos = DocumentosSolicitudHomologacionPracticas.objects.filter(
                        solicitud=solicitud).order_by('documento__documento__nombre')
                    data['filtro'] = filtro = solicitud.apertura
                    carreraqs = CarreraHomologacion.objects.filter(apertura=filtro,
                                                                   carrera=solicitud.inscripcion.carrera)
                    form = PracticasPreprofesionalesInscripcionSolicitarForm(initial=model_to_dict(solicitud))
                    malla = solicitud.inscripcion.mi_malla()
                    nivel = solicitud.inscripcion.mi_nivel().nivel
                    form.cargar_itinerario(malla, nivel)
                    form.ver_proceso()
                    data['form'] = form
                    if carreraqs.exists():
                        data['carrerahomologacion'] = carreraqs.first()
                    pasoactual = 1
                    data['paso2'] = paso2 = False if not documentos.exists() else True
                    data['paso3'] = paso3 = False if not solicitud.revision_vinculacion == 1 else True
                    data['paso4'] = paso4 = False if not solicitud.revision_director == 1 else True
                    data['paso5'] = paso5 = False if not solicitud.estados == 1 else True
                    if paso2:
                        pasoactual = 2
                    if paso3:
                        pasoactual = 3
                    if paso4:
                        pasoactual = 4
                    if paso5:
                        pasoactual = 5
                    data['pasoactual'] = pasoactual
                    template = get_template('alu_practicaspreprofesionalesinscripcion/modal/modalproceso.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            elif action == 'verhistorial':
                try:
                    solicitud = SolicitudHomologacionPracticas.objects.get(pk=int(request.GET['id']))
                    data['title'] = u'Historial.'
                    data['historial'] = HistoricoRevisionesSolicitudHomologacionPracticas.objects.filter(solicitud=solicitud).order_by('-fecha_creacion')
                    template = get_template('alu_practicaspreprofesionalesinscripcion/modal/verHistorial.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            elif action == 'validarhorashomologacion':
                try:
                    data['solicitud'] = solicitud = SolicitudHomologacionPracticas.objects.get(
                        pk=int(request.GET['id']))
                    data['documentos'] = documentos = DocumentosSolicitudHomologacionPracticas.objects.filter(
                        solicitud=solicitud).order_by('documento__documento__nombre')
                    data['filtro'] = filtro = solicitud.apertura
                    carreraqs = CarreraHomologacion.objects.filter(apertura=filtro,
                                                                   carrera=solicitud.inscripcion.carrera)
                    form = PracticasPreprofesionalesInscripcionSolicitarForm(initial=model_to_dict(solicitud))
                    malla = solicitud.inscripcion.mi_malla()
                    nivel = solicitud.inscripcion.mi_nivel().nivel
                    form.cargar_itinerario(malla, nivel)
                    form.ver_proceso()
                    data['form'] = form
                    if carreraqs.exists():
                        data['carrerahomologacion'] = carreraqs.first()
                    pasoactual = 1
                    data['paso2'] = paso2 = False if not documentos.exists() else True
                    data['paso3'] = paso3 = False if not solicitud.revision_vinculacion == 1 else True
                    data['paso4'] = paso4 = False if not solicitud.revision_director == 1 else True
                    data['paso5'] = paso5 = False if not solicitud.estados == 1 else True
                    if paso2:
                        pasoactual = 2
                    if paso3:
                        pasoactual = 3
                    if paso4:
                        pasoactual = 4
                    if paso5:
                        pasoactual = 5
                    data['pasoactual'] = pasoactual

                    template = get_template('alu_practicaspreprofesionalesinscripcion/modal/validardirectordecano.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            elif action == 'finalizarproceso':
                try:
                    data['filtro'] = solicitud = SolicitudHomologacionPracticas.objects.get(pk=int(request.GET['id']))
                    form = FinalizarHomologacionForm(initial=model_to_dict(solicitud))
                    form.bloquear()
                    data['form2'] = form
                    template = get_template("alu_practicaspreprofesionalesinscripcion/modal/finalizarhomologacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cargararchivoinforme':
                try:
                    data['apertura'] = apertura = AperturaPracticaPreProfesional.objects.get(
                        pk=int(encrypt(request.GET['idapertura'])))
                    data['carrera'] = carrera = Carrera.objects.get(pk=int(encrypt(request.GET['idcarrera'])))
                    form = ArchivoHomologacionPracticaForm()
                    data['form'] = form
                    template = get_template("alu_practicaspreprofesionalesinscripcion/addinformecarrera.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'cargararchivoresolucion':
                try:
                    data['apertura'] = apertura = AperturaPracticaPreProfesional.objects.get(
                        pk=int(encrypt(request.GET['idapertura'])))
                    data['carrera'] = carrera = Carrera.objects.get(pk=int(encrypt(request.GET['idcarrera'])))
                    form = ArchivoHomologacionPracticaForm()
                    data['form'] = form
                    template = get_template("alu_practicaspreprofesionalesinscripcion/addresolucioncarrera.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'versolucitudcarrera':
                try:
                    data['title'] = u"Solicitudes por carrera"
                    data['apertura'] = apertura = AperturaPracticaPreProfesional.objects.get(
                        pk=int(encrypt(request.GET['idapertura'])))
                    data['carrera'] = carrera = Carrera.objects.get(pk=int(encrypt(request.GET['idcarrera'])))
                    data['informe'] = carrera.informe_homologacion(apertura)
                    search = None
                    if 'id' in request.GET:
                        ids = int(encrypt(request.GET['id']))
                        practicasinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(id=ids).distinct()
                    elif 's' in request.GET:
                        search = request.GET['s']
                        practicasinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(
                            (Q(inscripcion__persona__nombres__icontains=search) |
                             Q(inscripcion__persona__apellido1__icontains=search) |
                             Q(inscripcion__persona__apellido2__icontains=search) |
                             Q(inscripcion__persona__cedula__icontains=search) |
                             Q(inscripcion__persona__pasaporte__icontains=search) |
                             Q(inscripcion__identificador__icontains=search) |
                             Q(inscripcion__inscripciongrupo__grupo__nombre__icontains=search) |
                             Q(inscripcion__carrera__nombre__icontains=search) |
                             Q(inscripcion__persona__usuario__username__icontains=search)),
                            status=True, aperturapractica=apertura, inscripcion__carrera=carrera,
                            tiposolicitud=3).distinct().order_by('inscripcion__persona__apellido1',
                                                                 'inscripcion__persona__apellido2',
                                                                 'inscripcion__persona__nombres',
                                                                 '-fecha_creacion')
                    else:
                        practicasinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(
                            aperturapractica=apertura,
                            inscripcion__carrera=carrera,
                            tiposolicitud=3, status=True)  # TIPO DE SOLICITUD = HOMOLOGACIÓN|3
                    paging = MiPaginador(practicasinscripcion, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['practicasinscripcion'] = page.object_list
                    return render(request, "alu_practicaspreprofesionalesinscripcion/viewsolicitudcarrera.html", data)
                except Exception as ex:
                    pass

            elif action == 'verevidenciahomologacion':
                try:
                    data[
                        'practicainscripcion'] = practicainscripcion = PracticasPreprofesionalesInscripcion.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    if not practicainscripcion.configuracionevidencia:
                        return JsonResponse(
                            {"result": "bad", 'mensaje': 'No tiene relación con evidencias de vinculación'})
                    data['evidencias'] = practicainscripcion.evidenciashomologacion()
                    template = get_template(
                        "alu_practicaspreprofesionalesinscripcion/modalverevidenciahomologacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'asignacionempresa':
                try:
                    data['title'] = u'Asignación de Empresa en Prácticas'
                    search = None
                    asignacionempresapractica = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search:
                            s = search.split(" ")
                            if len(s) == 1:
                                asignacionempresapractica = AsignacionEmpresaPractica.objects.filter(Q(nombre__icontains=s[0]) | Q(id__icontains=s[0]), Q(status=True))
                            elif len(s) == 2:
                                asignacionempresapractica = AsignacionEmpresaPractica.objects.filter(
                                    Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(status=True))
                            elif len(s) == 3:
                                asignacionempresapractica = AsignacionEmpresaPractica.objects.filter(
                                    Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(
                                        nombre__icontains=s[2]), Q(status=True))
                            else:
                                asignacionempresapractica = AsignacionEmpresaPractica.objects.filter(
                                    Q(nombre__icontains=search), Q(status=True))
                        else:
                            asignacionempresapractica = AsignacionEmpresaPractica.objects.filter(status=True)
                    else:
                        asignacionempresapractica = AsignacionEmpresaPractica.objects.filter(status=True)
                    paging = MiPaginador(asignacionempresapractica.order_by('id'), 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['asignacionempresapractica'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request,
                                  "alu_practicaspreprofesionalesinscripcion/viewasignacionempresapractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'addasignacionempresa':
                try:
                    data['title'] = u'Adicionar asignación de Empresa en Prácticas'
                    data['form'] = AsignacionEmpresaPracticaForm()
                    return render(request, "alu_practicaspreprofesionalesinscripcion/addasignacionempresa.html", data)
                except Exception as ex:
                    pass

            elif action == 'editasignacionempresa':
                try:
                    data['title'] = u'Editar asignación de Empresa en Prácticas'
                    data['asignacionempresa'] = asignacionempresa = AsignacionEmpresaPractica.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    form = AsignacionEmpresaPracticaForm(initial={
                        'nombre': asignacionempresa.nombre,
                        'pais':asignacionempresa.canton.provincia.pais if asignacionempresa.canton else None,
                        'provincia':asignacionempresa.canton.provincia if asignacionempresa.canton else None,
                        'canton':asignacionempresa.canton if asignacionempresa.canton else None
                    })
                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/editasignacionempresa.html", data)
                except Exception as ex:
                    pass

            elif action == 'delasignacionempresa':
                try:
                    data['title'] = u'Eliminar asignación de Empresa en Prácticas'
                    data['asignacionempresa'] = AsignacionEmpresaPractica.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/delasignacionempresa.html", data)
                except Exception as ex:
                    pass

            elif action == 'culminartutoria':
                try:
                    data['title'] = u'Culminar tutoria'
                    data['practica'] = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/culminatutoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'culminarpractica':
                try:
                    data['title'] = u'Culminar práctica'
                    data['practica'] = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/culminapractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'traertutorias':
                try:
                    data['title'] = u'Culminar tutoria'
                    data['practica'] = practica = PracticasPreprofesionalesInscripcion.objects.get(
                        pk=int(request.GET['id']))
                    data['tutorias'] = PracticasTutoria.objects.filter(practica=practica, status=True)
                    template = get_template("alu_practicaspreprofesionalesinscripcion/modaltutoria.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})

                except Exception as ex:
                    pass

            elif action == 'direccionconvenio':
                try:
                    id = request.GET['id']
                    filtro = ConvenioEmpresa.objects.get(pk=int(id))
                    direccion = filtro.empresaempleadora.direccion if filtro.empresaempleadora.direccion else 'NINGUNA'
                    response = JsonResponse({'result': True, 'direccion': direccion})
                except Exception as ex:
                    response = JsonResponse({'result': False, 'mensaje': 'INTENTELO MÁS TARDE'})
                return HttpResponse(response.content)

            elif action == 'direccionacuerdo':
                try:
                    id = request.GET['id']
                    filtro = AcuerdoCompromiso.objects.get(pk=int(id))
                    direccion = filtro.empresa.direccion if filtro.empresa.direccion else 'NINGUNA'
                    response = JsonResponse({'result': True, 'direccion': direccion})
                except Exception as ex:
                    response = JsonResponse({'result': False, 'mensaje': 'INTENTELO MÁS TARDE'})
                return HttpResponse(response.content)

            elif action == 'moverevidencia':
                try:
                    data['filtro'] = filtro = EvidenciaPracticasProfesionales.objects.get(pk=request.GET['id'])
                    data['evidenciasdisponibles'] = evidencias = EvidenciaPracticasProfesionales.objects.filter(
                        periodoppp=filtro.periodoppp, status=True).exclude(pk=filtro.pk)
                    template = get_template("alu_practicaspreprofesionalesinscripcion/moverevidencias.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'eliminarmasivopreinscripcion':
                try:
                    data['preinscripcion'] = preinscripcion = PreInscripcionPracticasPP.objects.get(status=True, pk=int(
                        request.GET['id']))
                    carreras = []
                    if preinscripcion.carreras():
                        carreras = preinscripcion.carreras().values_list('id', 'nombre', flat=False)
                    else:
                        if preinscripcion.coordinaciones():
                            carreras = Carrera.objects.values_list('id', 'nombre', flat=False).filter(
                                coordinacion__id__in=preinscripcion.coordinaciones().values_list('id', flat=False))
                    data['carreras'] = carreras
                    data['estados'] = ESTADO_PREINSCRIPCIONPPP
                    data['detalle'] = preinscripciones = preinscripcion.detallepreinscripcionpracticaspp_set.filter(
                        status=True)
                    template = get_template("alu_practicaspreprofesionalesinscripcion/eliminarmasivopre.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'revertiraprobaciondirector':
                try:
                    titulo = 'Agregar observación para Director'
                    data['form'] = ObservacionDecanoForm
                    data['solicitud'] = request.GET['id']
                    template = get_template("alu_practicaspreprofesionalesinscripcion/modal/modal_observacionDecano.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", "titulo": titulo, 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'revertiraprobacionvinculacion':
                try:
                    titulo = 'Agregar observación para Vinculación'
                    data['form'] = ObservacionDirectorForm
                    data['solicitud'] = request.GET['id']
                    template = get_template("alu_practicaspreprofesionalesinscripcion/modal/modal_observacionDirector.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", "titulo": titulo, 'data': json_content})
                except Exception as ex:
                    pass

            # elif action == 'fechamaximaplanpractica':
            #     try:
            #         fecha = request.GET['fecha']
            #
            #         config = ConfiguracionGeneralPracticasPPP.objects.filter(status=True, periodo=periodo)
            #         if config.exists():
            #             config.first()
            #             config.fechamaximaplantutoria = fecha
            #             config.save(request)
            #             log()
            #     except Exception as ex:

            elif action == 'gestionar_preins_indmasivosalud':
                try:
                    data['title'] = u'Gestionar Practicas PreProfesionales de Salud masivo'
                    data['preinscripcion'] = pre = PreInscripcionPracticasPP.objects.get(pk=int(encrypt_alu(request.GET['id'])))

                    form = PracticasPreprofesionalesInscripcionMasivoSaludForm()
                    form.cargar_data(pre)

                    data['form'] = form
                    return render(request, "alu_practicaspreprofesionalesinscripcion/gestionar_preins_indmasivosalud.html",
                                  data)
                except Exception as ex:
                    print(ex)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'generarcartavinculacion':
                try:
                    data['title'] = u'Carta de Vinculacion'

                    data['carta'] = cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.get(pk=int(encrypt(request.GET['id'])))
                    carreras = DetalleCartaInscripcion.objects.filter(status=True, carta=cartavinculacion).values_list('inscripcion__inscripcion__carrera', flat=True).distinct()
                    data['carreras'] = Carrera.objects.filter(id__in = carreras).order_by('nombre')


                    if not (cartavinculacion.convenio or cartavinculacion.acuerdo or cartavinculacion.empresa):
                        return JsonResponse({"result": "bad", "mensaje": u"Debe tener al menos un convenio o acuerdo."})

                    return conviert_html_to_pdf(
                        'alu_practicaspreprofesionalesinscripcion/informe_carta_vinculacion.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al generar la carta."})

            elif action == 'alumnoscarrera':
                data = []
                carreras = json.loads(request.GET['carreras_ids'])
                excludes = json.loads(request.GET['excludes']) if json.loads(request.GET['excludes']) else []
                term = request.GET['term']
                preinscripcion = PreInscripcionPracticasPP.objects.get(status=True, pk=int(request.GET['id']))

                preinscripciones = preinscripcion.detallepreinscripcionpracticaspp_set.filter(Q(status=True), Q(inscripcion__carrera__id__in=carreras), Q(inscripcion__persona__nombres__icontains=term) | Q(inscripcion__persona__apellido1__icontains=term) | Q(inscripcion__persona__cedula__icontains=term)).order_by(
                    'inscripcion__persona__nombres', 'inscripcion__persona__apellido1').exclude(inscripcion__id__in=excludes)
                for alumno in preinscripciones[:10]:
                    item = {'id': alumno.inscripcion.pk, 'text': alumno.inscripcion.persona.nombre_completo()}
                    data.append(item)
                return JsonResponse(data, safe=False)

            elif action == 'itinerariocarrera':
                itinerarios = ItinerariosMalla.objects.filter(status=True, malla__carrera_id= request.GET['carrera']).order_by('nombre').values('id', 'nombre')
                return JsonResponse({"result": True, 'itinerarios': itinerarios})

            elif action == 'cambiaritinerario':
                try:
                    data['action']=action
                    data['practica']= practica = PracticasPreprofesionalesInscripcion.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("alu_practicaspreprofesionalesinscripcion/modal/formitinerarioactividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'searchdata':
                try:
                    if not 'model' in request.GET:
                        raise NameError('Datos no encontrados')
                    m = request.GET['model']
                    data = {"result": "bad", 'mensaje': u'Error al obtener los datos.'}
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        sp = m.split(':')
                        model = eval(sp[0])
                        query = model.objects.filter(status=True, nombre__contains=q).distinct()
                        data = {"result": "ok", "results": [{"id": x.id, "name": x.nombre} for x in query]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

            return HttpResponseRedirect(request.path)
        else:
            try:

                data['title'] = u'Practicas Pre Profesionales Inscripción'
                empresa, id, tpfecha, tpsolicitud, tipop, estsolicitud, carreraid, desde, hasta, search, filtros, url_vars = request.GET.get('empresa', ''), request.GET.get('id', ''), request.GET.get('tpfecha', ''), request.GET.get('tpsolicitud', ''), request.GET.get('tipop', ''), request.GET.get('estsolicitud', ''), request.GET.get('carreraid', ''), request.GET.get('desde', ''), request.GET.get('hasta', ''), request.GET.get('search', ''), Q(status=True), ''
                if id:
                    filtros = filtros & Q(id=id)
                if tpsolicitud:
                    data['tpsolicitud'] = int(tpsolicitud)
                    url_vars += "&tpsolicitud={}".format(tpsolicitud)
                    filtros = filtros & Q(tiposolicitud=tpsolicitud)
                if tipop:
                    data['tipop'] = int(tipop)
                    url_vars += "&tipop={}".format(tipop)
                    filtros = filtros & Q(tipo=tipop)
                if estsolicitud:
                    data['estsolicitud'] = estsolicitud = int(estsolicitud)
                    url_vars += "&estsolicitud={}".format(estsolicitud)
                    if estsolicitud == 10:
                        filtros = filtros & Q(detalleevidenciaspracticaspro__isnull=False)
                    elif estsolicitud == 11:
                        # filtros = filtros & Q(detalleevidenciaspracticaspro__estadotutor=2)
                        estudiantesNuevos = PracticasPreprofesionalesInscripcion.objects.filter(status=True, culminada=False)
                        estudiantesInformeCompleto = [estudiante.pk for estudiante in estudiantesNuevos if estudiante.evidenciasaprobadas() == estudiante.totalevidencias()]

                        # for estudiante in estudiantesNuevos:
                        #     if estudiante.evidenciasaprobadas() == estudiante.totalevidencias():
                        #         estudiantesInformeCompleto.append(estudiante.pk)

                        filtros = filtros & Q(pk__in=estudiantesInformeCompleto)
                    elif estsolicitud == 12:
                        filtros = filtros & Q(detalleevidenciaspracticaspro__estadotutor=3)
                    elif estsolicitud == 13:
                        filtros = filtros & Q(anilladopracticaspreprofesionalesinscripcion__isnull=False)
                    elif estsolicitud == 14:
                        filtros = filtros & Q(culminatutoria=True)
                    elif estsolicitud == 15:
                        filtros = filtros & Q(culminatutoria=False)
                    elif estsolicitud == 16:
                        filtros = filtros & Q(culminada=True) & Q(estadosolicitud=2)
                    elif estsolicitud == 17:
                        filtros = filtros & Q(culminada=False) & Q(estadosolicitud=2)
                    else:
                        filtros = filtros & Q(estadosolicitud=estsolicitud)
                if carreraid:
                    data['carreraid'] = int(carreraid)
                    url_vars += "&carreraid={}".format(carreraid)
                    filtros = filtros & Q(inscripcion__carrera__id=carreraid)
                if desde:
                    data['desde'] = desde
                    url_vars += "&desde={}".format(desde)
                    data['tpfecha'] = tpfecha = int(tpfecha)
                    url_vars += "&tpfecha={}".format(tpfecha)
                    if tpfecha == 1:
                        filtros = filtros & Q(fecha_creacion__gte=desde)
                    else:
                        filtros = filtros & Q(fechadesde__gte=desde)
                if hasta:
                    data['hasta'] = hasta
                    url_vars += "&hasta={}".format(hasta)
                    data['tpfecha'] = tpfecha = int(tpfecha)
                    url_vars += "&tpfecha={}".format(tpfecha)
                    if tpfecha == 1:
                        filtros = filtros & Q(fecha_creacion__lte=hasta)
                    else:
                        filtros = filtros & Q(fechahasta__lte=hasta)
                if empresa:
                    data['empresa'] = empresa
                    filtros = filtros & (Q(otraempresaempleadora__icontains=empresa) | Q(empresaempleadora__nombre__icontains=empresa) | Q(acuerdo__empresa__nombre__icontains=empresa) | Q(convenio__empresaempleadora__nombre__icontains=empresa))
                    url_vars += "&empresa={}".format(empresa)
                if search:
                    data['search'] = search
                    s = search.split()
                    if len(s) == 1:
                        filtros = filtros & (Q(inscripcion__persona__apellido1__icontains=search) | Q(
                            inscripcion__persona__nombres__icontains=search) | Q(
                            inscripcion__persona__cedula__icontains=search) | Q(
                            inscripcion__persona__apellido2__icontains=search))
                    else:
                        filtros = filtros & (Q(inscripcion__persona__apellido1__icontains=s[0]) & Q(
                            inscripcion__persona__apellido2__icontains=s[1]))
                    url_vars += '&search={}'.format(search)
                data["url_vars"] = url_vars
                practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.select_related('preinscripcion').filter(filtros).exclude(inscripcion__coordinacion__in=[1])
                if es_director_carr:
                    carrerasids = miscarreras.values_list('id', flat=True)
                    practicaspreprofesionalesinscripcion = practicaspreprofesionalesinscripcion.filter(
                        inscripcion__carrera__in=carrerasids)
                elif es_decano:
                    carrerasids = []
                    for i in querydecano:
                        cordecano = i.coordinacion
                        coordinacion_carreras = cordecano.carreras().values_list('id', flat=True)
                        carrerasids += list(coordinacion_carreras)
                    # cordecano = querydecano.first().coordinacion
                    # carrerasids = cordecano.carreras().values_list('id', flat=True)
                    practicaspreprofesionalesinscripcion = practicaspreprofesionalesinscripcion.filter(
                        inscripcion__carrera__in=carrerasids)
                else:
                    carrerasids = PracticasPreprofesionalesInscripcion.objects.filter(status=True).values_list(
                        'inscripcion__carrera__id', flat=True)

                # estudiantesNuevos = PracticasPreprofesionalesInscripcion.objects.filter(status = True, culminada=False)
                # estudiantesInformeCompleto = 0
                # for estudiante in estudiantesNuevos:
                #         if estudiante.evidenciasaprobadas() == estudiante.totalevidencias():
                #             estudiantesInformeCompleto = estudiantesInformeCompleto + 1
                data['carreras'] = Carrera.objects.filter(status=True, coordinacion__excluir=False, pk__in=carrerasids).order_by('nombre')
                paging = MiPaginador(practicaspreprofesionalesinscripcion.distinct().order_by('-pk'), 10)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                    else:
                        p = paginasesion
                    try:
                        page = paging.page(p)
                    except:
                        p = 1
                    page = paging.page(p)
                except:
                    page = paging.page(p)
                request.session['paginador'] = p
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['practicaspreprofesionales'] = page.object_list
                data['periodo'] = periodo
                data['tipo_solicitud_practicapro'] = TIPO_SOLICITUD_PRACTICAPRO
                data['estados_solicitud_practicas'] = ESTADO_SOLICITUD
                data['tipo_practica_pp'] = TIPO_PRACTICA_PP
                data['id'] = request.GET['id'] if 'id' in request.GET else ''
                data['totalinscripciones'] = practicaspreprofesionalesinscripcion.count()
                # data['totalinformescompletos'] = estudiantesInformeCompleto
                data['totaldocentes'] = ActividadDetalleDistributivoCarrera.objects.select_related('actividaddetalle').filter(actividaddetalle__criterio__criteriodocenciaperiodo__criterio__id__in=[6, 154], actividaddetalle__criterio__distributivo__periodo=periodo, actividaddetalle__criterio__distributivo__status=True, status=True).count()
                data['reporte_1'] = obtener_reporte('certificado_cartaautorizacion')
                data['reporte_0'] = obtener_reporte('certificado_prapre_empresa')
                data['reporte_2'] = obtener_reporte('certificado_prapre_empresa_salud')
                data['reporte_3'] = obtener_reporte('certificado_actividadextracurricular')
                if 'export_to_excel' in request.GET:
                    # if data['permiteWebPush'] and request.user.is_superuser:
                    noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                        titulo='Reporte de PreInscritos Practicas PreProfesionales', destinatario=persona,
                                        url='',
                                        prioridad=1, app_label='SGA',
                                        fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                        en_proceso=True)
                    noti.save(request)
                    reporte_pre_inscritos_ppp(request=request, data=practicaspreprofesionalesinscripcion, notiid=noti.pk, periodo=periodo).start()
                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                if 'export_to_excel_anillado' in request.GET:
                    __author__ = 'Unemi'

                    title = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')

                    fuentecabecera = easyxf(
                        'font: name Calibri, color-index black, bold on, height 200; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Calibri, color-index black, height 200; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('SeguimientosAnillados')
                    ws.write_merge(0, 0, 0, 10, 'CONTROL DE DOCUMENTOS ACADÉMICOS', title)

                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=listado_seguimiento_anillados' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"ESTUDIANTENTE", 10000),
                        (u"CEDULA", 5000),
                        (u"TELEFONO", 5000),
                        (u"CORREO", 10000),
                        (u"CARRERA", 25000),
                        (u"NIVEL", 5000),
                        (u"ITINERARIO", 10000),
                        (u"INSTITUCIÓN EMPRESA", 20000),
                        (u"F.DESDE", 10000),
                        (u"F.HASTA", 4500),
                        (u"N° HORAS", 4500),
                        (u"FECHA", 4500),
                        (u"HORA", 4500),
                        (u"OSERVACIÓN", 25000),
                        (u"ESTADO", 25000),
                        (u"F.NACIMIENTO", 10000),
                        (u"EDAD", 10000),
                        (u"TIPO DISCAPACIDAD", 10000),
                        (u"% DISCAPACIDAD", 10000),
                        (u"CARNET DISCAPACIDAD", 10000),
                        (u"ETNIA", 10000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'

                    listado = AnilladoPracticasPreprofesionalesInscripcion.objects.filter(cab__in=practicaspreprofesionalesinscripcion).order_by('fecha_creacion')
                    row_num = 4
                    i = 0
                    for lista in listado:
                        persona_ = lista.cab.inscripcion.persona
                        perfil_ = persona_.mi_perfil()
                        campo1 = lista.cab.inscripcion.persona.__str__()
                        campo2 = lista.cab.inscripcion.persona.cedula
                        campo3 = lista.cab.inscripcion.persona.telefono
                        campo4 = lista.cab.inscripcion.persona.emailinst
                        campo5 = lista.cab.inscripcion.carrera.nombre if lista.cab.inscripcion.carrera else 'SIN CARRERA'
                        campo6 = lista.cab.nivelmalla.nombre if lista.cab.nivelmalla else 'SIN NIVEL'
                        campo7 = lista.cab.itinerariomalla.nombre if lista.cab.itinerariomalla else 'No tiene Itinerario'
                        campo8 = ''
                        if not lista.cab.tipo == 7:
                            if not lista.cab.institucion:
                                if not lista.cab.convenio and not lista.cab.acuerdo:
                                    if not lista.cab.empresaempleadora:
                                        if lista.cab.otraempresaempleadora:
                                            campo8 = lista.cab.otraempresaempleadora.upper()
                                        else:
                                            campo8 = 'NO SE ASIGNÓ UNA EMPRESA O CAMPO "OTRA EMPRESA" VACÍO'
                                    else:
                                        campo8 = lista.cab.empresaempleadora.nombre.upper()
                                else:
                                    if lista.cab.convenio:
                                        if lista.cab.convenio.empresaempleadora:
                                            campo8 = lista.cab.convenio.empresaempleadora.nombre.upper()
                                        else:
                                            campo8 = 'EMPRESA DEL CONVENIO NO ASIGNADA'
                                    elif lista.cab.acuerdo.empresa:
                                        if lista.cab.acuerdo.empresa:
                                            campo8 = lista.cab.acuerdo.empresa.nombre.upper()
                                        else:
                                            campo8 = 'EMPRESA DEL ACUERDO NO ASIGNADA'
                                    else:
                                        campo8 = 'DEBE SELECCIONAR UN ACUERDO O CONVENIO'
                            else:
                                campo8 = lista.cab.institucion.upper()
                        else:
                            campo8 = lista.cab.actividad.titulo
                        campo9 = lista.cab.fechadesde.strftime('%d-%m-%Y') if lista.cab.fechadesde else ''
                        campo10 = lista.cab.fechahasta.strftime('%d-%m-%Y') if lista.cab.fechahasta else ''
                        campo11 = lista.cab.numerohora
                        campo12 = lista.fecha.strftime('%d-%m-%Y')
                        campo13 = lista.hora.strftime('%H:%M:%S')
                        campo14 = lista.detalle
                        campo15 = lista.get_accion()
                        ws.write(row_num, 0, campo1, fuentenormal)
                        ws.write(row_num, 1, campo2, fuentenormal)
                        ws.write(row_num, 2, campo3, fuentenormal)
                        ws.write(row_num, 3, campo4, fuentenormal)
                        ws.write(row_num, 4, campo5, fuentenormal)
                        ws.write(row_num, 5, campo6, fuentenormal)
                        ws.write(row_num, 6, campo7, fuentenormal)
                        ws.write(row_num, 7, campo8, fuentenormal)
                        ws.write(row_num, 8, campo9, fuentenormal)
                        ws.write(row_num, 9, campo10, fuentenormal)
                        ws.write(row_num, 10, campo11, fuentenormal)
                        ws.write(row_num, 11, campo12, fuentenormal)
                        ws.write(row_num, 12, campo13, fuentenormal)
                        ws.write(row_num, 13, campo14, fuentenormal)
                        ws.write(row_num, 14, campo15, fuentenormal)
                        ws.write(row_num, 15, persona_.nacimiento, font_style)
                        ws.write(row_num, 16, persona_.edad(), font_style)
                        if perfil_.tienediscapacidad:
                            ws.write(row_num, 17, perfil_.tipodiscapacidad.nombre if perfil_.tipodiscapacidad else '', font_style)
                            ws.write(row_num, 18, perfil_.porcientodiscapacidad, font_style)
                            ws.write(row_num, 19, perfil_.carnetdiscapacidad, font_style)
                            ws.write(row_num, 20, perfil_.raza.__str__() if perfil_.raza else '', font_style)
                        else:
                            ws.write(row_num, 17, '', font_style)
                            ws.write(row_num, 18, '', font_style)
                            ws.write(row_num, 19, '', font_style)
                            ws.write(row_num, 20, '', font_style)
                        row_num += 1
                    wb.save(response)
                    return response
                return render(request, "alu_practicaspreprofesionalesinscripcion/view.html", data)
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                print(ex)