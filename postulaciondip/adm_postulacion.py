# -*- coding: UTF-8 -*-
import random
import os
import ast
from datetime import datetime, timedelta
import unicodedata
import json

import pyqrcode
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from xhtml2pdf import pisa

from core.firmar_documentos_ec import JavaFirmaEc
from decorators import secure_module, last_access
from postulaciondip.forms import CerrarActaForm, ArchivoInvitacionForm, FirmaElectronicaIndividualForm, PlanAccionForm, \
    PersonalAContratarForm, ActaSeleccionDocenteForm, ConvocatoriaForm, RequisitoForm, InscripcionConvocatoriaForm, \
    DatoPersonalForm, \
    RolPersonalApoyoForm, PersonalApoyoForm, ConfiguracionPlazosActaSeleccion, PersonalApoyoMaestriaForm, \
    ClasificacionDocumentoInvitacionForm, DocumentoInvitacionForm, SecuenciaDocumentoInvitacionForm, \
    FirmasDocumentoInvitacionForm, ComiteAcademicoPosgradoForm, IntegranteComiteAcademicoPosgradoForm, \
    HorarioClasesForm, TipoPersonalForm, ActaParaleloForm, DuplicarHorarioForm, PlanificacionMateriaPosgradoForm, \
    AdministrativoActaSeleccionDocenteForm, OrdenFirmaActaForm, MensajePredeterminadoForm, ConvocatoriaMasivaForm, \
    RequisitosConvocatoriaInscripcionForm, VotacionComiteForm, RequisitosInscripcionForm, \
    RequisitosPersonalContratarForm, \
    ValidarRequisitoPersonalContratarForm, RequisitoUpdateOpcionalForm, ConfiguracionInformeForm, \
    OrdenFirmaInformeContratacionForm, ResponsabilidadFirmaForm, InformeContratacionIntegrantesFirmaForm, \
    ConfiguracionGeneralActaSeleccionDocenteForm, CertificacionPresupuestariaInformeContratacionForm, \
    ConfiguracionConclusionesInformeContratacionForm, \
    ConfiguracionRecomendacionesInformeContratacionForm, RubricaSeleccionDocenteForm, \
    DetalleItemRubricaSeleccionDocenteForm, DetalleSubItemRubricaSeleccionDocenteForm, \
    DatoPersonalExtraForm
from postulaciondip.funciones import titulados_acorde_al_campo_del_perfil_requerido

from postulaciondip.models import ActaDocumentacion, HistorialActaSeleccionDocente, ActaSeleccionDocente, Convocatoria, \
    Requisito, RequisitoGenerales, RequisitosConvocatoria, InscripcionConvocatoriaRequisitos, InscripcionConvocatoria, \
    RequisitoGeneralesPersona, HistorialAprobacion, HistorialAprobacionIns, HistorialReqGeneral, ESTADO_REVISION, \
    InscripcionPostulante, InscripcionInvitacion, HistorialAprobacionInscripcion, PersonalApoyoMaestria, \
    PersonalApoyo, RolPersonalApoyo, DocumentoInvitacion, ClasificacionDocumentoInvitacion, FirmasDocumentoInvitacion, \
    SecuenciaDocumentoInvitacion, ComiteAcademicoPosgrado, IntegranteComiteAcademicoPosgrado, HorarioClases, PlanAccion, \
    PersonalAContratar, TipoPersonal, ActaParalelo, InscripcionRequisitoPreAprobado, ESTADO_ACTA, \
    OrdenFirmaActaSeleccionDocente, PlanificacionMateria, MensajePredeterminado, HistorialPersonalContratarActaParalelo, \
    HistorialConvocatoria, HorarioPlanificacionConvocatoria, VotacionComiteAcademico, \
    ConfiguracionRequisitosPersonalContratar, ConfiguracionGeneralActaSeleccionDocente, \
    InformeContratacion, DetalleInformeContratacion, ConfiguracionInforme, OrdenFirmaInformeContratacion, \
    ResponsabilidadFirma, InformeContratacionIntegrantesFirma, RubricaSeleccionDocente, \
    DetalleItemRubricaSeleccionDocente, DetalleSubItemRubricaSeleccionDocente, RecorridoActaSeleccionDocente, \
    BaremoComiteAcademico
from pdip.models import CertificacionPresupuestariaDip
from postulaciondip.postu_requisitos import valida_choque_horario_en_actas_generadas_pre_postulacion
from sga.commonviews import adduserdata
from settings import SITE_STORAGE
from django.core.files import File as DjangoFile
from sga.funciones import null_to_decimal, puede_realizar_accion, log, generar_nombre, MiPaginador, variable_valor, daterange, notificacion, \
    remover_caracteres_tildes_unicode, remover_caracteres_especiales_unicode, puede_realizar_accion_afirmativo
from django.db.models import Max, Min, Case, When, Value, IntegerField, Count,Sum, Q, F,Avg
from django.db.models.query_utils import Q
from inno.models import PlanificacionParalelo
from sga.models import CUENTAS_CORREOS, VariablesGlobales, Paralelo, Asignatura, Malla, NivelTitulacion, Titulacion, \
    Persona, AsignaturaMalla, Carrera, Periodo, Materia, Profesor, ProfesorMateria, RespuestaRubrica, RubricaPreguntas, \
    ProfesorDistributivoHoras, DIAS_CHOICES, Turno, MESES_CHOICES, SubAreaConocimientoTitulacion, \
    SubAreaEspecificaConocimientoTitulacion, AreaConocimientoTitulacion, ModuloGrupo, Modulo, TipoProfesor, \
    Administrativo
from sagest.models import Departamento
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from django.forms import model_to_dict
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, convert_html_to_pdf, \
    conviert_html_to_pdf_save_informe, conviert_html_to_pdf_save_file_model,conviert_html_to_pdfsaveqr_cartaaceptacioncertificado
from sga.funciones_templatepdf import download_html_to_pdf
from inno.models import PerfilRequeridoPac, DetalleFuncionSustantivaDocenciaPac
from core.firmar_documentos import firmar, obtener_posicion_x_y_saltolinea
from django.contrib import messages
from xlwt import *
from xlwt import easyxf
import PyPDF2
import xlwt
import io
import xlsxwriter
import fitz
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavecontratomae
@login_required(redirect_field_name='ret', login_url='/loginpostulacion')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    ex = ''
    data = {}
    hoy = datetime.now().date()
    adduserdata(request, data)
    persona = request.session.get('persona')
    periodo = request.session.get('periodo')
    perfilprincipal = request.session['perfilprincipal']
    data['IS_DEBUG'] = IS_DEBUG = variable_valor('IS_DEBUG')
    if not perfilprincipal.administrativo:
        return HttpResponseRedirect("/")

    miscarreras = persona.mis_carreras()
    if request.method == 'POST':
        action = request.POST['action']
        rt = request.POST['rt'] if 'rt' in request.POST else ''

        if action == 'generarconvocatoria':
            try:
                idasignaturamalla = request.POST['id']
                convocatoria = Convocatoria(asignaturamalla_id=idasignaturamalla)
                convocatoria.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar convocatoria."})

        elif action == 'addconvocatoria':
            try:
                tipo = int(request.POST.get('tipo', 1))
                f = ConvocatoriaForm(request.POST)
                f.initial_values(tipo)
                am = AsignaturaMalla.objects.filter(pk=int(encrypt(request.POST.get('idasigmalla', None)))).first()
                if Convocatoria.objects.filter(nombre=request.POST['nombre'].upper(), asignaturamalla=am, status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existe una convocatoria con el nombre: {0}".format(request.POST['nombre'].upper()),"showSwal": "True", "swalType": "warning"})

                if tipo == 2:
                    f.fields['campoamplio'].required = False

                if f.is_valid():
                    start_date = f.cleaned_data.get('fechainicio')
                    end_date = f.cleaned_data.get('fechafin')

                    if start_date and end_date:
                        if (end_date - start_date).days < 4:
                            return JsonResponse({"result": "bad", "mensaje":"Debe lanzar una convocatoria con almenos un plazo mayor a 5 dia."})

                    if not start_date == hoy:
                       return JsonResponse({"result": "bad", "mensaje": "Favor seleccione la fecha inicio actual."})


                    convocatoria = Convocatoria(asignaturamalla=am,
                                                nombre=f.cleaned_data.get('nombre').upper(),
                                                fechainicio=f.cleaned_data.get('fechainicio'),
                                                fechafin=f.cleaned_data.get('fechafin'),
                                                iniciohorario=f.cleaned_data.get('fechainiciohorario'),
                                                finhorario=f.cleaned_data.get('fechafinhorario'),
                                                activo=True,
                                                tipodocente=f.cleaned_data.get('tipodocente'),
                                                carrera_id=f.cleaned_data['carrera'].id if f.cleaned_data.get('carrera') else request.POST.get('idc'),
                                                periodo=f.cleaned_data.get('periodo'),
                                                vacantes=f.cleaned_data.get('vacantes', 1),
                                                paralelos=f.cleaned_data.get('paralelos', 1),
                                                tipo=tipo)
                    convocatoria.save(request)
                    convocatoria.notificar_vicerrector_posgrado(request,persona)
                    if 'planificacionmateria' in  request.POST and request.POST['planificacionmateria'] != '':
                        ePlanificacionMateria = PlanificacionMateria.objects.get(pk= int(request.POST['planificacionmateria']))
                        ePlanificacionMateria.estado = 3
                        ePlanificacionMateria.convocatoria = convocatoria
                        ePlanificacionMateria.save(request)

                    if f.cleaned_data.get('perfilrequeridopac'): convocatoria.perfilrequeridopac.set(f.cleaned_data['perfilrequeridopac'])
                    if f.cleaned_data.get('campoamplio'): convocatoria.campoamplio.set(f.cleaned_data['campoamplio'])
                    if f.cleaned_data.get('campoespecifico'): convocatoria.campoespecifico.set(f.cleaned_data['campoespecifico'])
                    if f.cleaned_data.get('campodetallado'): convocatoria.campodetallado.set(f.cleaned_data['campodetallado'])

                    eHistorialConvocatoria = HistorialConvocatoria(
                        convocatoria = convocatoria,
                        persona = persona,
                        fecha = hoy,
                        fechainicio=f.cleaned_data.get('fechainicio'),
                        fechafin=f.cleaned_data.get('fechafin'),
                        tipodocente=f.cleaned_data.get('tipodocente'),
                        vacantes=f.cleaned_data.get('vacantes', 1),
                        paralelos=f.cleaned_data.get('paralelos', 1),
                    )
                    eHistorialConvocatoria.save(request)
                    if f.cleaned_data.get('perfilrequeridopac'): eHistorialConvocatoria.perfilrequeridopac.set(f.cleaned_data['perfilrequeridopac'])
                    if f.cleaned_data.get('campoamplio'): eHistorialConvocatoria.campoamplio.set(f.cleaned_data['campoamplio'])
                    if f.cleaned_data.get('campoespecifico'): eHistorialConvocatoria.campoespecifico.set(f.cleaned_data['campoespecifico'])
                    if f.cleaned_data.get('campodetallado'): eHistorialConvocatoria.campodetallado.set(f.cleaned_data['campodetallado'])

                    convocatoria.notificar_perfiles_compatibles(request)
                    log(u'Agregó convocatoria: %s' % convocatoria, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar convocatoria."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar convocatoria."})

        elif action == 'convocatoria_masivo':
            try:
                id_string = request.POST.get('id', 0)
                id_list = ast.literal_eval(id_string)
                # Si id_list no es una lista, conviértelo en una lista con un solo elemento
                if not isinstance(id_list, tuple):
                    id_list = (id_list,)
                ePlanificacionMaterias = PlanificacionMateria.objects.filter(status=True, pk__in=id_list)
                f = ConvocatoriaMasivaForm(request.POST)
                cantidad_profesor= 0
                cantidad_autor= 0
                primera_iteracion = True
                _nombre_profesor = ''
                _nombre_profesor_autor = ''
                _ePlanificacionMateriasTipoProfesor = []
                _ePlanificacionMateriasTipoProfesorAutor = []
                if f.is_valid():
                    for planificacion in ePlanificacionMaterias:
                        if primera_iteracion == True:
                            _nombre_profesor += ' '+ planificacion.get_nombre_asignatura_a_lanzar()
                            _nombre_profesor_autor += ' '+ planificacion.get_nombre_asignatura_a_lanzar()
                            _asignaturamalla = planificacion.materia.asignaturamalla
                            _carrera_id = planificacion.materia.asignaturamalla.malla.carrera_id
                            _fechainicio = f.cleaned_data.get('fechainicio')
                            _fechafin = f.cleaned_data.get('fechafin')
                            _periodo = planificacion.materia.nivel.periodo_id
                            _activo = False
                            _ePlanificacionMateria = planificacion
                            _tipo = 1
                            _campoamplio = None
                            _campoespecifico = None
                            _campodetallado = None
                            _perfilrequeridopac = PerfilRequeridoPac.objects.filter(
                                personalacademico__asignaturaimpartir__asignatura_id=_asignaturamalla.asignatura_id,
                                personalacademico__asignaturaimpartir__asignatura__status=True,
                                personalacademico__asignaturaimpartir__status=True, personalacademico__status=True,
                                titulacion__titulo__status=True, status=True)

                            campo_amplio_set = set()
                            campo_especifico_set = set()
                            campo_detallado_set = set()

                            if _perfilrequeridopac.exists():
                                for ePerfilRequeridoPac in _perfilrequeridopac:
                                    campoamplios = ePerfilRequeridoPac.titulacion.campoamplio.filter(status=True, tipo=1)
                                    campoespecificos = ePerfilRequeridoPac.titulacion.campoespecifico.filter( status=True, tipo=1)
                                    campodetallados = ePerfilRequeridoPac.titulacion.campodetallado.filter(status=True,tipo=1)
                                    # Add campoamplios to the campo_amplio_set
                                    campo_amplio_set.update(campoamplios.values_list('id', flat=True))
                                    # Add campoespecificos to the campo_especifico_set
                                    campo_especifico_set.update(campoespecificos.values_list('id', flat=True))
                                    # Add campodetallados to the campo_detallado_set
                                    campo_detallado_set.update(campodetallados.values_list('id', flat=True))

                                # obtengo los campos amplio,especifico y detallados de cada perfil requerido y filtro sin que se repitan
                                unique_ids_ca = set(list(campo_amplio_set))
                                if not len(unique_ids_ca) != len(campo_amplio_set):
                                    eAreaConocimientoTitulacion = AreaConocimientoTitulacion.objects.filter(pk__in=unique_ids_ca).order_by('codigo')

                                unique_ids_ce = set(list(campo_especifico_set))
                                if not len(unique_ids_ce) != len(list(campo_especifico_set)):
                                    eSubAreaConocimientoTitulacion = SubAreaConocimientoTitulacion.objects.filter(pk__in=unique_ids_ce).order_by('codigo')

                                unique_ids_cd = set(list(campo_detallado_set))
                                if not len(unique_ids_cd) != len(list(campo_detallado_set)):
                                    eSubAreaEspecificaConocimientoTitulacion = SubAreaEspecificaConocimientoTitulacion.objects.filter(pk__in=unique_ids_cd).order_by('codigo')

                            #asigno solo los campos amplios para que la convocatoria salga configurada con ese los demas no asignono fue requerido
                            _campoamplio = eAreaConocimientoTitulacion
                            _campoespecifico = None #eSubAreaConocimientoTitulacion
                            _campodetallado = None #eSubAreaEspecificaConocimientoTitulacion

                            primera_iteracion = False
                        if planificacion.boolean_requiere_profesor_and_profesor_autor():
                            cantidad_profesor+= 1
                            cantidad_autor+= 1
                            _ePlanificacionMateriasTipoProfesor.append(planificacion)
                            _ePlanificacionMateriasTipoProfesorAutor.append(planificacion)
                            _nombre_profesor  += ' -'+ planificacion.get_nombre_paralelo_a_lanzar_masivo()
                            _nombre_profesor_autor  += ' -'+ planificacion.get_nombre_paralelo_a_lanzar_masivo()
                        elif planificacion.boolean_requiere_invitado_and_profesor_autor():
                            cantidad_autor+= 1
                            _nombre_profesor_autor += ' -'+ planificacion.get_nombre_paralelo_a_lanzar_masivo()
                            _ePlanificacionMateriasTipoProfesorAutor.append(planificacion)
                        elif planificacion.boolean_requiere_profesor():
                            cantidad_profesor+= 1
                            _nombre_profesor += ' -'+ planificacion.get_nombre_paralelo_a_lanzar_masivo()
                            _ePlanificacionMateriasTipoProfesor.append(planificacion)
                        else:
                            cantidad_profesor = cantidad_profesor
                            cantidad_autor = cantidad_autor
                            _nombre_profesor = ''
                            _nombre_profesor_autor = ''

                    _vacantes_profesor = cantidad_profesor
                    _paralelos_profesor = cantidad_profesor
                    _vacantes_profesorAutor = cantidad_autor
                    _paralelos_profesorAutor = cantidad_autor
                    planificacion.crear_convocatoria_tipo_profesor_masivo(_nombre_profesor, _asignaturamalla, _carrera_id,
                                                                   _fechainicio, _fechafin, _periodo, _activo,
                                                                   _ePlanificacionMateriasTipoProfesor, _perfilrequeridopac,
                                                                   _vacantes_profesor, _paralelos_profesor, _tipo, _campoamplio,
                                                                   _campoespecifico, _campodetallado, request)

                    planificacion.crear_convocatoria_tipo_profesor_autor_masivo(_nombre_profesor_autor, _asignaturamalla, _carrera_id,
                                                                          _fechainicio, _fechafin, _periodo, _activo,
                                                                          _ePlanificacionMateriasTipoProfesorAutor,
                                                                          _perfilrequeridopac,
                                                                          _vacantes_profesorAutor, _paralelos_profesorAutor,
                                                                          _tipo, _campoamplio,
                                                                          _campoespecifico, _campodetallado, request)


                    return JsonResponse({"result": False})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar convocatoria."})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar convocatoria."})

        elif action == 'convocatoria_masivo_por_paralelo':
            try:
                id_string = request.POST.get('id', 0)
                id_list = ast.literal_eval(id_string)
                # Si id_list no es una lista, conviértelo en una lista con un solo elemento
                if not isinstance(id_list, tuple):
                    id_list = (id_list,)
                ePlanificacionMaterias = PlanificacionMateria.objects.filter(status=True, pk__in=id_list)
                f = ConvocatoriaMasivaForm(request.POST)
                if f.is_valid():

                    for planificacion in ePlanificacionMaterias:
                        _nombre = planificacion.get_nombre_convocatoria_a_lanzar()
                        _asignaturamalla = planificacion.materia.asignaturamalla
                        _carrera_id = planificacion.materia.asignaturamalla.malla.carrera_id
                        _fechainicio = f.cleaned_data.get('fechainicio')
                        _fechafin = f.cleaned_data.get('fechafin')
                        _periodo = planificacion.materia.nivel.periodo_id
                        _activo = False
                        _ePlanificacionMateria = planificacion
                        _vacantes = 1
                        _paralelos = 1
                        _tipo = 1
                        _campoamplio = None
                        _campoespecifico = None
                        _campodetallado = None
                        _perfilrequeridopac = PerfilRequeridoPac.objects.filter(personalacademico__asignaturaimpartir__asignatura_id=_asignaturamalla.asignatura_id, personalacademico__asignaturaimpartir__asignatura__status=True, personalacademico__asignaturaimpartir__status=True, personalacademico__status=True, titulacion__titulo__status=True, status=True)

                        campo_amplio_set = set()
                        campo_especifico_set = set()
                        campo_detallado_set = set()

                        if _perfilrequeridopac.exists():
                            for ePerfilRequeridoPac in _perfilrequeridopac:
                                campoamplios = ePerfilRequeridoPac.titulacion.campoamplio.filter(status=True, tipo=1)
                                campoespecificos = ePerfilRequeridoPac.titulacion.campoespecifico.filter(status=True, tipo=1)
                                campodetallados = ePerfilRequeridoPac.titulacion.campodetallado.filter(status=True,tipo=1)
                                # Add campoamplios to the campo_amplio_set
                                campo_amplio_set.update(campoamplios.values_list('id', flat=True))
                                # Add campoespecificos to the campo_especifico_set
                                campo_especifico_set.update(campoespecificos.values_list('id', flat=True))
                                # Add campodetallados to the campo_detallado_set
                                campo_detallado_set.update(campodetallados.values_list('id', flat=True))

                            # Convert the sets to lists and assign them to the respective fields
                            unique_ids_ca = set(list(campo_amplio_set))
                            if not len(unique_ids_ca) != len(campo_amplio_set):
                                eAreaConocimientoTitulacion = AreaConocimientoTitulacion.objects.filter( pk__in=unique_ids_ca).order_by('codigo')

                            unique_ids_ce = set(list(campo_especifico_set))
                            if not len(unique_ids_ce) != len(list(campo_especifico_set)):
                                eSubAreaConocimientoTitulacion = SubAreaConocimientoTitulacion.objects.filter(pk__in=unique_ids_ce).order_by('codigo')

                            unique_ids_cd = set(list(campo_detallado_set))
                            if not len(unique_ids_cd) != len(list(campo_detallado_set)):
                                eSubAreaEspecificaConocimientoTitulacion = SubAreaEspecificaConocimientoTitulacion.objects.filter(pk__in=unique_ids_cd).order_by('codigo')

                        _campoamplio = eAreaConocimientoTitulacion
                        _campoespecifico = None
                        _campodetallado= None

                        if planificacion.boolean_requiere_profesor_and_profesor_autor():

                            planificacion.crear_convocatoria_tipo_profesor(_nombre, _asignaturamalla, _carrera_id,
                                                                           _fechainicio, _fechafin, _periodo, _activo,
                                                                           _ePlanificacionMateria, _perfilrequeridopac,
                                                                           _vacantes, _paralelos, _tipo, _campoamplio,
                                                                           _campoespecifico, _campodetallado, request)

                            planificacion.crear_convocatoria_tipo_profesor_autor(_nombre, _asignaturamalla, _carrera_id,
                                                                           _fechainicio, _fechafin, _periodo, _activo,
                                                                           _ePlanificacionMateria, _perfilrequeridopac,
                                                                           _vacantes, _paralelos, _tipo, _campoamplio,
                                                                           _campoespecifico, _campodetallado, request)

                        elif planificacion.boolean_requiere_invitado_and_profesor_autor():
                            planificacion.crear_convocatoria_tipo_profesor(_nombre, _asignaturamalla, _carrera_id,
                                                                           _fechainicio, _fechafin, _periodo, _activo,
                                                                           _ePlanificacionMateria, _perfilrequeridopac,
                                                                           _vacantes, _paralelos, _tipo, _campoamplio,
                                                                           _campoespecifico, _campodetallado, request)
                        elif planificacion.boolean_requiere_profesor():
                            planificacion.crear_convocatoria_tipo_profesor(_nombre, _asignaturamalla, _carrera_id,
                                                                           _fechainicio, _fechafin, _periodo, _activo,
                                                                           _ePlanificacionMateria, _perfilrequeridopac,
                                                                           _vacantes, _paralelos, _tipo, _campoamplio,
                                                                           _campoespecifico, _campodetallado, request)
                        else:
                            return JsonResponse({"result": True, "mensaje":"No se encontro el tipo de personal a contratar"})
                    return JsonResponse({"result": False})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar convocatoria."})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar convocatoria."})

        elif action == 'addconvocatoriadoble':
            try:
                tipo = int(request.POST.get('tipo', 1))
                f = ConvocatoriaForm(request.POST)
                f.initial_values(tipo)
                am = AsignaturaMalla.objects.filter(pk=int(encrypt(request.POST.get('idasigmalla', None)))).first()
                if Convocatoria.objects.filter(nombre=request.POST['nombre'].upper(), asignaturamalla=am, status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existe una convocatoria con el nombre: {0}".format(request.POST['nombre'].upper()),"showSwal": "True", "swalType": "warning"})
                tipo_docentes = TipoProfesor.objects.filter(pk__in=(18,15))
                if f.is_valid():
                    for tipo_docente in tipo_docentes:
                        convocatoria = Convocatoria(asignaturamalla=am,
                                                    nombre= f" {f.cleaned_data.get('nombre').upper()} - {tipo_docente.__str__()}",
                                                    fechainicio=f.cleaned_data.get('fechainicio'),
                                                    fechafin=f.cleaned_data.get('fechafin'),
                                                    activo=f.cleaned_data.get('activo'),
                                                    tipodocente=tipo_docente,
                                                    carrera_id=f.cleaned_data['carrera'].id if f.cleaned_data.get('carrera') else request.POST.get('idc'),
                                                    periodo=f.cleaned_data.get('periodo'),
                                                    vacantes=f.cleaned_data.get('vacantes', 1),
                                                    paralelos=f.cleaned_data.get('paralelos', 1),
                                                    tipo=tipo)
                        convocatoria.save(request)
                        if 'planificacionmateria' in  request.POST and request.POST['planificacionmateria'] != '':
                            ePlanificacionMateria = PlanificacionMateria.objects.get(pk= int(request.POST['planificacionmateria']))
                            ePlanificacionMateria.estado = 3
                            ePlanificacionMateria.convocatoria = convocatoria
                            ePlanificacionMateria.save(request)

                        if f.cleaned_data.get('perfilrequeridopac'): convocatoria.perfilrequeridopac.set(f.cleaned_data['perfilrequeridopac'])
                        if f.cleaned_data.get('campoamplio'): convocatoria.campoamplio.set(f.cleaned_data['campoamplio'])
                        if f.cleaned_data.get('campoespecifico'): convocatoria.campoespecifico.set(f.cleaned_data['campoespecifico'])
                        if f.cleaned_data.get('campodetallado'): convocatoria.campodetallado.set(f.cleaned_data['campodetallado'])
                        convocatoria.notificar_perfiles_compatibles(request)
                        log(u'Agregó convocatoria: %s' % convocatoria, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar convocatoria."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar convocatoria."})

        elif action == 'actualizar_detalle_acta':
            try:
                id = int(request.POST.get('id', 0))
                eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=id)
                eActaSeleccionDocente.detalle = request.POST.get('detalle', '')
                eActaSeleccionDocente.save(request)
                log(u'actualizo detalle acta: %s' % ActaSeleccionDocente, request, "edit")
                eActaSeleccionDocente.actualizar_documeto_pdf_acta(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar acta."})

        elif action == 'notificar_votacion_comite':
            try:
                id = int(request.POST.get('id', 0))
                eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=id)
                if not eActaSeleccionDocente.enviada_a_comite:
                    eActaSeleccionDocente.fecha_hora_inicio_revision_comite = datetime.now()
                    eActaSeleccionDocente.fecha_hora_fin_revision_comite =  datetime.now() + timedelta(hours=12)
                    eActaSeleccionDocente.save(request)
                else:
                    eActaSeleccionDocente.fecha_hora_fin_revision_comite = datetime.now() + timedelta(hours=12)
                    eActaSeleccionDocente.save(request)


                eActaSeleccionDocente.enviada_a_comite =True
                eActaSeleccionDocente.save(request)
                eActaSeleccionDocente.notificar_votacion_al_comite(request)

                return JsonResponse({"result": "ok","pk":eActaSeleccionDocente.pk})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar acta."})

        elif action == 'notificar_votacion_realizada_miembro_comite':
            try:
                id = int(request.POST.get('id', '0'))
                eActaParalelo = ActaParalelo.objects.get(pk=id)
                eActaParalelo.get_notificar_director_para_que_vote(request)

                return JsonResponse({"result": "ok","mensaje":"Notificación realizada con exito"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al notificar."})

        elif action == 'notificar_votacion_acta_completa':
            try:
                id = int(request.POST.get('id', '0'))
                eActaParalelo = ActaParalelo.objects.get(pk=id)
                ecarrera = eActaParalelo.convocatoria.carrera
                eperiodo = eActaParalelo.convocatoria.periodo
                ePersonalApoyoMaestrias = PersonalApoyoMaestria.objects.filter(status=True, carrera=ecarrera, periodo=eperiodo)
                eActaParalelo.acta.notificar_acta_votacion_por_todos_los_paralelos(request,ePersonalApoyoMaestrias)

                eActaParalelo.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                       actaparalelo=None,
                                                                       persona=persona,
                                                                       observacion=f"Votación realizada por todos los miembros de comité académico.",
                                                                       archivo=None)

                return JsonResponse({"result": "ok","mensaje":"Notificación realizada con exito"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al notificar."})

        elif action == 'actualizar_detalle_resolucion_acta':
            try:
                id = int(request.POST.get('id', 0))
                eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=id)
                eActaSeleccionDocente.detalle_resolucion = request.POST.get('detalle', '')
                eActaSeleccionDocente.save(request)
                log(u'actualizo detalle acta: %s' % ActaSeleccionDocente, request, "edit")
                eActaSeleccionDocente.actualizar_documeto_pdf_acta(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar acta."})


        elif action == 'delconvocatoria':
            try:
                cv = Convocatoria.objects.get(pk=int(encrypt(request.POST['id'])))
                cv.status=False
                cv.save()
                return JsonResponse({"result": "ok", 'error':False})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar convocatoria."})

        elif action == 'aprobarinscritoanalista':
            try:
                with transaction.atomic():
                    APROBADO = 2
                    APROBADO_PARA_COMITE = 12
                    model = InscripcionConvocatoria.objects.filter(status=True)
                    if 'id' in request.POST and request.POST['id']:
                        id = request.POST['id'].split(',')
                        model = model.filter(pk__in=id)

                    f = InscripcionConvocatoriaForm(request.POST)
                    if f.is_valid():
                        for m in model:

                            if int(f.cleaned_data['estado']) in (APROBADO,APROBADO_PARA_COMITE):
                                if m.convocatoria.get_horario().exists():
                                    # Validacion de choque de horario
                                    response = valida_choque_horario_pregrado(request, InscripcionConvocatoria=m,horarioClases=m.convocatoria.get_horario())

                                    if not response.get('result'): return JsonResponse(response)
                                    response = valida_choque_horario_en_actas_generadas_pre_postulacion(request, persona=m.postulante.persona , horarioClases=m.convocatoria.get_horario())
                                    if not response.get('result'): return JsonResponse(response)

                            m.estado, m.observacioncon = f.cleaned_data['estado'], f.cleaned_data['observacioncon']
                            m.save(request)

                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError(u"Error al validar los datos.")

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"{ex.__str__()}"})

        elif action == 'aprobarinscrito':
            try:
                with transaction.atomic():
                    model = InscripcionConvocatoria.objects.filter(status=True)
                    if 'id' in request.POST and request.POST['id']:
                        id = request.POST['id'].split(',')
                        model = model.filter(pk__in=id)

                    f = InscripcionConvocatoriaForm(request.POST)
                    if f.is_valid():
                        for m in model:


                            if  int(f.cleaned_data['estado']) == 2 :
                                paralelo = ActaParalelo.objects.get(pk=int(request.POST['idp']))
                                inscripcion, tipo = m, f.cleaned_data.get('tipoPersonal')
                                tipoinscripcion = 1 if Profesor.objects.values('id').filter( persona=inscripcion.postulante.persona, status=True).exists() else 2
                                if not paralelo.get_horario().exists():
                                    raise NameError(u'Debe configurar primero el horario.')
                                # Validacion de choque de horario
                                response = valida_choque_horario_pregrado(request, InscripcionConvocatoria=inscripcion, horarioClases=paralelo.get_horario())

                                if not response.get('result'): return JsonResponse(response)
                                response = valida_choque_horario_en_actas_generadas(request, InscripcionConvocatoria=inscripcion, horarioClases=paralelo.get_horario(),eActaParalelo=paralelo)

                                if not response.get('result'): return JsonResponse(response)

                                if tipo.pk in (2, 3):
                                    label_tipo = 'ALTERNO 1' if tipo.pk == 2 else 'ALTERNO 2'
                                    if PersonalAContratar.objects.filter(actaparalelo=paralelo, tipo_id=tipo.pk,status=True).exists():
                                        raise NameError(f'Exedió el número de postulantes de tipo {label_tipo}.')

                                if tipo.pk == 1:
                                    if PersonalAContratar.objects.filter(actaparalelo=paralelo, tipo_id=1,status=True).exists():
                                        raise NameError( u'Exedió el número de postulantes de tipo principal.')

                                    cantidadcontratos = PersonalAContratar.objects.values('id').filter(
                                        inscripcion=inscripcion, fecha_creacion__year=hoy.year, tipo__id=1,
                                        actaparalelo__convocatoria__tipodocente__in=[18, 15],
                                        actaparalelo__convocatoria__status=True, actaparalelo__acta__status=True,
                                        actaparalelo__status=True, actaparalelo__acta__fecha_legalizacion__isnull=False,
                                        status=True).count()
                                    if cantidadcontratos > 3:
                                        raise NameError(u'Exedió el número de contratos por año para docentes de tipo PROFESOR y PROFESOR AUTOR.')

                                    cuerpo = f"""
                                                        Estimad{'a' if inscripcion.postulante.persona.es_mujer() else 'o'} {f'{inscripcion.postulante.persona.nombres}'.split(' ')[0]}, por medio de la presente se le informa que 
                                                        usted a sido seleccionado por el comité académico <b>{paralelo.acta.comite.nombre}</b> para impartir clases en el módulo <b>{paralelo.convocatoria.asignaturamalla.asignatura}.</b>
                                                        Su carta de invitación será enviada al <b>Sistema de Selección Docentes Posgrado</b> dentro de poco.<br><br>
                                                        Saludos cordiales,
                                                    """
                                    notificacion('Sistema de Selección Docentes Posgrado', cuerpo, inscripcion.postulante.persona,None, '', inscripcion.pk, 1, 'sga', PersonalAContratar, request)

                                if not PersonalAContratar.objects.filter(inscripcion=inscripcion, actaparalelo=paralelo,tipo=tipo, status=True).values('id').exists():
                                    p = PersonalAContratar(inscripcion=inscripcion, tipo=tipo, actaparalelo=paralelo,tipoinscripcion=tipoinscripcion)
                                    p.save(request)

                                    miembrocomite = paralelo.acta.comite.get_integrantes().filter(persona=persona, status=True).first()
                                    eVotacionComiteAcademico = VotacionComiteAcademico.objects.filter(status=True, miembrocomite=miembrocomite)
                                    if not eVotacionComiteAcademico.filter(inscripcion=inscripcion).exists():
                                        eVotacionComiteAcademico = VotacionComiteAcademico(
                                            miembrocomite=miembrocomite,
                                            inscripcion=inscripcion,
                                            tipo=tipo,
                                            actaparalelo=paralelo
                                        )
                                        eVotacionComiteAcademico.save(request)

                                    eHistorialPersonalContratarActaParalelo = HistorialPersonalContratarActaParalelo(
                                        persona=persona,
                                        fecha=hoy,
                                        personalcontratar=p,
                                        estado=1
                                    )
                                    eHistorialPersonalContratarActaParalelo.save(request)
                                    log(u"Agregó personal", request, 'add')
                                else:
                                    raise NameError( f"El postulante %s ya se encuentra registrado. {inscripcion}")
                            else:
                                ePersonalAContratar = PersonalAContratar.objects.filter(status=True, inscripcion=m,actaparalelo_id = int(request.POST['idp']))
                                if ePersonalAContratar.count() == 1:
                                    ePersonalAContratar.first().eliminar_personal(request)

                            m.estado, m.observacioncon = f.cleaned_data['estado'], f.cleaned_data['observacioncon']
                            m.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError(u"Error al validar los datos.")

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"{ex.__str__()}"})

        elif action == 'aprobarinscrito_director_posgrado':
            try:
                with transaction.atomic():
                    model = InscripcionConvocatoria.objects.filter(status=True)
                    if 'id' in request.POST and request.POST['id']:
                        id = request.POST['id'].split(',')
                        model = model.filter(pk__in=id)

                    f = InscripcionConvocatoriaForm(request.POST)
                    if f.is_valid():
                        for m in model:


                            if  int(f.cleaned_data['estado']) == 2 :
                                paralelo = ActaParalelo.objects.get(pk=int(request.POST['idp']))
                                inscripcion, tipo = m, f.cleaned_data.get('tipoPersonal')
                                tipoinscripcion = 1 if Profesor.objects.values('id').filter( persona=inscripcion.postulante.persona, status=True).exists() else 2
                                if not paralelo.get_horario().exists():
                                    raise NameError(u'Debe configurar primero el horario.')
                                # Validacion de choque de horario
                                response = valida_choque_horario_pregrado(request, InscripcionConvocatoria=inscripcion, horarioClases=paralelo.get_horario())

                                if not response.get('result'): return JsonResponse(response)
                                response = valida_choque_horario_en_actas_generadas(request, InscripcionConvocatoria=inscripcion, horarioClases=paralelo.get_horario(),eActaParalelo=paralelo)

                                if not response.get('result'): return JsonResponse(response)

                                if tipo.pk in (2, 3):
                                    label_tipo = 'ALTERNO 1' if tipo.pk == 2 else 'ALTERNO 2'
                                    if PersonalAContratar.objects.filter(actaparalelo=paralelo, tipo_id=tipo.pk,status=True).exists():
                                        raise NameError(f'Exedió el número de postulantes de tipo {label_tipo}.')

                                if tipo.pk == 1:
                                    if PersonalAContratar.objects.filter(actaparalelo=paralelo, tipo_id=1,status=True).exists():
                                        raise NameError( u'Exedió el número de postulantes de tipo principal.')

                                    cantidadcontratos = PersonalAContratar.objects.values('id').filter(
                                        inscripcion=inscripcion, fecha_creacion__year=hoy.year, tipo__id=1,
                                        actaparalelo__convocatoria__tipodocente__in=[18, 15],
                                        actaparalelo__convocatoria__status=True, actaparalelo__acta__status=True,
                                        actaparalelo__status=True, actaparalelo__acta__fecha_legalizacion__isnull=False,
                                        status=True).count()
                                    if cantidadcontratos > 3:
                                        raise NameError(u'Exedió el número de contratos por año para docentes de tipo PROFESOR y PROFESOR AUTOR.')

                                    cuerpo = f"""
                                                        Estimad{'a' if inscripcion.postulante.persona.es_mujer() else 'o'} {f'{inscripcion.postulante.persona.nombres}'.split(' ')[0]}, por medio de la presente se le informa que 
                                                        usted a sido seleccionado por el comité académico <b>{paralelo.acta.comite.nombre}</b> para impartir clases en el módulo <b>{paralelo.convocatoria.asignaturamalla.asignatura}.</b>
                                                        Su carta de invitación será enviada al <b>Sistema de Selección Docentes Posgrado</b> dentro de poco.<br><br>
                                                        Saludos cordiales,
                                                    """
                                    notificacion('Sistema de Selección Docentes Posgrado', cuerpo, inscripcion.postulante.persona,None, '', inscripcion.pk, 1, 'sga', PersonalAContratar, request)

                                if not PersonalAContratar.objects.filter(inscripcion=inscripcion, actaparalelo=paralelo,tipo=tipo, status=True).values('id').exists():
                                    p = PersonalAContratar(inscripcion=inscripcion, tipo=tipo, actaparalelo=paralelo,tipoinscripcion=tipoinscripcion)
                                    p.save(request)

                                    miembrocomite = paralelo.acta.comite.get_integrantes().filter(persona=persona, status=True).first()
                                    eVotacionComiteAcademico = VotacionComiteAcademico.objects.filter(status=True, miembrocomite=miembrocomite)
                                    if not eVotacionComiteAcademico.filter(inscripcion=inscripcion).exists():
                                        eVotacionComiteAcademico = VotacionComiteAcademico(
                                            miembrocomite=miembrocomite,
                                            inscripcion=inscripcion,
                                            tipo=tipo,
                                            actaparalelo=paralelo
                                        )
                                        eVotacionComiteAcademico.save(request)

                                    eHistorialPersonalContratarActaParalelo = HistorialPersonalContratarActaParalelo(
                                        persona=persona,
                                        fecha=hoy,
                                        personalcontratar=p,
                                        estado=1
                                    )
                                    eHistorialPersonalContratarActaParalelo.save(request)
                                    log(u"Agregó personal", request, 'add')
                                else:
                                    raise NameError( f"El postulante %s ya se encuentra registrado. {inscripcion}")
                            else:
                                ePersonalAContratar = PersonalAContratar.objects.filter(status=True, inscripcion=m,actaparalelo_id = int(request.POST['idp']))
                                if ePersonalAContratar.count() == 1:
                                    ePersonalAContratar.first().eliminar_personal(request)

                            m.estado, m.observacioncon = f.cleaned_data['estado'], f.cleaned_data['observacioncon']
                            m.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError(u"Error al validar los datos.")

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"{ex.__str__()}"})


        elif action == 'delinscrito':
            try:
                if request.POST['id']:
                    model = InscripcionConvocatoria.objects.get(pk=int(request.POST['id']))
                    model.status = False
                    return JsonResponse({"error": False})
                else:
                    return JsonResponse({"result": "bad"})
            except Exception as ex:
                pass

        elif action == 'editconvocatoria':
            try:
                form = ConvocatoriaForm(request.POST)
                convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.POST['id'])))
                if convocatoria.tipo == 2:
                    form.establecer_requerido_false()
                    if form.is_valid():

                        start_date = form.cleaned_data['fechainicio']
                        end_date = form.cleaned_data['fechafin']

                        # if start_date and end_date:
                        #     if (end_date - start_date).days < 4:
                        #         return JsonResponse({"result": "bad","mensaje": "Debe lanzar una convocatoria con almenos un plazo mayor a 5 dia."})
                        #
                        # if not start_date == hoy:
                        #     return JsonResponse({"result": "bad", "mensaje": "Favor seleccione la fecha inicio actual."})
                        convocatoria.nombre = form.cleaned_data['nombre']
                        # convocatoria.fechainicio = form.cleaned_data['fechainicio']
                        # convocatoria.fechafin = form.cleaned_data['fechafin']
                        convocatoria.iniciohorario = form.cleaned_data['fechainiciohorario']
                        convocatoria.finhorario = form.cleaned_data['fechafinhorario']
                        convocatoria.activo =  True
                        convocatoria.tipodocente = form.cleaned_data['tipodocente']
                        convocatoria.periodo = form.cleaned_data['periodo']
                        convocatoria.vacantes = form.cleaned_data['vacantes']
                        convocatoria.paralelos = form.cleaned_data.get('paralelos')
                        convocatoria.carrera_id = request.POST['idc']
                        convocatoria.tiempodedicacion_id = request.POST['tiempodedicacion']
                        convocatoria.save(request)
                        convocatoria.notificar_vicerrector_posgrado_edita_convocatoria(request, persona)
                        log(u'Edito convocatoria invitado: %s' % convocatoria, request, "edit")
                        eHistorialConvocatoria = HistorialConvocatoria(
                            convocatoria = convocatoria,
                            persona=persona,
                            fecha=hoy,
                            fechainicio=form.cleaned_data.get('fechainicio'),
                            fechafin=form.cleaned_data.get('fechafin'),
                            tipodocente=form.cleaned_data.get('tipodocente'),
                            vacantes=form.cleaned_data.get('vacantes', 1),
                            paralelos=form.cleaned_data.get('paralelos', 1)
                        )
                        eHistorialConvocatoria.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "form": [{k: v[0]} for k, v in form.errors.items()]})
                else:
                    if form.is_valid():
                        start_date = form.cleaned_data['fechainicio']
                        end_date = form.cleaned_data['fechafin']

                        # if start_date and end_date:
                        #     if (end_date - start_date).days < 4:
                        #         return JsonResponse({"result": "bad",
                        #                              "mensaje": "Debe lanzar una convocatoria con almenos un plazo mayor a 5 dia."})
                        #
                        # if not start_date == hoy:
                        #     return JsonResponse(
                        #         {"result": "bad", "mensaje": "Favor seleccione la fecha inicio actual."})

                        convocatoria.nombre = form.cleaned_data['nombre']
                        # convocatoria.fechainicio = form.cleaned_data['fechainicio']
                        # convocatoria.fechafin = form.cleaned_data['fechafin']
                        convocatoria.iniciohorario = form.cleaned_data['fechainiciohorario']
                        convocatoria.finhorario = form.cleaned_data['fechafinhorario']
                        convocatoria.activo = True
                        convocatoria.tipodocente = form.cleaned_data['tipodocente']
                        convocatoria.periodo = form.cleaned_data['periodo']
                        convocatoria.vacantes = form.cleaned_data['vacantes']
                        convocatoria.paralelos = form.cleaned_data.get('paralelos')
                        convocatoria.carrera_id = request.POST['idc']
                        convocatoria.save(request)
                        convocatoria.perfilrequeridopac.clear()
                        convocatoria.perfilrequeridopac.set(form.cleaned_data['perfilrequeridopac'])
                        convocatoria.campoamplio.set(form.cleaned_data['campoamplio'])
                        convocatoria.campoespecifico.set(form.cleaned_data['campoespecifico'])
                        convocatoria.campodetallado.set(form.cleaned_data['campodetallado'])
                        log(u'Edito convocatoria: %s' % convocatoria, request, "edit")
                        convocatoria.notificar_vicerrector_posgrado_edita_convocatoria(request, persona)
                        eHistorialConvocatoria = HistorialConvocatoria(
                            convocatoria = convocatoria,
                            persona=persona,
                            fecha=hoy,
                            fechainicio=form.cleaned_data.get('fechainicio'),
                            fechafin=form.cleaned_data.get('fechafin'),
                            tipodocente=form.cleaned_data.get('tipodocente'),
                            vacantes=form.cleaned_data.get('vacantes', 1),
                            paralelos=form.cleaned_data.get('paralelos', 1)
                        )
                        eHistorialConvocatoria.save(request)
                        if form.cleaned_data.get('perfilrequeridopac'): eHistorialConvocatoria.perfilrequeridopac.set(form.cleaned_data['perfilrequeridopac'])
                        if form.cleaned_data.get('campoamplio'): eHistorialConvocatoria.campoamplio.set(form.cleaned_data['campoamplio'])
                        if form.cleaned_data.get('campoespecifico'): eHistorialConvocatoria.campoespecifico.set(form.cleaned_data['campoespecifico'])
                        if form.cleaned_data.get('campodetallado'): eHistorialConvocatoria.campodetallado.set(form.cleaned_data['campodetallado'])
                        # convocatoria.notificar_perfiles_compatibles(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "form": [{k: v[0]} for k, v in form.errors.items()]})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'addrequisito':
            try:
                form = RequisitoForm(request.POST, request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.PDF':
                                newfile._name = generar_nombre("archivopdip_", newfile._name)
                            else:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf."})
                if form.is_valid():
                    requisito = Requisito(nombre=form.cleaned_data['nombre'], observacion=form.cleaned_data['observacion'], activo=form.cleaned_data['activo'], tipoarchivo=1)
                    if newfile:
                        requisito.archivo = newfile
                    requisito.save(request)
                    log(u'Adiciono nuevo requisito: %s' % requisito, request, "addrequisito")
                    return JsonResponse({"result": True}, safe=False)
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error en el formulario.", "form": [{k: v[0]} for k, v in form.errors.items()]})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editrequisito':
            try:
                form = RequisitoForm(request.POST)
                requisito = Requisito.objects.get(pk=int(encrypt(request.POST['id'])))
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.PDF':
                                newfile._name = generar_nombre("archivopdip_", newfile._name)
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf."})
                if form.is_valid():
                    requisito.nombre = form.cleaned_data['nombre']
                    requisito.observacion = form.cleaned_data['observacion']
                    requisito.activo = form.cleaned_data['activo']
                    requisito.tipodocumento = 1
                    if newfile:
                        requisito.archivo = newfile
                    requisito.save(request)
                    log(u'Editó el requisito: %s' % requisito, request, "edit")
                    return JsonResponse({"result": True}, safe=False)
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error en el formulario.", "form": [{k: v[0]} for k, v in form.errors.items()]})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {ex.__str__()}"})
                transaction.set_rollback(True)

        elif action == 'editopcional':
            try:
                requisito = RequisitosConvocatoria.objects.get(pk=int(request.POST['id']))
                form = RequisitoUpdateOpcionalForm(request.POST)
                if form.is_valid():
                    requisito.opcional = form.cleaned_data['opcional']
                    requisito.save(request)
                    log(u'Editó el requisito convocatoria : %s' % requisito, request, "edit")
                    return JsonResponse({"result": True}, safe=False)
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error en el formulario.", "form": [{k: v[0]} for k, v in form.errors.items()]})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {ex.__str__()}"})
                transaction.set_rollback(True)

        elif action == 'eliminarequisito':
            try:
                idrequisito = request.POST['id']
                requisito = Requisito.objects.get(pk=idrequisito)
                if not requisito.enuso_convocatoria():
                    requisito.status=False
                    requisito.save()
                    return JsonResponse({"result": "ok", "error":False})
                else:
                    raise NameError("Requisito en uso.")
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": f"Error al eliminar requisito. {ex.__str__()}"})

        elif action == 'eliminarequisitogeneral':
            try:
                idrequisito = request.POST['id']
                requisito = RequisitoGenerales(pk=idrequisito)
                requisito.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar requisito."})

        elif action == 'delinscripcionconvocatoria':
            try:
                ic = InscripcionConvocatoria.objects.get(pk=int(encrypt(request.POST['id'])))
                if InscripcionInvitacion.objects.filter(inscripcion=ic):
                    return JsonResponse({"result": "bad", "mensaje": u"No es posible eliminar al pastulante debido a que ya a sido enviada una invitación."})

                ip = ic.postulante
                ic.status = False
                ip.estado = 1
                ip.save()
                ic.save()
                # if InscripcionInvitacion.objects.filter(inscripcion=ic):
                #     InscripcionInvitacion.objects.filter(inscripcion=ic).update(status=True)
                log(f"Eliminó al postulante {ic}, pk: {ic.pk}", request, 'del')
                return JsonResponse({"error": False})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar inscrito."})

        elif action == 'eliminarequisitoconvocatoria':
            try:
                idrequisitoconvocatoria = request.POST['id']
                requisito = RequisitosConvocatoria.objects.get(pk=idrequisitoconvocatoria)
                requisito.delete()
                return JsonResponse({"result": "ok", "error":False})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar requisito."})

        elif action == 'importarrequisitos':
            try:
                lista = request.POST['lista'].split(',')
                for elemento in lista:

                    if not RequisitoGenerales.objects.filter(requisito_id=elemento, status=True):
                        requisito = RequisitoGenerales(requisito_id=elemento)
                        requisito.save(request)

                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'importarrequisitosconvocatoria':
            try:
                lista = request.POST['lista'].split(',')
                idconvocatoria = request.POST['idconvocatoria']
                for elemento in lista:
                    if not RequisitosConvocatoria.objects.filter(requisito_id=elemento, convocatoria_id=idconvocatoria, status=True):
                        requisito = RequisitosConvocatoria(requisito_id=elemento, convocatoria_id=idconvocatoria)
                        if elemento == '8':
                            requisito.opcional = True
                        requisito.save(request)
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'validarrequisitopostulacion':
            try:
                icr = InscripcionConvocatoriaRequisitos.objects.get(pk=int(request.POST['id']))
                estado, observacion,fecha_caducidad = int(request.POST.get('est', 0)), request.POST.get('obs') , request.POST.get('fecha_caducidad',None)
                icr.estado = estado
                icr.observacion = observacion
                icr.fecharevision = datetime.now()
                icr.fecha_caducidad = None if fecha_caducidad == '' else fecha_caducidad
                icr.save(request)
                historial = HistorialAprobacion(inscripcionrequisito=icr, estado=icr.estado, tiporevision=1, observacion=icr.observacion)
                historial.save(request)
                InscripcionInvitacion.objects.filter(id=icr.inscripcioninvitacion.id).update(pasosproceso_id=4)
                log(u'{} : Validación de Requisito Individual Postu - {}'.format(icr.requisito.requisito.nombre, icr.inscripcioninvitacion), request, "edit")
                return JsonResponse({"result": "ok", 'mensaje': u"Requisito actualizado"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        elif action == 'cargararchivo':
            try:
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        newfile._name = generar_nombre("requisitoconvocatoria_", newfilesd)

                f = RequisitosConvocatoriaInscripcionForm(request.POST)
                f.del_observacion()
                if f.is_valid():
                    inscripcioninvitacion = InscripcionInvitacion.objects.get(pk=request.POST['id'])
                    if pk := int(request.POST.get('pk', 0)):
                        icr = InscripcionConvocatoriaRequisitos.objects.get(pk=pk)
                    else:
                        icr = InscripcionConvocatoriaRequisitos(inscripcioninvitacion=inscripcioninvitacion, requisito_id=request.POST['idevidencia'], observacion='Ninguna', estado=1)

                    ha = HistorialAprobacion(inscripcionrequisito=icr, observacion='Ninguna', estado=1, tiporevision=1)
                    if newfile:
                        icr.archivo = ha.archivo = newfile

                    icr.save(request)
                    ha.save(request)
                    log(u'Editó inscripcion convocatoria requisito de postulaciondip: %s' % icr, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error en el formulario, algunos campos se encuentran vacíos.')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})


        elif action == 'validarequisitofinalpostulacion':
            try:
                with transaction.atomic():
                    inscripcion = InscripcionInvitacion.objects.get(pk=int(request.POST['id']))
                    inscripcion.fechaarequisitos = datetime.now()
                    inscripcion.estadorequisitos = request.POST['estado']
                    inscripcion.observacionrequisitos = request.POST['observacion'].upper()
                    inscripcion.save(request)
                    inscripcionrequisito = inscripcion.inscripcionrequisito_set.filter(status=True).order_by('-requisitoproceso__requisito_id').first()
                    historial = HistorialAprobacionInscripcion(inscripcionrequisito=inscripcionrequisito,
                                                               estado=inscripcion.estadorequisitos,
                                                               tiporevision=2,
                                                               observacion=inscripcion.observacionrequisitos,
                                                               persona=persona)
                    historial.save(request)
                    ePersonalAContratar = inscripcion.get_personal_a_contratar()
                    ePersonalAContratar.estado = 4 if int(inscripcion.estadorequisitos) == 2  else 3
                    ePersonalAContratar.save(request)

                    respmensaje = 'Validación final guardada de ' + str(inscripcion.inscripcion.postulante.persona)
                    return JsonResponse({"result": "ok", 'mensaje': respmensaje})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'validarrequisito':
            try:
                inscripcion = InscripcionConvocatoriaRequisitos.objects.get(id=int(request.POST['id']))
                inscripcion.estado = request.POST['est']
                inscripcion.observacion = request.POST['obs']
                inscripcion.save(request)
                historial = HistorialAprobacion(inscripcionrequisito=inscripcion,
                                                estado=inscripcion.estado,
                                                tiporevision=1,
                                                observacion=inscripcion.observacion)
                historial.save(request)
                log(u'{} : Validación de Requisito Individual Postu - {}'.format(inscripcion.requisito.requisito.nombre, inscripcion), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'validarrequisitogeneral':
            try:
                requisitogeneral = RequisitoGeneralesPersona.objects.get(id=int(request.POST['id']))
                requisitogeneral.estado = request.POST['est']
                requisitogeneral.observacion = request.POST['obs']
                requisitogeneral.save(request)
                historial = HistorialReqGeneral(requisitogeneral=requisitogeneral,
                                                estado=requisitogeneral.estado,
                                                observacion=requisitogeneral.observacion)
                historial.save(request)
                log(u'{} : Validación de Requisito Individual Postu - {}'.format(
                    requisitogeneral.requisitogeneral.requisito.nombre, requisitogeneral), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'validarequisitoconvocatoria':
            try:
                with transaction.atomic():
                    inscripcion = InscripcionConvocatoria.objects.get(pk=int(request.POST['id']))
                    inscripcion.estado = request.POST['estado']
                    inscripcion.observacioncon = request.POST['observacion'].upper()
                    inscripcion.save(request)
                    historial = HistorialAprobacionIns(inscripcion=inscripcion,
                                                       estado=inscripcion.estado,
                                                       tiporevision=2,
                                                       observacion=inscripcion.observacioncon)
                    historial.save(request)
                    respmensaje = 'Validación guardada de ' + str(inscripcion.postulante.persona)
                    return JsonResponse({"result": False, 'modalsuccess': True, 'mensaje': respmensaje}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'validarequisitogeneral':
            try:
                with transaction.atomic():
                    inscripcion = InscripcionConvocatoria.objects.get(pk=int(request.POST['id']))
                    inscripcion.estadogen = request.POST['estado']
                    inscripcion.observaciongen = request.POST['observacion'].upper()
                    inscripcion.save(request)
                    historial = HistorialAprobacionIns(inscripcion=inscripcion,
                                                       estado=inscripcion.estadogen,
                                                       tiporevision=1,
                                                       observacion=inscripcion.observaciongen)
                    historial.save(request)
                    respmensaje = 'Validación guardada de ' + str(inscripcion.postulante.persona)
                    return JsonResponse({"result": False, 'modalsuccess': True, 'mensaje': respmensaje}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'descargarlistadopdf':
            try:
                data = {}
                data['convocatoria'] = convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.POST['idconv'])))
                data['inscritospdf'] = convocatoria.inscripcionconvocatoria_set.filter(status=True).order_by('postulante__persona__apellido1', 'postulante__persona__apellido2')
                return conviert_html_to_pdf(
                    'adm_postulacion/descargarlistadopdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        elif action == 'editdatospersonales':
            try:
                ip = InscripcionPostulante.objects.get(pk=int(request.POST['id']))
                form = DatoPersonalForm(request.POST)
                if form.is_valid():
                    ip.persona.nombres = form.cleaned_data['nombres']
                    ip.persona.apellido1 = form.cleaned_data['apellido1']
                    ip.persona.apellido2 = form.cleaned_data['apellido2']
                    ip.persona.telefono = form.cleaned_data['telefono']
                    ip.persona.email = form.cleaned_data['email']
                    ip.persona.save(request)
                    return JsonResponse({"result": True, "mensaje": u"Datos modificados correctamente."})
                else:
                    return JsonResponse({"result": False, "mensaje": u"Error al validar los datos."})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error de conexión."})

        elif action == 'agregardatosextra':
            try:
                ip = InscripcionConvocatoria.objects.get(pk=int(request.POST['id']))

                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() in  ['.pdf', '.PDF']:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})

                form = DatoPersonalExtraForm(request.POST, request.FILES)
                if form.is_valid():
                    ip.link = form.cleaned_data['link']
                    ip.save(request)

                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("hojavida_", newfile._name)
                        ip.postulante.hoja_vida = newfile
                        ip.postulante.save(request)
                    return JsonResponse({"result": True, "mensaje": u"Datos modificados correctamente."})
                else:
                    return JsonResponse({"result": False, "mensaje": u"Error al validar los datos."})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error de conexión."})

        elif action == 'detalletitulo':
            try:
                data['titulacion'] = titulacion = Titulacion.objects.get(pk=int(request.POST['id']))
                if titulacion.usuario_creacion:
                    data['personacreacion'] = Persona.objects.get(
                        usuario=titulacion.usuario_creacion) if titulacion.usuario_creacion.id > 1 else ""
                template = get_template("adm_postulacion/detalletitulo.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addrolpersonalapoyo':
            try:
                f = RolPersonalApoyoForm(request.POST)
                if f.is_valid():
                    if not RolPersonalApoyo.objects.values('id').filter(descripcion=f.cleaned_data['descripcion'].strip().upper()).exists():
                        rol = RolPersonalApoyo(descripcion=f.cleaned_data['descripcion'])
                        rol.save(request)
                        log(u"Adicionó rol del personal de apoyo %s" %rol, request, 'add')
                        return JsonResponse({"result": True})
                    else:
                        return JsonResponse({"result": False, "mensaje": f"Este rol ya se encuentra registrado."})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error al de conexión. {ex.__str__()}"})

        elif action == 'editrolpersonalapoyo':
            try:
                rol = RolPersonalApoyo.objects.get(pk=request.POST['id'])
                f = RolPersonalApoyoForm(request.POST)
                if f.is_valid():
                    if RolPersonalApoyo.objects.values('id').filter(descripcion=f.cleaned_data['descripcion'].strip().upper()).exists():
                        return JsonResponse({"result": False, "mensaje": f"Este rol ya se encuentra registrado."})
                    rol.descripcion = f.cleaned_data['descripcion']
                    rol.save(request)
                    log(u"Editó rol del personal de apoyo %s" % rol, request, 'add')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error al adicionar rol. {ex.__str__()}"})

        elif action == 'delrolpersonalapoyo':
            try:
                rol = RolPersonalApoyo.objects.get(pk=int(encrypt(request.POST['id'])))
                rol.status = False
                rol.save()
                log(u'Eliminó rol del personal de apoyo %s' % rol, request, 'del')
                return JsonResponse({"result": True, "error":False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error al eliminar rol. {ex.__str__()}"})

        elif action == 'addpersonalapoyo':
            try:
                f = PersonalApoyoForm(request.POST)
                f.edit(request.POST['persona'])
                if f.is_valid():
                    if not PersonalApoyo.objects.filter(persona=f.cleaned_data['persona']).values('id').exists():
                        pa = PersonalApoyo(persona=f.cleaned_data['persona'])
                        pa.save(request)
                        log(u"Adicionó personal de apoyo %s" % pa, request, 'add')
                        return JsonResponse({"result": True})
                    else:
                        return JsonResponse({"result": False, "mensaje":u"Persona repetida"})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error al adicionar personal de apoyo. {ex.__str__()}"})

        elif action == 'editpersonalapoyo':
            try:
                pa = PersonalApoyo.objects.get(pk=request.POST['id'])
                f = PersonalApoyoForm(request.POST)
                f.edit(request.POST['persona'])
                if f.is_valid():
                    pa.persona=f.cleaned_data['persona']
                    pa.save(request)
                    log(u"Editó personal de apoyo %s" % pa, request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error al editar personal de apoyo. {ex.__str__()}"})

        elif action == 'delpersonalapoyo':
            try:
                pa = PersonalApoyo.objects.get(pk=int(encrypt(request.POST['id'])))
                pa.status = False
                pa.save(request)
                log(u'Eliminó personal de apoyo %s' % pa, request, 'del')
                return JsonResponse({"result": True, 'error': False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error al eliminar el personal de apoyo. {ex.__str__()}"})

        elif action == 'addpersonalapoyomaestria':
            try:
                f = PersonalApoyoMaestriaForm(request.POST)
                f.edit(request.POST.getlist('cohorte'))

                if PersonalApoyoMaestria.objects.values('id').filter(personalapoyo=request.POST['personalapoyo'], carrera=request.POST['carrera'], periodo=request.POST['cohorte'], status=True):
                    return JsonResponse({"result": False, "mensaje": u"El personal de apoyo, carrera y periodo ya se encuentran registrados."})

                if f.is_valid():
                    pa = PersonalApoyoMaestria(personalapoyo=f.cleaned_data['personalapoyo'],
                                               fechainicio=f.cleaned_data['fechainicio'],
                                               fechafin=f.cleaned_data['fechafin'],
                                               carrera=f.cleaned_data['carrera'])
                    pa.save(request)
                    pa.periodo.clear()
                    pa.periodo.set(f.cleaned_data['cohorte'])
                    log(u"Adicionó personal de apoyo maestría %s" % pa, request, 'add')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error al adicionar personal de apoyo maestría. {ex.__str__()}"})

        elif action == 'editpersonalapoyomaestria':
            try:
                pa = PersonalApoyoMaestria.objects.get(pk=request.POST['id'])
                f = PersonalApoyoMaestriaForm(request.POST)
                f.edit(request.POST.getlist('cohorte'))
                if f.is_valid():
                    pa.personalapoyo=f.cleaned_data['personalapoyo']
                    pa.fechainicio=f.cleaned_data['fechainicio']
                    pa.fechafin=f.cleaned_data['fechafin']
                    pa.carrera=f.cleaned_data['carrera']
                    pa.save(request)
                    pa.periodo.clear()
                    pa.periodo.set(f.cleaned_data['cohorte'])
                    log(u"Editó personal de apoyo maestria %s" % pa, request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error al editar personal de apoyo maestria. {ex.__str__()}"})

        elif action == 'subir_manual_informe_contratacion':
            try:
                f = RequisitosInscripcionForm(request.POST,request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.PDF':
                                newfile._name = generar_nombre("informcontratacionmanual_", newfile._name)
                            else:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf."})

                pk = int(request.POST.get('id','0'))
                eInformeContratacion = InformeContratacion.objects.get(pk=pk)
                if f.is_valid():
                    documento_informe = eInformeContratacion.get_documento_informe()
                    if newfile:
                        documento_informe.archivo = newfile
                        documento_informe.save(request)
                        eInformeContratacion.estado= 3
                        eInformeContratacion.actualizar_todos_los_integrantes_a_firmado_completo(request)
                        eInformeContratacion.save(request)
                        eInformeContratacion.guardar_historial_informe_contratacion(request, persona, 'informe subido manual', eInformeContratacion.get_documento_informe().archivo)
                    log(u"Editó documento informe contratacion %s" % documento_informe, request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error al editar el documento del informe de contratación. {ex.__str__()}"})

        elif action == 'delpersonalapoyomaestria':
            try:
                pa = PersonalApoyoMaestria.objects.get(pk=int(encrypt(request.POST['id'])))
                pa.status = False
                pa.save()
                log(u'Eliminó personal de apoyo maestria %s' % pa, request, 'del')
                return JsonResponse({"result": True, "error": False, "rt": rt})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error de conexión. {ex.__str__()}"})

        elif action == 'adddocumentoinvitacion':
            try:
                f = DocumentoInvitacionForm(request.POST, request.FILES)
                if f.is_valid():
                    fdi = DocumentoInvitacion(secuenciadocumento=f.cleaned_data['secuenciadocumento'], clasificacion=f.cleaned_data['clasificacion'])
                    if 'firma' in request.FILES:
                        newfile = request.FILES['firma']
                        if newfile:
                            if newfile.size > 6291456:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                required = ['.png', '.jpg', '.jpeg']
                                if ext in required or ext in [x.upper() for x in required]:
                                    nombre_persona = unicodedata.normalize('NFD', u"%s" % fdi.clasificacion).encode('ascii', 'ignore').decode("utf-8")
                                    newfile._name = generar_nombre(f"{nombre_persona}_".lower().replace(' ', '_'), newfile._name)
                                    fdi.archivo = newfile
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extención %s. " % required})
                    fdi.save(request)
                    log(f"Agregó documento {fdi}", request, 'add')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": u"Error de conexión %s. " % ex.__str__()})

        elif action == 'editdocumentoinvitacion':
            try:
                f = DocumentoInvitacionForm(request.POST, request.FILES)
                fdi = DocumentoInvitacion.objects.get(pk=int(request.POST['id']))

                if f.is_valid():
                    fdi.secuenciadocumento=f.cleaned_data['secuenciadocumento']
                    fdi.codigo=f.cleaned_data['codigo']
                    fdi.estado=f.cleaned_data['estado']
                    fdi.clasificacion=f.cleaned_data['clasificacion']

                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            if newfile.size > 6291456:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                required = ['.png', '.jpg', '.jpeg']
                                if ext in required or ext in [x.upper() for x in required]:
                                    nombre = unicodedata.normalize('NFD', u"%s" % fdi.clasificacion).encode('ascii', 'ignore').decode("utf-8")
                                    newfile._name = generar_nombre(f"{nombre}_".lower().replace(' ', '_'), newfile._name)
                                    fdi.archivo = newfile
                                else:
                                    return JsonResponse({"result": False, "mensaje": u"Error, Solo archivo con extención %s. " % required})
                    fdi.save(request)
                    log(f"Editó documento {fdi}", request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": u"Error de conexión %s. " % ex.__str__()})

        elif action == 'deldocumentoinvitacion':
            try:
                pa = DocumentoInvitacion.objects.get(pk=int(request.POST['id']))
                pa.status = False
                pa.save()
                log(u'Eliminó documento %s' % pa, request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error de conexión. {ex.__str__()}"})

        elif action == 'addclasificaciondocumento':
            try:
                f = ClasificacionDocumentoInvitacionForm(request.POST)
                if f.is_valid():
                    description = f.cleaned_data['descripcion'].strip().upper()
                    if ClasificacionDocumentoInvitacion.objects.values('id').filter(descripcion=description, status=True).exists():
                        return JsonResponse({"result": False, "mensaje": f"La clasificación {description} ya existe"})

                    clasificacion = ClasificacionDocumentoInvitacion(descripcion=description, abreviatura=f.cleaned_data.get('abreviatura', '').strip().upper())
                    clasificacion.save(request)
                    log(u"Adicionó clasificacion ** %s ** para postulaciondip_documentoinvitacion " % clasificacion, request, 'add')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error de conexión. {ex.__str__()}"})

        elif action == 'editclasificaciondocumento':
            try:
                clasificacion = ClasificacionDocumentoInvitacion.objects.get(id=int(encrypt(request.POST['id'])))
                msj = f"Editó clasificación {clasificacion.descripcion} por %s"
                f = ClasificacionDocumentoInvitacionForm(request.POST)
                if f.is_valid():
                    description = f.cleaned_data['descripcion'].strip().upper()
                    abreviatura = f.cleaned_data['abreviatura'].strip().upper()
                    if not clasificacion.descripcion == description and ClasificacionDocumentoInvitacion.objects.values('id').filter(descripcion=description, status=True).exists():
                        return JsonResponse({"result": False, "mensaje": f"Ya existe un documento llamado: {description}."})

                    clasificacion.descripcion, clasificacion.abreviatura = description, abreviatura
                    clasificacion.save(request)

                    log(msj % clasificacion, request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error al adicionar rol. {ex.__str__()}"})

        elif action == 'delclasificaciondocumento':
            try:
                pa = ClasificacionDocumentoInvitacion.objects.get(pk=int(encrypt(request.POST['id'])))
                pa.status = False
                pa.save()
                log(u'Eliminó clasificacion %s' % pa, request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error de conexión. {ex.__str__()}"})

        elif action == 'addsecuencia':
            try:
                f = SecuenciaDocumentoInvitacionForm(request.POST)
                if f.is_valid():
                    secuencia = SecuenciaDocumentoInvitacion(anioejercicio=f.cleaned_data['anioejercicio'], secuencia=f.cleaned_data['secuencia'].strip(), tipo=f.cleaned_data['tipo'])
                    secuencia.save(request)
                    log(u"Adicionó secuencia ** %s ** para postulaciondip_documentoinvitacion " % secuencia, request, 'add')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error de conexión. {ex.__str__()}"})

        elif action == 'editsecuencia':
            try:
                secuencia = SecuenciaDocumentoInvitacion.objects.get(id=int(encrypt(request.POST['id'])))
                f = SecuenciaDocumentoInvitacionForm(request.POST)
                if f.is_valid():
                    secuencia.tipo = f.cleaned_data['tipo']
                    secuencia.secuencia = f.cleaned_data['secuencia']
                    secuencia.anioejercicio = f.cleaned_data['anioejercicio']
                    secuencia.save(request)
                    log(f"Editó secuencia {secuencia}", request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error de conexión. {ex.__str__()}"})

        elif action == 'delsecuencia':
            try:
                pa = SecuenciaDocumentoInvitacion.objects.get(pk=int(encrypt(request.POST['id'])))
                pa.status = False
                pa.save()
                log(u'Eliminó secuencia %s' % pa, request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error de conexión. {ex.__str__()}"})

        elif action == 'addfirmas':
            try:
                f = FirmasDocumentoInvitacionForm(request.POST, request.FILES)
                f.edit(request.POST['persona'])
                hoy = datetime.now()
                if f.is_valid():
                    fdi = FirmasDocumentoInvitacion(responsabilidad=f.cleaned_data['responsabilidad'], cargo=f.cleaned_data['cargo'], documentoinvitacion=f.cleaned_data['documentoinvitacion'],persona=f.cleaned_data['persona'])
                    if 'firma' in request.FILES:
                        newfile = request.FILES['firma']
                        if newfile:
                            if newfile.size > 6291456:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                required = ['.png', '.jpg', '.jpeg']
                                if ext in required or ext in [x.upper() for x in required]:
                                    nombre_persona = unicodedata.normalize('NFD', u"%s" % fdi.persona).encode('ascii', 'ignore').decode("utf-8")
                                    newfile._name = generar_nombre(f"{nombre_persona}_".lower().replace(' ', '_'), newfile._name)
                                    fdi.firma = newfile
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extención %s. " % required})
                    fdi.save(request)
                    log(f"Agregó firma {fdi}", request, 'add')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error de conexión. {ex.__str__()}"})

        elif action == 'editfirmas':
            try:
                hoy = datetime.now()
                fdi = FirmasDocumentoInvitacion.objects.filter(pk=request.POST['id']).first()
                f = FirmasDocumentoInvitacionForm(request.POST, request.FILES)
                f.edit(request.POST['persona'])
                if f.is_valid():
                    fdi.persona = f.cleaned_data['persona']
                    fdi.cargo = f.cleaned_data['cargo']
                    fdi.responsabilidad = f.cleaned_data['responsabilidad']
                    fdi.documentoinvitacion = f.cleaned_data['documentoinvitacion']
                    if 'firma' in request.FILES:
                        newfile = request.FILES['firma']
                        if newfile:
                            if newfile.size > 6291456:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                required = ['.png', '.jpg', '.jpeg']
                                if ext in required or ext in [x.upper() for x in required]:
                                    nombre_persona = unicodedata.normalize('NFD', u"%s" % fdi.persona).encode('ascii', 'ignore').decode("utf-8")
                                    newfile._name = generar_nombre(f"{nombre_persona}_".lower().replace(' ', '_'), newfile._name)
                                    fdi.firma = newfile
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extención %s. " % required})
                    fdi.save(request)
                    log(f"Editó firma {fdi}", request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error de conexión. {ex.__str__()}"})

        elif action == 'delfirmas':
            try:
                pa = FirmasDocumentoInvitacion.objects.get(pk=int(encrypt(request.POST['id'])))
                pa.status = False
                pa.save()
                log(u'Eliminó firma %s' % pa, request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error de conexión. {ex.__str__()}"})

        elif action == 'signaturechange':
            try:
                data['change'] = {"id": request.POST.get('id', ''), "value": request.POST.get('value', '')}
                return render(request, "adm_postulacion/documentoscontrato/informetecnicocontrataciondocente.html", {"data":data})
            except Exception as ex:
                pass

        elif action == 'addcomiteacademico':
            try:
                f = ComiteAcademicoPosgradoForm(request.POST)
                if f.is_valid():
                    f.save(request)
                    log(u"Adicionó commité académico %s" % f.cleaned_data.get('nombre'), request, 'add')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'editcomiteacademico':
            try:
                model = ComiteAcademicoPosgrado.objects.get(pk=request.POST['id'])
                f = ComiteAcademicoPosgradoForm(request.POST, instance=model)
                if f.is_valid():
                    f.save(request)
                    log(u"Editó commité académico %s" % f.cleaned_data.get('nombre'), request, 'edit')
                    messages.success(request, 'El comité académico se actualizó correctamente.')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'delcomiteacademico':
            try:
                model = ComiteAcademicoPosgrado.objects.get(pk=encrypt(request.POST['id']))
                model.status = False
                model.save(request)
                log(u"Eliminó el comité académico %s" % model.nombre, request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'addintegrantecomiteacademico':
            try:
                f = IntegranteComiteAcademicoPosgradoForm(request.POST)
                f.edit(request.POST['persona'])
                if f.is_valid():
                    ica = IntegranteComiteAcademicoPosgrado(persona=f.cleaned_data['persona'],tipo_cargo=f.cleaned_data['tipo_cargo'], comite_id=request.POST['comite'], cargo=f.cleaned_data['cargo'], tipo=f.cleaned_data.get('tipo'))
                    ica.save(request)
                    ica.asignar_permiso_al_modulo(request)
                    log(u"Adicionó a %s al comité académico %s" % (ica.persona, ica.comite), request, 'add')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'editintegrantecomiteacademico':
            try:
                f = IntegranteComiteAcademicoPosgradoForm(request.POST)
                ica = IntegranteComiteAcademicoPosgrado.objects.get(pk=request.POST['id'])
                f.edit(request.POST['persona'])
                if f.is_valid():
                    ica.persona = f.cleaned_data.get('persona')
                    ica.cargo = f.cleaned_data.get('cargo')
                    ica.tipo = f.cleaned_data.get('tipo')
                    ica.tipo_cargo = f.cleaned_data.get('tipo_cargo')
                    ica.save(request)
                    ica.asignar_permiso_al_modulo(request)
                    log(u"Editó el comité académico %s" % ica.comite, request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'delintegrantecomiteacademico':
            try:
                model = IntegranteComiteAcademicoPosgrado.objects.get(pk=encrypt(request.POST['id']))
                model.status = False
                model.save(request)
                log(u"Eliminó a %s del comité académico %s" % (model.persona, model.comite), request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'addactaseleccion':
            try:
                f = ActaSeleccionDocenteForm(request.POST)
                codigo = null_to_decimal(ActaSeleccionDocente.objects.filter(fecha_creacion__year=hoy.year).aggregate(code=Max('codigo'))['code']) + 1
                if f.is_valid():
                    acta = ActaSeleccionDocente(comite=f.cleaned_data['comite'],
                                                lugar=f.cleaned_data['lugar'],
                                                codigo=codigo,
                                                plazo_generacion=hoy + timedelta(variable_valor('PLAZO_GENERAR_ACTA_SELECCION')),
                                                plazo_legalizacion=hoy + timedelta(variable_valor('PLAZO_LEGALIZAR_ACTA_SELECCION')),
                                                observacion_ep=f.cleaned_data.get('observacion_ep'),
                                                tipo_formato_acta=f.cleaned_data.get('tipo_formato_acta'),
                                                )
                    acta.save(request)
                    acta.get_secuencia()
                    acta.generar_plan_de_accion_automatico(request)
                    acta.comite.asignar_permiso_al_modulo(request)
                    acta.actualizar_documeto_pdf_acta(request)
                    acta.guardar_recorrido_acta_seleccion_docente(request,actaparalelo=None,persona=persona,observacion = "Generación inicial del acta",archivo =None)

                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'add_orden_firma':
            try:
                f = OrdenFirmaActaForm(request.POST)
                if f.is_valid():
                    eOrdenFirmaActaSeleccionDocente = OrdenFirmaActaSeleccionDocente(descripcion=f.cleaned_data['descripcion'], orden=f.cleaned_data['orden'], funcion=f.cleaned_data['funcion'])
                    eOrdenFirmaActaSeleccionDocente.save(request)
                    log(u"Add orden firma acta de selección", request, 'add')
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.",
                                         "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'add_integrantefirmainformecontratacion':
            try:
                f = InformeContratacionIntegrantesFirmaForm(request.POST)
                pk = int(request.POST.get('id','0'))
                if pk == 0:
                    raise NameError("Parametro no encontrado")
                eInformeContratacion = InformeContratacion.objects.get(pk=pk)
                f.edit(request.POST['persona'])
                if f.is_valid():
                    eInformeContratacionIntegrantesFirma = InformeContratacionIntegrantesFirma(informecontratacion= eInformeContratacion, ordenFirmaInformeContratacion=f.cleaned_data['responsabilidadfirma'], persona=f.cleaned_data['persona'])
                    eInformeContratacionIntegrantesFirma.save(request)
                    log(u"Add eInformeContratacionIntegrantesFirma", request, 'add')
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.",
                                         "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'add_responsabilidad_firma':
            try:
                f = ResponsabilidadFirmaForm(request.POST)
                if f.is_valid():
                    eResponsabilidadFirma = ResponsabilidadFirma(responsabilidad=f.cleaned_data['responsabilidad'])
                    eResponsabilidadFirma.save(request)
                    log(u"Add responsable firma", request, 'add')
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.",
                                         "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'add_orden_firma_informe_contratacion':
            try:
                f = OrdenFirmaInformeContratacionForm(request.POST)
                if f.is_valid():
                    eOrdenFirmaInformeContratacion = OrdenFirmaInformeContratacion(responsabilidadfirma=f.cleaned_data['responsabilidadfirma'], orden=f.cleaned_data['orden'])
                    eOrdenFirmaInformeContratacion.save(request)
                    log(u"Add orden firma informe contratacion", request, 'add')
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.",
                                         "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'add_mensaje_predeterminado':
            try:
                f = MensajePredeterminadoForm(request.POST)
                if f.is_valid():
                    eMensajePredeterminado = MensajePredeterminado(descripcion=f.cleaned_data['descripcion'])
                    eMensajePredeterminado.save(request)
                    log(u"Add mensaje predeterminado", request, 'add')
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.",
                                         "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'add_rubrica_baremo':
            try:
                f = RubricaSeleccionDocenteForm(request.POST)
                if f.is_valid():
                    eRubricaSeleccionDocente = RubricaSeleccionDocente(descripcion=f.cleaned_data['descripcion'],activo=f.cleaned_data['activo'])
                    eRubricaSeleccionDocente.save(request)
                    log(u"Add rubrica seleccion docente", request, 'add')
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.",
                                         "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'add_item_rubrica_baremo':
            try:
                f = DetalleItemRubricaSeleccionDocenteForm(request.POST)
                if f.is_valid():
                    eDetalleItemRubricaSeleccionDocente = DetalleItemRubricaSeleccionDocente(rubricaselecciondocente_id = request.POST['id'],descripcion=f.cleaned_data['descripcion'],orden=f.cleaned_data['orden'])
                    eDetalleItemRubricaSeleccionDocente.save(request)
                    log(u"Add detalle rubrica seleccion docente", request, 'add')
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.",
                                         "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})


        elif action == 'add_subitem_rubrica_baremo':
            try:
                f = DetalleSubItemRubricaSeleccionDocenteForm(request.POST)
                if f.is_valid():
                    eDetalleSubItemRubricaSeleccionDocente = DetalleSubItemRubricaSeleccionDocente(detalleitemrubricaselecciondocente_id = request.POST['id'],descripcion=f.cleaned_data['descripcion'],puntaje=f.cleaned_data['puntaje'],orden=f.cleaned_data['orden'])
                    eDetalleSubItemRubricaSeleccionDocente.save(request)
                    log(u"Add detalle sub item rubrica seleccion docente", request, 'add')
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.",
                                         "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'edit_orden_firma':
            try:
                f = OrdenFirmaActaForm(request.POST)
                eOrdenFirmaActaSeleccionDocente = OrdenFirmaActaSeleccionDocente.objects.get(pk=request.POST.get('id'))
                if f.is_valid():
                    eOrdenFirmaActaSeleccionDocente.descripcion=f.cleaned_data.get('descripcion')
                    eOrdenFirmaActaSeleccionDocente.orden=f.cleaned_data.get('orden')
                    eOrdenFirmaActaSeleccionDocente.funcion=f.cleaned_data.get('funcion')
                    eOrdenFirmaActaSeleccionDocente.save(request)
                    log(u"Editó orden firma acta de selección", request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'edit_integrantefirmainformecontratacion':
            try:
                f = InformeContratacionIntegrantesFirmaForm(request.POST)
                eInformeContratacionIntegrantesFirma = InformeContratacionIntegrantesFirma.objects.get(pk=request.POST.get('id'))
                f.edit(request.POST['persona'])
                if f.is_valid():
                    eInformeContratacionIntegrantesFirma.ordenFirmaInformeContratacion=f.cleaned_data.get('responsabilidadfirma')
                    eInformeContratacionIntegrantesFirma.persona=f.cleaned_data.get('persona')
                    eInformeContratacionIntegrantesFirma.save(request)
                    log(u"Editó eInformeContratacionIntegrantesFirma", request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})


        elif action == 'edit_responsable_firma':
            try:
                f = ResponsabilidadFirmaForm(request.POST)
                eResponsabilidadFirma = ResponsabilidadFirma.objects.get(pk=request.POST.get('id'))
                if f.is_valid():
                    eResponsabilidadFirma.responsabilidad=f.cleaned_data.get('responsabilidad')
                    eResponsabilidadFirma.save(request)
                    log(u"Editó responsabilidad firma", request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'edit_orden_firma_informe_contratacion':
            try:
                f = OrdenFirmaInformeContratacionForm(request.POST)
                eOrdenFirmaInformeContratacion = OrdenFirmaInformeContratacion.objects.get(pk=request.POST.get('id'))
                if f.is_valid():
                    eOrdenFirmaInformeContratacion.responsabilidadfirma=f.cleaned_data.get('responsabilidadfirma')
                    eOrdenFirmaInformeContratacion.orden=f.cleaned_data.get('orden')
                    eOrdenFirmaInformeContratacion.save(request)
                    log(u"Editó orden firma acta de selección", request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'edit_mensaje_predeteminado':
            try:
                f = MensajePredeterminadoForm(request.POST)
                eMensajePredeterminado = MensajePredeterminado.objects.get(pk=request.POST.get('id'))
                if f.is_valid():
                    eMensajePredeterminado.descripcion=f.cleaned_data.get('descripcion')
                    eMensajePredeterminado.save(request)
                    log(u"Editó mensaje predeterminado", request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'edit_rubrica_baremo':
            try:
                f = RubricaSeleccionDocenteForm(request.POST)
                eRubricaSeleccionDocente = RubricaSeleccionDocente.objects.get(pk=request.POST.get('id'))
                if f.is_valid():
                    eRubricaSeleccionDocente.descripcion=f.cleaned_data.get('descripcion')
                    eRubricaSeleccionDocente.activo=f.cleaned_data.get('activo')
                    eRubricaSeleccionDocente.save(request)
                    log(u"Editó RubricaSeleccionDocente baremo", request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'edit_item_rubrica_baremo':
            try:
                f = DetalleItemRubricaSeleccionDocenteForm(request.POST)
                eDetalleItemRubricaSeleccionDocente = DetalleItemRubricaSeleccionDocente.objects.get(pk=request.POST.get('id'))
                if f.is_valid():
                    eDetalleItemRubricaSeleccionDocente.descripcion=f.cleaned_data.get('descripcion')
                    eDetalleItemRubricaSeleccionDocente.orden=f.cleaned_data.get('orden')
                    eDetalleItemRubricaSeleccionDocente.save(request)
                    log(u"Editó DetalleItemRubricaSeleccionDocente baremo", request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'edit_subitem_rubrica_baremo':
            try:
                f = DetalleSubItemRubricaSeleccionDocenteForm(request.POST)
                eDetalleSubItemRubricaSeleccionDocente = DetalleSubItemRubricaSeleccionDocente.objects.get(pk=request.POST.get('id'))
                if f.is_valid():
                    eDetalleSubItemRubricaSeleccionDocente.descripcion=f.cleaned_data.get('descripcion')
                    eDetalleSubItemRubricaSeleccionDocente.puntaje=f.cleaned_data.get('puntaje')
                    eDetalleSubItemRubricaSeleccionDocente.orden=f.cleaned_data.get('orden')
                    eDetalleSubItemRubricaSeleccionDocente.save(request)
                    log(u"Editó eDetalleSubItemRubricaSeleccionDocente baremo", request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'delete_orden_firma':
            try:
                eOrdenFirmaActaSeleccionDocente = OrdenFirmaActaSeleccionDocente.objects.get(pk=int(request.POST['id']))
                log(u'Elimino orden firma: %s' % eOrdenFirmaActaSeleccionDocente, request, "del")
                eOrdenFirmaActaSeleccionDocente.status = False
                eOrdenFirmaActaSeleccionDocente.save(request)
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delete_integrantefirmainformecontratacion':
            try:
                eInformeContratacionIntegrantesFirma = InformeContratacionIntegrantesFirma.objects.get(pk=int(request.POST['id']))
                log(u'Elimino InformeContratacionIntegrantesFirma: %s' % eInformeContratacionIntegrantesFirma, request, "del")
                eInformeContratacionIntegrantesFirma.status = False
                eInformeContratacionIntegrantesFirma.save(request)
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delete_responsabilidad_firma':
            try:
                eResponsabilidadFirma = ResponsabilidadFirma.objects.get(pk=int(request.POST['id']))
                log(u'Elimino  ResponsabilidadFirma: %s' % eResponsabilidadFirma, request, "del")
                eResponsabilidadFirma.status = False
                eResponsabilidadFirma.save(request)
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})


        elif action == 'delete_orden_firma_informe_contratacion':
            try:
                eOrdenFirmaInformeContratacion = OrdenFirmaInformeContratacion.objects.get(pk=int(request.POST['id']))
                log(u'Elimino orden firma: %s' % eOrdenFirmaInformeContratacion, request, "del")
                eOrdenFirmaInformeContratacion.status = False
                eOrdenFirmaInformeContratacion.save(request)
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delete_mensaje_predeteminado':
            try:
                eMensajePredeterminado = MensajePredeterminado.objects.get(pk=int(request.POST['id']))
                log(u'Elimino mensaje predeterminado: %s' % eMensajePredeterminado, request, "del")
                eMensajePredeterminado.status = False
                eMensajePredeterminado.save(request)
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delete_rubrica_baremo':
            try:
                eRubricaSeleccionDocente = RubricaSeleccionDocente.objects.get(pk=int(request.POST['id']))
                log(u'Elimino rubrica baremo: %s' % eRubricaSeleccionDocente, request, "del")
                eRubricaSeleccionDocente.status = False
                eRubricaSeleccionDocente.save(request)
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delete_item_rubrica_baremo':
            try:
                eDetalleItemRubricaSeleccionDocente = DetalleItemRubricaSeleccionDocente.objects.get(pk=int(request.POST['id']))
                log(u'Elimino item rubrica baremo: %s' % eDetalleItemRubricaSeleccionDocente, request, "del")
                eDetalleItemRubricaSeleccionDocente.status = False
                eDetalleItemRubricaSeleccionDocente.save(request)
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delete_subitem_rubrica_baremo':
            try:
                eDetalleSubItemRubricaSeleccionDocente = DetalleSubItemRubricaSeleccionDocente.objects.get(pk=int(request.POST['id']))
                log(u'Elimino sub item rubrica baremo: %s' % eDetalleSubItemRubricaSeleccionDocente, request, "del")
                eDetalleSubItemRubricaSeleccionDocente.status = False
                eDetalleSubItemRubricaSeleccionDocente.save(request)
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'editactaseleccion':
            try:
                f = ActaSeleccionDocenteForm(request.POST)
                acta = ActaSeleccionDocente.objects.get(pk=request.POST.get('id'))
                if f.is_valid():
                    acta.comite=f.cleaned_data.get('comite')
                    acta.lugar=f.cleaned_data.get('lugar')
                    acta.observacion_ep = f.cleaned_data.get('observacion_ep')
                    acta.tipo_formato_acta = f.cleaned_data.get('tipo_formato_acta')
                    acta.save(request)
                    acta.comite.asignar_permiso_al_modulo(request)
                    acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                       actaparalelo=None,
                                                                       persona=persona,
                                                                       observacion=f"Actualizó acta de selección docente",
                                                                       archivo=None)
                    log(u"Editó acta de selección", request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'delactaseleccion':
            try:
                acta = ActaSeleccionDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                acta.status = False
                acta.save(request)
                log(u"Eliminó acta", request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()

        elif action == 'eliminar_detalleinformecontratacion':
            try:
                eDetalleInformeContratacion = DetalleInformeContratacion.objects.get(pk=int(request.POST['id']))
                eDetalleInformeContratacion.eliminar_personal_contratar_en_detalle_informe_contratacion_and_cambiar_estado_a_pendiente(request)
                eDetalleInformeContratacion.informecontratacion.generar_actualizar_informe_memo_contratacion_pdf_segundo_plano(request)
                log(f"Eliminó del informe de contratacion a {eDetalleInformeContratacion.personalcontratar}", request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()

        elif action == 'addtipopersonal':
            try:
                f = TipoPersonalForm(request.POST)
                if f.is_valid():
                    f.save(request)
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'edittipopersonal':
            try:
                model = TipoPersonal.objects.filter(pk=request.POST.get('pk', None)).first()
                f = TipoPersonalForm(request.POST, instance=model)
                if f.is_valid():
                    f.save(request)
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'addhorario':
            try:
                f = HorarioClasesForm(request.POST)
                paralelo = ActaParalelo.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    dia, inicio, fin = f.cleaned_data['dia'], f.cleaned_data['inicio'], f.cleaned_data['fin']

                    if inicio < paralelo.inicio or fin < paralelo.inicio or fin > paralelo.fin or inicio > paralelo.fin:
                        return JsonResponse({"result": False, "mensaje": f"La fecha ingresada no se encuenta en el rango de fechas inicio/fin del módulo."})

                    if not HorarioClases.objects.filter(dia=dia, actaparalelo=paralelo, inicio=inicio, fin=fin, status=True).exists():
                        horario = HorarioClases(dia=dia, actaparalelo=paralelo, inicio=inicio, fin=fin)
                        horario.save(request)
                        horario.turno.clear()
                        horario.turno.set(f.cleaned_data.get('turno'))
                        log(u"Agregó horario a acta", request, 'add')
                        paralelo.acta.actualizar_documeto_pdf_acta(request)
                        paralelo.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                    actaparalelo=paralelo,
                                                                    persona=persona,
                                                                    observacion=f"Agregó horario al paralelo {paralelo} en la fecha inicio: {inicio}, fecha fin : {fin} ",
                                                                    archivo=None)
                        return JsonResponse({"result": True})
                    else:
                        return JsonResponse({"result": False, "mensaje": f"Ya existe un horario registrado en este dia y fecha."})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'addhorarioconvocatoria':
            try:
                f = HorarioClasesForm(request.POST)
                eConvocatoria = Convocatoria.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    dia, inicio, fin = f.cleaned_data['dia'], f.cleaned_data['inicio'], f.cleaned_data['fin']

                    if inicio < eConvocatoria.iniciohorario or fin < eConvocatoria.iniciohorario or fin > eConvocatoria.finhorario or inicio > eConvocatoria.finhorario:
                        return JsonResponse({"result": False, "mensaje": f"La fecha ingresada no se encuenta en el rango de fechas inicio/fin del módulo."})

                    if not HorarioPlanificacionConvocatoria.objects.filter(dia=dia, convocatoria=eConvocatoria, inicio=inicio, fin=fin, status=True).exists():
                        horario = HorarioPlanificacionConvocatoria(dia=dia, convocatoria=eConvocatoria, inicio=inicio, fin=fin)
                        horario.save(request)
                        horario.turno.clear()
                        horario.turno.set(f.cleaned_data.get('turno'))
                        log(u"Agregó horario a acta", request, 'add')
                        return JsonResponse({"result": True})
                    else:
                        return JsonResponse({"result": False, "mensaje": f"Ya existe un horario registrado en este dia y fecha."})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'edithorario':
            try:
                f = HorarioClasesForm(request.POST)
                horario = HorarioClases.objects.get(pk=request.POST.get('id'))

                if f.is_valid():
                    inicio, fin, dia, turno = f.cleaned_data['inicio'], f.cleaned_data['fin'], f.cleaned_data['dia'], f.cleaned_data['turno']
                    if not HorarioClases.objects.filter(dia=dia, actaparalelo=horario.actaparalelo, inicio=inicio, fin=fin, status=True).exclude(turno__id__in=f.cleaned_data['turno'].values_list('id', flat=True)).exists():
                        turnos_en_base = HorarioClases.objects.values_list('id', flat=True).filter(dia=dia, actaparalelo=horario.actaparalelo, inicio=inicio, fin=fin, status=True)
                        if not list(turno.values_list('id', flat=True)) == list(turnos_en_base):
                            horario.dia, horario.inicio, horario.fin = dia, inicio, fin
                            horario.save(request)
                            horario.turno.clear()
                            horario.turno.set(turno)
                            log(u"Editó horario a acta ", request, 'edit')
                            horario.actaparalelo.acta.actualizar_documeto_pdf_acta(request)
                            horario.actaparalelo.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                                   actaparalelo=horario.actaparalelo,
                                                                                   persona=persona,
                                                                                   observacion=f"Actualizó horario al paralelo {horario.actaparalelo.paralelo} en la fecha inicio: {inicio}, fecha fin : {fin} ",
                                                                                   archivo=None)
                            return JsonResponse({"result": True})
                        else:
                            return JsonResponse({"result": False, "mensaje": f"Los turnos que intenta registrar ya se encuentran ingresados en el sistema."})
                    else:
                        return JsonResponse({"result": False, "mensaje": f"Ya existe un horario registrado en este dia y fecha."})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'edithorarioconvocatoria':
            try:
                f = HorarioClasesForm(request.POST)
                horario = HorarioPlanificacionConvocatoria.objects.get(pk=request.POST.get('id'))

                if f.is_valid():
                    inicio, fin, dia, turno = f.cleaned_data['inicio'], f.cleaned_data['fin'], f.cleaned_data['dia'], f.cleaned_data['turno']
                    if not HorarioPlanificacionConvocatoria.objects.filter(dia=dia, convocatoria=horario.convocatoria, inicio=inicio, fin=fin, status=True).exclude(turno__id__in=f.cleaned_data['turno'].values_list('id', flat=True)).exists():
                        turnos_en_base = HorarioPlanificacionConvocatoria.objects.values_list('id', flat=True).filter(dia=dia, convocatoria=horario.convocatoria, inicio=inicio, fin=fin, status=True)
                        if not list(turno.values_list('id', flat=True)) == list(turnos_en_base):
                            horario.dia, horario.inicio, horario.fin = dia, inicio, fin
                            horario.save(request)
                            horario.turno.clear()
                            horario.turno.set(turno)
                            log(u"Editó horario a acta ", request, 'edit')
                            return JsonResponse({"result": True})
                        else:
                            return JsonResponse({"result": False, "mensaje": f"Los turnos que intenta registrar ya se encuentran ingresados en el sistema."})
                    else:
                        return JsonResponse({"result": False, "mensaje": f"Ya existe un horario registrado en este dia y fecha."})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'delhorario':
            try:
                eHorarioClases = HorarioClases.objects.filter(pk=encrypt(request.POST['id']))
                eHorarioClases.update(status=False)
                eHorarioClases.first().actaparalelo.acta.actualizar_documeto_pdf_acta(request)
                eHorarioClases.first().actaparalelo.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                                   actaparalelo=eHorarioClases.first().actaparalelo,
                                                                                   persona=persona,
                                                                                   observacion=f"Eliminó horario al paralelo {eHorarioClases.first().actaparalelo}.",
                                                                                   archivo=None)
                log(u"Eliminó horario de clase para acta de selección", request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'borrar_todo_el_horario_paralelo':
            try:
                eActaParalelo = ActaParalelo.objects.get(pk=int(request.POST['id']))
                eActaParalelo.get_horario().update(status=False)
                log(u"Eliminó horario de clase para acta de selección", request, 'del')
                eActaParalelo.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                            actaparalelo=eActaParalelo,
                                                                            persona=persona,
                                                                            observacion=f"Eliminó horario al paralelo {eActaParalelo}.",
                                                                            archivo=None)
                eActaParalelo.acta.actualizar_documeto_pdf_acta(request)

                return JsonResponse({"result": True, "error": False,'pk':eActaParalelo.pk,'pkcv':eActaParalelo.convocatoria.pk})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'delhorarioconvocatoria':
            try:
                HorarioPlanificacionConvocatoria.objects.filter(pk=encrypt(request.POST['id'])).update(status=False)
                log(u"Eliminó horario de clase para convocatoria", request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'addparalelo':
            try:
                acta = ActaSeleccionDocente.objects.get(pk=request.POST.get('id'))
                f = ActaParaleloForm(request.POST)
                if f.is_valid():
                    f.fechacreacionacta = acta.fecha_creacion
                    paralelo, inicio, fin, convocatoria = f.cleaned_data.get('paralelo'), f.cleaned_data.get('inicio'), f.cleaned_data.get('fin'), f.cleaned_data.get('convocatoria')

                    if not ActaParalelo.objects.filter(acta_id=acta, paralelo=paralelo, inicio=inicio, fin=fin, convocatoria=convocatoria, status=True).values('id').exists():
                        if  convocatoria.postulantes_revisados_todos():
                            if convocatoria.paralelos >= ActaParalelo.objects.filter(acta_id=acta, convocatoria=convocatoria, status=True).count() + 1 or not convocatoria.paralelos:
                                paralelo = ActaParalelo(acta=acta, paralelo=paralelo, inicio=inicio, fin=fin, convocatoria=convocatoria)
                                paralelo.save(request)
                                log(u"Agregó paralelo", request, 'add')
                                paralelo.clonar_horario_de_la_convocatoria_en_el_acta(request)
                                paralelo.acta.actualizar_documeto_pdf_acta(request)
                                paralelo.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                                               actaparalelo=paralelo,
                                                                                               persona=persona,
                                                                                               observacion=f"Se adicionó un nuevo paralelo:{paralelo}",
                                                                                               archivo=None)

                                return JsonResponse({"result": True})
                            else:
                                return JsonResponse({"result": False, "mensaje": f"Excedió el número de paralelos en la asignatura %s" % convocatoria.asignaturamalla.asignatura})
                        else:
                            return JsonResponse({"result": False, "mensaje": f"No se ha realizado la revisión de todos los postulantes en la convocatoria %s" % convocatoria})

                    else:
                        return JsonResponse({"result": False, "mensaje": f"El paralelo %s ya se encuentra registrado en esta asignatura" % paralelo})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'realizar_votacion_comite':
            try:
                eActaParalelo = ActaParalelo.objects.get(pk=int(request.POST.get('id_acta_paralelo')))
                miembrocomite = eActaParalelo.acta.comite.get_integrantes().filter(persona=persona, status=True).first()
                f = VotacionComiteForm(request.POST)
                if f.is_valid():
                    eVotacionComiteAcademico = VotacionComiteAcademico.objects.filter(status=True ,miembrocomite=miembrocomite,actaparalelo =eActaParalelo )
                    PRINCIPAL=1
                    ALTERNO_1=2
                    ALTERNO_2=3
                    if eVotacionComiteAcademico.filter(tipo_id=PRINCIPAL).count() >= 1 and  f.cleaned_data['tipoPersonal'].id == PRINCIPAL:
                        return JsonResponse({"result": False, "mensaje": f"Ya existe un principal seleccionado"})

                    if eVotacionComiteAcademico.filter(tipo_id=ALTERNO_1).count() >= 1 and  f.cleaned_data['tipoPersonal'].id == ALTERNO_1:
                        return JsonResponse({"result": False, "mensaje": f"Ya existe un alterno 1 seleccionado"})

                    if eVotacionComiteAcademico.filter(tipo_id=ALTERNO_2).count() >= 1 and  f.cleaned_data['tipoPersonal'].id == ALTERNO_2:
                        return JsonResponse({"result": False, "mensaje": f"Ya existe un alterno 2 seleccionado"})

                    if not eVotacionComiteAcademico.filter(inscripcion=f.cleaned_data['inscrito']).exists():
                        eVotacionComiteAcademico= VotacionComiteAcademico(
                            miembrocomite = miembrocomite,
                            inscripcion = f.cleaned_data['inscrito'],
                            tipo = f.cleaned_data['tipoPersonal'],
                            actaparalelo=  eActaParalelo
                        )
                        eVotacionComiteAcademico.save(request)
                        log(f"realizo voto {eVotacionComiteAcademico}", request, 'add')
                        eActaParalelo.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                                    actaparalelo=eActaParalelo,
                                                                                    persona=persona,
                                                                                    observacion=f"Realizó voto: por {eVotacionComiteAcademico} - {miembrocomite.cargo}",
                                                                                    archivo=None)

                    else:
                        instancia  = eVotacionComiteAcademico.filter(inscripcion=f.cleaned_data['inscrito']).first()
                        instancia.tipo = f.cleaned_data['tipoPersonal']
                        instancia.save(request)
                        log(f"{eVotacionComiteAcademico} update", request, 'change')
                        eActaParalelo.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                            actaparalelo=eActaParalelo,
                                                            persona=persona,
                                                            observacion=f"Actualizó voto por: {eVotacionComiteAcademico}",
                                                            archivo=None)
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'guardado_principales_alternos_automatico':
            try:
                eActaParalelo = ActaParalelo.objects.get(pk=int(request.POST.get('id_acta_paralelo')))
                # eActaParalelo.guardar_segun_validacion_principal_alternos(request)
                if eActaParalelo.acta.todos_los_miembros_del_comite_votaron_por_todos_los_banco_de_elegibles():
                    eActaParalelo.acta.ejecutar_en_segundo_plano_guardado_principal_alternos(request)


                return JsonResponse({"result": True})


            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'realizar_baremo_comite':
            try:
                eInscripcionConvocatoria = InscripcionConvocatoria.objects.get(pk=int(request.POST.get('eInscripcionConvocatoriaPk')))
                eDetalleSubItemRubricaSeleccionDocente = DetalleSubItemRubricaSeleccionDocente.objects.get(pk=int(request.POST.get('eDetalleSubItemRubricaSeleccionDocentePk')))
                eActaParalelo = ActaParalelo.objects.get(pk=int(request.POST.get('id_acta_paralelo')))
                miembrocomite = eActaParalelo.acta.comite.get_integrantes().filter(persona=persona, status=True).first()
                votacioncomiteacademico = miembrocomite.get_generar_registro_baremo_miembro_comite(request,eActaParalelo,eInscripcionConvocatoria)
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,votacioncomiteacademico=votacioncomiteacademico)
                if not eBaremoComiteAcademico.filter(detallesubitemrubricaselecciondocente__detalleitemrubricaselecciondocente =eDetalleSubItemRubricaSeleccionDocente.detalleitemrubricaselecciondocente).exists():
                    eBaremoComiteAcademico = BaremoComiteAcademico(
                        votacioncomiteacademico=votacioncomiteacademico,
                        detallesubitemrubricaselecciondocente=eDetalleSubItemRubricaSeleccionDocente,
                        puntaje=eDetalleSubItemRubricaSeleccionDocente.puntaje
                    )
                    eBaremoComiteAcademico.save(request)
                    log(f"realizo calificacion baremo {eBaremoComiteAcademico}", request, 'add')
                else:
                    if eBaremoComiteAcademico.count() == 1:
                        eActaParalelo.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                                    actaparalelo=eActaParalelo,
                                                                                    persona=persona,
                                                                                    observacion=f"Eliminó el voto: {votacioncomiteacademico} - {miembrocomite.cargo}",
                                                                                    archivo=None)
                        votacioncomiteacademico.status = False
                        votacioncomiteacademico.save(request)


                    eBaremoComiteAcademico.filter(detallesubitemrubricaselecciondocente__detalleitemrubricaselecciondocente =eDetalleSubItemRubricaSeleccionDocente.detalleitemrubricaselecciondocente).update(status=False)

                    # eBaremoComiteAcademico = BaremoComiteAcademico(
                    #     votacioncomiteacademico=votacioncomiteacademico,
                    #     detallesubitemrubricaselecciondocente=eDetalleSubItemRubricaSeleccionDocente,
                    #     puntaje=eDetalleSubItemRubricaSeleccionDocente.puntaje
                    # )
                    # eBaremoComiteAcademico.save(request)
                    # log(f"{eBaremoComiteAcademico} update", request, 'change')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'addconvocatoriaperfil':
            try:
                acta = ActaSeleccionDocente.objects.get(pk=request.POST.get('id'))
                f = ActaParaleloForm(request.POST)
                f.set_required_field('paralelo', False)
                if f.is_valid():
                    f.fechacreacionacta = acta.fecha_creacion
                    inicio, fin, convocatoria =  f.cleaned_data.get('inicio'), f.cleaned_data.get('fin'), f.cleaned_data.get('convocatoria')

                    if not ActaParalelo.objects.filter(acta_id=acta, paralelo=None, inicio=inicio, fin=fin, convocatoria=convocatoria, status=True).values('id').exists():
                        paralelo = ActaParalelo(acta=acta, paralelo=None, inicio=inicio, fin=fin, convocatoria=convocatoria)
                        paralelo.save(request)
                        log(u"Agregó convocatoria carrera invitado", request, 'add')
                        return JsonResponse({"result": True})
                    else:
                        return JsonResponse({"result": False, "mensaje": f"La convocatoria %s ya se encuentra registrada: {convocatoria}"})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'editparalelo':
            try:
                f = ActaParaleloForm(request.POST)
                ap = ActaParalelo.objects.filter(pk=request.POST.get('id', None)).first()
                if f.is_valid():
                    paralelo, inicio, fin, convocatoria = f.cleaned_data.get('paralelo'), f.cleaned_data.get('inicio'), f.cleaned_data.get('fin'), f.cleaned_data.get('convocatoria')
                    if not ActaParalelo.objects.filter(paralelo=paralelo, inicio=inicio, fin=fin, convocatoria=convocatoria, status=True).values('id').exists():
                        ap.paralelo, ap.inicio, ap.fin, ap.convocatoria = paralelo, inicio, fin, convocatoria
                        ap.save(request)
                        log(u"Editó paralelo", request, 'edit')
                        ap.acta.actualizar_documeto_pdf_acta(request)
                        ap.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                               actaparalelo=ap,
                                                                               persona=persona,
                                                                               observacion=f"Se actualizó el paralelo",
                                                                               archivo=None)
                        return JsonResponse({"result": True})
                    else:
                        return JsonResponse({"result": False, "mensaje": f"El paralelo %s ya se encuentra registrado en esta asignatura." % paralelo})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'editconvocatoriaperfil':
            try:
                f = ActaParaleloForm(request.POST)
                f.set_required_field('paralelo', False)
                ap = ActaParalelo.objects.filter(pk=request.POST.get('id', None)).first()
                if f.is_valid():
                    inicio, fin, convocatoria =f.cleaned_data.get('inicio'), f.cleaned_data.get('fin'), f.cleaned_data.get('convocatoria')
                    if not ActaParalelo.objects.filter(inicio=inicio, fin=fin, convocatoria=convocatoria, status=True).values('id').exists():
                        ap.inicio, ap.fin, ap.convocatoria =  inicio, fin, convocatoria
                        ap.save(request)
                        log(u"Editó convcatoria perfil invitado paralelo", request, 'edit')
                        return JsonResponse({"result": True})
                    else:
                        return JsonResponse({"result": False, "mensaje": f"La  convocatoria {ap.convocatoria} ya se encuentra registrada"})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'duplicar_horario':
            try:
                eActaParaleloOriginal = ActaParalelo.objects.get(pk=request.POST.get('id', None))
                f = DuplicarHorarioForm(request.POST)
                if f.is_valid():
                    eActaParaleloAsignarHorario =f.cleaned_data.get('paralelo')
                    if not HorarioClases.objects.filter(status=True,actaparalelo= eActaParaleloAsignarHorario).exists():
                        for horario in eActaParaleloOriginal.get_horario():
                            eHorarioClases = HorarioClases(
                                dia=horario.dia,
                                actaparalelo=eActaParaleloAsignarHorario,
                                inicio=horario.inicio,
                                fin=horario.fin,
                            )
                            eHorarioClases.save(request)
                            for turno in horario.turno.all():
                                eHorarioClases.turno.add(turno)
                            log(u"Copia horario paralelo", request, 'add')
                        eActaParaleloAsignarHorario.acta.actualizar_documeto_pdf_acta(request)
                        eActaParaleloOriginal.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                                         actaparalelo=eActaParaleloOriginal,
                                                                                         persona=persona,
                                                                                         observacion=f"Se replico el horario del paralelo {eActaParaleloOriginal}; a todos los paralelos.",
                                                                                         archivo=None)
                        return JsonResponse({"result": False, 'mensaje': 'Registro Exitoso'})
                    else:
                        return JsonResponse({"result": False, 'mensaje': 'El horario ya fue duplicado'})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': "bad", "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'delparalelo':
            try:
                eActaParalelo = ActaParalelo.objects.filter(pk=int(encrypt(request.POST['id'])))
                eActaParalelo.update(status=False)
                eActaParalelo.first().acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                 actaparalelo=eActaParalelo,
                                                                 persona=persona,
                                                                 observacion=f"Se eliminó el paralelo",
                                                                 archivo=None)
                log(u"Eliminó paralelo", request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'eliminar_voto_comite':
            try:
                pk = int(request.POST.get('id','0'))
                eInscripcionConvocatoria = InscripcionConvocatoria.objects.get(pk=pk)
                eActaParalelo = ActaParalelo.objects.get(pk=int(request.POST.get('id_acta_paralelo')))
                miembrocomite = eActaParalelo.acta.comite.get_integrantes().filter(persona=persona, status=True).first()
                evoto = eInscripcionConvocatoria.get_voto_miembro_comite(miembrocomite)
                if evoto:
                    evoto.status=False
                    evoto.save(request)
                    log(u"Eliminó voto comite academico posgrado", request, 'del')
                    votacioncomiteacademico = miembrocomite.get_votos_realizados(eActaParalelo).filter(inscripcion=eInscripcionConvocatoria).first() if miembrocomite.get_votos_realizados(eActaParalelo).filter(inscripcion=eInscripcionConvocatoria).exists() else None
                    if votacioncomiteacademico:
                        eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,votacioncomiteacademico=votacioncomiteacademico)
                        eBaremoComiteAcademico.filter(votacioncomiteacademico=votacioncomiteacademico).update(status=False)
                    eActaParalelo.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                                actaparalelo=eActaParalelo,
                                                                                persona=persona,
                                                                                observacion=f"Eliminó el voto: {evoto} - {miembrocomite.cargo}",
                                                                                archivo=None)
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'addplanaccion':
            try:
                f = PlanAccionForm(request.POST)
                if f.is_valid():
                    plan = PlanAccion(acta_id=request.POST.get('id', None), integrantecomiteacademico=f.cleaned_data.get('integrantecomiteacademico'), resolucion=f.cleaned_data.get('resolucion'))
                    plan.save(request)
                    log(u"Agregó plan de acción", request, 'add')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'editplanaccion':
            try:
                f = PlanAccionForm(request.POST)
                plan = PlanAccion.objects.filter(pk=request.POST.get('id', None)).first()
                if f.is_valid():
                    plan.integrantecomiteacademico=f.cleaned_data.get('integrantecomiteacademico')
                    plan.resolucion=f.cleaned_data.get('resolucion')
                    plan.save(request)
                    log(u"Editó plan de acción", request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'delplanaccion':
            try:
                plan = PlanAccion.objects.get(pk=int(encrypt(request.POST['id'])))
                plan.status=False
                plan.save(request)
                log(u"Eliminó plan de acción", request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'addtipo':
            try:
                f = TipoPersonalForm(request.POST)
                if f.is_valid():
                    descripcion = f.cleaned_data.get('descripcion').strip().upper()
                    if not TipoPersonal.objects.filter(descripcion=descripcion, status=True).values('id').exists():
                        f.save()
                        log(u"Agregó tipo de personal", request, 'add')
                        return JsonResponse({"result": True})
                    else:
                        return JsonResponse({"result": False, "mensaje": f"El tipo %s ya se encuentra registrado." % descripcion})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'edittipo':
            try:
                model = TipoPersonal.objects.get(pk=int(encrypt(request.POST.get('id'))))
                f = TipoPersonalForm(request.POST, instance=model)
                if f.is_valid():
                    descripcion = f.cleaned_data.get('descripcion')
                    if not TipoPersonal.objects.filter(descripcion=descripcion, status=True).values('id').exists():
                        f.save()
                        log(u"Agregó tipo de personal", request, 'add')
                        return JsonResponse({"result": True})
                    else:
                        return JsonResponse({"result": False, "mensaje": f"El tipo %s ya se encuentra registrado." % descripcion})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'deltipo':
            try:
                TipoPersonal.objects.filter(pk=int(encrypt(request.POST['id']))).update(status=False)
                log(u"Eliminó tipo de personal", request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'addpersonal':
            try:
                f = PersonalAContratarForm(request.POST)
                paralelo = ActaParalelo.objects.get(pk=request.POST.get('id'))

                if f.is_valid():
                    inscripcion, tipo = f.cleaned_data.get('inscripcion'), f.cleaned_data.get('tipo')
                    observacion = f.cleaned_data.get('observacion')
                    tipoinscripcion = 1 if Profesor.objects.values('id').filter(persona=inscripcion.postulante.persona, status=True).exists() else 2
                    if not paralelo.get_horario().exists():
                        return JsonResponse({'result': False, 'mensaje': u'Debe configurar primero el horario.'})
                    # Validacion de choque de horario
                    response = valida_choque_horario_pregrado(request, InscripcionConvocatoria=inscripcion,horarioClases=paralelo.get_horario())

                    if not response.get('result'): return JsonResponse(response)
                    response = valida_choque_horario_en_actas_generadas(request, InscripcionConvocatoria=inscripcion,
                                                                        horarioClases=paralelo.get_horario(),
                                                                        eActaParalelo=paralelo)

                    if not response.get('result'): return JsonResponse(response)

                    if tipo.pk in (2,3):
                        label_tipo = 'ALTERNO 1' if tipo.pk ==2 else'ALTERNO 2'
                        if PersonalAContratar.objects.filter(actaparalelo=paralelo, tipo_id=tipo.pk,status=True).exists():
                            return JsonResponse({'result': False, 'mensaje': f'Exedió el número de postulantes de tipo {label_tipo}.'})

                    if tipo.pk == 1:
                        if PersonalAContratar.objects.filter(actaparalelo=paralelo, tipo_id=1, status=True).exists():
                            return JsonResponse({'result':False, 'mensaje': u'Exedió el número de postulantes de tipo principal.'})

                        cantidadcontratos = PersonalAContratar.objects.values('id').filter(inscripcion=inscripcion, fecha_creacion__year=hoy.year, tipo__id=1, actaparalelo__convocatoria__tipodocente__in=[18, 15], actaparalelo__convocatoria__status=True, actaparalelo__acta__status=True, actaparalelo__status=True, actaparalelo__acta__fecha_legalizacion__isnull=False, status=True).count()
                        if cantidadcontratos > 3:
                            return JsonResponse({'result': False, 'mensaje': u'Exedió el número de contratos por año para docentes de tipo PROFESOR y PROFESOR AUTOR.'})

                        cuerpo = f"""
                            Estimad{'a' if inscripcion.postulante.persona.es_mujer() else 'o'} {f'{inscripcion.postulante.persona.nombres}'.split(' ')[0]}, por medio de la presente se le informa que 
                            usted a sido seleccionado por el comité académico <b>{paralelo.acta.comite.nombre}</b> para impartir clases en el módulo <b>{paralelo.convocatoria.asignaturamalla.asignatura}.</b>
                            Su carta de invitación será enviada al <b>Sistema de Selección Docentes Posgrado</b> dentro de poco.<br><br>
                            Saludos cordiales,
                        """
                        notificacion('Sistema de Selección Docentes Posgrado', cuerpo, inscripcion.postulante.persona,
                                     None, '', inscripcion.pk, 1, 'sga',
                                     PersonalAContratar, request)

                    if not PersonalAContratar.objects.filter(inscripcion=inscripcion, actaparalelo=paralelo, tipo=tipo, status=True).values('id').exists():
                        p = PersonalAContratar(inscripcion=inscripcion, tipo=tipo, actaparalelo=paralelo, tipoinscripcion=tipoinscripcion,observacion=observacion)
                        p.save(request)
                        p.actaparalelo.acta.actualizar_documeto_pdf_acta(request)
                        eHistorialPersonalContratarActaParalelo = HistorialPersonalContratarActaParalelo(
                            persona=persona,
                            fecha=hoy,
                            personalcontratar=p,
                            estado=1
                        )
                        eHistorialPersonalContratarActaParalelo.save(request)
                        log(u"Agregó personal", request, 'add')
                        p.actaparalelo.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                                    actaparalelo=p.actaparalelo,
                                                                                    persona=persona,
                                                                                    observacion=f"Analista agregó como {p.tipo} a {p.inscripcion}",
                                                                                    archivo=None)
                        return JsonResponse({"result": True})
                    else:
                        return JsonResponse({"result": False, "mensaje": f"El postulante %s ya se encuentra registrado." % inscripcion})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'addpersonalinvitado':
                    try:
                        f = PersonalAContratarForm(request.POST)
                        paralelo = ActaParalelo.objects.get(pk=request.POST.get('id'))

                        if f.is_valid():
                            inscripcion, tipo = f.cleaned_data.get('inscripcion'), f.cleaned_data.get('tipo')
                            observacion = f.cleaned_data.get('observacion')
                            tipoinscripcion = 1 if Profesor.objects.values('id').filter(persona=inscripcion.postulante.persona, status=True).exists() else 2
                            # if not paralelo.get_horario().exists():
                            #     return JsonResponse({'result': False, 'mensaje': u'Debe configurar primero el horario.'})
                            # Validacion de choque de horario
                            # response = valida_choque_horario_pregrado(request, InscripcionConvocatoria=inscripcion,horarioClases=paralelo.get_horario())

                            # if not response.get('result'): return JsonResponse(response)
                            # response = valida_choque_horario_en_actas_generadas(request, InscripcionConvocatoria=inscripcion,
                            #                                                     horarioClases=paralelo.get_horario(),
                            #                                                     eActaParalelo=paralelo)

                            # if not response.get('result'): return JsonResponse(response)

                            if tipo.pk in (2,3):
                                label_tipo = 'ALTERNO 1' if tipo.pk ==2 else'ALTERNO 2'
                                if PersonalAContratar.objects.filter(actaparalelo=paralelo, tipo_id=tipo.pk,status=True).exists():
                                    return JsonResponse({'result': False, 'mensaje': f'Exedió el número de postulantes de tipo {label_tipo}.'})

                            if tipo.pk == 1:
                                if PersonalAContratar.objects.filter(actaparalelo=paralelo, tipo_id=1, status=True).exists():
                                    return JsonResponse({'result':False, 'mensaje': u'Exedió el número de postulantes de tipo principal.'})

                                cantidadcontratos = PersonalAContratar.objects.values('id').filter(inscripcion=inscripcion, fecha_creacion__year=hoy.year, tipo__id=1, actaparalelo__convocatoria__tipodocente__in=[18, 15], actaparalelo__convocatoria__status=True, actaparalelo__acta__status=True, actaparalelo__status=True, actaparalelo__acta__fecha_legalizacion__isnull=False, status=True).count()
                                if cantidadcontratos > 3:
                                    return JsonResponse({'result': False, 'mensaje': u'Exedió el número de contratos por año para docentes de tipo PROFESOR y PROFESOR AUTOR.'})

                                # cuerpo = f"""
                                #     Estimad{'a' if inscripcion.postulante.persona.es_mujer() else 'o'} {f'{inscripcion.postulante.persona.nombres}'.split(' ')[0]}, por medio de la presente se le informa que
                                #     usted a sido seleccionado por el comité académico <b>{paralelo.acta.comite.nombre}</b> para impartir clases en el módulo <b>{paralelo.convocatoria.asignaturamalla.asignatura}.</b>
                                #     Su carta de invitación será enviada al <b>Sistema de Selección Docentes Posgrado</b> dentro de poco.<br><br>
                                #     Saludos cordiales,
                                # """
                                # notificacion('Sistema de Selección Docentes Posgrado', cuerpo, inscripcion.postulante.persona,
                                #              None, '', inscripcion.pk, 1, 'sga',
                                #              PersonalAContratar, request)

                            if not PersonalAContratar.objects.filter(inscripcion=inscripcion, actaparalelo=paralelo, tipo=tipo, status=True).values('id').exists():
                                p = PersonalAContratar(inscripcion=inscripcion, tipo=tipo, actaparalelo=paralelo, tipoinscripcion=tipoinscripcion,observacion=observacion)
                                p.save(request)
                                eHistorialPersonalContratarActaParalelo = HistorialPersonalContratarActaParalelo(
                                    persona=persona,
                                    fecha=hoy,
                                    personalcontratar=p,
                                    estado=1
                                )
                                eHistorialPersonalContratarActaParalelo.save(request)
                                log(u"Agregó personal", request, 'add')
                                return JsonResponse({"result": True})
                            else:
                                return JsonResponse({"result": False, "mensaje": f"El postulante %s ya se encuentra registrado." % inscripcion})
                        else:
                            return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
                    except Exception as ex:
                        transaction.rollback()
                        return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'editpersonal':
            try:
                model = PersonalAContratar.objects.get(pk=request.POST.get('id', None))
                f = PersonalAContratarForm(request.POST, instance=model)
                if f.is_valid():
                    inscripcion, tipo = f.cleaned_data.get('inscripcion'), f.cleaned_data.get('tipo')
                    if tipo.pk == 2 or (tipo.pk == 1 and not model.actaparalelo.get_personal_principal().values('id').exclude(inscripcion=inscripcion).exists()):
                        model.inscripcion, model.tipo = inscripcion, tipo
                        model.save(request)
                        eHistorialPersonalContratarActaParalelo = HistorialPersonalContratarActaParalelo(
                            persona=persona,
                            fecha=hoy,
                            personalcontratar=model,
                            estado=2
                        )
                        eHistorialPersonalContratarActaParalelo.save(request)
                        log(u"Editó personal", request, 'edit')
                        model.actaparalelo.acta.actualizar_documeto_pdf_acta(request)
                        model.actaparalelo.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                             actaparalelo=model.actaparalelo,
                                                             persona=persona,
                                                             observacion=f"Analista actualizó personal a contratar como {model.tipo} a {model.inscripcion}",
                                                             archivo=None)
                        return JsonResponse({"result": True})
                    else:
                        return JsonResponse({"result": False, "mensaje": f"El postulante ya se encuentra registrado."})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'asignar_observacion':
            try:
                model = PersonalAContratar.objects.get(pk=request.POST.get('id', None))
                f = PersonalAContratarForm(request.POST)
                if f.is_valid():
                    model.observacion =  f.cleaned_data.get('observacion')
                    model.save(request)
                    log(u"Editó personal", request, 'edit')
                    model.actaparalelo.acta.actualizar_documeto_pdf_acta(request)
                    model.actaparalelo.acta.guardar_recorrido_acta_seleccion_docente(request,actaparalelo=model.actaparalelo,
                                                                                                           persona=persona,
                                                                                                           observacion=f"Ingresó observación al personal a contratar: {model}; observación: {model.observacion}",
                                                                                                           archivo=None)
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'delpersonal':
            try:
                ePersonalAContratar= PersonalAContratar.objects.filter(pk=int(encrypt(request.POST['id'])))
                ePersonalAContratar.update(status=False)
                eHistorialPersonalContratarActaParalelo = HistorialPersonalContratarActaParalelo(
                    persona=persona,
                    fecha=hoy,
                    personalcontratar=ePersonalAContratar.first(),
                    estado=3
                )
                eHistorialPersonalContratarActaParalelo.save(request)
                ePersonalAContratar.first().actaparalelo.acta.actualizar_documeto_pdf_acta(request)
                ePersonalAContratar.first().actaparalelo.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                                 actaparalelo=ePersonalAContratar.first().actaparalelo,
                                                                                 persona=persona,
                                                                                 observacion=f"Eliminó personal a contratar como {ePersonalAContratar.first().tipo} a {ePersonalAContratar.first().inscripcion}",
                                                                                 archivo=None)
                log(u"Eliminó personal", request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'delpersonalcomite':
            try:
                ePersonalAContratar= PersonalAContratar.objects.filter(pk=int(encrypt(request.POST['id'])))
                ePersonalAContratar.update(status=False)
                eHistorialPersonalContratarActaParalelo = HistorialPersonalContratarActaParalelo(
                    persona=persona,
                    fecha=hoy,
                    personalcontratar=ePersonalAContratar.first(),
                    estado=3
                )
                eHistorialPersonalContratarActaParalelo.save(request)

                eInscripcionConvocatoria = ePersonalAContratar.first().inscripcion
                eActaParalelo = ePersonalAContratar.first().actaparalelo
                miembrocomite = eActaParalelo.acta.comite.get_integrantes().filter(persona=persona, status=True).first()
                evoto = eInscripcionConvocatoria.get_voto_miembro_comite(miembrocomite)
                # if evoto:
                #     evoto.status = False
                #     evoto.save(request)
                #     log(u"Eliminó voto comite academico posgrado", request, 'del')
                log(u"Eliminó personal", request, 'del')
                ePersonalAContratar.first().volver_a_estado_revision_para_comite(request)
                eActaParalelo.acta.actualizar_documeto_pdf_acta(request)
                eActaParalelo.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                                   actaparalelo=eActaParalelo,
                                                                                   persona=persona,
                                                                                   observacion=f"Eliminó personal: { ePersonalAContratar.first()} como: {ePersonalAContratar.first().tipo}",
                                                                                   archivo=None)

                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud Incorrecta. {ex.__str__()}"})

        elif action == 'legalizaracta':
            try:
                persona = request.session.get('persona')
                acta = ActaSeleccionDocente.objects.get(pk=request.POST.get('id'))
                integrante = acta.comite.get_integrantes().filter(persona=persona, status=True).first()
                validar_acta_legalizada(acta)
                if not HistorialActaSeleccionDocente.objects.filter(acta=acta, firmadopor=integrante, status=True).values('id').exists():
                    pdf = acta.archivo

                    pdfname = SITE_STORAGE + acta.archivo.url
                    palabras = u"%s" % persona
                    documento = fitz.open(pdfname)
                    numpaginafirma = int(documento.page_count)-1
                    with fitz.open(pdfname) as document:
                        words_dict = {}
                        for page_number, page in enumerate(document):
                            if page_number == numpaginafirma:
                                words = page.get_text("blocks")
                                words_dict[0] = words
                    valor = None
                    for cadena in words_dict[0]:
                        if palabras in cadena[4]:
                            valor = cadena

                    if valor:
                        y = 5000 - int(valor[3]) - 4140
                    else:
                        return JsonResponse({"result": False, 'mensaje':u"El nombre en la firma no es el correcto."})

                    firma = request.FILES.get("firma")
                    passfirma = request.POST.get('palabraclave')
                    txtFirmas = json.loads(request.POST['txtFirmas'])
                    if not txtFirmas:
                        return JsonResponse({"result": "bad", "mensaje": u"No se ha podido seleccionar la ubicación de la firma"})

                    generar_archivo_firmado = io.BytesIO()
                    x = txtFirmas[-1]

                    try:
                        if variable_valor("BOOL_FIRMA_NUEVA"):
                            bytes_certificado = firma.read()
                            extension_certificado = os.path.splitext(firma.name)[1][1:]
                            x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras)
                            datau = JavaFirmaEc(
                                archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                                extension_certificado=extension_certificado,
                                password_certificado=passfirma,
                                page=int(numpaginafirma), reason='', lx=x + 300, ly=y + 5
                            ).sign_and_get_content_bytes()

                            documento_a_firmar = io.BytesIO()
                            documento_a_firmar.write(datau)
                            documento_a_firmar.seek(0)
                            acta.archivo.save(f'{acta.archivo.name.split("/")[-1].replace(".pdf", "")}_firmado.pdf', ContentFile(documento_a_firmar.read()))
                            nombrefile_ = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(pdf.name)).replace('-','_').replace('.pdf', '')
                        else:
                            datau, datas = firmar(request, passfirma, firma, pdf, numpaginafirma, x["x"], y, x["width"], x["height"])
                            generar_archivo_firmado.write(datau)
                            generar_archivo_firmado.write(datas)
                            generar_archivo_firmado.seek(0)
                            extension = pdf.name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            nombrefile_ = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(pdf.name)).replace('-','_').replace('.pdf', '')
                            _name = generar_nombre(f"{acta.codigo.__str__()}._{acta.comite.nombre.__str__()}_", '')
                            _name = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(_name)).lower().replace(' ', '_').replace('-', '_')
                            file_obj = DjangoFile(generar_archivo_firmado, name=f"{_name}_firmado.pdf")
                            acta.archivo = file_obj
                    except Exception as ex:
                        messages.warning(request, f'Documento con inconsistencia en la firma.')
                        return JsonResponse({"result": False})

                    if not datau:
                        return JsonResponse({"result": "bad", "mensaje": f"{datas}"})


                    historial = HistorialActaSeleccionDocente(acta=acta, firmadopor=integrante, fecha_legalizacion=hoy, observacion=u"El actá fue firmada exitosamente",archivo= acta.archivo )
                    historial.save(request)

                    if acta.total_firmas_por_acta() == acta.get_integrante_comite().count():
                        acta.fecha_legalizacion = hoy


                    acta.save(request)

                    acta.notificar_a_la_persona_que_le_toca_firmar(request)

                    experta = Persona.objects.get(pk=variable_valor('ID_EXPERTO_GESTION_POSGRADO'))
                    cuerpo = f'Documento {acta} firmado con éxito por <b>{persona}</b>'
                    # notificacion('Firma de Acta de Comité Académico de las Escuelas de Posgrado', cuerpo, experta, None, f'/adm_postulacion?action=listadoactas&pk={acta.pk}', acta.pk, 1, 'sga', ActaSeleccionDocente, request)
                    acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                  actaparalelo=None,
                                                                  persona=persona,
                                                                  observacion=f"Documento PDF firmado por miembro del comité: {integrante.cargo}",
                                                                  archivo=None)
                    messages.success(request, f'Documento firmado con éxito')
                    if acta.firmada_por_todos():
                        acta.estado = 4
                        acta.cerrada = True
                        acta.save(request)
                        # acta.guardar_alternos_como_banco_elegibles()
                        eActaParalelo = ActaParalelo.objects.filter(status=True, acta=acta)
                        if eActaParalelo.exists():
                            carrera = eActaParalelo.first().convocatoria.carrera
                            periodo = eActaParalelo.first().convocatoria.periodo
                            ePersonalApoyoMaestrias = PersonalApoyoMaestria.objects.filter(status=True, carrera=carrera, periodo=periodo)

                        acta.notificar_acta_firmada_por_todos(request,ePersonalApoyoMaestrias)
                        acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                      actaparalelo=None,
                                                                      persona=persona,
                                                                      observacion=f"Documento PDF firmado por todos.",
                                                                      archivo=None)
                    log(u'Firmo Documento: {}'.format(nombrefile_), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": False, 'mensaje': u'Su firma ya se encuentra registrada.'})

                log(u"Legalizó acta de selección", request, 'edit')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex})

        elif action == 'firmar_por_token':
            try:
                persona = request.session.get('persona')
                acta = ActaSeleccionDocente.objects.get(pk=request.POST.get('id'))
                integrante = acta.comite.get_integrantes().filter(persona=persona, status=True).first()

                f = ArchivoInvitacionForm(request.POST, request.FILES)

                if f.is_valid() and request.FILES.get('archivo', None):
                    newfile = request.FILES.get('archivo')
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):].lower()
                            if ext == '.pdf':
                                _name = generar_nombre(f"{acta.codigo.__str__()}._{acta.comite.nombre.__str__()}_", '')
                                _name = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(_name)).lower().replace(' ','_').replace('-', '_')
                                newfile._name = generar_nombre(u"%s_" % _name, f"{_name}.pdf")
                                validar_acta_legalizada(acta)
                                if not HistorialActaSeleccionDocente.objects.filter(acta=acta, firmadopor=integrante, status=True).values('id').exists():
                                    acta.archivo = newfile
                                    acta.save(request)
                                    historial = HistorialActaSeleccionDocente(acta=acta, firmadopor=integrante, fecha_legalizacion=hoy, observacion=f"El actá fue firmada exitosamente: id_acta {acta.id} - {persona.cedula}",archivo= acta.archivo )
                                    historial.save(request)

                                    if acta.total_firmas_por_acta() == acta.get_integrante_comite().count():
                                        acta.fecha_legalizacion = hoy
                                        acta.save(request)

                                    acta.notificar_a_la_persona_que_le_toca_firmar(request)

                                    experta = Persona.objects.get(pk=variable_valor('ID_EXPERTO_GESTION_POSGRADO'))
                                    cuerpo = f'Documento {acta} firmado con éxito por <b>{persona}</b>'
                                    # notificacion('Firma de Acta de Comité Académico de las Escuelas de Posgrado', cuerpo, experta, None,
                                    #              f'/adm_postulacion?action=listadoactas&pk={acta.pk}', acta.pk, 1, 'sga',
                                    #              ActaSeleccionDocente, request)

                                    acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                                  actaparalelo=None,
                                                                                  persona=persona,
                                                                                  observacion=f"Documento PDF firmado por miembro del comité: {integrante.cargo}, manualmente.",
                                                                                  archivo=None)

                                    messages.success(request, f'Documento firmado con éxito')
                                    if acta.firmada_por_todos():
                                        acta.estado = 4
                                        acta.cerrada = True
                                        acta.save(request)
                                        # acta.guardar_alternos_como_banco_elegibles()
                                        eActaParalelo = ActaParalelo.objects.filter(status=True, acta=acta)
                                        if eActaParalelo.exists():
                                            carrera = eActaParalelo.first().convocatoria.carrera
                                            periodo = eActaParalelo.first().convocatoria.periodo
                                            ePersonalApoyoMaestrias = PersonalApoyoMaestria.objects.filter(status=True, carrera=carrera,
                                                                                                           periodo=periodo)

                                        acta.notificar_acta_firmada_por_todos(request, ePersonalApoyoMaestrias)
                                        acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                                      actaparalelo=None,
                                                                                      persona=persona,
                                                                                      observacion=f"Documento PDF firmado por todos, subido manualmente",
                                                                                      archivo=None)
                                    log(u'Firmo Documento: {}'.format(_name), request, "add")
                                    return JsonResponse({"result": "ok"})
                                else:
                                    return JsonResponse({"result": False, 'mensaje': u'Su firma ya se encuentra registrada.'})

                                log(u"Legalizó acta de selección", request, 'edit')
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivos PDF"})

                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, Formulario no valido"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex})

        elif action == 'cerraracta':
            try:
                acta = ActaSeleccionDocente.objects.get(id=request.POST.get('id'))
                acta.cerrada = not acta.cerrada
                acta.save(request)

                if acta.cerrada:
                    for ganador in acta.get_ganador():
                        enviar_carta_invitacion(request, acta=acta, ganador=ganador)

                    listafechas = request.POST.getlist('fecharequisito')
                    for fecha in listafechas:
                        inscripcion, fecharevision = fecha.split(',')
                        InscripcionInvitacion.objects.filter(inscripcion=inscripcion, status=True).update(fecharevisionrequisitos=fecharevision)

                return JsonResponse({'result':True, 'mensaje':u"Se a enviado la carta de invitación a los ganadores"})
            except Exception as ex:
                return JsonResponse({'result':False, 'mensaje':u"Error de conexión. %s" % ex.__str__()})

        elif action == 'evaluarrequisitoscontratacion':
            try:
                inscripcion = InscripcionConvocatoria.objects.get(pk=request.POST['id'])
                acta = ActaSeleccionDocente.objects.get(id=request.POST.get('id_acta'))
                acta.cerrada = True

                for ganador in acta.get_personalacontratar().filter(inscripcion=inscripcion, actaparalelo__acta=acta):
                    if not InscripcionInvitacion.objects.values('id').filter(inscripcion=inscripcion, status=True,actaparalelo=ganador.actaparalelo).exists():
                        jsonresponse = enviar_carta_invitacion(request, acta=acta, ganador=ganador, inscripcionconvocatoria=inscripcion)
                        jsonresponse = json.loads(jsonresponse.content)
                        if not jsonresponse.get('result'): raise NameError(jsonresponse.get('mensaje'))

                    invitacion = InscripcionInvitacion.objects.filter(inscripcion=inscripcion, status=True,actaparalelo=ganador.actaparalelo).first()
                    invitacion.fecharevisionrequisitos = request.POST.get('fecharequisitos')
                    invitacion.save(request)

                    _invitacionespasadas = InscripcionInvitacion.objects.filter(inscripcion__postulante__persona=inscripcion.postulante.persona, status=True)
                    _requisitos = inscripcion.listadorequisitos().values_list('requisito__id', flat=True)
                    _exclude = RequisitosConvocatoria.objects.filter(pk__in=set(json.loads(request.POST['lista_items1'])), status=True).values_list('requisito__id', flat=True)
                    for r in InscripcionConvocatoriaRequisitos.objects.filter(inscripcioninvitacion__in=_invitacionespasadas, requisito__requisito__id__in=_requisitos, status=True).exclude(requisito__requisito__id__in=_exclude):
                        if rc := RequisitosConvocatoria.objects.filter(requisito=r.requisito.requisito, status=True).first():
                            newinstance = InscripcionConvocatoriaRequisitos(inscripcioninvitacion=invitacion,
                                                                            requisito=rc,
                                                                            observacion=r.observacion,
                                                                            archivo=r.archivo,
                                                                            estado=r.estado,
                                                                            fecharevision=hoy,
                                                                            personaaprobador=persona)
                            newinstance.save(request)

                acta.save(request)
                return JsonResponse({'result':'ok'})
            except Exception as ex:
                pass

        elif action == 'editarfechamaximarequisitos':
            try:
                pk= int(request.POST.get('id', '0'))
                if pk == 0:
                    raise NameError("Parametro no encontrado")
                eInscripcionInvitacion = InscripcionInvitacion.objects.get(pk=pk)
                form = CerrarActaForm(request.POST)
                form.del_field('estado')
                if form.is_valid():
                    eInscripcionInvitacion.fecharevisionrequisitos =form.cleaned_data.get('fecharequisitos')
                    eInscripcionInvitacion.save(request)
                    log(f"edito la fecharevisionrequisitos al personal a contratar", request, 'edit')
                    return JsonResponse({'result':False})
                else:
                    return JsonResponse({'result': True, 'mensaje': u"Error en el formulario."})

            except Exception as ex:
                return JsonResponse({'result':True, 'mensaje':u"Error de conexión. %s" % ex.__str__()})

        elif action == 'configurar_requisitos':
            try:
                pk = int(request.POST.get('ePersonalAContratar', '0'))
                if pk == 0 :
                    raise NameError("Parametro no encontrado")
                ePersonalAContratar = PersonalAContratar.objects.get(pk=pk)

                eInscripcionInvitacion = ePersonalAContratar.get_estado_invitacion()
                eConfiguracionRequisitosPersonalContratar = ePersonalAContratar.get_requisitos_configurados_cargar_analista()
                if eConfiguracionRequisitosPersonalContratar:
                    for configuracion in eConfiguracionRequisitosPersonalContratar:
                        requisito = eInscripcionInvitacion.get_requisito_cargado_personal_contratar(configuracion.requisitoconvocatoria) if  eInscripcionInvitacion else None
                        if requisito.archivo == '':
                            raise NameError("Favor subir todos los requisitos que tenga en la secciòn de subir requisito.")
                        if requisito == None or requisito.archivo == '':
                            raise NameError("Favor subir todos los requisitos que tenga en la secciòn de subir requisito.")

                acta = ePersonalAContratar.actaparalelo.acta
                ganador = ePersonalAContratar
                inscripcion = ePersonalAContratar.inscripcion

                if not eInscripcionInvitacion:
                    jsonresponse = crear_invitacion(request, acta=acta, ganador=ganador, inscripcionconvocatoria=inscripcion)
                    jsonresponse = json.loads(jsonresponse.content)
                    if not jsonresponse.get('result'): raise NameError(jsonresponse.get('mensaje'))
                eInscripcionInvitacion = InscripcionInvitacion.objects.filter(inscripcion=inscripcion, status=True, actaparalelo=ganador.actaparalelo).first()

                eInscripcionInvitacion.configuracionrequisitos = True
                eInscripcionInvitacion.fecharevisionrequisitos = request.POST.get('fecharequisitos',None)
                eInscripcionInvitacion.save(request)
                jsonresponse = crear_solo_documento_carta_invitacion(request, acta=acta, ganador=ganador, inscripcionconvocatoria=inscripcion)
                jsonresponse = json.loads(jsonresponse.content)
                return JsonResponse({'result':'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": f"{ex.__str__()}"})

        elif action == 'generar_informe_de_contratacion':
            try:
                id_string = request.POST.get('ids', 0)
                id_list = ast.literal_eval(id_string)
                ePersonalAContratars = PersonalAContratar.objects.filter(status=True, pk__in =id_list )
                eConfiguracionInforme = ConfiguracionInforme.objects.filter(status=True).first()
                eInformeContratacion = InformeContratacion(
                    fechaemision = hoy,
                    para = eConfiguracionInforme.para,
                    de = eConfiguracionInforme.de,
                )
                eInformeContratacion.save(request)

                guardado_correcto ,mensaje = eInformeContratacion.generar_actualizar_carga_automatica_informe_contratacion(ePersonalAContratars,persona,request)
                if not guardado_correcto:
                    raise NameError(mensaje)
                else:

                    return JsonResponse({"result": False, 'mensaje': mensaje})


            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"{ex.__str__()}"})

        elif action == 'actualizar_configuracion_requisitos_personal_contratar':
            try:
                id = int(request.POST.get('id',0))
                estado_id = int(request.POST.get('estado_id'))
                requisitoconvocatoria_id = int(request.POST.get('requisitoconvocatoria_id'))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")

                ePersonalAContratar = PersonalAContratar.objects.get(pk=id)
                eConfiguracionRequisitosPersonalContratar = ePersonalAContratar.actualizar_configuracion_requisitos(request, estado_id,requisitoconvocatoria_id)
                eInscripcionInvitacion = eConfiguracionRequisitosPersonalContratar.personalcontratar.get_estado_invitacion()
                if not eInscripcionInvitacion:
                    acta = ePersonalAContratar.actaparalelo.acta
                    ganador = ePersonalAContratar
                    inscripcion = ePersonalAContratar.inscripcion
                    jsonresponse = crear_invitacion(request, acta=acta, ganador=ganador, inscripcionconvocatoria=inscripcion)
                    jsonresponse = json.loads(jsonresponse.content)
                    if not jsonresponse.get('result'): raise NameError(jsonresponse.get('mensaje'))

                eConfiguracionRequisitosPersonalContratar.carga_automatica_editar_el_archivo_and_fecha_caducidad(request)#cambiar cuando suelte en otro cuadro borra lo que tenga

                log(u'Actualizo configuracion requisito personal contratar: %s' % ePersonalAContratar, request, "edit")
                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        elif action == 'addplanificacionparalelo':
            try:
                f = PlanificacionMateriaPosgradoForm(request.POST)
                if f.is_valid():
                    ePlanificacionParalelo = PlanificacionParalelo.objects.filter(periodo_id=request.POST.get('idp'),
                                                                      carrera_id=request.POST.get('idc'),
                                                                      asignatura_id=request.POST.get('id'), status=True)
                    if not ePlanificacionParalelo.exists():
                        plan = PlanificacionParalelo(
                            carrera_id=request.POST.get('idc'),
                            periodo_id=request.POST.get('idp'),
                            paralelos=f.cleaned_data.get('paralelos'),
                            fechalimiteplanificacion=f.cleaned_data.get('fechalimiteplanificacion'),
                            asignatura_id=request.POST.get('id')
                        )
                        plan.save(request)
                    else:
                        plan= ePlanificacionParalelo.first()
                        plan.paralelos = f.cleaned_data.get('paralelos')
                        plan.fechalimiteplanificacion= f.cleaned_data.get('fechalimiteplanificacion')
                        plan.save(request)

                    return JsonResponse({'result':True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "error": True, "mensaje": f"Intentelo más tarde. {ex.__str__()}"}, safe=False)

        elif action == 'addplanificacionparalelomasivo':
                    try:
                        id_string = request.POST.get('id')
                        id_list = ast.literal_eval(id_string)

                        f = PlanificacionMateriaPosgradoForm(request.POST)
                        if f.is_valid():
                            for id_asignatura  in id_list:
                                ePlanificacionParalelo = PlanificacionParalelo.objects.filter(periodo_id=request.POST.get('idp'),
                                                                                  carrera_id=request.POST.get('idc'),
                                                                                  asignatura_id=id_asignatura, status=True)
                                if not ePlanificacionParalelo.exists():
                                    plan = PlanificacionParalelo(
                                        carrera_id=request.POST.get('idc'),
                                        periodo_id=request.POST.get('idp'),
                                        paralelos=f.cleaned_data.get('paralelos'),
                                        fechalimiteplanificacion=f.cleaned_data.get('fechalimiteplanificacion'),
                                        asignatura_id=id_asignatura
                                    )
                                    plan.save(request)
                                else:
                                    plan= ePlanificacionParalelo.first()
                                    plan.paralelos = f.cleaned_data.get('paralelos')
                                    plan.fechalimiteplanificacion= f.cleaned_data.get('fechalimiteplanificacion')
                                    plan.save(request)

                            return JsonResponse({'result':True})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": False, "error": True, "mensaje": f"Intentelo más tarde. {ex.__str__()}"}, safe=False)

        elif action == 'legalizaractamanual':
            try:
                acta = ActaSeleccionDocente.objects.get(pk=request.POST['id'])
                f = ArchivoInvitacionForm(request.POST, request.FILES)
                validar_acta_legalizada(acta)
                if f.is_valid() and request.FILES.get('archivo', None):
                    newfile = request.FILES.get('archivo')
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):].lower()
                            if ext == '.pdf':
                                name = unicodedata.normalize('NFD', u"%s. %s" % (acta.codigo, acta.comite)).encode('ascii', 'ignore').decode("utf-8").lower().replace(' ', '_').replace('-', '')
                                newfile._name = generar_nombre(u"%s_" % name, f"{name}.pdf")
                                acta.archivo = newfile
                                acta.fecha_legalizacion = hoy
                                acta.cerrada = False
                                acta.save(request)
                                acta.guardar_recorrido_acta_seleccion_docente(request,
                                              actaparalelo=None,
                                              persona=persona,
                                              observacion=f"Documento PDF acta selección docente subido manualmente",
                                              archivo=None)

                                firma_comite = acta.get_firmas()
                                _exclude = HistorialActaSeleccionDocente.objects.filter(acta=acta, firmadopor__in=firma_comite.values_list('id', flat=True), status=True).values_list('firmadopor__id', flat=True)
                                firmado_por = [HistorialActaSeleccionDocente(acta=acta, firmadopor=firma, fecha_legalizacion=hoy, observacion=u"NINGUNA",archivo= acta.archivo ) for firma in firma_comite.exclude(id__in=_exclude)]
                                if firmado_por: HistorialActaSeleccionDocente.objects.bulk_create(firmado_por)

                                # try:
                                #     experta = Persona.objects.get(pk=variable_valor('ID_EXPERTO_GESTION_POSGRADO'))
                                #     cuerpo = f'Documento {acta} firmado con éxito por <b>{", ".join([u"%s" % x.firmadopor for x in firmado_por])}</b>'
                                #     notificacion('Firma de Acta de Comité Académico de las Escuelas de Posgrado', cuerpo, experta, None, f'/adm_postulacion?action=listadoactas&pk={acta.pk}', acta.pk, 1, 'sga', ActaSeleccionDocente, request)
                                # except Exception as ex:
                                #     pass
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extención PDF."})

                    if acta.firmada_por_todos():
                        acta.estado = 4
                        # acta.guardar_alternos_como_banco_elegibles()
                        acta.save(request)
                    log(u"Legalizó acta de selección manual", request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex})

        elif action == 'pdf_horarios':
            data = {}
            data['periodo'] = periodo
            if not periodo.visible:
                return HttpResponseRedirect("/?info=No tiene permiso para imprimir en el periodo seleccionado.")
            data['profesor'] = profesor = Profesor.objects.filter().distinct().get(pk=request.POST['profesor'])
            data['aprobado'] = profesor.claseactividadestado_set.filter(status=True, periodo=periodo, estadosolicitud=2).exists()
            data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'],
                              [6, 'Sabado'], [7, 'Domingo']]
            turnosyclases = profesor.extrae_turnos_y_clases_docente(periodo)
            # turnoclases = Turno.objects.filter(clase__activo=True, clase__materia__nivel__periodo=periodo,
            #                                    clase__materia__profesormateria__profesor=profesor,
            #                                    clase__materia__profesormateria__principal=True).distinct().order_by(
            #     'comienza')
            turnoactividades = Turno.objects.filter(status=True,
                                                    claseactividad__detalledistributivo__distributivo__periodo=periodo,
                                                    claseactividad__detalledistributivo__distributivo__profesor=profesor).distinct(
                'comienza').order_by('comienza')
            data['turnos'] = turnosyclases[1] | turnoactividades
            data['puede_ver_horario'] = request.user.has_perm('sga.puede_visible_periodo') or (periodo.visible and periodo.visiblehorario)
            data['aprobado'] = profesor.claseactividadestado_set.filter(status=True, periodo=periodo, estadosolicitud=2).exists()
            return conviert_html_to_pdf(
                'docentes/horario_pfd.html',
                {
                    'pagesize': 'A4',
                    'data': data,
                }
            )

        elif action == 'editplazosactaseleccion':
            try:
                var = VariablesGlobales.objects.get(variable=request.POST.get('id'))
                f = ConfiguracionPlazosActaSeleccion(request.POST)

                if f.is_valid():
                    var.valor = f.cleaned_data.get('valor')
                    var.save(request)

                    log(f"Editó variable global {var}", request, 'edit')
                    return JsonResponse({'result': True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                pass

        elif action == 'configuracionesgeneralesactaselecciondocente':
            try:
                eConfiguracionGeneralActaSeleccionDocente = ConfiguracionGeneralActaSeleccionDocente.objects.filter(status=True)

                f = ConfiguracionGeneralActaSeleccionDocenteForm(request.POST)

                if f.is_valid():
                    if eConfiguracionGeneralActaSeleccionDocente.exists():
                       eConfiguracionGeneralActaSeleccionDocente = eConfiguracionGeneralActaSeleccionDocente.first()
                       eConfiguracionGeneralActaSeleccionDocente.convocado_por =  f.cleaned_data.get('convocado_por')
                       eConfiguracionGeneralActaSeleccionDocente.cargo_convocado_por =  f.cleaned_data.get('cargo_convocado_por')
                       eConfiguracionGeneralActaSeleccionDocente.organizado_por =  f.cleaned_data.get('organizado_por')
                       eConfiguracionGeneralActaSeleccionDocente.cargo_organizado_por =  f.cleaned_data.get('cargo_organizado_por')
                       eConfiguracionGeneralActaSeleccionDocente.tipo_cargo_convocado_por =  f.cleaned_data.get('tipo_cargo_convocado_por')
                       eConfiguracionGeneralActaSeleccionDocente.tipo_cargo_organizado_por =  f.cleaned_data.get('tipo_cargo_organizado_por')
                    else:
                        eConfiguracionGeneralActaSeleccionDocente = ConfiguracionGeneralActaSeleccionDocente(
                            convocado_por =  f.cleaned_data.get('convocado_por'),
                            cargo_convocado_por = f.cleaned_data.get('cargo_convocado_por'),
                            organizado_por = f.cleaned_data.get('organizado_por'),
                            cargo_organizado_por = f.cleaned_data.get('cargo_organizado_por'),
                            tipo_cargo_convocado_por = f.cleaned_data.get('tipo_cargo_convocado_por'),
                            tipo_cargo_organizado_por = f.cleaned_data.get('tipo_cargo_organizado_por')
                        )
                    eConfiguracionGeneralActaSeleccionDocente.save(request)


                    log(f"Editó variables de configuracion acta selecccion docente {eConfiguracionGeneralActaSeleccionDocente}", request, 'edit')
                    return JsonResponse({'result': True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                pass


        elif action == 'configurar_informe_contratacion_formato':
            try:
                f = ConfiguracionInformeForm(request.POST)
                eConfiguracionInforme = ConfiguracionInforme.objects.filter(status=True)
                if f.is_valid():
                    if not eConfiguracionInforme.exists():
                        eConfiguracionInforme = ConfiguracionInforme(
                            antecedentes = f.cleaned_data.get('antecedentes'),
                            motivacionjuridica = f.cleaned_data.get('motivacionjuridica'),
                            para = f.cleaned_data.get('para'),
                            de = f.cleaned_data.get('de'),
                            recomendaciones = f.cleaned_data.get('recomendaciones'),
                        )
                    else:
                        eConfiguracionInforme = eConfiguracionInforme.first()
                        eConfiguracionInforme.antecedentes = f.cleaned_data.get('antecedentes')
                        eConfiguracionInforme.motivacionjuridica = f.cleaned_data.get('motivacionjuridica')
                        eConfiguracionInforme.para = f.cleaned_data.get('para')
                        eConfiguracionInforme.de = f.cleaned_data.get('de')
                        eConfiguracionInforme.recomendaciones = f.cleaned_data.get('recomendaciones')
                    eConfiguracionInforme.save(request)

                    log(f"Actualizo configuracion informe posgrado {eConfiguracionInforme}", request, 'edit')
                    return JsonResponse({'result': True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                return HttpResponseRedirect("/adm_postulacion?action=listadoinformes&info=%s" % ex.__str__())


        elif action == 'evaluacionpreviacontratacion':
            try:
                ePersonalAContratar = PersonalAContratar.objects.get(id=request.POST.get('id'))
                f = InscripcionConvocatoriaForm(request.POST)
                if f.is_valid():
                    ePersonalAContratar.estado=f.cleaned_data.get('estado')
                    ePersonalAContratar.observacion=f.cleaned_data.get('observacioncon')
                    ePersonalAContratar.save(request)
                    return JsonResponse({'result': True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                pass

        elif action == 'cargar_requisito_personalcontratar':
            try:
                pk = int(request.POST.get('id','0'))
                if pk == 0:
                    raise NameError("Parametro no encontrado")

                eConfiguracionRequisitosPersonalContratar = ConfiguracionRequisitosPersonalContratar.objects.get(pk = pk)
                acta = eConfiguracionRequisitosPersonalContratar.personalcontratar.actaparalelo.acta
                ganador = eConfiguracionRequisitosPersonalContratar.personalcontratar
                inscripcion = eConfiguracionRequisitosPersonalContratar.personalcontratar.inscripcion
                eRequisitosConvocatoria = eConfiguracionRequisitosPersonalContratar.requisitoconvocatoria

                eInscripcionInvitacion = eConfiguracionRequisitosPersonalContratar.personalcontratar.get_estado_invitacion()
                if not eInscripcionInvitacion:
                    jsonresponse = crear_invitacion(request, acta=acta, ganador=ganador, inscripcionconvocatoria=inscripcion)
                    jsonresponse = json.loads(jsonresponse.content)
                    if not jsonresponse.get('result'): raise NameError(jsonresponse.get('mensaje'))

                eInscripcionInvitacion = InscripcionInvitacion.objects.filter(inscripcion=inscripcion, status=True, actaparalelo=ganador.actaparalelo).first()

                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        newfile._name = generar_nombre("requisitoconvocatoria_", newfilesd)

                f = RequisitosPersonalContratarForm(request.POST)
                if f.is_valid():
                    # inscripcioninvitacion = InscripcionInvitacion.objects.get(pk=request.POST['id'])

                    if InscripcionConvocatoriaRequisitos.objects.filter(inscripcioninvitacion=eInscripcionInvitacion, requisito_id=eRequisitosConvocatoria.pk, status=True):
                        icr = InscripcionConvocatoriaRequisitos.objects.filter(inscripcioninvitacion=eInscripcionInvitacion, requisito_id=eRequisitosConvocatoria.pk, status=True).first()
                    else:
                        icr = InscripcionConvocatoriaRequisitos(inscripcioninvitacion=eInscripcionInvitacion, requisito_id=eRequisitosConvocatoria.pk, observacion='Ninguna', estado=1 , fecha_caducidad = f.cleaned_data['fecha_caducidad'])

                    ha = HistorialAprobacion(inscripcionrequisito=icr, observacion='Ninguna', estado=1, tiporevision=1)
                    if newfile:
                        icr.archivo = ha.archivo = newfile
                        icr.fecha_caducidad = f.cleaned_data['fecha_caducidad']

                    icr.save(request)
                    ha.save(request)
                    log(u'Editó analista requisito personal contratar: %s' % icr, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error en el formulario, algunos campos se encuentran vacíos.')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'actualizar_fecha_caducidad_requisito_personalcontratar':
            try:
                pk = int(request.POST.get('id','0'))
                if pk == 0:
                    raise NameError("Parametro no encontrado")

                eConfiguracionRequisitosPersonalContratar = ConfiguracionRequisitosPersonalContratar.objects.get(pk = pk)
                acta = eConfiguracionRequisitosPersonalContratar.personalcontratar.actaparalelo.acta
                ganador = eConfiguracionRequisitosPersonalContratar.personalcontratar
                inscripcion = eConfiguracionRequisitosPersonalContratar.personalcontratar.inscripcion
                eRequisitosConvocatoria = eConfiguracionRequisitosPersonalContratar.requisitoconvocatoria
                eInscripcionInvitacion = eConfiguracionRequisitosPersonalContratar.personalcontratar.get_estado_invitacion()

                f = RequisitosPersonalContratarForm(request.POST)
                if f.is_valid():
                    if eInscripcionInvitacion:
                        if InscripcionConvocatoriaRequisitos.objects.filter(inscripcioninvitacion=eInscripcionInvitacion, requisito_id=eRequisitosConvocatoria.pk, status=True):
                            icr = InscripcionConvocatoriaRequisitos.objects.filter(inscripcioninvitacion=eInscripcionInvitacion, requisito_id=eRequisitosConvocatoria.pk, status=True).first()
                            icr.fecha_caducidad = f.cleaned_data['fecha_caducidad']
                            icr.save(request)
                            log(u'Editó analista requisito personal contratar: %s' % icr, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error en el formulario, algunos campos se encuentran vacíos.')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'validar_requisito_personalcontratar_analista':
            try:
                pk = int(request.POST.get('id','0'))
                if pk == 0:
                    raise NameError("Parametro no encontrado")
                eConfiguracionRequisitosPersonalContratar = ConfiguracionRequisitosPersonalContratar.objects.get(pk=pk)
                icr =eConfiguracionRequisitosPersonalContratar.get_requisito()

                f = ValidarRequisitoPersonalContratarForm(request.POST)
                if f.is_valid():
                    icr.estado =  f.cleaned_data.get('estado')
                    icr.observacion =  f.cleaned_data.get('observacion')
                    icr.fecharevision = datetime.now()
                    icr.save(request)
                    historial = HistorialAprobacion(inscripcionrequisito=icr, estado=icr.estado, tiporevision=1, observacion=icr.observacion)
                    historial.save(request)
                    if icr.estado =='3':
                        eConfiguracionRequisitosPersonalContratar.estado_requisito = 3
                        icr.archivo = None
                        icr.fecha_caducidad = None
                        icr.save(request)
                        eConfiguracionRequisitosPersonalContratar.save(request)
                    log(u'{} : Validación de Requisito Individual Postu - {}'.format(icr.requisito.requisito.nombre, icr.inscripcioninvitacion), request,"edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'actualizar_requisito_revision_final':
            try:
                pk = int(request.POST.get('id','0'))
                if pk == 0:
                    raise NameError("Parametro no encontrado")

                icr = InscripcionConvocatoriaRequisitos.objects.get(pk = pk)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        newfile._name = generar_nombre("requisitoconvocatoria_", newfilesd)

                f = RequisitosPersonalContratarForm(request.POST)
                if f.is_valid():
                    ha = HistorialAprobacion(inscripcionrequisito=icr, observacion='Ninguna', estado=1, tiporevision=1)
                    if newfile:
                        icr.archivo = ha.archivo = newfile
                        icr.fecha_caducidad = f.cleaned_data['fecha_caducidad']

                    icr.save(request)
                    ha.save(request)
                    log(u'Editó analista requisito personal contratar: %s' % icr, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error en el formulario, algunos campos se encuentran vacíos.')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'enviar_acta_para_revision':
            try:
                id = int(request.POST.get('id', '0'))
                REVISION_ACTA = 2
                INICIAR_PROCESO = 3
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")
                eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=id)
                if variable_valor("PASO_REVISION_VICERRECTORADO_ACTA_POSGRADO"):
                    eActaSeleccionDocente.estado = REVISION_ACTA
                    eActaSeleccionDocente.save(request)
                    eActaSeleccionDocente.volver_a_pendientes_paralelos_rechazados(request,persona)
                    eActaSeleccionDocente.notificar_acta_para_revision(request)
                    eActaSeleccionDocente.guardar_recorrido_acta_seleccion_docente(request,
                                                                  actaparalelo=None,
                                                                  persona=persona,
                                                                  observacion=f"Acta selección docente enviada para revisión de vicerrectorado académico de posgrado",
                                                                  archivo=None)
                    log(u"Acta enviada para revision", request, 'edit')
                else:
                    for ePersonalAContratar in eActaSeleccionDocente.get_ganador():
                        ePersonalAContratar.estado = INICIAR_PROCESO
                        ePersonalAContratar.save(request)
                        log(u'Confirmo el inicio de proceso: %s' % ePersonalAContratar, request, "edit")
                    eActaSeleccionDocente.iniciar_proceso_legalizar_acta(request)
                    log(u'Inicio legalizar acta: %s' % eActaSeleccionDocente, request, "edit")
                return JsonResponse({'result': True, 'pk':eActaSeleccionDocente.pk})

            except Exception as ex:
                pass

        elif action == 'calcular_total_valorhora_personal_contratar':
            try:
                id = int(request.POST.get('id', '0'))
                id_valo_x_hora = int(request.POST.get('id_valo_x_hora', '0'))
                if id== 0:
                    raise NameError("Parametro no encontrado")
                eDetalleInformeContratacion = DetalleInformeContratacion.objects.get(pk=id)
                eDetalleInformeContratacion.valor_x_hora_id = None if id_valo_x_hora == 0 else id_valo_x_hora
                eDetalleInformeContratacion.save(request)
                eDetalleInformeContratacion.informecontratacion.generar_actualizar_informe_memo_contratacion_pdf_segundo_plano(request)

                return JsonResponse({'result': True, 'pk':eDetalleInformeContratacion.informecontratacion_id})

            except Exception as ex:
                pass

        elif action == 'reiniciar_acta':
            try:
                id = int(request.POST.get('id', '0'))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")

                eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=id)
                eActaSeleccionDocente.fecha_generacion = hoy
                eActaSeleccionDocente.fecha_legalizacion = None
                eActaSeleccionDocente.cerrada = False
                eActaSeleccionDocente.estado = 1
                eActaSeleccionDocente.save(request)
                eActaSeleccionDocente.actualizar_documeto_pdf_acta(request)
                eActaSeleccionDocente.guardar_recorrido_acta_seleccion_docente(request,
                                                                               actaparalelo=None,
                                                                               persona=persona,
                                                                               observacion=f"Reinició acta de selección docente",
                                                                               archivo=None)

                log(u'reinicio la acta: %s' % eActaSeleccionDocente, request, "edit")
                return JsonResponse({'result': True, 'pk':eActaSeleccionDocente.pk})
            except Exception as ex:
                pass

        elif action == 'reiniciar_informe':
            try:
                id = int(request.POST.get('id', '0'))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")

                eInformeContratacion = InformeContratacion.objects.get(pk=id)
                eInformeContratacion.reiniciar_informe(request,persona)
                log(u'reinicio informe: %s' % eInformeContratacion, request, "edit")
                return JsonResponse({'result': True, 'pk':eInformeContratacion.pk})
            except Exception as ex:
                pass

        elif action == 'notificar_integrantes_firmar':
            try:
                id = int(request.POST.get('id', '0'))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")
                eInformeContratacion = InformeContratacion.objects.get(pk=id)
                eInformeContratacion.notificar_orden_integrante_toca_firmar(request)
                return JsonResponse({'result': True, 'pk':eInformeContratacion.pk})
            except Exception as ex:
                pass

        elif action == 'notificar_integrantes_firmar':
            try:
                id = int(request.POST.get('id', '0'))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")
                eInformeContratacion = InformeContratacion.objects.get(pk=id)
                eInformeContratacion.notificar_orden_integrante_toca_firmar(request)
                return JsonResponse({'result': True, 'pk':eInformeContratacion.pk})
            except Exception as ex:
                pass

        elif action == 'eliminar_invitacion':
            try:
                id = int(request.POST.get('id', '0'))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")
                eInscripcionInvitacion = InscripcionInvitacion.objects.get(pk=id)
                eInscripcionInvitacion.status =False
                eInscripcionInvitacion.save(request)
                eInscripcionConvocatoriaRequisitos = InscripcionConvocatoriaRequisitos.objects.filter(status=True,inscripcioninvitacion =eInscripcionInvitacion).update(status=False)
                log(u'reinicio la acta: %s' % eInscripcionInvitacion, request, "edit")
                return JsonResponse({'result': True})
            except Exception as ex:
                pass

        elif action == 'actualizar_acta_a_legalizada':
            try:
                LEGALIZADA = 4
                id = request.POST.get('id',0)
                eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk= id)
                eActaSeleccionDocente.estado = LEGALIZADA
                eActaSeleccionDocente.cerrada = True
                eActaSeleccionDocente.save(request)
                log(u"Acta legalizada", request, 'edit')
                return JsonResponse({'result': True, 'pk':eActaSeleccionDocente.pk})

            except Exception as ex:
                pass

        elif action == 'suprimir_acta_para_revision':
            try:
                PENDIENTE = 1
                id = request.POST.get('id', 0)
                eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=id)
                eActaSeleccionDocente.estado = PENDIENTE
                eActaSeleccionDocente.save(request)
                eActaSeleccionDocente.guardar_recorrido_acta_seleccion_docente(request,
                                                              actaparalelo=None,
                                                              persona=persona,
                                                              observacion=f"Suprimió la revisión por vicerrectorado académico de posgrado",
                                                              archivo=None)

                log(u"Acta suprimida de la revision para ajustes", request, 'edit')
                return JsonResponse({'result': True, 'pk':eActaSeleccionDocente.pk})

            except Exception as ex:
                pass
        elif action == 'generardocumento':
            mensaje = "Problemas al generar el documento. %s"
            try:
                nombre_dia = lambda x: {'1': 'Lunes', '2': 'Martes', '3': 'Miercoles', '4': 'Jueves', '5': 'Viernes', '6': 'Sabado', '0': 'Domingo'}[f'{x}']
                nombre_mes = lambda x: ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][int(x) - 1]
                if request.POST.get('iddoc') == '1':
                    return JsonResponse(json.loads(informe_tecnico_contratacion_docente(request=request, nombre_dia=nombre_dia, nombre_mes=nombre_mes).content))
                else:
                    return JsonResponse({'result': 'bad', 'url': '/adm_postulacion?action=listadoinvitaciones&rt=2'})
            except Exception as ex:
                return JsonResponse({"result": False, 'mensaje': mensaje % ex.__str__()})

        elif action == 'autollenado_plan_de_accion':
            try:
                acta_id = int(request.POST.get('id',0))
                if acta_id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")
                eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=acta_id)

                eActaSeleccionDocente.generar_plan_de_accion_automatico(request)

                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        elif action == 'autocargadocumentopersonalcontratar':
            try:
                pk = int(request.POST.get('id','0'))
                if pk == 0:
                    raise NameError("Parametro no encontrado")
                ePersonalAContratar = PersonalAContratar.objects.get(pk=pk)
                ePersonalAContratar.generar_configuracion_load_requisitos_auto_personal_contratar(request)


                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                pass

        elif action == 'autocargadocumentossga':
            try:
                pk = int(request.POST.get('id','0'))
                if pk == 0:
                    raise NameError("Parametro no encontrado")
                ePersonalAContratar = PersonalAContratar.objects.get(pk=pk)
                ePersonalAContratar.generar_configuracion_load_requisitos_sga_auto_personal_contratar(request)


                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                pass

        elif action == 'addconvocadopor':
            try:
                pk = request.POST.get('id', None)
                f = AdministrativoActaSeleccionDocenteForm(request.POST)
                f.edit(request.POST['administrativo'])
                if f.is_valid():
                    eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=pk)
                    eActaSeleccionDocente.convocadopor = f.cleaned_data.get('administrativo')
                    eActaSeleccionDocente.save(request)
                    eActaSeleccionDocente.guardar_recorrido_acta_seleccion_docente(request, actaparalelo=None, persona=persona,observacion=f"Actualización campo convocado por: {eActaSeleccionDocente.convocadopor }",archivo=None)
                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        elif action == 'editparainformeposgrado':
            try:
                pk = request.POST.get('id', None)
                f = AdministrativoActaSeleccionDocenteForm(request.POST)
                f.edit(request.POST['administrativo'])
                if f.is_valid():
                    eInformeContratacion = InformeContratacion.objects.get(pk=pk)
                    eInformeContratacion.para = f.cleaned_data.get('administrativo')
                    eInformeContratacion.save(request)
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})


        elif action == 'add_certificacion_presupuestaria':
            try:
                pk = request.POST.get('id', None)
                f = CertificacionPresupuestariaInformeContratacionForm(request.POST)
                if f.is_valid():
                    eDetalleInformeContratacion = DetalleInformeContratacion.objects.get(pk=pk)
                    eDetalleInformeContratacion.certificacionpresupuestaria = f.cleaned_data.get('certificacionpresupuestaria')
                    eDetalleInformeContratacion.save(request)
                    eDetalleInformeContratacion.informecontratacion.generar_actualizar_informe_memo_contratacion_pdf_segundo_plano(request)

                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})


        elif action == 'save-conclusiones-informe-contratacion':
            try:
                pk = int(request.POST.get('id', '0'))
                if pk == 0:
                    raise NameError("Parametro no encontrado")
                f = ConfiguracionConclusionesInformeContratacionForm(request.POST)
                eInformeContratacion = InformeContratacion.objects.get(pk=pk)
                if f.is_valid():
                    eInformeContratacion.conclusiones = f.cleaned_data['conclusiones']
                    eInformeContratacion.save(request)
                    eInformeContratacion.generar_actualizar_informe_memo_contratacion_pdf_segundo_plano(request)

                return JsonResponse({"result": True, "error": False})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        elif action == 'save-recomendaciones-informe-contratacion':
            try:
                pk = int(request.POST.get('id', '0'))
                if pk == 0:
                    raise NameError("Parametro no encontrado")
                f = ConfiguracionRecomendacionesInformeContratacionForm(request.POST)
                eInformeContratacion = InformeContratacion.objects.get(pk=pk)
                if f.is_valid():
                    eInformeContratacion.recomendaciones = f.cleaned_data['recomendaciones']
                    eInformeContratacion.save(request)
                    eInformeContratacion.generar_actualizar_informe_memo_contratacion_pdf_segundo_plano(request)

                return JsonResponse({"result": True, "error": False})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        elif action == 'editar_por_informe_posgrado':
            try:
                pk = request.POST.get('id', None)
                f = AdministrativoActaSeleccionDocenteForm(request.POST)
                f.edit(request.POST['administrativo'])
                if f.is_valid():
                    eInformeContratacion = InformeContratacion.objects.get(pk=pk)
                    eInformeContratacion.de = f.cleaned_data.get('administrativo')
                    eInformeContratacion.save(request)
                else:
                                        return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.",
                                         "form": [{k: v[0]} for k, v in f.errors.items()]})
                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        elif action == 'addorganizadopor':
            try:
                pk = request.POST.get('id', None)
                f = AdministrativoActaSeleccionDocenteForm(request.POST)
                f.edit(request.POST['administrativo'])
                if f.is_valid():
                    eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=pk)
                    eActaSeleccionDocente.organizadopor = f.cleaned_data.get('administrativo')
                    eActaSeleccionDocente.save(request)
                    eActaSeleccionDocente.guardar_recorrido_acta_seleccion_docente(request, actaparalelo=None,persona=persona, observacion=f"Actualización campo organizado por: {eActaSeleccionDocente.organizadopor}",archivo=None)

                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        elif action == 'firmar_informe_contratacion_por_archivo':
            try:
                persona = request.session.get('persona')
                observacion = f'Informe de contratación firmado por {persona}'
                pk = request.POST.get('id', '0')
                if pk == 0:
                    raise NameError("Parametro no encontrado")
                eInformeContratacion = InformeContratacion.objects.get(pk=pk)
                puede, mensaje = eInformeContratacion.puede_firmar_integrante_segun_orden(persona)
                if puede:
                    integrante = eInformeContratacion.get_integrante(persona)
                    pdf = eInformeContratacion.get_documento_informe().archivo
                    palabras = u"%s" % integrante.persona.nombre_titulos3y4()
                    firma = request.FILES.get("firma")
                    passfirma = request.POST.get('palabraclave')
                    bytes_certificado = firma.read()
                    extension_certificado = os.path.splitext(firma.name)[1][1:]
                    x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras)
                    datau = JavaFirmaEc(
                        archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                        extension_certificado=extension_certificado,
                        password_certificado=passfirma,
                        page=int(numpaginafirma), reason='', lx=x + 300, ly=y -15
                    ).sign_and_get_content_bytes()

                    documento_a_firmar = io.BytesIO()
                    documento_a_firmar.write(datau)
                    documento_a_firmar.seek(0)

                    eInformeContratacion.get_documento_informe().archivo.save(f'{eInformeContratacion.get_documento_informe().archivo.name.split("/")[-1].replace(".pdf", "")}_firmado.pdf', ContentFile(documento_a_firmar.read()))
                    integrante.firmo =True
                    integrante.save(request)

                    if eInformeContratacion.persona_es_quien_firma_informe_memo(integrante.pk):
                        pdf = eInformeContratacion.get_documento_memo().archivo
                        palabras = u"%s" % integrante
                        x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras.lower().title())
                        datau = JavaFirmaEc(
                            archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                            extension_certificado=extension_certificado,
                            password_certificado=passfirma,
                            page=int(numpaginafirma), reason='', lx=x + 5, ly=y +5
                        ).sign_and_get_content_bytes()

                        documento_a_firmar = io.BytesIO()
                        documento_a_firmar.write(datau)
                        documento_a_firmar.seek(0)
                        eInformeContratacion.get_documento_memo().archivo.save(
                            f'{eInformeContratacion.get_documento_memo().archivo.name.split("/")[-1].replace(".pdf", "")}_firmado.pdf',
                            ContentFile(documento_a_firmar.read()))


                    eInformeContratacion.guardar_historial_informe_contratacion(request, persona, observacion,eInformeContratacion.get_documento_informe().archivo)
                    eInformeContratacion.actualizar_estado_del_informe_de_contratacion(request)
                    log(u"Firmo informe de contratacion por honorarios profesionales", request, 'edit')
                    eInformeContratacion.notificar_orden_integrante_toca_firmar(request)
                else:
                    raise NameError(f"{mensaje}")


                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex})

        elif action == 'firmar_informe_contratacion_por_token':
            try:
                persona = request.session.get('persona')
                observacion = f'Informe de contratación firmado por {persona}'
                pk = request.POST.get('id', '0')
                if pk == 0:
                    raise NameError("Parametro no encontrado")
                eInformeContratacion = InformeContratacion.objects.get(pk=pk)
                puede, mensaje = eInformeContratacion.puede_firmar_integrante_segun_orden(persona)
                if puede:
                    integrante = eInformeContratacion.get_integrante(persona)
                    f = ArchivoInvitacionForm(request.POST, request.FILES)
                    if f.is_valid() and request.FILES.get('archivo', None):
                        newfile = request.FILES.get('archivo')
                        if newfile:
                            if newfile.size > 6291456:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):].lower()
                                if ext == '.pdf':
                                    _name = generar_nombre(f"{eInformeContratacion.get_documento_informe().codigo.__str__()}", '')
                                    _name = remover_caracteres_tildes_unicode( remover_caracteres_especiales_unicode(_name)).lower().replace(' ', '_').replace('-','_')
                                    newfile._name = generar_nombre(u"%s_" % _name, f"{_name}.pdf")

                                    eInformeContratacion.get_documento_informe().archivo = newfile
                                    eInformeContratacion.get_documento_informe().save(request)
                                    eInformeContratacion.guardar_historial_informe_contratacion(request, persona,
                                                                                                observacion,
                                                                                                eInformeContratacion.get_documento_informe().archivo)
                                    integrante.firmo = True
                                    integrante.save(request)
                                    eInformeContratacion.actualizar_estado_del_informe_de_contratacion(request)
                                    log(u"Firmo informe de contratacion por honorarios profesionales por token", request, 'edit')
                                    eInformeContratacion.notificar_orden_integrante_toca_firmar(request)
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivos PDF"})

                else:
                    raise NameError(f"{mensaje}")


                return JsonResponse({"result": "ok"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex})

        elif action == 'pdfbaremo':
            try:
                ida = int(request.POST['ida'])
                eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=ida)

                data["eActaSeleccionDocente"] = eActaSeleccionDocente

                qrname = 'ba_baremo_{}'.format(random.randint(1, 100000).__str__())
                directory = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'baremodetallado')
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'baremodetallado', 'ba'))
                try:
                    os.stat(directory)
                except:
                    os.mkdir(directory)

                rutapdf = folder + qrname + '.pdf'
                if os.path.isfile(rutapdf):
                    os.remove(rutapdf)

                imagenqr = 'qr' + qrname
                conviert_html_to_pdfsavecontratomae(
                    'adm_postulacion/baremodescargado.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                        'imprimeqr': True,
                        'qrname': imagenqr
                    }, qrname + '.pdf', 'baremodetallado'
                )

                qrresult ='/media/qrcode/baremodetallado/' + qrname + '.pdf'
                return JsonResponse({"result": "ok", 'url': qrresult})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al descargar pagaré."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud incorrecta. %s" % ex.__str__()})
    else:
        if 'action' in request.GET:
            data['rt'] = request.GET['rt'] if 'rt' in request.GET else ''
            data['action'] = action = request.GET['action']

            if action == 'contratacion':
                try:
                    data['title'] = u"Contratación"
                    pk = int(request.GET.get('id','0'))
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=pk)
                    eActaParalelo = eActaSeleccionDocente.get_convocatorias()
                    data['eActaParalelo'] = eActaParalelo
                    data['eActaSeleccionDocente'] = eActaSeleccionDocente

                    return render(request, 'adm_contratacion/contratacion.html', data)
                except Exception as ex:
                    pass

            elif action == 'evaluarrequisitoscontratacion':
                try:
                    data['invitacion'] = inscripcion = InscripcionConvocatoria.objects.get(pk=request.GET['id'])
                    data['title'] = f"Notificar y enviar requisitos de contratación: {inscripcion.postulante.persona}"

                    if inscripcion.convocatoria.requisitosconvocatoria().values('id').exists():
                        f = CerrarActaForm()
                        f.del_field('estado')
                        f.fields['fecharequisitos'].initial = inscripcion.get_fecha_revision_requisitos() if inscripcion.get_fecha_revision_requisitos() else hoy + timedelta(3)
                        data['form'] = f

                    data['id'] = inscripcion.pk
                    data['convocatoria'] = inscripcion.convocatoria
                    data['id_acta'] = request.GET.get('id_acta')

                    if invitacion := InscripcionInvitacion.objects.filter(inscripcion=inscripcion, status=True).first():
                        data['requisitospreaprobados'] = InscripcionRequisitoPreAprobado.objects.filter(inscripcioninvitacion=invitacion, status=True).order_by('-id').first()
                    return render(request, 'adm_contratacion/evaluarrequisitoscontratacion.html', data)
                except Exception as ex:
                    pass

            elif action == 'configurar_requisitos':
                try:
                    pk = int(request.GET.get('id','0'))

                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    data['ePersonalAContratar'] = ePersonalAContratar = PersonalAContratar.objects.get(pk=pk)
                    data['title'] = f"CONFIGURAR REQUISITOS DE CONTRATACIÓN: {ePersonalAContratar.inscripcion}{ePersonalAContratar.actaparalelo.paralelo}"
                    ePersonalAContratar.generar_automatico_requisitos_convocatoria(request)
                    if ePersonalAContratar.inscripcion.convocatoria.requisitosconvocatoria().values('id').exists():

                        f = CerrarActaForm()
                        f.del_field('estado')
                        f.fields['fecharequisitos'].initial = ePersonalAContratar.inscripcion.get_fecha_revision_requisitos() if ePersonalAContratar.inscripcion.get_fecha_revision_requisitos() else hoy + timedelta(3)
                        data['form'] = f

                    return render(request, 'adm_contratacion/configuracionrequisitos.html', data)
                except Exception as ex:
                    pass

            elif action == 'editarfechamaximarequisitos':
                try:
                    pk = int(request.GET.get('id','0'))

                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    data['eInscripcionInvitacion'] = eInscripcionInvitacion = InscripcionInvitacion.objects.get(pk=pk)
                    f = CerrarActaForm()
                    f.del_field('estado')
                    f.fields['fecharequisitos'].initial =eInscripcionInvitacion.fecharevisionrequisitos
                    data['form'] = f
                    data['id'] = eInscripcionInvitacion.pk
                    template = get_template('adm_contratacion/modal/formmodal.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})

                    return render(request, '', data)
                except Exception as ex:
                    pass

            elif action == 'generar_informe_de_contratacion':
                try:
                    ids = request.GET.getlist('ids[]')
                    ePersonalAContratars = PersonalAContratar.objects.filter(status=True, pk__in =ids)
                    data['ePersonalAContratars'] = ePersonalAContratars
                    data['ids'] = ids
                    template = get_template('adm_contratacion/modal/form_generar_informe.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})

                    return render(request, '', data)
                except Exception as ex:
                    pass

            elif action == 'revision_requisitos_personal_a_contratar':
                try:
                    pk = int(request.GET.get('id','0'))

                    if pk == 0:
                        raise NameError("Parametro no encontrado")

                    data['ePersonalAContratar'] = ePersonalAContratar = PersonalAContratar.objects.get(pk=pk)
                    data['title'] = f"REVISIÓN  REQUISITOS DE CONTRATACIÓN: {ePersonalAContratar.inscripcion} - {ePersonalAContratar.actaparalelo.paralelo}"

                    data['inscripcion'] = eInscripcionInvitacion = ePersonalAContratar.get_estado_invitacion()
                    data['estadofinalrequistos'] = estados_permitidos = [estado for estado in ESTADO_REVISION if estado[0] in (1, 2, 7)]
                    data['horario_pregrado'] = False
                    if eInscripcionInvitacion.get_horario_pregrado(periodo):
                        data['horario_pregrado'] = eInscripcionInvitacion.get_horario_pregrado(periodo)

                    if Profesor.objects.filter(persona=eInscripcionInvitacion.inscripcion.postulante.persona).exists():
                        profesor = Profesor.objects.filter(persona=eInscripcionInvitacion.inscripcion.postulante.persona).first()
                        data['profesor'] = profesor
                    return render(request, 'adm_contratacion/revisionrequisitospersonalacontratar.html', data)
                except Exception as ex:
                    pass

            elif action == 'reporte-tramite-contratacion':
                try:
                    return reporte_general_tramites_contratacion_posgrado(request)
                except Exception as ex:
                    pass

            elif action == 'grupo-actas':
                try:
                    data['title'] = u"Grupos de actas"
                    #data['grupodeactas'] = ActaConvocatoria.objects.filter(status=True)
                    return render(request, "adm_postulacion/gruposdeactas.html", data)
                except Exception as ex:
                    pass

            elif action == 'legalizaracta':
                try:
                    acta = ActaSeleccionDocente.objects.get(pk=request.GET['id'])
                    puede_firmar,eintegrante_anterior = acta.get_puede_firma_integrante_segun_orden(persona)
                    if not puede_firmar:
                        try:
                            return JsonResponse({"result": False,"message":"","mensaje": f"No es su turno de firmar, espere a que firme el {eintegrante_anterior.cargo}, {eintegrante_anterior.persona}"})
                        except Exception:
                            return JsonResponse({"result": False,"message":"","mensaje": f"{eintegrante_anterior}"})

                    f = FirmaElectronicaIndividualForm()
                    template = get_template("adm_postulacion/modal/firmardocumento.html")
                    data['id'] = acta.pk
                    data['id_cv'] = request.GET.get('id_cv', 0)
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            elif action == 'firmar_informe_contratacion_por_archivo':
                try:
                    eInformeContratacion = InformeContratacion.objects.get(pk=request.GET['id'])
                    f = FirmaElectronicaIndividualForm()
                    data['id'] = eInformeContratacion.pk
                    template = get_template("adm_postulacion/modal/firmardocumento.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            elif action == 'firmar_por_token':
                try:
                    acta = ActaSeleccionDocente.objects.get(pk=request.GET['id'])
                    puede_firmar,eintegrante_anterior = acta.get_puede_firma_integrante_segun_orden(persona)
                    if not puede_firmar:
                        try:
                            return JsonResponse({"result": False,"message":"","mensaje": f"No es su turno de firmar, espere a que firme el {eintegrante_anterior.cargo}, {eintegrante_anterior.persona}"})
                        except Exception:
                            return JsonResponse({"result": False,"message":"","mensaje": f"{eintegrante_anterior}"})
                    data['alert'] = {'type': 'warning', 'message':u"A continuación debe subir el documento firmado con su firma en el lugar que corresponda. <b>Favor revisar el documento antes de subir.</b>"}

                    data['form2'] = ArchivoInvitacionForm()
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    data['id'] = acta.pk
                    data['id_cv'] = request.GET.get('id_cv', 0)
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            elif action == 'firmar_informe_contratacion_por_token':
                try:
                    eInformeContratacion = InformeContratacion.objects.get(pk=request.GET['id'])
                    data['form2'] = ArchivoInvitacionForm()
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    data['id'] = eInformeContratacion.pk
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'legalizaractamanual':
                try:
                    acta = ActaSeleccionDocente.objects.get(pk=request.GET.get('id'))
                    data['id'] = acta.pk
                    data['form2'] = ArchivoInvitacionForm()
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})

            elif action == 'informe-tecnico-certificacion-presupuestaria':
                mensaje = "Problemas al generar el documento. %s"
                try:
                    carreras = Malla.objects.values('carrera__id').filter(carrera__niveltitulacion_id=4, carrera__coordinacion__id=7, vigente=True, cerrado=False, status=True).distinct('carrera__nombre').order_by('carrera__nombre')
                    data['maestrias'] = Carrera.objects.filter(pk__in=carreras, activa=True, status=True)
                    data['hoy'] = hoy
                    return download_html_to_pdf('adm_postulacion/documentoscontrato/informetecnicocertificacionpresupuestaria.html', {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': mensaje % ex.__str__()})

            elif action == 'memo-certificacion-presupuestaria':
                mensaje = "Problemas al generar el memorándum. %s"
                try:

                    documento = DocumentoInvitacion.objects.get(pk=request.GET.get('iddoc'))
                    ii = InscripcionInvitacion.objects.filter(pk=int(request.GET['pk'])).first()
                    finicio = ii.materia.inicio
                    ffin = ii.materia.fin
                    meses = list(dict.fromkeys([f.strftime('%m') for f in daterange(finicio, ffin)]))
                    diassemana = ii.materia.horario().values_list('dia', flat=True).filter(turno__status=True)
                    dias_mes_clases = []

                    for x in meses:
                        dias = list(dict.fromkeys([f.strftime('%d') for f in daterange(finicio, ffin) if f.strftime("%m") == x and f.isoweekday() in diassemana]))
                        dias_mes_clases.append({"mes": nombre_mes(x), "dias": dias, "num_mes":x}) if dias else None

                    data['dias_mes_clases'] = dias_mes_clases
                    data['suscrito'] = ii
                    mes = nombre_mes(int(hoy.strftime("%m")))
                    data['fechacabecera'] = f"Milagro, {hoy.strftime('%d')} de {mes} del {hoy.strftime('%Y')}"
                    data['rmu'] = ii.inscripcion.postulante.persona.contratodip_set.order_by('-id').first()
                    data['documento'] = documento
                    #data['secuencia'] =
                    data['firmas'] = FirmasDocumentoInvitacion.objects.filter(documentoinvitacion=documento.id, status=True)
                    if 'web' in request.GET:
                        data['web'] = True
                        return render(request, "adm_postulacion/documentoscontrato/memocertificacionpresupuestaria.html", {"data": data})
                    else:
                        return download_html_to_pdf('adm_postulacion/documentoscontrato/memocertificacionpresupuestaria.html', {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': mensaje % ex.__str__()})

            elif action == 'memocontratoadministrativo':
                mensaje = "Problemas al generar el documento. %s"
                try:
                    ii = InscripcionInvitacion.objects.filter(pk=int(request.GET['pk'])).first()
                    data['suscrito'] = ii
                    data['hoy'] = hoy
                    data['rmu'] = ii.inscripcion.postulante.persona.contratodip_set.order_by('-id').first()
                    return download_html_to_pdf('adm_postulacion/documentoscontrato/memocontratopersonaladministrativo.html', {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': mensaje % ex.__str__()})

            elif action == 'memocontrataciondocente':
                mensaje = "Problemas al generar el memorándum. %s"
                try:

                    documento = DocumentoInvitacion.objects.get(pk=request.GET.get('iddoc'))
                    ii = InscripcionInvitacion.objects.filter(pk=int(request.GET['pk'])).first()
                    finicio = ii.materia.inicio
                    ffin = ii.materia.fin
                    meses = list(dict.fromkeys([f.strftime('%m') for f in daterange(finicio, ffin)]))
                    diassemana = ii.materia.horario().values_list('dia', flat=True).filter(turno__status=True)
                    dias_mes_clases = []

                    for x in meses:
                        dias = list(dict.fromkeys([f.strftime('%d') for f in daterange(finicio, ffin) if f.strftime("%m") == x and f.isoweekday() in diassemana]))
                        dias_mes_clases.append({"mes": nombre_mes(x), "dias": dias, "num_mes":x}) if dias else None

                    data['dias_mes_clases'] = dias_mes_clases
                    data['suscrito'] = ii
                    mes = nombre_mes(int(hoy.strftime("%m")))
                    data['fechacabecera'] = f"Milagro, {hoy.strftime('%d')} de {mes} del {hoy.strftime('%Y')}"
                    data['rmu'] = ii.inscripcion.postulante.persona.contratodip_set.order_by('-id').first()
                    data['documento'] = documento
                    #data['secuencia'] =
                    data['firmas'] = FirmasDocumentoInvitacion.objects.filter(documentoinvitacion=documento.id, status=True)
                    if 'web' in request.GET:
                        data['web'] = True
                        return render(request, "adm_postulacion/documentoscontrato/memocontrataciondocente.html", {"data": data})
                    else:
                        return download_html_to_pdf('adm_postulacion/documentoscontrato/memocontrataciondocente.html', {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': mensaje % ex.__str__()})

            elif action == 'memopagodocente':
                mensaje = "Problemas al generar el memorándum. %s"
                try:
                    documento_id = request.GET.get('d')

                    ii = InscripcionInvitacion.objects.filter(pk=int(request.GET['pk'])).first()
                    data['suscrito'] = ii
                    mes = nombre_mes(int(hoy.strftime("%m")))
                    data['fechacabecera'] = f"Milagro, {hoy.strftime('%d')} de {mes} del {hoy.strftime('%Y')}"
                    data['rmu'] = ii.inscripcion.postulante.persona.contratodip_set.order_by('-id').first()
                    data['firmas'] = FirmasDocumentoInvitacion.objects.filter(documentoinvitacion=documento_id, status=True)
                    if 'web' in request.GET:
                        data['web'] = True
                        return render(request, "adm_postulacion/documentoscontrato/memopagodocente.html", {"data": data})
                    else:
                        return convert_html_to_pdf('adm_postulacion/documentoscontrato/memopagodocente.html', {'pagesize': 'A4', 'data': data}, f'{ii}', u'documentospostulaciondip/documentos/')
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': mensaje % ex.__str__()})

            elif action == 'acta-control-previo-pago-docente':
                mensaje = "Problemas al generar el documento. %s"
                try:
                    ii = InscripcionInvitacion.objects.filter(pk=int(request.GET['pk'])).first()
                    data['suscrito'] = ii
                    data['hoy'] = hoy
                    mes = nombre_mes(int(hoy.strftime("%m")))
                    data['fechacabecera'] = f"{hoy.strftime('%d')} de {mes} del {hoy.strftime('%Y')}"
                    return download_html_to_pdf('adm_postulacion/documentoscontrato/actacontrolpreviopago_docente.html', {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': mensaje % ex.__str__()})

            elif action == 'configuraciondocumentos':
                try:
                    r = int(encrypt(request.GET.get('r')))
                    breadcrumb = ['CONFIGURACIÓN DE DOCUMENTOS']
                    data['title'] = u"Configuraciones"
                    if r == 1:
                        breadcrumb.append('CLASIFICACIONES')
                        data['clasificacion'] = ClasificacionDocumentoInvitacion.objects.filter(status=True)
                        data['breadcrumb'] = breadcrumb
                        return render(request, "adm_postulacion/clasificaciondocumento.html", data)
                    elif r == 2:
                        breadcrumb.append('SECUENCIAS')
                        data['secuencias'] = SecuenciaDocumentoInvitacion.objects.filter(status=True).exclude(tipo__in = [3,2])
                        data['breadcrumb'] = breadcrumb
                        return render(request, "adm_postulacion/secuenciadocumento.html", data)
                    elif r == 3:
                        breadcrumb.append('DOCUMENTOS')
                        data['documentos'] = DocumentoInvitacion.objects.filter(status=True, clasificacion__status=True).exclude(clasificacion__in = [3,2])
                        data['breadcrumb'] = breadcrumb
                        return render(request, "adm_postulacion/configuraciondocumentos.html", data)
                    elif r == 4:
                        breadcrumb.append('FIRMAS')
                        data['firmas'] = FirmasDocumentoInvitacion.objects.filter(status=True)
                        data['breadcrumb'] = breadcrumb
                        return render(request, "adm_postulacion/firmaresponsables.html", data)
                except Exception as ex:
                    pass

            elif action == 'addclasificaciondocumento':
                try:
                    data['form2'] = ClasificacionDocumentoInvitacionForm()
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})

            elif action == 'editclasificaciondocumento':
                try:
                    data['id'] = id = request.GET['id']
                    clasificacion = ClasificacionDocumentoInvitacion.objects.filter(id=int(encrypt(id))).first()
                    data['form2'] = ClasificacionDocumentoInvitacionForm(initial={'descripcion': clasificacion.descripcion})
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})

            elif action == 'adddocumentoinvitacion':
                try:
                    data['form2'] = DocumentoInvitacionForm()
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})

            elif action == 'editdocumentoinvitacion':
                try:
                    data['id'] = id = request.GET['id']
                    clasificacion = DocumentoInvitacion.objects.filter(id=int(encrypt(id))).first()
                    data['form2'] = DocumentoInvitacionForm(initial={'descripcion': clasificacion.descripcion})
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})

            elif action == 'addsecuencia':
                try:
                    data['form2'] = SecuenciaDocumentoInvitacionForm()
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})

            elif action == 'editsecuencia':
                try:
                    data['id'] = id = request.GET['id']
                    secuencia = SecuenciaDocumentoInvitacion.objects.get(id=int(encrypt(id)))
                    data['form2'] = SecuenciaDocumentoInvitacionForm(initial=model_to_dict(secuencia))
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})

            elif action == 'addfirmas':
                try:
                    data['form2'] = FirmasDocumentoInvitacionForm()
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})

            elif action == 'editfirmas':
                try:
                    data['id'] = id = request.GET['id']
                    fdi = FirmasDocumentoInvitacion.objects.get(id=id)
                    f = FirmasDocumentoInvitacionForm(initial=model_to_dict(fdi))
                    f.edit(fdi.persona_id)
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})

            elif action == 'listadoprogramas':
                try:
                    data['title'] = u'Programas vigentes'
                    search, filtro, url_vars = None, Q(status=True, vigente=True), '&action='+action

                    filtro = filtro & (Q(carrera__niveltitulacion_id=4) | Q(carrera__coordinacion__id=7))
                    if 's' in request.GET:
                        if len(request.GET['s']):
                            data['s'] = search = request.GET['s']
                            url_vars += '&s=' + search
                            filtro = filtro & (Q(carrera__nombre__unaccent__icontains=search) | Q(carrera__mencion__unaccent__icontains=search))

                    data['listadoprogramas'] = Malla.objects.filter(filtro).order_by('carrera__nombre')
                    data['url_vars'] = url_vars
                    return render(request, "adm_postulacion/listadoprogramas.html", data)
                except Exception as ex:
                    pass

            elif action == 'editplazosactaseleccion':
                try:
                    data['id'] = variable = request.GET.get('id')
                    var = VariablesGlobales.objects.get(variable=variable)
                    f = ConfiguracionPlazosActaSeleccion(initial={'valor': var.valor})
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'configuracionesgeneralesactaselecciondocente':
                try:
                    eConfiguracionGeneralActaSeleccionDocente = ConfiguracionGeneralActaSeleccionDocente.objects.filter(status=True)
                    if eConfiguracionGeneralActaSeleccionDocente.exists():
                        f = ConfiguracionGeneralActaSeleccionDocenteForm(initial=model_to_dict(eConfiguracionGeneralActaSeleccionDocente.first()))
                    else:
                        f = ConfiguracionGeneralActaSeleccionDocenteForm()
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    pass

            elif action == 'configurar_informe_contratacion_formato':
                try:
                    eConfiguracionInforme = ConfiguracionInforme.objects.filter(status=True)
                    if eConfiguracionInforme.exists():
                        f = ConfiguracionInformeForm(initial=model_to_dict(eConfiguracionInforme.first()))
                    else:
                        f = ConfiguracionInformeForm()

                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'order_firma_acta':
                try:
                    eOrdenFirmaActaSeleccionDocente = OrdenFirmaActaSeleccionDocente.objects.filter(status=True).order_by('orden')
                    data['eOrdenFirmaActaSeleccionDocente'] = eOrdenFirmaActaSeleccionDocente
                    return render(request, "adm_postulacion/orden_firma.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadoinscritos':
                try:
                    data['title'] = u'Listado de inscritos'
                    data['eCarreras'] = Carrera.objects.filter(status=True, coordinacion__id=7).order_by('-id').distinct()
                    input_elegible=0
                    input_no_elegidos=0
                    idc = request.GET.get('idc', 0)
                    ida = request.GET.get('ida', 0)
                    if ida == 'null':
                        ida = 0
                    if 'elegible' in request.GET:
                        input_elegible = int(request.GET.get('elegible', 0))

                    if 'input_no_elegidos' in request.GET:
                        input_no_elegidos = int(request.GET.get('input_no_elegidos', 0))
                    url_vars, filtro = f"&action={action}", Q(status=True)


                    if input_no_elegidos != 0:
                        url_vars += f"&input_no_elegidos={input_no_elegidos}"
                        filtro &= Q(inscripcionconvocatoria__estado__in =[1,3,11])

                    if input_elegible != 0:
                        url_vars += f"&elegible={input_elegible}"
                        filtro &= Q(inscripcionconvocatoria__estado=11)
                    else:
                        if input_no_elegidos != 0:
                            url_vars += f"&input_no_elegidos={input_no_elegidos}"
                            filtro &= Q(inscripcionconvocatoria__estado__in=[1, 3, 11,12])


                    if int(ida):

                        url_vars += f"&ida={ida}"
                        filtro &= Q(inscripcionconvocatoria__convocatoria__asignaturamalla__asignatura_id=ida)


                    if int(idc):
                        filtro = filtro & (Q(inscripcionconvocatoria__convocatoria__carrera__id=idc))
                        data['idc'] = int(idc)
                        url_vars += f"&idc={idc}"

                    if 's' in request.GET:
                        data['s'] = search = request.GET['s']
                        url_vars += f"&s={search}"
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = Q(Q(persona__nombres__unaccent__icontains=search) | Q(persona__usuario__username__icontains=search) | Q(persona__apellido1__unaccent__icontains=search) | Q(persona__apellido2__unaccent__icontains=search) | Q(persona__cedula__icontains=search) | Q(persona__pasaporte__icontains=search))
                        else:
                            filtro = Q(Q(persona__apellido1__unaccent__icontains=ss[0]) & Q(persona__apellido2__unaccent__icontains=ss[1])) | Q(Q(persona__apellido2__unaccent__icontains=ss[0]) & Q(persona__apellido1__unaccent__icontains=ss[1])) & Q(persona__nombres__unaccent__icontains=search)

                    eInscripcionPostulante = InscripcionPostulante.objects.filter(filtro).order_by('persona__apellido1', 'persona__apellido2').distinct()
                    if input_no_elegidos != 0:
                        eInscripcionPostulante = eInscripcionPostulante.exclude(inscripcionconvocatoria__estado__in=[2])

                    data['total'] = eInscripcionPostulante.count()
                    paging = MiPaginador(eInscripcionPostulante, 15)
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
                    data['listadoinscritos'] = page.object_list
                    data['url_vars'] = url_vars
                    data['input_no_elegidos'] = input_no_elegidos
                    data['ida'] = int(ida)
                    return render(request, "adm_postulacion/listadoinscritos.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_postulacion?info=%s" % ex.__str__())

            elif action == 'filtrar_modulo_por_programa':
                try:
                    id= request.GET.get('id',0)
                    if not int(id) == 0:
                        eCarrera = Carrera.objects.get(pk= id)
                        eAsignatura_id = Convocatoria.objects.values_list('asignaturamalla__asignatura', flat =True).filter(asignaturamalla__malla__carrera=eCarrera, status=True).distinct()
                        eAsignaturas = Asignatura.objects.filter(status=True, pk__in=eAsignatura_id)
                        data = {"result": "ok", "results": [ {"id": x.id, "name": f"{x.nombre}"} for x in eAsignaturas]}
                    else:
                        data = {"result": "ok"}
                    return JsonResponse(data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_postulacion?info=%s" % ex.__str__())

            elif action == 'mensajespredeterminados':
                try:
                    data['title'] = u'Mensajes predeterminados'
                    url_vars, filtro = f"&action={action}", Q(status=True)

                    paging = MiPaginador(MensajePredeterminado.objects.filter(filtro).distinct(),15)
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
                    data['url_vars'] = url_vars
                    return render(request, "adm_postulacion/view_mensajepredeterminado.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_postulacion?info=%s" % ex.__str__())

            elif action == 'configuracionbaremo':
                try:
                    data['title'] = u'Configuración de Baremo'
                    url_vars, filtro = f"&action={action}", Q(status=True)

                    paging = MiPaginador(RubricaSeleccionDocente.objects.filter(filtro).distinct(),15)
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
                    data['url_vars'] = url_vars
                    return render(request, "adm_postulacion/view_baremo.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_postulacion?info=%s" % ex.__str__())

            elif action == 'itemsbaremo':
                try:
                    data['title'] = u'Configuración de items de la rubrica'
                    url_vars, filtro = f"&action={action}", Q(status=True)
                    pk = int(request.GET.get('id','0'))
                    if pk =='0':
                        raise NameError("Parametro no encontrado")
                    eRubricaSeleccionDocente = RubricaSeleccionDocente.objects.get(pk=pk)
                    filtro &= Q(rubricaselecciondocente=eRubricaSeleccionDocente)

                    eDetalleItemRubricaSeleccionDocente = DetalleItemRubricaSeleccionDocente.objects.filter(filtro).distinct().order_by('orden')

                    paging = MiPaginador(eDetalleItemRubricaSeleccionDocente,15)
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
                    data['eRubricaSeleccionDocente'] = eRubricaSeleccionDocente
                    data['url_vars'] = url_vars
                    return render(request, "adm_postulacion/view_itemsbaremo.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_postulacion?info=%s" % ex.__str__())

            elif action == 'subitemsbaremo':
                try:
                    data['title'] = u'Configuración de sub items de la rubrica'
                    url_vars, filtro = f"&action={action}", Q(status=True)
                    pk = int(request.GET.get('id','0'))
                    if pk =='0':
                        raise NameError("Parametro no encontrado")
                    eDetalleItemRubricaSeleccionDocente = DetalleItemRubricaSeleccionDocente.objects.get(pk=pk)
                    filtro &= Q(detalleitemrubricaselecciondocente=eDetalleItemRubricaSeleccionDocente)

                    eDetalleSubItemRubricaSeleccionDocente = DetalleSubItemRubricaSeleccionDocente.objects.filter(filtro).distinct()

                    paging = MiPaginador(eDetalleSubItemRubricaSeleccionDocente,15)
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
                    data['eDetalleItemRubricaSeleccionDocente'] = eDetalleItemRubricaSeleccionDocente
                    data['url_vars'] = url_vars
                    return render(request, "adm_postulacion/view_subitembaremo.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_postulacion?info=%s" % ex.__str__())

            elif action == 'listadoinscritosconvocatoria':
                try:
                    data['title'] = u'Listado de inscritos convocatoria'
                    strng = lambda x: request.GET.get(x, '')
                    numbr = lambda x: int(request.GET.get(x, 0))
                    idm, idc, idcv, idp, e, search = strng('idm'), strng('idc'), strng('idcv'), strng('idp'), numbr('e'), strng('s')
                    url_vars = f'&action={action}&idm={idm}&idc={idc}&idcv={idcv}&idp={idp}'
                    filtro = Q(convocatoria_id=int(encrypt(idcv)), status=True, postulante__status=True)

                    if e:
                        url_vars += f'&e={e}'
                        filtro &= Q(estado=e)
                        data['e'] = e

                    if search:
                        s = search.split()
                        if len(s) == 1:
                            filtro &= (Q(postulante__persona__nombres__icontains=s[0]) | Q(postulante__persona__apellido1__icontains=s[0]) |
                                       Q(postulante__persona__cedula__icontains=s[0]) | Q(postulante__persona__apellido2__icontains=s[0]) |
                                       Q(postulante__persona__cedula__contains=s[0]))

                        elif len(s) == 2:
                            filtro &= ((Q(postulante__persona__apellido1__contains=s[0]) & Q(postulante__persona__apellido2__contains=s[1])) |
                                       (Q(postulante__persona__nombres__icontains=s[0]) & Q(postulante__persona__nombres__icontains=s[1])) |
                                       (Q(postulante__persona__nombres__icontains=s[0]) & Q(postulante__persona__apellido1__contains=s[1])))

                    paging = MiPaginador(InscripcionConvocatoria.objects.filter(filtro).order_by('postulante__persona__apellido1', 'postulante__persona__apellido2').distinct(), 15)
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
                    data['listadoinscritos'] = page.object_list
                    data['search'] = search if search else ""
                    data['url_vars'] = url_vars
                    data['idm'] = idm
                    data['idc'] = idc
                    data['idcv'] = idcv
                    data['idp'] = idp
                    data['subtitle'] = Convocatoria.objects.filter(pk=int(encrypt(idcv))).first()
                    data['eAprobacion'] = ESTADO_REVISION
                    return render(request, "adm_postulacion/listadoinscritosconvocatoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadoinvitaciones':
                try:
                    data['title'] = u'Listado de invitaciones'
                    inputperiodo, search, tab, filtro = int(request.GET.get('p', 0)), request.GET.get('s', ''), int(request.GET.get('rt', 1)), Q(status=True)

                    if tab == 1:
                        filtro &= Q(Q(estadoinvitacion=2) | Q(estadoinvitacion=4))

                        querybase = InscripcionInvitacion.objects.filter(filtro).order_by('inscripcion__postulante__persona__apellido1', 'inscripcion__postulante__persona__apellido2').distinct()

                        if inputperiodo:
                            data['inputperiodo'] = inputperiodo
                            filtro &= Q(materia__nivel__periodo=inputperiodo)

                        if search:
                            data['s'] = search
                            ss = search.split(' ')
                            if len(ss) == 1:
                                filtro &= (Q(inscripcion__postulante__persona__nombres__icontains=search) |
                                           Q(inscripcion__postulante__persona__apellido1__icontains=search) |
                                           Q(inscripcion__postulante__persona__apellido2__icontains=search) |
                                           Q(inscripcion__postulante__persona__cedula__icontains=search) |
                                           Q(inscripcion__postulante__persona__pasaporte__icontains=search) |
                                           Q(inscripcion__postulante__persona__usuario__username__icontains=search))
                            else:
                                filtro &= (Q(inscripcion__postulante__persona__apellido1__icontains=ss[0]) &
                                           Q(inscripcion__postulante__persona__apellido2__icontains=ss[1]))

                        paging = MiPaginador(querybase.filter(filtro).order_by('inscripcion__postulante__persona__apellido1', 'inscripcion__postulante__persona__apellido2').distinct(), 15)
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
                        data['listadoinvitaciones'] = page.object_list

                    if tab == 2:
                        if persona.usuario.is_superuser or puede_realizar_accion_afirmativo(request, 'postulaciondip.puede_ver_todas_las_actas_de_seleccion_docente_posgrado'):
                            data['listaAceptados'] = InscripcionInvitacion.objects.filter(estadoinvitacion=4, pasosproceso_id__gte=2, status=True).order_by('actaparalelo__acta_id')
                        else:
                            if pam := PersonalApoyoMaestria.objects.filter(personalapoyo__persona=persona, fechafin__gte=hoy, status=True):
                                pamCarrera, pamPeriodo = pam.values_list('carrera_id', flat=True), pam.values_list('periodo__id', flat=True)
                                filtro = (Q(status=True) & Q(inscripcion__convocatoria__carrera_id__in=pamCarrera) & Q(inscripcion__convocatoria__periodo_id__in=pamPeriodo) & Q(estadoinvitacion=4, pasosproceso_id__gte=2))
                                data['listaAceptados'] = InscripcionInvitacion.objects.filter(filtro).filter(actaparalelo__isnull = False).order_by('actaparalelo__acta_id')

                    data['listaPeriodos'] = Periodo.objects.filter(status=True, clasificacion=2, activo=True)
                    data['rt'] = tab
                    return render(request, "adm_postulacion/listadoinvitaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'generarcartaaceptacion':
                try:
                    data = {}
                    dominio_sistema = 'http://127.0.0.1:8000'
                    if not IS_DEBUG:
                        dominio_sistema = 'https://sga.unemi.edu.ec'
                    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema
                    id=int(request.GET['pk'])
                    temp = lambda x: remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(x.__str__()))
                    eInscripcionInvitacion = InscripcionInvitacion.objects.get(pk=id)
                    fecha =eInscripcionInvitacion.fechaaceptacion
                    data['eInscripcionInvitacion'] = eInscripcionInvitacion
                    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                    #
                    qrname = 'qr_certificado_cartaaceptacion_' + str(eInscripcionInvitacion.id)
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'cartaaceptacionposgrado', 'qr'))
                    directory = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'cartaaceptacionposgrado'))
                    os.makedirs(f'{directory}/qr/', exist_ok=True)
                    try:
                        os.stat(directory)
                    except:
                        os.mkdir(directory)
                    nombrepersona = temp(eInscripcionInvitacion.inscripcion.postulante.persona.__str__()).replace(' ', '_')
                    htmlname = 'cartaaceptacion_{}_{}'.format(nombrepersona, random.randint(1, 100000).__str__())
                    urlname = "/media/qrcode/cartaaceptacionposgrado/%s" % htmlname
                    # rutahtml = SITE_STORAGE + urlname
                    data['url_qr'] = url_qr = f'{SITE_STORAGE}/media/qrcode/cartaaceptacionposgrado/qr/{htmlname}.png'
                    url = pyqrcode.create(f'FIRMADO POR: {nombrepersona}\nfirmado desde https://sga.unemi.edu.ec\n FECHA: {datetime.today()}\n{dominio_sistema}/media/qrcode/cartaaceptacionposgrado/{htmlname}.pdf\n2.10.1')
                    imageqr = url.png(f'{directory}/qr/{htmlname}.png', 16, '#000000')
                    data['qrname'] = 'qr' + qrname
                    pdf_file,response = conviert_html_to_pdf_save_file_model(
                        'adm_postulacion/docs/cartaaceptacioninvitacion.html',
                        {'pagesize': 'A4', 'data': data}
                    )

                    eInscripcionInvitacion.generar_acta_aceptacion(request,pdf_file)

                    return response
                except Exception as ex:
                    pass

            elif action == 'listadocohortes':
                try:
                    data['title'] = u'Listado de Cohortes de la Carrera'
                    if request.GET['idm'] and request.GET['idc']:
                        malla = Malla.objects.get(pk=int(encrypt(request.GET['idm'])))
                        materiaperiodo = Materia.objects.values_list('nivel__periodo_id', flat=True).filter(asignaturamalla__malla=malla, status =True).distinct()
                        url_vars = '&action='+action+'&idm='+request.GET['idm']+'&idc='+request.GET['idc']
                        filtro = Q(status=True, clasificacion=2, id__in=materiaperiodo, activo=True)
                        search = ''

                        if 's' in request.GET:
                            data['s'] = search = request.GET['s']
                            url_vars += '&s=' + search
                            filtro &= Q(nombre__icontains=search)

                        paging = MiPaginador(Periodo.objects.filter(filtro).order_by('-anio','-cohorte'), 15)
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
                        data['listadocohortes'] = page.object_list
                        data['url_vars'] = url_vars
                        data['idcarrera'] = int(encrypt(request.GET['idc']))
                        data['malla'] = malla
                        return render(request, "adm_postulacion/listadocohortes.html", data)
                except Exception as ex:
                    pass

            elif action == 'reportedistributivoposgrado':
                try:
                    __author__ = 'Unemi'
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('%s' % hoy)
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 50)
                    ws.set_column(2, 2, 30)
                    ws.set_column(3, 3, 40)
                    ws.set_column(4, 4, 20)
                    ws.set_column(5, 5, 20)
                    ws.set_column(6, 6, 30)
                    ws.set_column(7, 7, 30)
                    ws.set_column(8, 8, 50)
                    ws.set_column(9, 9, 60)
                    ws.set_column(10, 10, 60)
                    formatotitulo_filtros = workbook.add_format({'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})
                    formatosubtitulo_filtros = workbook.add_format({'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 12})
                    formatoceldacab = workbook.add_format({'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247','font_color': 'white'})
                    formatoceldaleft = workbook.add_format({'text_wrap': True, 'align': 'left', 'valign': 'vcenter', 'border': 1})
                    formatoceldacenter = workbook.add_format({'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
                    ws.merge_range('A1:G1', "DETALLE DISTRIBUTIVO POSGRADO", formatotitulo_filtros)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'CARRERA', formatoceldacab)
                    ws.write(1, 2, 'COHORTE', formatoceldacab)
                    ws.write(1, 3, 'ASIGNATURA', formatoceldacab)
                    ws.write(1, 4, 'PARALELO', formatoceldacab)
                    ws.write(1, 5, 'FECHA INICIO', formatoceldacab)
                    ws.write(1, 6, 'FECHA FIN', formatoceldacab)
                    ws.write(1, 7, 'MATERIA', formatoceldacab)
                    ws.write(1, 8, 'CAMPO AMPLIO', formatoceldacab)
                    ws.write(1, 9, u'CAMPO ESPECÍFICO', formatoceldacab)
                    ws.write(1, 10, 'CAMPO DETALLADO', formatoceldacab)
                    filas_recorridas = 3
                    cont = 1
                    materias = Materia.objects.filter(nivel__periodo__clasificacion=2, nivel__status=True, nivel__periodo__activo=True, nivel__periodo__status=True, asignatura__status=True, status=True)
                    for materia in materias:
                        carrera = materia.asignaturamalla.malla.carrera
                        for perfilrequerido in PerfilRequeridoPac.objects.filter(personalacademico__infraestructuraequipamientopac__programapac__carrera=carrera,personalacademico__asignaturaimpartir__asignatura=materia.asignatura,personalacademico__asignaturaimpartir__status=True, titulacion__status=True,status=True):
                            ws.write('A%s' % filas_recorridas, str(cont), formatoceldacenter)
                            ws.write('B%s' % filas_recorridas, u"%s" % materia.asignaturamalla.malla.carrera, formatoceldaleft)
                            ws.write('C%s' % filas_recorridas, u"%s" % materia.nivel.periodo, formatoceldacenter)
                            ws.write('D%s' % filas_recorridas, u"%s" % materia.asignatura, formatoceldacenter)
                            ws.write('E%s' % filas_recorridas, u"%s" % materia.paralelo, formatoceldacenter)
                            ws.write('F%s' % filas_recorridas, u"%s" % materia.inicio, formatoceldacenter)
                            ws.write('G%s' % filas_recorridas, u"%s" % materia.fin, formatoceldacenter)
                            ws.write('H%s' % filas_recorridas, u"%s" % materia, formatoceldacenter)
                            concat = ""
                            for ca in perfilrequerido.titulacion.campoamplio.all():
                                concat += f"* {ca}" if ca else ''
                            ws.write('I%s' % filas_recorridas, u"%s" % concat, formatoceldacenter)
                            concat = ""
                            for ce in perfilrequerido.titulacion.campoespecifico.all():
                                concat += f"* {ce}" if ce else ''
                            ws.write('J%s' % filas_recorridas, u"%s" % concat, formatoceldacenter)
                            concat = ""
                            for cd in perfilrequerido.titulacion.campodetallado.all():
                                concat += f"* {cd}" if cd else ''
                            ws.write('K%s' % filas_recorridas, u"%s" % concat, formatoceldacenter)
                            filas_recorridas += 1
                            cont += 1
                    workbook.close()
                    output.seek(0)
                    filename = 'detalle_distributivo_posgrado.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporte-estado-postulantes':
                try:
                    __author__ = 'Unemi'
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('%s' % hoy)

                    filtro = Q(status=True)
                    convocatoria = int(request.GET.get('idc', 0))
                    if convocatoria: filtro &= Q(convocatoria_id=convocatoria)

                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 50)
                    ws.set_column(2, 2, 50)
                    ws.set_column(3, 3, 40)
                    ws.set_column(4, 4, 20)
                    ws.set_column(5, 5, 20)
                    ws.set_column(6, 6, 20)
                    ws.set_column(6, 7, 20)
                    ws.set_column(6, 8, 20)

                    formatotitulo_filtros = workbook.add_format({'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14, 'fg_color': '#1C3247','font_color': 'white'})
                    formatosubtitulo_filtros = workbook.add_format({'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 12})
                    formatoceldacab = workbook.add_format({'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247','font_color': 'white'})
                    formatoceldaleft = workbook.add_format({'text_wrap': True, 'align': 'left', 'valign': 'vcenter', 'border': 1})
                    formatoceldacenter = workbook.add_format({'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
                    ws.merge_range('A1:I1', "REPORTE ESTADO DE POSTULACIÓN", formatotitulo_filtros)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'MAESTRÍA', formatoceldacab)
                    ws.write(1, 2, 'COHORTE', formatoceldacab)
                    ws.write(1, 3, 'DOCENTE (POSTULANTE)', formatoceldacab)
                    ws.write(1, 4, 'ESTADO DE POSTULACION', formatoceldacab)
                    ws.write(1, 5, '¿SE LE ENVIÓ INVITACIÓN?', formatoceldacab)
                    ws.write(1, 6, '¿ACEPTÓ INVITACIÓN?', formatoceldacab)
                    ws.write(1, 7, 'ESTADO INVITACIÓN', formatoceldacab)
                    ws.write(1, 8, '¿ENVIÓ REQUISITOS?', formatoceldacab)
                    filas_recorridas = 3
                    cont = 1
                    for ic in InscripcionConvocatoria.objects.filter(filtro):
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldacenter)
                        ws.write('B%s' % filas_recorridas, u"%s" % ic.convocatoria.carrera, formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, u"%s" % ic.convocatoria.periodo.nombre, formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, u"%s" % ic.postulante.persona, formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, u"%s" % ic.get_estado_display(), formatoceldacenter)
                        inv = ic.inscripcioninvitacion_set.filter(status=True).first()
                        ws.write('F%s' % filas_recorridas, u"%s" % 'SI' if inv else 'NO', formatoceldacenter)
                        ws.write('G%s' % filas_recorridas, u"%s" % 'SI' if inv and inv.fechaaceptacion else 'NO', formatoceldacenter)
                        ws.write('H%s' % filas_recorridas, u"%s" % inv.get_estadoinvitacion_display() if inv else '---', formatoceldacenter)
                        ws.write('I%s' % filas_recorridas, u"%s" % 'SI' if inv and inv.inscripcionrequisito_set.filter(status=True).exists() else 'NO', formatoceldacenter)

                        filas_recorridas += 1
                        cont += 1
                    workbook.close()
                    output.seek(0)
                    filename = 'reporte_estado_postulacion.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'resultadosevaluaciondocenteposgrado':
                try:
                    data['title'] = u"Resultados Evaluación Docente"
                    profesor = Profesor.objects.filter(Q(persona=int(encrypt(request.GET['id'])), activo=True, status=True)).first()
                    profesormateria = ProfesorMateria.objects.values_list('materia_id', flat=True).filter(Q(profesor=profesor) & Q(materia__cerrado=False) | Q(materia__cerrado__isnull=True) & Q(activo=True, principal=True))
                    hoy = datetime.now().date()
                    rubricas = RespuestaRubrica.objects.values_list('rubrica_id').filter(respuestaevaluacion__profesor=profesor, status=True).distinct()
                    preguntasrubricas = RubricaPreguntas.objects.filter(rubrica__in=rubricas)
                    data['hoy'] = hoy
                    data['preguntas'] = preguntasrubricas
                    data['periodo'] = periodo
                    data['profesor'] = profesor
                    data['idmat'], data['idmal'], data['idp'], data['idcv'] = request.GET.get('idmat', ''), request.GET.get('idmal', ''), request.GET.get('idp', ''), request.GET.get('idcv', '')
                    data['listadoMaterias'] = Materia.objects.filter(id__in=set(profesormateria), status=True)
                    return render(request, "niveles/resultadosevaluaciondocenteposgrado.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_postulacion?info=Error: %s" % ex.__str__())

            elif action == 'addplanificacionparalelo':
                try:
                    ePlanificacionParalelo = PlanificacionParalelo.objects.filter(periodo_id=request.GET.get('idp'),
                                                                                  carrera_id=request.GET.get('idc'),
                                                                                  asignatura_id=request.GET.get('id'),
                                                                                  status=True)
                    if ePlanificacionParalelo.exists():
                        f = PlanificacionMateriaPosgradoForm(initial=model_to_dict(ePlanificacionParalelo.first()))
                    else:
                        f = PlanificacionMateriaPosgradoForm()
                    data['form2'] = f
                    data['id'] = request.GET['id']
                    data['idp'] = request.GET['idp']
                    data['idc'] = request.GET['idc']
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addplanificacionparalelomasivo':
                try:
                    f = PlanificacionMateriaPosgradoForm()
                    data['form2'] = f
                    data['id'] = ids_asignatura_malla = request.GET.getlist('ids_asignatura[]')
                    data['idp'] = request.GET['periodo_id']
                    data['idc'] = request.GET['carrera_id']
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'convocatoria_masivo':
                try:
                    id_string = request.GET.get('ids',0)
                    id_list = ast.literal_eval(id_string)
                    # Si id_list no es una lista, conviértelo en una lista con un solo elemento
                    if not isinstance(id_list, tuple):
                        id_list = (id_list,)
                    ePlanificacionMateria = PlanificacionMateria.objects.filter(status=True,pk__in = id_list)
                    form = ConvocatoriaMasivaForm()
                    data['form2'] = form
                    data['id'] = id_string
                    data['ePlanificacionMateria'] = ePlanificacionMateria
                    template = get_template('adm_planificacion/modal/convocar_masivo.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'listadoconvocatorias':
                try:
                    data['title'] = u'Listado de convocatorias'
                    idm, idc, idp = request.GET.get('idm', ''), request.GET.get('idc', ''), request.GET.get('idp', '')
                    data['periodo'] = Periodo.objects.get(pk=int(encrypt(idp)))
                    data['idcarrera'] = idcarrera = int(encrypt(idc))
                    data['malla'] = malla = Malla.objects.get(pk=int(encrypt(idm)))
                    url_vars = f"&action={action}&idm={idm}&idc={idc}&idp={idp}"
                    # asignaturasdelperiodo = Materia.objects.values_list('asignatura_id', flat=True).filter(nivel__periodo_id=int(encrypt(idp)))
                    filtro = Q(malla__id=int(encrypt(idm)),  malla__carrera__id=idcarrera, asignatura__status=True, status=True, malla__carrera__status=True)
                    if 's' in request.GET:
                        data['s'] = search = request.GET['s']
                        url_vars += '&s=' + search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro &= Q(asignatura__nombre__icontains=search)
                        else:
                            filtro &= (Q(asignatura__nombre__icontains=ss[0]) & Q(asignatura__nombre__icontains=ss[1]))

                    paging = MiPaginador(malla.asignaturamalla_set.filter(filtro).order_by('asignatura__nombre'), 15)
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
                    data['listadoconvocatorias'] = page.object_list
                    data['url_vars'] = url_vars
                    data['idp'] = idp
                    return render(request, "adm_postulacion/listadoconvocatorias.html", data)
                except Exception as ex:
                    pass

            elif action == 'convocatorias':
                try:
                    data['title'] = u'Convocatorias'
                    filtro, s, p = Q(status=True), request.GET.get('s', ''), int(request.GET.get('p', 0))
                    url_vars = f"&action={action}&p={p}"

                    if p:
                        data['p'] = p
                        filtro &= Q(periodo__id=p)

                    if s:
                        filtro &= Q(Q(asignaturamalla__asignatura__nombre__unaccent__icontains=s) | Q(nombre__unaccent__icontains=s) | Q(periodo__nombre__unaccent__icontains=s) | Q(carrera__nombre__unaccent__icontains=s) | Q(tipodocente__nombre__unaccent__icontains=s))
                        url_vars += f"&s={s}"
                        data['s'] = s

                    # paging = MiPaginador(Convocatoria.objects.filter(filtro).order_by('-id'), 15)
                    # p = 1
                    # try:
                    #     paginasesion = 1
                    #     if 'paginador' in request.session:
                    #         paginasesion = int(request.session['paginador'])
                    #     if 'page' in request.GET:
                    #         p = int(request.GET['page'])
                    #     else:
                    #         p = paginasesion
                    #     try:
                    #         page = paging.page(p)
                    #     except:
                    #         p = 1
                    #     page = paging.page(p)
                    # except:
                    #     page = paging.page(p)
                    # request.session['paginador'] = p
                    # data['paging'] = paging
                    # data['page'] = page
                    # data['rangospaging'] = paging.rangos_paginado(p)
                    data['convocatorias'] = Convocatoria.objects.filter(filtro).order_by('-fechafin')#page.object_list
                    data['url_vars'] = url_vars

                    nDays = 10  # To get records of
                    lastNDays = hoy - timedelta(nDays)
                    eConv = Convocatoria.objects.filter(status=True)
                    eActa = ActaSeleccionDocente.objects.filter(archivo__isnull=False, status=True)
                    eInsc = InscripcionConvocatoria.objects.filter(status=True)
                    cvDetails = {'count': eConv.count(), 'last_records': eConv.filter(fecha_creacion__gte=lastNDays).count()}
                    acDetails = {'count': eActa.count(), 'last_records': eActa.filter(fecha_creacion__gte=lastNDays).count()}
                    icDetails = {'count': eInsc.count(), 'last_records': eInsc.filter(fecha_creacion__gte=lastNDays).count()}
                    iApproved = {'count': eInsc.filter(estado=2).count(), 'last_records': eInsc.filter(fecha_creacion__gte=lastNDays, estado=2).count()}

                    data['detalle_cv'] = cvDetails
                    data['detalle_ac'] = acDetails
                    data['detalle_ic'] = icDetails
                    data['detalle_ap'] = iApproved
                    data['nDays'] = nDays
                    data['back'] = r"?action=convocatorias"

                    data['PERIODOS_CONVOCATORIA'] = [(x.pk, x.nombre, x.convocatoria_set.values('id').filter(status=True).count()) for x in Periodo.objects.filter(pk__in=Convocatoria.objects.values_list('periodo__id', flat=True).filter(status=True, activo=True).distinct())]
                    return render(request, "adm_postulacion/convocatorias.html", data)

                except Exception as ex:
                    return HttpResponseRedirect("/adm_postulacion?info=Error de conexión. %s" % ex.__str__())

            elif action == 'addactaseleccion':
                try:
                    data['id'] = pk = request.GET.get('id', 0)
                    tipo_generacion = int(request.GET.get('tipo_generacion', '0'))
                    f = ActaSeleccionDocenteForm()
                    f.fields['tipo_formato_acta'].initial =tipo_generacion
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add_orden_firma':
                try:
                    f = OrdenFirmaActaForm()
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add_integrantefirmainformecontratacion':
                try:
                    f = InformeContratacionIntegrantesFirmaForm()
                    data['form2'] = f
                    data['id'] = int(request.GET.get('id','0'))
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add_responsabilidad_firma':
                try:
                    f = ResponsabilidadFirmaForm()
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add_orden_firma_informe_contratacion':
                try:
                    f = OrdenFirmaInformeContratacionForm()
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'historial_seleccion':
                try:
                    id = request.GET.get('id', 0)
                    if id == 0:
                        raise NameError("Parametro no encontrado")
                    eActaParalelo= ActaParalelo.objects.get(pk=id)
                    eHistorialPersonalContratarActaParalelo = HistorialPersonalContratarActaParalelo.objects.filter(status=True,personalcontratar__actaparalelo =eActaParalelo )
                    data['HistorialPersonalContratarActaParalelos'] = eHistorialPersonalContratarActaParalelo
                    template = get_template('comiteacademico/comite/historial.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add_mensaje_predeterminado':
                try:
                    f = MensajePredeterminadoForm()
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add_rubrica_baremo':
                try:
                    f = RubricaSeleccionDocenteForm()
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add_item_rubrica_baremo':
                try:
                    f = DetalleItemRubricaSeleccionDocenteForm()
                    data['form2'] = f
                    data['id'] = int(request.GET.get('id','0'))
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            elif action == 'add_subitem_rubrica_baremo':
                try:
                    f = DetalleSubItemRubricaSeleccionDocenteForm()
                    data['form2'] = f
                    data['id'] = int(request.GET.get('id','0'))
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit_orden_firma':
                try:
                    eOrdenFirmaActaSeleccionDocente = OrdenFirmaActaSeleccionDocente.objects.get(pk=request.GET.get('id'))
                    f = OrdenFirmaActaForm(initial=model_to_dict(eOrdenFirmaActaSeleccionDocente))
                    data['form2'] = f
                    data['id'] = eOrdenFirmaActaSeleccionDocente.pk
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit_integrantefirmainformecontratacion':
                try:
                    eInformeContratacionIntegrantesFirma = InformeContratacionIntegrantesFirma.objects.get(pk=request.GET.get('id'))
                    f = InformeContratacionIntegrantesFirmaForm(initial={
                        'responsabilidadfirma':eInformeContratacionIntegrantesFirma.ordenFirmaInformeContratacion,
                        'persona':eInformeContratacionIntegrantesFirma.persona
                    })
                    data['form2'] = f
                    data['id'] = eInformeContratacionIntegrantesFirma.pk
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit_responsable_firma':
                try:
                    eResponsabilidadFirma = ResponsabilidadFirma.objects.get(pk=request.GET.get('id'))
                    f = ResponsabilidadFirmaForm(initial={
                        'responsabilidad':eResponsabilidadFirma.responsabilidad
                    })
                    data['form2'] = f
                    data['id'] = eResponsabilidadFirma.pk
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit_orden_firma_informe_contratacion':
                try:
                    eOrdenFirmaInformeContratacion = OrdenFirmaInformeContratacion.objects.get(pk=request.GET.get('id'))
                    f = OrdenFirmaInformeContratacionForm(initial=model_to_dict(eOrdenFirmaInformeContratacion))
                    data['form2'] = f
                    data['id'] = eOrdenFirmaInformeContratacion.pk
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit_mensaje_predeteminado':
                try:
                    eMensajePredeterminado = MensajePredeterminado.objects.get(pk=request.GET.get('id'))
                    f = MensajePredeterminadoForm(initial=model_to_dict(eMensajePredeterminado))
                    data['form2'] = f
                    data['id'] = eMensajePredeterminado.pk
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            elif action == 'edit_rubrica_baremo':
                try:
                    eRubricaSeleccionDocente = RubricaSeleccionDocente.objects.get(pk=request.GET.get('id'))
                    f = RubricaSeleccionDocenteForm(initial=model_to_dict(eRubricaSeleccionDocente))
                    data['form2'] = f
                    data['id'] = eRubricaSeleccionDocente.pk
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            elif action == 'edit_item_rubrica_baremo':
                try:
                    eDetalleItemRubricaSeleccionDocente = DetalleItemRubricaSeleccionDocente.objects.get(pk=request.GET.get('id'))
                    f = DetalleItemRubricaSeleccionDocenteForm(initial=model_to_dict(eDetalleItemRubricaSeleccionDocente))
                    data['form2'] = f
                    data['id'] = eDetalleItemRubricaSeleccionDocente.pk
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            elif action == 'edit_subitem_rubrica_baremo':
                try:
                    eDetalleSubItemRubricaSeleccionDocente = DetalleSubItemRubricaSeleccionDocente.objects.get(pk=request.GET.get('id'))
                    f = DetalleSubItemRubricaSeleccionDocenteForm(initial=model_to_dict(eDetalleSubItemRubricaSeleccionDocente))
                    data['form2'] = f
                    data['id'] = eDetalleSubItemRubricaSeleccionDocente.pk
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editactaseleccion':
                try:
                    acta = ActaSeleccionDocente.objects.get(pk=request.GET.get('id'))
                    f = ActaSeleccionDocenteForm(initial=model_to_dict(acta))
                    data['form2'] = f
                    data['id'] = acta.pk
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'listadoactas':
                try:
                    data['title'] = u"Actas de Comité Académico"
                    url_vars = ' '
                    search = None
                    filtro, back = Q(status=True), '?action=convocatorias'
                    idcv = request.GET.get('id', '')
                    id_estado_acta = request.GET.get('id_estado_acta', 0)
                    search = request.GET.get('searchinput', '')
                    if id_estado_acta !=0:
                        filtro &= Q(estado=id_estado_acta)
                        data['id_estado_seleccionado'] = int(id_estado_acta)
                        url_vars += "&id_estado_acta={}".format(id_estado_acta)

                    if search.isdigit():
                        filtro &= Q(numero__contains=search)
                    elif search != '':
                        filtro &= Q(comite__nombre__icontains=search)
                        url_vars += "&searchinput={}".format(search)

                    if idcv:
                        data['convocatoria'] = convocatoria = Convocatoria.objects.get(pk=idcv)
                        filtro &= Q(actaparalelo__convocatoria=convocatoria)

                    if pk := request.GET.get('pk', ''):
                        filtro &= Q(pk=pk)
                        url_vars += "&pk={}".format(pk)

                    data['back'] = back
                    data['plazo_legalizar'] = variable_valor('PLAZO_LEGALIZAR_ACTA_SELECCION')
                    listadoactas = None

                    if persona.usuario.is_superuser or puede_realizar_accion_afirmativo(request,'postulaciondip.puede_ver_todas_las_actas_de_seleccion_docente_posgrado'):
                        listadoactas = ActaSeleccionDocente.objects.filter(filtro).order_by('-id').distinct()
                    else:
                        if pam := PersonalApoyoMaestria.objects.filter(personalapoyo__persona=persona, fechafin__gte=hoy, status=True):
                            pamCarrera, pamPeriodo = pam.values_list('carrera_id', flat=True), pam.values_list('periodo__id', flat=True)
                            filtro_actaparalelo = Q(actaparalelo__status=True, actaparalelo__convocatoria__carrera_id__in=pamCarrera,
                                                    actaparalelo__convocatoria__periodo_id__in=pamPeriodo,status=True)
                            filtro_sin_actaparalelo = Q(actaparalelo__isnull=True)
                            #filtro = Q()  # Inicializa el filtro como una consulta vacía
                            filtro &= (filtro_actaparalelo | filtro_sin_actaparalelo)

                            listadoactas = ActaSeleccionDocente.objects.filter(filtro).filter(Q(status=True)).order_by('-id').distinct()

                    data['pk_convocatoria'] = idcv
                    data['estados_acta'] = ESTADO_ACTA
                    CARTA_ACEPTACION_ID=2
                    data['documentos'] = ClasificacionDocumentoInvitacion.objects.filter(status=True).exclude(id=CARTA_ACEPTACION_ID)
                    data['certificacionpresupuestaria'] = CertificacionPresupuestariaDip.objects.filter(status=True)

                    paging = MiPaginador(listadoactas, 10)
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
                    data['listadoactas'] = page.object_list
                    data['searchinput'] = search if search else ""
                    data['url_vars'] = url_vars
                    return render(request, 'adm_postulacion/listadoactas.html', data)
                except Exception as ex:
                    pass

            elif action == 'recorridoactaselecciondocente':
                try:
                    pk = int(request.GET.get('id', '0'))
                    if pk == 0:
                        raise NameError("Parametro no encontrado")

                    eActaSelecionDocente = ActaSeleccionDocente.objects.get(pk=pk)
                    eRecorridoActaSeleccionDocentes = RecorridoActaSeleccionDocente.objects.filter(status=True,acta = eActaSelecionDocente).order_by('id')
                    data['eRecorridoActaSeleccionDocentes'] = eRecorridoActaSeleccionDocentes
                    data['eActaSelecionDocente'] = eActaSelecionDocente
                    template = get_template('adm_postulacion/modal/historial_recorrido_acta_seleccion_docente.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'listadoinformes':
                try:
                    data['title'] = u"Informes de contratación"
                    filtro = Q(status=True)
                    url_vars = '&action=listadoinformes'
                    search = None
                    search = request.GET.get('searchinput', '')

                    if search:
                        eDocumentoInvitacion =DocumentoInvitacion.objects.values_list('informecontratacion_id',flat=True).filter(status=True,clasificacion_id = 1,codigo__icontains = search)

                        filtro &= Q(pk__in=eDocumentoInvitacion)

                    if pk := request.GET.get('pk', ''):
                        filtro &= Q(pk=pk)
                        url_vars += "&pk={}".format(pk)

                    eInformeContratacion = InformeContratacion.objects.filter(filtro)
                    paging = MiPaginador(eInformeContratacion, 10)
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
                    data['searchinput'] = search if search else ""
                    data['url_vars'] = url_vars
                    return render(request, 'adm_contratacion/informescontratacion.html', data)
                except Exception as ex:
                    pass

            elif action == 'listado_personal_contratar_validado':
                try:
                    data['title'] = u"Personal a contratar válidado"
                    filtro =Q(status=True,estado = 4)
                    url_vars = '&action=listado_personal_contratar_validado'
                    search = request.GET.get('searchinput', '')
                    ePersonalAContratar = None
                    if search:
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro &= (Q(inscripcion__postulante__persona__nombres__icontains=search) |
                                 Q(inscripcion__postulante__persona__apellido1__icontains=search) |
                                 Q(inscripcion__postulante__persona__apellido2__icontains=search) |
                                 Q(inscripcion__postulante__persona__cedula__icontains=search))
                        else:
                            filtro &= ((Q(inscripcion__postulante__persona__nombres__icontains=ss[0]) & Q(inscripcion__postulante__persona__nombres__icontains=ss[1])) |
                                 (Q(inscripcion__postulante__persona__apellido1__icontains=ss[0]) & Q(inscripcion__postulante__persona__apellido2__icontains=ss[1])) |
                                 (Q(inscripcion__postulante__persona__cedula__icontains=ss[0]) & Q(inscripcion__postulante__persona__cedula__icontains=ss[1])))



                    if persona.usuario.is_superuser or puede_realizar_accion_afirmativo(request,'postulaciondip.puede_ver_todas_las_actas_de_seleccion_docente_posgrado'):
                        ePersonalAContratar = PersonalAContratar.objects.filter(filtro).order_by('-id').distinct()
                    else:
                        if pam := PersonalApoyoMaestria.objects.filter(personalapoyo__persona=persona, fechafin__gte=hoy, status=True):
                            pamCarrera, pamPeriodo = pam.values_list('carrera_id', flat=True), pam.values_list('periodo__id', flat=True)
                            filtro_actaparalelo = Q(actaparalelo__status=True, actaparalelo__convocatoria__carrera_id__in=pamCarrera,
                                                    actaparalelo__convocatoria__periodo_id__in=pamPeriodo,status=True)
                            filtro_sin_actaparalelo = Q(actaparalelo__isnull=True)
                            filtro &= (filtro_actaparalelo | filtro_sin_actaparalelo)

                            ePersonalAContratar = PersonalAContratar.objects.filter(filtro).order_by('-id').distinct()
                    paging = MiPaginador(ePersonalAContratar, 10)
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
                    data['url_vars'] = url_vars
                    return render(request, 'adm_contratacion/personalcontratarvalidado.html', data)
                except Exception as ex:
                    pass

            elif action == 'firmaractaselecciondocente':
                try:
                    request.session['view_selecciondocente_tribunal'] = 1
                    data['title'] = u"Firmar actas de Comité Académico"
                    url_vars = f"&action={action}"
                    integrante_comite = IntegranteComiteAcademicoPosgrado.objects.values_list('comite_id').filter(status=True, persona=persona)
                    data['existen_informes_que_deba_firmar'] = existe_informes_que_revisar(persona)
                    filtro = Q(status=True,comite__in=integrante_comite, estado__in=[3,4])
                    search = None
                    search = request.GET.get('searchinput', '')
                    if search.isdigit():
                        filtro &= Q(numero__contains=search)
                    elif search != '':
                        filtro &= Q(comite__nombre__icontains=search)
                        url_vars += "&searchinput={}".format(search)

                    if pk := request.GET.get('pk', ''):
                        filtro &= Q(pk=pk)
                        url_vars += "&pk={}".format(pk)

                    listadoactas = ActaSeleccionDocente.objects.filter(filtro).order_by('-id','estado').distinct()

                    paging = MiPaginador(listadoactas, 10)
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
                    data['listadoactas'] = page.object_list
                    data['searchinput'] = search if search else ""
                    data['url_vars'] = url_vars
                    data['plazo_legalizar'] = variable_valor('PLAZO_LEGALIZAR_ACTA_SELECCION')
                    return render(request, 'adm_postulacion/firmaractaselecciondocente.html', data)
                except Exception as ex:
                    pass

            elif action == 'firmarinformecontratacion':
                try:
                    request.session['view_selecciondocente_tribunal'] = 3
                    ids_informecontratacion = InformeContratacionIntegrantesFirma.objects.values_list('informecontratacion',flat =True).filter(status=True,ordenFirmaInformeContratacion__responsabilidadfirma_id__in=[3, 4], persona=persona).distinct()
                    filtro = Q(status=True, estado__in =[2,3],pk__in = ids_informecontratacion)
                    data['title'] = u"Firmar informes de contratación por honorarios profesionales"
                    url_vars = f"&action={action}"
                    search = None
                    search = request.GET.get('searchinput', '')

                    eInformeContratacion = InformeContratacion.objects.filter(filtro).order_by('estado').distinct()
                    data['existen_informes_que_deba_firmar'] = existe_informes_que_revisar(persona)
                    paging = MiPaginador(eInformeContratacion, 25)
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
                    data['eInformeContratacion'] = page.object_list
                    data['searchinput'] = search if search else ""
                    data['url_vars'] = url_vars
                    return render(request, 'adm_contratacion/firmarinformecontratacion.html', data)
                except Exception as ex:
                    pass

            elif action == 'grupocomiteacademico':
                try:
                    request.session['view_selecciondocente_tribunal'] = 2
                    if 'revisar_acta' in request.GET:
                        id = int(request.GET.get('revisar_acta',0))
                        if id == 0:
                            raise NameError("Parametro no encontrado")
                        acta = ActaSeleccionDocente.objects.get(pk = id )
                        data['title'] = 'Paralelos'
                        data['acta'] = acta
                        data['paralelos'] = ActaParalelo.objects.filter(acta=acta, status=True)
                        return render(request, 'comiteacademico/comite/view.html', data)

                    if 'paralelo_id' in request.GET:
                        id = request.GET.get('paralelo_id', 0)
                        if id == 0:
                            raise NameError("Parametro no encontrado")

                        data['title'] = u"Gestión del personal a contratar"
                        data['paralelo'] = paralelo = ActaParalelo.objects.get(pk=id)
                        data['personal'] = PersonalAContratar.objects.filter(actaparalelo=paralelo, status=True)
                        total_principales_en_acta = PersonalAContratar.objects.filter(actaparalelo__acta=paralelo.acta,tipo_id=1, status=True)
                        total_vacantes = paralelo.acta.get_total_vacantes()
                        data['puede_adicionar_personal'] = total_principales_en_acta.count() < total_vacantes
                        data['total_principales_en_acta'] = total_principales_en_acta
                        data['maximo_principal_paralelo'] = total_vacantes - total_principales_en_acta.count()
                        data['convocatoria'] = Convocatoria.objects.filter(pk=paralelo.convocatoria_id).first()
                        #inscripciones
                        NO_CUMPLE_PERFIL= 3
                        eInscripcionConvocatorias = InscripcionConvocatoria.objects.filter(
                            convocatoria=paralelo.convocatoria,
                            status=True,
                            postulante__status=True
                        ).order_by(
                            'postulante__persona__apellido1',
                            'postulante__persona__apellido2'
                        ).annotate(
                            estado_order=Case(
                                When(estado=12, then=Value(1)),
                                When(estado=11, then=Value(2)),
                                default=Value(3),
                                output_field=IntegerField()
                            )
                        ).order_by('estado_order')

                        data['listadoinscritos'] = todos_los_elegibles = eInscripcionConvocatorias.exclude(estado=NO_CUMPLE_PERFIL)
                        #banco elegible
                        bancoelegibles = InscripcionConvocatoria.objects.filter(estado=11,convocatoria__carrera_id=paralelo.convocatoria.carrera_id, convocatoria__asignaturamalla__asignatura_id=paralelo.convocatoria.asignaturamalla.asignatura_id, status=True)
                        data['bancoelegibles'] = bancoelegibles
                        miembrocomite = paralelo.acta.get_integrante(persona)

                        if miembrocomite:
                            es_director =True if miembrocomite.cargo.pk == 83 else False
                            try:
                                personas_seleccionadas = miembrocomite.get_votos_realizados(paralelo).values_list('inscripcion__postulante__persona_id', flat = True)
                            except Exception as ex:
                                print(ex)
                        else:
                            personas_seleccionadas = 0
                            es_director = False
                        data['es_director'] =es_director
                        data['personas_seleccionadas'] =personas_seleccionadas

                        personas_pendientes_de_realizar_baremo = todos_los_elegibles.count() - personas_seleccionadas.count() if not personas_seleccionadas == 0 else 0
                        data['personas_pendientes_de_realizar_baremo'] =personas_pendientes_de_realizar_baremo
                        return render(request, 'comiteacademico/comite/revisar_postulante.html', data)

                    data['title'] = u"Selección postulante comité académico"
                    url_vars = f"&action={action}"
                    integrante_comite = IntegranteComiteAcademicoPosgrado.objects.values_list('comite_id').filter(status=True, persona=persona)
                    filtro = Q(status=True, comite__in=integrante_comite)
                    search = None
                    search = request.GET.get('searchinput', '')

                    if search.isdigit():
                        filtro &= Q(numero__contains=search)
                    elif search != '':
                        filtro &= Q(comite__nombre__icontains=search)
                        url_vars += "&searchinput={}".format(search)
                    if pk := request.GET.get('pk', ''):
                        filtro &= Q(pk=pk)
                        url_vars += "&pk={}".format(pk)
                    # Filtra y ordena los resultados según las condiciones definidas
                    eActaSeleccionDocente = ActaSeleccionDocente.objects.filter(filtro).filter(enviada_a_comite=True).annotate(
                            estado_order=Case(
                                When(estado=2, then=Value(1)),
                                When(estado=3, then=Value(2)),
                                When(estado=4, then=Value(3)),
                                default=Value(4),
                                output_field=IntegerField()
                            )
                        ).order_by('-estado_order')

                    lista_resultados = list(filter(lambda x: x[1], map(lambda x: (x, x.get_cumple_con_horas_docente()), eActaSeleccionDocente)))
                    data['existen_informes_que_deba_firmar'] = existe_informes_que_revisar(persona)

                    paging = MiPaginador(lista_resultados, 10)
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
                    data['listadoactas'] = page.object_list
                    data['searchinput'] = search if search else ""
                    data['url_vars'] = url_vars
                    return render(request, 'comiteacademico/view.html', data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_postulacion?action=grupocomiteacademico&info=%s" % ex.__str__())

            elif action == 'actaseleccion':
                try:
                    data['title'] = u'Configurar Acta de Selección Docente'
                    acta = ActaSeleccionDocente.objects.get(pk=request.GET.get('id'))
                    data['progress'] = acta.porcentaje_configuracion()
                    data['t'] = int(request.GET.get('t', 0))
                    f = ActaSeleccionDocenteForm()
                    data['form'] = f
                    data['acta'] = acta
                    data['paralelos'] = ActaParalelo.objects.filter(acta=acta, status=True)
                    data['id'] = acta.pk
                    data['pk_cv'] = request.GET.get('pk_cv')
                    return render(request, "adm_postulacion/actaseleccion.html", data)
                except Exception as ex:
                    pass

            elif action == 'orden_firma_informe_contratacion':
                try:
                    eOrdenFirmaInformeContratacion = OrdenFirmaInformeContratacion.objects.filter(status=True).order_by('orden')
                    data['eOrdenFirmaInformeContratacion'] = eOrdenFirmaInformeContratacion
                    return render(request, "adm_contratacion/orden_firma.html", data)
                except Exception as ex:
                    pass

            elif action == 'responsabilidades_firma':
                try:
                    eResponsabilidadFirma = ResponsabilidadFirma.objects.filter(status=True).order_by("id")
                    data['eResponsabilidadFirma'] = eResponsabilidadFirma
                    return render(request, "adm_contratacion/responsabilidades_firma.html", data)
                except Exception as ex:
                    pass

            elif action == 'configurarinforme':
                try:
                    request.session['view_informe_configuracion'] = 'datos_generales'
                    data['title'] = u'Configurar Informe de contratación'
                    eInformeContratacion = InformeContratacion.objects.get(pk=request.GET.get('id'))
                    data['eInformeContratacion'] = eInformeContratacion
                    return render(request, "adm_contratacion/configurarinformecontratacion.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_postulacion?action=listadoinformes&info=%s" % ex.__str__())

            elif action == 'configurarinforme_personal_contratar':
                try:
                    request.session['view_informe_configuracion'] = 'personal_contratar'
                    data['title'] = u'Configurar Informe de contratación'
                    eInformeContratacion = InformeContratacion.objects.get(pk=request.GET.get('id'))
                    data['eInformeContratacion'] = eInformeContratacion
                    return render(request, "adm_contratacion/personal_a_contratar.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_postulacion?action=listadoinformes&info=%s" % ex.__str__())

            elif action == 'configurarinforme_conclusiones_recomendaciones':
                try:
                    request.session['view_informe_configuracion'] = 'conclusiones_recomendaciones'
                    data['title'] = u'Configurar Informe de contratación'
                    eInformeContratacion = InformeContratacion.objects.get(pk=request.GET.get('id'))
                    eConfiguracionConclusionesInformeContratacionForm = ConfiguracionConclusionesInformeContratacionForm()
                    eConfiguracionRecomendacionesInformeContratacionForm = ConfiguracionRecomendacionesInformeContratacionForm()

                    eConfiguracionConclusionesInformeContratacionForm.fields['conclusiones'].initial = eInformeContratacion.conclusiones
                    eConfiguracionRecomendacionesInformeContratacionForm.fields['recomendaciones'].initial = eInformeContratacion.recomendaciones

                    data['form_conclusiones'] = eConfiguracionConclusionesInformeContratacionForm
                    data['form_recomendaciones'] = eConfiguracionRecomendacionesInformeContratacionForm
                    data['eInformeContratacion'] = eInformeContratacion
                    return render(request, "adm_contratacion/conclusiones_recomendaciones.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_postulacion?action=listadoinformes&info=%s" % ex.__str__())

            elif action == 'configurarinforme_generar_pdf':
                try:
                    request.session['view_informe_configuracion'] = 'generar_pdf'
                    data['title'] = u'Configurar Informe de contratación'
                    eInformeContratacion = InformeContratacion.objects.get(pk=request.GET.get('id'))
                    data['eInformeContratacion'] = eInformeContratacion
                    return render(request, "adm_contratacion/generar_pdf.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_postulacion?action=listadoinformes&info=%s" % ex.__str__())

            elif action == 'integrantes_firman_informe':
                try:
                    data['title'] = u'Integrantes firman Informe de contratación'
                    eInformeContratacion = InformeContratacion.objects.get(pk=request.GET.get('id'))
                    data['eInformeContratacion'] = eInformeContratacion
                    return render(request, "adm_contratacion/integrantesfirmainformecontratacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'actaseleccion_invitado':
                try:
                    data['title'] = u'Configurar Acta de Selección Docente invitado'
                    acta = ActaSeleccionDocente.objects.get(pk=request.GET.get('id'))
                    data['progress'] = acta.porcentaje_configuracion()
                    data['t'] = int(request.GET.get('t', 0))
                    f = ActaSeleccionDocenteForm()
                    data['form'] = f
                    data['acta'] = acta
                    data['paralelos'] = ActaParalelo.objects.filter(acta=acta, status=True)
                    data['id'] = acta.pk
                    data['pk_cv'] = request.GET.get('pk_cv')
                    return render(request, "adm_postulacion/actaseleccioninvitado.html", data)
                except Exception as ex:
                    pass

            elif action == 'generaractaseleccion':
                try:
                    acta = ActaSeleccionDocente.objects.filter(pk=request.GET.get('id', None)).first()
                    plazo = datetime.now().date() + timedelta(variable_valor('PLAZO_GENERAR_ACTA_SELECCION'))

                    paralelos = ["%s - %s" % (paralelo[0], paralelo[1].strftime('%d/%m/%Y') if paralelo[1] else '') for paralelo in acta.actaparalelo_set.filter(status=True, inicio__lt=plazo).values_list('paralelo__nombre', 'inicio')]

                    if acta.tipo_formato_acta == 1:

                        if paralelos:
                            return JsonResponse({'result': False, 'mensaje': "La fecha de inicio de los paralelos: \n <b>%s</b> \n son menores al plazo mínimo para generar el acta (<b>%s</b>)." % (', \n'.join(paralelos), plazo.strftime('%d/%m/%Y'))})

                        if (url := get_acta_seleccion_docente_posgrado(acta, request=request)) is not None:
                            acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                          actaparalelo=None,
                                                                          persona=persona,
                                                                          observacion=f"Actualizó el documento PDF automaticamente",
                                                                          archivo=None)
                            return JsonResponse({'result':True, 'url':url})


                    else:
                        if (url := get_acta_seleccion_docente_posgrado_invitado(acta, request=request)) is not None:
                            return JsonResponse({'result':True, 'url':url})

                except Exception as ex:
                    return JsonResponse({'result':False, 'mensaje': u"%s" % ex.__str__()})

            elif action == 'actualizar_principales_alternos_baremo_acta':
                try:
                    acta = ActaSeleccionDocente.objects.filter(pk=request.GET.get('id', None)).first()
                    plazo = datetime.now().date() + timedelta(variable_valor('PLAZO_GENERAR_ACTA_SELECCION'))

                    paralelos = ["%s - %s" % (paralelo[0], paralelo[1].strftime('%d/%m/%Y') if paralelo[1] else '') for paralelo in acta.actaparalelo_set.filter(status=True, inicio__lt=plazo).values_list('paralelo__nombre', 'inicio')]

                    if acta.tipo_formato_acta == 1:
                        try:
                            acta.guardar_de_todas_las_convocatorias_los_principales_y_alternos(request)

                        except Exception as ex:
                            pass

                        if paralelos:
                            return JsonResponse({'result': False, 'mensaje': "La fecha de inicio de los paralelos: \n <b>%s</b> \n son menores al plazo mínimo para generar el acta (<b>%s</b>)." % (', \n'.join(paralelos), plazo.strftime('%d/%m/%Y'))})

                        if (url := get_acta_seleccion_docente_posgrado(acta, request=request)) is not None:
                            acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                          actaparalelo=None,
                                                                          persona=persona,
                                                                          observacion=f"Actualizó el documento PDF automaticamente",
                                                                          archivo=None)
                            return JsonResponse({'result':True, 'url':url})


                    else:
                        if (url := get_acta_seleccion_docente_posgrado_invitado(acta, request=request)) is not None:
                            return JsonResponse({'result':True, 'url':url})

                except Exception as ex:
                    return JsonResponse({'result':False, 'mensaje': u"%s" % ex.__str__()})

            elif action == 'generarinformecontratacion':
                try:
                    eInformeContratacion = InformeContratacion.objects.filter(pk=request.GET.get('id', None)).first()
                    if (url := eInformeContratacion.generar_actualizar_informe_memo_contratacion_pdf(request)) is not None:
                        return JsonResponse({'result': True, 'url': url})
                    else:
                        pass

                except Exception as ex:
                    return JsonResponse({'result':False, 'mensaje': u"%s" % ex.__str__()})

            elif action == 'horarios':
                try:
                    data['title'] = u"Gestión de horarios"
                    data['id'] = id = request.GET.get('id', None)
                    data['paralelo'] = paralelo = ActaParalelo.objects.get(pk=id)
                    if paralelo.inicio and paralelo.fin:
                        data['weeks'] = weeks_between(paralelo.inicio, paralelo.fin)
                        data['horarios'] = horarios = HorarioClases.objects.filter(actaparalelo=id, status=True)
                        data['dias'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sábado'], [7, 'Domingo']]
                        # data['mes'] = nombre_mes(paralelo.inicio.month)
                        data['lista_turnos'] = horarios.values_list('id', flat=True)
                        data['pk_cv'] = request.GET.get('pk_cv')
                        return render(request, "adm_postulacion/horarios.html", data)
                    else:
                        return HttpResponseRedirect(f'/adm_postulacion?action=paralelos&id={paralelo.acta.id}')
                except Exception as ex:
                    pass

            elif action == 'horarioconvocatoria':
                try:
                    data['title'] = u"Gestión de horarios"
                    id = request.GET.get('idcv', 0)
                    if id == 0:
                        raise NameError("Parametro no encontrado")

                    eConvocatoria = Convocatoria.objects.get(pk=id)
                    data['eConvocatoria'] = eConvocatoria
                    if eConvocatoria.iniciohorario and eConvocatoria.finhorario:
                        data['weeks'] = weeks_between(eConvocatoria.iniciohorario, eConvocatoria.finhorario)
                        data['horarios'] = horarios = HorarioPlanificacionConvocatoria.objects.filter(convocatoria=eConvocatoria.id, status=True)
                        data['dias'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sábado'], [7, 'Domingo']]
                        # data['mes'] = nombre_mes(paralelo.inicio.month)
                        data['lista_turnos'] = horarios.values_list('id', flat=True)
                        return render(request, "adm_postulacion/convocatoria/horario.html", data)
                    else:
                        return HttpResponseRedirect(f'/adm_postulacion?action=listadoconvocatorias&idm={encrypt(eConvocatoria.asignaturamalla.malla_id)}&idc={encrypt(eConvocatoria.asignaturamalla.malla.carrera_id)}&idp={encrypt(eConvocatoria.periodo_id)}')
                except Exception as ex:
                    pass

            elif action == 'tipo':
                try:
                    data['title'] = u"Tipos de personal"
                    data['id'] = acta_pk = request.GET.get('id', None)
                    data['tipos'] = TipoPersonal.objects.filter(status=True)
                    return render(request, "adm_postulacion/tipopersonal.html", data)
                except Exception as ex:
                    pass

            elif action == 'edittipo':
                try:
                    data['id'] = pk = request.GET.get('id')
                    horario = TipoPersonal.objects.get(pk=int(encrypt(pk)))
                    f = TipoPersonalForm(initial=model_to_dict(horario))
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addtipo':
                try:
                    f = TipoPersonalForm()
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'mostrar_historial_convocatoria':
                try:
                    pk = request.GET.get('id', 0)
                    if pk == 0:
                        raise NameError("Parametro no encontrado")

                    eConvocatoria = Convocatoria.objects.get(pk=pk)
                    eHistorialConvocatoria = HistorialConvocatoria.objects.filter(status=True,
                                                                                  convocatoria=eConvocatoria)

                    data['eHistorialConvocatoria'] = eHistorialConvocatoria
                    template = get_template('adm_postulacion/modal/historial_convocatoria.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addhorario':
                try:
                    data['id'] = actaparalelo_pk = request.GET.get('id')
                    fecha = datetime.strptime(request.GET['dia'], '%Y-%m-%d').date() if request.GET.get('dia') else None
                    model = HorarioClases.objects.filter(actaparalelo_id=actaparalelo_pk, status=True).first()
                    f = HorarioClasesForm(initial={'dia':fecha.weekday() + 1, 'inicio':fecha, 'fin':fecha})
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addhorarioconvocatoria':
                try:
                    data['id'] = id = request.GET.get('id')
                    fecha = datetime.strptime(request.GET['dia'], '%Y-%m-%d').date() if request.GET.get('dia') else None
                    model = HorarioPlanificacionConvocatoria.objects.filter(convocatoria_id=id, status=True).first()
                    f = HorarioClasesForm(initial={'dia':fecha.weekday() + 1, 'inicio':fecha, 'fin':fecha})
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edithorario':
                try:
                    data['id'] = pk = request.GET.get('id')
                    horario = HorarioClases.objects.get(pk=pk)
                    f = HorarioClasesForm(initial=model_to_dict(horario))
                    f.fields['turno'].initial = horario.turno.all()
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edithorarioconvocatoria':
                try:
                    data['id'] = pk = request.GET.get('id')
                    horario = HorarioPlanificacionConvocatoria.objects.get(pk=pk)
                    f = HorarioClasesForm(initial=model_to_dict(horario))
                    f.fields['turno'].initial = horario.turno.all()
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'listarequisitosconvocatoria':
                try:
                    data['title'] = u'Listado de Requisitos Convocatoria'
                    data['idmalla'] = int(encrypt(request.GET['idmalla']))
                    data['convocatoria'] = convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    url_vars = f'&action={action}&id={request.GET["id"]}&idmalla={request.GET["idmalla"]}'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        url_vars += f'&s={search}'
                        ss = search.split(' ')
                        if len(ss) == 1:
                            listarequisitosconvocatoria = convocatoria.requisitosconvocatoria_set.filter(Q(requisito__nombre__icontains=search) | Q(requisito__observacion__icontains=search)).order_by('requisito__nombre').order_by('requisito__nombre')
                        else:
                            listarequisitosconvocatoria = convocatoria.requisitosconvocatoria_set.filter((Q(requisito__nombre__icontains=ss[0]) & Q(requisito__nombre__icontains=ss[1])) | (Q(requisito__observacion__icontains=ss[0]) & Q(requisito__observacion__icontains=ss[1]))).order_by('requisito__nombre').order_by('requisito__nombre')
                    else:
                        listarequisitosconvocatoria = convocatoria.requisitosconvocatoria_set.filter(status=True).order_by('requisito__nombre')

                    paging = MiPaginador(listarequisitosconvocatoria, 15)
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
                    data['listarequisitosconvocatoria'] = page.object_list
                    data['s'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['url_vars'] = url_vars
                    return render(request, "adm_postulacion/listarequisitosconvocatoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'listainscritosconvocatoria':
                try:
                    data['title'] = u'Listado Inscritos Convocatoria'
                    data['malla'] = Malla.objects.get(pk=int(encrypt(request.GET['idmalla'])))
                    data['idmalla'] = int(encrypt(request.GET['idmalla']))
                    data['convocatoria'] = convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['total_requisitos_general'] = RequisitoGenerales.objects.filter(status=True).count()
                    data['total_requisitos_convocatoria'] = convocatoria.total_requisitos_convocatoria()
                    if 'tipoestado' in request.GET:
                        data['tipoestado'] = int(request.GET['tipoestado'])
                        listainscritosconvocatoria = convocatoria.inscripcionconvocatoria_set.filter(estado=request.GET['tipoestado'], status=True)
                    else:
                        data['tipoestado'] = 1
                        listainscritosconvocatoria = convocatoria.inscripcionconvocatoria_set.filter(estado=1, status=True)
                    totalinscritos = listainscritosconvocatoria.values('id').count()
                    data['total_inscritos'] = totalinscritos
                    data['estados'] = ESTADO_REVISION
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            listainscritosconvocatoria = convocatoria.inscripcionconvocatoria_set.filter \
                                (Q(postulante__persona__nombres__icontains=search) |
                                 Q(postulante__persona__apellido1__icontains=search) |
                                 Q(postulante__persona__apellido2__icontains=search) |
                                 Q(postulante__persona__cedula__icontains=search)).order_by(
                                'postulante__persona__nombres')
                        else:
                            listainscritosconvocatoria = convocatoria.inscripcionconvocatoria_set.filter \
                                ((Q(postulante__persona__nombres__icontains=ss[0]) & Q(
                                    postulante__persona__nombres__icontains=ss[1])) |
                                 (Q(postulante__persona__apellido1__icontains=ss[0]) & Q(
                                     postulante__persona__apellido2__icontains=ss[1])) |
                                 (Q(postulante__persona__cedula__icontains=ss[0]) & Q(
                                     postulante__persona__cedula__icontains=ss[1])))
                    paging = MiPaginador(listainscritosconvocatoria, 15)
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
                    data['listainscritosconvocatoria'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_postulacion/listainscritosconvocatoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'descargarlistainscritosconvocatoria':
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
                    ws = wb.add_sheet('exp_xls_post_part')
                    # ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_inscritos' + random.randint(1, 10000).__str__() + '.xls'
                    row_num = 0
                    columns = [
                        (u"N.", 2000),
                        (u"CEDULA", 4000),
                        (u"APELLIDO 1", 6000),
                        (u"APELLIDO 2", 6000),
                        (u"NOMBRE", 6000),
                        (u"EMAIL", 6000),
                        (u"TELEFONO", 4000),
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listado = InscripcionConvocatoria.objects.filter(
                        convocatoria_id=int(encrypt(request.GET['idconvo'])), status=True).order_by('postulante__persona__apellido1', 'postulante__persona__apellido2')
                    row_num = 0
                    for lista in listado:
                        row_num += 1
                        campo2 = '-'
                        if lista.postulante.persona.cedula:
                            campo2 = lista.postulante.persona.cedula
                        else:
                            if lista.postulante.persona.pasaporte:
                                campo2 = lista.postulante.persona.pasaporte
                        campo3 = lista.postulante.persona.apellido1
                        campo4 = lista.postulante.persona.apellido2
                        campo5 = lista.postulante.persona.nombres
                        campo6 = lista.postulante.persona.email
                        campo7 = lista.postulante.persona.telefono
                        ws.write(row_num, 0, row_num, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'listainscritosconvocatoriarequisitos':
                try:
                    data['title'] = u'Listado Requisitos Postulante'
                    data['idmalla'] = int(encrypt(request.GET['idmalla']))
                    data['listarequisitogeneralpersona'] = RequisitoGeneralesPersona.objects.filter(status=True)
                    data['insconvocatoria'] = insconvocatoria = InscripcionConvocatoria.objects.get(
                        pk=int(encrypt(request.GET['idinsc'])))
                    data['listainscritosconvocatoriarequisitos'] = InscripcionConvocatoriaRequisitos.objects.filter(inscripcioninvitacion__inscripcion=insconvocatoria, status=True)
                    return render(request, "adm_postulacion/listainscritosconvocatoriarequisitos.html", data)
                except Exception as ex:
                    pass

            elif action == 'aprobarinscrito':
                try:
                    if 'id' in request.GET and request.GET['id']:
                        id = request.GET['id']
                        if len(id.split(',')) > 1:
                            data['id'] = id[:-1]
                            f = InscripcionConvocatoriaForm()
                            f.estados_revision_inscrito_por_comite()
                        else:

                            data['id'] = id
                            ic = InscripcionConvocatoria.objects.filter(pk=int(request.GET['id'])).order_by('-id').first()
                            f = InscripcionConvocatoriaForm(initial={'estado': ic.estado, 'observacioncon': ic.observacioncon}) if ic else ''

                            f.estados_revision_inscrito_por_comite()
                            f.add_class()
                        if 'id_paralelo' in request.GET and request.GET['id_paralelo']:
                            ic = InscripcionConvocatoria.objects.filter(pk=int(request.GET['id'])).order_by('-id').first()
                            f.add_class()
                            data['idp'] = int(request.GET['id_paralelo'])
                            ePersonalAContratar= PersonalAContratar.objects.filter(inscripcion=ic, actaparalelo_id = int(request.GET['id_paralelo']),status=True)
                            if ePersonalAContratar.exists():
                                if ePersonalAContratar.count() == 1:
                                    f.edit_personalcontratar(ePersonalAContratar.first().tipo_id)
                        else:
                            f.por_analista()
                            f.estados_revision_inscrito()
                            data["action"] ='aprobarinscritoanalista'


                    data['form2'] = f
                    template = get_template("adm_postulacion/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'aprobarinscrito_director_posgrado':
                try:
                    if 'id' in request.GET and request.GET['id']:
                        id = request.GET['id']
                        if len(id.split(',')) > 1:
                            data['id'] = id[:-1]
                            f = InscripcionConvocatoriaForm()
                            f.estados_revision_inscrito_por_comite()
                        else:

                            data['id'] = id
                            ic = InscripcionConvocatoria.objects.filter(pk=int(request.GET['id'])).order_by('-id').first()
                            f = InscripcionConvocatoriaForm(initial={'estado': ic.estado, 'observacioncon': ic.observacioncon}) if ic else ''

                            f.estados_revision_inscrito_por_comite()
                            f.add_class()
                        if 'id_paralelo' in request.GET and request.GET['id_paralelo']:
                            ic = InscripcionConvocatoria.objects.filter(pk=int(request.GET['id'])).order_by('-id').first()
                            f.add_class()
                            data['idp'] = int(request.GET['id_paralelo'])
                            ePersonalAContratar= PersonalAContratar.objects.filter(inscripcion=ic, actaparalelo_id = int(request.GET['id_paralelo']),status=True)
                            if ePersonalAContratar.exists():
                                if ePersonalAContratar.count() == 1:
                                    f.edit_personalcontratar(ePersonalAContratar.first().tipo_id)
                        else:
                            f.por_analista()
                            f.estados_revision_inscrito()
                            data["action"] ='aprobarinscritoanalista'
                        data["eInscripcionPostulante"] =ic


                    data['form2'] = f
                    template = get_template("comiteacademico/comite/votaciondirectorform.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editdatospersonales':
                try:
                    data['inscripcion'] = ip = InscripcionPostulante.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form2'] = DatoPersonalForm(initial=model_to_dict(ip.persona))
                    data['id'] = ip.pk
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": str(ex)})

            elif action == 'agregardatosextra':
                try:
                    data['inscripcion'] = ip = InscripcionConvocatoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form2'] = DatoPersonalExtraForm()
                    data['id'] = ip.pk
                    data['action'] = 'agregardatosextra'
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": str(ex)})

            elif action == 'validarrequisito':
                try:
                    data['inscripcion'] = InscripcionConvocatoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template('adm_postulacion/modal/validardocumento.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            elif action == 'validarrequisitogeneral':
                try:
                    data['listadorequisitosgenerales'] = RequisitoGenerales.objects.filter(status=True)
                    data['inscripcion'] = InscripcionConvocatoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template('adm_postulacion/modal/validardocumentogeneral.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            elif action == 'validarrequisitopostulacion':
                try:
                    data['inscripcion'] = eInscripcionInvitacion= InscripcionInvitacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['estadofinalrequistos'] =  estados_permitidos = [estado for estado in ESTADO_REVISION if estado[0] in (1, 2, 4,5,6,7)]
                    data['horario_pregrado'] =False
                    if eInscripcionInvitacion.get_horario_pregrado(periodo):
                        data['horario_pregrado'] = eInscripcionInvitacion.get_horario_pregrado(periodo)

                    template = get_template('adm_postulacion/modal/validardocumento.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            elif action == 'subirrequisitomanual':
                try:
                    data['title'] = u"Requisitos de Contratación"
                    data['invitacion'] = invitacion = InscripcionInvitacion.objects.get(pk=request.GET.get('id'))
                    data['personaposgrado'] = invitacion.inscripcion.postulante.persona
                    data['listadorequisitos'] = RequisitosConvocatoria.objects.filter(convocatoria=invitacion.inscripcion.convocatoria, requisito__status=True, status=True).order_by('-requisito__id')
                    por_contratacion = False
                    if  'tipo' in request.GET:
                        por_contratacion= True
                    data['por_contratacion'] =por_contratacion
                    return render(request, 'adm_contratacion/subirrequisitomanual.html', data)
                except Exception as ex:
                    pass

            elif action == 'cargararchivo':
                try:
                    data['title'] = u'Evidencias de requisitos de maestría'
                    data['id'] = request.GET.get('id')
                    data['idevidencia'] = request.GET['idevidencia']
                    requisito = RequisitosConvocatoria.objects.get(pk=int(request.GET['idevidencia']), status=True)
                    form = RequisitosConvocatoriaInscripcionForm()
                    form.del_observacion()
                    data['form2'] = form
                    data['pk'] = request.GET.get('pk')
                    template = get_template("postu_requisitos/modal/formmodal_b5.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content,
                                         "nombre": "SUBIR DOCUMENTO DE REQUISITO " + str(requisito.requisito.nombre)})
                except Exception as ex:
                    pass

            elif action == 'seguimiento':
                try:
                    data['title'] = u'Evidencias de requisitos de maestría'
                    # data['id'] = request.GET['id']
                    data['id'] = 4

                    template = get_template("adm_postulacion/seguimiento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, "nombre": "SUBIR DOCUMENTO DE REQUISITO "})
                except Exception as ex:
                    pass

            elif action == 'verdatospersonalescomite':
                try:
                    from sga.models import ArticuloInvestigacion
                    ic = None
                    eInscripcionConvocatoria = InscripcionConvocatoria.objects.filter(pk=int(encrypt(request.GET['id'])))
                    if eInscripcionConvocatoria.exists():
                        ic = eInscripcionConvocatoria.first()
                    data['articulos'] = ArticuloInvestigacion.objects.select_related().filter((Q(
                        participantesarticulos__profesor__persona=ic.postulante.persona) | Q(
                        participantesarticulos__administrativo__persona=ic.postulante.persona) | Q(
                        participantesarticulos__inscripcion__persona=ic.postulante.persona)),
                                                                                              status=True,
                                                                                              aprobado=True,
                                                                                              participantesarticulos__status=True).order_by(
                        '-fechapublicacion')

                    data['eInscripcionConvocatoria'] = ic
                    data['inscripcion'] = ic.postulante
                    data['niveltituloposgrado'] = NivelTitulacion.objects.filter(pk__in=[3, 4], status=True).order_by('-rango')
                    template = get_template('adm_postulacion/modal/verdatospersonales.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            elif action == 'verdatospersonales':
                try:
                    from sga.models import ArticuloInvestigacion
                    data['eInscripcionConvocatoria'] = eInscripcionConvocatoria = InscripcionConvocatoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['inscripcion'] = inscripcion = eInscripcionConvocatoria.postulante
                    data['niveltituloposgrado'] = NivelTitulacion.objects.filter(pk__in=[3, 4], status=True).order_by(
                        '-rango')
                    data['articulos'] = ArticuloInvestigacion.objects.select_related().filter((Q(
                        participantesarticulos__profesor__persona=inscripcion.persona) | Q(
                        participantesarticulos__administrativo__persona=inscripcion.persona) | Q(
                        participantesarticulos__inscripcion__persona=inscripcion.persona)),
                        status=True, aprobado=True,
                        participantesarticulos__status=True).order_by('-fechapublicacion')
                    template = get_template('adm_postulacion/modal/verdatospersonales.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            elif action == 'evidenciasarticulo':
                try:
                    from sga.models import ArticuloInvestigacion, Evidencia
                    data['articulo'] = articulos = ArticuloInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['evidencias'] = Evidencia.objects.filter(status=True, matrizevidencia_id=3)

                    template = get_template("th_hojavida/detallearticulo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "message": u"Error al obtener los datos. [%s]" % msg})

            elif action == 'ver_postulaciones_realizadas':
                try:
                    eInscripcionPostulante = InscripcionPostulante.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['eInscripcionConvocatorias'] = eInscripcionPostulante.get_convocatorias_que_postulo()
                    template = get_template('adm_postulacion/modal/verpostulaciones.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            elif action == 'listcampoamplio':
                try:
                    listPerfilRequeridoPacs = ePerfilRequeridoPac_id  = request.GET.get('ePerfilRequeridoPac')
                    if len(ePerfilRequeridoPac_id) > 1:
                        listPerfilRequeridoPacs = ePerfilRequeridoPac_id.split(',')
                        ePerfilRequeridoPacs = PerfilRequeridoPac.objects.filter(status=True, pk__in =listPerfilRequeridoPacs)
                        campo_amplio_set = set()
                        for ePerfilRequeridoPac in ePerfilRequeridoPacs:
                            campoamplios = ePerfilRequeridoPac.titulacion.campoamplio.filter(status=True, tipo=1)
                            campo_amplio_set.update(campoamplios.values_list('id', flat=True))

                        unique_ids_campo_amplio_set = set(campo_amplio_set)

                        if not len(unique_ids_campo_amplio_set) != len(campo_amplio_set):
                            id_asignado_campo_amplio = unique_ids_campo_amplio_set

                    querybase = AreaConocimientoTitulacion.objects.filter(status=True, pk__in=id_asignado_campo_amplio).order_by('codigo')

                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'listcampoespecifico':
                try:
                    campoamplio = request.GET.get('campoamplio')
                    listPerfilRequeridoPacs = ePerfilRequeridoPac_id = request.GET.get('ePerfilRequeridoPac')
                    if len(ePerfilRequeridoPac_id) > 1:
                        listPerfilRequeridoPacs = ePerfilRequeridoPac_id.split(',')
                        ePerfilRequeridoPacs = PerfilRequeridoPac.objects.filter(status=True,pk__in=listPerfilRequeridoPacs)
                        campo_especifico_set = set()
                        for ePerfilRequeridoPac in ePerfilRequeridoPacs:
                            campoespecificos = ePerfilRequeridoPac.titulacion.campoespecifico.filter(status=True,tipo=1)
                            campo_especifico_set.update(campoespecificos.values_list('id', flat=True))
                        unique_ids_campo_especifico_set = set(campo_especifico_set)
                        if not len(unique_ids_campo_especifico_set) != len(campo_especifico_set):
                            id_asignado_campo_especifico = unique_ids_campo_especifico_set

                    listcampoamplio = campoamplio
                    if len(campoamplio) > 1:
                        listcampoamplio = campoamplio.split(',')
                    querybase = SubAreaConocimientoTitulacion.objects.filter(status=True, areaconocimiento__in=listcampoamplio, pk__in = id_asignado_campo_especifico).order_by('codigo')
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "idca": x.areaconocimiento.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'listcampodetallado':
                try:
                    listcampoespecifico = campoespecifico= request.GET.get('campoespecifico')
                    listPerfilRequeridoPacs = ePerfilRequeridoPac_id = request.GET.get('ePerfilRequeridoPac')
                    if len(ePerfilRequeridoPac_id) > 1:
                        listPerfilRequeridoPacs = ePerfilRequeridoPac_id.split(',')
                        ePerfilRequeridoPacs = PerfilRequeridoPac.objects.filter(status=True,pk__in=listPerfilRequeridoPacs)
                        campo_detallado_set = set()
                        for ePerfilRequeridoPac in ePerfilRequeridoPacs:
                            campodetallados = ePerfilRequeridoPac.titulacion.campodetallado.filter(status=True, tipo=1)
                            campo_detallado_set.update(campodetallados.values_list('id', flat=True))

                        unique_ids_campo_detallado_set = set(campo_detallado_set)

                        if not len(unique_ids_campo_detallado_set) != len(campo_detallado_set):
                            id_asignado_campo_detallado = unique_ids_campo_detallado_set

                    if len(campoespecifico) > 1:
                        listcampoespecifico = campoespecifico.split(',')
                    querybase = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, areaconocimiento__in=listcampoespecifico,pk__in=id_asignado_campo_detallado).order_by('codigo')
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'editconvocatoria':
                try:
                    cv = Convocatoria.objects.get(pk=int(encrypt(request.GET['idcv'])))
                    data['id'] = cv.id
                    data['idc'] = cv.carrera_id
                    data['idp'] = cv.periodo_id
                    existe_perfil_requerido = None

                    f = ConvocatoriaForm(initial=model_to_dict(cv))
                    if cv.tipo ==1:
                        data['idasigmalla'] = cv.asignaturamalla.asignatura_id
                        data['idm'] = cv.asignaturamalla.malla.id
                        f.set_perfilrequerido(cv.asignaturamalla.asignatura_id, list(cv.perfilrequeridopac.values_list('id', flat=True)), cv.carrera_id)
                        f.quitar_campos_tipo_convocatoria_normal()
                        existe_perfil_requerido = f.fields['perfilrequeridopac'].queryset
                        title =  u"%s" % cv.nombre
                    else:
                        title = u"Convocatoria para docente invitado"
                        f.fields['periodo'].initial = cv.periodo_id
                        f.quitar_campos_por_docente_invitado()
                        f.requeridos()
                    data['form'] = f
                    data['title'] = title
                    data['existe_perfil_requerido'] = existe_perfil_requerido

                    data['convocatoria'] = cv
                    return render(request, "adm_postulacion/modal/addconvocatoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'personalapoyomaestria':
                try:
                    puede_realizar_accion(request, 'postulaciondip.puede_gestionar_personal_apoyo')
                    data['title'] = u"Personal de Apoyo Maestría"
                    s, r, url_vars = request.GET.get('s', ''), int(request.GET.get('r', 0)), ""
                    filtro = Q(status=True)

                    if r:
                        data['r'] = r
                        url_vars += f'&r={r}'
                        filtro &= Q(personalapoyo__rol__id=r)

                    if s:
                        data['s'] = s
                        url_vars += f'&s={s}'
                        filtro &= (Q(carrera__nombre__icontains=s))

                    data['listaPersonalApoyoMaestria'] = PersonalApoyoMaestria.objects.filter(filtro).order_by('personalapoyo__persona__apellido1', 'personalapoyo__persona__apellido2')
                    data['personal'] = PersonalApoyo.objects.filter(pk__in = PersonalApoyoMaestria.objects.filter(filtro).order_by('personalapoyo__persona__apellido1', 'personalapoyo__persona__apellido2').values_list('personalapoyo', flat=True).distinct())
                    data['url_vars'] = url_vars
                    data['rt'] = int(request.GET.get('rt', 1))
                    return render(request, "adm_postulacion/personalapoyo.html", data)
                except Exception as ex:
                    pass

            elif action == 'confpersonalapoyo':
                try:
                    data['title'] = u"Configuración de personas y roles"
                    s = int(request.GET.get('rt', 1))
                    data['rt'] = s
                    if s == 1:
                        data['listaRoles'] = RolPersonalApoyo.objects.filter(status=True)
                    else:
                        data['listaPersonalApoyo'] = PersonalApoyo.objects.filter(status=True)
                    return render(request, "adm_postulacion/configuracionpersonalapoyo.html", data)
                except Exception as ex:
                    pass

            elif action == 'get-integrante-comite':
                return JsonResponse({'result': True, 'data': [(u"%s" % x.persona, u"%s" % x.cargo) for x in IntegranteComiteAcademicoPosgrado.objects.filter(comite_id=request.GET['pk'], status=True)]})

            elif action == 'addpersonalapoyo':
                try:
                    data['form2'] = PersonalApoyoForm()
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'editpersonalapoyo':
                try:
                    pa = PersonalApoyo.objects.get(pk=int(encrypt(request.GET['id'])))
                    f = PersonalApoyoForm(initial=model_to_dict(pa))
                    f.edit(pa.persona.id)
                    data['form2'] = f
                    data['id'] = pa.pk
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'editpersonalapoyomaestria':
                try:
                    pa = PersonalApoyoMaestria.objects.get(pk=int(encrypt(request.GET['id'])))
                    f = PersonalApoyoMaestriaForm(initial=model_to_dict(pa))
                    f.edit(pa.periodo.values_list('id', flat=True), pa.carrera_id)
                    data['form2'] = f
                    data['id'] = pa.pk
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'subir_manual_informe_contratacion':
                try:
                    f = RequisitosInscripcionForm()
                    data['form2'] = f
                    data['id'] = request.GET.get('id','0')

                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})



            elif action == 'load_fechas_contrato':
                try:
                    fecha_incio = None
                    fecha_fin = None
                    ePersonalApoyo = PersonalApoyo.objects.get(pk= int(request.GET.get('id',0)))
                    contrato = ePersonalApoyo.persona.contratodip_set.filter(Q(status=True)).order_by('-id')
                    if contrato.exists():
                        fecha_incio = contrato.first().fechainicio
                        fecha_fin = contrato.first().fechafin

                    return JsonResponse({"result": True,"fecha_inicio":fecha_incio ,"fecha_fin": fecha_fin})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'load_fecha_inicio_fin_horario_convocatoria':
                try:
                    fecha_incio = None
                    fecha_fin = None
                    eConvocatoria = Convocatoria.objects.get(pk= int(request.GET.get('id',0)))
                    if eConvocatoria.iniciohorario:
                        fecha_incio = eConvocatoria.iniciohorario
                    if eConvocatoria.finhorario:
                        fecha_fin = eConvocatoria.finhorario

                    return JsonResponse({"result": True,"inicio":fecha_incio ,"fin": fecha_fin})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'load_mensaje_predeterminado_por_estado':
                try:
                    mensaje_personalizado = ''
                    sms = ''

                    id_estado = int(request.GET.get('id',0))
                    if id_estado == 0:
                        raise NameError("Parametro no encontrado")

                    id_postulante = int(request.GET.get('id_postulante', 0))
                    if id_postulante == 0:
                        raise NameError("Parametro no encontrado id_postulante")
                    eInscripcionConvocatoria = InscripcionConvocatoria.objects.get(pk=id_postulante)

                    maestria =eInscripcionConvocatoria.convocatoria.carrera
                    cohorte = eInscripcionConvocatoria.convocatoria.periodo.numero_cohorte_romano() + " " +eInscripcionConvocatoria.convocatoria.periodo.anio.__str__()
                    tipodocente = eInscripcionConvocatoria.convocatoria.tipodocente
                    modulo = eInscripcionConvocatoria.convocatoria.asignaturamalla.asignatura
                    paralelo = "-"

                    if id_estado == 1:
                        sms = ''
                    elif id_estado == 2:
                         sms = MensajePredeterminado.objects.get(pk= 1).descripcion
                    elif id_estado == 3:
                         sms = MensajePredeterminado.objects.get(pk= 2).descripcion
                    elif id_estado == 11:
                         sms = MensajePredeterminado.objects.get(pk= 3).descripcion
                    elif id_estado == 12:
                         sms = MensajePredeterminado.objects.get(pk= 4).descripcion
                    else:
                        sms= ''

                    mensaje_personalizado = sms.format(maestria=maestria, cohorte=cohorte, modulo=modulo, paralelo=paralelo,tipodocente = tipodocente)

                    return JsonResponse({"result": True,"sms":mensaje_personalizado})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'verificar_banco_elegibles_en_modulo':
                try:
                    url = ''
                    existe =False
                    ida = int(encrypt(request.GET.get('id',0)))
                    idc = int(encrypt(request.GET.get('idc',0)))
                    eAsignaturaMalla = AsignaturaMalla.objects.get(pk=ida)
                    eInscripcionPostulante = InscripcionPostulante.objects.filter(inscripcionconvocatoria__estado=11,
                                                         inscripcionconvocatoria__convocatoria__asignaturamalla__asignatura_id=eAsignaturaMalla.asignatura_id,
                                                         inscripcionconvocatoria__convocatoria__carrera__id=idc
                                                         ).order_by('persona__apellido1', 'persona__apellido2').distinct()
                    if eInscripcionPostulante.exists():
                        existe = True
                        url = f'/adm_postulacion?action=listadoinscritos&elegible=1&idc={idc}&ida={eAsignaturaMalla.asignatura_id}'


                    return JsonResponse({"result": True,"existe":existe, "url":url})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'addpersonalapoyomaestria':
                try:
                    data['form2'] = PersonalApoyoMaestriaForm()
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'comite-academico':
                try:
                    data['title'] = u"Comite Académico Posgrado"
                    data['comiteacademico'] = ComiteAcademicoPosgrado.objects.filter(status=True)
                    idcv = request.GET.get('idcv', None)
                    data['back'] = f"?action=listadoactas"
                    return render(request, 'adm_postulacion/comiteacademico.html', data)
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'integrante-comite-academico':
                try:
                    data['title'] = u"Integrante Comite Académico Posgrado"
                    filtro = Q(status=True)
                    if pk := request.GET.get('pk', 0): filtro &= Q(comite_id=pk)
                    data['comite'] = comite = ComiteAcademicoPosgrado.objects.filter(pk=pk).first()
                    data['integrantecomiteacademico'] = IntegranteComiteAcademicoPosgrado.objects.filter(filtro)
                    eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=int(request.GET.get('idacta',1)))
                    if eActaSeleccionDocente.tipo_formato_acta == 1:
                        data['return'] = f"?action=actaseleccion&id={request.GET['idacta']}" if request.GET.get('idacta', None) else f"?action=comite-academico"
                    else:
                        data['return'] = f"?action=actaseleccion_invitado&id={request.GET['idacta']}" if request.GET.get('idacta', None) else f"?action=comite-academico"

                    return render(request, 'adm_postulacion/integrantecomiteacademico.html', data)
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'addcomiteacademico':
                try:
                    from pdip.models import PerfilPuestoDip
                    form = ComiteAcademicoPosgradoForm()
                    data['form2'] = form
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": 'ok', 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'editcomiteacademico':
                try:
                    model = ComiteAcademicoPosgrado.objects.get(pk=encrypt(request.GET['id']))
                    data['form2'] = ComiteAcademicoPosgradoForm(initial=model_to_dict(model))
                    data['id'] = model.id
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": 'ok', 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'addintegrantecomiteacademico':
                try:
                    f = IntegranteComiteAcademicoPosgradoForm()
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": 'ok', 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'editintegrantecomiteacademico':
                try:
                    ica = IntegranteComiteAcademicoPosgrado.objects.get(pk=encrypt(request.GET['id']))
                    f = IntegranteComiteAcademicoPosgradoForm(initial=model_to_dict(ica))
                    f.edit(ica.persona.id)
                    data['form2'] = f
                    data['id'] = ica.id
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": 'ok', 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'buscarperiodoporcarrera':
                try:
                    mallas = Malla.objects.values_list('id').filter(carrera_id=request.GET['id'], vigente=True, status=True)
                    listaPeriodosMateria = Materia.objects.values_list('nivel__periodo_id', flat=True).filter(asignaturamalla__malla__in=mallas, asignaturamalla__malla__status=True, asignaturamalla__status=True, status=True)
                    return JsonResponse({"result": True, 'data': [{'id':x.id, 'value': f"{x} - {x.clasificacion}"} for x in Periodo.objects.filter(pk__in=listaPeriodosMateria, clasificacion=2)]})
                except Exception as ex:
                    pass

            elif action == 'addrolpersonalapoyo':
                try:
                    data['form2'] = RolPersonalApoyoForm()
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'editrolpersonalapoyo':
                try:
                    rol = RolPersonalApoyo.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form2'] = RolPersonalApoyoForm(initial=model_to_dict(rol))
                    data['id'] = rol.id
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'buscarperfilrequeridopc':
                try:
                    q = request.GET['q'].upper().strip()
                    querybase = PerfilRequeridoPac.objects.filter(personalacademico__asignaturaimpartir__asignatura_id=int(request.GET['a']), titulacion__titulo__status=True, status=True)
                    per = querybase.filter((Q(titulacion__titulo__nombre__icontains=q) | Q(titulacion__titulo__abreviatura__icontains=q))).distinct()[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.titulacion.titulo.abreviatura, x.titulacion.titulo.nombre)} for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'buscarpersona':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    filtro = Q(usuario__isnull=False,status=True)
                    if len(s) == 1:
                        filtro &= ((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) | Q(apellido2__icontains=q) | Q(cedula__contains=q)))
                    elif len(s) == 2:
                        filtro &= ((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                   (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                   (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1])))
                    else:
                        filtro &= ((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) |
                                   (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2])))

                    per = Persona.objects.filter(filtro).exclude(cedula='').order_by('apellido1', 'apellido2', 'nombres').distinct()[:15]
                    return JsonResponse({"result": "ok", "results": [{"id": x.id, "name": "%s %s" % (f"<img src='{x.get_foto()}' width='25' height='25' style='border-radius: 20%;' alt='...'>", x.nombre_completo_inverso())} for x in per]})
                except Exception as ex:
                    pass

            elif action == 'buscaradministrativo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Administrativo.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                      | Q(persona__apellido2__icontains=s[0])
                                                      | Q(persona__cedula__icontains=s[0])
                                                      | Q(persona__pasaporte__icontains=s[0])
                                                      | Q(persona__ruc__icontains=s[0]),
                                                      status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        personas = Administrativo.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                               & Q(persona__apellido2__icontains=s[1]),
                                                           status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso())} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cantidad_perfiles_cumplen':
                try:
                    listcampoamplio = ids_campoamplio = request.GET.getlist('ids_campoamplio[]')
                    listcampoespecifico  =ids_campoespecifico = request.GET.getlist('ids_campoespecifico[]')
                    listcampodetallado = ids_campodetallado = request.GET.getlist('ids_campodetallado[]')

                    # if len(ids_campoamplio) > 1:
                    #     listcampoamplio = ids_campoamplio.split(',')
                    #
                    # if len(ids_campoespecifico) > 1:
                    #     listcampoespecifico = ids_campoespecifico.split(',')
                    #
                    # if len(ids_campodetallado) > 1:
                    #     listcampodetallado = ids_campodetallado.split(',')

                    cumplen = titulados_acorde_al_campo_del_perfil_requerido(listcampoamplio,listcampoespecifico,listcampodetallado)

                    return JsonResponse({"result": "ok", "total":cumplen.count() })
                except Exception as ex:
                    pass

            elif action == 'addconvocatoria':
                try:
                    tipo = int(encrypt(request.GET.get('tipo', 'OPPQQRRSSTTUUVVWWXXX')))
                    f = ConvocatoriaForm()
                    if tipo == 1:
                        f.quitar_campos_tipo_convocatoria_normal()
                        am = AsignaturaMalla.objects.get(pk=int(encrypt(request.GET['id'])))
                        title = u"%s" % am.asignatura.nombre
                        data['idm'] = int(encrypt(request.GET['idm']))
                        data['idc'] = idc = int(encrypt(request.GET['idc']))
                        data['idp'] = idp = int(encrypt(request.GET['idp']))
                        f.set_perfilrequerido(am.asignatura.pk, None, idc)
                        f.fields['periodo'].initial = idp
                        data['existe_perfil_requerido'] = f.fields['perfilrequeridopac'].queryset
                        data['idasigmalla'] = am.pk
                        data['asignatura'] = am.asignatura
                    else:
                        title = u"Convocatoria para docente invitado"
                        f.fields['periodo'].initial = periodo.pk
                        f.fields.pop('campoamplio',None)
                        f.fields.pop('campoespecifico',None)
                        f.fields.pop('campodetallado',None)
                        f.requeridos()

                    data['title'] = title
                    f.initial_values(tipo)
                    data['form'] = f
                    data['tipo'] = tipo
                    return render(request, "adm_postulacion/modal/addconvocatoria.html", data)
                except Exception as ex:
                    pass
            # GET
            elif action == 'listarequisitogeneral':
                try:
                    data['title'] = u'Listado de Requisitos Generales'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            listarequisitogeneral = RequisitoGenerales.objects.filter(
                                Q(requisito__nombre__icontains=search) | Q(
                                    requisito__observacion__icontains=search)).order_by('requisito__nombre')
                        else:
                            listarequisitogeneral = RequisitoGenerales.objects.filter(
                                (Q(requisito__nombre__icontains=ss[0]) & Q(requisito__nombre__icontains=ss[1])) | (
                                        Q(requisito__observacion__icontains=ss[0]) & Q(
                                    requisito__observacion__icontains=ss[1]))).order_by('requisito__nombre')
                    else:
                        listarequisitogeneral = RequisitoGenerales.objects.filter(status=True).order_by(
                            'requisito__nombre')
                    paging = MiPaginador(listarequisitogeneral, 15)
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
                    data['listarequisitogeneral'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_postulacion/listarequisitogeneral.html", data)
                except Exception as ex:
                    pass
            # GET
            elif action == 'verlistadorequisitos':
                try:
                    lista = []
                    listageneral = RequisitoGenerales.objects.values_list('requisito_id', flat=True).filter(status=True)
                    listarequisitogeneral = Requisito.objects.filter(activo=True, status=True).exclude(
                        id__in=listageneral).order_by('nombre')
                    for lis in listarequisitogeneral:
                        lista.append([lis.id, lis.nombre, lis.observacion])
                    data = {"results": "ok", 'listarequisitogeneral': lista}
                    return JsonResponse(data)
                except Exception as ex:
                    pass
            # GET
            elif action == 'verlistadorequisitosconvocatoria':
                try:
                    convocatoria = int(encrypt(request.GET['idconvocatoria']))
                    listageneral = RequisitosConvocatoria.objects.values_list('requisito_id', flat=True).filter(convocatoria_id=convocatoria, status=True)
                    lrc = Requisito.objects.values_list('id', 'nombre', 'observacion').filter(activo=True, status=True).exclude(id__in=listageneral).order_by('nombre')
                    return JsonResponse({"results": "ok", 'listarequisitoconvocatoria': list(lrc)})
                except Exception as ex:
                    pass
            # GET
            elif action == 'listarequisito':
                try:
                    data['title'] = u'Listado de Requisitos Generales'
                    data['listarequisito'] = Requisito.objects.filter(status=True).order_by('nombre')
                    data['s'] = request.GET.get('s')
                    return render(request, "adm_postulacion/listarequisito.html", data)
                except Exception as ex:
                    pass
            # GET
            elif action == 'editrequisito':
                try:
                    data['title'] = u'Editar Requisito'
                    data['requisito'] = requisito = Requisito.objects.get(status=True, pk=int(encrypt(request.GET['id'])))
                    data['id'] = request.GET.get('id')
                    data['form2'] = RequisitoForm(initial={'nombre': requisito.nombre, 'observacion': requisito.observacion})
                    template = get_template("postu_requisitos/modal/formmodal_b5.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            # GET
            elif action == 'editopcional':
                try:
                    data['title'] = u'Editar Requisito'
                    eRequisitosConvocatoria = RequisitosConvocatoria.objects.get(status=True, pk=int(encrypt(request.GET['id'])))
                    data['form2'] = RequisitoUpdateOpcionalForm(initial ={'opcional':eRequisitosConvocatoria.opcional})
                    data['id'] = eRequisitosConvocatoria.pk
                    template = get_template("postu_requisitos/modal/formmodal_b5.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            # GET
            elif action == 'addrequisito':
                try:
                    form = RequisitoForm()
                    data['form2'] = form
                    data['redirect_path'] = request.path
                    template = get_template("postu_requisitos/modal/formmodal_b5.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addinscrito':
                try:
                    data['title'] = u'Registrar postulación'
                    hoy = datetime.now().date()
                    data['puedeinscribirse'] = True
                    return render(request, "adm_postulacion/addinscrito.html", data)
                except Exception as ex:
                    pass
            # GET
            elif action == 'delrequisitogenerales':
                try:
                    data['title'] = u'Eliminar requisito de maestría'
                    data['requisito'] = RequisitoGenerales.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_admision/delrequisitomaestria.html", data)
                except Exception as ex:
                    pass

            elif action == 'paralelos':
                try:
                    data['title'] = u"Paralelos"
                    data['id'] = acta_pk = request.GET.get('id', None)
                    data['acta'] = acta = ActaSeleccionDocente.objects.filter(pk=acta_pk, status=True).first()
                    data['paralelos'] = paralelos = ActaParalelo.objects.filter(acta=acta, status=True)
                    data['pk_cv'] = request.GET.get('pk_cv')
                    return render(request, "adm_postulacion/paralelos.html", data)
                except Exception as ex:
                    pass

            elif action == 'personal_a_contratar':
                try:
                    data['title'] = u"Personal a contratar"
                    data['id'] = acta_pk = request.GET.get('id', None)
                    data['acta'] = acta = ActaSeleccionDocente.objects.get(pk=acta_pk)
                    data['paralelos'] = paralelos = ActaParalelo.objects.filter(acta=acta, status=True)
                    return render(request, "actaselecciondocente/perfil_invitado.html", data)
                except Exception as ex:
                    pass

            elif action == 'addparalelo':
                try:
                    plazo = variable_valor('PLAZO_GENERAR_ACTA_SELECCION')
                    data['id'] = pk = request.GET.get('id', None)
                    f = ActaParaleloForm()
                    data['form2'] = f
                    data['alert'] = {'message':f"La fecha de inicio del módulo no puede ser menor a <b>{plazo if plazo else 'N'}</b> días de generar el acta."}
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})


                except Exception as ex:
                    pass

            elif action == 'addconvocatoriaperfil':
                try:
                    plazo = variable_valor('PLAZO_GENERAR_ACTA_SELECCION')
                    data['id'] = pk = request.GET.get('id', None)
                    f = ActaParaleloForm()
                    f.set_required_field('paralelo',False)
                    f.del_field('paralelo')
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editparalelo':
                try:
                    data['id'] = pk = request.GET.get('id', None)
                    model = ActaParalelo.objects.get(pk=pk)
                    f = ActaParaleloForm(initial=model_to_dict(model))
                    excluded = ActaParalelo.objects.values_list('paralelo_id', flat=True).filter(acta=model.acta, status=True).exclude(paralelo_id=model.paralelo.id)
                    f.fields['paralelo'].queryset = Paralelo.objects.filter(status=True).exclude(pk__in=excluded)
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editconvocatoriaperfil':
                try:
                    data['id'] = pk = request.GET.get('id', None)
                    model = ActaParalelo.objects.get(pk=pk)
                    f = ActaParaleloForm(initial=model_to_dict(model))
                    f.del_field('paralelo')
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'obtener_horario':
                try:
                    data['id'] = id = request.GET.get('id', None)
                    data['paralelo'] = paralelo = ActaParalelo.objects.get(pk=id)
                    data['weeks'] = weeks_between(paralelo.inicio, paralelo.fin)
                    data['horarios'] = horarios = HorarioClases.objects.filter(actaparalelo=id, status=True)
                    data['dias'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sábado'], [7, 'Domingo']]
                    data['lista_turnos'] = horarios.values_list('id', flat=True)
                    data['pk_cv'] = request.GET.get('pk_cv')
                    template = get_template('adm_postulacion/modal/horario.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    pass

            elif action == 'duplicar_horario':
                try:
                    id = request.GET.get('id', None)
                    eActaParalelo = ActaParalelo.objects.get(pk=id)
                    eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=eActaParalelo.acta.pk)
                    form = DuplicarHorarioForm()
                    form .buscar_paralelo(eActaSeleccionDocente.obtener_actas_paralelos_sin_horario())
                    data['form2'] = form
                    data['action'] = action
                    data['id'] = eActaParalelo.pk
                    template = get_template('adm_postulacion/modal/formModalDuplicar.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    pass

            elif action == 'addplanaccion':
                try:
                    data['id'] = pk = request.GET.get('id', None)
                    acta = ActaSeleccionDocente.objects.get(pk=pk)
                    f = PlanAccionForm()
                    f._init(acta.comite.pk)
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editplanaccion':
                try:
                    data['id'] = pk = request.GET.get('id', None)
                    plan = PlanAccion.objects.get(pk=pk)
                    f = PlanAccionForm(initial=model_to_dict(plan))
                    f._init(plan.acta.comite.pk)
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'personal':
                try:
                    data['title'] = u"Gestión del personal a contratar"
                    data['paralelo'] = paralelo = ActaParalelo.objects.get(pk=request.GET.get('id', None))
                    data['personal'] = PersonalAContratar.objects.filter(actaparalelo=paralelo, status=True)
                    total_principales_en_acta = PersonalAContratar.objects.filter(actaparalelo__acta=paralelo.acta, tipo_id=1, status=True)

                    total_vacantes = paralelo.acta.get_total_vacantes()
                    data['puede_adicionar_personal'] = total_principales_en_acta.count() < total_vacantes
                    data['total_principales_en_acta'] = total_principales_en_acta
                    data['maximo_principal_paralelo'] = total_vacantes - total_principales_en_acta.count()

                    data['convocatoria'] = Convocatoria.objects.filter(pk=request.GET.get('pk_cv')).first()
                    return render(request, 'adm_postulacion/personal.html', data)
                except Exception as ex:
                    pass

            elif action == 'personalinvitado':
                try:
                    data['title'] = u"Gestión del personal a contratar"
                    data['paralelo'] = paralelo = ActaParalelo.objects.get(pk=request.GET.get('id', None))
                    data['personal'] = PersonalAContratar.objects.filter(actaparalelo=paralelo, status=True)
                    total_principales_en_acta = PersonalAContratar.objects.filter(actaparalelo__acta=paralelo.acta, tipo_id=1, status=True)

                    total_vacantes = paralelo.acta.get_total_vacantes()
                    data['puede_adicionar_personal'] = total_principales_en_acta.count() < total_vacantes
                    data['total_principales_en_acta'] = total_principales_en_acta
                    data['maximo_principal_paralelo'] = total_vacantes - total_principales_en_acta.count()
                    return render(request, 'actaselecciondocente/personal_invitado.html', data)
                except Exception as ex:
                    pass

            elif action == 'addpersonal':
                try:
                    data['id'] = pk = request.GET.get('id', None)
                    model = ActaParalelo.objects.get(pk=pk)
                    f = PersonalAContratarForm()
                    f._init(convocatoria=model.convocatoria)
                    data['form2'] = f
                    data['alert'] = {'type': 'warning', 'message':u"Si la lista de postulantes se muestra vacía, quizá deba aprobarlo previamente. Para esto cierre esta ventana modal y de click en el botón <b>Listado de inscritos</b> "}
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addpersonalinvitado':
                try:
                    data['id'] = pk = request.GET.get('id', None)
                    model = ActaParalelo.objects.get(pk=pk)
                    f = PersonalAContratarForm()
                    f._init(convocatoria=model.convocatoria)
                    data['form2'] = f
                    data['alert'] = {'type': 'warning', 'message':u"Si la lista de postulantes se muestra vacía, quizá deba aprobarlo previamente. Para esto cierre esta ventana modal y de click en el botón <b>Listado de inscritos</b> "}
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addpersonalcomite':
                try:
                    data['id'] = id = request.GET.get('id', None)
                    data['action'] ='addpersonal'
                    data['inscrito_id'] = inscrito_id = request.GET.get('inscrito_id', None)
                    model = ActaParalelo.objects.get(pk=id)
                    f = PersonalAContratarForm()
                    f._init(convocatoria=model.convocatoria)
                    f.cargar_inscrito_seleccionado(pk=inscrito_id)
                    data['form2'] = f
                    data['alert'] = {'type': 'warning', 'message':u"Si la lista de postulantes se muestra vacía, quizá deba aprobarlo previamente. Para esto cierre esta ventana modal y de click en el botón <b>Listado de inscritos</b> "}
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addpersonalbancoelegible':
                try:
                    data['id'] = pk = request.GET.get('id', None)
                    model = ActaParalelo.objects.get(pk=pk)
                    f = PersonalAContratarForm()
                    f.cargar_banco_de_elegibles(carrera_id=model.convocatoria.carrera_id, asignatura_id =model.convocatoria.asignaturamalla.asignatura_id)
                    data['form2'] = f
                    data['action'] = 'addpersonal'
                    data['alert'] = {'type': 'warning', 'message':u"Si la lista de postulantes se muestra vacía, quizá deba aprobarlo previamente. Para esto cierre esta ventana modal y de click en el botón <b>Listado de inscritos</b> "}
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editpersonal':
                try:
                    data['id'] = pk = request.GET.get('id', None)
                    model = PersonalAContratar.objects.get(pk=pk)
                    f = PersonalAContratarForm(initial=model_to_dict(model))
                    f._init(convocatoria=model.inscripcion.convocatoria)
                    f.cargar_banco_elegible_editar(pk= model.inscripcion.pk,convocatoria=model.inscripcion.convocatoria)
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'asignar_observacion':
                try:
                    data['id'] = pk = request.GET.get('id', None)
                    model = PersonalAContratar.objects.get(pk=pk)
                    f = PersonalAContratarForm(initial=model_to_dict(model))
                    f.del_field('inscripcion')
                    f.del_field('tipo')
                    data['form2'] = f
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cerraracta':
                try:
                    acta = ActaSeleccionDocente.objects.get(pk=request.GET.get('id'))
                    if acta.cerrada:
                        acta.cerrada = False
                        acta.save(request)
                        return JsonResponse({"result": True})
                    else:
                        invitacion = InscripcionInvitacion.objects.filter(inscripcion__id__in=acta.get_ganador().values_list('inscripcion__id', flat=True), status=True)
                        data['id'] = acta.pk
                        postulantes = InscripcionConvocatoria.objects.filter(pk__in=acta.get_ganador().values_list('inscripcion_id', flat=True))
                        data['postulantes'] = postulantes
                        template = get_template('adm_postulacion/modal/cerraractaselecciondocente.html')
                        return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'evaluacionpreviacontratacion':
                try:
                    ePersonalAContratar = PersonalAContratar.objects.get(id=request.GET.get('id'))
                    f = InscripcionConvocatoriaForm()
                    f.fields['estado'].choices = ((1, u"PENDIENTE"), (2, 'REPROGRAMACIÓN ACADÉMICA'), (3, 'INICIAR PROCESO'))
                    f.fields['estado'].initial = ePersonalAContratar.estado
                    f.fields['observacioncon'].initial = ePersonalAContratar.observacion if ePersonalAContratar.observacion else ''
                    data['form2'] = f
                    data['id'] = ePersonalAContratar.pk
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cargar_requisito_personalcontratar':
                try:
                    pk = int(request.GET.get('id','0'))
                    if pk == 0 :
                        raise NameError("Parametro no encontrado")
                    eConfiguracionRequisitosPersonalContratar = ConfiguracionRequisitosPersonalContratar.objects.get(pk=pk)
                    form = RequisitosPersonalContratarForm()
                    data['form2'] = form
                    data['id'] = eConfiguracionRequisitosPersonalContratar.pk
                    template = get_template('adm_postulacion/modal/modalrequisito.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'actualizar_fecha_caducidad_requisito_personalcontratar':
                try:
                    pk = int(request.GET.get('id','0'))
                    if pk == 0 :
                        raise NameError("Parametro no encontrado")
                    eConfiguracionRequisitosPersonalContratar = ConfiguracionRequisitosPersonalContratar.objects.get(pk=pk)
                    form = RequisitosPersonalContratarForm()
                    form.del_field('archivo')
                    data['form2'] = form
                    data['id'] = eConfiguracionRequisitosPersonalContratar.pk
                    template = get_template('adm_postulacion/modal/modalrequisito.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'validar_requisito_personalcontratar_analista':
                try:
                    pk = int(request.GET.get('id','0'))
                    if pk == 0 :
                        raise NameError("Parametro no encontrado")
                    eConfiguracionRequisitosPersonalContratar = ConfiguracionRequisitosPersonalContratar.objects.get(pk=pk)
                    data['id']=eConfiguracionRequisitosPersonalContratar.pk
                    form = ValidarRequisitoPersonalContratarForm()
                    form.fields['estado'].choices = ((2, 'APROBADO'), (3,'RECHAZADO'))
                    data['form2'] = form
                    template = get_template('adm_postulacion/modal/modalrequisito.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'actualizar_requisito_revision_final':
                try:
                    pk = int(request.GET.get('id', '0'))
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eInscripcionConvocatoriaRequisitos = InscripcionConvocatoriaRequisitos.objects.get(pk=pk)
                    form = RequisitosPersonalContratarForm()
                    data['form2'] = form
                    data['id'] = eInscripcionConvocatoriaRequisitos.pk
                    template = get_template('adm_postulacion/modal/modalrequisito.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'abriracta':
                try:
                    acta = ActaSeleccionDocente.objects.filter(pk=request.GET.get('id', None)).first()
                    acta.cerrada=False
                except Exception as ex:
                    pass

            elif action == 'asignar_partida_presupuestaria':
                try:

                    template = get_template("adm_postulacion/modal/asignar_partida_presupuestaria.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addorganizadopor':
                try:
                    pk = request.GET.get('id', None)
                    eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=pk)
                    form = AdministrativoActaSeleccionDocenteForm()
                    data["id"] = eActaSeleccionDocente.pk
                    data['form2'] = form
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addconvocadopor':
                try:
                    pk = request.GET.get('id', None)
                    eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=pk)
                    form = AdministrativoActaSeleccionDocenteForm()
                    data["id"] = eActaSeleccionDocente.pk
                    data['form2'] = form
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editparainformeposgrado':
                try:
                    pk = request.GET.get('id', None)
                    eInformeContratacion = InformeContratacion.objects.get(pk=pk)
                    form = AdministrativoActaSeleccionDocenteForm(initial={
                        'administrativo':eInformeContratacion.para
                    })
                    data["id"] = eInformeContratacion.pk
                    data['form2'] = form
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editar_por_informe_posgrado':
                try:
                    pk = request.GET.get('id', None)
                    eInformeContratacion = InformeContratacion.objects.get(pk=pk)
                    form = AdministrativoActaSeleccionDocenteForm(initial={
                        'administrativo': eInformeContratacion.de
                    })
                    data["id"] = eInformeContratacion.pk
                    data['form2'] = form
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'asignaturas':
                try:
                    data['title'] = u'Asignaturas'
                    idm, idc, idp = request.GET.get('idm', ''), request.GET.get('idc', ''), request.GET.get('idp', '')
                    data['periodo'] = Periodo.objects.get(pk=int(encrypt(idp)))
                    data['idcarrera'] = idcarrera = int(encrypt(idc))
                    data['malla'] = malla = Malla.objects.get(pk=int(encrypt(idm)))
                    url_vars = f"&action={action}&idm={idm}&idc={idc}&idp={idp}"
                    filtro = Q(malla__id=int(encrypt(idm)), malla__carrera__id=idcarrera, asignatura__status=True,
                               status=True, malla__carrera__status=True)
                    if 's' in request.GET:
                        data['s'] = search = request.GET['s']
                        url_vars += '&s=' + search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro &= Q(asignatura__nombre__icontains=search)
                        else:
                            filtro &= (Q(asignatura__nombre__icontains=ss[0]) & Q(asignatura__nombre__icontains=ss[1]))

                    paging = MiPaginador(malla.asignaturamalla_set.filter(filtro).order_by('asignatura__nombre'), 15)
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
                    data['asignaturas'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "adm_planificacion/asignaturas_view.html", data)
                except Exception as ex:
                    pass

            elif action == 'paralelos_planificacion':
                try:
                    data['title'] = u'Paralelos'
                    url_vars = '&action=paralelos_planificacion'
                    pk = request.GET.get('id', '0')
                    idp = request.GET.get('idp', '0')
                    filtro = None
                    url_vars += '&id=' + pk
                    url_vars += '&idp=' + idp
                    eAsignaturaMalla = AsignaturaMalla.objects.get(pk=pk)
                    data['eAsignaturaMalla'] = eAsignaturaMalla
                    data['idm'] = eAsignaturaMalla.malla.pk
                    data['idc'] = eAsignaturaMalla.malla.carrera.pk
                    data['idp'] = idp

                    ePlanificacionMaterias = PlanificacionMateria.objects.filter(status=True,
                                                                                 materia__asignaturamalla=eAsignaturaMalla)

                    paging = MiPaginador(ePlanificacionMaterias, 15)
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
                    data['planificacionparalelos'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "adm_planificacion/planificacion_paralelos_view.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalle_planificacion':
                id = request.GET.get('id', 0)
                ePlanificacionMateria = PlanificacionMateria.objects.get(pk=id)
                data['ePlanificacionMateria'] = ePlanificacionMateria
                template = get_template('adm_planificacion/modal/detallePlanificacion.html')
                return JsonResponse({"result": True, 'data': template.render(data)})

            elif action == 'realizar_convocatoria':
                try:
                    id = request.GET.get('id', 0)
                    ePlanificacionMateria = PlanificacionMateria.objects.get(pk=id)
                    tipo = 1
                    # tipo = int(encrypt(request.GET.get('tipo', 'OPPQQRRSSTTUUVVWWXXX')))
                    f = ConvocatoriaForm()
                    f.fields['tipodocente'].queryset = ePlanificacionMateria.get_tipo_docente_requiere()
                    f.fields['tipodocente'].initial = ePlanificacionMateria.get_tipo_docente_requiere().first().pk
                    if tipo == 1:
                        am = ePlanificacionMateria.materia.asignaturamalla
                        title = u"%s" % am.asignatura.nombre
                        data['idm'] = ePlanificacionMateria.materia.asignaturamalla.malla_id
                        data['idc'] = idc = ePlanificacionMateria.materia.asignaturamalla.malla.carrera_id
                        data['idp'] = idp = ePlanificacionMateria.materia.nivel.periodo_id
                        f.set_perfilrequerido(am.asignatura.pk, None, idc)
                        f.fields['periodo'].initial = idp
                        f.fields['nombre'].initial =ePlanificacionMateria.get_nombre_convocatoria_a_lanzar()
                        data['existe_perfil_requerido'] = f.fields['perfilrequeridopac'].queryset
                        data['idasigmalla'] = am.pk
                        data['asignatura'] = am.asignatura
                    else:
                        title = u"Convocatoria para docente invitado"
                        f.fields['periodo'].initial = periodo.pk

                    data['title'] = title
                    f.initial_values(tipo)
                    data['form'] = f
                    data['tipo'] = tipo
                    data['action'] = "addconvocatoria"
                    data['ePlanificacionMateria'] = ePlanificacionMateria
                    return render(request, "adm_postulacion/modal/addconvocatoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'realizar_convocatoria_doble':
                try:
                    id = request.GET.get('id', 0)
                    ePlanificacionMateria = PlanificacionMateria.objects.get(pk=id)
                    tipo = 1
                    # tipo = int(encrypt(request.GET.get('tipo', 'OPPQQRRSSTTUUVVWWXXX')))
                    f = ConvocatoriaForm()
                    f.delete_tipo_docente()
                    if tipo == 1:
                        am = ePlanificacionMateria.materia.asignaturamalla
                        title = u"%s" % am.asignatura.nombre
                        data['idm'] = ePlanificacionMateria.materia.asignaturamalla.malla_id
                        data['idc'] = idc = ePlanificacionMateria.materia.asignaturamalla.malla.carrera_id
                        data['idp'] = idp = ePlanificacionMateria.materia.nivel.periodo_id
                        f.set_perfilrequerido(am.asignatura.pk, None, idc)
                        f.fields['periodo'].initial = idp
                        f.fields['nombre'].initial =ePlanificacionMateria.get_nombre_convocatoria_a_lanzar()
                        data['existe_perfil_requerido'] = f.fields['perfilrequeridopac'].queryset
                        data['idasigmalla'] = am.pk
                        data['asignatura'] = am.asignatura
                    else:
                        title = u"Convocatoria para docente invitado"
                        f.fields['periodo'].initial = periodo.pk

                    data['title'] = title
                    f.initial_values(tipo)
                    data['form'] = f
                    data['tipo'] = tipo
                    data['action'] = "addconvocatoriadoble"
                    data['ePlanificacionMateria'] = ePlanificacionMateria
                    return render(request, "adm_postulacion/modal/addconvocatoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'realizar_votacion_comite':
                try:
                    with transaction.atomic():
                        pk = int(request.GET.get('id', '0'))
                        if pk == 0:
                            raise NameError("Parametro no encontrado")
                        form = VotacionComiteForm()
                        eInscripcionConvocatoria = InscripcionConvocatoria.objects.get(pk=pk)
                        form.load_inscrito(eInscripcionConvocatoria)

                        data['eInscripcionPostulante'] = eInscripcionConvocatoria
                        data['form'] = form
                        data['id_acta_paralelo'] = int(request.GET.get('id_paralelo', '0'))
                        template = get_template('comiteacademico/comite/votar_comite.html')
                        return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": f"{ex.__str__()}"})

            elif action == 'realizar_baremo_comite':
                try:
                    with transaction.atomic():
                        pk = int(request.GET.get('id', '0'))
                        if pk == 0:
                            raise NameError("Parametro no encontrado")
                        eInscripcionConvocatoria = InscripcionConvocatoria.objects.get(pk=pk)
                        eRubricaSeleccionDocentes = RubricaSeleccionDocente.objects.filter(status=True,activo = True)
                        eRubricaSeleccionDocente = eRubricaSeleccionDocentes.first() if eRubricaSeleccionDocentes.exists() else None
                        data['eRubricaSeleccionDocente'] = eRubricaSeleccionDocente
                        data['eInscripcionConvocatoria'] = eInscripcionConvocatoria
                        data['id_acta_paralelo'] = int(request.GET.get('id_paralelo', '0'))
                        data['eActaParalelo'] = eActaParalelo = ActaParalelo.objects.get(pk = int(request.GET.get('id_paralelo', '0')))

                        miembrocomite = eActaParalelo.acta.comite.get_integrantes().filter(persona=persona,status=True).first()
                        votacioncomiteacademico= miembrocomite.get_votos_realizados(eActaParalelo).filter(inscripcion = eInscripcionConvocatoria).first() if miembrocomite.get_votos_realizados(eActaParalelo).filter(inscripcion = eInscripcionConvocatoria).exists() else None
                        data['seleccionado'] = votacioncomiteacademico
                        data['eBaremoComiteAcademico'] = eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,votacioncomiteacademico = votacioncomiteacademico)
                        data['eBaremoComiteAcademico'] = eBaremoComiteAcademico.aggregate(total_puntaje=Sum('puntaje'))
                        data['eBaremoComiteAcademicoPk'] = eBaremoComiteAcademico.values_list('detallesubitemrubricaselecciondocente',flat=True)
                        template = get_template('comiteacademico/comite/calificar_baremo.html')
                        return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": f"{ex.__str__()}"})

            elif action == 'ver_votaciones':
                try:
                    with transaction.atomic():
                        id_acta_paralelo = int(request.GET.get('id_paralelo', '0'))
                        if id_acta_paralelo == 0:
                            raise NameError("Parametro no encontrado")
                        eActaParalelo = ActaParalelo.objects.get(pk=id_acta_paralelo)

                        data["eActaParalelo"] = eActaParalelo
                        template = get_template('comiteacademico/comite/ver_votacion_comite.html')
                        return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": f"{ex.__str__()}"})

            elif action == 'ver_votaciones_por_acta':
                try:
                    with transaction.atomic():
                        pk = int(request.GET.get('id', '0'))
                        if pk == 0:
                            raise NameError("Parametro no encontrado")
                        eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=pk)
                        data['eActaSeleccionDocente'] = eActaSeleccionDocente
                        template = get_template('adm_postulacion/modal/ver_votaciones_acta.html')
                        return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": f"{ex.__str__()}"})

            elif action == 'add_certificacion_presupuestaria':
                try:
                    pk = request.GET.get('id', None)
                    eDetalleInformeContratacion = DetalleInformeContratacion.objects.get(pk=pk)
                    form = CertificacionPresupuestariaInformeContratacionForm(initial={
                        'certificacionpresupuestaria':eDetalleInformeContratacion.certificacionpresupuestaria
                    })
                    data['form2'] = form
                    data['id'] = pk
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'view_requisitos_persona_a_contratar':
                try:
                    pk = request.GET.get('id', '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eDetalleInformeContratacion = DetalleInformeContratacion.objects.get(pk=pk)
                    data['eDetalleInformeContratacion'] = eDetalleInformeContratacion
                    data['personalcontratar'] = eDetalleInformeContratacion.personalcontratar
                    template = get_template('adm_contratacion/modal/requisitos.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'view_requisitos_contratacion':
                try:
                    pk = request.GET.get('id', '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    ePersonalAContratar = PersonalAContratar.objects.get(pk=pk)
                    data['personalcontratar'] = ePersonalAContratar
                    template = get_template('adm_contratacion/modal/requisitos.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'view_requisitos_contratacion_link':
                pk = request.GET.get('id', '0')
                if pk == 0:
                    raise NameError("Parametro no encontrado")
                ePersonalAContratar = PersonalAContratar.objects.get(pk=pk)
                data['personalcontratar'] = ePersonalAContratar

                return render(request, "adm_contratacion/link_requisito.html", data)

            elif action == 'historial_informe_contratacion':
                try:
                    pk = int(request.GET.get('id', '0'))
                    if not pk:
                        raise NameError("Parametro no encontrado")

                    eInformeContratacion = InformeContratacion.objects.get(pk = pk)

                    data['eInformeContratacion'] = eInformeContratacion
                    template = get_template('adm_contratacion/modal/historial_informe.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verificar_turno_para_firmar':
                try:
                    pk = request.GET.get('id','0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eInformeContratacion = InformeContratacion.objects.get(pk=pk)
                    puede, mensaje = eInformeContratacion.puede_firmar_integrante_segun_orden(persona)
                    return JsonResponse({"result": True, "puede":puede,"mensaje":mensaje})
                except Exception as ex:
                    pass

            elif action == 'baremodetallado':
                try:
                    data['title'] = 'Detalle del baremo'
                    id_acta_paralelo = int(request.GET.get('id', '0'))
                    if id_acta_paralelo == 0:
                        raise NameError("Parametro no encontrado")
                    eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=id_acta_paralelo)

                    data["eActaSeleccionDocente"] = eActaSeleccionDocente
                    return render(request, "seleccionposgrado/baremodetallado.html", data)
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Administración del sistema postulación'

                if persona.sexo.id == 1:
                    icon_user_access_profile = "/static/images/iconos/user_access_profile_women.png"
                elif persona.sexo.id == 2:
                    icon_user_access_profile = "/static/images/iconos/user_access_profile_men.png"
                else:
                    icon_user_access_profile = "/static/images/iconos/user_access_profile.png"

                misgrupos = ModuloGrupo.objects.filter(grupos__in=persona.usuario.groups.filter(id__in=[424,425])).distinct()
                modulos = Modulo.objects.values("id", "url", "icono", "nombre", "descripcion").filter(
                    Q(modulogrupo__in=misgrupos), activo=True, submodulo=False).distinct().order_by('nombre')
                data['mismodulos'] = modulos
                # menu_panel = [{"url": "/adm_postulacion?action=listadoprogramas", "img": "/static/images/iconssga/icon_users.svg", "title": "Postulaciones", "description": "Listado de postulaciones"},
                #               {"url": "/adm_postulacion?action=listadoinscritos", "img": "/static/images/iconssga/icon_inscripciones.svg", "title": "Inscritos", "description": "Listado de inscritos"},
                #               {"url": "/adm_postulacion?action=listadoinvitaciones", "img": "/static/images/iconssga/icon_pre_inscripcion.svg", "title": "Invitaciones", "description": "Listado de invitación postulación"},
                #               {"url": "/adm_postulacion?action=listadoactas", "img": "/static/images/iconssga/icon_inventario.svg", "title": "Actas de comité académico", "description": "Listado de actas de comité académico"},
                #               {"url": '/seleccionprevia',"img": "/static/images/iconssga/icon_certificados_de_docentes.svg","title": "Resumen Actas comité académico",  "description": "Listado de actas de comité académico."}
                #               ]
                #
                # data['menu_panel'] = menu_panel
                return render(request, "adm_postulacion/view.html", data)
            except Exception as ex:
                pass



def existe_informes_que_revisar(persona):
    # informe de contrtacion por honoario profesionales
    existen_informes_que_deba_firmar = False
    eInformeContratacion = InformeContratacion.objects.filter(status=True)
    if eInformeContratacion.exists():
        existen_informes_que_deba_firmar = eInformeContratacion.first().existen_informes_que_deba_firmar_el_integrante_aprobador(persona)

    return existen_informes_que_deba_firmar

def weeks_between(start_date, end_date):
    """
    Retorna una lista de semanas entre la fecha de inicio y fin dadas.
    Cada semana se representa como una lista de días.
    """
    weeks = []
    # Ajustar la fecha de inicio al primer día de la semana (lunes)
    start_date -= timedelta(days=start_date.weekday())
    while start_date <= end_date:
        # Obtener el último día de la semana (domingo)
        week_end = start_date + timedelta(days=6)
        # Asegurarse de que el último día de la semana no sea mayor que la fecha de fin
        if week_end > end_date:
            week_end = end_date
        # Agregar la semana a la lista
        weeks.append([(x.weekday() + 1, x) for x in daterange(start_date, week_end + timedelta(1))])
        # Avanzar al siguiente lunes
        start_date += timedelta(days=7)
    return weeks


def validapersonalinterno(postulante, hoy, request, lista, tipobeca, tipoconta):
    arregloemail = [23, 24, 25, 26, 27, 28]
    emailaleatorio = random.choice(arregloemail)
    if not InscripcionPostulante.objects.filter(persona=postulante, status=True).exists():
        aspirante = InscripcionPostulante(persona=postulante)
        aspirante.save()
    else:
        aspirante = InscripcionPostulante.objects.filter(persona=postulante, status=True)[0]

    if not Group.objects.filter(pk=347, user=postulante.usuario):
        usuario = User.objects.get(pk=postulante.usuario.id)
        g = Group.objects.get(pk=347)
        g.user_set.add(usuario)
        g.save()
    archivoadjunto = ''
    banneradjunto = ''
    asunto = u"Requisitos para admisión de "
    if archivoadjunto:
        send_html_mail(asunto, "emails/registroexitopersonal.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'formato': banneradjunto}, lista, [], [archivoadjunto], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
    else:
        send_html_mail(asunto, "emails/registroexitopersonal.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'formato': banneradjunto}, lista, [], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])

    return aspirante

def validapersonal(aspirante, lista, userpostulante, clavepostulante):
    archivoadjunto = ''
    banneradjunto = ''
    lista.append(conectar_cuenta(CUENTAS_CORREOS[18][1]))
    arregloemail = [23, 24, 25, 26, 27, 28]
    emailaleatorio = random.choice(arregloemail)
    asunto = u"Requisitos para admisión de "
    if archivoadjunto:
        send_html_mail(asunto, "emails/registroexitodip.html",
                       {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante,
                        'usuario': userpostulante,
                        'clave': clavepostulante,
                        'formato': banneradjunto},
                       lista, [], [archivoadjunto],
                       cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
    else:
        send_html_mail(asunto, "emails/registroexitodip.html",
                       {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante,
                        'usuario': userpostulante,
                        'clave': clavepostulante,
                        'formato': banneradjunto},
                       lista, [], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
    return aspirante


def get_acta_seleccion_docente_posgrado(self, **kwargs):
    try:
        acta = self # Por si la funcion se llegara a mover de lugar.
        data, hoy = {}, datetime.now().date()
        data['acta'] = acta
        data['paralelos'] = ActaParalelo.objects.filter(acta=acta, status=True)
        request = kwargs.pop('request', None)
        hoy = datetime.now().date()
        name = unicodedata.normalize('NFD', u"%s. %s" % (acta.codigo, acta.comite.nombre)).encode('ascii', 'ignore').decode("utf-8").lower().replace(' ', '_').replace('-', '')
        filename = generar_nombre(u"%s_" % name, f"{name}.pdf")
        filepath = u"actaselecciondocente/%s" % hoy.year
        folder_pdf = os.path.join(os.path.join(SITE_STORAGE, 'media', 'actaselecciondocente', hoy.year.__str__(), ''))
        os.makedirs(folder_pdf, exist_ok=True)
        data['pagesize'] = 'A4'
        data['request'] = request
        data['hoy'] = hoy
        if convert_html_to_pdf('adm_postulacion/docs/actaselecciondocente.html', data, filename, folder_pdf):
            self.archivo = os.path.join(filepath, filename)
            self.fecha_generacion = hoy
            self.save(request)
            HistorialActaSeleccionDocente.objects.filter(acta=acta).update(status=False)

            asunto = u"ACTA DE COMITÉ ACADÉMICO %s" % acta.comite
            email_experta = ['dmaciasv@unemi.edu.ec',]
            # email_experta = ['jcuadradoh2@unemi.edu.ec',]
            # send_html_mail(asunto, "emails/notificar_creacion_acta_seleccion_docente.html", {'sistema': request.session.get('nombresistema'), 'acta': acta}, email_experta, [], [acta.archivo], cuenta=CUENTAS_CORREOS[0][1])

        return self.archivo.url if self.archivo else None
    except Exception as ex:
        raise NameError(u'Solicitud incorrecta. %s' % ex.__str__())

def get_acta_seleccion_docente_posgrado_invitado(self, **kwargs):
    try:
        acta = self # Por si la funcion se llegara a mover de lugar.
        data, hoy = {}, datetime.now().date()
        data['acta'] = acta
        data['paralelos'] = ActaParalelo.objects.filter(acta=acta, status=True)
        request = kwargs.pop('request', None)
        hoy = datetime.now().date()
        name = unicodedata.normalize('NFD', u"%s. %s" % (acta.codigo, acta.comite.nombre)).encode('ascii', 'ignore').decode("utf-8").lower().replace(' ', '_').replace('-', '')
        filename = generar_nombre(u"%s_" % name, f"{name}.pdf")
        filepath = u"actaselecciondocente/%s" % hoy.year
        folder_pdf = os.path.join(os.path.join(SITE_STORAGE, 'media', 'actaselecciondocente', hoy.year.__str__(), ''))
        os.makedirs(folder_pdf, exist_ok=True)
        data['pagesize'] = 'A4'
        data['request'] = request
        data['hoy'] = hoy
        if convert_html_to_pdf('adm_postulacion/docs/actaselecciondocenteinvitado.html', data, filename, folder_pdf):
            self.archivo = os.path.join(filepath, filename)
            self.fecha_generacion = hoy
            self.save(request)
            HistorialActaSeleccionDocente.objects.filter(acta=acta).update(status=False)

            # asunto = u"ACTA DE COMITÉ ACADÉMICO %s" % acta.comite
            # email_experta = ['dmaciasv@unemi.edu.ec', 'ecarrasqueror@unemi.edu.ec']
            # # email_experta = ['jcuadradoh2@unemi.edu.ec',]
            # send_html_mail(asunto, "emails/notificar_creacion_acta_seleccion_docente.html", {'sistema': request.session.get('nombresistema'), 'acta': acta}, email_experta, [], [acta.archivo], cuenta=CUENTAS_CORREOS[0][1])

        return self.archivo.url if self.archivo else None
    except Exception as ex:
        raise NameError(u'Solicitud incorrecta. %s' % ex.__str__())


def get_acta_seleccion_docente_posgrado_grupal(self, **kwargs):
    try:
        actas = kwargs.pop('actas')

        data, hoy = {}, datetime.now().date()
        data['actas'] = actas
        data['paralelos'] = ActaParalelo.objects.filter(acta__in=actas, status=True)
        data['horas_modulo'] = DetalleFuncionSustantivaDocenciaPac.objects.values_list('horas', 'asignatura__nombre').filter(asignatura=actas.values_list('convocatoria__asignaturamalla__asignatura', flat=True), status=True)
        request = kwargs.pop('request', None)
        hoy = datetime.now().date()
        name = unicodedata.normalize('NFD', u"%s. %s" % (actas.last().codigo, actas.last().comite)).encode('ascii', 'ignore').decode("utf-8").lower().replace(' ', '_').replace('-', '')
        filename = generar_nombre(u"%s_" % name, f"{name}.pdf")
        filepath = u"actaselecciondocente/%s" % hoy.year
        folder_pdf = os.path.join(os.path.join(SITE_STORAGE, 'media', 'actaselecciondocente', hoy.year.__str__(), ''))
        os.makedirs(folder_pdf, exist_ok=True)
        data['pagesize'] = 'A4'
        data['request'] = request
        data['hoy'] = hoy
        if convert_html_to_pdf('adm_postulacion/actaselecciondocentegrupal.html', data, filename, folder_pdf):
            self.archivo = os.path.join(filepath, filename)
            self.fecha_generacion = hoy
            self.save(request)
            HistorialActaSeleccionDocente.objects.filter(acta__in=actas).update(status=False)

            asunto = u"ACTA DE COMITÉ ACADÉMICO %s" % actas.last().comite
            email_experta = ['dmaciasv@unemi.edu.ec',]
            # email_experta = ['jcuadradoh2@unemi.edu.ec',]
            send_html_mail(asunto, "emails/notificar_creacion_acta_seleccion_docente.html", {'sistema': request.session.get('nombresistema'), 'acta': actas}, email_experta, [], [acta.archivo], cuenta=CUENTAS_CORREOS[0][1])

        return self.archivo.url if self.archivo else None
    except Exception as ex:
        raise NameError(u'Solicitud incorrecta. %s' % ex.__str__())


def validar_acta_legalizada(self, **kwargs):
    plazo = datetime.now().date() + timedelta(variable_valor('PLAZO_LEGALIZAR_ACTA_SELECCION'))
    paralelos = ["%s - %s" % (paralelo[0], paralelo[1].strftime('%d/%m/%Y') if paralelo[1] else '') for paralelo in self.actaparalelo_set.filter(status=True, inicio__lt=plazo).values_list('paralelo__nombre', 'inicio')]
    if paralelos: raise NameError("La fecha de inicio de los paralelos: \n <b>%s</b> \n son menores al plazo mínimo para legalizar el acta (<b>%s</b>)." % (', \n'.join(paralelos), plazo.strftime('%d/%m/%Y')))


def reporte_general_tramites_contratacion_posgrado(request, **kwargs):
    try:
        __author__ = 'Unemi'
        style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
        style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
        style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
        title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
        style1 = easyxf(num_format_str='D-MMM-YY')
        font_style = XFStyle()
        font_style.font.bold = True
        font_style2 = XFStyle()
        font_style2.font.bold = False
        wb = Workbook(encoding='utf-8')
        ws = wb.add_sheet('exp_xls_post_part', cell_overwrite_ok=True)
        # ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
        response = HttpResponse(content_type="application/ms-excel")
        response['Content-Disposition'] = 'attachment; filename=reporte_general_tramites_contratacion_posgrado' + random.randint(1, 10000).__str__() + '.xls'
        row_num = 0
        columns = [
                    (u"N.", 2000),
                    (u"CEDULA", 4000),
                    (u"POSTULANTE", 9000),
                    (u"ASIGNATURA", 10000),
                    (u"ESTADO", 6000),
                    (u"EMAIL", 6000),
                    (u"TELEFONO", 4000),
                    (u"ESTADO CONTRATACIÓN", 5000)
                   ]
        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num][0], font_style)
            ws.col(col_num).width = columns[col_num][1]

        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'yyyy/mm/dd'
        #listado = InscripcionConvocatoria.objects.filter(convocatoria_id=int(encrypt(request.GET['idconvo'])), status=True).order_by('postulante__persona__apellido1', 'postulante__persona__apellido2')
        listado = InscripcionInvitacion.objects.filter(status=True)
        row_num = 0

        for lista in listado:
            row_num += 1
            campo1 = '-'
            if lista.inscripcion.postulante.persona.cedula:
                campo1 = lista.inscripcion.postulante.persona.cedula
            else:
                if lista.inscripcion.postulante.persona.pasaporte:
                    campo1 = lista.inscripcion.postulante.persona.pasaporte
            campo2 = u"%s" % lista.inscripcion.postulante.persona
            pac = lista.inscripcion.personalacontratar_set.first()

            campo3 = u"%s %s" % (lista.inscripcion.convocatoria.asignaturamalla.asignatura, pac.actaparalelo.paralelo if pac else '')
            campo4 = u"%s" % lista.get_estadorequisitos_display()
            campo5 = u"%s" % lista.inscripcion.postulante.persona.emailinst if lista.inscripcion.postulante.persona.emailinst else ''
            campo6 = u"%s" % lista.inscripcion.postulante.persona.telefono
            campo7 = u"%s" % lista.inscripcion.get_estadogen_display()

            ws.write(row_num, 0, row_num, font_style2)
            ws.write(row_num, 1, campo1, font_style2)
            ws.write(row_num, 2, campo2, font_style2)
            ws.write(row_num, 3, campo3, font_style2)
            ws.write(row_num, 4, campo4, font_style2)
            ws.write(row_num, 5, campo5, font_style2)
            ws.write(row_num, 6, campo6, font_style2)
            ws.write(row_num, 7, campo7, font_style2)

        wb.save(response)
        return response
    except Exception as ex:
        pass


def enviar_carta_invitacion(request, **kwargs):
    nombre_mes = lambda x: ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][int(x) - 1]
    import unicodedata
    from .models import HistorialInvitacion
    from sga.models import FirmaPersona, Materia
    from inno.models import HorarioTutoriaAcademica
    persona = request.session.get('persona')
    acta = kwargs.pop('acta')
    ganador = kwargs.pop('ganador')
    try:
        data = {}
        data['IS_DEBUG'] = IS_DEBUG = variable_valor('IS_DEBUG')
        hoy = datetime.now().date()
        inscripcionconvocatoria = InscripcionConvocatoria.objects.get(pk=ganador.inscripcion.id)
        InscripcionConvocatoria.objects.filter(pk=ganador.inscripcion.id).update(estadogen=1)
        materia = Materia.objects.filter(asignaturamalla=inscripcionconvocatoria.convocatoria.asignaturamalla, paralelomateria=ganador.actaparalelo.paralelo, status=True).first()
        if materia: data['horariotutoria'] = HorarioTutoriaAcademica.objects.filter(profesormateria__materia=materia, status=True).order_by('dia')

        data['inscripcionpostulante'] = inscripcionconvocatoria.postulante
        month, day = "%02d" % hoy.month, "%02d" % hoy.day

        if not InscripcionInvitacion.objects.values('id').filter(inscripcion_id=inscripcionconvocatoria.id, status=True,actaparalelo =ganador.actaparalelo).exists():
            # Si aún no existe esa materia creada se guarda en None
            invitacion = InscripcionInvitacion(materia=materia, pasosproceso_id=1, inscripcion=inscripcionconvocatoria,actaparalelo =ganador.actaparalelo)
        else:
            invitacion = InscripcionInvitacion.objects.get(inscripcion_id=inscripcionconvocatoria.id, status=True,actaparalelo =ganador.actaparalelo)

        filename = generar_nombre(f'carta_invitacion_{inscripcionconvocatoria.id}_', 'invitacion') + ".pdf"

        dominio_sistema = 'http://127.0.0.1:8000'
        if not IS_DEBUG:
            dominio_sistema = 'https://sga.unemi.edu.ec'
        data["DOMINIO_DEL_SISTEMA"] = dominio_sistema
        temp = lambda x: remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(x.__str__()))
        qrname = 'qr_certificado_cartainvitacion_' + str(invitacion.id)
        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'cartainvitacion', 'qr'))
        directory = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'cartainvitacion'))
        os.makedirs(f'{directory}/qr/', exist_ok=True)
        try:
            os.stat(directory)
        except:
            os.mkdir(directory)

        nombrepersona = temp(invitacion.inscripcion.postulante.persona.__str__()).replace(' ', '_')
        htmlname = 'cartainvitacion_{}_{}'.format(nombrepersona, random.randint(1, 100000).__str__())
        urlname = "/media/qrcode/cartainvitacion/%s" % htmlname
        # rutahtml = SITE_STORAGE + urlname
        data['url_qr'] = url_qr = f'{SITE_STORAGE}/media/qrcode/cartainvitacion/qr/{htmlname}.png'
        url = pyqrcode.create(  f'Generado desde https://sga.unemi.edu.ec\n FECHA: {datetime.today()}\n{dominio_sistema}/media/qrcode/cartaaceptacionposgrado/{htmlname}.pdf\n2.10.1')
        imageqr = url.png(f'{directory}/qr/{htmlname}.png', 16, '#000000')
        data['qrname'] = 'qr' + qrname

        ID_PERSONA_ESPINOSA_SOLIS = 26497
        data['firma'] = FirmaPersona.objects.filter(persona__pk=ID_PERSONA_ESPINOSA_SOLIS, status=True).first()
        mes = "%s" % nombre_mes(int(hoy.strftime("%m")))
        data['fechacabecera'] = f"Milagro, {day} de {mes.lower()} del {hoy.year}"

        data['acta'] = acta
        data['ganador'] = ganador

        data['convocatoria'] = ganador.actaparalelo.convocatoria

        pdf_file, response = conviert_html_to_pdf_save_file_model(
            'adm_postulacion/docs/invitacionpdf.html',
            {
                'pagesize': 'A4',
                'data': data,
            }
        )

        invitacion.estadoinvitacion = 2
        invitacion.archivo = filename
        invitacion.actaparalelo = ganador.actaparalelo
        invitacion.configuracionrequisitos = True
        invitacion.archivo.save(filename, pdf_file)
        invitacion.save(request)

        historial = HistorialInvitacion(invitacion=invitacion, pasosproceso_id=1, estadoinvitacion=2, personaaprobador=persona, observacion='Envío de invitación')
        historial.archivo = filename
        historial.archivo.save(filename, pdf_file)
        historial.save(request)

        ###########

        invitacion.generar_acta_de_invitacion(request, pdf_file)
        #############


        return JsonResponse({"result": True, "url": f"{invitacion.archivo.url}", 'invitacion':invitacion.pk})
    except Exception as ex:
        transaction.set_rollback(True)
        return JsonResponse({"result": False, "mensaje": f"Error de conexión. %s" % ex.__str__()})

def crear_invitacion(request, **kwargs):
    nombre_mes = lambda x: ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][int(x) - 1]
    import unicodedata
    from .models import HistorialInvitacion
    from sga.models import FirmaPersona, Materia
    from inno.models import HorarioTutoriaAcademica
    persona = request.session.get('persona')
    acta = kwargs.pop('acta')
    ganador = kwargs.pop('ganador')
    try:
        data = {}
        data['IS_DEBUG'] = IS_DEBUG = variable_valor('IS_DEBUG')
        hoy = datetime.now().date()
        inscripcionconvocatoria = InscripcionConvocatoria.objects.get(pk=ganador.inscripcion.id)
        InscripcionConvocatoria.objects.filter(pk=ganador.inscripcion.id).update(estadogen=1)
        materia = Materia.objects.filter(asignaturamalla=inscripcionconvocatoria.convocatoria.asignaturamalla, paralelomateria=ganador.actaparalelo.paralelo, status=True).first()
        if materia: data['horariotutoria'] = HorarioTutoriaAcademica.objects.filter(profesormateria__materia=materia, status=True).order_by('dia')

        data['inscripcionpostulante'] = inscripcionconvocatoria.postulante
        month, day = "%02d" % hoy.month, "%02d" % hoy.day

        if not InscripcionInvitacion.objects.values('id').filter(inscripcion_id=inscripcionconvocatoria.id, status=True,actaparalelo =ganador.actaparalelo).exists():
            # Si aún no existe esa materia creada se guarda en None
            invitacion = InscripcionInvitacion(materia=materia, pasosproceso_id=1, inscripcion=inscripcionconvocatoria,actaparalelo =ganador.actaparalelo)
        else:
            invitacion = InscripcionInvitacion.objects.get(inscripcion_id=inscripcionconvocatoria.id, status=True,actaparalelo =ganador.actaparalelo)

        invitacion.estadoinvitacion = 2
        invitacion.actaparalelo = ganador.actaparalelo
        invitacion.configuracionrequisitos = False
        invitacion.save(request)


        return JsonResponse({"result": True, 'invitacion':invitacion.pk})
    except Exception as ex:
        transaction.set_rollback(True)
        return JsonResponse({"result": False, "mensaje": f"Error de conexión. %s" % ex.__str__()})

def crear_solo_documento_carta_invitacion(request, **kwargs):
    nombre_mes = lambda x: ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][int(x) - 1]
    import unicodedata
    from .models import HistorialInvitacion
    from sga.models import FirmaPersona, Materia
    from inno.models import HorarioTutoriaAcademica
    persona = request.session.get('persona')
    acta = kwargs.pop('acta')
    ganador = kwargs.pop('ganador')
    try:
        data = {}
        data['IS_DEBUG'] = IS_DEBUG = variable_valor('IS_DEBUG')
        hoy = datetime.now().date()
        inscripcionconvocatoria = InscripcionConvocatoria.objects.get(pk=ganador.inscripcion.id)
        InscripcionConvocatoria.objects.filter(pk=ganador.inscripcion.id).update(estadogen=1)
        materia = Materia.objects.filter(asignaturamalla=inscripcionconvocatoria.convocatoria.asignaturamalla, paralelomateria=ganador.actaparalelo.paralelo, status=True).first()
        if materia: data['horariotutoria'] = HorarioTutoriaAcademica.objects.filter(profesormateria__materia=materia, status=True).order_by('dia')

        data['inscripcionpostulante'] = inscripcionconvocatoria.postulante
        month, day = "%02d" % hoy.month, "%02d" % hoy.day

        if not InscripcionInvitacion.objects.values('id').filter(inscripcion_id=inscripcionconvocatoria.id, status=True,actaparalelo =ganador.actaparalelo).exists():
            # Si aún no existe esa materia creada se guarda en None
            invitacion = InscripcionInvitacion(materia=materia, pasosproceso_id=1, inscripcion=inscripcionconvocatoria,actaparalelo =ganador.actaparalelo)
        else:
            invitacion = InscripcionInvitacion.objects.get(inscripcion_id=inscripcionconvocatoria.id, status=True,actaparalelo =ganador.actaparalelo)

        filename = generar_nombre(f'carta_invitacion_{inscripcionconvocatoria.id}_', 'invitacion') + ".pdf"

        dominio_sistema = 'http://127.0.0.1:8000'
        if not IS_DEBUG:
            dominio_sistema = 'https://sga.unemi.edu.ec'
        data["DOMINIO_DEL_SISTEMA"] = dominio_sistema
        temp = lambda x: remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(x.__str__()))
        qrname = 'qr_certificado_cartainvitacion_' + str(invitacion.id)
        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'cartainvitacion', 'qr'))
        directory = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'cartainvitacion'))
        os.makedirs(f'{directory}/qr/', exist_ok=True)
        try:
            os.stat(directory)
        except:
            os.mkdir(directory)

        nombrepersona = temp(invitacion.inscripcion.postulante.persona.__str__()).replace(' ', '_')
        htmlname = 'cartainvitacion_{}_{}'.format(nombrepersona, random.randint(1, 100000).__str__())
        urlname = "/media/qrcode/cartainvitacion/%s" % htmlname
        # rutahtml = SITE_STORAGE + urlname
        data['url_qr'] = url_qr = f'{SITE_STORAGE}/media/qrcode/cartainvitacion/qr/{htmlname}.png'
        url = pyqrcode.create(  f'Generado desde https://sga.unemi.edu.ec\n FECHA: {datetime.today()}\n{dominio_sistema}/media/qrcode/cartaaceptacionposgrado/{htmlname}.pdf\n2.10.1')
        imageqr = url.png(f'{directory}/qr/{htmlname}.png', 16, '#000000')
        data['qrname'] = 'qr' + qrname

        ID_PERSONA_ESPINOSA_SOLIS = 26497
        data['firma'] = FirmaPersona.objects.filter(persona__pk=ID_PERSONA_ESPINOSA_SOLIS, status=True).first()
        mes = "%s" % nombre_mes(int(hoy.strftime("%m")))
        data['fechacabecera'] = f"Milagro, {day} de {mes.lower()} del {hoy.year}"

        data['acta'] = acta
        data['ganador'] = ganador

        data['convocatoria'] = ganador.actaparalelo.convocatoria

        pdf_file, response = conviert_html_to_pdf_save_file_model(
            'adm_postulacion/docs/invitacionpdf.html',
            {
                'pagesize': 'A4',
                'data': data,
            }
        )

        invitacion.archivo = filename
        invitacion.archivo.save(filename, pdf_file)
        invitacion.save(request)

        historial = HistorialInvitacion(invitacion=invitacion, pasosproceso_id=1, estadoinvitacion=2, personaaprobador=persona, observacion='Envío de invitación')
        historial.archivo = filename
        historial.archivo.save(filename, pdf_file)
        historial.save(request)

        ###########

        invitacion.generar_acta_de_invitacion(request, pdf_file)
        #############


        return JsonResponse({"result": True, "url": f"{invitacion.archivo.url}", 'invitacion':invitacion.pk})
    except Exception as ex:
        transaction.set_rollback(True)
        return JsonResponse({"result": False, "mensaje": f"Error de conexión. %s" % ex.__str__()})


def valida_choque_horario_pregrado(request: object, **kwargs: object) -> object:
    from sga.models import Clase, ProfesorMateria
    from .models import HorarioClases
    try:
        eHorarioClases = kwargs.pop('horarioClases', None)
        eInscripcionConvocatoria = kwargs.pop('InscripcionConvocatoria', None)
        persona = eInscripcionConvocatoria.postulante.persona
        for horario in eHorarioClases:
            lista_turnos = horario.turno.all()
            dia = horario.dia
            inicio = horario.inicio
            fin = horario.fin
            profesormateria = ProfesorMateria.objects.filter(profesor__persona=persona, materia__cerrado=False, materia__inicio__lte=inicio, materia__fin__gte=fin)
            for pm in profesormateria:
                tipoprofesor = pm.tipoprofesor
                periodo = pm.materia.nivel.periodo
                profesor = pm.profesor
                materia = pm.materia
                for turno in lista_turnos:
                    claseconflicto = Clase.objects.filter(Q(inicio__lte=inicio, fin__gte=inicio) | Q(inicio__lte=fin, fin__gte=fin) | Q(inicio__gte=inicio, fin__lte=fin), Q(turno=turno, dia=dia, activo=True, materia__cerrado=False, profesor=profesor))
                    if claseconflicto: raise NameError(f"El profesor ya tiene asignada una materia en el  turno : {turno} y día: {dia}.")

                # CONFLICTO OTRAS CLASES
                # if not ProfesorMateria.objects.filter(profesor=profesor, novalidahorario=True, activo=True, tipoprofesor=profesor, materia=materia).exists():
                #     if claseconflicto.values('id').filter(tipoprofesor=profesor, profesor=profesor, materia__asignatura_id=materia.asignatura.id).exists():
                #         raise NameError(u"La materia ya existe en este turno, dia y profesor en ese rango de fechas.")
                #     elif claseconflicto.values('id').filter(tipoprofesor=tipoprofesor, profesor=profesor).exists():
                #         raise NameError(u"El profesor ya tiene asignada una materia en ese turno y día.")
                for turno in lista_turnos:
                    claseconflicto = Clase.objects.filter(Q(inicio__lte=inicio, fin__gte=inicio) | Q(inicio__lte=fin, fin__gte=fin) | Q(inicio__gte=inicio, fin__lte=fin), materia__nivel__periodo=periodo, turno=turno, dia=dia, activo=True, materia__cerrado=False)
                    if claseconflicto.values('id').filter(tipoprofesor=tipoprofesor, profesor=profesor, materia__asignatura_id=materia.asignatura.id).exists():
                        raise NameError(f"La materia ya existe en este turno: {turno}, dia : {dia}, aula y profesor en ese rango de fechas.")

                    elif claseconflicto.values('id').filter(tipoprofesor=tipoprofesor, profesor=profesor).exists():
                        raise NameError(f"El profesor ya tiene asignada una materia en ese turno: {turno}, día: {dia} y aula.")

                if materia.tipomateria == 1:
                    for turno in lista_turnos:
                        verificar_conflito_docente = profesor.existe_conflicto_docente(periodo, materia, tipoprofesor, inicio, fin, dia, turno)
                        if verificar_conflito_docente[0]: raise NameError(verificar_conflito_docente[1])

                elif materia.coordinacion().id != 9:
                    for turno in lista_turnos:
                        verificar_conflito_docente = profesor.existe_conflicto_docente(periodo, materia, tipoprofesor, inicio, fin, dia, turno)
                        if verificar_conflito_docente[0]: raise NameError(verificar_conflito_docente[1])

        return {'result': True}

    except Exception as ex:
        return {'result':False, 'mensaje': u"%s" % ex.__str__()}


def valida_choque_horario_en_actas_generadas(request: object, **kwargs: object) -> object:
    from .models import HorarioClases
    try:
        eHorarioClases_new = kwargs.pop('horarioClases', None)
        eInscripcionConvocatoria = kwargs.pop('InscripcionConvocatoria', None)
        ePersonalAContratars =PersonalAContratar.objects.filter(status=True, tipo_id=1, inscripcion__postulante__persona = eInscripcionConvocatoria.postulante.persona).exclude(actaparalelo__convocatoria__id = eInscripcionConvocatoria.convocatoria.id)

        for horario in eHorarioClases_new:
            lista_turnos = horario.turno.all()
            dia = horario.dia
            inicio = horario.inicio
            fin = horario.fin
            for turno in lista_turnos:
                for ePersonalAContratar in ePersonalAContratars:
                    eActaParalelo = ePersonalAContratar.actaparalelo
                    eHorarioClasesePersonalAContratar = HorarioClases.objects.filter(status=True,actaparalelo = eActaParalelo).filter(
                        Q(dia=dia) &((Q(turno__comienza__gte=turno.comienza) & Q(turno__termina__lte=turno.termina)) |
                         (Q(turno__comienza__lte=turno.comienza) & Q(turno__termina__gte=turno.termina)) |
                         (Q(turno__comienza__lte=turno.termina) & Q(turno__comienza__gte=turno.comienza)) |
                         (Q(turno__termina__gte=turno.comienza) & Q(turno__termina__lte=turno.termina))) &
                        ((Q(inicio__gte=inicio) & Q(fin__lte=fin)) |(Q(inicio__lte=inicio) & Q(fin__gte=fin)) | Q(inicio__lte=fin) & Q(inicio__gte=inicio)) | (Q(fin__gte=inicio) & Q(fin__lte=fin))
                    )
                    if eHorarioClasesePersonalAContratar.exists():
                        raise NameError(f"Conficto de horarios en acta: {eActaParalelo.acta} - {eActaParalelo}")


        return {'result': True}

    except Exception as ex:
        return {'result':False, 'mensaje': u"%s" % ex.__str__()}


def informe_tecnico_contratacion_docente(**kwargs):
    from .models import HistorialInvitacion
    from sagest.models import PersonaDepartamentoFirmas

    data, documentoinvitacion = {}, None
    request, nombre_dia, nombre_mes = kwargs.pop('request', None), kwargs.pop('nombre_dia', None), kwargs.pop('nombre_mes', None)
    persona = request.session.get('persona')
    mensaje = "Problemas al generar el informe técnico. %s"
    try:
        hoy, abreviaturanombre = datetime.now(), ''
        documento = ClasificacionDocumentoInvitacion.objects.get(pk=request.POST.get('iddoc'))
        secuencia = SecuenciaDocumentoInvitacion(tipo=documento)
        secuencia.save(request)
        codigo = secuencia.set_secuencia()

        for c in persona.nombre_completo().split(' '):
            abreviaturanombre += c[0] if c.__len__() else ''

        if directorpos := PersonaDepartamentoFirmas.objects.filter(denominacionpuesto=815, activo=True).first():
            data['directorposgrado'] = directorpos.personadepartamento

        if vicerrector := PersonaDepartamentoFirmas.objects.filter(denominacionpuesto=795, activo=True).first():
            data['vicerrectorposgrado'] = vicerrector.personadepartamento

        # data['dias_mes_clases'] = dias_mes_clases
        # data['turno_dias'] = turnos_dias
        # data['suscrito'] = invitaciones
        # evidencia = [x.get_personal_principal() for x in  ii.acta.get_paralelo_ganador()]
        data['hoy'] = hoy
        mes = nombre_mes(hoy.strftime("%m"))
        data['fechacabecera'] = f"{hoy.strftime('%d')} de {mes} del {hoy.strftime('%Y')}"
        # data['rmu'] = ii.inscripcion.postulante.persona.contratodip_set.order_by('-id').first()
        # fechainvitacion = ii.historialinvitacion_set.filter(status=True).last().fecha_creacion
        # data['fechainvitacion'] = f"{fechainvitacion.strftime('%d')} de {nombre_mes(fechainvitacion.strftime('%m'))} {fechainvitacion.strftime('%Y')}"
        data['firmas'] = FirmasDocumentoInvitacion.objects.filter(documentoinvitacion=documento, status=True)
        data['fechainvitacion'] = HistorialInvitacion.objects.filter(status=True).order_by('-id').first()
        data['codigo'] = codigodocumento = "ITI-POS-%s-%s-%s" % (abreviaturanombre, "%03d" % codigo, secuencia.anioejercicio)

        # SE PRESENTAN UNICAMENTE LOS PARALELOS APROBADOS
        data['actas'] = actas = ActaSeleccionDocente.objects.filter(pk__in=request.POST.getlist('lista_items1'), status=True)
        data['paralelos'] = paralelos = ActaParalelo.objects.filter(acta__in=actas.values_list('id', flat=True), status=True, estado=1).distinct()
        data['convocatoria'] = Convocatoria.objects.filter(pk__in=paralelos.values_list('convocatoria', flat=True), status=True).distinct().first()
        data['total_vacantes'] = sum([acta.get_total_vacantes() for acta in actas])
        data['modulos'] = Asignatura.objects.filter(pk__in=paralelos.values_list('convocatoria__asignaturamalla__asignatura', flat=True), status=True)
        data['total_valor_calculado'] = "%.2f" % sum([x.convocatoria.get_valor_total_modulo() for x in paralelos])
        invitaciones = InscripcionInvitacion.objects.filter(Q(actaparalelo__in=paralelos.values_list('id', flat=True)) | Q(inscripcion__in=paralelos.values_list('personalacontratar__inscripcion', flat=True).filter(personalacontratar__tipo=1).distinct())).filter(status=True).distinct()
        data['evidencias'] = invitaciones
        data['certificacion'] = CertificacionPresupuestariaDip.objects.filter(pk=request.POST.get('certificacion')).first()


        # GENERAR Y GUARDAR DOCUMENTO
        filename = f"/{secuencia.pk}_informe_tecnico_contratacion_.pdf"
        filepath = u"documentospostulaciondip/documentos/%s" % hoy.year
        folder_pdf = os.path.join(SITE_STORAGE, 'media', 'documentospostulaciondip', '')

        os.makedirs(folder_pdf, exist_ok=True)
        os.makedirs(os.path.join(folder_pdf, 'documentos', ''), exist_ok=True)
        os.makedirs(os.path.join(folder_pdf, 'documentos', hoy.year.__str__(), ''), exist_ok=True)

        newfile = convert_html_to_pdf('../templates/adm_postulacion/documentoscontrato/informetecnicocontrataciondocente.html',
                                      {'pagesize': 'A4', 'data': data}, filename,
                                      os.path.join(os.path.join(SITE_STORAGE, 'media', filepath, '')))

        documentoinvitacion = DocumentoInvitacion(secuenciadocumento=secuencia, codigo=codigodocumento, clasificacion=documento, archivo=filepath + filename if newfile else None)
        documentoinvitacion.save(request)
        for acta in actas:
            actadocumento = ActaDocumentacion(acta=acta, documentoinvitacion=documentoinvitacion)
            actadocumento.save(request)

        return JsonResponse({'result': 'ok', 'url': documentoinvitacion.archivo.url.__str__() if newfile else ''})
    except Exception as ex:
        return JsonResponse({'result': 'bad', 'mensaje': f"Error al crear el documento. {ex.__str__()}"})
