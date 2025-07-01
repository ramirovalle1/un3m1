# -*- coding: latin-1 -*-
import json
import os
import random
import sys
import zipfile
from datetime import datetime, timedelta
from django.db.models.functions import ExtractMonth, ExtractYear
import pyqrcode
import xlwt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q, Count, Sum, Avg, ExpressionWrapper, DecimalField, Value, IntegerField, F
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.template import Context
from django.template.loader import get_template
from xlwt import *

from decorators import secure_module, last_access
from settings import SITE_STORAGE, DEBUG, TIPO_PERIODO_REGULAR
from sga.commonviews import adduserdata, obtener_reporte, traerNotificaciones
from sga.excelbackground import reporte_pre_inscritos_ppp
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
    AcuerdoCompromisoAsignacionTutorForm, EmpresaAsignacionTutorForm, ValidarSolicitudAsignacionTutorForm, CambioCarreraPracticaConActividadForm, \
    ObservacionDecanoForm, ObservacionDirectorForm, PracticasPreprofesionalesInscripcionMasivoSaludForm, PreInscripcionPracticasSaludForm, FirmaInformeMensualActividadesForm
from sga.funciones import log, MiPaginador, generar_nombre, convertir_fecha, notificacion, \
    remover_caracteres_especiales_unicode, get_director_vinculacion, remover_caracteres_tildes_unicode, convertirfecha2,generar_codigo, calcula_edad_fn_fc, convertir_fecha_invertida, \
    validarcedula
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavecartavinculacion, conviert_html_to_pdf_name, \
    conviert_html_to_pdf_name_save
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
    EmpresaEmpleadora, DetalleDistributivo, Notificacion, HistorialDocumentosSolicitudHomologacionPracticas, InscripcionActividadConvalidacionPPV, \
    HistoricoRevisionesSolicitudHomologacionPracticas, Persona, PreinscribirMasivoHistorial, Externo, PerfilUsuario
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt, encrypt_alu
from inno.models import *
from inno.forms import InsumoInformeInternadoRotativoForm, PracticasPreprofesionalesInscripcionMasivoEstudianteSaludForm, ConfiguracionInscripcionPracticasPPForm, \
    PracticasPreprofesionalesInscripcionSaludForm, AsignacionMasivoSaludForm, ActualizaConfiguracionInscripcionPracticasPPForm, FormatoPppForm, FechasConvocatoriaPPPForm, \
    ResponsableCentroSaludForm, MasivoPreinscripcionSaludForm, MasivoEmpresaSaludForm, UbicacionEmpresaPracticaForm
from inno.funciones import haber_aprobado_modulos_ingles, haber_aprobado_modulos_computacion, asignaturas_aprobadas_primero_septimo_nivel, \
    haber_cumplido_horas_creditos_vinculacion, asignaturas_aprobadas_primero_penultimo_nivel
from bd.funciones import calcular_edad
from utils.filtros_genericos import consultarPersona

@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
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
    data['practicasalud'] = practicasalud = True
    if persona.es_profesor():
        coordinacion = persona.profesor().coordinacion
    if persona.id in [17579, 818, 5194, 23532, 169, 12130, 16630, 1652, 21604, 30751, 30802, 27946, 16781]:
        coordinacion = []
    miscarreras = persona.mis_carreras_tercer_nivel()
    tiene_carreras_director = True if miscarreras else False
    querydecano = ResponsableCoordinacion.objects.filter(periodo=periodo, status=True, persona=persona, tipo=1)
    es_director_carr = tiene_carreras_director if not querydecano.exists() else False
    data['es_director_carr'] = es_director_carr
    data['es_decano'] = es_decano = querydecano.exists()
    data['hoy'] = hoy = datetime.now().date()
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
                postar = DatosEmpresaPreInscripcionPracticasPP.objects.get(id=int(request.POST['id']))
                form = ValidarSolicitudEmpresaForm(request.POST)
                if form.is_valid():
                    postar.est_empresas = form.cleaned_data['est_empresas']
                    postar.observacion = form.cleaned_data['observacion']
                    postar.fecha_revision = datetime.now()
                    postar.persona_revision = persona
                    postar.save(request)
                    asunto = u"GENERACIÓN DE SOLICITUD A EMPRESA"
                    para = postar.preinscripcion.inscripcion.persona
                    notificacion(asunto, postar.observacion, para, None, '/alu_preinscripcioppp', postar.pk, 1, 'sga',
                                 DatosEmpresaPreInscripcionPracticasPP, request)
                    log(u'Valido Solicitud Empresa Preinscripción Practicas : %s %s' % (
                        postar, postar.preinscripcion.inscripcion), request, "add")
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
                    conf_turnos = ConfiguracionOrdenPrioridadInscripcion.objects.filter(preinscripcion=preinscripcion).first()
                    if conf_turnos:
                        for t in conf_turnos.ordenprioridadinscripcion_set.filter(status=True):
                            t.status = False
                            t.save(request)
                            historial = HistorialAsignacionTurno(ordenprioridad=t, nota=t.nota, observacion='Eliminado de manera masiva', fecha=hoy, persona=persona)
                            historial.save(request)
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'migrarmasivoperiodo':
            try:
                with transaction.atomic():
                    preinscripcion = PreInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
                    aData = json.loads(request.POST['aData'])
                    for dato in aData:
                        inscripcion = Inscripcion.objects.get(id=int(dato[0]))
                        nivelalumno = inscripcion.mi_nivel().nivel if inscripcion.coordinacion.id != 1 else None

                        for i in dato[1]:
                            # VALIDAR QUE NO SE GRABE 2 VECES
                            itinerario = ItinerariosMalla.objects.get(pk=int(i)) if int(i) > 0 else None
                            if not DetallePreInscripcionPracticasPP.objects.filter(status=True, preinscripcion=preinscripcion, inscripcion=inscripcion, itinerariomalla=itinerario).exclude(estado=3).exists():
                            # if not DetallePreInscripcionPracticasPP.objects.filter(preinscripcion=preinscripcion, inscripcion=inscripcion).exists():
                                detalle = DetallePreInscripcionPracticasPP(preinscripcion=preinscripcion,
                                                                           inscripcion=inscripcion,
                                                                           nivelmalla=nivelalumno,
                                                                           itinerariomalla=itinerario,
                                                                           estado=1,
                                                                           fecha=datetime.now())
                                detalle.save(request)
                                #Notificación al estudiante por itinerario
                                asunto = u"PRE INSCRIPCIÓN EN PRÁCTICAS PRE PROFESIONALES"
                                para = inscripcion.persona
                                genero = 'a' if para.es_mujer() else 'o'
                                notificacion(asunto, f"Estimad{genero} {para.__str__()}, usted se encuentra pre inscrit{genero} en las prácticas pre profesionales de la convocatoria {preinscripcion.motivo.__str__()} ({preinscripcion.__str__()}). {itinerario.__str__() if itinerario else ''}",
                                            para, None,
                                             '/alu_preinscripcioppp?', detalle.pk, 1,
                                             'sga', DetallePreInscripcionPracticasPP, request)
                                log(u'Adicionó una Pre-Inscripción de practicas preprofesionales (masivo): %s el estudiante: %s' % (detalle, inscripcion), request, "add")
                    return JsonResponse({"result": "ok", 'mensaje': u'Se ejecutó el proceso correctamente'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al migrar los datos, intentelo más tarde."})

        if action == 'ordenprioridad':
            try:
                with transaction.atomic():
                    preinscripcion = PreInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
                    aData = DetallePreInscripcionPracticasPP.objects.filter(preinscripcion=preinscripcion, status=True).exclude(estado=3).distinct('inscripcion')
                    grupoorden = int(request.POST['orden'])
                    if copi := preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first():
                        copi.fecha = hoy
                        copi.persona = persona
                        copi.save(request)
                    else:
                        copi = ConfiguracionOrdenPrioridadInscripcion(preinscripcion=preinscripcion, fecha=hoy, grupoorden=grupoorden, persona=persona)
                        copi.save(request)
                    copi.grupoorden = grupoorden
                    copi.save(request)

                    resultadosalgoritmo = []
                    resultadosalgoritmoaux = []
                    mejorespuntuados = []
                    if aData:
                        if grupoorden == 1:
                            # Algoritmo de orden PROMEDIO
                            for resp in aData:
                                recoraacdemico = resp.inscripcion.recordacademico_set.filter(asignatura_id__isnull=False, status=True, validapromedio=True, valida=True)
                                promedio = round(recoraacdemico.aggregate(promedio=Avg('nota'))['promedio'], 2)
                                resultadosalgoritmoaux.append([resp.inscripcion.id, promedio])
                            resultadosalgoritmo = list(sorted(resultadosalgoritmoaux, key=lambda x: x[1], reverse=True))

                            cantidadmeritoacademico = int(round(len(resultadosalgoritmo) * 0.1))  # Se obtiene el 10% de los mejores puntuados
                            mejorespuntuados = list(map(lambda x: [x[0], x[1],'','','','','','','','','MÉRITO ACADÉMICO'], resultadosalgoritmo[:cantidadmeritoacademico]))
                            resultadosalgoritmo = list(map(lambda x: [x[0], x[1],'','','','','','','','',''], resultadosalgoritmo[cantidadmeritoacademico:]))

                        if grupoorden == 2:
                            # Algoritmo de orden DISCAPACIDAD/ENFERMEDAD
                            for resp in aData:
                                inscripcion = resp.inscripcion
                                estudiante_persona = inscripcion.persona
                                recoraacdemico = resp.inscripcion.recordacademico_set.filter(asignatura_id__isnull=False, status=True, validapromedio=True, valida=True)
                                promedio = round(recoraacdemico.aggregate(promedio=Avg('nota'))['promedio'], 2)
                                etiqueta, discapacidad, porciento, enfermedad, familiardiscapacidad, familiarporciento, familiarenfermedad= '', 0, 0, 0, 0, 0, 0
                                # Prioridad 2
                                personadiscapacidad = PerfilInscripcionExtensionSalud.objects.filter(status=True, estadoaprobacion=2, perfilinscripcion__persona=estudiante_persona).first()
                                if personadiscapacidad:
                                    discapacidad = 1
                                    porciento = personadiscapacidad.perfilinscripcion.porcientodiscapacidad
                                    etiqueta = 'DISCAPACIDAD ' + str(porciento) + '%'

                                personaenfermedad = PersonaEnfermedadExtensionSalud.objects.filter(status=True, estadoaprobacion=2, personaenfermedad__persona=estudiante_persona)
                                if personaenfermedad:
                                    enfermedad = 1
                                    etiqueta += u'%sENFERMEDAD' % ('/' if etiqueta != '' else '')

                                if etiqueta == '':
                                    personafamiliardiscapacidad = PersonaDatosFamiliaresExtensionSalud.objects.filter(status=True, estadoaprobaciondiscapacidad=2, personafamiliar__persona=estudiante_persona)
                                    if personafamiliardiscapacidad:
                                        familiardiscapacidad = 1
                                        familiarporciento = personafamiliardiscapacidad.first().personafamiliar.porcientodiscapacidad
                                        etiqueta = 'FAMILIAR DISCAPACIDAD ' + str(familiarporciento) + '%'
                                    personafamiliarenfermedad = EnfermedadFamiliarSalud.objects.filter(status=True, estadoaprobacion=2, personafamiliarext__personafamiliar__persona=estudiante_persona)
                                    if personafamiliarenfermedad:
                                        familiarenfermedad = 1
                                        etiqueta += u'%sFAMILIAR ENFERMEDAD' % ('/' if etiqueta != '' else '')
                                resultadosalgoritmoaux.append([resp.inscripcion.id, promedio, discapacidad, porciento, enfermedad, familiardiscapacidad, familiarporciento, familiarenfermedad,'','',etiqueta])
                            resultadosalgoritmo = list(sorted(resultadosalgoritmoaux, key=lambda x: (x[2], x[3], x[4], x[5], x[6], x[7], x[1]), reverse=True))

                        if grupoorden == 3:
                            # Algoritmo de orden EMBARAZO
                            for resp in aData:
                                embarazo, etiqueta = 0, ''
                                inscripcion = resp.inscripcion
                                estudiante_persona = inscripcion.persona
                                recoraacdemico = resp.inscripcion.recordacademico_set.filter(asignatura_id__isnull=False, status=True, validapromedio=True, valida=True)
                                promedio = round(recoraacdemico.aggregate(promedio=Avg('nota'))['promedio'], 2)
                                personaembarazo = PersonaDetalleMaternidadExtensionSalud.objects.filter(status=True, estadoaprobacion=2, personamaternidad__persona=estudiante_persona)
                                if personaembarazo:
                                    embarazo = 1
                                    etiqueta = 'EMBARAZO'
                                resultadosalgoritmoaux.append([resp.inscripcion.id, promedio, embarazo,'','','','','','','',etiqueta])
                            resultadosalgoritmo = list(sorted(resultadosalgoritmoaux, key=lambda x: (x[2], x[1]), reverse=True))

                        if grupoorden == 4:
                            # Algoritmo de orden HIJOS MENORES 5AÑOS
                            for resp in aData:
                                hijosmenores, etiqueta = 0, ''
                                inscripcion = resp.inscripcion
                                estudiante_persona = inscripcion.persona
                                recoraacdemico = resp.inscripcion.recordacademico_set.filter(asignatura_id__isnull=False, status=True, validapromedio=True, valida=True)
                                promedio = round(recoraacdemico.aggregate(promedio=Avg('nota'))['promedio'], 2)
                                ninio = PersonaDatosFamiliaresExtensionSalud.objects.filter(status=True, estadoaprobacionninio=2, personafamiliar__persona=estudiante_persona)
                                if ninio:
                                    hijosmenores = 1
                                    etiqueta = u'NIÑOS/AS MENORES DE 5 AÑOS'
                                resultadosalgoritmoaux.append([resp.inscripcion.id, promedio, hijosmenores,'','','','','','','',etiqueta])
                            resultadosalgoritmo = list(sorted(resultadosalgoritmoaux, key=lambda x: (x[2], x[1]), reverse=True))

                        if grupoorden == 5:
                            for resp in aData.values_list('inscripcion_id', 'id'):
                                inscripcion = Inscripcion.objects.get(pk=int(resp[0]))
                                recoraacdemico = inscripcion.recordacademico_set.filter(asignatura_id__isnull=False, status=True, validapromedio=True, valida=True)
                                promedio = round(recoraacdemico.aggregate(promedio=Avg('nota'))['promedio'], 2)
                                resultadosalgoritmoaux.append([int(resp[0]), promedio])
                            resultadosalgoritmo = list(sorted(resultadosalgoritmoaux, key=lambda x: x[1], reverse=True))
                            #Prioridad 1
                            cantidadmeritoacademico = int(round(len(resultadosalgoritmo) * 0.1))  # Se obtiene el 10% de los mejores puntuados
                            mejorespuntuados = list(map(lambda x: [x[0], x[1], '', '', '', '', '', '', '', '', 'MÉRITO ACADÉMICO'], resultadosalgoritmo[:cantidadmeritoacademico]))
                            inscripcionesmejorespuntuados = list(map(lambda x: x[0], mejorespuntuados))

                            resultadosalgoritmoaux = []
                            for resp in aData.values_list('inscripcion_id', 'id').exclude(inscripcion_id__in=inscripcionesmejorespuntuados):
                                inscripcion = Inscripcion.objects.get(pk=int(resp[0]))
                                estudiante_persona = inscripcion.persona
                                recoraacdemico = inscripcion.recordacademico_set.filter(asignatura_id__isnull=False, status=True, validapromedio=True, valida=True)
                                promedio = round(recoraacdemico.aggregate(promedio=Avg('nota'))['promedio'], 2)
                                etiqueta, discapacidad, porciento, enfermedad, familiardiscapacidad, familiarporciento, familiarenfermedad, embarazo, hijosmenores = '', 0, 0, 0, 0, 0, 0, 0, 0

                                #Prioridad 2
                                personadiscapacidad = PerfilInscripcionExtensionSalud.objects.filter(status=True, estadoaprobacion=2, perfilinscripcion__persona=estudiante_persona).first()
                                if personadiscapacidad:
                                    discapacidad = 1
                                    porciento = personadiscapacidad.perfilinscripcion.porcientodiscapacidad
                                    etiqueta = 'DISCAPACIDAD ' + str(porciento) + '%'
                                personaenfermedad = PersonaEnfermedadExtensionSalud.objects.filter(status=True, estadoaprobacion=2, personaenfermedad__persona=estudiante_persona)
                                if personaenfermedad:
                                    enfermedad = 1
                                    etiqueta += u'%sENFERMEDAD' % ('/' if etiqueta != '' else '')
                                if etiqueta == '':
                                    personafamiliardiscapacidad = PersonaDatosFamiliaresExtensionSalud.objects.filter(status=True, estadoaprobaciondiscapacidad=2, personafamiliar__persona=estudiante_persona)
                                    if personafamiliardiscapacidad:
                                        familiardiscapacidad = 1
                                        familiarporciento = personafamiliardiscapacidad.first().personafamiliar.porcientodiscapacidad
                                        etiqueta = 'FAMILIAR DISCAPACIDAD ' + str(familiarporciento) + '%'
                                    personafamiliarenfermedad = EnfermedadFamiliarSalud.objects.filter(status=True, estadoaprobacion=2, personafamiliarext__personafamiliar__persona=estudiante_persona)
                                    if personafamiliarenfermedad:
                                        familiarenfermedad = 1
                                        etiqueta += u'%sFAMILIAR ENFERMEDAD' % ('/' if etiqueta != '' else '')

                                    # Prioridad 3
                                    if etiqueta == '':
                                        personaembarazo = PersonaDetalleMaternidadExtensionSalud.objects.filter(status=True, estadoaprobacion=2, personamaternidad__persona=estudiante_persona)
                                        if personaembarazo:
                                            embarazo = 1
                                            etiqueta = 'EMBARAZO'

                                        # Prioridad 4
                                        if etiqueta == '':
                                            ninio = PersonaDatosFamiliaresExtensionSalud.objects.filter(status=True, estadoaprobacionninio=2, personafamiliar__persona=estudiante_persona)
                                            if ninio:
                                                hijosmenores = 1
                                                etiqueta = u'NIÑOS/AS MENORES DE 5 AÑOS'

                                resultadosalgoritmoaux.append([int(resp[0]), promedio, discapacidad, porciento, enfermedad, familiardiscapacidad, familiarporciento, familiarenfermedad, embarazo, hijosmenores, etiqueta])
                            resultadosalgoritmo = list(sorted(resultadosalgoritmoaux, key=lambda x: (x[2], x[3], x[4], x[5], x[6], x[7], x[8], x[9], x[1]), reverse=True))

                        numeroorden = 1
                        for result in mejorespuntuados:
                            if registro := OrdenPrioridadInscripcion.objects.filter(configuracionorden=copi, inscripcion_id=result[0], grupoorden=grupoorden).first():
                                registro.orden = numeroorden
                                registro.nota = result[1]
                                registro.etiqueta = result[10]
                            else:
                                registro = OrdenPrioridadInscripcion(configuracionorden=copi, inscripcion_id=result[0], orden=numeroorden, grupoorden=grupoorden, nota=result[1], etiqueta=result[10])
                            registro.status = True #si el turno esta deshabilitado, se habilita
                            registro.save(request)
                            numeroorden += 1

                            #historial de asignacion
                            historial = HistorialAsignacionTurno(ordenprioridad=registro, nota=registro.nota, observacion=registro.etiqueta, fecha=hoy, persona=persona)
                            historial.save(request)

                        for result in resultadosalgoritmo:
                            if registro := OrdenPrioridadInscripcion.objects.filter(configuracionorden=copi, inscripcion_id=result[0], grupoorden=grupoorden).first():
                                registro.orden = numeroorden
                                registro.nota = result[1]
                                registro.etiqueta = result[10]
                            else:
                                registro = OrdenPrioridadInscripcion(configuracionorden=copi, inscripcion_id=result[0], orden=numeroorden, grupoorden=grupoorden, nota=result[1], etiqueta=result[10])
                            registro.status = True #si el turno esta deshabilitado, se habilita
                            registro.save(request)
                            numeroorden += 1

                            # historial de asignacion
                            historial = HistorialAsignacionTurno(ordenprioridad=registro, nota=registro.nota, observacion=registro.etiqueta, fecha=hoy, persona=persona)
                            historial.save(request)

                        log(u'Adicionó un regitro de orden de prioridad (masivo); de %s' % (preinscripcion), request, "add")
                    return JsonResponse({"result": "ok", 'mensaje': u'Se ejecutó el proceso correctamente'})
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al ejecutar el proceso, intentelo más tarde."})

        elif action == 'actualizarestadoturno':
            try:
                orden = OrdenPrioridadInscripcion.objects.get(status=True, pk=int(request.POST['id']))
                if orden.activo:
                    orden.activo = False
                else:
                    orden.activo = True
                orden.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                print(ex)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"{str(ex)} Error al guardar los datos."})

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
                # excluir el itinerario para la selecion de los demas estudiantes
                turno = None
                detalle = practicas.preinscripcion
                if orden := detalle.inscripcion.ordenprioridadinscripcion_set.first():
                    grupoorden = detalle.preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first().grupoorden if detalle.preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first() else None
                    if grupoorden:
                        if turno := orden.obtenerturnoinscripcion(grupoorden, detalle.preinscripcion):
                            orden.excluirdato += str(detalle.itinerariomalla.id) + ','
                            orden.save(request)
                            if not DetallePreInscripcionPracticasPP.objects.filter(preinscripcion=detalle.preinscripcion, inscripcion=detalle.inscripcion, status=True).exclude(pk=detalle.id).exists():
                                orden.status = False
                                orden.save(request)
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
                    if int(f.cleaned_data['tipo']) == 1 or int(f.cleaned_data['tipo']) == 2 or int(f.cleaned_data['tipo']) == 4:
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
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

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
                        detalle = DetalleEvidenciasPracticasPro.objects.get(evidencia_id=request.POST['idevidencia'],
                                                                            inscripcionpracticas_id=request.POST['id'])
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
                    practica = PracticasPreprofesionalesInscripcion.objects.get(id=request.POST['id'])
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
                    if DetalleEvidenciasPracticasPro.objects.filter(evidencia_id=request.POST['idevidencia'],
                                                                    inscripcionpracticas_id=request.POST[
                                                                        'id']).exists():
                        detalle = DetalleEvidenciasPracticasPro.objects.get(evidencia_id=request.POST['idevidencia'],
                                                                            inscripcionpracticas_id=request.POST['id'])
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
                detallepracticas = DetalleEvidenciasPracticasPro.objects.get(evidencia_id=request.POST['idevidencia'],
                                                                             inscripcionpracticas_id=request.POST['id'],
                                                                             status=True)
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
                vinculados = DetalleCartaInscripcion.objects.values_list('inscripcion__pk', flat=True).filter(status=True)
                practicantes = PracticasPreprofesionalesInscripcion.objects.filter(status=True, estadosolicitud=2, preinscripcion__preinscripcion__periodo=periodo, convenio=convenio).exclude(id__in=vinculados)
                lista = [{'idP': p.id, 'cedula': p.inscripcion.persona.cedula, 'nombres': p.inscripcion.persona.nombre_completo_inverso(),
                          'carrera': p.inscripcion.carrera.nombre}
                         for p in practicantes]

                return JsonResponse({"result": "ok", "direccion": direccion, "representante": representante, "cargo": cargo, 'lista': lista})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error en los datos de la empresa."})

        elif action == 'datosacuerdo':
            try:
                acuerdo = AcuerdoCompromiso.objects.get(pk=int(request.POST['id']))
                direccion = acuerdo.empresa.direccion
                representante = acuerdo.empresa.representante
                cargo = acuerdo.empresa.cargo
                vinculados = DetalleCartaInscripcion.objects.values_list('inscripcion__pk', flat=True).filter(status=True)
                practicantes = PracticasPreprofesionalesInscripcion.objects.filter(status=True,estadosolicitud=2,preinscripcion__preinscripcion__periodo = periodo, acuerdo=acuerdo).exclude(id__in=vinculados)
                lista = [{'idP': p.id, 'cedula': p.inscripcion.persona.cedula, 'nombres': p.inscripcion.persona.nombre_completo_inverso(),
                          'carrera':p.inscripcion.carrera.nombre}
                                      for p in practicantes]

                return JsonResponse({"result": "ok", "direccion": direccion, "representante": representante, "cargo": cargo, 'lista':lista})
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

                    #relaciona el formato html con la evidencia
                    if f.cleaned_data['formato']:
                        ef = EvidenciaFormatoPpp(evidencia=evidencia, formato=f.cleaned_data['formato'], fecha=hoy)
                        ef.save(request)

                    log(u'Adiciono evidencia de practica pre profesional: %s - %s [PERIODO DE EVIDENCIA - %s]' % (
                        evidencia, evidencia.id, periodoevidencia), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
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
                    #relaciona el formato html con la evidencia
                    if f.cleaned_data['formato']:
                        if ef := EvidenciaFormatoPpp.objects.filter(evidencia=evidencia, status=True).first():
                            ef.formato = f.cleaned_data['formato']
                            ef.fechaformato = hoy
                            ef.save(request)
                        else:
                            ef = EvidenciaFormatoPpp(evidencia=evidencia, formato=f.cleaned_data['formato'], fecha=hoy)
                            ef.save(request)
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
                if ef := EvidenciaFormatoPpp.objects.filter(evidencia=evidencia, status=True).first():
                    ef.status = False
                    ef.save(request)
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

        elif action == 'addformatoppp':
            try:
                with transaction.atomic():
                    f = FormatoPppForm(request.POST)
                    f.iniciar(request.POST['carrera'], request.POST.getlist('itinerariomalla'))
                    if f.is_valid():
                        formato = FormatoPracticaPreprofesionalSalud(nombre=f.cleaned_data['nombre'],
                                                                     htmlnombre=f.cleaned_data['htmlnombre'],
                                                                     carrera=f.cleaned_data['carrera'],
                                                                     activo=f.cleaned_data['activo'])
                        formato.save(request)
                        for iti in request.POST.getlist('itinerariomalla'):
                            formato.itinerariomalla.add(ItinerariosMalla.objects.get(pk=iti))
                        formato.save(request)
                        log(u'Adicionó formato de prácticas pre profesionales: %s' % (formato), request, "add")
                        messages.success(request, 'Registro guardado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'editformatoppp':
            try:
                formato = FormatoPracticaPreprofesionalSalud.objects.get(pk=int(encrypt(request.POST['id'])))
                f = FormatoPppForm(request.POST)
                f.iniciar(request.POST['carrera'], request.POST.getlist('itinerariomalla'))
                if f.is_valid():
                    formato.nombre = f.cleaned_data['nombre']
                    formato.htmlnombre = f.cleaned_data['htmlnombre']
                    formato.carrera = f.cleaned_data['carrera']
                    formato.activo = f.cleaned_data['activo']
                    formato.save(request)
                    if request.POST.getlist('itinerariomalla'):
                        formato.itinerariomalla.exclude(id__in=request.POST.getlist('itinerariomalla')).delete()
                        formato.itinerariomalla.add(*request.POST.getlist('itinerariomalla'))
                        # for iti in request.POST.getlist('itinerariomalla'):
                        #     formato.itinerariomalla.add(ItinerariosMalla.objects.get(pk=iti))
                    formato.save(request)
                    log(u'Editó formato de prácticas pre profesionales: %s' % (formato), request, "edit")
                    messages.success(request, 'Registro editado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'deleteformato':
            try:
                registro = FormatoPracticaPreprofesionalSalud.objects.get(id=request.POST['id'])
                if registro:
                    registro.status = False
                    registro.save(request)
                else:
                    raise NameError('error')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

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
                    if PreInscripcionPracticasPP.objects.filter(fechainicio=f.cleaned_data['fechainicio'], fechafin=f.cleaned_data['fechainicio'], carrera__in=f.cleaned_data['carrera'], status=True).exists():
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
                    extconf = ExtPreInscripcionPracticasPP(preinscripcion=conf, vinculacion=f.cleaned_data['vinculacion'])
                    extconf.save()
                    for coor in f.cleaned_data['coordinacion']:
                        conf.coordinacion.add(coor)
                    for carr in f.cleaned_data['carrera']:
                        conf.carrera.add(carr)
                    for preg in f.cleaned_data['pregunta']:
                        conf.pregunta.add(preg)
                    conf.save(request)
                    log(u'Adicionó configuaracion de pre-inscripción de practicas preprofesionales: %s' % (conf),
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
                    if PreInscripcionPracticasPP.objects.filter(fechainicio=f.cleaned_data['fechainicio'], carrera__in=f.cleaned_data['carrera'],
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

                    # conf.pregunta = f.cleaned_data['pregunta']
                    conf.pregunta.clear()
                    for preg in f.cleaned_data['pregunta']:
                        conf.pregunta.add(preg)

                    conf.fechamaximoagendatutoria = f.cleaned_data['fechamaximoagendatutoria']
                    conf.inglesaprobado = f.cleaned_data['inglesaprobado']
                    conf.computacionaprobado = f.cleaned_data['computacionaprobado']
                    if extconf := ExtPreInscripcionPracticasPP.objects.filter(preinscripcion=conf, status=True).first():
                        extconf.vinculacion = f.cleaned_data['vinculacion']
                    else:
                        extconf = ExtPreInscripcionPracticasPP(preinscripcion=conf, vinculacion=f.cleaned_data['vinculacion'])
                    extconf.save(request)
                    conf.save(request)
                    log(u'Editó configuaración de pre-inscripción de practicas preprofesionales: %s' % (conf), request,
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
                    log(u'Elimino configuaración de pre-inscripción de practicas preprofesionales: %s' % (conf),
                        request, "del")
                    if extconf := ExtPreInscripcionPracticasPP.objects.filter(preinscripcion=conf, status=True).first():
                        extconf.delete()
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

                if str(inscripcion.id) not in variable_valor('NOVALIDA_NIVEL_SALUD'):
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

                    if orden := inscripcion.ordenprioridadinscripcion_set.first(): #Limpia exclusiones del turno por alguna eliminacion de preinscripcion .
                        if detallepreinscripcion.itinerariomalla:
                            exclusiones = orden.excluirdato.split(',')
                            if str(detallepreinscripcion.itinerariomalla.id) in exclusiones:
                                resultado = preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first()
                                if resultado and resultado.grupoorden:
                                    if turno := orden.obtenerturnoinscripcion(resultado.grupoorden, preinscripcion):
                                        limpiaexclusion = orden.excluirdato.replace(str(detallepreinscripcion.itinerariomalla.id), '')
                                        orden.excluirdato = limpiaexclusion
                                        orden.save(request)

                    log(u'Adicionó detalle de preinscripción prácticas PP: %s' % (detallepreinscripcion),
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'addmasivopreinscripccion':
            try:
                f = MasivoPreinscripcionSaludForm(request.POST)
                preinscripcion = PreInscripcionPracticasPP.objects.get(pk=int(encrypt(request.POST['id'])))
                f.init(request.POST['carrera'], request.POST.getlist('itinerariomalla'), request.POST.getlist('inscripciones'))
                if len(request.POST.getlist('inscripciones')) == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar un alumno."})
                if not f.is_valid():
                    raise NameError('Error en el formulario.')

                listado_casos = []
                listado_estudiantes = request.POST.getlist('inscripciones')
                bandera = False
                for inscripcion in listado_estudiantes:
                    inscripcion = Inscripcion.objects.get(pk=int(inscripcion))
                    if not inscripcion.inscripcionmalla_set.filter(status=True):
                        listado_casos.append([str(inscripcion.persona), 'No tiene una malla asociada para poder inscribirse.'])
                        continue
                    if inscripcion.cumple_total_parcticapp():
                        listado_casos.append([str(inscripcion.persona), 'Estudiante ya cumplio con las horas requeridas de practicas.'])
                        continue

                    if not DetalleRespuestaPreInscripcionPPP.objects.filter(preinscripcion=preinscripcion, inscripcion=inscripcion).exists():
                        detallerespuesta = DetalleRespuestaPreInscripcionPPP(preinscripcion=preinscripcion, inscripcion=inscripcion)
                        detallerespuesta.save(request)

                    listado_itinerarios = f.cleaned_data['itinerariomalla']
                    for itinerario in listado_itinerarios:
                        if not DetallePreInscripcionPracticasPP.objects.filter(inscripcion=inscripcion, preinscripcion=preinscripcion, itinerariomalla=itinerario).exists():
                            if str(inscripcion.id) not in variable_valor('NOVALIDA_NIVEL_SALUD'):
                                if not cumple_preinscribirse_itinerariomalla(inscripcion, itinerario.id):
                                    listado_casos.append([str(inscripcion.persona), f'{itinerario.id} - No cumple con todos los requisitos para poder inscribirse.'])
                                    continue

                            detallepreinscripcion = DetallePreInscripcionPracticasPP(inscripcion=inscripcion, nivelmalla=None,
                                                                                     preinscripcion=preinscripcion, fecha=datetime.now(),
                                                                                     itinerariomalla=itinerario, estado=f.cleaned_data['estado'])
                            detallepreinscripcion.save(request)
                            bandera = True
                            log(u'Adicionó detalle de preinscripción prácticas PP: %s' % (detallepreinscripcion), request, "add")

                            if orden := inscripcion.ordenprioridadinscripcion_set.first(): #Limpia exclusiones del turno por alguna eliminacion de preinscripcion .
                                if detallepreinscripcion.itinerariomalla:
                                    exclusiones = orden.excluirdato.split(',')
                                    if str(detallepreinscripcion.itinerariomalla.id) in exclusiones:
                                        resultado = preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first()
                                        if resultado and resultado.grupoorden:
                                            if turno := orden.obtenerturnoinscripcion(resultado.grupoorden, preinscripcion):
                                                limpiaexclusion = orden.excluirdato.replace(str(detallepreinscripcion.itinerariomalla.id), '')
                                                orden.excluirdato = limpiaexclusion
                                                orden.save(request)
                        else:
                            listado_casos.append([str(inscripcion.persona), f'Estudiante ya se encuentra pre inscrito en {itinerario.id} - {itinerario.nombre}.'])
                msg1, msg = 'Masivo ejecutado con éxito.' if bandera else '', ''
                if listado_casos:
                    resp, msg = '', 'Se le ha generado una notificación de casos excluidos en el proceso.'
                    for l in listado_casos:
                        resp += l[0] +': '+ l[1] +'; '
                    observacion = f'Se ha ejecutado una pre inscripción masiva y se detectaron varios inconvenientes: {resp}'
                    notificacion(f"Preinscripción masiva Salud- estudiantes con problemas ({len(listado_casos)})", observacion, persona, None, f'/alu_prcaticassalud?action=listapreinscritos&id={encrypt(preinscripcion.id)}',
                                 preinscripcion.pk, 1, 'sga', PreInscripcionPracticasPP, request)
                messages.success(request, f'{msg1} {msg}')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'masivoactualizaempresa':
            try:
                f = MasivoEmpresaSaludForm(request.POST)
                preinscripcion = PreInscripcionPracticasPP.objects.get(pk=int(encrypt(request.POST['id'])))
                f.init(request.POST['carrera'], request.POST.getlist('itinerariomalla'), request.POST.getlist('inscripciones'))
                if len(request.POST.getlist('inscripciones')) == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar un alumno."})
                if not f.is_valid():
                    raise NameError('Error en el formulario.')
                listado_casos = []
                listado_estudiantes = request.POST.getlist('inscripciones')
                for d in listado_estudiantes:
                    inscripcion = None
                    if detalle := DetallePreInscripcionPracticasPP.objects.get(pk=int(d)):
                        inscripcion = detalle.inscripcion
                    else:
                        continue
                    if inscripcion:
                        registros = inscripcion.detallepreinscripcionpracticaspp_set.filter(status=True, itinerariomalla__in=request.POST.getlist('itinerariomalla'))
                        for r in registros:
                            practica = r.practicaspreprofesionalesinscripcion_set.filter(status=True).first()
                            if practica:
                                empresa = f.cleaned_data['asignacionempresapractica']
                                practica.asignacionempresapractica = empresa
                                practica.lugarpractica = empresa.canton
                                practica.save(request)
                                log(u'Actualizó empresa masivo prácticas PP: %s' % (practica), request, "edit")
                                listado_casos.append([str(inscripcion.persona), f'{practica.itinerariomalla.id} - {practica.itinerariomalla.nombre}'])
                msg1, msg = 'Masivo ejecutado con éxito.', ''
                if listado_casos:
                    resp, msg = '', 'Se le ha generado una notificación de estudiantes actualizados.'
                    for l in listado_casos:
                        resp += l[0] +': '+ l[1] +'; '
                    observacion = f'Se ha ejecutado una actualización masiva de EMPRESA o CENTRO DE SALUD: {resp}'
                    notificacion(f"Asignación masiva Salud(Empresas) - estudiantes afectados ({len(listado_casos)})", observacion, persona, None, f'/alu_prcaticassalud?action=listapreinscritos&id={encrypt(preinscripcion.id)}',
                                 preinscripcion.pk, 1, 'sga', PreInscripcionPracticasPP, request)
                messages.success(request, f'{msg1} {msg}')
                return JsonResponse({"result": "ok"})
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
                    log(u'Elimino Pregunta para la pre-inscripción de practicas preprofesionales: %s' % pre, request,
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
                if 'id' in request.POST:
                    pre = PreInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
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
                    response['Content-Disposition'] = 'attachment; filename=Listas_PreInscritos' + random.randint(1,
                                                                                                                  10000).__str__() + '.xls'
                    columns = [
                        (u"MALLA", 10000),
                        (u"FACULTAD", 10000),
                        (u"CARRERA", 10000),
                        (u"NIVEL", 3000),
                        (u"JORNADA", 5000),
                        (u"PARALELO", 5000),
                        (u"DOCUMENTO", 3000),
                        (u"ESTUDIANTE", 10000),
                        (u"CELULAR", 5000),
                        (u"CONVENCIONAL", 3000),
                        (u"PRE INSCRIPCIÓN (NOMBRE DE LA PRE INSCRIPCIÓN)", 10000),
                        (u"GÉNERO", 10000),
                        (u"EMAIL", 10000),
                        (u"EMAIL INSTITUCIONAL", 10000),
                        (u"PAIS", 10000),
                        (u"PROVINCIA", 10000),
                        (u"CANTON", 10000),
                        (u"PARROQUIA", 10000),
                        (u"DIRECCION DOMICILIARIA", 10000),
                        (u"ITINERARIO", 2000),
                        (u"HORAS", 3000),
                        (u"FECHA REGISTRO", 3000),
                        (u"HORA REGISTRO", 10000),
                        (u"ESTADO SOLICITUD", 3000),
                        (u"ESTADO ESTUDIANTE", 3000),
                        (u"TIPO", 3000),
                        (u"EMPRESA", 3000),
                        (u"OTRA EMPRESA", 3000),
                        (u"DEPARTAMENTO", 3000),
                        (u"FECHA DESDE", 3000),
                        (u"FECHA HASTA", 3000),
                        (u"TUTOR UNEMI", 3000),
                        (u"SUPERVISOR UNEMI", 3000),
                        (u"TIPO INSTITUCION", 3000),
                        (u"SECTOR ECONOMICO", 3000),
                        (u"OBSERVACION SOLICITUD", 3000),
                        (u"OBSERVACION ESTUDIANTE", 3000),
                        (u"PERIODO EVIDENCIA", 3000),
                        (u"SOLICITUD", 3000),
                        (u"FECHA SOLICITUD", 3000),
                        (u"FECHA INSCRIPCION", 3000),
                        (u"RECORD ACADEMICO", 6000),
                        (u"¿TIENE DISPACADIDAD?", 6000),
                        (u"¿TIPO DISPACADIDAD?", 10000),
                        (u"¿PPL?", 6000),
                        (u"DETALLE PPD", 10000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    col_num = len(columns)
                    if pre.preguntas():
                        for p in pre.preguntas():
                            ws.write(row_num, col_num, '%s' % p.descripcion, font_style)
                            ws.col(col_num).width = 10000
                            col_num = col_num + 1
                    row_num = 4
                    for pi in pre.detallepreinscripcionpracticaspp_set.filter(status=True).order_by(
                            'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                            'inscripcion__persona__nombres').distinct():
                        ws.write(row_num, 0, '%s' % pi.inscripcion.mi_malla() if pi.inscripcion.mi_malla() else '',font_style2)
                        ws.write(row_num, 1,'%s' % pi.inscripcion.mi_coordinacion().nombre if pi.inscripcion.mi_coordinacion() else '',font_style2)
                        ws.write(row_num, 2, '%s' % pi.inscripcion.carrera.nombre if pi.inscripcion.carrera else '',font_style2)
                        ws.write(row_num, 3, '%s' % pi.inscripcion.mi_nivel() if pi.inscripcion.mi_nivel() else '',font_style2)
                        ws.write(row_num, 4, '%s' % pi.inscripcion.nivelperiodo(periodo).nivel.sesion.nombre if pi.inscripcion.nivelperiodo(periodo) else '', font_style2)
                        if pi.inscripcion.matricula_periodo(periodo):
                            ws.write(row_num, 5, '%s' % pi.inscripcion.matricula_periodo(
                                periodo).paralelo.nombre if pi.inscripcion.matricula_periodo(periodo).paralelo else '',
                                     font_style2)
                        else:
                            ws.write(row_num, 5, '%s' % '', font_style2)
                        ws.write(row_num, 6,'%s' % pi.inscripcion.persona.cedula if pi.inscripcion.persona.cedula else pi.inscripcion.persona.pasaporte, font_style2)
                        ws.write(row_num, 7,'%s' % pi.inscripcion.persona.nombre_completo_inverso() if pi.inscripcion.persona else '',font_style2)
                        ws.write(row_num, 8,'%s' % pi.inscripcion.persona.telefono if pi.inscripcion.persona.telefono else '',font_style2)
                        ws.write(row_num, 9,'%s' % pi.inscripcion.persona.telefono_conv if pi.inscripcion.persona.telefono_conv else '',font_style2)
                        ws.write(row_num, 10, '%s' % pi.preinscripcion.motivo if pi.preinscripcion.motivo else '',font_style2)
                        # ws.write(row_num, 9, '%s' % pi.inscripcion.persona.nombre_completo_inverso() if pi.inscripcion.persona else '', font_style2)
                        if pi.inscripcion.persona.sexo:
                            ws.write(row_num, 11,
                                     '%s' % "MASCULINO" if pi.inscripcion.persona.sexo.id == 2 else "FEMENINO",
                                     font_style2)
                        else:
                            ws.write(row_num, 11, 'NO TIENE SEXO', font_style2)
                        ws.write(row_num, 12,'%s' % pi.inscripcion.persona.email if pi.inscripcion.persona.email else "",font_style2)
                        ws.write(row_num, 13,'%s' % pi.inscripcion.persona.emailinst if pi.inscripcion.persona.emailinst else "",font_style2)
                        ws.write(row_num, 14,'%s' % pi.inscripcion.persona.pais,font_style2)
                        ws.write(row_num, 15,'%s' % pi.inscripcion.persona.provincia,font_style2)
                        ws.write(row_num, 16,'%s' % pi.inscripcion.persona.canton.nombre if pi.inscripcion.persona.canton else "",font_style2)
                        ws.write(row_num, 17,'%s' % pi.inscripcion.persona.parroquia,font_style2)
                        ws.write(row_num, 18,'%s' % pi.inscripcion.persona.direccion_corta(),font_style2)
                        ws.write(row_num, 19, '%s' % pi.itinerariomalla.nombre if pi.itinerariomalla else "",font_style2)
                        if pi.itinerariomalla:
                            ws.write(row_num, 20,'%s' % pi.itinerariomalla.horas_practicas if pi.itinerariomalla.horas_practicas else "",font_style2)
                        else:
                            ws.write(row_num, 20, '%s' % "", font_style2)
                        ws.write(row_num, 21, '%s' % pi.fecha if pi.fecha.strftime('%d-%m-%Y') else "", font_style2)
                        ws.write(row_num, 22, '%s' % pi.fecha if pi.fecha.strftime("%H:%M %p") else "", font_style2)
                        ws.write(row_num, 23, '%s' % pi.get_estado_display() if pi.estado else "", font_style2)
                        ws.write(row_num, 24,'%s' % pi.estado_estudiantes().get_estado_display() if pi.estado_estudiantes() else "",font_style2)
                        ws.write(row_num, 25, '%s' % pi.get_tipo_display() if pi.tipo else "", font_style2)
                        ws.write(row_num, 26, '%s' % pi.empresaempleadora.nombre if pi.empresaempleadora else "",font_style2)
                        ws.write(row_num, 27, '%s' % pi.otraempresaempleadora, font_style2)
                        ws.write(row_num, 28, '%s' % pi.departamento.nombre if pi.departamento else "", font_style2)
                        ws.write(row_num, 29, '%s' % pi.fechadesde.strftime('%d-%m-%Y') if pi.fechadesde else "",font_style2)
                        ws.write(row_num, 30, '%s' % pi.fechahasta.strftime('%d-%m-%Y') if pi.fechahasta else "",font_style2)
                        ws.write(row_num, 31, '%s' % pi.tutorunemi.persona.nombre_completo() if pi.tutorunemi else "",font_style2)
                        ws.write(row_num, 32, '%s' % pi.supervisor.persona.nombre_completo() if pi.supervisor else "",font_style2)
                        ws.write(row_num, 33, '%s' % pi.get_tipoinstitucion_display() if pi.tipoinstitucion else "",font_style2)
                        ws.write(row_num, 34, '%s' % pi.get_sectoreconomico_display() if pi.sectoreconomico else "",font_style2)
                        observacion1 = ""
                        if pi.detallerecoridopreinscripcionpracticaspp_set.filter(status=True, esestudiante=False):
                            observacion1 = pi.detallerecoridopreinscripcionpracticaspp_set.filter(status=True, esestudiante=False)[0].observacion
                        observacion2 = ""
                        if pi.detallerecoridopreinscripcionpracticaspp_set.filter(status=True, esestudiante=True):
                            observacion2 = pi.detallerecoridopreinscripcionpracticaspp_set.filter(status=True, esestudiante=True)[0].observacion
                        ws.write(row_num, 35, '%s' % observacion1 if observacion1 else "", font_style2)
                        ws.write(row_num, 36, '%s' % observacion2 if observacion2 else "", font_style2)
                        ws.write(row_num, 37, '%s' % pi.periodoppp.nombre if pi.periodoppp else "",font_style2)
                        col_num = 46
                        for preg in pre.preguntas():
                            if pre.detallerespuestapreinscripcionppp_set.filter(status=True,inscripcion=pi.inscripcion).exists():
                                detalle = pre.detallerespuestapreinscripcionppp_set.filter(status=True,inscripcion=pi.inscripcion)[0]
                                if detalle.respuesta.filter(pregunta=preg).exists():
                                    descripcion = detalle.respuesta.filter(pregunta=preg)[0].descripcion
                                    ws.write(row_num, col_num, '%s' % descripcion, font_style2)
                                    col_num = col_num + 1
                        if pi.archivo:
                            ws.write(row_num, 38, "SI", font_style2)
                        else:
                            ws.write(row_num, 38, "NO", font_style2)
                        if pi.fechaarchivo:
                            ws.write(row_num, 39, "{} {}".format(str(pi.fechaarchivo), pi.horaarchivo), font_style2)
                        else:
                            ws.write(row_num, 39, "NO", font_style2)
                        ws.write(row_num, 40, str(pi.fecha_creacion), font_style2)
                        recordacademico = ''
                        if Inscripcion.objects.filter(persona=pi.inscripcion.persona,
                                                      carrera=pi.inscripcion.carrera).exists():
                            recordacademico = Inscripcion.objects.filter(persona=pi.inscripcion.persona,
                                                                         carrera=pi.inscripcion.carrera).first().promedio_record()
                        ws.write(row_num, 41, recordacademico, font_style2)
                        tienediscapacidad = 'NO'
                        tipodiscapacidad = 'NINGUNA'
                        ppl = 'NO'
                        pplobs = 'NINIGUNA'
                        if pi.inscripcion.persona.tiene_discapasidad():
                            tienediscapacidad = 'SI'
                            if pi.inscripcion.persona.tiene_discapasidad().filter(tipodiscapacidad__isnull=False).exists():
                                tipodiscapacidad = pi.inscripcion.persona.tiene_discapasidad().first().tipodiscapacidad.nombre
                            else:
                                tipodiscapacidad = 'NO DETERMINADA'
                        ws.write(row_num, 42, tienediscapacidad, font_style2)
                        ws.write(row_num, 43, tipodiscapacidad, font_style2)
                        if pi.inscripcion.persona.ppl:
                            ppl = 'SI'
                            pplobs = pi.inscripcion.persona.observacionppl
                        ws.write(row_num, 44, ppl, font_style2)
                        ws.write(row_num, 45, pplobs, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar el reporte"})
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'estudiantes_asignados_excel':
            try:
                if 'id' in request.POST:
                    pre = PreInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
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
                    response['Content-Disposition'] = 'attachment; filename=Lista_inscritos_ppp' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CARRERA", 8000),
                        (u"DOCUMENTO", 3500),
                        (u"ESTUDIANTE", 12000),
                        (u"GÉNERO", 4000),
                        (u"EMAIL", 7000),
                        (u"EMAIL INSTITUCIONAL", 7000),
                        (u"PAIS", 4000),
                        (u"PROVINCIA", 4000),
                        (u"CANTON", 8000),
                        (u"PARROQUIA", 8000),
                        (u"DIRECCION DOMICILIARIA", 10000),
                        (u"ITINERARIO", 20000),
                        (u"HORAS", 3000),
                        (u"FECHA REGISTRO", 4000),
                        (u"ESTADO", 3000),
                        (u"EMPRESA", 12000),
                        (u"FECHA DESDE", 4000),
                        (u"FECHA HASTA", 4000),
                        (u"TUTOR UNEMI", 12000),
                        (u"SUPERVISOR UNEMI", 12000),
                        (u"PERIODO EVIDENCIA", 12000),
                        (u"RECORD ACADEMICO", 6000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    col_num = len(columns)

                    row_num = 4
                    for pi in pre.detallepreinscripcionpracticaspp_set.filter(status=True).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                                                                                                    'inscripcion__persona__nombres').distinct():
                        pp = pi.practicaspreprofesionalesinscripcion_set.filter(status=True).first()
                        ws.write(row_num, 0, '%s' % pi.inscripcion.carrera.nombre if pi.inscripcion.carrera else '',font_style2)
                        ws.write(row_num, 1,'%s' % pi.inscripcion.persona.cedula if pi.inscripcion.persona.cedula else pi.inscripcion.persona.pasaporte, font_style2)
                        ws.write(row_num, 2,'%s' % pi.inscripcion.persona.nombre_completo_inverso() if pi.inscripcion.persona else '',font_style2)
                        if pi.inscripcion.persona.sexo:
                            ws.write(row_num, 3, '%s' % "MASCULINO" if pi.inscripcion.persona.sexo.id == 2 else "FEMENINO", font_style2)
                        else:
                            ws.write(row_num, 3, 'NO TIENE SEXO', font_style2)
                        ws.write(row_num, 4, '%s' % pi.inscripcion.persona.email if pi.inscripcion.persona.email else "",font_style2)
                        ws.write(row_num, 5, '%s' % pi.inscripcion.persona.emailinst if pi.inscripcion.persona.emailinst else "",font_style2)
                        ws.write(row_num, 6, '%s' % pi.inscripcion.persona.pais,font_style2)
                        ws.write(row_num, 7, '%s' % pi.inscripcion.persona.provincia,font_style2)
                        ws.write(row_num, 8, '%s' % pi.inscripcion.persona.canton.nombre if pi.inscripcion.persona.canton else "",font_style2)
                        ws.write(row_num, 9, '%s' % pi.inscripcion.persona.parroquia,font_style2)
                        ws.write(row_num, 10, '%s' % pi.inscripcion.persona.direccion_corta(),font_style2)
                        ws.write(row_num, 11, '%s' % pi.itinerariomalla.nombre if pi.itinerariomalla else "",font_style2)
                        ws.write(row_num, 12, '%s' % pi.itinerariomalla.horas_practicas if pi.itinerariomalla and pi.itinerariomalla.horas_practicas else "",font_style2)
                        ws.write(row_num, 13, '%s' % pi.fecha if pi.fecha.strftime('%d-%m-%Y %H:%M:%S') else "", font_style2)
                        ws.write(row_num, 14, '%s' % pi.get_estado_display() if pi.estado else "", font_style2)
                        ws.write(row_num, 15, '%s' % pp.asignacionempresapractica.nombre if pp and pp.asignacionempresapractica else "",font_style2)
                        ws.write(row_num, 16, '%s' % pp.fechadesde.strftime('%d-%m-%Y') if pp and pp.fechadesde else "",font_style2)
                        ws.write(row_num, 17, '%s' % pp.fechahasta.strftime('%d-%m-%Y') if pp and pp.fechahasta else "",font_style2)
                        ws.write(row_num, 18, '%s' % pp.tutorunemi.persona.nombre_completo() if pp and pp.tutorunemi else "",font_style2)
                        ws.write(row_num, 19, '%s' % pp.supervisor.persona.nombre_completo() if pp and pp.supervisor else "",font_style2)
                        ws.write(row_num, 20, '%s' % pp.periodoppp.nombre if pp and pp.periodoppp else "",font_style2)
                        ws.write(row_num, 21, pi.inscripcion.promedio_record(), font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar el reporte"})
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'datospersonales_excel':
            try:
                if 'id' in request.POST:
                    pre = PreInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
                    inscripciones_ids = pre.detallepreinscripcionpracticaspp_set.values_list('inscripcion', flat=True).filter(status=True).order_by('inscripcion').distinct()
                    estudiantes = Inscripcion.objects.filter(pk__in=inscripciones_ids)
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
                    ws = wb.add_sheet('Datos personales')
                    ws.write_merge(0, 0, 0, 19, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write(1, 0, 'Total de estudiantes: %s' % estudiantes.count(), font_style)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Datos_personales_estudiantes' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"DOCUMENTO", 3000),
                        (u"ESTUDIANTE", 10000),
                        (u"F NACIMIENTO", 3000),
                        (u"CELULAR", 5000),
                        (u"CONVENCIONAL", 5000),
                        (u"GÉNERO", 5000),
                        (u"EMAIL", 10000),
                        (u"EMAIL INSTITUCIONAL", 10000),
                        (u"PAIS", 5000),
                        (u"PROVINCIA", 6000),
                        (u"CANTON", 6000),
                        (u"PARROQUIA", 6000),
                        (u"DIRECCION DOMICILIARIA", 15000),
                        (u"RECORD ACADEMICO", 5500),
                        (u"¿TIENE DISCAPACIDAD?", 6000),
                        (u"¿TIPO DISCAPACIDAD?", 10000),
                        (u"¿PPL?", 2000),
                        (u"DETALLE PPL", 10000),
                        (u"CARRERA", 15000),
                        (u"NIVEL", 3000),
                        (u"JORNADA", 5000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 4
                    for insc in estudiantes:
                        ws.write(row_num, 0, '%s' % insc.persona.cedula if insc.persona.cedula else insc.persona.pasaporte, font_style2)
                        ws.write(row_num, 1, '%s' % insc.persona.nombre_completo_inverso() if insc.persona else '', font_style2)
                        ws.write(row_num, 2, '%s' % insc.persona.nacimiento.strftime("%d-%m-%Y") if insc.persona and insc.persona.nacimiento else '', font_style2)
                        ws.write(row_num, 3, '%s' % insc.persona.telefono if insc.persona.telefono else '', font_style2)
                        ws.write(row_num, 4, '%s' % insc.persona.telefono_conv if insc.persona.telefono_conv else '', font_style2)
                        if insc.persona.sexo: ws.write(row_num, 5, '%s' % "MASCULINO" if insc.persona.sexo.id == 2 else "FEMENINO", font_style2)
                        else: ws.write(row_num, 5, 'NO TIENE SEXO', font_style2)
                        ws.write(row_num, 6, '%s' % insc.persona.email if insc.persona.email else "", font_style2)
                        ws.write(row_num, 7, '%s' % insc.persona.emailinst if insc.persona.emailinst else "", font_style2)
                        ws.write(row_num, 8, '%s' % insc.persona.pais, font_style2)
                        ws.write(row_num, 9, '%s' % insc.persona.provincia, font_style2)
                        ws.write(row_num, 10, '%s' % insc.persona.canton.nombre if insc.persona.canton else "", font_style2)
                        ws.write(row_num, 11, '%s' % insc.persona.parroquia, font_style2)
                        ws.write(row_num, 12, '%s' % insc.persona.direccion_corta(), font_style2)
                        ws.write(row_num, 13, insc.promedio_record(), font_style2)
                        tienediscapacidad = 'NO'
                        tipodiscapacidad = 'NINGUNA'
                        ppl = 'NO'
                        pplobs = 'NINIGUNA'
                        if insc.persona.tiene_discapasidad():
                            tienediscapacidad = 'SI'
                            if insc.persona.tiene_discapasidad().filter(tipodiscapacidad__isnull=False).exists():
                                tipodiscapacidad = insc.persona.tiene_discapasidad().first().tipodiscapacidad.nombre
                            else:
                                tipodiscapacidad = 'NO DETERMINADA'
                        ws.write(row_num, 14, tienediscapacidad, font_style2)
                        ws.write(row_num, 15, tipodiscapacidad, font_style2)
                        if insc.persona.ppl:
                            ppl = 'SI'
                            pplobs = insc.persona.observacionppl
                        ws.write(row_num, 16, ppl, font_style2)
                        ws.write(row_num, 17, pplobs, font_style2)
                        ws.write(row_num, 18, '%s' % insc.carrera.nombre if insc.carrera else '', font_style2)
                        ws.write(row_num, 19, '%s' % insc.mi_nivel() if insc.mi_nivel() else '', font_style2)
                        ws.write(row_num, 20, '%s' % insc.nivelperiodo(periodo).nivel.sesion.nombre if insc.nivelperiodo(periodo) else '', font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar el reporte"})
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delpreinscripcion':
            try:
                detalle = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                if detalle:
                    #excluir el itinerario para la selecion de los demas estudiantes
                    turno = None
                    if orden := detalle.inscripcion.ordenprioridadinscripcion_set.first():
                        grupoorden = detalle.preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first().grupoorden if detalle.preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first() else None
                        if grupoorden:
                            if turno := orden.obtenerturnoinscripcion(grupoorden, detalle.preinscripcion):
                                orden.excluirdato += str(detalle.itinerariomalla.id) + ','
                                orden.save(request)
                                if not DetallePreInscripcionPracticasPP.objects.filter(preinscripcion=detalle.preinscripcion, inscripcion=detalle.inscripcion, status=True).exclude(pk=detalle.id).exists():
                                    orden.status = False
                                    orden.save(request)

                    if detalle.puede_eliminar_todo(detalle.inscripcion):
                        respuestas = DetalleRespuestaPreInscripcionPPP.objects.filter(inscripcion=detalle.inscripcion,
                                                                                      preinscripcion=detalle.preinscripcion)
                        if respuestas:
                            for r in respuestas:
                                r.delete()
                        detalle.delete()
                    else:
                        detalle.delete()
                    log(u'Eliminó la pre-inscripción de practicas preprofesionales: %s' % detalle, request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'gestionar_preins_ind':
            try:
                form = PracticasPreprofesionalesInscripcionSaludForm(request.POST)
                preins = DetallePreInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
                confippp = int(request.POST['confippp']) if ('confippp' in request.POST and request.POST['confippp']) else None
                tutorunemi = int(request.POST['tutorunemi']) if ('tutorunemi' in request.POST and request.POST['tutorunemi']) else None
                asignacionempresapractica = request.POST.get('asignacionempresapractica', None)
                periodoevidencia = request.POST['periodoevidencia'] if ('periodoevidencia' in request.POST and request.POST['periodoevidencia']) else None
                if not asignacionempresapractica:
                    asignacionempresapractica = None
                    form.fields['asignacionempresapractica'].required = False
                    if not len(request.POST.get('otraempresaempleadora', '')) > 1:
                        if int(request.POST['estadopreinscripcion']) == 2:
                            raise NameError(u'Debe seleccionar o ingresar una Empresa.')
                        else:
                            form.ocultarcampos()
                itinerario = preins.itinerariomalla.id if preins.itinerariomalla else None
                form.init(itinerario, tutorunemi, asignacionempresapractica, periodoevidencia, confippp)
                if form.is_valid():
                    # preins = DetallePreInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
                    # if 'archivo' in request.FILES:
                    #     arch = request.FILES['archivo']
                    #     extension = arch._name.split('.')
                    #     tam = len(extension)
                    #     exte = extension[tam - 1]
                    #     if arch.size > 4194304:
                    #         transaction.set_rollback(True)
                    #         return JsonResponse(
                    #             {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    #     if not exte.lower() == 'pdf':
                    #         transaction.set_rollback(True)
                    #         return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                    #     preins.archivo = arch
                    #     preins.fechaarchivo = datetime.now().date()
                    #     preins.horaarchivo = datetime.now().time()
                    #     preins.save(request)
                    if int(form.cleaned_data['estadopreinscripcion']) == 2:
                        preins.tipo = 4
                        # preins.tipo = form.cleaned_data['tipo']
                        preins.fechadesde = form.cleaned_data['fechadesde']
                        # preins.nivelmalla = form.cleaned_data['nivelmalla']
                        preins.nivelmalla = preins.inscripcion.mi_nivel().nivel
                        # preins.itinerariomalla = form.cleaned_data['itinerario']
                        preins.itinerariomalla.id = itinerario
                        preins.fechahasta = form.cleaned_data['fechahasta']
                        # preins.empresaempleadora_id = int(request.POST['empresaempleadora']) if form.cleaned_data['empresaempleadora'] else None
                        preins.empresaempleadora_id = None
                        preins.otraempresaempleadora = form.cleaned_data['otraempresaempleadora']
                        preins.tutorunemi_id = int(request.POST['tutorunemi']) if form.cleaned_data['tutorunemi'] else None
                        preins.supervisor_id = int(request.POST['supervisor']) if form.cleaned_data['supervisor'] else None
                        preins.numerohora = form.cleaned_data['numerohora']
                        preins.tipoinstitucion = form.cleaned_data['tipoinstitucion']
                        # preins.sectoreconomico = form.cleaned_data['sectoreconomico']
                        preins.sectoreconomico = 5
                        # preins.departamento = form.cleaned_data['departamento']
                        preins.departamento_id = 41
                        preins.periodoppp = form.cleaned_data['periodoevidencia']
                        preins.convenio = int(form.cleaned_data['convenio']) if form.cleaned_data['convenio'] and int(form.cleaned_data['convenio']) > 0 else None
                        preins.lugarpractica = form.cleaned_data['lugarpractica']
                        # preins.acuerdo = form.cleaned_data['acuerdo']
                        preins.acuerdo = None
                        preins.save(request)
                        if preins.recorrido():
                            if not preins.recorrido().estado == int(form.cleaned_data['estadopreinscripcion']):
                                recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                     fecha=datetime.now().date(),
                                                                                     observacion=form.cleaned_data['observacion'],
                                                                                     # observacion='Asignación de pre inscripión',
                                                                                     estado=form.cleaned_data['estadopreinscripcion'])
                            else:
                                recorrido = preins.recorrido()
                                recorrido.observacion = form.cleaned_data['observacion']
                                # recorrido.observacion = 'Asignación de pre inscripión'
                            recorrido.save(request)
                        else:
                            recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                 fecha=datetime.now().date(),
                                                                                 observacion=form.cleaned_data['observacion'],
                                                                                 # observacion='Asignación de pre inscripión',
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
                                                                      convenio_id=preins.convenio,
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
                                                                      # observacion='Estudiante Asignado',
                                                                      estadosolicitud=2,
                                                                      fechaasigsupervisor=datetime.now().date())
                        practa.save(request)
                        log(u'El estudiante %s acepto la asignacion de práctica preprofesionales a la empresa: %s' % (
                            preins.inscripcion,
                            preins.empresaempleadora if preins.empresaempleadora else preins.otraempresaempleadora),
                            request,
                            "add")

                        turno = None
                        if orden := preins.inscripcion.ordenprioridadinscripcion_set.first():
                           grupoorden = preins.preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first().grupoorden if preins.preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first() else None
                           if grupoorden:
                               turno = orden.obtenerturnoinscripcion(grupoorden, preins.preinscripcion)

                        configuracionoferta = form.cleaned_data['confippp']
                        if configuracionoferta:
                            # Relaciona datos adicionales para la tabla PracticasPreprofesionalesInscripcion
                            practaexten = PracticasPreprofesionalesInscripcionExtensionSalud(practicasppinscripcion=practa, dia=configuracionoferta.dia, configinscppp=configuracionoferta, responsable=configuracionoferta.responsable)
                            practaexten.save(request)
                            # Almacena historial de inscritos en la oferta
                            historialinscripcionoferta = HistorialInscricionOferta(configinscppp=configuracionoferta, practicasppinscripcion=practa, fecha=datetime.now().date())
                            historialinscripcionoferta.save(request)
                            if turno:
                                historialinscripcionoferta.ordenprioridad = turno
                            historialinscripcionoferta.save(request)

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
                                                                                     observacion=form.cleaned_data['observacion'],
                                                                                     # observacion='Estado de la Pre-inscripción',
                                                                                     estado=form.cleaned_data['estadopreinscripcion'])
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
                                                                                 observacion=form.cleaned_data['observacion'],
                                                                                 # observacion='Estado de la Pre-inscripción',
                                                                                 estado=form.cleaned_data['estadopreinscripcion'])
                            recorrido.save(request)
                            if int(form.cleaned_data['estadopreinscripcion']) == 3:
                                log(u'Rechazo la pre-inscripción: %s' % preins, request, "rech")
                            log(u'La puso pendiente la pre-inscripción: %s' % preins, request, "pend")
                    preins.estado = int(form.cleaned_data['estadopreinscripcion'])
                    preins.save(request)
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

        if action == 'gestionar_preins_masivo':
            try:
                form = PracticasPreprofesionalesInscripcionMasivoEstudianteSaludForm(request.POST)
                tutorunemi = int(request.POST['tutorunemi']) if ('tutorunemi' in request.POST and request.POST['tutorunemi']) else None
                confippp = int(request.POST['confippp']) if ('confippp' in request.POST and request.POST['confippp']) else None
                asignacionempresapractica = request.POST.get('asignacionempresapractica', None)
                periodoevidencia = request.POST['periodoevidencia'] if ('periodoevidencia' in request.POST and request.POST['periodoevidencia']) else None
                itinerario = int(request.POST['itinerario']) if ('itinerario' in request.POST and request.POST['itinerario']) else None
                lugarpractica = int(request.POST['lugarpractica']) if ('lugarpractica' in request.POST and request.POST['lugarpractica']) else None
                if not asignacionempresapractica:
                    asignacionempresapractica = None
                    form.fields['asignacionempresapractica'].required = False
                    if not len(request.POST.get('otraempresaempleadora', '')) > 1:
                        if int(request.POST['estadopreinscripcion']) == 2:
                            raise NameError(u'Debe seleccionar o ingresar una Empresa.')
                        else:
                            form.ocultarcampos()
                # form.init(itinerario, tutorunemi, asignacionempresapractica, periodoevidencia)
                form.init(request.POST['carrera'], itinerario, request.POST.getlist('inscripciones'), tutorunemi,
                          lugarpractica, asignacionempresapractica, periodoevidencia, confippp)
                if form.is_valid():
                    periodopractica = PreInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
                    idinscritos = request.POST.getlist('inscripciones')
                    configuracionoferta = form.cleaned_data['confippp']
                    if configuracionoferta and len(idinscritos) > configuracionoferta.cupos_disponibles():
                        raise NameError(f"No existen cupos disponibles para el total de estudiantes seleccionados. Cupos disponibles: {configuracionoferta.cupos_disponibles()}; Total estudiantes: {len(idinscritos)}")
                    cabmasivo = PreinscribirMasivoHistorial(preinscripcion=periodopractica)
                    cabmasivo.save()
                    for idin in idinscritos:
                        preins = DetallePreInscripcionPracticasPP.objects.get(status=True, pk=int(idin))
                        cabmasivo.inscripcion.add(preins)
                        if int(form.cleaned_data['estadopreinscripcion']) == 2:
                            preins.tipo = 4
                            preins.fechadesde = form.cleaned_data['fechadesde']
                            preins.nivelmalla = preins.inscripcion.mi_nivel().nivel
                            preins.itinerariomalla = form.cleaned_data['itinerario']
                            preins.fechahasta = form.cleaned_data['fechahasta']
                            preins.empresaempleadora_id = None
                            preins.otraempresaempleadora = form.cleaned_data['otraempresaempleadora']
                            preins.tutorunemi_id = int(request.POST['tutorunemi']) if form.cleaned_data['tutorunemi'] else None
                            preins.supervisor_id = int(request.POST['supervisor']) if form.cleaned_data['supervisor'] else None
                            preins.numerohora = form.cleaned_data['numerohora']
                            preins.tipoinstitucion = form.cleaned_data['tipoinstitucion']
                            preins.sectoreconomico = 5
                            preins.departamento_id = 41
                            preins.periodoppp = form.cleaned_data['periodoevidencia']
                            preins.convenio = int(form.cleaned_data['convenio']) if form.cleaned_data['convenio'] and int(form.cleaned_data['convenio']) > 0 else None
                            preins.lugarpractica = form.cleaned_data['lugarpractica']
                            preins.acuerdo = None
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
                                                                          acuerdo_id=preins.acuerdo,
                                                                          convenio_id=preins.convenio,
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

                            turno = None
                            if orden := preins.inscripcion.ordenprioridadinscripcion_set.first():
                                grupoorden = preins.preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first().grupoorden if preins.preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first() else None
                                if grupoorden:
                                    turno = orden.obtenerturnoinscripcion(grupoorden, preins.preinscripcion)

                            configuracionoferta = form.cleaned_data['confippp']
                            if configuracionoferta:
                                # Relaciona datos adicionales para la tabla PracticasPreprofesionalesInscripcion
                                practaexten = PracticasPreprofesionalesInscripcionExtensionSalud(practicasppinscripcion=practa, dia=configuracionoferta.dia, configinscppp=configuracionoferta, responsable=configuracionoferta.responsable)
                                practaexten.save(request)
                                # Almacena historial de inscritos en la oferta
                                historialinscripcionoferta = HistorialInscricionOferta(configinscppp=configuracionoferta, practicasppinscripcion=practa, fecha=datetime.now().date())
                                historialinscripcionoferta.save(request)
                                if turno:
                                    historialinscripcionoferta.ordenprioridad = turno
                                historialinscripcionoferta.save(request)

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
                return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {str(ex)}."})

        if action == 'gestionar_tipo_masivo':
            try:
                tipo = int(request.POST.get('tipo', 0))
                textotipo = ''
                form = AsignacionMasivoSaludForm(request.POST)
                form.init(request.POST['carrera'], request.POST['itinerario'], request.POST.getlist('inscripciones'))
                form.asignarmasivo(tipo)
                if form.is_valid():
                    periodopractica = PreInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
                    idinscritos = request.POST.getlist('inscripciones')

                    for idin in idinscritos:
                        preins = DetallePreInscripcionPracticasPP.objects.get(status=True, pk=int(idin))
                        estudiante = preins.inscripcion.persona.nombre_completo_inverso()
                        practa = preins.practicaspreprofesionalesinscripcion_set.filter(status=True).first()
                        if practa or preins:
                            if 'supervisor' in form.cleaned_data and form.cleaned_data['supervisor']:
                                textotipo = 'Supervisor'
                                idprof = int(form.cleaned_data['supervisor'])
                                profesor1 = Profesor.objects.get(pk=idprof)
                                preins.supervisor = profesor1
                                preins.save(request)
                                if practa:
                                    practa.supervisor = profesor1
                                    practa.fechaasigsupervisor = datetime.now().date()
                                    practa.save(request)
                                #notificacion
                                asunto = u"ASIGNACIÓN SUPERVISOR ACADÉMICO PRÁCTICAS PREPROFESIONALES "
                                para = profesor1.persona
                                observacion = 'Se le comunica que ha sido designado como supervisor académico del estudiante: {} de la carrera: {}'.format(
                                    estudiante, preins.inscripcion.carrera)
                                notificacion(asunto, observacion, para, None, '/pro_cronograma?action=listasupervision',
                                             preins.pk, 1, 'sga', DetallePreInscripcionPracticasPP, request)

                            if 'tutorunemi' in form.cleaned_data and form.cleaned_data['tutorunemi']:
                                textotipo = 'Tutor'
                                idprof = int(form.cleaned_data['tutorunemi'])
                                profesor1 = Profesor.objects.get(pk=idprof)
                                preins.tutorunemi = profesor1
                                preins.save(request)
                                if practa:
                                    practa.tutorunemi = profesor1
                                    practa.fechaasigtutor = datetime.now().date()
                                    practa. save(request)
                                #notificacion
                                asunto = u"ASIGNACIÓN TUTOR ACADÉMICO PRÁCTICAS PREPROFESIONALES "
                                para = profesor1.persona
                                observacion = 'Se le comunica que ha sido designado como tutor académico del estudiante: {} de la carrera: {}'.format(
                                    estudiante, preins.inscripcion.carrera)
                                notificacion(asunto, observacion, para, None, '/pro_cronograma?action=listatutorias',
                                             preins.pk, 1, 'sga', DetallePreInscripcionPracticasPP, request)

                            if 'responsable' in form.cleaned_data and form.cleaned_data['responsable']:
                                textotipo = 'Responsable centro salud'
                                responsable = form.cleaned_data['responsable']
                                if practa:
                                    practaext = practa.practicaspreprofesionalesinscripcionextensionsalud_set.filter(status=True).first()
                                    if practaext:
                                        practaext.responsable = responsable
                                        practaext.fechaasigresponsable = datetime.now().date()
                                        practaext.save(request)
                                        #notificacion
                                        asunto = u"ASIGNACIÓN RESPONSABLE CENTRO SALUD PRÁCTICAS PREPROFESIONALES "
                                        para = responsable.persona
                                        observacion = 'Se le comunica que ha sido designado como responsable de centro se salud del estudiante: {} de la carrera: {}'.format(
                                            estudiante, preins.inscripcion.carrera)
                                        notificacion(asunto, observacion, para, None, '/pro_cronograma?action=listasupervision',
                                                     preins.pk, 1, 'sga', DetallePreInscripcionPracticasPP, request)

                            log(u'Se asignó %s al estudiante %s en proceso masivo' % (textotipo, preins.inscripcion), request, "edit")
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

        elif action == 'addconfiginscripcion':
            try:
                with transaction.atomic():
                    preins = PreInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
                    tutorunemi = int(request.POST['tutorunemi']) if ('tutorunemi' in request.POST and request.POST['tutorunemi']) else None
                    supervisor = int(request.POST['supervisor']) if ('supervisor' in request.POST and request.POST['supervisor'] != '' and int(request.POST['supervisor']) > 0) else None
                    convenio = int(request.POST['convenio']) if ('convenio' in request.POST and request.POST['convenio'] != '' and int(request.POST['convenio']) > 0) else None
                    carreras = request.POST.getlist('carrera')
                    itinerarios = request.POST.getlist('itinerariomalla')
                    form = ConfiguracionInscripcionPracticasPPForm(request.POST, request.FILES)
                    form.init(carreras, itinerarios, tutorunemi, request.POST['asignacionempresapractica'], request.POST['periodoevidencia'])
                    if form.is_valid():
                        configuracion = ConfiguracionInscripcionPracticasPP(preinscripcion=preins,
                                                                            # itinerariomalla=form.cleaned_data['itinerariomalla'],
                                                                            # tipo=form.cleaned_data['tipo'],
                                                                            fechainicio=form.cleaned_data['fechainicio'],
                                                                            fechafin=form.cleaned_data['fechafin'],
                                                                            tutorunemi=form.cleaned_data['tutorunemi'],
                                                                            supervisor_id=supervisor,
                                                                            numerohora=form.cleaned_data['numerohora'],
                                                                            cupo=form.cleaned_data['cupo'],
                                                                            # acuerdo_id=acuerdo,
                                                                            convenio_id=convenio,
                                                                            tipoinstitucion=form.cleaned_data['tipoinstitucion'],
                                                                            asignacionempresapractica=form.cleaned_data['asignacionempresapractica'],
                                                                            # empresaempleadora=form.cleaned_data['empresaempleadora'] if request.POST['empresaempleadora'] else None,
                                                                            # otraempresaempleadora=form.cleaned_data['otraempresaempleadora'],
                                                                            lugarpractica=form.cleaned_data['lugarpractica'],
                                                                            responsable=form.cleaned_data['responsable'],
                                                                            dia=form.cleaned_data['dia'],
                                                                            # sectoreconomico=5,  # SERVICIOS
                                                                            # departamento_id=41,  # FACULTAD CIENCIAS DE LA SALUD (FACS)
                                                                            periodoppp=form.cleaned_data['periodoevidencia'],
                                                                            # observacion=form.cleaned_data['observacion'],
                                                                            fechainiciooferta=form.cleaned_data['fechainiciooferta'],
                                                                            fechafinoferta=form.cleaned_data['fechafinoferta'],
                                                                            estado=2
                                                                            )
                        configuracion.save(request)
                        for iti in itinerarios:
                            configuracion.itinerariomalla.add(iti)
                        configuracion.save(request)

                        if not configuracion.asignacionempresapractica.canton and configuracion.lugarpractica:
                            empresa = configuracion.asignacionempresapractica
                            empresa.canton = configuracion.lugarpractica
                            empresa.save()

                        log(u'Adicionó Configuración de oferta para prácticas pre profesionales salud : %s' % (configuracion), request, "add")
                        messages.success(request, 'Registro guardado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'addresponsable':
            try:
                with transaction.atomic():
                    f = ResponsableCentroSaludForm(request.POST)
                    cedula, pasaporte = '',''
                    if int(request.POST['habilita']) == 0:
                        f.habilita(False)
                    if f.is_valid():
                        identificacion = f.cleaned_data['identificacion'].upper().strip()
                        pers = consultarPersona(identificacion)
                        if int(f.cleaned_data['tipoidentificacion']) == 1:
                            cedula = identificacion
                        else:
                            pasaporte = identificacion
                        if not pers:
                            pers = Persona(cedula=cedula,
                                           pasaporte=pasaporte,
                                           nombres=f.cleaned_data['nombre'],
                                           apellido1=f.cleaned_data['apellido1'],
                                           apellido2=f.cleaned_data['apellido2'],
                                           nacimiento=f.cleaned_data['nacimiento'],
                                           telefono=f.cleaned_data['telefono'],
                                           sexo=f.cleaned_data['sexo'],
                                           email=f.cleaned_data['email'],
                                           telefono_conv=f.cleaned_data['telefono_conv'],
                                           )
                            pers.save(request)
                            log(u'Adiciono persona: %s' % persona, request, "add")
                        else:
                            pers.telefono = f.cleaned_data['telefono']
                            pers.telefono_conv = f.cleaned_data['telefono_conv']
                            pers.email = f.cleaned_data['email']
                            pers.save(request)
                            log(u'Edito persona de usuario: %s' % pers, request, "edit")
                        if f.cleaned_data['generaperfil'] and not pers.tiene_usuario_externo():
                            externo = Externo.objects.filter(persona=pers, status=True).first()
                            if not externo:
                                externo = Externo(persona=pers)
                                externo.save(request)
                                log(u'Adiciono externo: %s' % externo, request, "add")
                            perfil = PerfilUsuario(persona=pers, externo=externo)
                            perfil.save(request)
                            log(u'Adiciono perfil de usuario externo: %s' % perfil, request, "add")
                        if not ResponsableCentroSalud.objects.filter(persona=pers, status=True).exists():
                            responsable = ResponsableCentroSalud(persona=pers,
                                                                 asignacionempresapractica=f.cleaned_data['asignacionempresapractica'],
                                                                 # otraempresaempleadora=f.cleaned_data['otraempresaempleadora'],
                                                                 cargodesempena=f.cleaned_data['cargo'],
                                                                 telefonooficina=f.cleaned_data['telefono_ofi'])
                            responsable.save(request)
                        log(u'Adicionó responsable prácticas pre profesionales salud : %s' % (responsable), request, "add")
                        messages.success(request, 'Registro guardado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'editresponsable':
            try:
                with transaction.atomic():
                    f = ResponsableCentroSaludForm(request.POST)
                    f.habilita(False)
                    f.habilita2()
                    responsable = ResponsableCentroSalud.objects.get(pk=int(request.POST['id']))
                    pers = responsable.persona
                    if f.is_valid():
                        pers.telefono = f.cleaned_data['telefono']
                        pers.telefono_conv = f.cleaned_data['telefono_conv']
                        pers.email = f.cleaned_data['email']
                        pers.save(request)
                        log(u'Edito persona de usuario: %s' % pers, request, "edit")

                        responsable.asignacionempresapractica = f.cleaned_data['asignacionempresapractica']
                        # responsable.otraempresaempleadora = f.cleaned_data['otraempresaempleadora']
                        responsable.cargodesempena = f.cleaned_data['cargo']
                        responsable.telefonooficina = f.cleaned_data['telefono_ofi']
                        responsable.save(request)
                        log(u'Editó responsable prácticas pre profesionales salud : %s' % (responsable), request, "edit")

                        if f.cleaned_data['generaperfil'] and not pers.tiene_usuario_externo():
                            externo = Externo.objects.filter(persona=pers, status=True).first()
                            if not externo:
                                externo = Externo(persona=pers)
                                externo.save(request)
                                log(u'Adiciono externo: %s' % externo, request, "add")
                            perfil = PerfilUsuario(persona=pers, externo=externo)
                            perfil.save(request)
                            log(u'Adicionó perfil de usuario externo: %s' % perfil, request, "add")

                        messages.success(request, 'Registro editado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'crearperfilexterno':
            try:
                responsable = ResponsableCentroSalud.objects.get(pk=int(request.POST['id']))
                pers = responsable.persona
                if not responsable.persona.tiene_usuario_externo():
                    externo = Externo.objects.filter(persona=pers, status=True).first()
                    if not externo:
                        externo = Externo(persona=pers)
                        externo.save(request)
                        log(u'Adiciono externo: %s' % externo, request, "add")
                    perfil = PerfilUsuario(persona=pers, externo=externo)
                    perfil.save(request)
                    log(u'Adicionó perfil de usuario externo: %s' % perfil, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": f"{pers.nombre_invertido} ya cuenta con un perfil externo creado."})
            except Exception as ex:
                print(u'Error on line %s: %s'%(format(sys.exc_info()[-1].tb_lineno), ex))
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {str(ex)}"})

        elif action == 'delresponsable':
            try:
                responsable = ResponsableCentroSalud.objects.get(pk=int(request.POST['id']))
                responsable.status = False
                responsable.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                print(u'Error on line %s: %s'%(format(sys.exc_info()[-1].tb_lineno), ex))
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {str(ex)}"})

        elif action == 'editconfiginscripcion':
            try:
                with transaction.atomic():
                    form = ConfiguracionInscripcionPracticasPPForm(request.POST, request.FILES)
                    configuracion = ConfiguracionInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['idconfig']))
                    tutorunemi = int(request.POST['tutorunemi']) if ('tutorunemi' in request.POST and request.POST['tutorunemi']) else None
                    supervisor = int(request.POST['supervisor']) if ('supervisor' in request.POST and request.POST['supervisor'] != '' and int(request.POST['supervisor']) > 0) else None
                    convenio = int(request.POST['convenio']) if ('convenio' in request.POST and request.POST['convenio'] != '' and int(request.POST['convenio']) > 0) else None
                    asignacionempresapractica = request.POST.get('asignacionempresapractica', None)
                    eItinerarios = request.POST.getlist('itinerariomalla') if not configuracion.itinerariomalla.all() else configuracion.itinerariomalla.all()
                    eCarreras = request.POST.getlist('carrera') if not configuracion.itinerariomalla.all() else eItinerarios.values_list('malla__carrera_id')
                    form.init(eCarreras, eItinerarios, tutorunemi, asignacionempresapractica, request.POST['periodoevidencia'])
                    form.bloqueo()
                    if form.is_valid():
                        # configuracion.tipo = form.cleaned_data['tipo']
                        configuracion.fechainicio = form.cleaned_data['fechainicio']
                        configuracion.fechafin = form.cleaned_data['fechafin']
                        configuracion.tutorunemi = form.cleaned_data['tutorunemi']
                        configuracion.responsable = form.cleaned_data['responsable']
                        configuracion.supervisor_id = supervisor
                        configuracion.numerohora = form.cleaned_data['numerohora']
                        configuracion.cupo = form.cleaned_data['cupo']
                        # configuracion.acuerdo_id = acuerdo
                        configuracion.convenio_id = convenio
                        configuracion.tipoinstitucion = form.cleaned_data['tipoinstitucion']
                        configuracion.asignacionempresapractica = form.cleaned_data['asignacionempresapractica']
                        # configuracion.empresaempleadora = form.cleaned_data['empresaempleadora'] if request.POST['empresaempleadora'] else None
                        # configuracion.otraempresaempleadora = form.cleaned_data['otraempresaempleadora']
                        configuracion.lugarpractica = form.cleaned_data['lugarpractica']
                        configuracion.periodoppp = form.cleaned_data['periodoevidencia']
                        configuracion.dia = form.cleaned_data['dia']
                        configuracion.fechainiciooferta = form.cleaned_data['fechainiciooferta']
                        configuracion.fechafinoferta = form.cleaned_data['fechafinoferta']
                        if request.POST.getlist('itinerariomalla'):
                            configuracion.itinerariomalla.clear()
                            for iti in request.POST.getlist('itinerariomalla'):
                                configuracion.itinerariomalla.add(iti)
                        configuracion.save(request)
                        log(u'Editó Configuración de oferta para prácticas pre profesionales salud : %s' % (configuracion), request, "edit")
                        messages.success(request, 'Registro editado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'delconfiginscripcion':
            try:
                configuracion = ConfiguracionInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
                configuracion.status = False
                configuracion.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                print(u'Error on line %s: %s'%(format(sys.exc_info()[-1].tb_lineno), ex))
                # print(ex)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {str(ex)}"})

        elif action == 'duplicarconfiguracionoferta':
            try:
                conf = ConfiguracionInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
                configduplica = ConfiguracionInscripcionPracticasPP(preinscripcion=conf.preinscripcion,
                                                                    # itinerariomalla=conf.itinerariomalla,
                                                                    fechainicio=conf.fechainicio,
                                                                    fechafin=conf.fechafin,
                                                                    tutorunemi=conf.tutorunemi,
                                                                    supervisor=conf.supervisor,
                                                                    numerohora=conf.numerohora,
                                                                    cupo=0,
                                                                    convenio=conf.convenio,
                                                                    tipoinstitucion=conf.tipoinstitucion,
                                                                    asignacionempresapractica=conf.asignacionempresapractica,
                                                                    # otraempresaempleadora=conf.otraempresaempleadora,
                                                                    lugarpractica=conf.lugarpractica,
                                                                    responsable=conf.responsable,
                                                                    dia=conf.dia,
                                                                    periodoppp=conf.periodoppp,
                                                                    fechainiciooferta=conf.fechainiciooferta,
                                                                    fechafinoferta=conf.fechafinoferta,
                                                                    estado=conf.estado
                                                                    )
                configduplica.save(request)
                for i in conf.itinerariomalla.all():
                    configduplica.itinerariomalla.add(i)
                configduplica.save(request)
                log(u'Duplicó la configuración de oferta para prácticas pre profesionales salud : %s' % (configduplica), request, "add")
                messages.success(request, 'Registro guardado con éxito.')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                print(u'Error on line %s: %s'%(format(sys.exc_info()[-1].tb_lineno), ex))
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {str(ex)}"})

        elif action == 'actualizarestado':
            try:
                with transaction.atomic():
                    form = ActualizaConfiguracionInscripcionPracticasPPForm(request.POST)
                    configuracion = ConfiguracionInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['idconfig']))
                    if form.is_valid():
                        configuracion.estado = form.cleaned_data['estado']
                        configuracion.save(request)
                        # configuracion.fechainiciooferta = form.cleaned_data['fechainiciooferta']
                        # configuracion.fechafinoferta = form.cleaned_data['fechafinoferta']
                        # configuracion.save(request)
                        # if form.cleaned_data['fechainiciooferta'] and form.cleaned_data['fechafinoferta']:
                        #     configuracion.estado = 2 if form.cleaned_data['fechainiciooferta'] <= hoy <= form.cleaned_data['fechafinoferta'] else 3
                        #     configuracion.save(request)
                        # log(u'Editó Configuración de oferta para prácticas pre profesionales salud : %s' % (configuracion), request, "edit")
                        log(u'Editó estado onfiguración de oferta para prácticas pre profesionales salud : %s' % (configuracion), request, "edit")
                        messages.success(request, 'Registro actualizado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'fechasconvocatoria':
            try:
                with transaction.atomic():
                    form = FechasConvocatoriaPPPForm(request.POST)
                    pre = PreInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['id']))
                    form.init(request.POST['periodoevidencia'])
                    if form.is_valid():
                        if extconf := pre.extpreinscripcionpracticaspp_set.filter(status=True).first():
                            extconf.finiciopractica = form.cleaned_data['finiciopractica']
                            extconf.ffinpractica = form.cleaned_data['ffinpractica']
                            extconf.finicioconvocatoria = form.cleaned_data['finicioconvocatoria']
                            extconf.ffinconvocatoria = form.cleaned_data['ffinconvocatoria']
                            extconf.periodoevidencia = form.cleaned_data['periodoevidencia']
                        else:
                            extconf = ExtPreInscripcionPracticasPP(preinscripcion=pre,
                                                                   finiciopractica= form.cleaned_data['finiciopractica'],
                                                                   ffinpractica= form.cleaned_data['ffinpractica'],
                                                                   finicioconvocatoria= form.cleaned_data['finicioconvocatoria'],
                                                                   ffinconvocatoria=form.cleaned_data['ffinconvocatoria'],
                                                                   periodoevidencia=form.cleaned_data['periodoevidencia']
                                                                   )
                        extconf.save(request)
                        log(u'Editó fechas convocatoria ppp salud : %s' % (extconf), request, "edit")
                        messages.success(request, 'Registro actualizado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'detalleobservacion':
            try:
                data['pre'] = pre = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                data['detalles'] = pre.detallerecoridopreinscripcionpracticaspp_set.filter(status=True).order_by(
                    '-fecha')
                template = get_template("alu_practicassalud/detalleobservacion.html")
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

                if not (request.POST['convenio'] or request.POST['acuerdo']):
                    return JsonResponse({"result": "bad", "mensaje": u"Debe tener al menos un convenio o acuerdo."})
                form = CartaVinculacionForm(request.POST)
                if form.is_valid():
                    year = datetime.now().strftime('%Y')
                    numsolicitudporanio = CartaVinculacionPracticasPreprofesionales.objects.filter(fecha_creacion__year=year).count() + 1
                    codsolicitud = generar_codigo(numsolicitudporanio, PREFIX, SUFFIX)

                    cartavinculacion = CartaVinculacionPracticasPreprofesionales(
                        memo = codsolicitud+'-OF',
                        fecha=form.cleaned_data['fecha'],
                        convenio=form.cleaned_data['convenio'],
                        acuerdo=form.cleaned_data['acuerdo'],
                        representante=form.cleaned_data['representante'],
                        cargo=form.cleaned_data['cargo'],
                        director=form.cleaned_data['director']
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
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

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

        elif action == 'actualizaubicacionempresa':
            try:
                form = UbicacionEmpresaPracticaForm(request.POST)
                if form.is_valid():
                    asignacionempresa = AsignacionEmpresaPractica.objects.get(pk=int(encrypt(request.POST['id'])))
                    if ubicacionempresa := UbicacionEmpresaPractica.objects.filter(status=True, asignacionempresapractica=asignacionempresa).first():
                        ubicacionempresa.latitud = form.cleaned_data['latitud']
                        ubicacionempresa.longitud = form.cleaned_data['longitud']
                        ubicacionempresa.actual = True
                    else:
                        ubicacionempresa = UbicacionEmpresaPractica(asignacionempresapractica=asignacionempresa, latitud=form.cleaned_data['latitud'], longitud=form.cleaned_data['longitud'], actual=True)
                    ubicacionempresa.save(request)
                    log(u'Actualizó ubicación empresa práctica: %s [%s]' % (ubicacionempresa, ubicacionempresa.id), request, "edit")
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
                lista_email = [filtro.correo, ]
                # lista_email = ['hllerenaa@unemi.edu.ec',]
                # GENERAR PDF
                fecha = filtro.fecha_creacion
                data['fecha'] = str(fecha.day) + " de " + str(
                    MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                if responsablevinculacion:
                    data['responsablevinculacion'] = responsablevinculacion
                    # firma = FirmaPersona.objects.filter(persona=responsablevinculacion, tipofirma=2,
                    #                                     status=True).first()
                    firma = responsablevinculacion.archivo.url
                    data['firmaimg'] = firma if firma else None
                template_pdf = 'alu_preinscripcionppp/solicitudpdf.html'
                nombrepersona = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(
                    (filtro.preinscripcion.inscripcion.persona.__str__()).replace(' ', '_')))
                nombredocumento = 'SOLICITUD_EMPRESA_{}_{}'.format(nombrepersona, random.randint(1, 100000).__str__())
                directory = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'solicitudempresas')
                try:
                    os.stat(directory)
                except:
                    os.mkdir(directory)
                valida = conviert_html_to_pdf_name_save(template_pdf, {'pagesize': 'A4', 'data': data, },
                                                        nombredocumento)
                if valida:
                    # if filtro.archivodescargar:
                    #     filtro.archivodescargar.delete()
                    #     filtro.save(request)
                    filtro.archivodescargar = 'qrcode/solicitudempresas/' + nombredocumento + '.pdf'
                    filtro.save(request)
                # GENERAR PDF
                instancia = DatosEmpresaPreInscripcionPracticasPP.objects.get(pk=request.POST['id'])
                documentolista = [instancia.archivodescargar]
                send_html_mail(subject, template, datos_email, lista_email, [], documentolista,
                               cuenta=CUENTAS_CORREOS[4][1])
                response = JsonResponse({'resp': True})
            except Exception as ex:
                response = JsonResponse({'resp': False, 'mensaje': ex})
            return HttpResponse(response.content)

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

        elif action == 'addfirma':
            try:

                f = FirmaInformeMensualActividadesForm(request.POST)
                del f.fields['persona']

                if f.is_valid():
                    firma = FirmaInformeMensualActividades(informe_id=request.GET.get('id'), cargo=f.cleaned_data.get('cargo'), persona_id=request.POST.get('persona'), responsabilidad=f.cleaned_data.get('responsabilidad'))
                    firma.save(request)

                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})
            
        elif action == 'editfirma':
            try:
                firma = FirmaInformeMensualActividades.objects.get(pk=request.POST.get('id'))
                f = FirmaInformeMensualActividadesForm(request.POST)
                del f.fields['persona']
                
                if f.is_valid():
                    firma.persona_id=request.POST.get('persona')
                    firma.cargo=f.cleaned_data.get('cargo') 
                    firma.responsabilidad=f.cleaned_data.get('responsabilidad')
                    firma.save(request)

                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})

        elif action == 'addinsumoinformeinternadorotativo':
            try:
                f = InsumoInformeInternadoRotativoForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data.get('activo'): InsumoInformeInternadoRotativo.objects.filter(status=True).update(activo=False)
                    insumo = InsumoInformeInternadoRotativo(motivacionjuridica=f.cleaned_data.get('motivacionjuridica'), activo=f.cleaned_data.get('activo'), informe=1)
                    insumo.save(request)

                    FirmaInformeMensualActividades.objects.create(cargo_id=request.POST.get('cargo_1'), persona_id=request.POST.get('persona_1'), responsabilidad=1, informe=1, insumo=insumo)
                    FirmaInformeMensualActividades.objects.create(cargo_id=request.POST.get('cargo_2'), persona_id=request.POST.get('persona_2'), responsabilidad=2, informe=1, insumo=insumo)
                    historial = HistorialInsumoInformeInternadoRotativo(insumo=insumo, tipoaccion=1)
                    historial.save(request)
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})

        elif action == 'editinsumoinformeinternadorotativo':
            try:
                f = InsumoInformeInternadoRotativoForm(request.POST)
                insumo = InsumoInformeInternadoRotativo.objects.get(pk=request.POST.get('id'))
                if f.is_valid():
                    insumo.motivacionjuridica = f.cleaned_data.get('motivacionjuridica')
                    if estado := f.cleaned_data.get('activo'):
                        InsumoInformeInternadoRotativo.objects.filter(status=True).update(activo=False)
                        insumo.activo = estado

                    insumo.save(request)
                    FirmaInformeMensualActividades.objects.filter(insumo=insumo, status=True).delete()
                    FirmaInformeMensualActividades.objects.create(cargo_id=request.POST.get('cargo_1'), persona_id=request.POST.get('persona_1'), responsabilidad=1, informe=1, insumo=insumo)
                    FirmaInformeMensualActividades.objects.create(cargo_id=request.POST.get('cargo_2'), persona_id=request.POST.get('persona_2'), responsabilidad=2, informe=1, insumo=insumo)
                    historial = HistorialInsumoInformeInternadoRotativo(insumo=insumo, tipoaccion=2)
                    historial.save(request)
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})

        elif action == 'delinsumoinformeinternadorotativo':
            try:
                insumo = InsumoInformeInternadoRotativo.objects.get(pk=request.POST.get('id'))
                insumo.status = False
                insumo.save(request)
                historial = HistorialInsumoInformeInternadoRotativo(insumo=insumo, tipoaccion=3)
                historial.save(request)
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})

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
                    return render(request, "alu_practicassalud/add.html", data)
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
                    return render(request, "alu_practicassalud/edit.html", data)
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
                    return render(request, "alu_practicassalud/editcarrera.html", data)
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
                    return render(request, "alu_practicassalud/editcarrera_actividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirarchivos':
                try:
                    data['title'] = u'Carga de evidencias de Prácticas Preprofesionales'
                    data['practicas'] = practicas = PracticasPreprofesionalesInscripcion.objects.get(
                        pk=request.GET['id'])

                    data[
                        'evidencias'] = practicas.periodoppp.evidencias_practica() if practicas.tipo != 7 else practicas.detalleevidenciaspracticaspro_set.filter(
                        status=True)

                    data['periodopractica'] = practicas.periodoppp
                    data['formevidencias'] = EvidenciaPracticasForm()
                    data['nevidencias'] = practicas.formatoevidenciaalumno()
                    return render(request, "alu_practicassalud/evidenciaspracticas.html", data)
                except Exception as ex:
                    pass

            elif action == 'addevidenciaspracticasnormal':
                try:
                    data['title'] = u'Evidencia Practicas'
                    data['form'] = EvidenciaPracticasNormalForm
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    template = get_template(
                        "alu_practicassalud/add_evidenciaspracticasnormal.html")
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
                    template = get_template("alu_practicassalud/add_evidenciaspracticas.html")
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
                    template = get_template("alu_practicassalud/ponerfechalimite.html")
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
                        "alu_practicassalud/add_aprobarevidenciaspracticas.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    data['title'] = u'Eliminar Practicas PreProfesionales'
                    data['campo'] = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicassalud/delete.html", data)
                except:
                    pass

            elif action == 'deletetutoracademico':
                try:
                    data['title'] = u'Eliminar Tutor Académico de Practicas PreProfesionales'
                    data['campo'] = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicassalud/deletetutor.html", data)
                except:
                    pass

            elif action == 'eliminasupervisor':
                try:
                    data['title'] = u'Eliminar Supervisor Académico de Practicas PreProfesionales'
                    data['campo'] = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicassalud/deletesupervisor.html", data)
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
                    return render(request, "alu_practicassalud/viewdepartamentos.html", data)
                except Exception as ex:
                    pass

            elif action == 'adddepartamento':
                try:
                    data['title'] = u'Adicionar Departamento Empresa'
                    form = PracticasDepartamentoForm()
                    data['form'] = form
                    return render(request, "alu_practicassalud/adddepartamento.html", data)
                except Exception as ex:
                    pass

            elif action == 'editdepartamento':
                try:
                    data['title'] = u'Editar Departamento'
                    data['departamento'] = departamento = PracticasDepartamento.objects.get(pk=request.GET['id'])
                    form = PracticasDepartamentoForm(initial={'nombre': departamento.nombre})
                    data['form'] = form
                    return render(request, "alu_practicassalud/editardepartamento.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletedepartamento':
                try:
                    data['title'] = u'Eliminar Departamento'
                    data['departamento'] = PracticasDepartamento.objects.get(pk=request.GET['iddepartamento'])
                    return render(request, "alu_practicassalud/deletedepartamento.html", data)
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
                    template = get_template("alu_practicassalud/aprobarrechazarsolicitud.html")
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
                    template = get_template("alu_practicassalud/detalles.html")
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
                    return render(request, "alu_practicassalud/ofertaspracticas.html", data)
                except Exception as ex:
                    pass

            elif action == 'addoferta':
                try:
                    data['title'] = u'Agregar Oferta'
                    form = OfertasPracticasForm()
                    form.cargar_itinerario()
                    data['form'] = form
                    return render(request, "alu_practicassalud/addoferta.html", data)
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
                    return render(request, "alu_practicassalud/editoferta.html", data)
                except Exception as ex:
                    pass

            elif action == 'deloferta':
                try:
                    data['title'] = u'Eliminar Oferta'
                    data['oferta'] = OfertasPracticas.objects.get(pk=int(request.GET['id']), status=True)
                    return render(request, "alu_practicassalud/deleoferta.html", data)
                except Exception as ex:
                    pass

            elif action == 'alumalla':
                try:
                    data['title'] = u'MALLA DEL ALUMNO'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['inscripcion_malla'] = inscripcionmalla = inscripcion.malla_inscripcion()
                    data['malla'] = malla = inscripcionmalla.malla
                    data['nivelesdemallas'] = NivelMalla.objects.all().order_by('id')
                    data['ejesformativos'] = EjeFormativo.objects.all().order_by('nombre')
                    data['asignaturasmallas'] = [(x, inscripcion.aprobadaasignatura(x)) for x in
                                                 AsignaturaMalla.objects.filter(malla=malla)]
                    resumenniveles = [{'id': x.id, 'horas': x.total_horas(malla), 'creditos': x.total_creditos(malla)}
                                      for x in NivelMalla.objects.all().order_by('id')]
                    data['resumenes'] = resumenniveles
                    template = get_template("alu_practicassalud/alumalla.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'listaprofesordistributivo':
                try:
                    # listaidcriterio = [6, 23, 31]
                    listaidcriterio, listaprofesor, practicasprofesionales, inscripcion, iditinerario, id = [6, 23, 167, 83, 31, 153, 154], [], None, None, request.GET.get('iditinerario', ''), request.GET.get('id', '')
                    if id:
                        # EDITAR PRACTICA PREPROFESIONALES
                        practicasprofesionales = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                        carrera = practicasprofesionales.inscripcion.carrera
                        fechadesde = convertir_fecha_invertida(request.GET['fd'])
                        fechahasta = convertir_fecha_invertida(request.GET['fh'])
                        carrera_id = carrera.id
                        preinscripcionid = practicasprofesionales.preinscripcion.id
                        preinsc = practicasprofesionales.preinscripcion
                    else:
                        # ADICIONAR PRACTICA PREPROFESIONALES
                        inscripcion = Inscripcion.objects.get(pk=int(request.GET['idi']))
                        carrera = inscripcion.carrera
                        fechadesde = convertir_fecha_invertida(request.GET['fd'])
                        fechahasta = convertir_fecha_invertida(request.GET['fh'])
                        carrera_id = request.GET['carrera']
                        preinscripcionid = request.GET['preinscripcion']
                        preinsc = DetallePreInscripcionPracticasPP.objects.get(pk=preinscripcionid)
                    periodo = request.session['periodo']
                    if inscripcion:
                        if inscripcion.carrera.modalidad == 3:
                            profesoresdistributivo = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo).distinct()
                        else:
                            profesoresdistributivo = ProfesorDistributivoHoras.objects.filter(detalledistributivo__criteriodocenciaperiodo__criterio__id__in=listaidcriterio,
                                                                                              detalledistributivo__actividaddetalledistributivo__actividaddetalledistributivocarrera__carrera=carrera, status=True, periodo=periodo).distinct()
                    else:
                        if practicasprofesionales.inscripcion.carrera.modalidad == 3:
                            profesoresdistributivo = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo).distinct()
                        else:
                            profesoresdistributivo = ProfesorDistributivoHoras.objects.filter(detalledistributivo__criteriodocenciaperiodo__criterio__id__in=listaidcriterio, detalledistributivo__actividaddetalledistributivo__actividaddetalledistributivocarrera__carrera=carrera, status=True, periodo=periodo).distinct()
                    if profesoresdistributivo and iditinerario:
                        profesoresdistributivo = profesoresdistributivo.filter(detalledistributivo__actividaddetalledistributivo__actividaddetalledistributivocarrera__itinerariosactividaddetalledistributivocarrera__itinerario_id=iditinerario)
                    for x in profesoresdistributivo:
                        listaprofesor.append([u'%s' % x.profesor.id, u'%s - (%s) - hor.(%s) - asig.(%s)' % (
                            x.profesor.persona.nombre_completo_inverso(), x.periodo.nombre,
                            x.horas_docencia_segun_criterio_carrera(listaidcriterio, carrera_id),
                            x.profesor.contar_practicaspreprofesionales_asignadas_carrera(periodo, carrera_id,
                                                                                          preinscripcionid))])

                    periodoevidencia = CabPeriodoEvidenciaPPP.objects.filter(
                        (Q(fechainicio__lte=fechadesde) & Q(fechafin__gte=fechadesde)) | (
                                Q(fechafin__lte=fechahasta) & Q(fechafin__gte=fechahasta))).distinct()
                    listape = []
                    for p in CabPeriodoEvidenciaPPP.objects.filter(status=True, periodoevidenciapracticaprofesionales__carrera=carrera_id).order_by('-fechainicio'):
                        listape.append([p.id, p.nombre])

                    listaaempresap = []
                    for ep in AsignacionEmpresaPractica.objects.values_list('id', 'nombre').filter(status=True).order_by('nombre'):
                        listaaempresap.append([ep[0], ep[1]])
                    # Acuerdo Compromiso
                    # listaacuerdo = []
                    # # , carrera=carrera
                    # for a in AcuerdoCompromiso.objects.filter(status=True).order_by('-fechaelaboracion'):
                    #     # acuerdo1 = a.empresa.nombre +" - "+ a.carrera.nombre +" - "+ str(a.fechaelaboracion)
                    #     acuerdo1 = str(a)
                    #     listaacuerdo.append([a.id, acuerdo1])

                    # Convenio Empresa
                    # listaconvenio = []
                    # for c in ConvenioEmpresa.objects.filter(fechafinalizacion__gte=fechadesde, status=True).order_by('fechafinalizacion'):
                        # for c in ConvenioEmpresa.objects.filter(fechainicio__gte=fechadesde, fechainicio__lte=fechahasta ,status=True).order_by('-fechainicio'):
                        # for c in ConvenioEmpresa.objects.filter(fechafinalizacion__lte=fechadesde,status=True).order_by('-fechainicio'):
                        # convenio1 = c.objetivo + " - " + c.empresaempleadora.nombre +" - "+ str(c.fechainicio) +" - "+ str(c.fechafinalizacion)
                        # convenio1 = "{}".format(str(c))
                        # listaconvenio.append([c.id, convenio1])

                    # MUESTRA EL MENSAJE DEL PERIODO
                    data = {"result": "ok", "results": listaprofesor, "mensaje": u'%s %s' % (
                        "Según las fechas de la Práctica Preprofesionales está en el periodo", periodo),
                            'periodoevidencias': listape, 'listaaempresap': listaaempresap,
                            # 'listaacuerdo': listaacuerdo, 'listaconvenio': listaconvenio,
                            'perevid': periodoevidencia[0].id if periodoevidencia else 0}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

            elif action == 'actualizarcampos':
                try:
                    data = {}
                    listatutor, listape, listaaempresap = [], [], []
                    id_configoferta, id_preins = request.GET.get('idconfig', ''), request.GET.get('idpreinsc', 0)
                    if id_configoferta:
                        configoferta = ConfiguracionInscripcionPracticasPP.objects.get(pk=id_configoferta)
                        if configoferta.tutorunemi:
                            listatutor.append([str(configoferta.tutorunemi.id), u'%s - asig.(%s)' % (configoferta.tutorunemi.persona.nombre_completo_inverso(), configoferta.tutorunemi.contar_practicaspreprofesionales_asignadas_carrera(configoferta.preinscripcion.periodo, configoferta.itinerariomalla.malla.carrera.id, id_preins))])
                        if configoferta.periodoppp:
                            listape.append([configoferta.periodoppp.id, configoferta.periodoppp.nombre])
                        if configoferta.asignacionempresapractica:
                            listaaempresap.append([configoferta.asignacionempresapractica.id, configoferta.asignacionempresapractica.nombre])
                        # MUESTRA EL MENSAJE DEL PERIODO
                        data = {"result": "ok", "results": listatutor, "mensaje": u'%s %s' % ("Según las fechas de la Práctica Preprofesionales está en el periodo", periodo),
                            'periodoevidencias': listape, 'listaaempresap': listaaempresap,
                            '_fechadesde': configoferta.fechainicio.strftime('%Y-%m-%d') if configoferta.fechainicio else datetime.now().date().strftime('%Y-%m-%d'),
                            '_fechahasta': configoferta.fechafin.strftime('%Y-%m-%d') if configoferta.fechafin else datetime.now().date().strftime('%Y-%m-%d'),
                            '_tutorunemi': configoferta.tutorunemi.id if configoferta.tutorunemi else 0,
                            '_idsupervisorunemi': configoferta.supervisor.id if configoferta.supervisor else 0,
                            '_supervisorunemi': u'%s - %s' %(configoferta.supervisor.persona.cedula if configoferta.supervisor.persona.cedula else configoferta.supervisor.persona.pasaporte ,str(configoferta.supervisor)) if configoferta.supervisor else '',
                            '_empresa': configoferta.asignacionempresapractica.id if configoferta.asignacionempresapractica else 0,
                            '_otraempresa': configoferta.otraempresaempleadora,
                            '_horas': configoferta.numerohora,
                            '_idconvenioempresa': configoferta.convenio.id if configoferta.convenio else 0,
                            '_convenioempresa': str(configoferta.convenio) if configoferta.convenio else '',
                            '_lugarpractica': configoferta.lugarpractica.id if configoferta.lugarpractica else 0,
                            '_tipoinstitucion': configoferta.tipoinstitucion,
                            '_periodoevidencia': configoferta.periodoppp.id if configoferta.periodoppp else 0,
                            }
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
                    return render(request, "alu_practicassalud/viewdocumento.html", data)
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
                        "alu_practicassalud/modal/formdocumentositinerarios_apertura.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'adddocumento':
                try:
                    data['form2'] = DocumentoRequeridoPracticaForm()
                    template = get_template("alu_practicassalud/modal/formdocumentos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editdocumento':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = RequisitosHomologacionPracticas.objects.get(pk=request.GET['id'])
                    data['form2'] = DocumentoRequeridoPracticaForm(initial=model_to_dict(filtro))
                    template = get_template("alu_practicassalud/modal/formdocumentos.html")
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
                                  "alu_practicassalud/viewaperturasolicitudpractica.html", data)
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
                    return render(request, "alu_practicassalud/addaperturasolicitud.html", data)
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
                                  "alu_practicassalud/editaperturasolicitudpractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delaperturasolicitud':
                try:
                    data['title'] = u'Eliminar apertura de solicitud en Práctica Pre-Profesionales'
                    data['apertura'] = AperturaPracticaPreProfesional.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicassalud/delaperturasolicitud.html", data)
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
                    return render(request, "alu_practicassalud/viewformatospractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'addformatopractica':
                try:
                    data['title'] = u'Adicionar Formatos de Práctica Pre-Profesionales'
                    data['form'] = FormatoPracticaPreProfesionalForm()
                    return render(request, "alu_practicassalud/addformatopractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'editformatopractica':
                try:
                    data['title'] = u'Editar formato de Práctica Pre-Profesionales'
                    data['formato'] = formato = FormatoPracticaPreProfesional.objects.get(pk=int(request.GET['id']))
                    data['form'] = FormatoPracticaPreProfesionalForm(
                        initial={'nombre': formato.nombre, 'vigente': formato.vigente})
                    return render(request, "alu_practicassalud/editformatopractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delformatopractica':
                try:
                    data['title'] = u'Eliminar formato de Práctica Pre-Profesionales'
                    data['formato'] = FormatoPracticaPreProfesional.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicassalud/delformatopractica.html", data)
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
                    return render(request, "alu_practicassalud/viewdetalleformatospractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'adddetalleformatopractica':
                try:
                    data['title'] = u'Adicionar detalle formatos de Práctica Pre-Profesionales'
                    data['form'] = DetalleFormatoPracticaPreProfesionalForm()
                    data['formato'] = FormatoPracticaPreProfesional.objects.get(pk=int(request.GET['id']), status=True)
                    return render(request, "alu_practicassalud/adddetalleformatopractica.html",
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
                    return render(request, "alu_practicassalud/editdetalleformatopractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'deldetalleformatopractica':
                try:
                    data['title'] = u'Eliminar detalle de formato de Práctica Pre-Profesionales'
                    data['detalleformato'] = DetalleFormatoPracticaPreProfesional.objects.get(pk=int(request.GET['id']),
                                                                                              status=True)
                    return render(request, "alu_practicassalud/deldetalleformatopractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'duplicarsolicitudpractica':
                try:
                    data['title'] = u'Duplicar solicitud de práctica pre profesional'
                    data['practicapreprofesional'] = PracticasPreprofesionalesInscripcion.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    return render(request,
                                  "alu_practicassalud/confirmarduplicarsolicitudpractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'perevidenciapractica':
                try:
                    data['title'] = u'Periodo de evidencia de Práctica Pre-Profesionales'
                    url_vars = f'&action={action}'
                    search = None
                    periodoevidencia = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        url_vars += f'&s={search}'
                        s = search.split(" ")
                        if len(s) == 1:
                            periodoevidencia = CabPeriodoEvidenciaPPP.objects.filter(Q(nombre__icontains=s[0]), Q(status=True)).order_by('-fechainicio')
                        elif len(s) == 2:
                            periodoevidencia = CabPeriodoEvidenciaPPP.objects.filter(
                                Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(status=True)).order_by('-fechainicio')
                        elif len(s) == 3:
                            periodoevidencia = CabPeriodoEvidenciaPPP.objects.filter(
                                Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(nombre__icontains=s[2]), Q(status=True)).order_by('-fechainicio')
                        else:
                            periodoevidencia = CabPeriodoEvidenciaPPP.objects.filter(Q(nombre__icontains=search), Q(status=True)).order_by('-fechainicio')
                    else:
                        periodoevidencia = CabPeriodoEvidenciaPPP.objects.filter(status=True).order_by('-fechainicio')
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
                    data['url_vars'] = url_vars
                    return render(request, "alu_practicassalud/viewperiodoevidenciapractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'addperevidenciapractica':
                try:
                    data['title'] = u'Adicionar periodo de evidencias de Práctica Pre-Profesionales'
                    data['form'] = PeriodoEvidenciaPracticaProfesionalesForm()
                    return render(request, "alu_practicassalud/addperevidenciapractica.html",
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
                    return render(request, "alu_practicassalud/editperevidenciapractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'delperevidenciapractica':
                try:
                    data['title'] = u'Eliminar periodo de evidencias de Práctica Pre-Profesionales'
                    data['periodoevidencia'] = CabPeriodoEvidenciaPPP.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicassalud/delperevidenciapractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'evidenciapractica':
                try:
                    data['title'] = u'Evidencia de Práctica Pre-Profesionales'
                    search = None
                    evidencia = None
                    data['id'] = idevidencia = request.GET['id']
                    url_vars = f'&action={action}&id={idevidencia}'
                    data['periodoevidencia'] = periodoevidencia = CabPeriodoEvidenciaPPP.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    if 's' in request.GET:
                        search = request.GET['s']
                        url_vars += f'&s={search}'
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
                                evidencia = periodoevidencia.evidenciapracticasprofesionales_set.filter(Q(nombre__icontains=search), Q(status=True))
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
                    data['url_vars'] = url_vars
                    return render(request, "alu_practicassalud/viewevidenciapractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'addevidenciapractica':
                try:
                    data['title'] = u'Adicionar periodo de evidencias de Práctica Pre-Profesionales'
                    data['periodoevidencia'] = periodoevidencia = CabPeriodoEvidenciaPPP.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['form'] = EvidenciaPracticasPreProfesionalForm(
                        initial={'fechainicio': periodoevidencia.fechainicio.strftime('%Y-%m-%d'), 'fechafin': periodoevidencia.fechafin.strftime('%Y-%m-%d')})
                    return render(request, "alu_practicassalud/addevidenciapractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'editevidenciapractica':
                try:
                    data['title'] = u'Editar periodo de evidencias de Práctica Pre-Profesionales'
                    data['evidencia'] = evidencia = EvidenciaPracticasProfesionales.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    ef = EvidenciaFormatoPpp.objects.filter(evidencia=evidencia).first()
                    data['form'] = EvidenciaPracticasPreProfesionalForm(initial={'nombre': evidencia.nombre,
                                                                                 'fechainicio': evidencia.fechainicio.strftime('%Y-%m-%d'),
                                                                                 'fechafin': evidencia.fechafin.strftime('%Y-%m-%d'),
                                                                                 'nombrearchivo': evidencia.nombrearchivo,
                                                                                 'configurarfecha': evidencia.configurarfecha,
                                                                                 'orden': evidencia.orden,
                                                                                 'puntaje': evidencia.puntaje,
                                                                                 'formato': ef.formato if ef else None
                                                                                 # 'fechaformato': ef.fecha.strftime('%Y-%m-%d') if ef else hoy.strftime('%Y-%m-%d')
                                                                                 })
                    return render(request, "alu_practicassalud/editevidenciapractica.html", data)
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
                    return render(request, "alu_practicassalud/editevidenciapractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delevidenciapractica':
                try:
                    data['title'] = u'Eliminar periodo de evidencias de Práctica Pre-Profesionales'
                    data['evidencia'] = EvidenciaPracticasProfesionales.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicassalud/delevidenciapractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delarchivoevidenciapractica':
                try:
                    data['title'] = u'Eliminar archivo de evidencias de Práctica Pre-Profesionales '
                    data['evidencia'] = EvidenciaPracticasProfesionales.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicassalud/delarchivoevidenciapractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'delarchivodetalleevidencia':
                try:
                    data['title'] = u'Eliminar archivo de evidencias del estudiante'
                    data['evidencia'] = DetalleEvidenciasPracticasPro.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicassalud/delarchivodetalleevidencia.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'formatoppp':
                try:
                    data['title'] = u'Listado de formatos - Salud'

                    now = datetime.now().date()
                    search, filters, url_vars = '', Q(status=True), ''
                    formato = FormatoPracticaPreprofesionalSalud.objects.filter(filters)
                    if id := int(encrypt(request.GET.get('id', 0))):
                        data['id'] = id
                        url_vars += f'&id={id}'

                    if 's' in request.GET:
                        search = request.GET['s']
                        url_vars += f'&s={search}'
                        if ' ' in search:
                            s = search.split(" ")
                            if len(s) == 1:
                                filters &= Q(nombre__icontains=s[0])
                            elif len(s) == 2:
                                filters &= (Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]))
                            elif len(s) == 3:
                                filters &= (Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(nombre__icontains=s[2]))
                            else:
                                filters &= Q(nombre__icontains=search)
                        else:
                            filters &= Q(nombre__icontains=search)
                    listado = formato.filter(filters).order_by('nombre')
                    paging = MiPaginador(listado, 15)
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
                    data['listado'] = page.object_list
                    data['search'] = search if search else ""
                    data['url_vars'] = url_vars
                    return render(request, "alu_practicassalud/viewformatoppp.html", data)
                except Exception as ex:
                    print('{} - Error on line {}'.format(str(ex), sys.exc_info()[-1].tb_lineno))
                    return JsonResponse({"result": "bad", 'to': "{}?action=evidenciapractica&id={}".format(request.path, encrypt(id))}, safe=False)

            elif action == 'addformatoppp':
                try:
                    data['action'] = request.GET['action']
                    data['title'] = u'Adicionar formato'
                    # if id := request.GET.get('id', None):
                    #     data['id'] = int(id)
                    form = FormatoPppForm()
                    data['form'] = form
                    template = get_template("alu_practicassalud/modal/formformato.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'editformatoppp':
                try:
                    data['title'] = u'Editar formato'
                    data['action'] = request.GET['action']
                    if id := int(encrypt(request.GET.get('id', 0))):
                        data['id'] = id
                    if id > 0:
                        data['formato'] = formato = FormatoPracticaPreprofesionalSalud.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                        f = FormatoPppForm(initial={'nombre': formato.nombre,
                                                      'htmlnombre': formato.htmlnombre,
                                                      'carrera': formato.carrera,
                                                      'activo': formato.activo
                                                      })
                        f.editar(formato)
                        data['form'] = f
                        template = get_template("alu_practicassalud/modal/formformato.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'inscripcionoferta':
                try:
                    data['title'] = u'Inscritos en oferta de Prácticas Preprofesionales'
                    data['oferta'] = oferta = OfertasPracticas.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['practicaspreprofesionales'] = PracticasPreprofesionalesInscripcion.objects.filter(
                        oferta=oferta, status=True).order_by('-fecha_creacion')
                    return render(request, "alu_practicassalud/inscripcionoferta.html", data)
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
                    return render(request, "alu_practicassalud/viewinformemensualsupervisor.html",
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
                    return render(request, "alu_practicassalud/viewinformemensual.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinformemensual':
                try:
                    data['title'] = u'Adicionar informe mensual de Prácticas Preprofesionales'
                    form = InformeMensualSupervisorPracticaForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "alu_practicassalud/addinformemensual.html", data)
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
                    return render(request, "alu_practicassalud/editinformemensual.html", data)
                except Exception as ex:
                    pass

            elif action == 'delinformemensual':
                try:
                    data['title'] = u'Eliminar informe mensual de Prácticas Preprofesionales'
                    data['informesupervisor'] = InformeMensualSupervisorPractica.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicassalud/delinformemensual.html", data)
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
                    return render(request, "alu_practicassalud/viewdetallepractica.html", data)
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
                    return render(request, "alu_practicassalud/viewdetallevisita.html", data)
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
                    return render(request, "alu_practicassalud/viewarchivogeneral.html", data)
                except Exception as ex:
                    pass

            elif action == 'addarchivogeneral':
                try:
                    data['title'] = u'Adicionar archivos generales'
                    data['form'] = ArchivoGeneralPracticaPreProfesionalesFrom()
                    return render(request, "alu_practicassalud/addarchivogeneral.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarchivogeneral':
                try:
                    data['title'] = u'Editar archivos generales'
                    data['archivogeneral'] = archivogeneral = ArchivoGeneralPracticaPreProfesionales.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['form'] = ArchivoGeneralPracticaPreProfesionalesFrom(
                        initial={'nombre': archivogeneral.nombre, 'visible': archivogeneral.visible,'carrera': archivogeneral.carreras()})
                    return render(request, "alu_practicassalud/editarchivogeneral.html", data)
                except Exception as ex:
                    pass

            elif action == 'delarchivogeneral':
                try:
                    data['title'] = u'Eliminar archivos generales'
                    data['archivogeneral'] = ArchivoGeneralPracticaPreProfesionales.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicassalud/delarchivogeneral.html", data)
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
                    return render(request, "alu_practicassalud/addconfpreinscripcion.html", data)
                except Exception as ex:
                    print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, ex))
                    pass

            elif action == 'editconfpreinscripcion':
                try:
                    data['title'] = u'Editar configuración de pre-inscripciones'
                    data['conf'] = conf = PreInscripcionPracticasPP.objects.get(status=True,
                                                                                pk=int(encrypt(request.GET['id'])))
                    form = PreInscripcionPracticasPPForm(initial=model_to_dict(conf))
                    form.cargar_carrera(conf)
                    if practicasalud or conf.coordinaciones().first().id == 1:
                        coordsalud = Coordinacion.objects.filter(id=1)
                        form.fields['coordinacion'].queryset = coordsalud
                        form.fields['carrera'].queryset = Carrera.objects.filter(status=True, coordinacion=coordsalud.first())
                        form.fields['subirarchivo'].label = u'Permite subir archivo de prioridad (Estudiante)?'
                        form.fields['actualizararchivo'].label = u'Actualizar archivo prioriodad (Estudiante)?'
                        extconf = conf.extpreinscripcionpracticaspp_set.filter(status=True).first()
                        form.fields['vinculacion'].initial = extconf.vinculacion if extconf else False
                        del form.fields['puede_solicitar']
                        del form.fields['puede_asignar']
                        del form.fields['fechamaximoagendatutoria']
                        del form.fields['agendatutoria']
                    else:
                        del form.fields['inglesaprobado']
                        del form.fields['computacionaprobado']
                    data['form'] = form
                    return render(request, "alu_practicassalud/editconfpreinscripcion.html", data)
                except Exception as ex:
                    pass

            if action == 'delconfpreinscripcion':
                try:
                    data['title'] = u'Eliminar configuración de pre-inscripciones'
                    data['conf'] = PreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicassalud/delconfpreinscripcion.html", data)
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
                        preinscripciones = PreInscripcionPracticasPP.objects.filter(pk=ids, status=True)
                    else:
                        preinscripciones = PreInscripcionPracticasPP.objects.filter(status=True)
                    # if practicasalud:
                    #     preinscripciones = preinscripciones.filter(coordinacion__in=[1])
                    filtro = Q(status=True)
                    if 's' in request.GET:
                        search = request.GET['s']
                        s = search.split(" ")
                        if len(s) == 1:
                            filtro =  filtro & (Q(mensaje__icontains=s[0]) | Q(carrera__nombre__icontains=s[0]))
                        elif len(s) == 2:
                            filtro = filtro & (Q(mensaje__icontains=s[0]) & Q(mensaje__icontains=s[1]) |
                                               Q(carrera__nombre__icontains=s[0]) & Q(carrera__nombre__icontains=s[1]))
                        elif len(s) == 3:
                            filtro = filtro & (Q(mensaje__icontains=s[0]) & Q(mensaje__icontains=s[1]) & Q(mensaje__icontains=s[2]) |
                                               Q(carrera__nombre__icontains=s[0]) & Q(carrera__nombre__icontains=s[1]) & Q(carrera__nombre__icontains=s[2]))
                        else:
                            filtro = filtro & (Q(mensaje__icontains=search) | Q(carrera__nombre__icontains=search))

                    paging = MiPaginador(preinscripciones.filter(filtro).distinct('id', 'fechainicio').order_by('-fechainicio'), 25)
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
                    return render(request, "alu_practicassalud/confpreinscripcionppp.html", data)
                except Exception as ex:
                    pass

            elif action == 'configurarofertasinscripcion':
                try:
                    data['title'] = u'Configuración de ofertas para practicas pre-profesionales'
                    data['action'] = action
                    data['id'] = id = int(encrypt(request.GET['id']))
                    idemp, iditi = 0, 0
                    search, filtros, url_vars = request.GET.get('s', ''), Q(status=True, preinscripcion_id=id), f'&action={action}&id={request.GET["id"]}'
                    ids = None
                    data['preinscripcion'] = preinscripcion = PreInscripcionPracticasPP.objects.get(pk=id)
                    confinscripciones = ConfiguracionInscripcionPracticasPP.objects.filter(filtros)
                    if 'idemp' in request.GET:
                        idemp = int(request.GET['idemp'])
                        if idemp > 0:
                            filtros = filtros & Q(asignacionempresapractica_id=idemp)
                            url_vars += f"&idemp={idemp}"
                            data['idemp'] = idemp

                    if 'iditi' in request.GET:
                        iditi = int(request.GET['iditi'])
                        if iditi > 0:
                            filtros = filtros & Q(itinerariomalla__in=[iditi])
                            url_vars += f"&iditi={iditi}"
                            data['iditi'] = iditi

                    if search:
                        s = search.split()
                        if len(s) == 1:
                            filtros = filtros & (Q(itinerariomalla__nombre__icontains=search) | Q(itinerariomalla__malla__carrera__nombre__icontains=search) |
                                                 Q(tutorunemi__persona__nombres__icontains=search) | Q(tutorunemi__persona__apellido1__icontains=search) | Q(tutorunemi__persona__apellido2__icontains=search) |
                                                 Q(supervisor__persona__nombres__icontains=search) | Q(supervisor__persona__apellido1__icontains=search) | Q(supervisor__persona__apellido2__icontains=search) |
                                                 Q(asignacionempresapractica__nombre__icontains=search) | Q(asignacionempresapractica__canton__nombre__icontains=search)
                                                 # | Q(empresaempleadora__nombre__icontains=search) | Q(empresaempleadora__nombrecorto__icontains=search)
                                                 )
                        elif len(s) == 2:
                            filtros = filtros & ((Q(itinerariomalla__nombre__icontains=s[0]) & Q(itinerariomalla__nombre__icontains=s[1])) | (Q(itinerariomalla__malla__carrera__nombre__icontains=s[0]) & Q(itinerariomalla__malla__carrera__nombre__icontains=s[1])) |
                                                 (Q(tutorunemi__persona__nombres__icontains=s[0]) & Q(tutorunemi__persona__nombres__icontains=s[1])) | (Q(tutorunemi__persona__apellido1__icontains=s[0]) & Q(tutorunemi__persona__apellido2__icontains=s[1])) |
                                                 (Q(supervisor__persona__nombres__icontains=s[0]) & Q(supervisor__persona__nombres__icontains=s[1])) | (Q(supervisor__persona__apellido1__icontains=s[0]) & Q(supervisor__persona__apellido2__icontains=s[1])) |
                                                 (Q(asignacionempresapractica__nombre__icontains=s[0]) &Q(asignacionempresapractica__nombre__icontains=s[1])) | (Q(asignacionempresapractica__canton__nombre__icontains=s[0]) & Q(asignacionempresapractica__canton__nombre__icontains=s[1]))
                                                 # |(Q(empresaempleadora__nombre__icontains=s[0]) & Q(empresaempleadora__nombre__icontains=s[1])) | (Q(empresaempleadora__nombrecorto__icontains=s[0]) & Q(empresaempleadora__nombrecorto__icontains=s[1]))
                                                 )
                        data['search'] = f"{search}"
                        url_vars += f"&s={search}"
                    data['itinerarios'] = ItinerariosMalla.objects.filter(pk__in=confinscripciones.values_list('itinerariomalla', flat=True))
                    data['empresas'] = confinscripciones.values_list('asignacionempresapractica_id','asignacionempresapractica__nombre').distinct('asignacionempresapractica_id')
                    paging = MiPaginador(confinscripciones.filter(filtros).order_by('-id'), 20)
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
                    data['url_vars'] = url_vars
                    data['extconf'] = ExtPreInscripcionPracticasPP.objects.filter(status=True, preinscripcion_id=id).first()
                    data['ids'] = ids if ids else ""
                    return render(request, "alu_practicassalud/configuracioninscripcionppp.html", data)
                except Exception as ex:
                    pass

            elif action == 'addconfiginscripcion':
                try:
                    data['title'] = u'Adicionar nueva oferta'
                    data['action'] = request.GET['action']
                    data['preinscripcion'] = pre = PreInscripcionPracticasPP.objects.get(pk=int(encrypt(request.GET['id'])))
                    qscarreras = pre.carrera.values_list('id', flat=True).all()
                    form = ConfiguracionInscripcionPracticasPPForm()
                    form.iniciarform(qscarreras)
                    if extconf := pre.extpreinscripcionpracticaspp_set.filter(status=True).first():
                        form.iniciarfechas(extconf)
                    data['supervisor'] = data['convenio'] = data['acuerdo'] = 0
                    data['form'] = form
                    template = get_template("alu_practicassalud/modal/formconfiginscripcionoferta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editconfiginscripcion':
                try:
                    data['title'] = u'Editar oferta'
                    data['action'] = request.GET['action']
                    data['configuracion'] = configuracion = ConfiguracionInscripcionPracticasPP.objects.get(pk=int(encrypt(request.GET['id'])))
                    qscarreras = configuracion.preinscripcion.carrera.values_list('id', flat=True).all()
                    form = ConfiguracionInscripcionPracticasPPForm()
                    form.iniciarform(qscarreras)
                    eCarreras = configuracion.itinerariomalla.values_list('malla__carrera_id', flat=True).all()
                    form.init(eCarreras if eCarreras else qscarreras, configuracion.itinerariomalla.all() if configuracion.itinerariomalla.all() else None, configuracion.tutorunemi.id if configuracion.tutorunemi else None,
                              configuracion.asignacionempresapractica.id, configuracion.periodoppp.id)
                    form.editar(configuracion)
                    data['supervisor'] = configuracion.supervisor.id if configuracion.supervisor else 0
                    data['convenio'] = configuracion.convenio.id if configuracion.convenio else 0
                    data['form'] = form
                    template = get_template("alu_practicassalud/modal/formconfiginscripcionoferta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'actualizarestado':
                try:
                    data['title'] = u'Actualizar oferta'
                    data['action'] = request.GET['action']
                    # data['eMensaje'] = '¿Está seguro/a de ejecutar la acción?;Al confirmar, se actualizará el estado con base a las fechas indicadas.'
                    data['configuracion'] = configuracion = ConfiguracionInscripcionPracticasPP.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = ActualizaConfiguracionInscripcionPracticasPPForm(initial={'estado': configuracion.estado})
                    # form.iniciar(configuracion)
                    data['form'] = form
                    template = get_template("alu_practicassalud/modal/formconfiginscripcionoferta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'verinscritos':
                try:
                    data['action'] = request.GET['action']
                    data['configuracion'] = configuracion = ConfiguracionInscripcionPracticasPP.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['listadoinscritos'] = configuracion.inscritos_oferta()
                    template = get_template("alu_practicassalud/modal/viewinscritos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'fechasconvocatoria':
                try:
                    data['title'] = u'Registrar fechas de convocatoria'
                    data['action'] = request.GET['action']
                    data['eMensaje'] = '¿Está seguro/a de ejecutar la acción?; Al confirmar, se establecerán los ajustes predeterminados para prácticas pre profesionales.'
                    data['preinscripcion'] = pre = PreInscripcionPracticasPP.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = FechasConvocatoriaPPPForm()
                    if extconf := pre.extpreinscripcionpracticaspp_set.filter(status=True).first():
                        form.iniciar(extconf)
                    data['form'] = form
                    template = get_template("alu_practicassalud/modal/formconfiginscripcionoferta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'responablecentrosalud':
                try:
                    data['title'] = u'Responsables de centros de salud para practicas pre-profesionales'
                    data['action'] = action
                    data['id'] = id = int(encrypt(request.GET['id']))
                    idemp = 0
                    search, filtros, url_vars = request.GET.get('s', ''), Q(status=True), f'&action={action}'
                    ids = None
                    responsables = ResponsableCentroSalud.objects.filter(filtros)

                    if 'idemp' in request.GET:
                        idemp = int(request.GET['idemp'])
                        if idemp > 0:
                            filtros = filtros & Q(asignacionempresapractica_id=idemp)
                            url_vars += f"&idemp={idemp}"
                            data['idemp'] = idemp

                    if search:
                        s = search.split()
                        if len(s) == 1:
                            filtros = filtros & (Q(persona__cedula__icontains=s[0]) | Q(persona__pasaporte__icontains=s[0]) |
                                                 Q(persona__nombres__icontains=s[0]) | Q(persona__apellido1__icontains=s[0]) | Q(persona__apellido2__icontains=s[0]) |
                                                 Q(asignacionempresapractica__nombre__icontains=s[0]) | Q(asignacionempresapractica__canton__nombre__icontains=s[0])
                                                 )
                        elif len(s) == 2:
                            filtros = filtros & (
                                    (Q(persona__nombres__icontains=s[0]) & Q(persona__nombres__icontains=s[1])) | (Q(persona__apellido1__icontains=s[0]) & Q(persona__apellido2__icontains=s[1])) |
                                    (Q(asignacionempresapractica__nombre__icontains=s[0]) & Q(asignacionempresapractica__nombre__icontains=s[1])) | (Q(asignacionempresapractica__canton__nombre__icontains=s[0]) & Q(asignacionempresapractica__canton__nombre__icontains=s[1]))
                                    )
                        else:
                            filtros = filtros & (Q(persona__cedula__icontains=search) | Q(persona__pasaporte__icontains=search) |
                                                 Q(persona__nombres__icontains=search) | Q(persona__apellido1__icontains=search) | Q(persona__apellido2__icontains=search) |
                                                 Q(asignacionempresapractica__nombre__icontains=search) | Q(asignacionempresapractica__canton__nombre__icontains=search)
                                                 )
                        data['search'] = f"{search}"
                        url_vars += f"&s={search}"
                    data['empresas'] = responsables.values_list('asignacionempresapractica_id', 'asignacionempresapractica__nombre').distinct('asignacionempresapractica_id')
                    paging = MiPaginador(responsables.filter(filtros).order_by('-persona__apellido1'), 20)
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
                    data['responsables'] = page.object_list
                    data['url_vars'] = url_vars
                    data['ids'] = ids if ids else ""
                    return render(request, "alu_practicassalud/responsablecentrosalud.html", data)
                except Exception as ex:
                    pass

            elif action == 'consultacedulaexterno':
                try:
                    cedula = request.GET['cedula'].strip().upper()
                    if request.GET['tipo'].strip() == '1':
                        resp = validarcedula(cedula)
                        if resp != 'Ok':
                            return JsonResponse({'result': 'bad', 'mensaje': u"%s." % (resp)})

                    pers = consultarPersona(cedula)
                    if pers:
                        # if len(pers.mis_perfilesusuarios()) == 1 and pers.tiene_usuario_externo():
                        return JsonResponse({"result": True,
                                             "apellido1": pers.apellido1,
                                             "apellido2": pers.apellido2,
                                             "nacimiento": pers.nacimiento.strftime('%Y-%m-%d'),
                                             "nombres": pers.nombres,
                                             "sexo": pers.sexo.id,
                                             "telefono": pers.telefono,
                                             "telefono_conv": pers.telefono_conv,
                                             "email": pers.email})
                        # else:
                        #     return JsonResponse({'result': 'bad', 'mensaje': 'Identificación digítada ya se encuentra registrada.'})
                    else:
                        return JsonResponse({'result': False, 'mensaje': ''})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": str(ex)})

            elif action == 'addresponsable':
                try:
                    data['title'] = u'Adicionar Responsable del centro de Salud'
                    data['action'] = request.GET['action']
                    form = ResponsableCentroSaludForm()
                    data['form'] = form
                    template = get_template("alu_practicassalud/modal/formresponsable.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editresponsable':
                try:
                    data['title'] = u'Editar responsable'
                    data['action'] = request.GET['action']
                    data['responsable'] = responsable = ResponsableCentroSalud.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = ResponsableCentroSaludForm(initial={
                        'nombre': responsable.persona.nombres,
                        'apellido1': responsable.persona.apellido1,
                        'apellido2': responsable.persona.apellido2,
                        'sexo': responsable.persona.sexo,
                        'nacimiento': responsable.persona.nacimiento,
                        'telefono': responsable.persona.telefono,
                        'telefono_conv': responsable.persona.telefono_conv,
                        'email': responsable.persona.email,
                        'asignacionempresapractica': responsable.asignacionempresapractica,
                        'otraempresaempleadora': responsable.otraempresaempleadora,
                        'cargo': responsable.cargodesempena,
                        'telefono_ofi': responsable.telefonooficina
                    })

                    form.editar(responsable)
                    data['form'] = form
                    template = get_template("alu_practicassalud/modal/formresponsable.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addpreguntapreinscripcion':
                try:
                    data['title'] = u'Adicionar Pregunta para pre-inscripción'
                    data['form'] = PreguntaPreInscripcionPracticasPPForm()
                    return render(request, "alu_practicassalud/addpreguntapreinscripcion.html",
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
                    return render(request, "alu_practicassalud/editpreguntapreinscripcion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'delpreguntapreinscripcion':
                try:
                    data['title'] = u'Eliminar pregunta para pre-inscripción'
                    data['pre'] = PreguntaPreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicassalud/delpreguntapreinscripcion.html",
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
                    return render(request, "alu_practicassalud/preguntas.html", data)
                except Exception as ex:
                    pass

            elif action == 'listapreinscritos':
                try:
                    data['title'] = u'Listado de estudiantes Pre-Inscritos'
                    search = None
                    ids = None
                    idest = 0
                    idcar = 0
                    iditi = 0
                    docu = None
                    data['preinscripcion'] = preinscripcion = PreInscripcionPracticasPP.objects.get(status=True, pk=int(
                        encrypt(request.GET['id'])))
                    carreras = []
                    if preinscripcion.carreras():
                        carreras = preinscripcion.carreras().values_list('id', 'nombre', flat=False)
                    else:
                        if preinscripcion.coordinaciones():
                            carreras = Carrera.objects.values_list('id', 'nombre', flat=False).filter(
                                coordinacion__id__in=preinscripcion.coordinaciones().values_list('id', flat=False))
                    data['carreras'] = carreras
                    preinscripciones = preinscripcion.detallepreinscripcionpracticaspp_set.filter(status=True).order_by(
                        'inscripcion__persona__nombres', 'inscripcion__persona__apellido1')
                    itinerarios = preinscripciones.values_list('itinerariomalla', flat=True)
                    # for pr in preinscripciones:
                    #     pr.recorrido1(request)
                    if 'idest' in request.GET:
                        idest = int(request.GET['idest'])
                        if idest > 0 and idest < 6:
                            preinscripciones = preinscripciones.filter(estado=idest)
                        if idest == 6:
                            lista_solicitantes = DatosEmpresaPreInscripcionPracticasPP.objects.filter(status=True, preinscripcion__in=preinscripciones.values_list('pk', flat=True))
                            preinscripciones = preinscripciones.filter(
                                pk__in=lista_solicitantes.values_list('preinscripcion__pk', flat=True))
                        if idest == 7:
                            lista_solicitantes = SolicitudVinculacionPreInscripcionPracticasPP.objects.filter(status=True, preinscripcion__in=preinscripciones.values_list('pk', flat=True))
                            preinscripciones = preinscripciones.filter(pk__in=lista_solicitantes.values_list('preinscripcion__pk', flat=True))
                    if 'idcar' in request.GET:
                        idcar = int(request.GET['idcar'])
                        if idcar > 0:
                            preinscripciones = preinscripciones.filter(inscripcion__carrera__id=idcar)
                            itinerarios = preinscripciones.values_list('itinerariomalla', flat=True)
                    data['itinerarios'] = ItinerariosMalla.objects.filter(pk__in=itinerarios)
                    if 'iditi' in request.GET:
                        iditi = int(request.GET['iditi'])
                        if iditi > 0:
                            preinscripciones = preinscripciones.filter(itinerariomalla_id=iditi)
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
                    paging = MiPaginador(preinscripciones.order_by('inscripcion__persona__apellido1'), 15)
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
                    data['iditi'] = iditi
                    data['estados'] = ESTADO_PREINSCRIPCIONPPP
                    data['cant_inscritos_busqueda'] = preinscripciones.values('id').count()
                    data['inssolicitudcount'] = preinscripciones.exclude(archivo='').count()
                    data['inspendsolicitudcount'] = preinscripciones.filter(archivo='').count()
                    data['cant_llamadas__pendientes'] = preinscripciones.filter(accion=1).count()
                    data['cant_llamadas_contestadas'] = preinscripciones.filter(accion=2).count()
                    data['cant_llamadas__no_contestadas'] = preinscripciones.filter(accion=3).count()
                    data['cant_llamadas_no_interesados'] = preinscripciones.filter(accion=4).count()
                    data['grupoorden'] = preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first().grupoorden if preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first() else None
                    data['periodosacademicos'] = Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True, fin__lte=datetime.now().date())
                    data['DEBUG'] = DEBUG
                    data['PUEDE_ELIMINAR_PPP'] = variable_valor('PUEDE_ELIMINAR_PPP_SALUD')
                    return render(request, "alu_practicassalud/listapreinscripcionesv3.html", data)
                except Exception as ex:
                    pass

            elif action == 'verobservaciones':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = DetallePreInscripcionPracticasPP.objects.get(pk=request.GET['id'])
                    data['detalle'] = detalle = filtro.seguimientopreprofesionalesinscripcion_set.filter(status=True).order_by('pk')
                    template = get_template("alu_practicassalud/modal/detalleobs.html")
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
                    template = get_template("alu_practicassalud/modal/formobservacion.html")
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
                        (u"ESTUDIANTENTE", 10000),
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
                        "alu_practicassalud/modal/formanilladoobservacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'veranilladoobservaciones':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = PracticasPreprofesionalesInscripcion.objects.get(pk=request.GET['id'])
                    data['detalle'] = detalle = filtro.anilladopracticaspreprofesionalesinscripcion_set.filter(
                        status=True).order_by('pk')
                    template = get_template("alu_practicassalud/modal/detalleanilladodobs.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'missolicitudesempresa':
                try:
                    data['filtro'] = filtro = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    template = get_template(
                        "alu_practicassalud/modal/missolicitudesempresas.html")
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
                    return render(request, "alu_practicassalud/adddetallepreinscripcion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'delpreinscripcion':
                try:
                    data['title'] = u'Eliminar pre-inscripción de Práctica Pre-Profesional'
                    data['pre'] = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicassalud/delpreinscripcion.html", data)
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
                    data['title'] = u'Gestionar Practicas Preprofesionales'
                    data['preinscripcion'] = pre = DetallePreInscripcionPracticasPP.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = PracticasPreprofesionalesInscripcionSaludForm()
                    form.iniciar(pre)
                    form.cargar_estado()
                    data['carrerains'] = carrerains = pre.inscripcion.carrera
                    data['supervisor'] = data['convenio'] = data['acuerdo'] = 0
                    data['form'] = form
                    return render(request, "alu_practicassalud/gestionar_preins_ind.html", data)
                except Exception as ex:
                    pass

            elif action == 'gestionar_preins_masivo':
                try:
                    data['title'] = u'Gestionar Inscripción Masiva Practicas Preprofesionales'
                    data['action'] = 'gestionar_preins_masivo'
                    data['preinscripcion'] = pre = PreInscripcionPracticasPP.objects.get(pk=int(encrypt(request.GET['id'])))
                    qscarreras = pre.carrera.values_list('id', flat=True).all()
                    form = PracticasPreprofesionalesInscripcionMasivoEstudianteSaludForm()
                    form.iniciarform(qscarreras)
                    form.cargar_estado()
                    # form.cargar_tipo()
                    data['form'] = form
                    return render(request, "alu_practicassalud/gestionar_preins_masivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addmasivopreinscripccion':
                try:
                    data['title'] = u'Adicionar Prácticas Preprofesionales'
                    data['action'] = 'addmasivopreinscripccion'
                    data['preinscripcion'] = pre = PreInscripcionPracticasPP.objects.get(pk=int(encrypt(request.GET['id'])))
                    qscarreras = pre.carrera.values_list('id', flat=True).all()
                    form = MasivoPreinscripcionSaludForm()
                    form.iniciarform(qscarreras)
                    form.cargar_estado()
                    data['form'] = form
                    return render(request, "alu_practicassalud/adicionar_preinscripcion_masivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'masivoactualizaempresa':
                try:
                    data['title'] = u'Actualiza Centro salud Prácticas Preprofesionales'
                    data['action'] = 'masivoactualizaempresa'
                    data['preinscripcion'] = pre = PreInscripcionPracticasPP.objects.get(pk=int(encrypt(request.GET['id'])))
                    qscarreras = pre.carrera.values_list('id', flat=True).all()
                    form = MasivoEmpresaSaludForm()
                    form.iniciarform(qscarreras)
                    data['form'] = form
                    data['empresa'] = True
                    return render(request, "alu_practicassalud/actualizar_empresa_masivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'gestionar_tipo_masivo':
                try:
                    data['title'] = u'Gestionar Inscripción Masiva Practicas Preprofesionales'
                    data['action'] = 'gestionar_tipo_masivo'
                    data['tipo'] = tipo = int(request.GET.get('tipo', 0))
                    data['tipoasignar'] = True
                    data['preinscripcion'] = pre = PreInscripcionPracticasPP.objects.get(pk=int(encrypt(request.GET['id'])))
                    qscarreras = pre.carrera.values_list('id', flat=True).all()
                    form = AsignacionMasivoSaludForm()
                    form.iniciarform(qscarreras)
                    form.cargar_estado()
                    form.asignarmasivo(tipo) #1 supervisor #2 tutor
                    data['form'] = form
                    return render(request, "alu_practicassalud/gestionar_preins_masivo.html", data)
                except Exception as ex:
                    pass

            if action == 'buscaritinerario':
                try:
                    listcar = json.loads(request.GET['idcar'])
                    mallas = Malla.objects.filter(carrera__id__in=listcar)
                    qsbase = ItinerariosMalla.objects.filter(status=True, malla__vigente=True, malla__in=mallas)
                    if 'search' in request.GET:
                        qsbase = qsbase.filter(nombre__icontains=request.GET['search'])
                    resp = [{'id': cr.pk, 'text': cr.__str__()+' - [VIGENTE]' if cr.malla.vigente else cr.__str__()} for cr in qsbase.order_by('nombre')]
                    return HttpResponse(json.dumps({'state': True, 'result': resp}))
                except Exception as ex:
                    pass

            if action == 'buscaritinerario2':
                try:
                    idcar = int(request.GET['idcar'])
                    mallas = Malla.objects.filter(carrera__id=idcar)
                    qsbase = ItinerariosMalla.objects.filter(status=True, malla__vigente=True, malla__in=mallas)
                    if 'search' in request.GET:
                        qsbase = qsbase.filter(nombre__icontains=request.GET['search'])
                    resp = [{'id': cr.pk, 'text': cr.__str__()+' - [VIGENTE]' if cr.malla.vigente else cr.__str__()} for cr in qsbase.order_by('nombre')]
                    return HttpResponse(json.dumps({'state': True, 'result': resp}))
                except Exception as ex:
                    pass

            if action == 'buscarestudiantes':
                try:
                    iditinerario = request.GET['itinerario']
                    idperiodopractica = request.GET['idperiodopractica']
                    periodopractica = PreInscripcionPracticasPP.objects.get(id=idperiodopractica)
                    itinerario = ItinerariosMalla.objects.get(id=iditinerario)
                    filtros = Q(status=True, itinerariomalla=itinerario)
                    if estado := int(request.GET.get('estado', 0)):
                        filtros = filtros & (Q(estado=estado))
                    else:
                        filtros = filtros & (Q(estado=1))
                    if 'search' in request.GET:
                        search = request.GET['search']
                        s = search.split(" ")
                        if len(s) == 1:
                            filtros = filtros & (
                                Q(inscripcion__persona__nombres__icontains=search) | Q(
                                    inscripcion__persona__apellido1__icontains=search) | Q(
                                    inscripcion__persona__cedula__icontains=search) | Q(
                                    inscripcion__persona__apellido2__icontains=search))
                        elif len(s) == 2:
                            filtros = filtros & (
                                (Q(inscripcion__persona__nombres__icontains=s[0]) & Q(
                                    inscripcion__persona__nombres__icontains=s[1])) |
                                (Q(inscripcion__persona__apellido1__icontains=s[0]) & Q(
                                    inscripcion__persona__apellido2__icontains=s[1]))
                            )
                    qsbase = periodopractica.detallepreinscripcionpracticaspp_set.filter(filtros)
                    qsbase = qsbase.order_by('inscripcion__persona__nombres', 'inscripcion__persona__apellido1')[:10]
                    resp = [{'id': cr.pk, 'text': f'{cr.get_estado_display()}: {cr.inscripcion.persona.cedula} {cr.inscripcion.__str__()} | {cr.nivelmatriculamalla()} | {str(cr.fecha_creacion.date())}'} for cr in qsbase]
                    return HttpResponse(json.dumps({'state': True, 'result': resp, 'hiti': itinerario.horas_practicas}))
                except Exception as ex:
                    pass

            if action == 'buscar_estudiantesppp_estado':
                try:
                    idperiodopractica = request.GET['idperiodopractica']
                    periodopractica = PreInscripcionPracticasPP.objects.get(id=idperiodopractica)
                    filtros = Q(status=True)
                    if estado := int(request.GET.get('estado', 0)):
                        filtros = filtros & (Q(estado=estado))
                    if 'search' in request.GET:
                        search = request.GET['search']
                        s = search.split(" ")
                        if len(s) == 1:
                            filtros = filtros & (
                                Q(inscripcion__persona__nombres__icontains=search) | Q(
                                    inscripcion__persona__apellido1__icontains=search) | Q(
                                    inscripcion__persona__cedula__icontains=search) | Q(
                                    inscripcion__persona__apellido2__icontains=search))
                        elif len(s) == 2:
                            filtros = filtros & (
                                (Q(inscripcion__persona__nombres__icontains=s[0]) & Q(
                                    inscripcion__persona__nombres__icontains=s[1])) |
                                (Q(inscripcion__persona__apellido1__icontains=s[0]) & Q(
                                    inscripcion__persona__apellido2__icontains=s[1]))
                            )
                    qsbase = periodopractica.detallepreinscripcionpracticaspp_set.filter(filtros)
                    qsbase = qsbase.distinct('inscripcion__persona__nombres', 'inscripcion__persona__apellido1').order_by('inscripcion__persona__nombres', 'inscripcion__persona__apellido1')[:10]
                    resp = [{'id': cr.pk, 'text': f'{cr.get_estado_display()}: {cr.inscripcion.persona.cedula} {cr.inscripcion.__str__()} | {cr.nivelmatriculamalla()} | {str(cr.fecha_creacion.date())}'} for cr in qsbase]
                    return HttpResponse(json.dumps({'state': True, 'result': resp}))
                except Exception as ex:
                    pass

            if action == 'buscar_estudiantessalud':
                try:
                    idcar = int(request.GET['carrera'])
                    filtros = Q(status=True, carrera__id=idcar)
                    if 'search' in request.GET:
                        search = request.GET['search']
                        s = search.split(" ")
                        if len(s) == 1:
                            filtros = filtros & (
                                Q(persona__cedula__icontains=search) | Q(persona__pasaporte__icontains=search) |
                                Q(persona__nombres__icontains=search) | Q( persona__apellido1__icontains=search) |
                                Q(persona__cedula__icontains=search) | Q(persona__apellido2__icontains=search))
                        elif len(s) == 2:
                            filtros = filtros & (
                                (Q(persona__nombres__icontains=s[0]) & Q(persona__nombres__icontains=s[1])) |
                                (Q(persona__apellido1__icontains=s[0]) & Q(persona__apellido2__icontains=s[1]))
                            )
                    qsbase = Inscripcion.objects.filter(filtros)
                    qsbase = qsbase.order_by('persona__nombres', 'persona__apellido1')[:10]
                    resp = [{'id': cr.pk, 'text': f'{cr.persona.cedula} - {cr.persona.nombre_completo_inverso()} - {cr.carrera.alias} - {cr.modalidad.nombre} - {cr.sesion.nombre}'} for cr in qsbase]
                    return HttpResponse(json.dumps({'state': True, 'result': resp}))
                except Exception as ex:
                    pass

            elif action == 'listaprofesordistributivomasivo':
                try:
                    # listaidcriterio = [6, 154, 144]
                    listaidcriterio, listaprofesor, practicasprofesionales, inscripcion, itinerarios, id = [6, 23, 167, 83, 31, 153, 154], [], None, None, json.loads(request.GET['iditinerario']), request.GET.get('id', '')
                    preinscripcion = PreInscripcionPracticasPP.objects.get(pk=int(request.GET['preinscripcion']))
                    # ADICIONAR PRACTICA PREPROFESIONALES
                    bandera = int(request.GET.get('bandera', 0))
                    if bandera == 1: carreras = Carrera.objects.filter(pk=int(request.GET['idcarr']))
                    else: carreras = Carrera.objects.filter(pk__in=json.loads(request.GET['idcarr']))

                    fechadesde = request.GET['fd']
                    fechahasta = request.GET['fh']
                    carrera_id = request.GET['idcarr']
                    periodo = request.session['periodo']

                    profesoresdistributivo = ProfesorDistributivoHoras.objects.filter(detalledistributivo__criteriodocenciaperiodo__criterio__id__in=listaidcriterio,
                                                                                      detalledistributivo__actividaddetalledistributivo__actividaddetalledistributivocarrera__carrera__in=carreras,
                                                                                      status=True, periodo=periodo).distinct()

                    # if profesoresdistributivo and iditinerario:
                    #     profesoresdistributivo = profesoresdistributivo.filter(detalledistributivo__actividaddetalledistributivo__actividaddetalledistributivocarrera__itinerariosactividaddetalledistributivocarrera__itinerario_id=iditinerario)
                    # else:
                    #     profesoresdistributivo = []
                    for x in profesoresdistributivo:
                        for c in carreras:
                            listaprofesor.append([u'%s' % x.profesor.id, u'%s - (%s) - hor.(%s)' % (
                                x.profesor.persona.nombre_completo_inverso(), x.periodo.nombre,
                                x.horas_docencia_segun_criterio_carrera(listaidcriterio, c.id))])

                    # Periodo de evidencias
                    periodoevidencia = CabPeriodoEvidenciaPPP.objects.filter(
                        (Q(fechainicio__lte=fechadesde) & Q(fechafin__gte=fechadesde)) | (
                                Q(fechafin__lte=fechahasta) & Q(fechafin__gte=fechahasta))).distinct()
                    listape = []
                    for p in CabPeriodoEvidenciaPPP.objects.values_list('id', 'nombre').filter(status=True, periodoevidenciapracticaprofesionales__carrera__in=carreras).distinct('id').order_by('id'):
                        listape.append([p[0], p[1]])
                    idperiodoevidencia = 0
                    if extconf := preinscripcion.extpreinscripcionpracticaspp_set.filter(status=True).first():
                        idperiodoevidencia = extconf.periodoevidencia.id if extconf.periodoevidencia else 0

                    listaaempresap = []
                    for ep in AsignacionEmpresaPractica.objects.values_list('id', 'nombre').filter(status=True).order_by('nombre'):
                        listaaempresap.append([ep[0], ep[1]])

                    max_value = max(itinerarios) if isinstance(itinerarios, list) else itinerarios
                    itinerario = ItinerariosMalla.objects.get(pk=max_value)
                    # MUESTRA EL MENSAJE DEL PERIODO
                    data = {"result": "ok", "results": listaprofesor, "mensaje": u'%s %s' % (
                        "Según las fechas de la Práctica Preprofesionales está en el periodo", periodo),
                            'periodoevidencias': listape, 'listaaempresap': listaaempresap,
                            # 'listaacuerdo': listaacuerdo, 'listaconvenio': listaconvenio,
                            'perevid': idperiodoevidencia if idperiodoevidencia > 0 else periodoevidencia[0].id if periodoevidencia else 0,
                            'numerohora': itinerario.horas_practicas if itinerario else 0
                            }
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

            elif action == 'listaresponables':
                try:
                    empresa = request.GET['ide']
                    filtro = Q(status=True)
                    lugarpractica = 0
                    if empresa and int(empresa) > 0:
                        emp = AsignacionEmpresaPractica.objects.get(pk=int(empresa))
                        filtro = filtro & Q(asignacionempresapractica=emp)
                        if emp.canton:
                            lugarpractica = emp.canton.id
                    listaresponable = []
                    for ep in ResponsableCentroSalud.objects.values_list('id', 'persona__apellido1', 'persona__apellido2', 'persona__nombres', 'asignacionempresapractica__nombre').filter(filtro).order_by('persona__apellido1'):
                        persona = f"{ep[1]} {ep[2]} {ep[3]} - {ep[4]}" if not empresa else f"{ep[1]} {ep[2]} {ep[3]}"
                        listaresponable.append([ep[0], persona])
                    data = {"result": "ok", 'listaresponable': listaresponable, 'lugarpractica':lugarpractica}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

            elif action == 'obtenerofertas':
                try:
                    data = {}
                    listaofertas = []
                    iditinerario = request.GET.get('iditinerario', '')
                    if iditinerario:
                        resultado = ConfiguracionInscripcionPracticasPP.objects.annotate(inscritos=Count('historialinscricionoferta__id', filter=F('historialinscricionoferta__status'))
                                                                                        ).filter(itinerariomalla__id=iditinerario, estado=2, cupo__gt=F('inscritos'))
                        for res in resultado:
                            listaofertas.append([res.id, str(res)])
                        data = {"result": "ok", "listaofertas": listaofertas}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

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
                    template = get_template("alu_practicassalud/informesmensualesdocentes.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verinscritos':
                try:
                    actividad = int(request.GET['actividad'])
                    data['actividad'] = actividad = ActividadDetalleDistributivoCarrera.objects.get(pk=actividad)
                    data['listado'] = listado = actividad.tutoriasdocentes_inscrito()
                    data['liscount'] = listado.count()
                    template = get_template("alu_practicassalud/listadoinscritosactividad.html")
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
                    template = get_template("alu_practicassalud/listadoinscritossupervisor.html")
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
                    template = get_template("alu_practicassalud/listadoagendadocente.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'veragendaconvocados':
                try:
                    data['id'] = id = int(request.GET['id'])
                    data['instancia'] = instancia = AgendaPracticasTutoria.objects.get(pk=id)
                    template = get_template("alu_practicassalud/modal/verconvocados.html")
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
                return render(request, "alu_practicassalud/viewdocentes.html", data)

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
                    return render(request, "alu_practicassalud/viewdocentessincarrera.html", data)
                except Exception as ex:
                    pass

            elif action == 'additinerariodocente':
                try:
                    data['filtro'] = filtro = ActividadDetalleDistributivoCarrera.objects.get(pk=int(request.GET['id']))
                    listaitinerarios = ItinerariosActividadDetalleDistributivoCarrera.objects.filter(status=True, actividad=filtro)
                    form = ItinerarioMallaDocenteDistributivoForm(initial={'itinerario': listaitinerarios.values_list('itinerario__id', flat=True)})
                    form.fields['itinerario'].queryset = ItinerariosMalla.objects.filter(status=True, malla__carrera=filtro.carrera).distinct()
                    data['form2'] = form
                    template = get_template("alu_practicassalud/modal/formitinerarios.html")
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
                return render(request, "alu_practicassalud/viewsupervisores.html", data)

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
                    return render(request, "alu_practicassalud/gestionar_preins_indmasivo.html",
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
                    return render(request, "alu_practicassalud/editgestion_preins_ind.html", data)
                except Exception as ex:
                    pass

            elif action == 'conffirmadirectorvinculacion':
                try:
                    data['title'] = u'Personal Vinculación'
                    # data['nopermitido'] = ConfiguracionFirmaPracticasPreprofesionales.objects.filter(status=True, activo=True).exists()
                    data['directores'] = ConfiguracionFirmaPracticasPreprofesionales.objects.filter(
                        status=True).order_by('id')
                    return render(request, "alu_practicassalud/directoresvinculacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'adddirectorvinculacion':
                try:
                    data['title'] = u'Adicionar Personal de Vinculación'
                    form = DirectorVinculacionFirmaForm()
                    data['form'] = form
                    # form.editar()
                    return render(request, "alu_practicassalud/adddirectorvinculalacion.html",
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
                    return render(request, "alu_practicassalud/editdirectorvinculacion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'deletedirectorvinculacion':
                try:
                    data['title'] = u'Eliminar Director de Vinculación'
                    data['firma'] = ConfiguracionFirmaPracticasPreprofesionales.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicassalud/deletedirectorvinculacion.html",
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
                        'alu_practicassalud/informe_carta_vinculacion.html',
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
                                        Q(carrera__nombre__icontains=search) | Q(
                                    memo__icontains=search) | Q(
                                    representante__icontains=search)),
                                    Q(status=True))
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
                    return render(request, "alu_practicassalud/viewcartavinculacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcartavinculacion':
                try:
                    data['title'] = u'Adicionar Nueva Carta de Vinculación'
                    form = CartaVinculacionForm(initial={'fecha': datetime.now()})
                    data['form'] = form
                    return render(request, "alu_practicassalud/addcartavinculacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcartavinculacion':
                try:
                    data['title'] = u'Editar Carta de Vinculación'
                    data['cartavinculacion'] = cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = CartaVinculacionForm(initial={
                        'fecha': cartavinculacion.fecha,
                        'memo': cartavinculacion.memo,
                        'convenio': cartavinculacion.convenio,
                        'acuerdo': cartavinculacion.acuerdo,
                        'representante': cartavinculacion.representante,
                        'cargo': cartavinculacion.cargo,
                        'director': cartavinculacion.director,
                        'archivo': cartavinculacion.archivo,
                    })
                    data['form'] = form
                    return render(request, "alu_practicassalud/editcartavinculacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'delcartavinculacion':
                try:
                    data['title'] = u'Eliminar carta de vinculación'
                    data['cartavinculacion'] = CartaVinculacionPracticasPreprofesionales.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicassalud/delcartavinculacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'vercartavinculacion':
                try:
                    data['cartavinculacion'] = cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['inscripciones'] = cartavinculacion.detallecartainscripcion_set.filter(status=True)
                    # data['itinerarios'] = cartavinculacion.detallecartaitinerario_set.filter(status=True)

                    return render(request, "alu_practicassalud/modalvercartavinculacion.html",
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
                        'alu_practicassalud/informe_carta_vinculacion.html',
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
                                  "alu_practicassalud/viewconfiguracionevidenciapractica.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'addconfevidenciahomologacion':
                try:
                    data[
                        'title'] = u'Adicionar configuración de evidencias para homologación de Práctica Pre-Profesionales'
                    data['form'] = ConfiguracionEvidenciaHomologacionPracticaForm()
                    return render(request, "alu_practicassalud/addconfevidenciahomologacion.html",
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
                                  "alu_practicassalud/editconfevidenciahomologacion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'delconfevidenciahomologacion':
                try:
                    data[
                        'title'] = u'Eliminar configuración de evidencias para homologación de Práctica Pre-Profesionales '
                    data['configuracionevidencia'] = ConfiguracionEvidenciaHomologacionPractica.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicassalud/delconfevidenciahomologacion.html",
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
                    return render(request, "alu_practicassalud/viewevidenciahomologacion.html",
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
                    return render(request, "alu_practicassalud/addevidenciahomologacion.html",
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
                    return render(request, "alu_practicassalud/editevidenciahomologacion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'delevidenciahomologacion':
                try:
                    data['title'] = u'Eliminar evidencia para homologación'
                    data['evidencia'] = evidencia = EvidenciaHomologacionPractica.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicassalud/delevidenciahomologacion.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'delarchivoevidenciahomologacion':
                try:
                    data['title'] = u'Eliminar archivo de evidencias para homologación'
                    data['evidencia'] = EvidenciaHomologacionPractica.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request,
                                  "alu_practicassalud/delarchivoevidenciahomologacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'informehomologacion':
                try:
                    data['title'] = u'Informes para la Homologación'
                    data['apertura'] = apertura = AperturaPracticaPreProfesional.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['carreras'] = carreras = apertura.carreras_todo()
                    data['cantidad_carreras'] = len(carreras)
                    return render(request, "alu_practicassalud/viewinformehomologacion.html",
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
                    return render(request, "alu_practicassalud/viewdocumentorequerido.html", data)
                except Exception as ex:
                    pass

            elif action == 'solicitantes':
                data['title'] = u'Solicitantes Homologación'
                data['id'] = id = int(request.GET['id'])
                data['apertura'] = apertura = AperturaPracticaPreProfesional.objects.get(pk=id)
                carreras = apertura.carrerahomologacion_set.filter(status=True)
                valcarreras = False
                if es_decano or es_director_carr:
                    #     cordecano = querydecano.first().coordinacion
                    #     coordinacion_carreras = cordecano.carreras().values_list('id', flat=True)
                    #     carreras = carreras.filter(carrera__in=coordinacion_carreras)
                    #     valcarreras = True
                    # if es_director_carr:
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
                return render(request, "alu_practicassalud/solicitanteshomologacion.html", data)

            elif action == 'editarsolicitudempresa':
                try:
                    data['filtro'] = filtro = DatosEmpresaPreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    form = SolicitudEmpresaPreinscripcionForm(initial=model_to_dict(filtro))
                    data['form2'] = form
                    template = get_template("alu_practicassalud/modal/formsolicitudempresa.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'validarsolicitudempresa':
                try:
                    data['filtro'] = filtro = DatosEmpresaPreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    form = ValidarSolicitudEmpresaForm()
                    data['form2'] = form
                    template = get_template(
                        "alu_practicassalud/modal/validarsolicitudempresa.html")
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
                    template = get_template("alu_practicassalud/modal/validarsolicitudasignaciontutor.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'solicitudpdf':
                try:
                    data['title'] = 'SOLICITUD EMPRESA'
                    data['hoy'] = datetime.now()
                    data['filtro'] = filtro = DatosEmpresaPreInscripcionPracticasPP.objects.get(pk=encrypt(request.GET['pk']))
                    fecha = filtro.fecha_revision
                    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                    if responsablevinculacion:
                        data['responsablevinculacion'] = responsablevinculacion
                        # firma = FirmaPersona.objects.filter(persona=responsablevinculacion, tipofirma=2, status=True).first()
                        firma = responsablevinculacion.archivo.url if responsablevinculacion.archivo else None
                        data['firmaimg'] = firma if firma else None
                    template_pdf = 'alu_preinscripcionppp/solicitudpdf.html'
                    nombrepersona = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode((filtro.preinscripcion.inscripcion.persona.__str__()).replace(' ', '_')))
                    nombredocumento = 'SOLICITUD_EMPRESA_{}_{}'.format(nombrepersona, random.randint(1, 100000).__str__())
                    directory = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'solicitudempresas')
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
                    return conviert_html_to_pdf_name(
                        template_pdf,
                        {
                            'pagesize': 'A4',
                            'data': data,
                        },
                        nombredocumento
                    )
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
                return render(request, "alu_practicassalud/asignaciontutor/viewasignacion.html", data)

            elif action == 'generaracuerdo':
                data['title'] = u'Generar Acuerdo'
                data['filtro'] = filtro = SolicitudVinculacionPreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                data['nombre_empresa'] = nombre_empresa = filtro.empresanombre
                data['form'] = AcuerdoCompromisoAsignacionTutorForm()
                data['empresas_coincidencias'] = lista_empresas = EmpresaEmpleadora.objects.filter(status=True, nombre__unaccent__icontains=nombre_empresa).order_by('-pk')
                data['primer_elemento'] = lista_empresas.first()
                return render(request, "alu_practicassalud/asignaciontutor/generaracuerdo.html", data)

            elif action == 'validarsolicitud':
                data['title'] = u'Validar Solicitud'
                data['filtro'] = filtro = SolicitudVinculacionPreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                data['form'] = AcuerdoCompromisoAsignacionTutorForm()
                return render(request, "alu_practicassalud/asignaciontutor/validarsolicitud.html", data)

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
                    template = get_template('alu_practicassalud/asignaciontutor/formempresa.html')
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
                    return render(request, "alu_practicassalud/asignaciontutor/formasignacion.html", data)
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
                return render(request, "alu_practicassalud/viewsolicitudempresas.html", data)

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
                    return render(request, "alu_practicassalud/viewdocumentositinerarios.html",
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
                    template = get_template('alu_practicassalud/modal/addcarreras.html')
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
                    template = get_template('alu_practicassalud/modal/itinerarios.html')
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
                        'alu_practicassalud/modal/documentoshomologacionsolicitud.html')
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
                    template = get_template('alu_practicassalud/modal/modalproceso.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            elif action == 'verhistorial':
                try:
                    solicitud = SolicitudHomologacionPracticas.objects.get(pk=int(request.GET['id']))
                    data['title'] = u'Historial.'
                    data['historial'] = HistoricoRevisionesSolicitudHomologacionPracticas.objects.filter(solicitud=solicitud).order_by('-fecha_creacion')
                    template = get_template('alu_practicassalud/modal/verHistorial.html')
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

                    template = get_template('alu_practicassalud/modal/validardirectordecano.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            elif action == 'finalizarproceso':
                try:
                    data['filtro'] = solicitud = SolicitudHomologacionPracticas.objects.get(pk=int(request.GET['id']))
                    form = FinalizarHomologacionForm(initial=model_to_dict(solicitud))
                    form.bloquear()
                    data['form2'] = form
                    template = get_template("alu_practicassalud/modal/finalizarhomologacion.html")
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
                    template = get_template("alu_practicassalud/addinformecarrera.html")
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
                    template = get_template("alu_practicassalud/addresolucioncarrera.html")
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
                    return render(request, "alu_practicassalud/viewsolicitudcarrera.html", data)
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
                        "alu_practicassalud/modalverevidenciahomologacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'asignacionempresa':
                try:
                    data['title'] = u'Asignación de Empresa en Prácticas'
                    search = None
                    url_vars = f'&action={action}'
                    asignacionempresapractica = AsignacionEmpresaPractica.objects.filter(status=True)
                    data['cantones'] = asignacionempresapractica.values_list('canton_id', 'canton__nombre').distinct('canton_id').exclude(canton__isnull=True)
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search:
                            s = search.split(" ")
                            if len(s) == 1:
                                asignacionempresapractica = asignacionempresapractica.filter(Q(nombre__icontains=s[0]), Q(status=True))
                            elif len(s) == 2:
                                asignacionempresapractica = asignacionempresapractica.filter(
                                    Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(status=True))
                            elif len(s) == 3:
                                asignacionempresapractica = asignacionempresapractica.filter(
                                    Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(
                                        nombre__icontains=s[2]), Q(status=True))
                            else:
                                asignacionempresapractica = asignacionempresapractica.filter(
                                    Q(nombre__icontains=search), Q(status=True))
                            url_vars += f"&s={search}"

                    if 'idc' in request.GET:
                        idc = int(request.GET['idc'])
                        if idc > 0:
                            asignacionempresapractica = asignacionempresapractica.filter(canton_id=idc)
                            url_vars += f"&idc={idc}"
                            data['idc'] = idc

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
                    data['url_vars'] = url_vars
                    return render(request, "alu_practicassalud/viewasignacionempresapractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'addasignacionempresa':
                try:
                    data['title'] = u'Adicionar asignación de Empresa en Prácticas'
                    data['form'] = AsignacionEmpresaPracticaForm()
                    return render(request, "alu_practicassalud/addasignacionempresa.html", data)
                except Exception as ex:
                    pass

            elif action == 'editasignacionempresa':
                try:
                    data['title'] = u'Editar asignación de Empresa en Prácticas'
                    data['asignacionempresa'] = asignacionempresa = AsignacionEmpresaPractica.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    form = AsignacionEmpresaPracticaForm(initial=model_to_dict(asignacionempresa))
                    data['form'] = form
                    data['action'] = action
                    return render(request, "alu_practicassalud/editasignacionempresa.html", data)
                except Exception as ex:
                    pass

            elif action == 'actualizaubicacionempresa':
                try:
                    data['title'] = u'Editar asignación de Empresa en Prácticas'
                    data['asignacionempresa'] = asignacionempresa = AsignacionEmpresaPractica.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['ubicacionempresa'] = ubicacionempresa = UbicacionEmpresaPractica.objects.filter(status=True, asignacionempresapractica=asignacionempresa).first()
                    form = None
                    if ubicacionempresa:
                        form = UbicacionEmpresaPracticaForm(initial=model_to_dict(ubicacionempresa))
                    else:
                        form = UbicacionEmpresaPracticaForm()
                        form.fields['asignacionempresapractica'].initial = asignacionempresa
                    form.fields['asignacionempresapractica'].widget.attrs = {'disabled': 'disabled'}
                    data['form'] = form
                    data['action'] = action
                    return render(request, "alu_practicassalud/editasignacionempresa.html", data)
                except Exception as ex:
                    pass

            elif action == 'delasignacionempresa':
                try:
                    data['title'] = u'Eliminar asignación de Empresa en Prácticas'
                    data['asignacionempresa'] = AsignacionEmpresaPractica.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_practicassalud/delasignacionempresa.html", data)
                except Exception as ex:
                    pass

            elif action == 'culminartutoria':
                try:
                    data['title'] = u'Culminar tutoria'
                    data['practica'] = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicassalud/culminatutoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'traertutorias':
                try:
                    data['title'] = u'Culminar tutoria'
                    data['practica'] = practica = PracticasPreprofesionalesInscripcion.objects.get(
                        pk=int(request.GET['id']))
                    data['tutorias'] = PracticasTutoria.objects.filter(practica=practica, status=True)
                    template = get_template("alu_practicassalud/modaltutoria.html")
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
                    template = get_template("alu_practicassalud/moverevidencias.html")
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
                    template = get_template("alu_practicassalud/eliminarmasivopre.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'migrarmasivoperiodo':
                try:
                    data = {}
                    nivel_filtro = 7
                    data['action'] = request.GET['action']
                    data['periodo_masivo'] = periodo_masivo = int(request.GET['periodo_masivo'])
                    data['periodo_masivo'] = nivel_masivo = int(request.GET['nivel_masivo'])
                    data['preinscripcion'] = preinscripcion = PreInscripcionPracticasPP.objects.get(status=True, pk=int(encrypt(request.GET['id'])))
                    listado_carreras = preinscripcion.carrera.all()

                    listado_estudiantes_enpracticas = DetallePreInscripcionPracticasPP.objects.filter(preinscripcion__carrera__in=listado_carreras, estado__in=[1, 2, 5], status=True)
                    listado_estudiantes_preacticasfaltantes = DetallePreInscripcionPracticasPP.objects.filter(preinscripcion__carrera__in=listado_carreras, estado__in=[3, 4, 6], status=True)
                    inscripciones_excluir = Inscripcion.objects.filter(status=True, pk__in=listado_estudiantes_enpracticas.values_list('inscripcion_id', flat=True)).exclude(pk__in=listado_estudiantes_preacticasfaltantes.values_list('inscripcion_id', flat=True))

                    faltan_itinerarios = [] #Comprobar si falta algún itinerario al estudiante excluido
                    for ins in inscripciones_excluir:
                        itinerarios_estudiante = ins.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.filter(status=True)
                        if nivel_masivo > 0:
                            itinerarios_estudiante = itinerarios_estudiante.filter(nivel=nivel_masivo)
                        for iti in itinerarios_estudiante:
                            if not ins.detallepreinscripcionpracticaspp_set.values_list('id', flat=True).filter(status=True, itinerariomalla=iti).exists():
                                faltan_itinerarios.append(ins.id)

                    if nivel_masivo > 0: nivel_filtro = nivel_masivo
                    inscripciones = Inscripcion.objects.filter(status=True, matricula__nivel__periodo=periodo_masivo, carrera__in=listado_carreras, inscripcionnivel__nivel__orden__gte=nivel_filtro
                                                               ).exclude(pk__in=inscripciones_excluir.values_list('id', flat=True).exclude(pk__in=faltan_itinerarios))

                    listaestudiantespracticaspendientes = []
                    listaestppp = []
                    listaestpppnocumplen = []
                    listaestpppcumplen = []
                    for ins in inscripciones.order_by('inscripcion__persona__nombres', 'inscripcion__persona__apellido1'):
                        valida_estudiante = False
                        if str(ins.persona.cedula) in variable_valor('VALIDA_CASO') or str(ins.persona.pasaporte) in variable_valor('VALIDA_CASO'):
                            cccc = 'este es el caso'
                        # matricula = ins.matricula_set.filter(status=True)[0]
                        matricula = ins.matricula_set.filter(status=True, nivel__periodo=periodo_masivo).first()
                        if matricula:
                            if nivel_masivo > 0:
                                if nivel_masivo == 7 and matricula.nivelmalla.orden <= 7: valida_estudiante = True
                                elif nivel_masivo == 8 and matricula.nivelmalla.orden >= 8 and asignaturas_aprobadas_primero_penultimo_nivel(ins.id):
                                    valida_estudiante = True
                            else:
                                if matricula.nivelmalla.orden >= 8:
                                    if asignaturas_aprobadas_primero_penultimo_nivel(ins.id):
                                        valida_estudiante = True
                                else:
                                    valida_estudiante = True
                        inscripcionvalida, estudiante, itinerarios, validado = cumple_criterios_practicas(ins, matricula, preinscripcion, valida_estudiante, nivel_masivo)
                        if inscripcionvalida:
                            listaestudiantespracticaspendientes.append([estudiante.id, list(itinerarios.values_list('id', flat=True)) if itinerarios else []])
                            resp_itinerarios = []
                            for iti in itinerarios:
                                resp_itinerarios.append([iti[0], iti[1]])
                            #eEstudiante = str(estudiante) +', Nivel matricula '+ str(matricula.nivelmalla.orden) +', Nivel malla '+ str(estudiante.mi_nivel().nivel.orden)
                            listaestppp.append([str(estudiante.persona.cedula) if estudiante.persona.cedula else str(estudiante.persona.pasaporte), str(estudiante), str(estudiante.carrera), resp_itinerarios])
                            listaestpppcumplen.append([estudiante.id, list(itinerarios.values_list('id', flat=True)) if itinerarios else []])
                        else:
                            if validado:
                                listaestpppnocumplen.append([estudiante.id, list(itinerarios.values_list('id', flat=True)) if itinerarios else []])
                    data['cantinscripcion'] = len(listaestudiantespracticaspendientes)
                    data['aDataestppp'] = listaestudiantespracticaspendientes
                    data['listaestppp'] = listaestppp
                    data['cantnocumplen'] = len(listaestpppnocumplen)
                    data['listaestpppnocumplen'] = listaestpppnocumplen
                    data['listaestpppcumplen'] = listaestpppcumplen
                    template = get_template("alu_practicassalud/modal/masivomigrar_periodocarrera.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            elif action == 'estudiantes_preinscribir_excel':
                try:
                    if 'ids' in request.GET:
                        listado_estudiantes = json.loads(request.GET['ids'])
                        bandera = int(request.GET['band'])
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
                        ws = wb.add_sheet('Datos personales')
                        ws.write_merge(0, 0, 0, 19, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                        ws.write(1, 0, 'Total de estudiantes: %s' % len(listado_estudiantes), font_style)
                        response = HttpResponse(content_type="application/ms-excel")
                        nombre = 'aptos_' if bandera == 1 else 'no_aptos_'
                        response['Content-Disposition'] = 'attachment; filename=Datos_personales_estudiantes_' + nombre + random.randint(1, 10000).__str__() + '.xls'
                        columns = [
                            (u"DOCUMENTO", 3000),
                            (u"ESTUDIANTE", 10000),
                            (u"CELULAR", 5000),
                            (u"CONVENCIONAL", 5000),
                            (u"GÉNERO", 5000),
                            (u"EMAIL", 10000),
                            (u"EMAIL INSTITUCIONAL", 10000),
                            (u"PAIS", 5000),
                            (u"PROVINCIA", 6000),
                            (u"CANTON", 6000),
                            (u"PARROQUIA", 6000),
                            (u"DIRECCION DOMICILIARIA", 15000),
                            (u"RECORD ACADEMICO", 5500),
                            (u"¿TIENE DISPACADIDAD?", 6000),
                            (u"¿TIPO DISPACADIDAD?", 10000),
                            (u"¿PPL?", 2000),
                            (u"DETALLE PPL", 10000),
                            (u"CARRERA", 15000),
                            (u"NIVEL MALLA", 4000),
                            (u"NIVEL MATRICULA", 5000),
                            (u"JORNADA", 5000),
                            (u"HASTA 7MO NIVEL APROBADO", 6000),
                            (u"INGLES APROBADO", 5000),
                            (u"COMPUTACIÓN APROBADO", 5000),
                            (u"VINCULACIÓN H.COMPLETAS", 5000),
                            (u"CANT. ITINERARIOS", 5000),
                            (u"ITINERARIOS", 5000),
                        ]
                        row_num = 3
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        row_num = 4
                        for i in listado_estudiantes:
                            insc = Inscripcion.objects.get(pk=int(i[0]))
                            ws.write(row_num, 0, '%s' % insc.persona.cedula if insc.persona.cedula else insc.persona.pasaporte, font_style2)
                            ws.write(row_num, 1, '%s' % insc.persona.nombre_completo_inverso() if insc.persona else '', font_style2)
                            ws.write(row_num, 2, '%s' % insc.persona.telefono if insc.persona.telefono else '', font_style2)
                            ws.write(row_num, 3, '%s' % insc.persona.telefono_conv if insc.persona.telefono_conv else '', font_style2)
                            if insc.persona.sexo:
                                ws.write(row_num, 4, '%s' % "MASCULINO" if insc.persona.sexo.id == 2 else "FEMENINO", font_style2)
                            else:
                                ws.write(row_num, 4, 'NO TIENE SEXO', font_style2)
                            ws.write(row_num, 5, '%s' % insc.persona.email if insc.persona.email else "", font_style2)
                            ws.write(row_num, 6, '%s' % insc.persona.emailinst if insc.persona.emailinst else "", font_style2)
                            ws.write(row_num, 7, '%s' % insc.persona.pais, font_style2)
                            ws.write(row_num, 8, '%s' % insc.persona.provincia, font_style2)
                            ws.write(row_num, 9, '%s' % insc.persona.canton.nombre if insc.persona.canton else "", font_style2)
                            ws.write(row_num, 10, '%s' % insc.persona.parroquia, font_style2)
                            ws.write(row_num, 11, '%s' % insc.persona.direccion_corta(), font_style2)
                            ws.write(row_num, 12, insc.promedio_record(), font_style2)
                            tienediscapacidad = 'NO'
                            tipodiscapacidad = 'NINGUNA'
                            ppl = 'NO'
                            pplobs = 'NINIGUNA'
                            if insc.persona.tiene_discapasidad():
                                tienediscapacidad = 'SI'
                                if insc.persona.tiene_discapasidad().filter(tipodiscapacidad__isnull=False).exists():
                                    tipodiscapacidad = insc.persona.tiene_discapasidad().first().tipodiscapacidad.nombre
                                else:
                                    tipodiscapacidad = 'NO DETERMINADA'
                            ws.write(row_num, 13, tienediscapacidad, font_style2)
                            ws.write(row_num, 14, tipodiscapacidad, font_style2)
                            if insc.persona.ppl:
                                ppl = 'SI'
                                pplobs = insc.persona.observacionppl
                            ws.write(row_num, 15, ppl, font_style2)
                            ws.write(row_num, 16, pplobs, font_style2)
                            ws.write(row_num, 17, '%s' % insc.carrera.nombre if insc.carrera else '', font_style2)
                            ws.write(row_num, 18, '%s' % insc.mi_nivel() if insc.mi_nivel() else '', font_style2)
                            matricula = insc.matricula_set.filter(status=True)[0]
                            ws.write(row_num, 19, '%s' % matricula.nivelmalla if matricula else '', font_style2)
                            ws.write(row_num, 20, '%s' % insc.nivelperiodo(periodo).nivel.sesion.nombre if insc.nivelperiodo(periodo) else '', font_style2)
                            ws.write(row_num, 21, '%s' % 'SI' if asignaturas_aprobadas_primero_septimo_nivel(insc.id) else 'NO', font_style2)
                            ws.write(row_num, 22, '%s' % 'SI' if haber_cumplido_horas_creditos_vinculacion(insc.id) else 'NO', font_style2)
                            ws.write(row_num, 23, '%s' % 'SI' if haber_aprobado_modulos_ingles(insc.id) else 'NO', font_style2)
                            ws.write(row_num, 24, '%s' % 'SI' if haber_aprobado_modulos_computacion(insc.id) else 'NO', font_style2)
                            ws.write(row_num, 25, '%s' % len(i[1]), font_style2)
                            resp = ''
                            for iti in i[1]:
                                itinerario = ItinerariosMalla.objects.get(pk=int(iti))
                                resp += str(itinerario.id) + ' - ' + str(itinerario.nombre)+'; '
                            ws.write(row_num, 26, '%s' % resp, font_style2)
                            row_num += 1
                        wb.save(response)
                        return response
                    else:
                        pass
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            elif action == 'estudiantes_ordenprioridad_excel':
                try:
                    if 'ids' in request.GET:
                        listado_estudiantes = OrdenPrioridadInscripcion.objects.filter(pk__in=json.loads(request.GET['ids']))
                        bandera = int(request.GET['band'])
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
                        ws = wb.add_sheet('Orden estudiantes')
                        ws.write_merge(0, 0, 0, 19, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                        ws.write(1, 0, 'Total de estudiantes: %s' % listado_estudiantes.count(), font_style)
                        response = HttpResponse(content_type="application/ms-excel")
                        nombre = 'orden_prioridad_'
                        response['Content-Disposition'] = 'attachment; filename=Datos_estudiantes_' + nombre + random.randint(1, 10000).__str__() + '.xls'
                        columns = [
                            (u"ORDEN", 1500),
                            (u"DOCUMENTO", 3500),
                            (u"ESTUDIANTE", 10000),
                            (u"PRIORIDAD", 8000),
                            (u"RECORD ACADEMICO", 5500),
                            (u"TURNO ACTIVO", 4000),
                            (u"CELULAR", 4000),
                            (u"CONVENCIONAL", 4500),
                            (u"GÉNERO", 4000),
                            (u"EMAIL", 10000),
                            (u"EMAIL INSTITUCIONAL", 10000),
                            (u"CARRERA", 15000),
                            (u"NIVEL MALLA", 3000),
                            (u"NIVEL MATRICULA", 3000),
                            (u"JORNADA", 5000),
                            (u"HASTA 7MO NIVEL APROBADO", 6000),
                            (u"INGLES APROBADO", 5000),
                            (u"COMPUTACIÓN APROBADO", 5000),
                            (u"VINCULACIÓN H.COMPLETAS", 5000),
                            (u"CÓDIGO TURNO", 4000),
                        ]
                        row_num = 3
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        row_num = 4
                        for estudiante in listado_estudiantes:
                            insc = estudiante.inscripcion
                            ws.write(row_num, 0, '%s' % estudiante.orden, font_style2)
                            ws.write(row_num, 1, '%s' % insc.persona.cedula if insc.persona.cedula else insc.persona.pasaporte, font_style2)
                            ws.write(row_num, 2, '%s' % insc.persona.nombre_completo_inverso() if insc.persona else '', font_style2)
                            ws.write(row_num, 3, '%s' % estudiante.etiqueta if estudiante.etiqueta else '', font_style2)
                            ws.write(row_num, 4, insc.promedio_record(), font_style2)
                            ws.write(row_num, 5, '%s' % "SI" if estudiante.activo else "NO", font_style2)
                            ws.write(row_num, 6, '%s' % insc.persona.telefono if insc.persona.telefono else '', font_style2)
                            ws.write(row_num, 7, '%s' % insc.persona.telefono_conv if insc.persona.telefono_conv else '', font_style2)
                            if insc.persona.sexo:
                                ws.write(row_num, 8, '%s' % "MASCULINO" if insc.persona.sexo.id == 2 else "FEMENINO", font_style2)
                            else:
                                ws.write(row_num, 8, 'NO TIENE SEXO', font_style2)
                            ws.write(row_num, 9, '%s' % insc.persona.email if insc.persona.email else "", font_style2)
                            ws.write(row_num, 10, '%s' % insc.persona.emailinst if insc.persona.emailinst else "", font_style2)
                            ws.write(row_num, 11, '%s' % insc.carrera.nombre if insc.carrera else '', font_style2)
                            ws.write(row_num, 12, '%s' % insc.mi_nivel() if insc.mi_nivel() else '', font_style2)
                            matricula = insc.matricula_set.filter(status=True)[0]
                            ws.write(row_num, 13, '%s' % matricula.nivelmalla if matricula else '', font_style2)
                            ws.write(row_num, 14, '%s' % insc.nivelperiodo(periodo).nivel.sesion.nombre if insc.nivelperiodo(periodo) else '', font_style2)
                            ws.write(row_num, 15, '%s' % 'SI' if asignaturas_aprobadas_primero_septimo_nivel(insc.id) else 'NO', font_style2)
                            ws.write(row_num, 16, '%s' % 'SI' if haber_cumplido_horas_creditos_vinculacion(insc.id) else 'NO', font_style2)
                            ws.write(row_num, 17, '%s' % 'SI' if haber_aprobado_modulos_ingles(insc.id) else 'NO', font_style2)
                            ws.write(row_num, 18, '%s' % 'SI' if haber_aprobado_modulos_computacion(insc.id) else 'NO', font_style2)
                            ws.write(row_num, 19, '%s' % str(estudiante.id), font_style2)
                            row_num += 1
                        wb.save(response)
                        return response
                    else:
                        pass
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            if action == 'ordenprioridad':
                try:
                    data = {}
                    data['action'] = request.GET['action']
                    data['grupoorden'] = GRUPO_ORDEN
                    data['preinscripcion'] = preinscripcion = PreInscripcionPracticasPP.objects.get(status=True, pk=int(encrypt(request.GET['id'])))
                    data['idgo'] = idgo = preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first()
                    grupoorden = idgo.grupoorden if idgo else 0

                    listaestudiantes = []
                    listaestorden = []

                    data['pensedientes_asignar'] = pensedientes_asignar = len(preinscripcion.detallepreinscripcionpracticaspp_set.values_list('id', flat=True).filter(status=True, estado=1))
                    if listado_ordenprioridad := OrdenPrioridadInscripcion.objects.filter(status=True, grupoorden=grupoorden, configuracionorden__preinscripcion=preinscripcion):
                        for ordenprioridad in listado_ordenprioridad:
                            documento = str(ordenprioridad.inscripcion.persona.cedula) if ordenprioridad.inscripcion.persona.cedula else str(ordenprioridad.inscripcion.persona.pasaporte)
                            estadoppp = []
                            if ppp := PracticasPreprofesionalesInscripcion.objects.filter(status=True, preinscripcion__preinscripcion=preinscripcion, preinscripcion__estado=2, preinscripcion__inscripcion=ordenprioridad.inscripcion):
                                for p in ppp:
                                    estadoppp.append([p.preinscripcion.itinerariomalla.id, p.preinscripcion.itinerariomalla.nombre, p.preinscripcion.get_estado_display()])
                            listaestudiantes.append([int(ordenprioridad.orden), documento, str(ordenprioridad.inscripcion.persona), str(ordenprioridad.nota), str(ordenprioridad.etiqueta) if ordenprioridad.etiqueta else '', estadoppp])
                            listaestorden.append(ordenprioridad.id)
                    listaestudiantes = list(sorted(listaestudiantes, key=lambda x: x[0]))
                    data['cantidad'] = len(listaestudiantes)
                    data['listaestppp'] = listaestudiantes
                    data['listaestorden'] = listaestorden
                    template = get_template("alu_practicassalud/modal/establecerordenprioridad.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'revertiraprobaciondirector':
                try:
                    titulo = 'Agregar observación para Director'
                    data['form'] = ObservacionDecanoForm
                    data['solicitud'] = request.GET['id']
                    template = get_template("alu_practicassalud/modal/modal_observacionDecano.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", "titulo": titulo, 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'revertiraprobacionvinculacion':
                try:
                    titulo = 'Agregar observación para Vinculación'
                    data['form'] = ObservacionDirectorForm
                    data['solicitud'] = request.GET['id']
                    template = get_template("alu_practicassalud/modal/modal_observacionDirector.html")
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
                    return render(request, "alu_practicassalud/gestionar_preins_indmasivosalud.html",
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


                    if not (cartavinculacion.convenio or cartavinculacion.acuerdo):
                        return JsonResponse({"result": "bad", "mensaje": u"Debe tener al menos un convenio o acuerdo."})

                    return conviert_html_to_pdf(
                        'alu_practicassalud/informe_carta_vinculacion.html',
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

            elif action == 'addinsumoinformeinternadorotativo':
                try:
                    f = InsumoInformeInternadoRotativoForm()
                    data['form2'] = f
                    template = get_template('alu_practicassalud/modal/addmarcojuridico.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editinsumoinformeinternadorotativo':
                try:
                    insumo = InsumoInformeInternadoRotativo.objects.get(pk=request.GET.get('id'))
                    f = InsumoInformeInternadoRotativoForm(initial=model_to_dict(insumo))
                    data['form2'] = f
                    data['insumo'] = insumo
                    data['id'] = insumo.pk
                    template = get_template('alu_practicassalud/modal/addmarcojuridico.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'historialinsumoinformemensual':
                try:
                    insumo = InsumoInformeInternadoRotativo.objects.get(pk=request.GET.get('id'))
                    data['historial'] = HistorialInsumoInformeInternadoRotativo.objects.filter(insumo=insumo, status=True)
                    template = get_template('alu_practicassalud/modal/historialinsumoinformemensual.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": 'error'})

            elif action == 'denominacionpuesto':
                try:
                    _persona = Persona.objects.get(pk=request.GET.get('id'))
                    return JsonResponse({"result": "ok", "results": [{"id": dp.id, "value": f"{dp.descripcion}"} for dp in _persona.mis_cargos_actuales()]})
                except Exception as ex:
                    pass

            elif action == 'insumoinformemensual':
                try:
                    data['title'] = u'Insumos de informe mensual (internado rotativo)'
                    data['firmas'] = FirmaInformeMensualActividades.objects.filter(status=True)
                    data['insumos'] = InsumoInformeInternadoRotativo.objects.filter(status=True)
                    f = FirmaInformeMensualActividadesForm()
                    data['form'] = f
                    return render(request, "alu_practicassalud/insumoinformemensual.html", data)
                except Exception as ex:
                    pass

            elif action == 'addfirma':
                try:
                    f = FirmaInformeMensualActividadesForm()
                    data['form2'] = f
                    data['id'] = 1
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})
                
            elif action == 'editfirma':
                try:
                    firma = FirmaInformeMensualActividades.objects.get(pk=request.GET.get('id'))
                    f = FirmaInformeMensualActividadesForm(initial=model_to_dict(firma))
                    f.edit(firma.persona.pk)
                    data['form2'] = f                    
                    data['id'] = firma.pk
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})

            elif action == 'buscarpersona':
                try:
                    from sagest.models import DistributivoPersona
                    q = request.GET['q'].upper().strip()
                    s = [x.upper().strip() for x in q.split(" ") if not x == ""]

                    filtro = Q(persona__usuario__isnull=False,status=True)
                    if len(s) == 1: filtro &= Q(persona__nombres__icontains=q) | Q(persona__apellido1__icontains=q) | Q(persona__apellido2__icontains=q) | Q(persona__cedula__contains=q)
                    if len(s) == 2: filtro &= ((Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1])) | (Q(persona__nombres__icontains=s[0]) & Q(persona__nombres__icontains=s[1])) | (Q(persona__nombres__icontains=s[0]) & Q(persona__apellido1__contains=s[1])))
                    if len(s) >  2: filtro &= ((Q(persona__nombres__contains=s[2]) & Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1])) | (Q(persona__nombres__contains=s[0]) & Q(persona__nombres__contains=s[1]) & Q(persona__apellido1__contains=s[2])))

                    _persona = DistributivoPersona.objects.filter(filtro).exclude(persona__cedula='').order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres').distinct('persona__apellido1', 'persona__apellido2', 'persona__nombres')[:15]
                    return JsonResponse({"result": "ok", "results": [{"id": x.persona.id, "name": "%s %s" % (f"<img src='{x.persona.get_foto()}' width='25' height='25' style='border-radius: 20%;' alt='...'>", x.persona.nombre_completo_inverso())} for x in _persona]})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:

                data['title'] = u'Practicas Pre Profesionales Salud Inscripción'
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
                        filtros = filtros & Q(detalleevidenciaspracticaspro__estadotutor=2)
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
                practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.select_related('preinscripcion').filter(filtros)
                if es_director_carr:
                    carrerasids = miscarreras.values_list('id', flat=True)
                    practicaspreprofesionalesinscripcion = practicaspreprofesionalesinscripcion.filter(
                        inscripcion__carrera__in=carrerasids)
                elif es_decano:
                    cordecano = querydecano.first().coordinacion
                    carrerasids = cordecano.carreras().values_list('id', flat=True)
                    practicaspreprofesionalesinscripcion = practicaspreprofesionalesinscripcion.filter(
                        inscripcion__carrera__in=carrerasids)
                else:
                    carrerasids = PracticasPreprofesionalesInscripcion.objects.filter(status=True).values_list(
                        'inscripcion__carrera__id', flat=True)
                data['carreras'] = Carrera.objects.filter(status=True, coordinacion__excluir=False, pk__in=carrerasids).order_by('nombre')
                practicaspreprofesionalesinscripcion = practicaspreprofesionalesinscripcion.filter(inscripcion__coordinacion__in=[1]).distinct().order_by('-pk')
                paging = MiPaginador(practicaspreprofesionalesinscripcion, 10)
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
                return render(request, "alu_practicassalud/view.html", data)
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                print(ex)


def cumple_criterios_practicas(inscripcion, matricula, preinscripcion, valida_estudiante, nivel_masivo):
    itinerarios = []
    falta_horas = False
    validar_preinscripcion_ = True
    es_validado = False
    try:
        if not inscripcion.cumple_total_parcticapp() and valida_estudiante:
            es_validado = True
            periodospreins = preinscripcion
            # if str(inscripcion.persona.cedula) in variable_valor('VALIDA_CASO') or str(inscripcion.persona.pasaporte) in variable_valor('VALIDA_CASO'):
            #     cccc = 'este es el caso'
            aproboseptimo = asignaturas_aprobadas_primero_septimo_nivel(inscripcion.id)
            if inscripcion.carrera.id in [1, 3]:
                aproboseptimo = True
            vinculacion = haber_cumplido_horas_creditos_vinculacion(inscripcion.id)
            inglesaprobado = haber_aprobado_modulos_ingles(inscripcion.id)
            computacionaprobado = haber_aprobado_modulos_computacion(inscripcion.id)
            if not preinscripcion.inglesaprobado and not preinscripcion.computacionaprobado:
                validar_preinscripcion_ = True
            if preinscripcion.inglesaprobado and not preinscripcion.computacionaprobado:
                validar_preinscripcion_ = inglesaprobado
            if not preinscripcion.inglesaprobado and preinscripcion.computacionaprobado:
                validar_preinscripcion_ = computacionaprobado
            if preinscripcion.inglesaprobado and preinscripcion.computacionaprobado:
                validar_preinscripcion_ = (computacionaprobado and inglesaprobado)

            if validar_preinscripcion_ := validar_preinscripcion_ and aproboseptimo and vinculacion:
                listapre = inscripcion.detallepreinscripcionpracticaspp_set.values_list('itinerariomalla_id', flat=False).filter(status=True, estado__in=[1, 2, 5])
                if matricula.nivelmalla.orden <= 7:
                    nivel_orden = 7
                else:
                    nivel_orden = matricula.nivelmalla.orden

                if inscripcion.inscripcionmalla_set.values('id').exists():
                    if inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.filter(status=True).exists():
                        listaitinerariorealizado = inscripcion.cumple_total_horas_itinerario()
                        itinerariosvalidosid = []
                        for it in inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.filter(status=True):
                            nivelhasta = it.nivel.orden - 1
                            if inscripcion.todas_materias_aprobadas_rango_nivel2(1, nivelhasta):
                                itinerariosvalidosid.append(it.pk)
                        practicaculminada = inscripcion.practicaspreprofesionalesinscripcion_set.values_list('preinscripcion__itinerariomalla_id').filter(status=True, culminada=True, estadosolicitud=2, preinscripcion__itinerariomalla__isnull=False, preinscripcion__itinerariomalla_id__in=itinerariosvalidosid)
                        practicaculminada2 = inscripcion.practicaspreprofesionalesinscripcion_set.values_list('actividad__itinerariomalla_id').filter(status=True, culminada=True, estadosolicitud=2, actividad__itinerariomalla__isnull=False, actividad__itinerariomalla_id__in=itinerariosvalidosid)

                        if inscripcion.carrera_id in [112, 111, 110, 1, 3]:
                            nivel_orden += 1
                        if nivel_masivo == 0: #extrae todos los itinerarios faltantes del estudiante
                            itinerarios = inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.values_list('id', 'nombre', 'nivel__nombre').filter(status=True).filter(pk__in=itinerariosvalidosid).exclude(id__in=listaitinerariorealizado).exclude(id__in=listapre).exclude(id__in=practicaculminada).exclude(id__in=practicaculminada2)
                        else:
                            itinerarios = inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.values_list('id', 'nombre', 'nivel__nombre').filter(status=True, nivel__orden__lte=nivel_orden).filter(pk__in=itinerariosvalidosid).exclude(id__in=listaitinerariorealizado).exclude(id__in=listapre).exclude(id__in=practicaculminada).exclude(id__in=practicaculminada2)
                else:
                    if nivel_orden > 5:
                        if not inscripcion.detallepreinscripcionpracticaspp_set.filter(status=True, itinerariomalla__isnull=True).exists():
                            falta_horas = inscripcion.cumple_total_parcticapp()

        return (validar_preinscripcion_ and itinerarios) or (validar_preinscripcion_ and falta_horas), inscripcion, itinerarios, es_validado
    except Exception as ex:
        return False, inscripcion, itinerarios, False

def cumple_preinscribirse_itinerariomalla(inscripcion, itinerario):
    itinerariomalla, orden = ItinerariosMalla.objects.get(pk=itinerario), inscripcion.mi_nivel().nivel.orden
    nivelitinerario = itinerariomalla.nivel.orden - 1 if (itinerariomalla.nivel.orden - 1) > 0 else 1
    if not inscripcion.cumple_total_parcticapp():
        matricula = inscripcion.matricula_set.filter(status=True).first()
        if inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.filter(status=True).exists():
            nivelhasta = orden - 1 if orden > 1 else 1
            if inscripcion.todas_materias_aprobadas_rango_nivel(1, nivelitinerario):
                periodospreins = PreInscripcionPracticasPP.objects.values_list('id', flat=False).filter(fechainicio__lte=datetime.now().date(), fechafin__gte=datetime.now().date())
                listapre = inscripcion.detallepreinscripcionpracticaspp_set.values_list('itinerariomalla_id', flat=False).filter(status=True, estado=1, preinscripcion__in=periodospreins)
                if inscripcion.carrera_id in [112, 111, 110, 1, 3]:
                    return inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.filter(status=True, nivel__orden__lte=nivelitinerario+1).exclude(id__in=inscripcion.cumple_total_horas_itinerario()).exclude(id__in=listapre)

                return inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.filter(status=True, nivel__orden__lte=orden).exclude(id__in=inscripcion.cumple_total_horas_itinerario()).exclude(id__in=listapre)
            else:
                return False
        else:
            if inscripcion.todas_materias_aprobadas_rango_nivel(1, 5):
                if inscripcion.mi_nivel().nivel.orden > 5:
                    periodospreins = PreInscripcionPracticasPP.objects.values_list('id', flat=False).filter(
                        fechainicio__lte=datetime.now().date(), fechafin__gte=datetime.now().date())
                    if periodospreins:
                        return True if not inscripcion.detallepreinscripcionpracticaspp_set.values('id').filter(
                            status=True, estado=1, preinscripcion__in=periodospreins).exists() else False
                    else:
                        return False
            else:
                return False
    return False