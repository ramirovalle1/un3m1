# -*- coding: UTF-8 -*-
import json
import random
import io
import os
import xlsxwriter
import xlwt
import fitz
from unidecode import unidecode

from core.firmar_documentos_ec_descentralizada import qrImgFirma
from investigacion.forms import DocenteExternoForm
from investigacion.models import UserCriterioRevisor
from sga.tasks import send_html_mail
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta, date
from django.db import transaction
from django.db.models import Q
from django.db.models.aggregates import Sum
from django.http import JsonResponse, HttpResponse
from django.http.response import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.template.context import Context
from django.core.files.base import ContentFile
from django.template.loader import get_template
from xlwt import *
from sga.templatetags.sga_extras import encrypt
from django.forms import  model_to_dict
from decorators import last_access, secure_module
from sga.commonviews import adduserdata
from sga.forms import EvidenciaForm, ParticipanteProfesorForm, ParticipanteEstudianteForm, \
    ParticipanteAdministrativoForm, PresupuestoProyectoForm, \
    ProyectoVinculacion1Form, ProyectoVinculacion2Form, MarcoLogicoForm, FechaInformeForm, EvidenciaInformeForm, \
    FechaFinProyectoFrom, CarreraParticipanteForm, PerfilProfesionalForm, ParticipanteProfesorForm2, BeneficiariosForm, \
    ArProblemaForm, ArProb_CausaEfectoForm, DatoSecundarioForm, LineaBaseForm, ArObjetivoForm, MarcoLogicoForm2, \
    CronogramaForm, PresupuestoForm, RedaccionForm, AnexosForm, InvolucradoForm, AvanceEjecucionForm, \
    Configuracion_Informe_VinculacionForm, Detalle_InformeForm, ActividadExtraForm, AprobacionInformeForm, \
    PeriodoInscripcionFrom, InformeProyectoVinculacionForm, RegistrarHorasViculacionForm, InformeProyectoVinculacionFechaForm, ParticipanteProfesorVinculacionForm
from sga.funciones import log, generar_nombre, MiPaginador, null_to_decimal, get_director_vinculacion, variable_valor, notificacion2
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, convert_html_to_pdf
from sga.models import  CriterioDocencia, Inscripcion, DetalleEvidencias, ProyectosInvestigacion, \
    ParticipantesMatrices, PresupuestosProyecto, CarrerasProyecto, Graduado, Evidencia, ParticipantesTipo, Carrera, \
    ProyectoVinculacionCampos, Canton, \
    SubLineaInvestigacion, ProyectoVinculacionInscripcion, NivelMalla, PoliticasObjetivoPlanNacional, \
    PoliticaProyectosInvestigacion, MetasPndPlanNacional, MetasPndProyectosInvestigacion, \
    MetasZonalPlanNacional, MetasZonalProyectosInvestigacion, MetasComplementariaPlanNacional, \
    MetasComplementariaProyectosInvestigacion, LineamientoPlanNacional, LineamientoProyectosInvestigacion, \
    MarcoLogicoProyectosInvestigacion, InformeMarcoLogicoProyectosInvestigacion, DetalleInforme, \
    DetalleEvidenciasInformes, LineaProgramasInvestigacion, AreaProgramasInvestigacion, LineaInvestigacion, \
    AreaConocimientoTitulacion, SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion, \
    ProyectosInvestigacionCarreras, FechaProyectos, ProyectosInvestigacionAprobacion, ProyectosInvestigacionZonas, \
    ProyectosInvestigacionCantones, Zona, Presupuesto, ArbolObjetivo, ArbolProblema, DatoSecundario, MatrizLineaBase, \
    MarcoLogico, CarrerasParticipantes, PerfilProfesional, Beneficiarios, Cronograma, Profesor, Problema, Anexos, \
    Involucrado, ESTADOS_PROYECTO_VINCULACION_INVESTIGACION, DetalleCumplimiento, ConfiguracionInformeVinculacion, \
    DetalleInforme, MarcoLogicoReporte, DetalleInformeVinculacion, ActividadExtraVinculacion, \
    PeriodoInscripcionVinculacion, CarreraInscripcionVinculacion, InformesProyectoVinculacionDocente, InformesProyectoVinculacionEstudiante, \
    miinstitucion, Suministro, Notificacion, Persona, Externo, DetalleDistributivo, EvidenciaActividadDetalleDistributivo, HistorialAprobacionEvidenciaActividad
from postulaciondip.forms import FirmaElectronicaIndividualForm
from sagest.models import Producto, DetalleIngresoProducto
from core.firmar_documentos import firmar, obtener_posicion_x_y, obtener_posicion_x_y_saltolinea, verificarFirmasPDF
from settings import DEBUG, SITE_STORAGE
from django.core.files import File as DjangoFile
from core.firmar_documentos_ec import JavaFirmaEc
from django.contrib import messages
from inno.forms import TecnicoAsociadoProyectoVinculacionForm
from inno.models import TecnicoAsociadoProyectoVinculacion, MigracionEvidenciaActividad
from sga.templatetags.sga_extras import nombremes

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['periodo']= periodo = request.session['periodo']
    usuario = persona.usuario
    fecha = datetime.now().date()
    responsablevinculacion = get_director_vinculacion()
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    data['profesor']= profesor = perfilprincipal.profesor
    miscarreras = persona.mis_carreras()
    if request.method == 'POST':
        data['action'] = action = request.POST['action']

        if action == 'addproyecto':
            try:
                f = ProyectoVinculacion1Form(request.POST)
                if f.is_valid():
                    if not ProyectosInvestigacion.objects.filter(nombre=f.cleaned_data['nombre']).exists():
                        if not request.POST['conv'] =="":
                            conv = FechaProyectos.objects.get(pk=request.POST['conv'])
                            estado = 5
                        else:
                            conv=None
                            estado = 6
                        proyecto = ProyectosInvestigacion(
                                                        convocatoria=conv,
                                                        nombre=f.cleaned_data['nombre'],
                                                        fechainicio=f.cleaned_data['fechainicio'],
                                                        fechaplaneacion=f.cleaned_data['fechaPlanificacion'],
                                                        programa=f.cleaned_data['programa'],
                                                        tipo=1,
                                                        tipoproinstitucion=f.cleaned_data['tipoproinstitucion'],
                                                        alcanceterritorial=f.cleaned_data['alcanceterritorial'],
                                                        areaconocimiento=f.cleaned_data['areaconocimiento'],
                                                        subareaconocimiento=f.cleaned_data['subareaconocimiento'],
                                                        subareaespecificaconocimiento=f.cleaned_data['subareaespecificaconocimiento'],
                                                        tiempoejecucion=f.cleaned_data['tiempoejecucion'],
                                                        tiempo_duracion_horas=f.cleaned_data['tiempo_duracion_horas'],
                                                        lineainvestigacion=f.cleaned_data['lineainvestigacion'],
                                                        sublineainvestigacion=f.cleaned_data['sublineainvestigacion'],
                                                        sectorcoordenada=f.cleaned_data['sectorcoordenada'],
                                                        objetivos_PND=f.cleaned_data['objetivos_PND'],
                                                        politicas_PND=f.cleaned_data['politicas_PND'],
                                                        linea_accion=f.cleaned_data['linea_accion'],
                                                        estrategia_desarrollo=f.cleaned_data['estrategia_desarrollo'],
                                                        investigacion_institucional=f.cleaned_data['investigacion_institucional'],
                                                        necesidades_sociales=f.cleaned_data['necesidades_sociales'],
                                                        circuito=f.cleaned_data['circuito'],
                                                        distrito=f.cleaned_data['distrito'],
                                                        # canton=f.cleaned_data['canton'],
                                                        # zona=f.cleaned_data['zona'],
                                                        aprobacion=estado,
                        )

                        proyecto.save(request)
                        # proyecto.canton = f.cleaned_data["canton"]
                        # proyecto.zona = f.cleaned_data["zona"]
                        for cant in f.cleaned_data['canton']:
                            proyecto.canton.add(cant)
                        for z in f.cleaned_data['zona']:
                            proyecto.zona.add(z)
                        # zonas = f.cleaned_data['zona']

                        # lineas= f.cleaned_data['carreras']
                        # for lis in lineas:
                        #     detalle=ProyectosInvestigacionCarreras(proyectovinculacion=proyecto,carreras_id=lis.id)
                        #     detalle.save(request)

                        # for zona in zonas:
                        #     proyectozona=ProyectosInvestigacionZonas(proyectovinculacion=proyecto,zona_id=zona.id)
                        #     proyectozona.save(request)
                        # for canton in cantones:
                        #     proyectocanton=ProyectosInvestigacionCantones(proyectovinculacion=proyecto,canton_id=canton.id)
                        #     proyectocanton.save(request)




                        participantesmatrices = ParticipantesMatrices(matrizevidencia_id=2,
                                                                      proyecto=proyecto,
                                                                      profesor=profesor,
                                                                      horas=0,
                                                                      tipoparticipante_id=1
                                                                      )
                        participantesmatrices.save(request)
                        # PoliticaProyectosInvestigacion.objects.filter(proyectovinculacion=proyecto).delete()
                        # politicas
                        # for p in PoliticasObjetivoPlanNacional.objects.filter(objetivo=f.cleaned_data['objetivoplannacional'], status=True):
                        #     politicaproyectosinvestigacion = PoliticaProyectosInvestigacion(proyectovinculacion=proyecto,
                        #                                                                     politica=p,
                        #                                                                     status=False)
                        #     politicaproyectosinvestigacion.save(request)
                        # metaspnd
                        # for p in MetasPndPlanNacional.objects.filter(objetivo=f.cleaned_data['objetivoplannacional'], status=True):
                        #     metaspndproyectosinvestigacion = MetasPndProyectosInvestigacion(proyectovinculacion=proyecto,
                        #                                                                     metaspnd=p,
                        #                                                                     status=False)
                        #     metaspndproyectosinvestigacion.save(request)
                        # metaszona
                        # for p in MetasZonalPlanNacional.objects.filter(objetivo=f.cleaned_data['objetivoplannacional'], status=True):
                        #     metaszonalproyectosinvestigacion = MetasZonalProyectosInvestigacion(proyectovinculacion=proyecto,
                        #                                                                         metaszonal=p,
                        #                                                                         status=False)
                        #     metaszonalproyectosinvestigacion.save(request)
                        # metascomplementaria
                        # for p in MetasComplementariaPlanNacional.objects.filter(objetivo=f.cleaned_data['objetivoplannacional'], status=True):
                        #     metascomplementariaproyectosinvestigacion = MetasComplementariaProyectosInvestigacion(proyectovinculacion=proyecto,
                        #                                                                                           metascomplementaria=p,
                        #                                                                                           status=False)
                            # metascomplementariaproyectosinvestigacion.save(request)
                        # lineamiento
                        # for p in LineamientoPlanNacional.objects.filter(objetivo=f.cleaned_data['objetivoplannacional'], status=True):
                        #     lineamientoproyectosinvestigacion = LineamientoProyectosInvestigacion(proyectovinculacion=proyecto,
                        #                                                                           lineamiento=p,
                        #                                                                           status=False)
                        #     lineamientoproyectosinvestigacion.save(request)
                        log(u'Adiciono proyecto de investigación docente: %s' % proyecto, request, "add")
                        return JsonResponse({"result": "ok", 'id': proyecto.id})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error a guardar."})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addcarreraparticipante':
            try:
                f = CarreraParticipanteForm(request.POST)
                if f.is_valid():
                    if not CarrerasParticipantes.objects.filter(proyecto__pk = request.POST['idproyecto'], carrera = f.cleaned_data['carrera'], status=True ).exists():
                        carrera = CarrerasParticipantes(
                                                        proyecto=ProyectosInvestigacion.objects.get(pk=request.POST['idproyecto']),
                                                        carrera= f.cleaned_data['carrera'],
                                                        # cupos= f.cleaned_data['cupos']
                        )
                        carrera.save(request)
                        request.session['pestaña'] = 'carreraParticipante'
                        request.session['vista'] = '3'
                        log(u'Adiciono carrera al proyecto: %s' % carrera, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Carrera ya se encuentra registrada en el proyecto"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcarreraparticipante':
            try:
                f = CarreraParticipanteForm(request.POST)
                if f.is_valid():
                    datos = CarrerasParticipantes.objects.get(pk = request.POST['id'])
                    datos.carrera = f.cleaned_data['carrera']
                    # datos.cupos = f.cleaned_data['cupos']
                    datos.save(request)
                    request.session['pestaña'] = 'carreraParticipante'
                    request.session['vista'] = '3'
                    log(u'Edito carrera al proyecto: %s' % datos, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletecarreraparticipante':
            try:
                participante = CarrerasParticipantes.objects.get(pk=request.POST['id'])
                participante.status = False

                if PerfilProfesional.objects.filter(carreras_participantes = participante, status = True).exists():
                    perfil = PerfilProfesional.objects.get(carreras_participantes = participante, status = True)
                    perfil.status = False
                    perfil.save(request)
                log(u'Elimino carrera practicipante de investigación docente: %s' % participante, request, "del")
                participante.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addperfilprofesional':
            try:
                f = PerfilProfesionalForm(request.POST)
                if f.is_valid():
                    perfil = PerfilProfesional(
                                                    proyecto=ProyectosInvestigacion.objects.get(pk=request.POST['idproyecto']),
                                                    carreras_participantes= CarrerasParticipantes.objects.get(pk=request.POST['idcarrera']),
                                                    resultados_aprendizaje= f.cleaned_data['resultados_aprendizaje'],
                                                    perfil= f.cleaned_data['perfil']
                    )
                    perfil.save(request)
                    perfil.asignatura.clear()
                    for data in f.cleaned_data["asignatura"]:
                        perfil.asignatura.add(data)
                    request.session['pestaña'] = 'carreraParticipante'
                    request.session['vista'] = '3'
                    log(u'Adiciono perfil al proyecto: %s' % perfil, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editperfilprofesional':
            try:
                f = PerfilProfesionalForm(request.POST)
                if f.is_valid():
                    perfil = PerfilProfesional.objects.get(pk = request.POST['id'])
                    perfil.resultados_aprendizaje= f.cleaned_data['resultados_aprendizaje']
                    perfil.perfil = f.cleaned_data['perfil']
                    perfil.save(request)
                    perfil.asignatura.clear()
                    for data in f.cleaned_data["asignatura"]:
                        perfil.asignatura.add(data)
                    request.session['pestaña'] = 'carreraParticipante'
                    request.session['vista'] = '3'
                    log(u'Edito perfil al proyecto: %s' % perfil, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addbeneficiario':
            try:
                f = BeneficiariosForm(request.POST)
                if f.is_valid():
                    beneficiario = Beneficiarios(
                        proyecto=ProyectosInvestigacion.objects.get(pk=request.POST['idproyecto']),
                        nombre=f.cleaned_data['nombre'],
                        direccion=f.cleaned_data['direccion'],
                        representante=f.cleaned_data['representante'],
                        cargo_repre=f.cleaned_data['cargo_repre'],
                        telefono=f.cleaned_data['telefono'],
                        correo=f.cleaned_data['correo'],
                        coordenadas=f.cleaned_data['coordenadas'],
                        num_beneficiario_directo=f.cleaned_data['num_beneficiario_directo'],
                        num_beneficiario_indirecto=f.cleaned_data['num_beneficiario_indirecto'],
                        especifico=f.cleaned_data['especifico'],
                        caracteristica=f.cleaned_data['caracteristica'],
                    )
                    beneficiario.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("proyecto_", newfile._name)

                        beneficiario.archivo = newfile
                        beneficiario.save(request)
                    request.session['pestaña'] = 'beneficiario'
                    request.session['vista'] = '4'
                    log(u'Adiciono beneficiario al proyecto: %s' % beneficiario, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editbeneficiario':
            try:
                f = BeneficiariosForm(request.POST)
                if f.is_valid():
                    beneficiario = Beneficiarios.objects.get(pk = request.POST['id'])
                    beneficiario.nombre = f.cleaned_data['nombre']
                    beneficiario.direccion = f.cleaned_data['direccion']
                    beneficiario.representante = f.cleaned_data['representante']
                    beneficiario.cargo_repre = f.cleaned_data['cargo_repre']
                    beneficiario.telefono = f.cleaned_data['telefono']
                    beneficiario.correo = f.cleaned_data['correo']
                    beneficiario.coordenadas = f.cleaned_data['coordenadas']
                    beneficiario.num_beneficiario_directo = f.cleaned_data['num_beneficiario_directo']
                    beneficiario.num_beneficiario_indirecto = f.cleaned_data['num_beneficiario_indirecto']
                    beneficiario.especifico = f.cleaned_data['especifico']
                    beneficiario.caracteristica = f.cleaned_data['caracteristica']

                    beneficiario.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("proyecto_", newfile._name)

                        beneficiario.archivo = newfile
                        beneficiario.save(request)
                    request.session['pestaña'] = 'beneficiario'
                    request.session['vista'] = '4'
                    log(u'Edito beneficiario al proyecto: %s' % beneficiario, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletebeneficiario':
            try:
                participante = Beneficiarios.objects.get(pk=request.POST['id'])
                participante.status = False
                log(u'Elimino beneficiario del proyecto: %s' % participante, request, "del")
                participante.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addinvolucrado':
            try:
                f = InvolucradoForm(request.POST)
                if f.is_valid():
                    involucrado = Involucrado(
                        proyecto=ProyectosInvestigacion.objects.get(pk=request.POST['idproyecto']),
                        nombre=f.cleaned_data['nombre'],
                        direccion=f.cleaned_data['direccion'],
                        representante=f.cleaned_data['representante'],
                        cargo_repre=f.cleaned_data['cargo_repre'],
                        telefono=f.cleaned_data['telefono'],
                        correo=f.cleaned_data['correo'],
                        coordenadas=f.cleaned_data['coordenadas'],
                        tipoActor=f.cleaned_data['tipoActor'],
                    )
                    involucrado.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("proyecto_", newfile._name)

                        involucrado.archivo = newfile
                        involucrado.save(request)
                    request.session['pestaña'] = 'beneficiario'
                    request.session['vista'] = '4'
                    log(u'Adiciono involucrado al proyecto: %s' % involucrado, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editinvolucrado':
            try:
                f = InvolucradoForm(request.POST)
                if f.is_valid():
                    involucrado = Involucrado.objects.get(pk = request.POST['id'])
                    involucrado.nombre = f.cleaned_data['nombre']
                    involucrado.direccion = f.cleaned_data['direccion']
                    involucrado.representante = f.cleaned_data['representante']
                    involucrado.cargo_repre = f.cleaned_data['cargo_repre']
                    involucrado.telefono = f.cleaned_data['telefono']
                    involucrado.correo = f.cleaned_data['correo']
                    involucrado.coordenadas = f.cleaned_data['coordenadas']
                    involucrado.tipoActor = f.cleaned_data['tipoActor']
                    involucrado.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("proyecto_", newfile._name)

                        involucrado.archivo = newfile
                        involucrado.save(request)
                    request.session['pestaña'] = 'beneficiario'
                    request.session['vista'] = '4'
                    log(u'Edito involucrado al proyecto: %s' % involucrado, request, "edi")
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteinvolucrado':
            try:
                involucrado = Involucrado.objects.get(pk=request.POST['id'])
                involucrado.status = False
                involucrado.save(request)
                log(u'Elimino involucrado del proyecto: %s' % involucrado, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'editArbolProblema':
            try:
                f = ArProblemaForm(request.POST)
                if f.is_valid():
                    # Arbol Problema
                    datos = ArbolProblema.objects.get(pk=(request.POST['id']))
                    datos.detalle = f.cleaned_data['detalle']
                    datos.editado = True
                    datos.save(request)
                    # Linea Base
                    datosLinBase = MatrizLineaBase.objects.get(arbolProblema_id=request.POST['id'])
                    datosLinBase.detalle = f.cleaned_data['detalle']
                    datosLinBase.editado = False
                    datosLinBase.save(request)
                    # Arbol Objetivo
                    datosArObj = ArbolObjetivo.objects.get(arbolProblema_id=request.POST['id'])
                    datosArObj.detalle = f.cleaned_data['detalle']
                    datosArObj.editado = False
                    datosArObj.save(request)
                    # Marco Logico
                    if MarcoLogico.objects.filter(arbolObjetivo_id=datosArObj.id).exists():
                        datosMarLogico = MarcoLogico.objects.get(arbolObjetivo_id=datosArObj.id)
                        datosMarLogico.resumen_narrativo = f.cleaned_data['detalle']
                        datosMarLogico.editado = False
                        datosMarLogico.save(request)

                    log(u'Edito Arbol de problema al proyecto: %s' % datos, request, "edit")
                    request.session['pestaña'] = 'aproblema'
                    request.session['vista'] = '5'
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addSubCausa':
            try:
                f = ArProblemaForm(request.POST)
                if f.is_valid():
                    auxCausa = ArbolProblema.objects.get(pk=(request.POST['id']))
                    auxSubCausa = len(ArbolProblema.objects.filter(status=True, parentID=auxCausa, tipo=2))
                    causa = ArbolProblema(
                        proyecto=ProyectosInvestigacion.objects.get(pk=(request.POST['pry'])),
                        parentID=ArbolProblema.objects.get(pk=(request.POST['id'])),
                        orden=auxCausa.orden + '.' + str(auxSubCausa + 1),
                        tipo=2,
                        editado=True,
                        detalle=f.cleaned_data['detalle'],
                    )
                    causa.save(request)
                    medio = ArbolObjetivo(
                        proyecto=ProyectosInvestigacion.objects.get(pk=(request.POST['pry'])),
                        arbolProblema=causa,
                        parentID=ArbolObjetivo.objects.get(arbolProblema_id=(request.POST['id'])),
                        orden=auxCausa.orden + '.' + str(auxSubCausa + 1),
                        tipo=2,
                        detalle=f.cleaned_data['detalle'],
                    )
                    medio.save(request)
                    causalinBase = MatrizLineaBase(
                        proyecto=ProyectosInvestigacion.objects.get(pk=(request.POST['pry'])),
                        arbolProblema=causa,
                        descripcion=f.cleaned_data['detalle'],
                    )
                    causalinBase.save(request)
                    acciones = MarcoLogico(
                        proyecto=ProyectosInvestigacion.objects.get(pk=(request.POST['pry'])),
                        arbolObjetivo=medio,
                        resumen_narrativo=f.cleaned_data['detalle'],
                    )
                    acciones.save(request)

                    log(u'Adiciono subcausa Arbol de problema al proyecto: %s' % auxCausa, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addCausaEfecto':
            try:
                f = ArProb_CausaEfectoForm(request.POST)
                if f.is_valid():
                    auxCausa = len(
                        ArbolProblema.objects.filter(proyecto=request.POST['pry'], status=True,parentID=None, tipo=2))
                    auxEfecto = len(
                        ArbolProblema.objects.filter(proyecto=request.POST['pry'], status=True,parentID=None, tipo=3))
                    # Arbol Problema
                    causa = ArbolProblema(
                        proyecto=ProyectosInvestigacion.objects.get(pk=request.POST['pry']),
                        detalle=f.cleaned_data['causa'],
                        tipo=2,
                        orden=auxCausa + 1,
                        editado=True,
                    )
                    causa.save(request)
                    efecto = ArbolProblema(
                        proyecto=ProyectosInvestigacion.objects.get(pk=request.POST['pry']),
                        detalle=f.cleaned_data['efecto'],
                        tipo=3,
                        orden=auxCausa + 1,
                        editado=True,
                    )
                    efecto.save(request)
                    # Linea base
                    causalinBase = MatrizLineaBase(
                        proyecto=ProyectosInvestigacion.objects.get(pk=request.POST['pry']),
                        arbolProblema=causa,
                        # descripcion=f.cleaned_data['causa'],
                    )
                    causalinBase.save(request)
                    efectolinBase = MatrizLineaBase(
                        proyecto=ProyectosInvestigacion.objects.get(pk=request.POST['pry']),
                        arbolProblema=efecto,
                        descripcion=f.cleaned_data['efecto'],
                    )
                    efectolinBase.save(request)
                    # Arbol Objetivo
                    medio = ArbolObjetivo(
                        proyecto=ProyectosInvestigacion.objects.get(pk=request.POST['pry']),
                        arbolProblema=causa,
                        detalle=f.cleaned_data['causa'],
                        tipo=2,
                        orden=auxCausa + 1,
                    )
                    medio.save(request)
                    fin = ArbolObjetivo(
                        proyecto=ProyectosInvestigacion.objects.get(pk=request.POST['pry']),
                        arbolProblema=efecto,
                        detalle=f.cleaned_data['efecto'],
                        tipo=3,
                        orden=auxEfecto + 1,
                    )
                    fin.save(request)
                    # Marco Logico
                    componente = MarcoLogico(
                        proyecto=ProyectosInvestigacion.objects.get(pk=request.POST['pry']),
                        arbolObjetivo=medio,
                        resumen_narrativo=f.cleaned_data['causa'],
                        editado=True,
                    )
                    componente.save(request)
                    # fin
                    finalidad = MarcoLogico(
                        proyecto=ProyectosInvestigacion.objects.get(pk=request.POST['pry']),
                        arbolObjetivo=ArbolObjetivo.objects.get(pk=fin.pk),
                        resumen_narrativo=fin.detalle,
                    )
                    finalidad.save(request)

                    #subcausas
                    auxSubCausa = len(ArbolProblema.objects.filter(status=True, parentID=causa, tipo=2))
                    subcausa = ArbolProblema(
                        proyecto=ProyectosInvestigacion.objects.get(pk=(request.POST['pry'])),
                        parentID=causa,
                        orden=str(causa.orden) + '.' + str(auxSubCausa + 1),
                        tipo=2,
                        detalle=f.cleaned_data['causa'],
                    )
                    subcausa.save(request)
                    medio = ArbolObjetivo(
                        proyecto=ProyectosInvestigacion.objects.get(pk=(request.POST['pry'])),
                        arbolProblema=subcausa,
                        parentID=ArbolObjetivo.objects.get(arbolProblema=causa),
                        orden=str(causa.orden) + '.' + str(auxSubCausa + 1),
                        tipo=2,
                        detalle=f.cleaned_data['causa'],
                    )
                    medio.save(request)
                    causalinBase = MatrizLineaBase(
                        proyecto=ProyectosInvestigacion.objects.get(pk=(request.POST['pry'])),
                        arbolProblema=subcausa,
                        descripcion=f.cleaned_data['causa'],
                    )
                    causalinBase.save(request)
                    acciones = MarcoLogico(
                        proyecto=ProyectosInvestigacion.objects.get(pk=(request.POST['pry'])),
                        arbolObjetivo=medio,
                        resumen_narrativo=f.cleaned_data['causa'],
                    )
                    acciones.save(request)

                    log(u'Adiciono causa efecto Arbol de problema al proyecto: %s' % auxCausa, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteArbolProblema':
            try:
                total = 0.0
                if ArbolProblema.objects.filter(status=True,parentID_id=request.POST['id']).exists():
                    subelemento = ArbolProblema.objects.filter(status=True,parentID_id=request.POST['id'])
                    for sub in subelemento:
                        arPro = ArbolProblema.objects.get(id=sub.pk)
                        arPro.status = False
                        arPro.save(request)
                        arObj = ArbolObjetivo.objects.get(arbolProblema_id=arPro.id)
                        arObj.status = False
                        arObj.save(request)
                        linBase = MatrizLineaBase.objects.get(arbolProblema_id=arPro.id)
                        linBase.status = False
                        linBase.save(request)
                        if MarcoLogico.objects.filter(arbolObjetivo_id=arObj.id).exists():
                            marLogi = MarcoLogico.objects.get(arbolObjetivo_id=arObj.id)
                            marLogi.status = False
                            marLogi.save(request)
                        if Presupuesto.objects.filter(status=True, aobjetivo=arObj).exists():
                            presupuesto = Presupuesto.objects.filter(status=True, aobjetivo=arObj)
                            for presupuesto in presupuesto:
                                presupuesto.status = False
                                presupuesto.save(request)
                            for pre in Presupuesto.objects.filter(status=True, proyecto=arObj.proyecto):
                                total = total + float(pre.total)
                            pry = ProyectosInvestigacion.objects.get(id=arObj.proyecto.id)
                            pry.valorpresupuestointerno = total
                            pry.save(request)

                if not ArbolProblema.objects.filter(status=True,parentID_id=request.POST['id']).exists():
                    arPro = ArbolProblema.objects.get(id=request.POST['id'])
                    arPro.status = False
                    arPro.save(request)
                    arObj = ArbolObjetivo.objects.get(arbolProblema_id=arPro.id)
                    arObj.status = False
                    arObj.save(request)
                    linBase = MatrizLineaBase.objects.get(arbolProblema_id=arPro.id)
                    linBase.status = False
                    linBase.save(request)
                    if MarcoLogico.objects.filter(arbolObjetivo_id=arObj.id).exists():
                        marLogi = MarcoLogico.objects.get(arbolObjetivo_id=arObj.id)
                        marLogi.status = False
                        marLogi.save(request)
                    if Presupuesto.objects.filter(status=True, aobjetivo=arObj).exists():
                        presupuesto = Presupuesto.objects.filter(status=True, aobjetivo=arObj)
                        for presupuesto in presupuesto:
                            presupuesto.status = False
                            presupuesto.save(request)
                        for pre in Presupuesto.objects.filter(status=True, proyecto=arObj.proyecto):
                            total = total + float(pre.total)
                        pry = ProyectosInvestigacion.objects.get(id=arObj.proyecto.id)
                        pry.valorpresupuestointerno = total
                        pry.save(request)

                    log(u'Elimino arbol de problema del proyecto: %s' % arPro, request, "del")



                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'datoLinea':
            try:
                dataRecibida = request.POST['val']
                proyecto = ProyectosInvestigacion.objects.get(pk=request.POST['pry'])
                if dataRecibida == 'true':
                    proyecto.linea_base = True
                else:
                    proyecto.linea_base = False
                proyecto.save(request)
                log(u'edito dato de linea base: %s' % proyecto, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addDatoSecundario':
            try:
                f = DatoSecundarioForm(request.POST)
                if f.is_valid():
                    datoSecundario = DatoSecundario(
                        proyecto=ProyectosInvestigacion.objects.get(pk=request.POST['pry']),
                        descripcion=f.cleaned_data['descripcion'],
                    )
                    datoSecundario.save(request)
                    request.session['pestaña'] = 'lineaBase'
                    request.session['vista'] = '6'
                    log(u'Adiciono dato secundario al proyecto: %s' % datoSecundario, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editDatoSecundario':
            try:
                f = DatoSecundarioForm(request.POST)
                if f.is_valid():
                    datos = DatoSecundario.objects.get(pk=request.POST['id'])
                    datos.descripcion = f.cleaned_data['descripcion']
                    datos.save(request)
                    request.session['pestaña'] = 'lineaBase'
                    request.session['vista'] = '6'
                    log(u'Edito dato secundario al proyecto: %s' % datos, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise ()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteDatoSecundario':
            try:
                datos = DatoSecundario.objects.get(id=request.POST['id'])
                datos.status = False
                datos.save(request)
                log(u'Elimino datos secundarios del proyecto: %s' % datos, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'editLineaBase':
            try:
                f = LineaBaseForm(request.POST)
                if f.is_valid():
                    datos = MatrizLineaBase.objects.get(pk=request.POST['id'])
                    datos.descripcion = f.cleaned_data['descripcion']
                    datos.metodo = f.cleaned_data['metodo']
                    datos.fuente = f.cleaned_data['fuente']
                    datos.datos_linea_base = f.cleaned_data['linea_base']
                    datos.editado = True
                    datos.save(request)
                    request.session['pestaña'] = 'lineaBase'
                    request.session['vista'] = '6'
                    log(u'Edito dato secundario al proyecto: %s' % datos, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise ()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editArbolObjetivo':
            try:
                f = ArObjetivoForm(request.POST)
                if f.is_valid():
                    datos = ArbolObjetivo.objects.get(pk=request.POST['id'])
                    datos.detalle = f.cleaned_data['detalle']
                    datos.editado = True
                    datos.save(request)
                    if MarcoLogico.objects.filter(arbolObjetivo_id=request.POST['id']).exists():
                        datosMarLogico = MarcoLogico.objects.get(arbolObjetivo_id=request.POST['id'])
                        datosMarLogico.resumen_narrativo = f.cleaned_data['detalle']
                        datosMarLogico.editado = False
                        datosMarLogico.save(request)
                    datos.save(request)
                    request.session['pestaña'] = 'arbol'
                    request.session['vista'] = '7'
                    log(u'Edito arbol de objetivo: %s' % datos, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise ()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editMarcoLogico':
            try:
                f = MarcoLogicoForm2(request.POST)
                if f.is_valid():
                    datos = MarcoLogico.objects.get(pk=request.POST['id'])
                    datos.resumen_narrativo = f.cleaned_data['resumen_narrativo']
                    datos.indicador = f.cleaned_data['indicador']
                    datos.fuente = f.cleaned_data['fuente']
                    datos.supuestos = f.cleaned_data['supuestos']
                    datos.cumplimiento = f.cleaned_data['cumplimiento']
                    datos.editado = True
                    datos.save(request)


                    acciones = ArbolObjetivo.objects.filter(parentID = datos.arbolObjetivo, status=True)
                    if acciones.exists():
                        if datos.cumplimiento == "0.00":
                            cumpl_acciones=0.00
                        else:
                            cumpl_acciones = float(datos.cumplimiento)/acciones.count()
                        for acc in acciones:
                            actividad = MarcoLogico.objects.get(arbolObjetivo=acc)
                            actividad.cumplimiento = cumpl_acciones
                            actividad.save(request)

                    request.session['pestaña'] = 'marco'
                    request.session['vista'] = '8'
                    log(u'Edito marco logico: %s' % datos, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise ()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addcronograma':
            try:
                f = CronogramaForm(request.POST)
                if f.is_valid():
                    aobj = ArbolObjetivo.objects.get(pk=request.POST['aObj'])
                    porcent = MarcoLogico.objects.get(arbolObjetivo=aobj).cumplimiento
                    tareas = Cronograma.objects.filter(status=True, aobjetivo=aobj)
                    if (f.cleaned_data['fecha_inicio'] >= aobj.proyecto.fechainicio and f.cleaned_data['fecha_inicio'] <= aobj.proyecto.fechaplaneacion) and (f.cleaned_data['fecha_fin'] >= aobj.proyecto.fechainicio and f.cleaned_data['fecha_fin'] <= aobj.proyecto.fechaplaneacion):
                        cronograma = Cronograma(
                            proyecto=aobj.proyecto,
                            aobjetivo=aobj,
                            descripcion=f.cleaned_data['descripcion'],
                            fecha_inicio=f.cleaned_data['fecha_inicio'],
                            fecha_fin=f.cleaned_data['fecha_fin'],
                        )
                        cronograma.save(request)

                        cronograma.responsable.clear()
                        for resp in f.cleaned_data['responsable']:
                            cronograma.responsable.add(resp)

                        for tarea in tareas:
                            tarea.cumplimiento = porcent / tareas.count()
                            tarea.save(request)
                        request.session['pestaña'] = 'cronograma'
                        request.session['vista'] = '9'
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe ingresar una fecha dentro del rango de ejecución"})
                        # fechainicio__lte = datetime.now(), fechafin__gte = datetime.now()

                    log(u'Adiciono cronograma al proyecto: %s' % cronograma, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcronograma':
            try:
                f = CronogramaForm(request.POST)
                if f.is_valid():
                    datos = Cronograma.objects.get(pk=request.POST['id'])
                    if (f.cleaned_data['fecha_inicio'] >= datos.proyecto.fechainicio and f.cleaned_data['fecha_inicio'] <= datos.proyecto.fechaplaneacion) and (f.cleaned_data['fecha_fin'] >= datos.proyecto.fechainicio and f.cleaned_data['fecha_fin'] <= datos.proyecto.fechaplaneacion):

                        datos.descripcion = f.cleaned_data['descripcion']
                        datos.fecha_inicio = f.cleaned_data['fecha_inicio']
                        datos.fecha_fin = f.cleaned_data['fecha_fin']
                        datos.save(request)

                        datos.responsable.clear()
                        for resp in f.cleaned_data['responsable']:
                            datos.responsable.add(resp)
                        request.session['pestaña'] = 'cronograma'
                        request.session['vista'] = '9'
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe ingresar una fecha dentro del rango de ejecución"})
                    log(u'edito cronograma al proyecto: %s' % datos, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletecronograma':
            try:
                datos = Cronograma.objects.get(id=request.POST['id'])
                aobj = ArbolObjetivo.objects.get(pk=datos.aobjetivo.pk)
                datos.status = False
                datos.save(request)

                porcent = MarcoLogico.objects.get(arbolObjetivo=aobj).cumplimiento
                tareas = Cronograma.objects.filter(status=True, aobjetivo=aobj)

                for tarea in tareas:
                    tarea.cumplimiento = porcent / tareas.count()
                    tarea.save(request)
                request.session['pestaña'] = 'cronograma'
                request.session['vista'] = '9'

                log(u'Elimino cronograma del proyecto: %s' % datos, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addpresupuesto':
            try:
                f = PresupuestoForm(request.POST)
                if f.is_valid():
                    aobj = ArbolObjetivo.objects.get(pk=request.POST['aObj'])
                    pry = ProyectosInvestigacion.objects.get(pk=aobj.proyecto.pk)
                    presupuesto = Presupuesto(
                        proyecto=aobj.proyecto,
                        aobjetivo=aobj,
                        cantidad=f.cleaned_data['cantidad'],
                        suministro=f.cleaned_data['suministro'],
                        costo_unitario=f.cleaned_data['costo_unitario'],
                        subtotal=f.cleaned_data['subtotal'],
                        iva=f.cleaned_data['iva'],
                        total=f.cleaned_data['total'],
                        especificaciones=f.cleaned_data['especificaciones'],
                    )
                    presupuesto.save(request)
                    total = 0.0
                    for pre in Presupuesto.objects.filter(status=True, proyecto=pry):
                        total = total + float(pre.total)
                    pry.valorpresupuestointerno = total
                    pry.save(request)
                    request.session['pestaña'] = 'presupuesto'
                    request.session['vista'] = '10'
                    log(u'Adiciono presupuesto al proyecto: %s' % presupuesto, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editpresupuesto':
            try:
                f = PresupuestoForm(request.POST)
                if f.is_valid():
                    datos = Presupuesto.objects.get(pk=request.POST['id'])
                    pry = ProyectosInvestigacion.objects.get(pk=datos.proyecto.pk)
                    datos.cantidad = f.cleaned_data['cantidad']
                    datos.producto = None
                    datos.suministro = f.cleaned_data['suministro']
                    datos.insumo = None
                    datos.costo_unitario = f.cleaned_data['costo_unitario']
                    datos.subtotal = f.cleaned_data['subtotal']
                    datos.iva = f.cleaned_data['iva']
                    datos.total = f.cleaned_data['total']
                    datos.otros = False
                    datos.especificaciones = f.cleaned_data['especificaciones']
                    datos.save(request)

                    total = 0.0
                    for pre in Presupuesto.objects.filter(status=True, proyecto=pry):
                        total = total + float(pre.total)
                    pry.valorpresupuestointerno = total
                    pry.save(request)

                    request.session['pestaña'] = 'presupuesto'
                    request.session['vista'] = '10'
                    log(u'Edito presupuesto al proyecto: %s' % datos, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletepresupuesto':
            try:
                datos = Presupuesto.objects.get(id=request.POST['id'])
                datos.status = False
                datos.save(request)
                log(u'Elimino presupuesto del proyecto: %s' % datos, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addredaccion':
            try:
                f = RedaccionForm(request.POST)
                if f.is_valid():
                    redaccion = Problema(
                        proyecto=ProyectosInvestigacion.objects.get(pk=request.POST['pry']),
                        descripcion=f.cleaned_data['descripcion'],
                        antecedentes=f.cleaned_data['antecedentes'],
                        deteccion_necesidades=f.cleaned_data['deteccion_necesidades'],
                        justificacion=f.cleaned_data['justificacion'],
                        Pertinencia=f.cleaned_data['Pertinencia'],
                        metodologia=f.cleaned_data['metodologia'],
                        seguimiento=f.cleaned_data['seguimiento'],
                        evaluacion=f.cleaned_data['evaluacion'],
                        producto=f.cleaned_data['producto'],
                        Bibliografia=f.cleaned_data['Bibliografia'],
                        objetivo_general=f.cleaned_data['objetivo_general'],
                        objetivos_especificos=f.cleaned_data['objetivos_especificos'],
                        convenio=f.cleaned_data['convenio'],
                    )
                    redaccion.save(request)
                    request.session['pestaña'] = 'redaccion'
                    request.session['vista'] = '11'
                    log(u'Adiciono redaccion al proyecto: %s' % redaccion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editredaccion':
            try:
                f = RedaccionForm(request.POST)
                if f.is_valid():
                    datos = Problema.objects.get(pk=request.POST['id'])
                    datos.descripcion = f.cleaned_data['descripcion']
                    datos.antecedentes = f.cleaned_data['antecedentes']
                    datos.deteccion_necesidades = f.cleaned_data['deteccion_necesidades']
                    datos.justificacion = f.cleaned_data['justificacion']
                    datos.Pertinencia = f.cleaned_data['Pertinencia']
                    datos.metodologia = f.cleaned_data['metodologia']
                    datos.seguimiento = f.cleaned_data['seguimiento']
                    datos.evaluacion = f.cleaned_data['evaluacion']
                    datos.producto = f.cleaned_data['producto']
                    datos.Bibliografia = f.cleaned_data['Bibliografia']
                    datos.objetivo_general = f.cleaned_data['objetivo_general']
                    datos.objetivos_especificos = f.cleaned_data['objetivos_especificos']
                    datos.convenio = f.cleaned_data['convenio']
                    datos.save(request)
                    request.session['pestaña'] = 'redaccion'
                    request.session['vista'] = '11'
                    log(u'edito redaccion al proyecto: %s' % datos, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addanexo':
            try:
                f = AnexosForm(request.POST)
                if f.is_valid():
                    anexo = Anexos(
                        proyecto=ProyectosInvestigacion.objects.get(pk=request.POST['pry']),
                        titulo=f.cleaned_data['titulo'],
                    )
                    anexo.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("proyecto_", newfile._name)

                        anexo.archivo = newfile
                        anexo.save(request)

                    log(u'Adiciono anexo al proyecto: %s' % anexo, request, "add")
                    request.session['pestaña'] = 'anexo'
                    request.session['vista'] = '12'
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editanexo':
            try:
                f = AnexosForm(request.POST)
                if f.is_valid():
                    anexo = Anexos.objects.get(pk=request.POST['id'])
                    anexo.titulo = f.cleaned_data['titulo']
                    anexo.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("proyecto_", newfile._name)

                        anexo.archivo = newfile
                        anexo.save(request)

                    log(u'Edito anexo al proyecto: %s' % anexo, request, "edit")
                    request.session['pestaña'] = 'anexo'
                    request.session['vista'] = '12'
                    return JsonResponse({"result": "ok"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteanexo':
            try:
                datos = Anexos.objects.get(id=request.POST['id'])
                datos.status = False
                datos.save(request)
                log(u'Elimino anexo del proyecto: %s' % datos, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'solicitarevision':
            try:
                datos = ProyectosInvestigacion.objects.get(id=request.POST['id'])
                if FechaProyectos.objects.values('id').filter(status=True, fechainicio__lte=datetime.now(),fechafin__gte=datetime.now()).exists():
                    conv = FechaProyectos.objects.filter(status=True, fechainicio__lte=datetime.now(),
                                                         fechafin__gte=datetime.now()).last()
                    datos.convocatoria = conv
                    datos.aprobacion = 4
                    datos.save(request)
                    log(u'Solicito revision de proyecto: %s' % datos, request, "edit")
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Actualmente no existe un periodo de convocatoria activa para solicitar revisión"})
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addfechafinp':
            try:

                f = FechaFinProyectoFrom(request.POST)
                proyecto = ProyectosInvestigacion.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    proyecto.fechareal = f.cleaned_data['fechafin']
                    proyecto.save(request)
                    log(u'Añadió fecha fin: %s' % proyecto.nombre, request, "add")
                    return JsonResponse({"result": "ok"})

                else:

                    raise NameError('Error')

            except Exception as ex:

                transaction.set_rollback(True)

                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'aprobarsolicitudproyecto':
            try:
                participante = ProyectoVinculacionInscripcion.objects.get(pk=request.POST['id'])
                participante.estado=2
                participante.save(request)

                if not ParticipantesMatrices.objects.filter(proyecto=participante.proyectovinculacion,inscripcion=participante.inscripcion, status=True).exists():
                    programas = ParticipantesMatrices(matrizevidencia_id=2,
                                                      proyecto=participante.proyectovinculacion,
                                                      inscripcion=participante.inscripcion,
                                                      horas=0,
                                                      preinscripcion = participante,
                                                      )
                    programas.save(request)

                    saludo = 'Estimada ' if participante.inscripcion.persona.sexo_id == 1 else 'Estimado '
                    notificacion = Notificacion(titulo=f"Estado de solicitud de participación en proyectos de vinculación",
                                                cuerpo=f"{saludo}  {participante.inscripcion.persona.nombre_completo_inverso()}, su preinscripción al proyecto de vinculación {programas.proyecto.nombre} ha sido aprobada",
                                                destinatario=participante.inscripcion.persona,
                                                url="/alu_proyectovinculacion?panel=3",
                                                fecha_hora_visible=datetime.now() + timedelta(days=2),
                                                content_type=None,
                                                object_id=None,
                                                prioridad=1,
                                                app_label='sga')
                    notificacion.save()

                    asunto = "Solicitud de Proyecto de Vinculación aprobada."
                    mensaje = "ha sido revisado su informe"
                    template = "emails/aceptacion_preinscripcion_vinc.html"
                    datos = {'sistema': u'SGA - UNEMI',
                             'mensaje': mensaje,
                             'fecha': datetime.now().date(),
                             'hora': datetime.now().time(),
                             'saludo': 'Estimada' if programas.inscripcion.persona.sexo_id == 1 else 'Estimado',
                             'estudiante': programas.inscripcion.persona.nombre_completo_inverso(),
                             'proyecto': programas.proyecto.nombre,
                             'autoridad2': '',
                             't': miinstitucion()
                             }
                    email = programas.inscripcion.persona.lista_emails_envio()

                    send_html_mail(asunto, template, datos, email, [], cuenta=variable_valor('CUENTAS_CORREOS')[0])
                    #log(u'Aprobo solicitud proyecto vinparticipantesproyectosculacion docente: %s' % participante, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'deleteparticipanteproyecto':
            try:

                participantes = ParticipantesMatrices.objects.get(pk=request.POST['id'])
                solicitudes = ProyectoVinculacionInscripcion.objects.filter(status=True,
                                                                              inscripcion=participantes.inscripcion,
                                                                              proyectovinculacion=participantes.proyecto)
                if solicitudes.exists():
                    solicitud= ProyectoVinculacionInscripcion.objects.get(status=True,inscripcion=participantes.inscripcion,proyectovinculacion=participantes.proyecto)

                    solicitud.status = False
                    solicitud.save(request)
                    participantes.save(request)

                participantes.status = False
                log(u'Elimino practicipante de investigación docente: %s' % participantes, request, "del")
                participantes.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'deletesolicitudproyecto':
            try:
                participante = ProyectoVinculacionInscripcion.objects.get(pk=request.POST['id'])
                participante.observacion = request.POST['observacion']
                participante.estado = 3
                participante.save(request)
                proyecto = ProyectosInvestigacion.objects.get(pk=participante.proyectovinculacion.id)
                saludo = 'Estimada '  if participante.inscripcion.persona.sexo_id == 1 else 'Estimado '
                notificacion = Notificacion(titulo=f"Estado de solicitud de participación en proyectos de vinculación",
                                            cuerpo=f"{saludo}  {participante.inscripcion.persona.nombre_completo_inverso()}, su preinscripción al proyecto de vinculación {proyecto.nombre} ha sido rechazada",
                                            destinatario=participante.inscripcion.persona,
                                            url="/alu_proyectovinculacion?panel=3",
                                            fecha_hora_visible=datetime.now() + timedelta(days=2),
                                            content_type=None,
                                            object_id=None,
                                            prioridad=1,
                                            app_label='sga')
                notificacion.save()

                log(u'Elimino solicitud proyecto vinculacion docente: %s' % participante, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delevidencia':
            try:
                detalleevidenciasinformes = DetalleEvidenciasInformes.objects.get(pk=request.POST['id'])
                log(u'Elimino evidencia de informe: %s' % detalleevidenciasinformes, request, "del")
                detalleevidenciasinformes.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delmarcologico':
            try:
                marcologicoproyectosinvestigacion = MarcoLogicoProyectosInvestigacion.objects.get(pk=request.POST['id'])
                log(u'Elimino marco logico: %s' % marcologicoproyectosinvestigacion, request, "del")
                marcologicoproyectosinvestigacion.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'deletepresupuestoproyecto':
            try:
                presupuesto = PresupuestosProyecto.objects.get(pk=request.POST['id'])
                presupuesto.status = False
                log(u'Elimino presupuesto de proyecto de investigación docente: %s' % presupuesto, request, "del")
                presupuesto.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'editproyecto':
            try:
                f = ProyectoVinculacion1Form(request.POST)
                proyecto = ProyectosInvestigacion.objects.select_related().get(pk=request.POST['id'],tipo=1)
                if f.is_valid():
                    # bandera = False
                    # newfile = None
                    #
                    # if proyecto.objetivoplannacional:
                    # if proyecto.objetivoplannacional:
                    #     if proyecto.objetivoplannacional.id == f.cleaned_data['objetivoplannacional'].id:
                    #         bandera = True


                    proyecto.nombre = f.cleaned_data['nombre']
                    proyecto.fechainicio = f.cleaned_data['fechainicio']
                    # proyecto.fechafin=f.cleaned_data['fechafin']
                    proyecto.fechaplaneacion = f.cleaned_data['fechaPlanificacion']
                    proyecto.programa = f.cleaned_data['programa']
                    proyecto.tipo = 1
                    proyecto.tipoproinstitucion = f.cleaned_data['tipoproinstitucion']
                    proyecto.alcanceterritorial = f.cleaned_data['alcanceterritorial']
                    proyecto.areaconocimiento = f.cleaned_data['areaconocimiento']
                    proyecto.subareaconocimiento = f.cleaned_data['subareaconocimiento']
                    proyecto.subareaespecificaconocimiento = f.cleaned_data['subareaespecificaconocimiento']
                    proyecto.tiempoejecucion = f.cleaned_data['tiempoejecucion']
                    proyecto.lineainvestigacion = f.cleaned_data['lineainvestigacion']
                    proyecto.sublineainvestigacion = f.cleaned_data['sublineainvestigacion']
                    # proyecto.valorpresupuestointerno = f.cleaned_data['valorpresupuestointerno']
                    # proyecto.valorpresupuestoexterno = f.cleaned_data['valorpresupuestoexterno']
                    proyecto.sectorcoordenada = f.cleaned_data['sectorcoordenada']
                    # proyecto.presupuestototal = f.cleaned_data['valorpresupuestointerno'] + f.cleaned_data['valorpresupuestoexterno']
                    # proyecto.institucionbeneficiaria = f.cleaned_data['institucionbeneficiaria']
                    # proyecto.objetivoplannacional = f.cleaned_data['objetivoplannacional']
                    # proyecto.cupo = f.cleaned_data['cupo']
                    # proyecto.aprobacion = 5
                    # proyecto.saldoo = f.cleaned_data['cupo']

                    proyecto.objetivos_PND =  f.cleaned_data['objetivos_PND']
                    proyecto.politicas_PND = f.cleaned_data['politicas_PND']
                    proyecto.linea_accion = f.cleaned_data['linea_accion']
                    proyecto.estrategia_desarrollo = f.cleaned_data['estrategia_desarrollo']
                    proyecto.investigacion_institucional = f.cleaned_data['investigacion_institucional']
                    proyecto.necesidades_sociales = f.cleaned_data['necesidades_sociales']
                    proyecto.tiempo_duracion_horas = f.cleaned_data['tiempo_duracion_horas']
                    proyecto.circuito = f.cleaned_data['circuito']
                    proyecto.distrito = f.cleaned_data['distrito']
                    proyecto.save(request)
                    # proyecto.canton = f.cleaned_data['canton']
                    # proyecto.zona = f.cleaned_data['zona']
                    proyecto.canton.clear()
                    for cant in f.cleaned_data['canton']:
                        proyecto.canton.add(cant)
                    proyecto.zona.clear()
                    for z in f.cleaned_data['zona']:
                        proyecto.zona.add(z)
                    request.session['pestaña'] = 'datos'
                    request.session['vista'] = '1'
                    # proyecto.carrera = f.cleaned_data['carreras']
                    # lineas= f.cleaned_data['carreras']
                    # for lis in lineas:
                    #     detalle=ProyectosInvestigacionCarreras.objects.get(proyectovinculacion=proyecto,carreras_id=lis.id)
                    #     detalle.carreras=Carrera.objects.get(pk=int(lis.id))
                    #     detalle.save(request)



                    # cantones = f.cleaned_data['canton']

                    # for zona in zonas:
                    #     proyectozona = ProyectosInvestigacionZonas.objects.get(proyectovinculacion__id=proyecto.id, zona_id=zona.id)
                    #     proyectozona.proyectovinculacion=proyecto
                    #     proyectozona.zona=zona
                    #     proyectozona.save(request)
                    # for canton in cantones:
                    #     proyectocanton = ProyectosInvestigacionCantones.objects.get(proyectovinculacion__id=proyecto.id,
                    #                                                     canton_id=canton.id)
                    #     proyectocanton.canton=canton
                    #     proyectocanton.proyectovinculacion=proyecto
                    #     proyectocanton.save(request)

                    # if not bandera:
                    #     PoliticaProyectosInvestigacion.objects.filter(proyectovinculacion=proyecto).delete()
                    #     MetasPndProyectosInvestigacion.objects.filter(proyectovinculacion=proyecto).delete()
                    #     MetasZonalProyectosInvestigacion.objects.filter(proyectovinculacion=proyecto).delete()
                    #     MetasComplementariaProyectosInvestigacion.objects.filter(proyectovinculacion=proyecto).delete()
                    #     LineamientoProyectosInvestigacion.objects.filter(proyectovinculacion=proyecto).delete()
                    #     for p in PoliticasObjetivoPlanNacional.objects.filter(objetivo=f.cleaned_data['objetivoplannacional'], status=True):
                    #         politicaproyectosinvestigacion = PoliticaProyectosInvestigacion(proyectovinculacion=proyecto,
                    #                                                                         politica=p,
                    #                                                                         status=False)
                    #         politicaproyectosinvestigacion.save(request)
                    #     # metaspnd
                    #     for p in MetasPndPlanNacional.objects.filter(objetivo=f.cleaned_data['objetivoplannacional'], status=True):
                    #         metaspndproyectosinvestigacion = MetasPndProyectosInvestigacion(proyectovinculacion=proyecto,
                    #                                                                         metaspnd=p,
                    #                                                                         status=False)
                    #         metaspndproyectosinvestigacion.save(request)
                    #     # metaszona
                    #     for p in MetasZonalPlanNacional.objects.filter(objetivo=f.cleaned_data['objetivoplannacional'], status=True):
                    #         metaszonalproyectosinvestigacion = MetasZonalProyectosInvestigacion(proyectovinculacion=proyecto,
                    #                                                                             metaszonal=p,
                    #                                                                             status=False)
                    #         metaszonalproyectosinvestigacion.save(request)
                    #     # metascomplementaria
                    #     for p in MetasComplementariaPlanNacional.objects.filter(objetivo=f.cleaned_data['objetivoplannacional'], status=True):
                    #         metascomplementariaproyectosinvestigacion = MetasComplementariaProyectosInvestigacion(proyectovinculacion=proyecto,
                    #                                                                                               metascomplementaria=p,
                    #                                                                                               status=False)
                    #         metascomplementariaproyectosinvestigacion.save(request)
                    #     # lineamiento
                    #     for p in LineamientoPlanNacional.objects.filter(objetivo=f.cleaned_data['objetivoplannacional'], status=True):
                    #         lineamientoproyectosinvestigacion = LineamientoProyectosInvestigacion(proyectovinculacion=proyecto,
                    #                                                                               lineamiento=p,
                    #                                                                               status=False)
                    #         lineamientoproyectosinvestigacion.save(request)

                    log(u'Editó proyecto de investigación docente: %s' % proyecto, request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editmarcologico':
            try:
                f = MarcoLogicoForm(request.POST)
                marcologicoproyectosinvestigacion = MarcoLogicoProyectosInvestigacion.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    numero = f.cleaned_data['numero']
                    if marcologicoproyectosinvestigacion.tipo == 0 or marcologicoproyectosinvestigacion.tipo == 1:
                        numero = 0
                    marcologicoproyectosinvestigacion.resumen = f.cleaned_data['resumen']
                    marcologicoproyectosinvestigacion.indicadores = f.cleaned_data['indicadores']
                    marcologicoproyectosinvestigacion.fuentes = f.cleaned_data['fuentes']
                    marcologicoproyectosinvestigacion.supuestos = f.cleaned_data['supuestos']
                    marcologicoproyectosinvestigacion.numero = numero
                    marcologicoproyectosinvestigacion.save(request)
                    log(u'Editó marco logico: %s' % marcologicoproyectosinvestigacion, request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'politicaproyecto':
            try:
                f = ProyectoVinculacion2Form(request.POST)
                if f.is_valid():
                    proyectos = ProyectosInvestigacion.objects.get(pk=request.POST['id'], tipo=1)
                    if proyectos.proyectovinculacioncampos_set.filter(status=True).exists():
                        proyectovinculacioncampos = proyectos.proyectovinculacioncampos_set.filter(status=True)[0]
                        proyectovinculacioncampos.necesidadessociales = f.cleaned_data['necesidadessociales']
                        proyectovinculacioncampos.investigacioninstitucional = f.cleaned_data['investigacioninstitucional']
                        proyectovinculacioncampos.save(request)

                    if 'lista_items1' in request.POST:
                        PoliticaProyectosInvestigacion.objects.filter(proyectovinculacion=proyectos).update(status=False)
                        for politica in json.loads(request.POST['lista_items1']):
                            PoliticaProyectosInvestigacion.objects.filter(id=int(politica['id'])).update(status=True)
                    if 'lista_items2' in request.POST:
                        MetasPndProyectosInvestigacion.objects.filter(proyectovinculacion=proyectos).update(status=False)
                        for metaspnd in json.loads(request.POST['lista_items2']):
                            MetasPndProyectosInvestigacion.objects.filter(id=int(metaspnd['id'])).update(status=True)
                    if 'lista_items3' in request.POST:
                        MetasZonalProyectosInvestigacion.objects.filter(proyectovinculacion=proyectos).update(status=False)
                        for metaszonal in json.loads(request.POST['lista_items3']):
                            MetasZonalProyectosInvestigacion.objects.filter(id=int(metaszonal['id'])).update(status=True)
                    if 'lista_items4' in request.POST:
                        MetasComplementariaProyectosInvestigacion.objects.filter(proyectovinculacion=proyectos).update(status=False)
                        for metascomplementaria in json.loads(request.POST['lista_items4']):
                            MetasComplementariaProyectosInvestigacion.objects.filter(id=int(metascomplementaria['id'])).update(status=True)
                    if 'lista_items5' in request.POST:
                        LineamientoProyectosInvestigacion.objects.filter(proyectovinculacion=proyectos).update(status=False)
                        for lineamiento in json.loads(request.POST['lista_items5']):
                            LineamientoProyectosInvestigacion.objects.filter(id=int(lineamiento['id'])).update(status=True)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addevidenciasproyectos':
            try:
                f = EvidenciaForm(request.POST, request.FILES)
                # 2.5MB - 2621440
                # 5MB - 5242880
                # 10MB - 10485760
                # 20MB - 20971520
                # 50MB - 5242880
                # 100MB 104857600
                # 250MB - 214958080
                # 500MB - 429916160
                d = request.FILES['archivo']
                if d.size > 10485760:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                newfiles = request.FILES['archivo']
                newfilesd = newfiles._name
                ext = newfilesd[newfilesd.rfind("."):]
                if ext != '.pdf':
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf"})

                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("proyecto_", newfile._name)
                    if DetalleEvidencias.objects.filter(evidencia_id=request.POST['idevidencia'], proyecto_id=request.POST['id']).exists():
                        detalle = DetalleEvidencias.objects.get(evidencia_id=request.POST['idevidencia'], proyecto_id=request.POST['id'])
                        detalle.descripcion = f.cleaned_data['descripcion']
                        detalle.archivo = newfile
                        detalle.save(request)
                        log(u'Adiciono evidencia proyecto de investigación docente: %s' % detalle, request, "add")
                    else:
                        evidencia = DetalleEvidencias(evidencia_id=request.POST['idevidencia'],
                                                      proyecto_id=request.POST['id'],
                                                      descripcion=f.cleaned_data['descripcion'],
                                                      archivo=newfile)
                        evidencia.save(request)
                        log(u'Adiciono evidencia proyecto de investigación docente: %s' % evidencia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addevidenciasinforme':
            try:
                f = EvidenciaInformeForm(request.POST, request.FILES)
                # 2.5MB - 2621440
                # 5MB - 5242880
                # 10MB - 10485760
                # 20MB - 20971520
                # 50MB - 5242880
                # 100MB 104857600
                # 250MB - 214958080
                # 500MB - 429916160
                d = request.FILES['archivo']
                if d.size > 10485760:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                newfiles = request.FILES['archivo']
                newfilesd = newfiles._name
                ext = newfilesd[newfilesd.rfind("."):]
                if ext != '.pdf' and ext != '.jpg' and ext != '.png' :
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.jpg,.png"})

                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("proyecto_", newfile._name)
                    detalleevidenciasinformes = DetalleEvidenciasInformes(detalleinforme_id=request.POST['id'],
                                                                          descripcion=f.cleaned_data['descripcion'],
                                                                          archivo=newfile)
                    detalleevidenciasinformes.save(request)
                    log(u'Adiciono evidencia Informe de investigación docente: %s' % detalleevidenciasinformes, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteproyecto':
            try:
                proyecto = ProyectosInvestigacion.objects.get(pk=request.POST['id'],tipo=1)
                proyecto.status = False
                log(u'Eliminó proyecto de investigación docente: %s' % proyecto, request, "add")
                proyecto.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addparticipantesdocentesp':
            try:
                es_externo = False
                externo = None
                personae = None

                f = ParticipanteProfesorVinculacionForm(request.POST)

                if f.is_valid():
                    # Verificar que no esté repetido el integrante
                    if int(f.cleaned_data['tipo']) == 1:
                        if ParticipantesMatrices.objects.filter(proyecto_id=request.POST['id'], profesor_id=f.cleaned_data['profesor'], status=True).exists():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El docente ya se encuentra inscrito en el proyecto", "showSwal": "True", "swalType": "warning"})
                    else:
                        # Consulto la persona
                        personae = Persona.objects.get(pk=f.cleaned_data['profesor'])

                        # Verifico si tiene perfil externo
                        if Externo.objects.filter(persona=personae, status=True).exists():
                            es_externo = True
                            externo = Externo.objects.get(persona=personae, status=True)

                            if ParticipantesMatrices.objects.filter(proyecto_id=request.POST['id'], externo_id=externo.id, status=True).exists():
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El docente ya se encuentra inscrito en el proyecto", "showSwal": "True", "swalType": "warning"})

                    # Si no existe externo, se debe crear ese perfil, Docentes externos
                    if int(f.cleaned_data['tipo']) == 2:
                        if es_externo is False:
                            # Guardo externo
                            externo = Externo(
                                persona=personae,
                                nombrecomercial='',
                                institucionlabora='',
                                cargodesempena=''
                            )
                            externo.save(request)

                    if int(f.cleaned_data['tipo']) == 1:
                        distributivo = Profesor.objects.get(id=f.cleaned_data['profesor']).distributivohoraseval(periodo)
                    else:
                        distributivo = None

                    # Guardo el docente participante del proyecto
                    docente = ParticipantesMatrices(matrizevidencia_id=2,
                                                    proyecto_id=request.POST['id'],
                                                    profesor_id=f.cleaned_data['profesor'] if int(int(f.cleaned_data['tipo'])) == 1 else None,
                                                    externo_id=externo.id if int(int(f.cleaned_data['tipo'])) == 2 else None,
                                                    horas=f.cleaned_data['horas'] if int(int(f.cleaned_data['tipo'])) == 1 else 0,
                                                    tipoparticipante_id=2 if int(int(f.cleaned_data['tipo'])) == 1 else 5,
                                                    carrera=distributivo.carrera if distributivo else None
                                                    )
                    docente.save(request)

                    # Guardo los niveles
                    for niv in f.cleaned_data["nivel"]:
                        docente.nivel.add(niv)

                    request.session['pestaña'] = 'docentesParticipantes'
                    request.session['vista'] = '2'
                    log(u'%s adicionó participante docente: %s' % (persona, docente), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editparticipantesdocentes':
            try:
                es_externo = False
                externo = None
                personae = None

                f = ParticipanteProfesorVinculacionForm(request.POST)
                if f.is_valid():
                    tipodocente = int(request.POST['tipodocente'])

                    # Verificar que no esté repetido el integrante
                    if tipodocente == 1:
                        if ParticipantesMatrices.objects.filter(proyecto_id=request.POST['idproyecto'], profesor_id=f.cleaned_data['profesor'], status=True).exclude(pk=request.POST['id']).exists():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El docente ya se encuentra inscrito en el proyecto", "showSwal": "True", "swalType": "warning"})
                    else:
                        # Consulto la persona
                        personae = Persona.objects.get(pk=f.cleaned_data['profesor'])

                        # Verifico si tiene perfil externo
                        if Externo.objects.filter(persona=personae, status=True).exists():
                            es_externo = True
                            externo = Externo.objects.get(persona=personae, status=True)

                            if ParticipantesMatrices.objects.filter(proyecto_id=request.POST['idproyecto'], externo_id=externo.id, status=True).exclude(pk=request.POST['id']).exists():
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El docente ya se encuentra inscrito en el proyecto", "showSwal": "True", "swalType": "warning"})

                    docente = ParticipantesMatrices.objects.get(pk=request.POST['id'])

                    if tipodocente == 1:
                        docente.profesor = Profesor.objects.get(pk=f.cleaned_data['profesor'])
                        docente.horas = f.cleaned_data['horas']
                        docente.save(request)

                        docente.nivel.clear()
                        for niv in f.cleaned_data["nivel"]:
                            docente.nivel.add(niv)
                    else:
                        # Si no existe externo, se debe crear ese perfil, Docentes externos
                        if tipodocente == 2:
                            if es_externo is False:
                                # Guardo externo
                                externo = Externo(
                                    persona=personae,
                                    nombrecomercial='',
                                    institucionlabora='',
                                    cargodesempena=''
                                )
                                externo.save(request)

                        docente.externo = externo
                        docente.save(request)

                    request.session['pestaña'] = 'docentesParticipantes'
                    request.session['vista'] = '2'

                    log(u'%s editó participante docente: %s' % (persona, docente), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'adddocenteexterno':
            try:
                if not 'idp' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                f = DocenteExternoForm(request.POST)

                if f.is_valid():
                    # Verifica si existe la persona
                    if Persona.objects.values('id').filter(Q(cedula=f.cleaned_data['cedula'])|Q(pasaporte=f.cleaned_data['cedula']), status=True).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La persona ya está registrada en la base de datos", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['pasaporte']:
                        if Persona.objects.values('id').filter(Q(cedula=f.cleaned_data['pasaporte'])|Q(pasaporte=f.cleaned_data['pasaporte']), status=True).exists():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La persona ya está registrada en la base de datos", "showSwal": "True", "swalType": "warning"})

                    # proyecto = ProyectosInvestigacion.objects.get(pk=int(encrypt(request.POST['idp'])))
                    proyecto = ProyectosInvestigacion.objects.get(pk=request.POST['idp'])

                    # Guardo la persona
                    personaexterna = Persona(
                        nombres=f.cleaned_data['nombres'],
                        apellido1=f.cleaned_data['apellido1'],
                        apellido2=f.cleaned_data['apellido2'],
                        cedula=f.cleaned_data['cedula'],
                        pasaporte=f.cleaned_data['pasaporte'],
                        nacimiento=f.cleaned_data['nacimiento'],
                        sexo=f.cleaned_data['sexo'],
                        nacionalidad=f.cleaned_data['nacionalidad'],
                        email=f.cleaned_data['email'].strip().lower(),
                        telefono=f.cleaned_data['telefono']
                    )
                    personaexterna.save(request)

                    # Guardo externo
                    externo = Externo(
                        persona=personaexterna,
                        nombrecomercial='',
                        institucionlabora=f.cleaned_data['institucionlabora'],
                        cargodesempena=f.cleaned_data['cargodesempena']
                    )
                    externo.save(request)

                    #Creo perfil externo
                    personaexterna.crear_perfil(externo=externo)
                    personaexterna.mi_perfil()
                    log(u'Agregó persona externa: %s' % (personaexterna), request, "add")

                    # Asigno la persona externa al proyecto con la función que cumple
                    integranteproyecto = ParticipantesMatrices(
                        matrizevidencia_id=2,
                        proyecto_id=request.POST['idp'],
                        profesor_id=None,
                        externo_id=externo.id,
                        horas=0,
                        tipoparticipante_id=5
                    )
                    integranteproyecto.save(request)

                    log(u'%s agregó integrante al proyecto: %s - %s' % (persona, proyecto, personaexterna), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addmarcologico':
            try:
                f = MarcoLogicoForm(request.POST)
                if f.is_valid():
                    proyecto = ProyectosInvestigacion.objects.get(pk=request.POST['id'], tipo=1)
                    numero = f.cleaned_data['numero']
                    if f.cleaned_data['tipo'] == '0':
                        numero = 0
                        if proyecto.marcologicoproyectosinvestigacion_set.filter(status=True, tipo=0).count()>=1:
                            return JsonResponse({"result": "r","mensaje": u"Solo puede ingresar un Tipo Fin."})
                    if f.cleaned_data['tipo'] == '1':
                        numero = 0
                        if proyecto.marcologicoproyectosinvestigacion_set.filter(status=True, tipo=1).count()>=1:
                            return JsonResponse({"result": "r","mensaje": u"Solo puede ingresar un Tipo Propósito."})

                    marcologicoproyectosinvestigacion = MarcoLogicoProyectosInvestigacion(proyectovinculacion=proyecto,
                                                                                          tipo=f.cleaned_data['tipo'],
                                                                                          resumen=f.cleaned_data['resumen'],
                                                                                          indicadores=f.cleaned_data['indicadores'],
                                                                                          fuentes=f.cleaned_data['fuentes'],
                                                                                          supuestos=f.cleaned_data['supuestos'],
                                                                                          numero=numero)
                    marcologicoproyectosinvestigacion.save(request)
                    log(u'Adiciono marco logico: %s' % marcologicoproyectosinvestigacion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addparticipantesestudiantes':
            try:
                f = ParticipanteEstudianteForm(request.POST)
                if f.is_valid():
                    datainscripcion = Inscripcion.objects.get(pk=int(f.cleaned_data['inscripcion']))
                    if ParticipantesMatrices.objects.filter(proyecto_id=request.POST['id'], inscripcion__persona=datainscripcion.persona, status=True).exists():
                        return JsonResponse({"result": "r", "mensaje": u"Error el estudiante ya se encuentra inscrito en el proyecto."})
                    programas = ParticipantesMatrices(matrizevidencia_id=2,
                                                      proyecto_id=request.POST['id'],
                                                      inscripcion_id=f.cleaned_data['inscripcion'],
                                                      horas=f.cleaned_data['horas']
                                                      )
                    programas.save(request)
                    log(u'Adiciono participante estudiante proyecto de investigación docente: %s' % programas, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delparticipantesproyectos':
            try:
                nompersona = ''
                proyecto = ProyectosInvestigacion.objects.get(pk=request.POST['idproyecto'],tipo=1,status=True)
                participantes = ParticipantesMatrices.objects.filter(proyecto=proyecto,status=True)
                participantes1 = ProyectoVinculacionInscripcion.objects.filter(status=True,proyectovinculacion=proyecto)
                for participante1 in participantes1:
                    participante1.status = False
                    participante1.save(request)
                for participante in participantes:
                    participante.status = False
                    if participante.inscripcion:
                        nompersona = ' ESTUDIANTE ' + participante.inscripcion.persona.apellido1 + ' ' + participante.inscripcion.persona.apellido2 + ' ' + participante.inscripcion.persona.nombres
                    if participante.profesor:
                        nompersona = ' DOCENTE ' + participante.profesor.persona.apellido1 + ' ' + participante.profesor.persona.apellido2 + ' ' + participante.profesor.persona.nombres
                    if participante.administrativo:
                        nompersona = ' ADMINISTRATIVO ' + participante.administrativo.persona.apellido1 + ' ' + participante.administrativo.persona.apellido2 + ' ' + participante.administrativo.persona.nombres
                    participante.save(request)
                    log(u'Eliminación masiva de participantes de proyectos docente: %s - %s' % (proyecto, nompersona), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al solicitar cupo."})

        elif action == 'addparticipantesadministrativos':
            try:
                f = ParticipanteAdministrativoForm(request.POST)
                if f.is_valid():
                    if ParticipantesMatrices.objects.filter(proyecto_id=request.POST['id'],administrativo_id=f.cleaned_data['administrativo'],status=True).exists():
                        return JsonResponse({"result": "r","mensaje": u"Error personal administrativo ya se encuentra inscrito en el proyecto."})
                    programas = ParticipantesMatrices(matrizevidencia_id=2,
                                                      proyecto_id=request.POST['id'],
                                                      administrativo_id=f.cleaned_data['administrativo'],
                                                      horas=f.cleaned_data['horas']
                                                      )
                    programas.save(request)
                    log(u'Adiciono participante Administrativo programa de investigación docente: %s' % programas, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'updatehoras':
            try:
                participantes = ParticipantesMatrices.objects.get(pk=request.POST['indi'])
                valor = int(request.POST['valor'])
                cupoanterior = participantes.horas
                participantes.horas = valor
                participantes.save(request)
                return JsonResponse({'result': 'ok', 'valor': participantes.horas})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad'})

        elif action == 'updatetipoparticipante':
            try:
                participantes = ParticipantesMatrices.objects.get(pk=request.POST['idparticipante'])
                tipopar = request.POST['tipoparticipante']
                tipoparanterior = participantes.tipoparticipante_id
                participantes.tipoparticipante_id = tipopar
                participantes.save(request)
                log(u'Editó tipo de participante de investigación docente: %s' % participantes, request, "add")
                return JsonResponse({'result': 'ok', 'valor': participantes.tipoparticipante_id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad'})

        elif action == 'addcarrerasproyectos':
            try:
                idproyecto = request.POST['idproyecto']
                carrerasproyectos = CarrerasProyecto.objects.filter(proyecto_id=int(idproyecto))
                carrerasproyectos.delete()
                lista = request.POST['listacarrerasproyecto']
                listacantidad = request.POST['listacantidadproyecto']
                listanivel = request.POST['listanivelproyecto']
                if lista:
                    elementos = lista.split(',')
                    elementoscantidad = listacantidad.split(',')
                    elementosnivel = listanivel.split(',')
                    i=0
                    for elemento in elementos:
                        addcarrera = CarrerasProyecto(carrera_id=int(elemento),proyecto_id=int(idproyecto), cantidad=int(elementoscantidad[i]), nivelmalla_id=int(elementosnivel[i]))
                        addcarrera.save(request)
                        i+=1
                        log(u'Adiciono carreras de proyecto de investigación docente: %s' % addcarrera, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addpresupuestoproyectos':
            try:
                idproyecto = request.POST['idproyecto']
                presupuesto = PresupuestosProyecto(anioejecucion=int(request.POST['anioejecucion']),
                                                   planificado=float(request.POST['planificado']),
                                                   ejecutado=float(request.POST['ejecutado']),
                                                   proyecto_id=int(idproyecto))
                presupuesto.save(request)
                log(u'Adiciono presupuesto de  proyectos de investigación docente: %s' % presupuesto, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addinforme':
            try:
                f = FechaInformeForm(request.POST,request.FILES)
                if f.is_valid():
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                    proyecto = ProyectosInvestigacion.objects.get(pk=request.POST['id'], tipo=1, status=True)
                    if InformeMarcoLogicoProyectosInvestigacion.objects.filter(proyectovinculacion=proyecto,fecha=f.cleaned_data['fecha'],status=True).exists():
                        return JsonResponse({"result": "r","mensaje": u"Ya existe un informe en esa fecha."})

                    fecha = f.cleaned_data['fecha']
                    mes = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
                           "Octubre", "Noviembre", "Diciembre"]
                    fecha = mes[fecha.month-1]
                    informemarcologicoproyectosinvestigacion = InformeMarcoLogicoProyectosInvestigacion(proyectovinculacion=proyecto,
                                                                                                        fecha=f.cleaned_data['fecha'],
                                                                                                        archivo=newfile,
                                                                                                        descripcion=fecha.upper())
                    informemarcologicoproyectosinvestigacion.save(request)
                    marcologicoproyectosinvestigacionfines = proyecto.marcologicoproyectosinvestigacion_set.filter(status=True, tipo=0).order_by('id')
                    marcologicoproyectosinvestigacionpropositos = proyecto.marcologicoproyectosinvestigacion_set.filter(status=True, tipo=1).order_by('id')
                    marcologicoproyectosinvestigacioncomponentes = proyecto.marcologicoproyectosinvestigacion_set.filter(status=True, tipo=2).order_by('id')
                    marcologicoproyectosinvestigacionacciones = proyecto.marcologicoproyectosinvestigacion_set.filter(status=True, tipo=3).order_by('id')
                    for marcologicoproyectosinvestigacionfin in marcologicoproyectosinvestigacionfines:
                        detalleinforme = DetalleInforme(informemarcologicoproyectosinvestigacion= informemarcologicoproyectosinvestigacion,
                                                        marcologicoproyectosinvestigacion=marcologicoproyectosinvestigacionfin)
                        detalleinforme.save(request)

                    for marcologicoproyectosinvestigacionproposito in marcologicoproyectosinvestigacionpropositos:
                        detalleinforme = DetalleInforme(informemarcologicoproyectosinvestigacion= informemarcologicoproyectosinvestigacion,
                                                        marcologicoproyectosinvestigacion=marcologicoproyectosinvestigacionproposito)
                        detalleinforme.save(request)

                    for marcologicoproyectosinvestigacioncomponente in marcologicoproyectosinvestigacioncomponentes:
                        detalleinforme = DetalleInforme(informemarcologicoproyectosinvestigacion= informemarcologicoproyectosinvestigacion,
                                                        marcologicoproyectosinvestigacion=marcologicoproyectosinvestigacioncomponente)
                        detalleinforme.save(request)

                    for marcologicoproyectosinvestigacionaccione in marcologicoproyectosinvestigacionacciones:
                        detalleinforme = DetalleInforme(informemarcologicoproyectosinvestigacion= informemarcologicoproyectosinvestigacion,
                                                        marcologicoproyectosinvestigacion=marcologicoproyectosinvestigacionaccione)
                        detalleinforme.save(request)
                    log(u'Adiciono informe: %s' % informemarcologicoproyectosinvestigacion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'proyectopdf':
            try:
                data['proyectosinvestigacion'] = proyectosinvestigacion = ProyectosInvestigacion.objects.get(pk=request.POST['id'])
                data['marcologicoproyectosinvestigacionfins'] = proyectosinvestigacion.marcologicoproyectosinvestigacion_set.filter(status=True, tipo=0).order_by('id')
                data['marcologicoproyectosinvestigacionpropositos'] = proyectosinvestigacion.marcologicoproyectosinvestigacion_set.filter(status=True, tipo=1).order_by('id')
                data['marcologicoproyectosinvestigacioncomponentes'] = proyectosinvestigacion.marcologicoproyectosinvestigacion_set.filter(status=True, tipo=2).order_by('id')
                data['marcologicoproyectosinvestigacionacciones'] = proyectosinvestigacion.marcologicoproyectosinvestigacion_set.filter(status=True, tipo=3).order_by('id')
                participantesmatrices = proyectosinvestigacion.participantesmatrices_set.filter(status=True, tipoparticipante__id=1)
                data['participantesmatrices'] = ''
                data['coordinacion'] = ''
                data['decano'] = ''
                if participantesmatrices:
                    data['participantesmatrices'] = participantesmatrices[0].profesor.persona.nombre_titulo()
                    data['coordinacion'] = participantesmatrices[0].profesor.coordinacion.nombre
                    data['decano'] = participantesmatrices[0].profesor.coordinacion.responsable().persona.nombre_titulo()
                proyectosinvestigacioncampos=proyectosinvestigacion.proyectovinculacioncampos_set.filter(status=True)
                data['proyectosinvestigacioncampos'] = None
                if proyectosinvestigacioncampos.exists():
                    data['proyectosinvestigacioncampos'] = proyectosinvestigacioncampos[0]
                return conviert_html_to_pdf(
                    'proyectovinculaciondocente/proyecto.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        elif action == 'informepdf':
            try:
                data['informemarcologicoproyectosinvestigacion'] = informemarcologicoproyectosinvestigacion = InformeMarcoLogicoProyectosInvestigacion.objects.get(pk=request.POST['id'])
                data['proyecto'] = proyecto = informemarcologicoproyectosinvestigacion.proyectovinculacion
                data['programa'] = proyecto.programa
                data['usuario'] = usuario
                data['fecha'] = fecha
                data['coordinaciones'] = proyecto.coordinaciones()
                data['carreras'] = proyecto.carrera()
                data['institucionbeneficiaria'] = proyecto.institucionbeneficiaria
                data['docente'] = proyecto.usuario_creacion.persona_set.all()[0].nombre_titulo()
                data['fechainforme'] = informemarcologicoproyectosinvestigacion.fecha
                data['marcologicoproyectosinvestigacionfins'] = informemarcologicoproyectosinvestigacion.detalleinforme_set.filter(status=True, marcologicoproyectosinvestigacion__tipo=0).order_by('id')
                data['marcologicoproyectosinvestigacionpropositos'] = informemarcologicoproyectosinvestigacion.detalleinforme_set.filter(status=True, marcologicoproyectosinvestigacion__tipo=1).order_by('id')
                data['marcologicoproyectosinvestigacioncomponentes'] = informemarcologicoproyectosinvestigacion.detalleinforme_set.filter(status=True, marcologicoproyectosinvestigacion__tipo=2).order_by('id')
                data['marcologicoproyectosinvestigacionacciones'] = informemarcologicoproyectosinvestigacion.detalleinforme_set.filter(status=True, marcologicoproyectosinvestigacion__tipo=3).order_by('id')
                # participantesmatrices =  informemarcologicoproyectosinvestigacion.proyectovinculacion.participantesmatrices_set.filter(status=True, tipoparticipante__id=1)
                # data['participantesmatrices'] = ''
                # data['coordinacion'] = ''
                # data['decano'] = ''
                # if participantesmatrices:
                #     data['participantesmatrices'] = participantesmatrices[0].profesor.persona.nombre_titulo()
                #     data['coordinacion'] = participantesmatrices[0].profesor.coordinacion.nombre
                #     data['decano'] = participantesmatrices[0].profesor.coordinacion.responsable().persona.nombre_titulo()
                # proyectosinvestigacioncampos=proyectosinvestigacion.proyectovinculacioncampos_set.filter(status=True)
                # data['proyectosinvestigacioncampos'] = None
                # if proyectosinvestigacioncampos.exists():
                #     data['proyectosinvestigacioncampos'] = proyectosinvestigacioncampos[0]
                return conviert_html_to_pdf(
                    'proyectovinculaciondocente/informe.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        elif action == 'factores':
            try:
                tipo = int(request.POST['tipo'])
                detalleinforme = DetalleInforme.objects.get(pk=request.POST['id'])
                if tipo == 1:
                    detalleinforme.factoresgeneradores = request.POST['valor']
                if tipo == 2:
                    detalleinforme.factoresexito = request.POST['valor']
                if tipo == 3:
                    detalleinforme.numero = request.POST['valor']
                detalleinforme.save(request)
                if tipo == 3:
                    for deta in  DetalleInforme.objects.filter(status=True, marcologicoproyectosinvestigacion=detalleinforme.marcologicoproyectosinvestigacion).order_by('informemarcologicoproyectosinvestigacion__fecha'):
                        deta.porcentaje = deta.porcentaje_informe()
                        deta.save(request)
                log(u'Modifico factor en informe %s, en tipo: %s ' % (detalleinforme,tipo), request, "edit")
                return JsonResponse({"result": "ok"})
            except:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addavance':
            try:
                idtarea = request.POST['idtarea']
                cronograma = Cronograma.objects.get(pk=idtarea)
                f = AvanceEjecucionForm(request.POST)
                if f.is_valid():
                    avance = DetalleCumplimiento(
                        proyecto= Cronograma.objects.get(pk=idtarea).proyecto,
                        tarea = cronograma,
                        avance = f.cleaned_data['porcentaje'],
                        fecha_ingreso = f.cleaned_data['fecha'],
                        observacion= f.cleaned_data['observacion'],
                        profesor = profesor
                        )
                    avance.save(request)
                    if cronograma.avance() == 100:
                        cronograma.estado_finalizado = True
                        cronograma.save(request)

                    if 'evidencia' in request.FILES:
                        newfile = request.FILES['evidencia']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 10485760:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                        if not exte in ['pdf',]:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf"})
                        newfile._name = generar_nombre("proyecto_", newfile._name)

                        avance.evidencia = newfile
                        avance.save(request)
                    log(u'Adiciono avance de ejecucion de proyectos de investigación docente: %s' % avance, request, "add")
                    if avance.profesor:
                        notificacion = Notificacion(titulo="Evidencia de avance de proyecto cargada",
                                                    cuerpo=f"{avance.profesor.persona.nombre_completo_inverso()} ha cargado evicencia de avance del proyecto de Servicio Comunitario.",
                                                    destinatario=avance.proyecto.lider(),
                                                    url="/proyectovinculaciondocente?action=ejecucion&id=" + str(avance.proyecto.pk),
                                                    fecha_hora_visible=datetime.now() + timedelta(days=2),
                                                    content_type=None,
                                                    object_id=None,
                                                    prioridad=1,
                                                    app_label='sga')
                        notificacion.save()

                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editavance':
            try:
                idtarea = request.POST['idtarea']
                detalle = DetalleCumplimiento.objects.get(pk=idtarea)
                f = AvanceEjecucionForm(request.POST)
                if f.is_valid():
                    detalle.avance = f.cleaned_data['porcentaje']
                    detalle.observacion = f.cleaned_data['observacion']
                    detalle.fecha_ingreso = f.cleaned_data['fecha']
                    detalle.save(request)
                    if detalle.tarea.avance() == 100:
                        crono = Cronograma.objects.get(pk=detalle.tarea.pk)
                        crono.estado_finalizado = True
                        crono.save(request)

                    if 'evidencia' in request.FILES:
                        newfile = request.FILES['evidencia']
                        newfile._name = generar_nombre("proyecto_", newfile._name)

                        detalle.evidencia = newfile
                        detalle.save(request)

                    log(u'Edito avance de ejecución de proyectos de investigación docente: %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delavance':
            try:
                idtarea = request.POST['id']
                detalle = DetalleCumplimiento.objects.get(pk=idtarea)
                detalle.status = False
                detalle.save(request)
                log(u'Eliminó avance de ejecución de proyectos de investigación docente: %s' % detalle, request, "del")
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'aprobaravance':
            try:
                idtarea = request.POST['id']
                detalle = DetalleCumplimiento.objects.get(pk=idtarea)
                detalle.aprobacion = True
                detalle.save(request)

                if detalle.tarea.avance() == float(detalle.tarea.cumplimiento):
                    crono = Cronograma.objects.get(pk=detalle.tarea.pk)
                    crono.estado_finalizado = True
                    crono.save(request)

                if detalle.profesor:
                    notificacion = Notificacion(titulo="Evidencia de avance de proyecto aprobada",
                                                cuerpo=f"{profesor.persona.nombre_completo_inverso()} ha aprobado la evidencia de avance del proyecto de Servicio Comunitario.",
                                                destinatario= detalle.profesor.persona,
                                                url="/proyectovinculaciondocente?action=ejecucion&id=" + str(detalle.proyecto.pk),
                                                fecha_hora_visible=datetime.now() + timedelta(days=2),
                                                content_type=None,
                                                object_id=None,
                                                prioridad=1,
                                                app_label='sga')
                    notificacion.save()

                log(u'Aprobó avance de ejecución de proyectos de investigación docente: %s' % detalle, request, "edit")
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'addconfigurarinforme':
            try:
                f = Configuracion_Informe_VinculacionForm(request.POST)
                if f.is_valid():
                    eslider = ParticipantesMatrices.objects.filter(status=True, proyecto__pk=request.POST['id'],
                                                                   tipoparticipante__pk=1, profesor=profesor).exists()
                    if eslider:
                        proyectoinvestigacion = ProyectosInvestigacion.objects.get(pk=int(request.POST['id']))
                        if not proyectoinvestigacion.get_tecnicoasociado():
                            return JsonResponse({'result': 'bad', 'mensaje': 'El proyecto no tiene configurado un Técnico asociado de Vinculación. Comunicarse con el departamento de vinculación.'})
                        detallecumplimiento = DetalleCumplimiento.objects.filter(status=True, proyecto__pk=request.POST['id'],
                                                                             aprobacion_adm=False, fecha_ingreso__gte=f.cleaned_data['fecha_inicio'],
                                                                             fecha_ingreso__lte=f.cleaned_data['fecha_fin'], tarea__status=True
                                                                             )
                    else:
                        detallecumplimiento = DetalleCumplimiento.objects.filter(status=True,
                                                                                 proyecto__pk=request.POST['id'],
                                                                                 aprobacion_adm=False,
                                                                                 fecha_ingreso__gte=f.cleaned_data['fecha_inicio'],
                                                                                 fecha_ingreso__lte=f.cleaned_data['fecha_fin'],
                                                                                 usuario_creacion=request.user, tarea__status=True
                                                                                 )

                    if detallecumplimiento.exists():
                        return JsonResponse({'result': 'bad', 'mensaje': 'Tiene informes pedientes de aprobación entre estas fechas'})


                    if not ConfiguracionInformeVinculacion.objects.filter(proyecto__pk=request.POST['id'], fecha_inicio=f.cleaned_data['fecha_inicio'], fecha_fin=f.cleaned_data['fecha_fin'], status=True,usuario_creacion=request.user ).exists():
                        configuracioninforme = ConfiguracionInformeVinculacion(
                                                        proyecto=ProyectosInvestigacion.objects.get(pk=request.POST['id']),
                                                        fecha_inicio=f.cleaned_data['fecha_inicio'],
                                                        fecha_fin=f.cleaned_data['fecha_fin'],
                                                        informecondensado=eslider,
                                                        actividades_extras = f.cleaned_data['actividades_extras'],
                                                        profesor=profesor,
                                                        observacion = f.cleaned_data['observacion'],
                                                        )
                        configuracioninforme.save(request)
                        log(u'Adiciono configuracion: %s' % configuracioninforme, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Esta configuracion ya se encuentra Registrada"})
                else:
                     raise()
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editconfigurarinforme':
            try:
                f = Configuracion_Informe_VinculacionForm(request.POST)
                if f.is_valid():
                   configuracion = ConfiguracionInformeVinculacion.objects.get(pk=request.POST['id'])
                   configuracion.fecha_inicio = f.cleaned_data['fecha_inicio']
                   configuracion.fecha_fin = f.cleaned_data['fecha_fin']
                   configuracion.actividades_extras = f.cleaned_data['actividades_extras']
                   configuracion.observacion = f.cleaned_data['observacion']
                   configuracion.profesor=profesor
                   configuracion.save(request)

                   # Editar evidencia rechazada tambien del módulo Mi Cronograma
                   owner, lider = configuracion.profesor.persona, configuracion.proyecto.lider()
                   if evidencia := EvidenciaActividadDetalleDistributivo.objects.filter(criterio__criteriodocenciaperiodo__criterio=[151, 150][owner == lider], criterio__distributivo__profesor=configuracion.profesor, proyectovinculacion=configuracion.proyecto, desde=configuracion.fecha_inicio, hasta=configuracion.fecha_fin, generado=True, status=True).first():
                       evidencia.desde = configuracion.fecha_inicio
                       evidencia.hasta = configuracion.fecha_fin
                       evidencia.save(request)

                   log(u'Edito la configuracion de informe: %s' % configuracion, request, "edit")
                   return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editgenerar':
            try:
                f = Detalle_InformeForm(request.POST)
                if f.is_valid():
                    registro = DetalleInformeVinculacion.objects.get(pk=request.POST['id'])
                    registro.factor_problema = f.cleaned_data['factor_problema']
                    registro.factor_exito = f.cleaned_data['factor_exito']
                    registro.editado = True
                    registro.save(request)
                    log(u'Edito el informe: %s' % registro, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delconfiguracion':
            try:
                conf = request.POST['id']
                configuracion = ConfiguracionInformeVinculacion.objects.get(pk=conf)

                actividades = ActividadExtraVinculacion.objects.filter(status=True, configuracion=configuracion)
                for act in actividades:
                    act.status = False
                    act.save(request)
                configuracion.status = False
                configuracion.save(request)
                log(u'Eliminó la configuracion de informe de Proyectos de Vinculacion: %s' % configuracion, request, "del")

                # Eliminar evidencia rechazada tambien del módulo Mi Cronograma
                owner, lider = configuracion.profesor.persona, configuracion.proyecto.lider()
                if migracion := configuracion.migracionevidenciaactividad_set.filter(status=True).first():
                    evidencia = migracion.evidencia
                    evidencia.delete()
                    log(f'Eliminó la evidencia de la actividad {evidencia.criterio.pk} del mes {evidencia.hasta.month}/{evidencia.hasta.year}', request, "del")
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'addactividad':
            try:
                f = ActividadExtraForm(request.POST)
                if f.is_valid():
                    conf = ConfiguracionInformeVinculacion.objects.get(pk=request.POST['conf'])
                    if (f.cleaned_data['fecha_inicio'] >= conf.fecha_inicio and f.cleaned_data['fecha_inicio'] <= conf.fecha_fin) and (f.cleaned_data['fecha_fin'] >= conf.fecha_inicio and f.cleaned_data['fecha_fin'] <= conf.fecha_fin):
                        actividad = ActividadExtraVinculacion(
                            configuracion= conf,
                            proyecto = conf.proyecto,
                            descripcion = f.cleaned_data['descripcion'],
                            fecha_inicio = f.cleaned_data['fecha_inicio'],
                            fecha_fin = f.cleaned_data['fecha_fin'],
                        )
                        actividad.save(request)

                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("actividadextra_", newfile._name)

                            actividad.archivo = newfile
                            actividad.save(request)
                        log(u'Adiciono actividades extras al informe de vinculacion: %s' % actividad, request, "add")
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe ingresar una fecha dentro del rango de informe"})
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editactividad':
            try:
                f = ActividadExtraForm(request.POST)
                if f.is_valid():
                    actividad = ActividadExtraVinculacion.objects.get(pk=request.POST['id'])
                    actividad.descripcion = f.cleaned_data['descripcion']
                    actividad.fecha_inicio = f.cleaned_data['fecha_inicio']
                    actividad.fecha_fin = f.cleaned_data['fecha_fin']
                    actividad.save(request)

                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("actividadextra_", newfile._name)

                        actividad.archivo = newfile
                        actividad.save(request)
                    log(u'Edito actividades extras al informe de vinculacion: %s' % actividad, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delactividad':
            try:
                data['id'] = id = request.POST['id']
                actividad = ActividadExtraVinculacion.objects.get(pk=id)
                actividad.status = False
                actividad.save(request)
                log(u'Elimino actividades extras al informe de vinculacion: %s' % actividad, request, "del")
                return JsonResponse({"error": False})
            except Exception as ex:
                pass

        elif action == 'solicitudrevision':
            try:
                idsolicitud = request.POST['id']
                solicitud = ConfiguracionInformeVinculacion.objects.get(pk=idsolicitud)
                esLider = persona == solicitud.proyecto.lider()
                pk_criterio = [151, 150][esLider]
                criterio = CriterioDocencia.objects.get(pk=pk_criterio)
                if not DetalleDistributivo.objects.values('id').filter(criteriodocenciaperiodo__criterio__pk=pk_criterio, distributivo__profesor__persona=solicitud.profesor.persona, distributivo__periodo=periodo, status=True).exists():
                    notificacion2('Carga de informe mensual para proyecto de vinculación', f"Estimad{'a' if solicitud.profesor.persona.es_mujer() else 'o'} {solicitud.profesor.persona.nombres.split()[0]}, <b>NO</b> cuenta con el criterio {criterio} en el periodo {periodo} por lo cual su evidencia <b class='text-danger'>no se migrará al módulo Mi Cronograma</b>.", solicitud.profesor.persona, None, '', solicitud.pk, 1, 'sga', ConfiguracionInformeVinculacion)

                if DetalleInformeVinculacion.objects.filter(configuracion=solicitud, status=True, usuario_creacion=request.user, editado=False).exclude(actividad__arbolObjetivo__tipo=3).exists():
                    return JsonResponse({"result": 'bad', "error": True, "mensaje": u"Debe editar la información del informe para solicitar revisión."})

                solicitud.aprobacion = 2
                solicitud.save(request)

                if tecnico := solicitud.proyecto.get_tecnicoasociado():
                    mes = solicitud.fecha_fin.month
                    notificacion2('Revisión de informe mensual para proyecto de vinculación', f"Estimad{'a' if tecnico.persona.es_mujer() else 'o'} {tecnico.persona.nombres.split()[0].title()}, {'la' if solicitud.profesor.persona.es_mujer() else 'el'} docente {solicitud.profesor.persona.__str__().title()} {'lider' if esLider else 'promotor'} de proyecto de vinculación <b>solicitó la revisión</b> de su evidencia de avance del proyecto {solicitud.proyecto.nombre.title()} correspondiente al avance del mes de {nombremes(mes).lower()}..", tecnico.persona, None, f'/programasvinculacion?action=configurarinforme_adm&id={solicitud.proyecto.pk}', solicitud.pk, 1, 'sga', ConfiguracionInformeVinculacion)

                # Migrar al módulo 'Mi Cronograma'
                err, msj = migrar_evidencia_proyecto_vinculacion(request, solicitud)
                log(f'#[{persona.pk}] Solicitó revisión de informe %s en el periodo {periodo.pk}' % solicitud, request, "edit")
                return JsonResponse({'result': 'ok', "error": False, 'pk': solicitud.pk, 'mensaje': msj})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'aprobarInforme':
            try:
                f = AprobacionInformeForm(request.POST)
                if f.is_valid():
                    informe = ConfiguracionInformeVinculacion.objects.get(pk=request.POST['id'])
                    informe.aprobacion = int(f.cleaned_data['aprobacion'])
                    informe.detalle_aprobacion = f.cleaned_data['detalle_aprobacion']
                    informe.personaaprueba = persona
                    informe.save(request)
                    estado = 'aprobado' if informe.aprobacion == 3 else 'rechazado'
                    notificacion = Notificacion(titulo=f"Aprobación de informe mensual de avance",
                                                cuerpo=f"{persona.nombre_completo_inverso()} ha {estado} el informe de avance mensual del proyecto de Servicio Comunitario.",
                                                destinatario=informe.profesor.persona,
                                                url="/proyectovinculaciondocente?action=configurarinforme&id=" + str(informe.proyecto.pk),
                                                fecha_hora_visible=datetime.now() + timedelta(days=2),
                                                content_type=None,
                                                object_id=None,
                                                prioridad=1,
                                                app_label='sga')
                    notificacion.save()
                    log(u'Aprobó la configuración de informe: %s' % informe, request, "edit")

                    # -- firmainformevinculacion
                    if informe.aprobacion == 3:
                        data['form2'] = FirmaElectronicaIndividualForm()
                        data['id'] = informe.pk
                        data['modal'] = 'panelAprobacion'
                        data['action'] = 'firmainformevinculacion'
                        template = get_template("proyectovinculaciondocente/modal/firmardocumentoauto.html")
                        json_content = template.render(data)
                        return JsonResponse({'result': 'ok', 'html': json_content})
                    # -- firmainformevinculacion
                    return JsonResponse({"result": "ok", 'estado': informe.aprobacion})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'addperiodoinscripcion':
            try:
                f = PeriodoInscripcionFrom(request.POST)
                if f.is_valid():
                    periodo = PeriodoInscripcionVinculacion(
                        proyecto = ProyectosInvestigacion.objects.get(pk=request.POST['proyecto']),
                        observacion= f.cleaned_data['observacion'],
                        fechainicio= f.cleaned_data['fechainicio'],
                        fechafin= f.cleaned_data['fechafin'],
                    )
                    periodo.save(request)

                    carreras = CarrerasParticipantes.objects.filter(status=True, proyecto__pk= request.POST['proyecto'])
                    for carr in carreras:
                        carrera = CarreraInscripcionVinculacion(
                            periodo = periodo,
                            carrera = carr,
                        )
                        carrera.save(request)

                    log(u'Añadió periodo de inscripcion de proyecto de vinculacion: %s' % periodo, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'editperiodoinscripcion':
            try:
                f = PeriodoInscripcionFrom(request.POST)
                if f.is_valid():
                    periodo = PeriodoInscripcionVinculacion.objects.get(pk=request.POST['id'])

                    periodo.observacion = f.cleaned_data['observacion']
                    periodo.fechainicio = f.cleaned_data['fechainicio']
                    periodo.fechafin = f.cleaned_data['fechafin']
                    periodo.save(request)

                    log(u'Editó periodo de inscripcion de proyecto de vinculacion: %s' % periodo, request, "edit")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'actualizacupo':
            try:
                carrera = CarreraInscripcionVinculacion.objects.get(pk=request.POST['carrera'])
                carrera.cupos = int(request.POST['cupo'])
                carrera.save(request)
                return JsonResponse({'result': 'ok', 'cupo': carrera.cupos})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad'})

        elif action == 'addhabilitacioninforme':
            try:
                with transaction.atomic():
                    proyecto = ProyectosInvestigacion.objects.get(pk=request.POST['proyectoid'])
                    form = InformeProyectoVinculacionForm(request.POST, request.FILES)
                    if form.is_valid():
                        informe = InformesProyectoVinculacionDocente(proyecto=proyecto,
                                                                     nombre=form.cleaned_data['nombre'].upper(),
                                                                     descripcion=form.cleaned_data['descripcion'],
                                                                     flimite=form.cleaned_data['flimite'])
                        informe.save(request)
                        if 'formato' in request.FILES:
                            newfile = request.FILES['formato']
                            newfile._name = generar_nombre(informe.nombre_input(), newfile._name)
                            informe.formato = newfile
                            informe.save(request)
                        log(u'Adiciono Requisito Actividad Extracurricular: %s' % informe, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        # elif action == 'editarhabilitacioninforme':
        #     try:
        #         with transaction.atomic():
        #             informe = InformesProyectoVinculacionDocente.objects.get(pk=request.POST['id'])
        #             f = InformeProyectoVinculacionForm(request.POST, request.FILES)
        #             if f.is_valid():
        #                 informe.nombre = f.cleaned_data['nombre'].upper()
        #                 informe.descripcion = f.cleaned_data['descripcion']
        #                 informe.flimite = f.cleaned_data['flimite']
        #                 if 'formato' in request.FILES:
        #                     newfile = request.FILES['formato']
        #                     newfile._name = generar_nombre(informe.nombre_input(), newfile._name)
        #                     informe.formato = newfile
        #                 informe.save(request)
        #                 log(u'Modificó Actividad Extracurricular: %s' % informe, request, "edit")
        #                 return JsonResponse({"result": False}, safe=False)
        #             else:
        #                 transaction.set_rollback(True)
        #                 return JsonResponse({"result": True, "form": [{k: v[0]} for k, v in f.errors.items()],
        #                                      "mensaje": "Complete los datos requeridos."}, safe=False)
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editarhabilitacioninforme':
            try:
                with transaction.atomic():
                    informe = InformesProyectoVinculacionDocente.objects.get(pk=request.POST['id'])
                    f = InformeProyectoVinculacionFechaForm(request.POST)
                    if f.is_valid():

                        informe.flimite = f.cleaned_data['flimite']

                        informe.save(request)
                        log(u'Modificó Actividad Extracurricular: %s' % informe, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'eliminarhabilitacioninforme':
            try:
                informe = InformesProyectoVinculacionDocente.objects.get(pk=int(request.POST['id']))
                informe.status = False
                informe.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'evaluarinformes':
            try:
                informe = InformesProyectoVinculacionEstudiante.objects.get(pk=int(request.POST['id']))
                informe.estado = request.POST['est']
                informe.observacion = request.POST['obs']
                informe.fecharevisionarchivo = datetime.now().date()
                informe.save(request)

                asunto = "Revisión de informes de Proyecto de Vinculación."
                mensaje = "ha sido revisado su informe"
                template = "emails/notificarrevisioninformevinculacion.html"
                datos = {'sistema': u'SGA - UNEMI',
                         'mensaje': mensaje,
                         'fecha': datetime.now().date(),
                         'hora': datetime.now().time(),
                         'saludo': 'Estimada' if informe.proyecto.inscripcion.persona.sexo_id == 1 else 'Estimado',
                         'estudiante': informe.proyecto.inscripcion.persona.nombre_completo_inverso(),
                         'estado': request.POST['est'],
                         'informe': informe,
                         'proyecto': informe.proyecto.proyecto.nombre,
                         'autoridad2': '',
                         't': miinstitucion()
                         }
                email = informe.proyecto.inscripcion.persona.lista_emails_envio()

                send_html_mail(asunto, template, datos, email, [], cuenta=variable_valor('CUENTAS_CORREOS')[0])

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'registrarhoras':
            try:
                f = RegistrarHorasViculacionForm(request.POST)
                if f.is_valid():
                    participacion = ParticipantesMatrices.objects.get(pk=request.POST['idparticipacion'])
                    participacion.horas = f.cleaned_data['horas']
                    participacion.save(request)
                    log(u'Horas registradas correctamente: %s' % participacion, request, 'edit')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'firmainformevinculacionmasivo':
            try:
                solicitudes = ConfiguracionInformeVinculacion.objects.filter(pk__in=request.POST.get('pks', '0').split(','), status=True)
                for soli in solicitudes:
                    try:
                        datas = None
                        es_lider, es_integ = soli.proyecto.lider() == soli.profesor, soli.profesor.persona == soli.profesor
                        documento_a_firmar = soli.archivo
                        certificado = request.FILES["firma"]
                        passfirma = request.POST['palabraclave']
                        razon = request.POST.get('razon', '')
                        name_documento_a_firmar, extension_documento_a_firmar = os.path.splitext(documento_a_firmar.name)
                        extension_certificado = os.path.splitext(certificado.name)[1][1:]
                        bytes_certificado = certificado.read()
                        palabras = u"%s" % persona.nombre_titulos3y4().upper()
                        posx, posy, numpaginafirma = obtener_posicion_x_y_saltolinea(documento_a_firmar.url, palabras)
                        if not posy: raise NameError(f"No se encontró el nombre {palabras} en el archivo del informe, por favor verifique si el nombre de esta persona se encuentra en la sección de firmas.")
                        posx, posy = posx + 30, posy - 230

                        try:
                            datau = JavaFirmaEc(archivo_a_firmar=documento_a_firmar,
                                                archivo_certificado=bytes_certificado,
                                                extension_certificado=extension_certificado,
                                                password_certificado=passfirma,
                                                page=numpaginafirma, reason=u"Validar informe de vinculación", lx=posx,
                                                ly=posy).sign_and_get_content_bytes()
                        except Exception as x:
                            datau, datas = firmar(request, passfirma, certificado, documento_a_firmar, numpaginafirma,
                                                  posx, posy, 150, 45)

                        if not datau: raise NameError(f'Documento con inconsistencia en la firma.')

                        documento_a_firmar = io.BytesIO()
                        documento_a_firmar.write(datau)
                        documento_a_firmar.seek(0)

                        _name = generar_nombre(f'{persona.usuario}_', 'file.pdf')

                        soli.archivo.save(_name, ContentFile(documento_a_firmar.read()))

                        if soli.aprobacion == 3: _, msj = migrar_evidencia_proyecto_vinculacion(request, soli, 4)
                        log(u'Firmo Documento: {}'.format(name_documento_a_firmar), request, "add")
                    except Exception as ex:
                        ...

                return JsonResponse({'result': 'ok', 'proyecto': solicitudes[0].proyecto.pk})
            except Exception as ex:
                pass

        elif action == 'firmainformevinculacion':
            try:
                para_revision = int(request.POST.get('revision', 0))
                soli = ConfiguracionInformeVinculacion.objects.get(pk=request.POST.get('id'))
                datas = None
                es_lider, es_integ = soli.proyecto.lider() == persona, soli.profesor.persona == persona
                documento_a_firmar = soli.archivo
                certificado = request.FILES["firma"]
                passfirma = request.POST['palabraclave']
                razon = request.POST.get('razon', '')
                name_documento_a_firmar, extension_documento_a_firmar = os.path.splitext(documento_a_firmar.name)
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()
                palabras = u"%s" % persona.nombre_titulos3y4().upper()
                posx, posy, numpaginafirma = obtener_posicion_x_y_saltolinea(documento_a_firmar.url, palabras)
                datau, msj = None, 'Documento firmado correctamente'
                if not posy: raise NameError(f"No se encontró el nombre {palabras} en el archivo del informe, por favor verifique si el nombre de esta persona se encuentra en la sección de firmas.")
                posx, posy = posx + 30, posy - 230

                for n in range(1, 4):
                    try:
                        datau = JavaFirmaEc(archivo_a_firmar=documento_a_firmar, archivo_certificado=bytes_certificado, extension_certificado=extension_certificado, password_certificado=passfirma, page=numpaginafirma, reason=razon, lx=posx, ly=posy).sign_and_get_content_bytes()
                    except Exception as x:
                        msj = f'Por favor asegúrese de que la contraseña sea correcta y vuelva a intentarlo más tarde. {x=}'

                    documento_a_firmar = io.BytesIO()
                    documento_a_firmar.write(datau)
                    documento_a_firmar.seek(0)

                    _name = generar_nombre(f'{persona.usuario}_', 'file.pdf')
                    file_obj = DjangoFile(documento_a_firmar, name=_name)
                    if datau: break

                if datau:
                    soli.archivo = file_obj
                    soli.save(request)

                if soli.aprobacion == 3: _, msj = migrar_evidencia_proyecto_vinculacion(request, soli, 4)
                log(u'Firmo Documento: {}'.format(name_documento_a_firmar), request, "add")
                return JsonResponse({'result': 'ok', 'id': soli.pk, 'proyecto': soli.proyecto.pk, 'para_revision': para_revision, 'mensaje': msj})
            except Exception as ex:
                return JsonResponse({'result': False, 'mensaje': f'Documento con inconsistencia en la firma. {ex.__str__()}.'})

        elif action == 'addtecnicoasociado':
            try:
                f = TecnicoAsociadoProyectoVinculacionForm(request.POST)
                f.delpersona()

                for t in TecnicoAsociadoProyectoVinculacion.objects.filter(status=True):
                    t.activo = t.status = False
                    t.save(request)

                if not f.is_valid():
                    return JsonResponse({"result": "bad", "form": [{k: v[0]} for k, v in f.errors.items()]})

                tecnico = TecnicoAsociadoProyectoVinculacion(persona_id=request.POST.get('persona', None),
                                                             proyecto_id=request.POST.get('proyecto', None),
                                                             cargo=f.cleaned_data.get('cargo'),
                                                             fechainicio=f.cleaned_data.get('fechainicio'),
                                                             fechafin=f.cleaned_data.get('fechafin'),
                                                             activo=True)
                tecnico.save(request)
                log(f"Adicionó técnico para revisión de informe al proyecto {tecnico.proyecto.pk}", request, 'add')
                return JsonResponse({'result': True})
            except Exception as ex:
                return JsonResponse({'result': False, 'mensaje': 'Error de conexión, %s' % ex.__str__()})

        elif action == 'firmarinforme':
            try:
                id = int(encrypt(request.POST['id']))
                informe_estudiante = InformesProyectoVinculacionEstudiante.objects.get(pk=id)
                archivo_a_firmar = informe_estudiante.archivo
                documento_a_firmar = archivo_a_firmar.file
                nombre_documento = os.path.basename(informe_estudiante.archivo.name)
                certificado = request.FILES["firma"]
                contrasenaCertificado = request.POST['palabraclave']
                razon = request.POST['razon'] if 'razon' in request.POST else ''
                jsonFirmas = json.loads(request.POST['txtFirmas'])
                name_documento_a_firmar, extension_documento_a_firmar = os.path.splitext(documento_a_firmar.name)
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()
                if not jsonFirmas:
                    messages.error(request, "Error: Debe seleccionar ubicación de la firma")
                    return redirect(request.path)
                for membrete in jsonFirmas:
                    datau = JavaFirmaEc(
                        archivo_a_firmar=documento_a_firmar, archivo_certificado=bytes_certificado, extension_certificado=extension_certificado,
                        password_certificado=contrasenaCertificado,
                        page=int(membrete["numPage"]), reason=razon, lx=membrete["x"], ly=membrete["y"]
                    ).sign_and_get_content_bytes()
                    documento_a_firmar = io.BytesIO()
                    documento_a_firmar.write(datau)
                    documento_a_firmar.seek(0)
                informe_estudiante.archivo.save(f'{nombre_documento}', ContentFile(documento_a_firmar.read()))
                informe_estudiante.save()
                log(f"Firmo documento  {informe_estudiante.archivo}", request, 'add')
                return JsonResponse({"result":True})
            except Exception as ex:
                messages.error(request, "Error: {}".format(ex))
                return redirect(request.path)

        elif action == 'uploadFile':
            try:
                configuracion = ConfiguracionInformeVinculacion.objects.get(pk=request.POST.get('id'))

                if DetalleInformeVinculacion.objects.filter(configuracion=configuracion, status=True, usuario_creacion=request.user, editado=False).exclude(actividad__arbolObjetivo__tipo=3).exists():
                    raise NameError(u"Debe completar la información del informe para solicitar revisión")

                archivo = request.FILES['archivo']

                if not archivo:
                    raise NameError(f'Por favor ingrese un archivo firmado.')

                valido, _, dict = verificarFirmasPDF(archivo)

                if dict:
                    if dict.get('firmasValidas'):
                        # if not list(filter(lambda c: c.get('emitidoPara') == persona.nombre_completo() or c.get('emitidoPara') == persona.nombre_completo_inverso(), dict.get('certificado'))):
                        #     raise NameError(f'La firma electronica del archivo ingresado no corresponde a la del usuario {persona.nombre_completo()}/{persona.nombre_completo_inverso()}')

                        archivo.name = generar_nombre(f'{persona.usuario}_', 'file.pdf')
                        configuracion.archivo = archivo
                        configuracion.aprobacion = 2
                        configuracion.save(request)

                        # Migrar al módulo 'Mi Cronograma'
                        migrar_evidencia_proyecto_vinculacion(request, configuracion)
                        return JsonResponse({'result': 'ok'})

                raise NameError('El documento ingresado no tiene ninguna firma electrónica válida.')
            except Exception as ex:
                return JsonResponse({'result': False, 'mensaje': f'{ex.__str__()}'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'edittecnicoasociado':
                try:
                    TecnicoAsociadoProyectoVinculacion.objects.filter(status=True).update(activo=False, status=False)
                    tecnico = TecnicoAsociadoProyectoVinculacion.objects.get(pk=request.GET.get('pk'))
                    tecnico.status = True
                    tecnico.activo = True
                    tecnico.save(request)
                    return JsonResponse({'result': True})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': 'Error de conexión, %s' % ex.__str__()})

            if action == 'excelparticipanteproyecto':
                try:
                    idproyecto = request.GET['idproyecto']
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
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Matriz_Participantes_Proyectos' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"NUM", 2000),
                        (u"PROGRAMA", 10000),
                        (u"PROYECTO", 10000),
                        (u"CEDULA", 10000),
                        (u"APELLIDOS", 10000),
                        (u"CORREO", 10000),
                        (u"HORAS", 2000),
                        (u"TIPO", 2000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listaparticipantes = ParticipantesMatrices.objects.filter(status=True, matrizevidencia_id=2, proyecto_id=idproyecto).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')
                    row_num = 4
                    for participantes in listaparticipantes:
                        i = 0
                        campo1 = participantes.id
                        campo2 = participantes.proyecto.programa.nombre
                        campo3 = participantes.proyecto.nombre
                        if participantes.profesor:
                            campo4 = participantes.profesor.persona.cedula
                        if participantes.inscripcion:
                            campo4 = participantes.inscripcion.persona.cedula
                        if participantes.administrativo:
                            campo4 = participantes.administrativo.persona.cedula
                        if participantes.profesor:
                            campo5 = participantes.profesor.persona.nombre_completo_inverso()
                        if participantes.inscripcion:
                            campo5 = participantes.inscripcion.persona.nombre_completo_inverso()
                        if participantes.administrativo:
                            campo5 = participantes.administrativo.persona.nombre_completo_inverso()
                        if participantes.administrativo:
                            campo6 = participantes.administrativo.persona.emailinst
                        elif participantes.profesor:
                            campo6 = participantes.profesor.persona.emailinst
                        elif participantes.inscripcion:
                            campo6 = participantes.inscripcion.persona.emailinst
                        campo7 = participantes.horas
                        if participantes.profesor:
                            campo8 = participantes.tipoparticipante.nombre
                        if participantes.inscripcion:
                            campo8 = 'ESTUDIANTE'
                        if participantes.administrativo:
                            campo8 = 'ADMINISTRATIVO'
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
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

            elif action == 'excelparticipanteproyectototal':
                try:
                    tipoproyectos = request.GET['tipo']
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
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Matriz_Participantes_Proyectos' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"NUM", 2000),
                        (u"PROGRAMA", 10000),
                        (u"PROYECTO", 10000),
                        (u"CEDULA", 10000),
                        (u"APELLIDOS", 10000),
                        (u"HORAS", 2000),
                        (u"TIPO", 2000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listaparticipantes = ParticipantesMatrices.objects.filter(status=True, matrizevidencia_id=2, proyecto__tipo=tipoproyectos)
                    row_num = 4
                    for participantes in listaparticipantes:
                        i = 0
                        campo1 = participantes.id
                        campo2 = participantes.proyecto.programa.nombre
                        campo3 = participantes.proyecto.nombre
                        if participantes.profesor:
                            campo4 = participantes.profesor.persona.cedula
                        if participantes.inscripcion:
                            campo4 = participantes.inscripcion.persona.cedula
                        if participantes.administrativo:
                            campo4 = participantes.administrativo.persona.cedula
                        if participantes.profesor:
                            campo5 = participantes.profesor.persona.nombre_completo()
                        if participantes.inscripcion:
                            campo5 = participantes.inscripcion.persona.nombre_completo()
                        if participantes.administrativo:
                            campo5 = participantes.administrativo.persona.nombre_completo()
                        campo6 = participantes.horas
                        if participantes.profesor:
                            campo7 = participantes.tipoparticipante.nombre
                        if participantes.inscripcion:
                            campo7 = 'ESTUDIANTE'
                        if participantes.administrativo:
                            campo7 = 'ADMINISTRATIVO'
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'excelparticipantevinculacion':
                try:
                    tipoproyectos = request.GET['tipo']
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
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Matriz_Participantes_Proyectos' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"NUM", 2000),
                        (u"PROGRAMA", 10000),
                        (u"PROYECTO", 10000),
                        (u"ANIO", 2000),
                        (u"CARRERAS PROYECTO", 10000),
                        (u"CEDULA", 3000),
                        (u"APELLIDOS", 10000),
                        (u"CARRERAS ESTUDIANTE", 10000),
                        (u"HORAS", 2000),
                        (u"TIPO", 2000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listaparticipantes = ParticipantesMatrices.objects.filter(status=True, matrizevidencia_id=2, proyecto__tipo=tipoproyectos).order_by('inscripcion__persona__apellido1','inscripcion__persona__apellido2')
                    row_num = 4
                    for participantes in listaparticipantes:
                        lista = []
                        i = 0
                        campo1 = participantes.id
                        campo2 = participantes.proyecto.programa.nombre
                        campo3 = participantes.proyecto.nombre
                        campocarrera = ''
                        anio = str(participantes.proyecto.fechainicio)
                        anio = anio.split('-')
                        if participantes.profesor:
                            campo4 = participantes.profesor.persona.cedula
                        if participantes.inscripcion:
                            campo4 = participantes.inscripcion.persona.cedula
                            campocarrera = participantes.inscripcion.carrera.nombre + ' ' + participantes.inscripcion.carrera.alias
                        if participantes.administrativo:
                            campo4 = participantes.administrativo.persona.cedula
                        if participantes.profesor:
                            campo5 = participantes.profesor.persona.nombre_completo_inverso()
                        if participantes.inscripcion:
                            campo5 = participantes.inscripcion.persona.nombre_completo_inverso()
                        if participantes.administrativo:
                            campo5 = participantes.administrativo.persona.nombre_completo_inverso()
                        campo6 = participantes.horas
                        if participantes.profesor:
                            campo7 = participantes.tipoparticipante.nombre
                        if participantes.inscripcion:
                            campo7 = 'ESTUDIANTE'
                        if participantes.administrativo:
                            campo7 = 'ADMINISTRATIVO'

                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        if participantes.inscripcion:
                            if participantes.proyecto.carrerasproyecto_set.filter(status=True).exists():
                                carrerasproyectos = participantes.proyecto.carrerasproyecto_set.filter(status=True)
                                for carrerasproy in carrerasproyectos:
                                    lista.append(carrerasproy.carrera.nombre + ',')
                        ws.write(row_num, 3, anio[0], font_style2)
                        ws.write(row_num, 4, str(lista), font_style2)
                        ws.write(row_num, 5, campo4, font_style2)
                        ws.write(row_num, 6, campo5, font_style2)
                        ws.write(row_num, 7, campocarrera, font_style2)
                        ws.write(row_num, 8, campo6, font_style2)
                        ws.write(row_num, 9, campo7, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'excelestudiantesinscrito':
                try:
                    idperiodo = request.GET['id']
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
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Matriz_Participantes_Proyectos' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"NUM", 2000),
                        (u"PROYECTO", 10000),
                        (u"CEDULA", 10000),
                        (u"APELLIDOS / NOMBRES", 10000),
                        (u"CARRERA", 10000),
                        (u"NIVEL MATRICULA", 10000),
                        (u"CORREO PERSONAL", 10000),
                        (u"CORREO INSTITUCIONAL", 10000),
                        (u"CELULAR", 10000),
                        (u"ESTADO", 10000),
                        (u"HORAS REALIZADAS", 10000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listaparticipantes = ProyectoVinculacionInscripcion.objects.filter(status=True, periodo__id =idperiodo ).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')
                    row_num = 4
                    i = 0
                    for participantes in listaparticipantes:
                        i+=1
                        if participantes.estado == 1:
                            estado= "SOLICITADO"
                        elif participantes.estado == 2:
                            estado = "APROBADO"
                        else:
                            estado = "RECHAZADO"
                        matricula = participantes.inscripcion.matricula_periodo(participantes.periodo.periodo)
                        if matricula:
                            nivel = matricula.nivelmalla
                        else:
                            nivel = participantes.inscripcion.mi_nivel().nivel
                        ws.write(row_num, 0, i, font_style2)
                        ws.write(row_num, 1, participantes.proyectovinculacion.nombre, font_style2)
                        ws.write(row_num, 2, participantes.inscripcion.persona.cedula, font_style2)
                        ws.write(row_num, 3, participantes.inscripcion.persona.nombre_completo_inverso(), font_style2)
                        ws.write(row_num, 4, participantes.inscripcion.carrera.nombre, font_style2)
                        ws.write(row_num, 5, str(nivel), font_style2)
                        ws.write(row_num, 6, participantes.inscripcion.persona.email, font_style2)
                        ws.write(row_num, 7, participantes.inscripcion.persona.emailinst, font_style2)
                        ws.write(row_num, 8, participantes.inscripcion.persona.telefono, font_style2)
                        ws.write(row_num, 9, estado, font_style2)
                        ws.write(row_num, 10, participantes.inscripcion.numero_horas_vinculacion(), font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'tecnicoasociadoproyectovinculacion':
                try:
                    data['title'] = 'Gestión de técnico asociado'
                    data['proyecto'] = proyecto = ProyectosInvestigacion.objects.get(pk=request.GET.get('id'))
                    data['tecnicos'] = proyecto.get_historialtecnicoasociado().order_by('-activo', '-fechafin')
                    return render(request, 'proyectovinculaciondocente/tecnicoasociadoproyectovinculacion.html', data)
                except Exception as ex:
                    pass

            elif action == 'addtecnicoasociado':
                try:
                    f = TecnicoAsociadoProyectoVinculacionForm()
                    data['form2'] = f
                    data['id'] = 1
                    template = get_template('proyectovinculaciondocente/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})

            elif action == 'addproyecto':
                try:
                    data['title'] = u'Adicionar Proyecto'
                    form = ProyectoVinculacion1Form(initial={
                        'sectorcoordenada' : "-2.1498491508722646,-79.60318654775621",
                    })
                    data['form'] = form
                    if "conv" in request.GET:
                        data['conv'] = request.GET['conv']
                    return render(request, "proyectovinculaciondocente/addproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'crearproyecto':
                try:
                    data['title'] = u'Formulación de proyectos de servicios comunitarios'
                    data['conv']= request.GET['conv']
                    data['eslider'] = ParticipantesMatrices.objects.filter(status=True, proyecto__pk=request.POST['id'],tipoparticipante__pk=1,profesor=profesor).exists()
                    return render(request, "proyectovinculaciondocente/crearproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'addfechafinp':
                try:
                    data['title'] = u'Adicionar fecha fin del proyecto'
                    form = FechaFinProyectoFrom()
                    data['form'] = form
                    data['proyectos'] = proyectos = ProyectosInvestigacion.objects.get(pk=request.GET['id'])
                    return render(request, "proyectovinculaciondocente/add_fechafin.html", data)
                except Exception as ex:
                    pass

            elif action == 'editproyecto':
                try:
                    data['title'] = u'Editar Proyecto'
                    data['proyectos'] = proyectos = ProyectosInvestigacion.objects.get(pk=request.GET['id'],tipo=1)

                    lista = []
                    listacant =[]
                    listacarrera=[]
                    # for listaaa in  ProyectosInvestigacionCarreras.objects.select_related().filter(proyectovinculacion=proyectos):
                    #     listacarrera.append(Carrera.objects.get(pk=int(listaaa.carreras.id)))

                    # for lis in ProyectosInvestigacionZonas.objects.select_related().filter(proyectovinculacion=proyectos):
                    #
                    #     lista.append(Zona.objects.get(pk=int(lis.zona.id)))

                    # for listaa in ProyectosInvestigacionCantones.objects.select_related().filter(proyectovinculacion=proyectos):
                    #     listacant.append(Canton.objects.get(pk=int(listaa.canton.id)))
                    # data['zona'] = zona = lista
                    # data['canton'] = canton = listacant
                    # data['carreras'] = carreras = listacarrera



                    form = ProyectoVinculacion1Form(initial={'programa': proyectos.programa,
                                                             'nombre': proyectos.nombre,
                                                             'tiempoejecucion': proyectos.tiempoejecucion,
                                                             'fechainicio': proyectos.fechainicio,
                                                             'fechafin': proyectos.fechafin,
                                                             'fechaPlanificacion':proyectos.fechaplaneacion,
                                                             'tipoproinstitucion': proyectos.tipoproinstitucion,
                                                             'lineainvestigacion': proyectos.lineainvestigacion,
                                                             'sublineainvestigacion': proyectos.sublineainvestigacion,
                                                             'alcanceterritorial': proyectos.alcanceterritorial,
                                                            'areaconocimiento': proyectos.areaconocimiento,
                                                            'subareaconocimiento': proyectos.subareaconocimiento,
                                                             'subareaespecificaconocimiento': proyectos.subareaespecificaconocimiento,
                                                             'valorpresupuestointerno': proyectos.valorpresupuestointerno,
                                                             'valorpresupuestoexterno': proyectos.valorpresupuestoexterno,
                                                             'presupuestototal': proyectos.presupuestototal,
                                                             # 'carreras':carreras,
                                                             'zona': [i.id for i in proyectos.zona.all()],
                                                             'canton': [i.id for i in proyectos.canton.all()],
                                                             'institucionbeneficiaria': proyectos.institucionbeneficiaria,
                                                             # 'sectorcoordenada': proyectos.sectorcoordenada,
                                                             #'periodoejecucion': proyectos.periodoejecucion,
                                                             # 'objetivoplannacional': proyectos.objetivoplannacional,
                                                             # 'cupo':proyectos.cupo
                                                             # 'archivo': proyectos.archivo
                                                             'objetivos_PND' : proyectos.objetivos_PND,
                                                            'politicas_PND' : proyectos.politicas_PND,
                                                            'linea_accion' : proyectos.linea_accion,
                                                            'estrategia_desarrollo' : proyectos.estrategia_desarrollo,
                                                            'investigacion_institucional' : proyectos.investigacion_institucional,
                                                            'necesidades_sociales' : proyectos.necesidades_sociales,
                                                            'tiempo_duracion_horas' : proyectos.tiempo_duracion_horas,
                                                            'distrito' : proyectos.distrito,
                                                            'circuito' : proyectos.circuito,
                                                            'sectorcoordenada' : proyectos.sectorcoordenada,
                    })
                    #form.editar(proyectos)
                    data['form'] = form
                    return render(request, "proyectovinculaciondocente/editproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'editar':
                try:
                    data['title'] = u'Proyecto de servicio comunitario'
                    # id = int(encrypt(request.GET['id']))
                    id = request.GET['id']
                    data['proyecto'] = proyecto = ProyectosInvestigacion.objects.get(id=(id))
                    if proyecto.aprobacion == 1 or proyecto.aprobacion == 2 or proyecto.aprobacion == 4 :
                        return HttpResponseRedirect("/proyectovinculaciondocente?info=No puede editar la información de este proyecto.")

                    data['conv'] = FechaProyectos.objects.filter(status=True, fechainicio__lte=datetime.now(),fechafin__gte=datetime.now()).last()
                    data['beneficiarios'] = Beneficiarios.objects.filter(status=True, proyecto_id=id)
                    data['involucrados'] = Involucrado.objects.filter(status=True, proyecto_id=id)
                    data['presupuesto'] = Presupuesto.objects.filter(status=True, proyecto_id=id)
                    data['presupuesto2'] = Presupuesto.objects.filter(status=True, proyecto=proyecto).distinct('producto__pk')
                    total = 0.0
                    for pre in Presupuesto.objects.filter(status=True, proyecto=proyecto):
                        total = total + float(pre.total)
                    data['total_presupuesto'] = total
                    data['presupuesto3'] = MarcoLogico.objects.filter(status=True, proyecto=proyecto, arbolObjetivo__tipo=2,arbolObjetivo__parentID__isnull=True).order_by('arbolObjetivo__orden')
                    subttotal = 0.0
                    for pre in Presupuesto.objects.filter(status=True, proyecto=proyecto):
                        subttotal = subttotal + float(pre.total)
                    data['total_subtotal'] = subttotal
                    data['cronograma'] = Cronograma.objects.filter(status=True, proyecto_id=id)
                    data['listaCarreras'] = CarrerasParticipantes.objects.filter(status=True, proyecto_id=id)
                    data['listaPerfilProfesional'] = PerfilProfesional.objects.filter(status=True, proyecto_id=id)
                    # data['form_cronograma'] = CronogramaForm()
                    if not ArbolProblema.objects.filter(status=True, proyecto_id=id).exists():
                        aPro = ArbolProblema(
                            proyecto=ProyectosInvestigacion.objects.get(pk=id),
                            detalle="Detalle del Problema",
                            tipo=1,
                            orden='1',
                        )
                        aPro.save(request)
                        liBase = MatrizLineaBase(
                            proyecto=ProyectosInvestigacion.objects.get(pk=id),
                            # descripcion=aPro.detalle,
                            arbolProblema=ArbolProblema.objects.get(pk=aPro.pk),
                        )
                        liBase.save(request)
                        aObj = ArbolObjetivo(
                            proyecto=ProyectosInvestigacion.objects.get(pk=id),
                            arbolProblema=ArbolProblema.objects.get(pk=aPro.pk),
                            detalle="Detalle del Proposito",
                            tipo=1,
                        )
                        aObj.save(request)
                        marLogi = MarcoLogico(
                            proyecto=ProyectosInvestigacion.objects.get(pk=id),
                            arbolObjetivo=ArbolObjetivo.objects.get(pk=aObj.pk),
                            resumen_narrativo=aObj.detalle,
                        )
                        marLogi.save(request)
                        for x in range(0,2):
                            aPro = ArbolProblema(
                                proyecto=ProyectosInvestigacion.objects.get(pk=id),
                                detalle="Detalle de la Causa"+ str(x+1),
                                tipo=2,
                                orden=x+1,
                            )
                            aPro.save(request)
                            auxIdAPro=aPro.pk
                            liBase = MatrizLineaBase(
                                proyecto=ProyectosInvestigacion.objects.get(pk=id),
                                arbolProblema=ArbolProblema.objects.get(pk=aPro.pk),
                                # descripcion=aPro.detalle,
                            )
                            liBase.save(request)
                            aObj = ArbolObjetivo(
                                proyecto=ProyectosInvestigacion.objects.get(pk=id),
                                arbolProblema=ArbolProblema.objects.get(pk=aPro.pk),
                                detalle="Detalle del Medio "+ str(x+1),
                                tipo=2,
                                orden=x + 1,
                            )
                            aObj.save(request)
                            auxIdAObj = aObj.pk
                            marLogi = MarcoLogico(
                                proyecto=ProyectosInvestigacion.objects.get(pk=id),
                                arbolObjetivo=ArbolObjetivo.objects.get(pk=aObj.pk),
                                resumen_narrativo=aObj.detalle,
                            )
                            marLogi.save(request)
                            #SUB CAUSA
                            aPro = ArbolProblema(
                                proyecto=ProyectosInvestigacion.objects.get(pk=id),
                                detalle="Detalle de la SubCausa " + str(x + 1)+'.1',
                                tipo=2,
                                parentID=ArbolProblema.objects.get(pk=auxIdAPro),
                                orden=str(x + 1) + '.1',
                            )
                            aPro.save(request)
                            liBase = MatrizLineaBase(
                                proyecto=ProyectosInvestigacion.objects.get(pk=id),
                                arbolProblema=ArbolProblema.objects.get(pk=aPro.pk),
                                # descripcion=aPro.detalle,
                            )
                            liBase.save(request)
                            aObj = ArbolObjetivo(
                                proyecto=ProyectosInvestigacion.objects.get(pk=id),
                                arbolProblema=ArbolProblema.objects.get(pk=aPro.pk),
                                detalle="Detalle del SubMedio " + str(x + 1)+'.1',
                                parentID=ArbolObjetivo.objects.get(pk=auxIdAObj),
                                tipo=2,
                                orden=str(x + 1) + '.1',
                            )
                            aObj.save(request)
                            marLogi = MarcoLogico(
                                proyecto=ProyectosInvestigacion.objects.get(pk=id),
                                arbolObjetivo=ArbolObjetivo.objects.get(pk=aObj.pk),
                                resumen_narrativo=aObj.detalle,
                            )
                            marLogi.save(request)
                        #EFECTO
                        for x in range(0,2):
                            aPro = ArbolProblema(
                                proyecto=ProyectosInvestigacion.objects.get(pk=id),
                                detalle="Detalle del Efecto " + str(x+1),
                                tipo=3,
                                orden= x+1,
                            )
                            aPro.save(request)

                            liBase = MatrizLineaBase(
                                proyecto=ProyectosInvestigacion.objects.get(pk=id),
                                arbolProblema=ArbolProblema.objects.get(pk=aPro.pk),
                                # descripcion=aPro.detalle,
                            )
                            liBase.save(request)
                            aObj = ArbolObjetivo(
                                proyecto=ProyectosInvestigacion.objects.get(pk=id),
                                arbolProblema=ArbolProblema.objects.get(pk=aPro.pk),
                                detalle="Detalle del FIN " + str(x+1),
                                tipo=3,
                                orden=x + 1,
                            )
                            aObj.save(request)
                            marLogi = MarcoLogico(
                                proyecto=ProyectosInvestigacion.objects.get(pk=id),
                                arbolObjetivo=ArbolObjetivo.objects.get(pk=aObj.pk),
                                resumen_narrativo=aObj.detalle,
                            )
                            marLogi.save(request)

                    data['aPro_problema']= ArbolProblema.objects.get(status=True, proyecto_id=id, tipo=1)
                    data['aPro_causa'] = ArbolProblema.objects.filter(status=True, proyecto_id=id, tipo=2).order_by('orden')
                    data['aPro_efecto'] = ArbolProblema.objects.filter(status=True, proyecto_id=id, tipo=3).order_by('orden')
                    data['aObj_proposito'] = ArbolObjetivo.objects.get(status=True, proyecto_id=id, tipo=1)
                    data['aObj_medio'] = ArbolObjetivo.objects.filter(status=True, proyecto_id=id, tipo=2).order_by('orden')
                    data['aObj_fin'] = ArbolObjetivo.objects.filter(status=True, proyecto_id=id, tipo=3).order_by('orden')
                    efectos = MatrizLineaBase.objects.filter(status=True, proyecto_id=id,arbolProblema__tipo=3).order_by('arbolProblema__orden')
                    causas= MatrizLineaBase.objects.filter(status=True, proyecto_id=id,arbolProblema__tipo=2).order_by('arbolProblema__orden')
                    problema= MatrizLineaBase.objects.filter(status=True, proyecto_id=id,arbolProblema__tipo=1)
                    data['aPro_lineaBase'] = list(efectos)+list(problema)+list(causas)
                    data['aPro_marcoLogico_fin'] = MarcoLogico.objects.filter(status=True, proyecto_id=id, arbolObjetivo__tipo=3)
                    data['aPro_marcoLogico_proposito'] = MarcoLogico.objects.filter(status=True, proyecto_id=id, arbolObjetivo__tipo=1)
                    data['aPro_marcoLogico_componentes'] = MarcoLogico.objects.filter(status=True, proyecto_id=id, arbolObjetivo__tipo=2,arbolObjetivo__parentID__isnull=True).order_by('arbolObjetivo__orden')
                    data['aPro_marcoLogico_acciones'] = acciones = MarcoLogico.objects.filter(status=True, proyecto_id=id, arbolObjetivo__tipo=2,arbolObjetivo__parentID__isnull=False).order_by('arbolObjetivo__orden')
                    if Problema.objects.filter(status=True, proyecto_id=id).exists():
                        data['redaccion'] = Problema.objects.get(status=True, proyecto_id=id)
                    data['lista']=ParticipantesMatrices.objects.filter(status=True, proyecto_id=id,tipoparticipante__tipo=1).order_by('fecha_creacion')
                    data['datoSecundario']=DatoSecundario.objects.filter(status=True, proyecto_id=id)
                    data['anexos']= Anexos.objects.filter(status=True, proyecto_id=id)
                    #control de pestañas
                    #
                    proyecto = ProyectosInvestigacion.objects.filter(pk=id).count()
                    if proyecto >= 1:
                        data['bool_proyecto'] = True

                    carrerasParticipantes = CarrerasParticipantes.objects.filter(proyecto_id=id, status=True)
                    carrera = False
                    for x in carrerasParticipantes:
                        perfil = PerfilProfesional.objects.filter(carreras_participantes=x, status = True).exists()
                        if not perfil:
                            carrera = False
                            break
                        else:
                            carrera =True

                    if carrera:
                        data['bool_car_participantes'] = True

                    lider = ParticipantesMatrices.objects.filter(proyecto_id=id, tipoparticipante__id = 1,status=True).count()
                    liderh = ParticipantesMatrices.objects.get(proyecto_id=id, tipoparticipante__id = 1,status=True)
                    promotor = ParticipantesMatrices.objects.filter(proyecto_id=(id), tipoparticipante__id = 2, status=True).count()
                    if lider == 1 and promotor>=1 and liderh.horas>0:
                        data['bool_doc_participantes'] = True

                    beneficiario = Beneficiarios.objects.filter(proyecto_id=(id), status=True).count()
                    if beneficiario >= 1:
                        data['bool_beneficiarios'] = True

                    linea = ProyectosInvestigacion.objects.get(pk=(id))
                    if linea.linea_base:
                        lineaBase = MatrizLineaBase.objects.filter(proyecto_id=(id), editado=False, status=True).count()
                        if not lineaBase >= 1:
                            data['bool_linea'] = True
                    else:
                        if DatoSecundario.objects.filter(status=True,proyecto=linea).count() >= 1:
                            data['bool_linea'] = True
                    marcoLogico = MarcoLogico.objects.filter(proyecto_id=(id), editado=False, status=True).count()
                    component = MarcoLogico.objects.filter(status=True, proyecto_id=id, arbolObjetivo__tipo=2,arbolObjetivo__parentID__isnull=True)
                    porcentaje=0.0
                    for comp in component:
                        porcentaje = porcentaje + float(comp.cumplimiento)
                    if not marcoLogico >= 1:
                        if porcentaje == 100.0:
                            data['bool_marcoLogico'] = True

                    arbolObjetivo = ArbolObjetivo.objects.filter(proyecto_id=(id), editado=False, status=True).count()
                    if not arbolObjetivo >= 1:
                        data['bool_arbolObjetivo'] = True

                    arbolProblema = ArbolProblema.objects.filter(proyecto_id=(id), editado=False, status=True).count()
                    if not arbolProblema >= 1:
                        data['bool_arbolProblema'] = True

                    for x in acciones:
                        crono = Cronograma.objects.filter(aobjetivo=x.arbolObjetivo, status = True).exists()
                        if not crono:
                            cronograma = False
                            break
                        else:
                            cronograma =True

                    if cronograma:
                        data['bool_cronograma'] = True

                    presupuesto = Presupuesto.objects.filter(proyecto_id=(id), status= True).count()
                    if presupuesto >= 1:
                        data['bool_presupuesto'] = True

                    anexos = Anexos.objects.filter(proyecto_id=(id), status=True).count()
                    if anexos >= 3:
                        data['bool_anexos'] = True

                    data['eslider'] = ParticipantesMatrices.objects.filter(status=True, proyecto__pk=id,tipoparticipante__pk=1,profesor=profesor).exists()

                    return render(request, "proyectovinculaciondocente/crearproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'generarpdf':
                try:
                    data['proyecto'] = proyecto = ProyectosInvestigacion.objects.get(id=request.GET['id'])
                    data['carrerasparticipantes'] = CarrerasParticipantes.objects.filter(status=True, proyecto=proyecto)
                    data['presupuesto'] = Presupuesto.objects.filter(status=True, proyecto=proyecto)
                    data['presupuesto3'] = MarcoLogico.objects.filter(status=True, proyecto=proyecto,arbolObjetivo__tipo=2,arbolObjetivo__parentID__isnull=True).order_by('arbolObjetivo__orden')
                    subttotal = 0.0
                    for pre in Presupuesto.objects.filter(status=True, proyecto=proyecto):
                        subttotal = subttotal + float(pre.total)
                    data['total_subtotal'] = subttotal
                    data['docentesparticipantes'] = docentes = ParticipantesMatrices.objects.filter(status=True, proyecto=proyecto,tipoparticipante__tipo=1).order_by('fecha_creacion')
                    data['perfilprofesional'] = PerfilProfesional.objects.filter(status=True, proyecto=proyecto)
                    data['beneficiarios'] = Beneficiarios.objects.filter(status=True, proyecto=proyecto)
                    data['problema'] = Problema.objects.get(status=True, proyecto=proyecto)
                    data['marcologico'] = MarcoLogico.objects.filter(status=True, proyecto=proyecto)
                    data['aPro_marcoLogico_fin'] = MarcoLogico.objects.filter(status=True, proyecto=proyecto,arbolObjetivo__tipo=3)
                    data['aPro_marcoLogico_proposito'] = MarcoLogico.objects.filter(status=True, proyecto=proyecto,arbolObjetivo__tipo=1)
                    data['aPro_marcoLogico_componentes'] = MarcoLogico.objects.filter(status=True, proyecto=proyecto,arbolObjetivo__tipo=2,arbolObjetivo__parentID__isnull=True).order_by('arbolObjetivo__orden')
                    data['aPro_marcoLogico_acciones'] = acciones = MarcoLogico.objects.filter(status=True,proyecto=proyecto,arbolObjetivo__tipo=2,arbolObjetivo__parentID__isnull=False).order_by('arbolObjetivo__orden')
                    data['presupuesto2'] = Presupuesto.objects.filter(status=True, proyecto=proyecto).distinct('producto__pk')
                    total = 0.0
                    for pre in Presupuesto.objects.filter(status=True, proyecto=proyecto):
                        total = total + float(pre.total)
                    data['total_presupuesto'] = total

                    data['efectos'] = ArbolProblema.objects.filter(status=True, proyecto=proyecto, tipo=3).order_by('orden')
                    data['causas'] = ArbolProblema.objects.filter(status=True, proyecto=proyecto, tipo=2).order_by('orden')
                    data['problemaarbol'] = ArbolProblema.objects.filter(status=True, proyecto=proyecto, tipo=1).order_by('orden')
                    data['aObj_proposito'] = ArbolObjetivo.objects.filter(status=True, proyecto=proyecto,tipo=1).order_by('orden')
                    data['aObj_medio'] = ArbolObjetivo.objects.filter(status=True, proyecto=proyecto,tipo=2).order_by('orden')
                    data['aObj_fin'] = ArbolObjetivo.objects.filter(status=True, proyecto=proyecto, tipo=3).order_by('orden')
                    data['datosecundario'] = DatoSecundario.objects.filter(status=True, proyecto=proyecto)
                    data['efec'] = MatrizLineaBase.objects.filter(status=True, proyecto=proyecto,arbolProblema__tipo=3).order_by('arbolProblema__orden')
                    data['caus'] = MatrizLineaBase.objects.filter(status=True, proyecto=proyecto,arbolProblema__tipo=2).order_by('arbolProblema__orden')
                    data['prob'] = MatrizLineaBase.objects.filter(status=True, proyecto=proyecto,arbolProblema__tipo=1)
                    data['aPro_lineaBase'] = list(data['efec']) + list(data['prob']) + list(data['caus'])
                    data['lineabase'] = MatrizLineaBase.objects.filter(status=True, proyecto=proyecto)
                    data['cronograma'] = Cronograma.objects.filter(status=True, proyecto=proyecto)
                    data['fecha'] = datetime.now().strftime("%Y-%m-%d")
                    lider = ParticipantesMatrices.objects.get(status=True, proyecto=proyecto, tipoparticipante__pk=1)
                    carrera_lider = lider.profesor.carrera_comun_periodo(periodo)
                    if carrera_lider:
                        coordinacion = carrera_lider.coordinacion_carrera()
                        decano = coordinacion.responsable_periododos(periodo,1)
                        data['coordinacion'] = coordinacion
                        data['decano'] = decano
                    data['lider'] = lider.profesor.persona

                    return conviert_html_to_pdf(
                        'proyectovinculaciondocente/proyectovinculacion.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'politicaproyecto':
                try:
                    data['proyectos'] = proyectos = ProyectosInvestigacion.objects.get(pk=request.GET['id'],tipo=1)
                    data['title'] = u'Politica Proyecto del Objetivo ' + proyectos.objetivoplannacional.objetivo
                    data['politicaproyectosinvestigaciones'] = proyectos.politicaproyectosinvestigacion_set.all().order_by("id")
                    data['metaspndproyectosinvestigaciones'] = proyectos.metaspndproyectosinvestigacion_set.all().order_by("id")
                    data['metaszonalproyectosinvestigaciones'] = proyectos.metaszonalproyectosinvestigacion_set.all().order_by("id")
                    data['metascomplementariaproyectosinvestigaciones'] = proyectos.metascomplementariaproyectosinvestigacion_set.all().order_by("id")
                    data['lineamientoproyectosinvestigaciones'] = proyectos.lineamientoproyectosinvestigacion_set.all().order_by("id")
                    data['marcologicoproyectosinvestigacion'] = proyectos.marcologicoproyectosinvestigacion_set.filter(status=True)
                    proyectovinculacioncampos = proyectos.proyectovinculacioncampos_set.filter(status=True)
                    necesidades = ''
                    investigacion = ''
                    if proyectovinculacioncampos:
                        necesidades = proyectovinculacioncampos[0].necesidadessociales
                        investigacion = proyectovinculacioncampos[0].investigacioninstitucional
                    data['investigacion'] = investigacion
                    data['necesidades'] = necesidades
                    data['form'] = ProyectoVinculacion2Form(initial={'investigacioninstitucional': investigacion,
                                                                     'necesidadessociales': necesidades})
                    return render(request, "proyectovinculaciondocente/politicaproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'marcologico':
                try:
                    data['proyectos'] = proyectos = ProyectosInvestigacion.objects.get(pk=request.GET['id'],tipo=1)
                    data['title'] = u'Marco Lógico' + proyectos.nombre
                    data['marcologicoproyectosinvestigacionfins'] = proyectos.marcologicoproyectosinvestigacion_set.filter(status=True, tipo=0).order_by('id')
                    data['marcologicoproyectosinvestigacionpropositos'] = proyectos.marcologicoproyectosinvestigacion_set.filter(status=True, tipo=1).order_by('id')
                    data['marcologicoproyectosinvestigacioncomponentes'] = proyectos.marcologicoproyectosinvestigacion_set.filter(status=True, tipo=2).order_by('id')
                    data['marcologicoproyectosinvestigacionacciones'] = proyectos.marcologicoproyectosinvestigacion_set.filter(status=True, tipo=3).order_by('id')
                    data['tiene_informes']=proyectos.informemarcologicoproyectosinvestigacion_set.filter(status=True).exists()
                    return render(request, "proyectovinculaciondocente/marcologico.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinforme':
                try:
                    data['title'] = u'Nuevo Informe'
                    form = FechaInformeForm()
                    data['id'] = request.GET['id']
                    data['form'] = form
                    return render(request, "proyectovinculaciondocente/addinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinforme':
                try:
                    data['informe'] = informe = InformeMarcoLogicoProyectosInvestigacion.objects.get(pk=request.GET['id'])
                    data['title'] = u'Informe Marco Lógico ' + informe.proyectovinculacion.nombre + ' ' + str(informe.fecha)
                    data['informemarcologicoproyectosinvestigacionfines'] = DetalleInforme.objects.filter(informemarcologicoproyectosinvestigacion=informe, status=True,marcologicoproyectosinvestigacion__tipo=0).order_by('id')
                    data['informemarcologicoproyectosinvestigacionpropositos'] = DetalleInforme.objects.filter(informemarcologicoproyectosinvestigacion=informe, status=True,marcologicoproyectosinvestigacion__tipo=1).order_by('id')
                    data['informemarcologicoproyectosinvestigacioncomponentes'] = DetalleInforme.objects.filter(informemarcologicoproyectosinvestigacion=informe, status=True,marcologicoproyectosinvestigacion__tipo=2).order_by('id')
                    data['informemarcologicoproyectosinvestigacionacciones'] = DetalleInforme.objects.filter(informemarcologicoproyectosinvestigacion=informe, status=True,marcologicoproyectosinvestigacion__tipo=3).order_by('id')
                    return render(request, "proyectovinculaciondocente/editinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'aprobarsolicitudproyecto':
                try:
                    data['title'] = u'Aprobar Solicitud Proyectos Vinculacion'
                    data['participante'] = participante = ProyectoVinculacionInscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "proyectovinculaciondocente/aprobarsolicitudproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteparticipanteproyecto':
                try:
                    data['title'] = u'Eliminar Participante'
                    tipo = request.GET['tipo']
                    data['participante'] = participante = ParticipantesMatrices.objects.get(pk=request.GET['id'])
                    if tipo == '1':
                        data['nombres'] = participante.profesor.persona.nombre_completo() if participante.profesor else participante.externo.persona.nombre_completo()
                    if tipo == '2':
                        data['nombres'] = participante.inscripcion.persona.nombre_completo()
                    if tipo == '3':
                        data['nombres'] = participante.administrativo.persona.nombre_completo()
                    return render(request, "proyectovinculaciondocente/deleteparticipanteproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletesolicitudproyecto':
                try:
                    data['title'] = u'Eliminar Solicitud'
                    data['participante'] = participante = ProyectoVinculacionInscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "proyectovinculaciondocente/deletesolicitudproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'delevidencia':
                try:
                    data['title'] = u'Eliminar evidencia'
                    data['detalleevidenciasinformes'] = detalleevidenciasinformes = DetalleEvidenciasInformes.objects.get(pk=request.GET['id'])
                    data['proyectoid'] = detalleevidenciasinformes.detalleinforme.informemarcologicoproyectosinvestigacion.id
                    return render(request, "proyectovinculaciondocente/delevidencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'delmarcologico':
                try:
                    data['title'] = u'Eliminar'
                    data['marcologicoproyectosinvestigacion'] = MarcoLogicoProyectosInvestigacion.objects.get(pk=request.GET['id'])
                    return render(request, "proyectovinculaciondocente/delmarcologico.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletepresupuestoproyecto':
                try:
                    data['title'] = u'Eliminar Presupuesto'
                    data['presupuesto'] = PresupuestosProyecto.objects.get(pk=request.GET['id'])
                    return render(request, "proyectovinculaciondocente/deletepresupuestoproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'archivoenviados':
                try:
                    data['title'] = u'Archivos Enviados'
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        data['proyectoss']=ProyectosInvestigacion.objects.get(pk=ids)
                        data['aprobacion']=ProyectosInvestigacionAprobacion.objects.filter(proyecto__id=ids)
                    return render(request, "proyectovinculaciondocente/evidenciadearchivoenviados.html", data)
                except Exception as ex:
                    pass

            elif action == 'evidenciasproyectos':
                try:
                    data['title'] = u'Evidencia Proyectos'
                    data['proyectos'] = proyectosinvestigacion = ProyectosInvestigacion.objects.get(pk=request.GET['id'],tipo=1)
                    data['informemarcologicoproyectosinvestigaciones'] = InformeMarcoLogicoProyectosInvestigacion.objects.filter(proyectovinculacion=proyectosinvestigacion, status=True).order_by('fecha')
                    data['evidencias'] = Evidencia.objects.filter(status=True, matrizevidencia_id=2)
                    data['formevidencias'] = EvidenciaForm()
                    return render(request, "proyectovinculaciondocente/evidenciasproyectos.html", data)
                except Exception as ex:
                    pass

            elif action == 'addevidenciasproyectos':
                try:
                    data['title'] = u'Evidencia Programa'
                    data['form'] = EvidenciaForm
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    template = get_template("proyectovinculaciondocente/add_evidenciaproyectos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'addevidenciasinforme':
                try:
                    data['title'] = u'Evidencia Informe'
                    data['form'] = EvidenciaInformeForm
                    data['detalleinforme'] = detalleinforme = DetalleInforme.objects.get(pk=int(request.GET['id']))
                    template = get_template("proyectovinculaciondocente/addevidenciasinforme.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'addparticipantesdocentesp':
                try:
                    data['title'] = u'Agregar Participante Docente'
                    form = ParticipanteProfesorVinculacionForm()
                    data['form'] = form
                    data['id'] = id = request.GET['idproyecto']
                    return render(request, "proyectovinculaciondocente/addparticipantedocente.html", data)
                except Exception as ex:
                    pass

            elif action == 'editparticipantesdocentes':
                try:
                    data['title'] = u'Editar Participante Docente'
                    data['id'] = id = request.GET['id']

                    docente = ParticipantesMatrices.objects.get(pk=id)
                    data['idproyecto'] = docente.proyecto.pk
                    data['docente'] = docente

                    form = ParticipanteProfesorVinculacionForm(
                        initial={
                            'tipo': 1 if docente.profesor else 2,
                            # 'profesor': docente.profesor,
                            'horas': docente.horas,
                            'nivel': [i.id for i in docente.nivel.all()]
                        }
                    )

                    data['form'] = form
                    data['accionbuscar'] = 'Profesor' if docente.profesor else 'Persona'
                    data['tipodocente'] = 1 if docente.profesor else 2
                    data['iddocente'] = docente.profesor.id if docente.profesor else docente.externo.persona.id
                    data['nomdocente'] = docente.profesor.persona.flexbox_repr() if docente.profesor else docente.externo.persona.flexbox_repr()

                    return render(request, "proyectovinculaciondocente/editparticipantedocente.html", data)
                except Exception as ex:
                    pass

            elif action == 'addparticipantesestudiantes':
                try:
                    data['title'] = u'Participante Estudiante'
                    data['form'] = ParticipanteEstudianteForm
                    data['id'] = request.GET['idproyecto']
                    return render(request, "proyectovinculaciondocente/addparticipanteestudiante.html", data)
                except Exception as ex:
                    pass

            if action == 'addparticipantesadministrativos':
                try:
                    data['title'] = u'Participante Administrativo'
                    data['form'] = ParticipanteAdministrativoForm
                    data['id'] = request.GET['idproyecto']
                    return render(request, "proyectovinculaciondocente/addparticipanteadministrativo.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteproyecto':
                try:
                    data['title'] = u'Eliminar Proyecto'
                    data['proyecto'] = ProyectosInvestigacion.objects.get(pk=request.GET['id'],tipo=1)
                    return render(request, "proyectovinculaciondocente/deleteproyecto.html", data)
                except Exception as ex:
                    pass

            if action == 'participantesproyectos':
                try:
                    participantes_estudiantes = []
                    data['title'] = u'Participantes de Proyectos'

                    search = None
                    ids = None
                    inscripcionid = None
                    data['proyecto'] = proyectos = ProyectosInvestigacion.objects.get(pk=request.GET['id'],tipo=1)
                    data['tipoparticipante'] = ParticipantesTipo.objects.filter(tipo=proyectos.tipo)
                    participantesmatrices = ParticipantesMatrices.objects.filter(status=True, matrizevidencia_id=2, proyecto=proyectos).order_by('inscripcion__persona__apellido1')
                    data['personal_docente'] = personal_docente = participantesmatrices.filter(profesor__in=participantesmatrices.values_list('profesor_id', flat=True))
                    data['personal_administrativo'] = personal_administrativo = participantesmatrices.filter(administrativo__in=participantesmatrices.values_list('administrativo_id', flat=True))
                    if 's' in request.GET:
                        search = request.GET['s']
                        if ' ' in search:
                            s = search.split(" ")
                            participantes_estudiantes = participantesmatrices.filter((Q(inscripcion__persona__apellido1__contains=s[0]) & Q(inscripcion__persona__apellido2__contains=s[1])))
                        else:
                            participantes_estudiantes = participantesmatrices.filter(Q(inscripcion__persona__nombres__contains=search) |
                                                                                     Q(inscripcion__persona__apellido1__contains=search) |
                                                                                     Q(inscripcion__persona__apellido2__contains=search) |
                                                                                     Q(inscripcion__persona__cedula__contains=search))
                    else:
                        participantesmatrices = ParticipantesMatrices.objects.filter(status=True, matrizevidencia_id=2, proyecto=proyectos).order_by('-tipoparticipante', 'inscripcion__persona__apellido1')
                        participantes_estudiantes = participantesmatrices.filter(inscripcion__in=participantesmatrices.values_list('inscripcion_id', flat=True))
                    paging = MiPaginador(participantes_estudiantes, 25)
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
                    data['participantes'] = page.object_list
                    data['cantidad_estudiantes'] = participantes_estudiantes.count()
                    data['cantidad_docentes'] = personal_docente.count()
                    data['cantidad_administrativos'] = personal_administrativo.count()
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "proyectovinculaciondocente/participantesproyectos.html", data)
                except Exception as ex:
                    pass

            if action == 'participantesproyectos_':
                try:
                    participantes_estudiantes = []
                    panel = None
                    data['proyecto'] = proyectos = ProyectosInvestigacion.objects.get(pk=request.GET['id'], tipo=1)
                    data['tipoparticipante'] = ParticipantesTipo.objects.filter(tipo=proyectos.tipo)
                    participantesmatrices = ParticipantesMatrices.objects.filter(status=True, matrizevidencia_id=2, proyecto=proyectos).order_by('inscripcion__persona__apellido1')
                    personal_docente = participantesmatrices.filter(profesor__in=participantesmatrices.values_list('profesor_id', flat=True))
                    personal_administrativo = participantesmatrices.filter(administrativo__in=participantesmatrices.values_list('administrativo_id', flat=True))
                    participantes_estudiantes = participantesmatrices.filter(inscripcion__in=participantesmatrices.values_list('inscripcion_id', flat=True))
                    # participantes_estudiantes = participantesmatrices.filter(inscripcion__in=participantesmatrices.values_list('inscripcion_id', flat=True))
                    if 'panel' in request.GET:
                        panel = request.GET['panel']
                        if panel == '2':
                            data['personal_docente'] = personal_docente
                        elif panel == '3':
                            data['personal_administrativo'] = personal_administrativo
                    else:
                        # participantes_estudiantes = []
                        data['title'] = u'Participantes de Proyectos'
                        search = None
                        ids = None
                        inscripcionid = None
                        if 's' in request.GET:
                            search = request.GET['s']
                            if ' ' in search:
                                s = search.split(" ")
                                participantes_estudiantes = participantesmatrices.filter((Q(inscripcion__persona__apellido1__contains=s[0]) & Q(inscripcion__persona__apellido2__contains=s[1])))
                            else:
                                participantes_estudiantes = participantesmatrices.filter(Q(inscripcion__persona__nombres__contains=search) |
                                                                                         Q(inscripcion__persona__apellido1__contains=search) |
                                                                                         Q(inscripcion__persona__apellido2__contains=search) |
                                                                                         Q(inscripcion__persona__cedula__contains=search))
                        else:
                            participantesmatrices = ParticipantesMatrices.objects.filter(status=True, matrizevidencia_id=2, proyecto=proyectos).order_by('-tipoparticipante', 'inscripcion__persona__apellido1')
                            participantes_estudiantes = participantesmatrices.filter(inscripcion__in=participantesmatrices.values_list('inscripcion_id', flat=True))
                        paging = MiPaginador(participantes_estudiantes, 25)
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

                        data['search'] = search if search else ""
                        data['ids'] = ids if ids else ""
                        data['participantes'] = page.object_list
                    data['cantidad_estudiantes'] = participantes_estudiantes.count()
                    data['cantidad_docentes'] = personal_docente.count()
                    data['cantidad_administrativos'] = personal_administrativo.count()
                    data['panel'] = panel
                    data['proyectoid'] = proyectos.id
                    return render(request, "proyectovinculaciondocente/participantesproyectos_.html", data)
                except Exception as ex:
                    pass

            if action == 'informeafirmar':
                try:
                    data['id'] = id = int(request.GET['id'])
                    informe_estudiante = InformesProyectoVinculacionEstudiante.objects.get(pk=id)
                    archivo_a_firmar=informe_estudiante.archivo
                    data['archivo_url'] = archivo = f'/media/{archivo_a_firmar}'
                    data['title']=u'Firmar informe de Vinculacion'
                    qr = qrImgFirma(request, persona, "png", paraMostrar=True)
                    data["qrBase64"] = qr[0]
                    data['action']='firmarinforme'
                    template = get_template('formfirmaelectronica_v2.html')
                    return JsonResponse({'result':True,'data':template.render(data)})
                    #return HttpResponse(f'Dentro de la accion informe a firmar id del proyecto {archivo_informe}')
                except Exception as ex:
                    mensaje = f'error:{ex}'
                    return HttpResponse(mensaje) #manejar la respuesta de error

            elif action == 'verificarfirmas':
                try:
                    id = int(request.GET['id'])
                    informe_estudiante = InformesProyectoVinculacionEstudiante.objects.get(pk=id)
                    archivo = informe_estudiante.archivo.file
                    valido, msg, diccionario = verificarFirmasPDF(archivo)
                    return JsonResponse({'result': True,'context':diccionario})
                except Exception as ex:
                    return JsonResponse({'result': False, "mensaje": 'Error!: {}'.format(ex)}, safe=False)

            if action == 'revisarinformes':
                try:
                    data['id'] = id = int(request.GET['id'])
                    data['proyecto'] = matrizproyecto = ParticipantesMatrices.objects.get(pk=int(request.GET['id']))
                    data['part'] = participante = int(request.GET['participante'])
                    ESTADOS_PASOS = (
                        (1, u'APROBADO'),
                        (2, u'RECHAZADO')
                    )

                    ESTADOS_INFORMES = (
                        (1, u'APROBAR'),
                        (2, u'RECHAZAR')
                    )
                    data['informes_estudiantes'] = informes_estudiantes = InformesProyectoVinculacionEstudiante.objects.filter(status=True, proyecto=matrizproyecto).order_by('informedocente__nombre')
                    data['estados'] = ESTADOS_PASOS

                    data['estados_informes'] = ESTADOS_INFORMES


                    template = get_template('proyectovinculaciondocente/modal/modal_revisarinformes.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            if action == 'solicitudproyectos':
                try:
                    data['title'] = u'Solicitudes de Proyectos'
                    search = None
                    ids = None
                    inscripcionid = None
                    data['proyecto'] = proyectos = ProyectosInvestigacion.objects.get(pk=request.GET['id'],tipo=1)
                    if 's' in request.GET:
                        search = request.GET['s']
                        if ' ' in search:
                            s = search.split(" ")
                            participantes = proyectos.proyectovinculacioninscripcion_set.filter((Q(inscripcion__persona__apellido1__contains=s[0]) &
                                                                                                Q(inscripcion__persona__apellido2__contains=s[1])),
                                                                                                status=True, estado=1, proyectovinculacion=proyectos).order_by('inscripcion__persona__apellido1')
                        else:
                            participantes = proyectos.proyectovinculacioninscripcion_set.filter(Q(inscripcion__persona__nombres__contains=search) |
                                                                                                Q(inscripcion__persona__apellido1__contains=search) |
                                                                                                Q(inscripcion__persona__apellido2__contains=search) |
                                                                                                Q(inscripcion__persona__cedula__contains=search),
                                                                                                status=True, estado=1, proyectovinculacion=proyectos).order_by('inscripcion__persona__apellido1')
                    else:
                        participantes = proyectos.proyectovinculacioninscripcion_set.filter(status=True, estado=1).order_by('inscripcion__persona__apellido1')
                    paging = MiPaginador(participantes, 25)
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
                    data['participantes'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "proyectovinculaciondocente/solicitudproyectos.html", data)
                except Exception as ex:
                    pass

            if action == 'verinscritos':
                try:
                    data['title'] = u'Solicitudes de Proyectos'
                    search = None
                    ids = None
                    inscripcionid = None
                    periodo = PeriodoInscripcionVinculacion.objects.get(pk=request.GET['id'])
                    data['proyecto'] = proyectos = ProyectosInvestigacion.objects.get(pk= periodo.proyecto.pk)
                    data['periodo'] = periodo.pk
                    carreras = []
                    carreras = CarreraInscripcionVinculacion.objects.filter(status=True,periodo=periodo).values_list('carrera__carrera__id', 'carrera__carrera__nombre', flat=False)
                    data['carreras'] = carreras
                    participantes = ProyectoVinculacionInscripcion.objects.filter(status=True,periodo=periodo).order_by('inscripcion__persona__apellido1')
                    data['total'] = participantes.count()
                    car = 0
                    est = 0
                    if 'car' in request.GET:
                        if not request.GET['car'] == "0":
                            participantes = participantes.filter(inscripcion__carrera=request.GET['car'])
                            car = int(request.GET['car'])

                    if 'est' in request.GET:
                        if not request.GET['est'] == "0":
                            participantes = participantes.filter(estado=request.GET['est'])
                            est = int(request.GET["est"])

                    if 's' in request.GET:
                        search = request.GET['s']
                        if ' ' in search:
                            s = search.split(" ")
                            participantes = participantes.filter((Q(inscripcion__persona__apellido1__contains=s[0]) &
                                                                                            Q(inscripcion__persona__apellido2__contains=s[1])),
                                                                                            status=True, periodo=periodo).order_by('inscripcion__persona__apellido1')
                        else:
                            participantes = participantes.filter(Q(inscripcion__persona__nombres__contains=search) |
                                                                                        Q(inscripcion__persona__apellido1__contains=search) |
                                                                                        Q(inscripcion__persona__apellido2__contains=search) |
                                                                                        Q(inscripcion__persona__cedula__contains=search),
                                                                                        status=True, periodo=periodo).order_by('inscripcion__persona__apellido1')


                    paging = MiPaginador(participantes, 25)
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
                    data['participantes'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['car'] = car
                    data['est'] = est
                    data['busqueda'] = participantes.count()
                    data['aprobadas'] = participantes.filter(estado=2).count()
                    data['pendientes'] = participantes.filter(estado=1).count()
                    data['rechazadas'] = participantes.filter(estado=3).count()
                    return render(request, "proyectovinculaciondocente/verinscritos.html", data)
                except Exception as ex:
                    pass

            if action == 'carrerasproyectos':
                try:
                    data['title'] = u'Carreras de Proyecto'
                    data['proyecto'] = proyectos = ProyectosInvestigacion.objects.get(pk=request.GET['id'],tipo=1)
                    data['carreras'] = Carrera.objects.filter(status=True, activa=True).exclude(coordinacion__id__in=[9,7]).order_by('coordinacion','nombre')
                    data['carrerasproyecto'] = CarrerasProyecto.objects.filter(status=True, proyecto=proyectos)
                    data['niveles'] = NivelMalla.objects.filter(status=True).order_by('id')
                    return render(request, "proyectovinculaciondocente/carrerasproyectos.html", data)
                except Exception as ex:
                    pass

            elif action == 'presupuestoproyectos':
                try:
                    data['title'] = u'Presupuesto de Proyecto'
                    data['proyecto'] = proyectos = ProyectosInvestigacion.objects.get(pk=request.GET['id'],tipo=1)
                    data['presupuestoproyecto'] = presupuesto = proyectos.presupuestosproyecto_set.filter(status=True) #PresupuestosProyecto.objects.filter(status=True, proyecto=proyectos)
                    data['totalplanificado'] = presupuesto.aggregate(totoplanificado=Sum('planificado'))['totoplanificado']
                    data['totalejecutado'] = presupuesto.aggregate(totejecutado=Sum('ejecutado'))['totejecutado']
                    data['formpresupuesto'] = PresupuestoProyectoForm
                    return render(request, "proyectovinculaciondocente/presupuestoproyectos.html", data)
                except Exception as ex:
                    pass

            elif action == 'excelpresupuesto':

                try:

                    __author__ = 'Unemi'

                    proyecto = ProyectosInvestigacion.objects.get(pk=request.GET['pry'])

                    output = io.BytesIO()

                    workbook = xlsxwriter.Workbook(output)

                    ws = workbook.add_worksheet('Por actividad')

                    ws.set_column(0, 0, 10)

                    ws.set_column(1, 1, 40)

                    ws.set_column(2, 2, 40)

                    ws.set_column(3, 3, 10)

                    ws.set_column(4, 4, 10)

                    ws.set_column(5, 5, 10)

                    ws.set_column(6, 6, 10)

                    ws.set_column(7, 7, 10)

                    ws.set_column(8, 8, 10)

                    ws.set_column(9, 9, 10)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'fg_color': '#EBF5FB'})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#0b2f44',
                         'font_color': 'white'})

                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.write(0, 0, 'Cant.', formatoceldacab)

                    ws.write(0, 1, 'Rubro', formatoceldacab)

                    ws.write(0, 2, 'Especificaciones', formatoceldacab)

                    ws.write(0, 3, 'C. Unitario', formatoceldacab)

                    ws.write(0, 4, 'Subtotal', formatoceldacab)

                    ws.write(0, 5, 'Iva', formatoceldacab)

                    ws.write(0, 6, 'Total', formatoceldacab)

                    acciones = MarcoLogico.objects.filter(status=True, proyecto=proyecto, arbolObjetivo__tipo=2,
                                                          arbolObjetivo__parentID__isnull=False).order_by(
                        'arbolObjetivo__orden')

                    filas_recorridas = 2

                    for accion in acciones:

                        i = 0

                        ws.merge_range('A%s:G%s' % (filas_recorridas, filas_recorridas), str(accion.resumen_narrativo),
                                       formatoceldaleft)

                        filas_recorridas += 1

                        for rubro in accion.suministro():
                            ws.write('A%s' % filas_recorridas, (rubro.cantidad), formatoceldaleft)

                            ws.write('B%s' % filas_recorridas,
                                     str(rubro.suministro.rubro if rubro.suministro else rubro.producto),
                                     formatoceldaleft)

                            ws.write('C%s' % filas_recorridas, str(rubro.especificaciones), formatoceldaleft)

                            ws.write('D%s' % filas_recorridas, (null_to_decimal(rubro.costo_unitario, 4)),
                                     formatoceldaleft)

                            ws.write_formula('E%s' % filas_recorridas,
                                             '=(A%s*D%s)' % (filas_recorridas, filas_recorridas), formatoceldaleft)

                            ws.write_formula('F%s' % filas_recorridas,
                                             '=(E%s*0.12)' % (filas_recorridas) if rubro.suministro.aplicaIva else '0',
                                             formatoceldaleft)

                            ws.write_formula('G%s' % filas_recorridas,
                                             '=SUM(E%s+F%s)' % (filas_recorridas, filas_recorridas), formatoceldaleft)

                            filas_recorridas += 1

                    ws.write('F%s' % filas_recorridas, 'Total', formatoceldaleft)

                    ws.write_formula('G%s' % filas_recorridas, '=SUM(G2:G%s)' % (filas_recorridas - 1),
                                     formatoceldaleft)

                    ws2 = workbook.add_worksheet('Consolidado')

                    ws2.set_column(0, 0, 10)

                    ws2.set_column(1, 1, 40)

                    ws2.set_column(2, 2, 40)

                    ws2.set_column(3, 3, 10)

                    ws2.set_column(4, 4, 10)

                    ws2.set_column(5, 5, 10)

                    ws2.set_column(6, 6, 10)

                    ws2.write(0, 0, 'Cant.', formatoceldacab)

                    ws2.write(0, 1, 'Rubro', formatoceldacab)

                    ws2.write(0, 2, 'Especificaciones', formatoceldacab)

                    ws2.write(0, 3, 'C. Unitario', formatoceldacab)

                    ws2.write(0, 4, 'Subtotal', formatoceldacab)

                    ws2.write(0, 5, 'Iva', formatoceldacab)

                    ws2.write(0, 6, 'Total', formatoceldacab)

                    presupuesto = Presupuesto.objects.filter(status=True, proyecto=proyecto).distinct('suministro__pk')

                    filas_recorridas = 2

                    for pre in presupuesto:
                        i = 0

                        presupuesto = Presupuesto.objects.filter(status=True, proyecto=proyecto,
                                                                 suministro=pre.suministro)

                        ws2.write('A%s' % filas_recorridas, presupuesto.aggregate(valor=Sum('cantidad'))['valor'],
                                  formatoceldaleft)

                        ws2.write('B%s' % filas_recorridas,
                                  str(pre.suministro.rubro if pre.suministro else pre.producto), formatoceldaleft)

                        ws2.write('C%s' % filas_recorridas, str(pre.especificaciones), formatoceldaleft)

                        ws2.write('D%s' % filas_recorridas, (null_to_decimal(pre.costo_unitario, 4)), formatoceldaleft)

                        ws2.write_formula('E%s' % filas_recorridas, '=(A%s*D%s)' % (filas_recorridas, filas_recorridas),
                                          formatoceldaleft)

                        ws2.write_formula('F%s' % filas_recorridas,
                                          '=(E%s*0.12)' % (filas_recorridas) if pre.suministro.aplicaIva else '0',
                                          formatoceldaleft)

                        ws2.write_formula('G%s' % filas_recorridas,
                                          '=SUM(E%s+F%s)' % (filas_recorridas, filas_recorridas), formatoceldaleft)

                        filas_recorridas += 1

                    ws2.write('F%s' % filas_recorridas, 'Total', formatoceldaleft)

                    ws2.write_formula('G%s' % filas_recorridas, '=SUM(G2:G%s)' % (filas_recorridas - 1),
                                      formatoceldaleft)

                    workbook.close()

                    output.seek(0)

                    filename = 'Presupuesto.xlsx'

                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

                    response['Content-Disposition'] = 'attachment; filename=%s' % filename

                    return response

                except Exception as ex:

                    pass

            elif action == 'cargarsublineas1':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_profesor_materia')
                    sublineas = LineaProgramasInvestigacion.objects.values_list('sublineainvestigacion__id',flat=True).filter(status=True,programasinvestigacion__id=int(request.GET['idp'])).order_by('-id')
                    if 'linea_id' in request.GET:
                        lista = []
                        lineas= SubLineaInvestigacion.objects.filter(lineainvestigacion=int(request.GET['linea_id']), id__in=sublineas)
                        for lis in lineas:
                            lista.append([lis.id, lis.nombre])
                        data = {"results": "ok", 'lista':lista}
                        return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'cargarsublineas':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_profesor_materia')
                    if 'linea_id' in request.GET:
                        lista = []
                        lineas= SubLineaInvestigacion.objects.filter(lineainvestigacion=int(request.GET['linea_id']))
                        for lis in lineas:
                            lista.append([lis.id, lis.nombre])
                        data = {"results": "ok", 'lista':lista}
                        return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'subareaconocimiento1':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_profesor_materia')

                    if 'id' in request.GET:
                        lista = []
                        subareaconocimiento = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=int(request.GET['id']))
                        lista1 = []
                        subespeciconoocimiento =SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento=int(request.GET['id']))

                        for lis in subespeciconoocimiento:
                            lista1.append([lis.id, lis.nombre])

                        for lis in subareaconocimiento:
                            lista.append([lis.id, lis.nombre])
                        data = {"results": "ok", 'lista':lista,'lista1':lista1}
                        return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'cargaprograma':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_profesor_materia')
                    lineas1 = LineaProgramasInvestigacion.objects.values_list('lineainvestigacion__id',flat=True).filter(status=True, programasinvestigacion__id=int(request.GET['idp'])).order_by('-id').distinct()
                    areas1 = AreaProgramasInvestigacion.objects.values_list('areaconocimiento__id', flat=True).filter(status=True, programasinvestigacion__id=int(request.GET['idp'])).order_by('-id').distinct()
                    lista = []
                    lista1 = []
                    lineas= LineaInvestigacion.objects.filter(id__in=lineas1)
                    for lis in lineas:
                        lista.append([lis.id, lis.nombre])

                    areas=AreaConocimientoTitulacion.objects.filter(id__in=areas1)
                    for lis in areas:
                        lista1.append([lis.id, lis.nombre])
                    data = {"results": "ok", 'lista':lista, 'lista1':lista1}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'cargacanton':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_profesor_materia')
                    if 'zona_id' in request.GET:
                        lista = []
                        lineas= Canton.objects.filter(zona__id=int(request.GET['zona_id']))
                        for lis in lineas:
                            lista.append([lis.id, lis.nombre])
                        data = {"results": "ok", 'lista':lista}
                        return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'addmarcologico':
                try:
                    data['title'] = u'Adicionar'
                    data['form'] = MarcoLogicoForm
                    data['id'] = request.GET['id']
                    return render(request, "proyectovinculaciondocente/addmarcologico.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcarreraparticipante':
                try:
                    data['title'] = u'Adicionar'
                    data['form'] = CarreraParticipanteForm
                    data['idproyecto'] = request.GET['idproyecto']
                    return render(request, "proyectovinculaciondocente/addcarreraparticipante.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcarreraparticipante':
                try:
                    data['title'] = u'Adicionar'
                    data['id']= id= request.GET['id']
                    datos =  CarrerasParticipantes.objects.get(pk=id)
                    data['form'] = CarreraParticipanteForm(initial={
                        'carrera': datos.carrera,
                        # 'cupos': datos.cupos,
                    })
                    data['idproyecto'] = datos.proyecto.pk
                    return render(request, "proyectovinculaciondocente/editcarreraparticipante.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletecarreraparticipante':
                try:
                    data['title'] = u'Eliminar carrera participante'
                    data['participante'] = carrera = CarrerasParticipantes.objects.get(pk=request.GET['id'])
                    return render(request, "proyectovinculaciondocente/deletecarreraparticipante.html", data)
                except Exception as ex:
                    pass

            elif action == 'addperfilprofesional':
                try:
                    data['title'] = u'Adicionar perfil profesional'
                    data['form'] = form = PerfilProfesionalForm()
                    carrera = CarrerasParticipantes.objects.get(pk=request.GET['idcarrera'])
                    form.filtro(carrera.carrera)
                    data['idproyecto'] = request.GET['idproyecto']
                    data['idcarrera'] = request.GET['idcarrera']
                    return render(request, "proyectovinculaciondocente/addperfilprofesional.html", data)
                except Exception as ex:
                    pass

            elif action == 'editperfilprofesional':
                try:
                    data['title'] = u'Adicionar perfil profesional'
                    data['id'] = id = request.GET['id']
                    perfil = PerfilProfesional.objects.get(pk=id)
                    data['idproyecto'] = perfil.proyecto.pk
                    data['form'] = form = PerfilProfesionalForm(initial={
                        'perfil' : perfil.perfil,
                        'resultados_aprendizaje' : perfil.resultados_aprendizaje,
                        'asignatura': [i.id for i in perfil.asignatura.all()]
                    })
                    form.filtro(perfil.carreras_participantes.carrera)
                    return render(request, "proyectovinculaciondocente/editperfilprofesional.html", data)
                except Exception as ex:
                    pass

            if action == 'addbeneficiario':
                try:
                    data['title'] = u'Adicionar beneficiarios'
                    data['form'] = BeneficiariosForm
                    data['idproyecto'] = request.GET['idproyecto']
                    return render(request, "proyectovinculaciondocente/addbeneficiario.html", data)
                except Exception as ex:
                    pass

            if action == 'editbeneficiario':
                try:
                    data['title'] = u'Editar beneficiarios'
                    data['id'] = id = request.GET['id']
                    datos = Beneficiarios.objects.get(pk=id)
                    data['form'] = BeneficiariosForm(initial={
                        'nombre': datos.nombre,
                        'direccion': datos.direccion,
                        'correo': datos.correo,
                        'representante': datos.representante,
                        'cargo_repre': datos.cargo_repre,
                        'telefono': datos.telefono,
                        'coordenadas': datos.coordenadas,
                        'num_beneficiario_directo': datos.num_beneficiario_directo,
                        'num_beneficiario_indirecto': datos.num_beneficiario_indirecto,
                        'especifico': datos.especifico,
                        'caracteristica': datos.caracteristica,
                    })


                    data['idproyecto'] = datos.proyecto.id
                    return render(request, "proyectovinculaciondocente/editbeneficiario.html", data)
                except Exception as ex:
                    pass

            if action == 'deletebeneficiario':
                try:
                    data['title'] = u'Eliminar beneficiario'
                    data['participante'] = beneficiario = Beneficiarios.objects.get(pk=request.GET['id'])
                    return render(request, "proyectovinculaciondocente/deletebeneficiario.html", data)
                except Exception as ex:
                    pass

            if action == 'addinvolucrado':
                try:
                    data['title'] = u'Adicionar involucrados'
                    data['form'] = InvolucradoForm
                    data['idproyecto'] = request.GET['idproyecto']
                    return render(request, "proyectovinculaciondocente/addinvolucrado.html", data)
                except Exception as ex:
                    pass

            if action == 'editinvolucrado':
                try:
                    data['title'] = u'Editar involucrados'
                    data['id'] = id = request.GET['id']
                    datos = Involucrado.objects.get(pk=id)
                    data['form'] = InvolucradoForm(initial={
                        'nombre': datos.nombre,
                        'direccion': datos.direccion,
                        'correo': datos.correo,
                        'representante': datos.representante,
                        'cargo_repre': datos.cargo_repre,
                        'telefono': datos.telefono,
                        'coordenadas': datos.coordenadas,
                        'tipoActor': datos.tipoActor,
                    })


                    data['idproyecto'] = datos.proyecto.id
                    return render(request, "proyectovinculaciondocente/editinvolucrado.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteinvolucrado':
                try:
                    data['title'] = u'Eliminar beneficiario'
                    data['participante'] = Involucrado.objects.get(pk=request.GET['id'])
                    return render(request, "proyectovinculaciondocente/deleteinvolucrado.html", data)
                except Exception as ex:
                    pass

            if action == 'editArbolProblema':
                try:
                    data['title'] = u'Editar árbol de problema'
                    data['id'] = id = request.GET['id']
                    datos = ArbolProblema.objects.get(id=id)
                    data['form'] = ArProblemaForm(initial={
                        'detalle': datos.detalle,
                    })
                    id = request.GET['id']
                    data['idproyecto'] = datos.proyecto.id
                    return render(request, "proyectovinculaciondocente/editarbolproblema.html", data)
                except Exception as ex:
                    pass

            if action == 'addSubCausa':
                try:
                    data['title'] = u'Añadir subcausa'
                    data['form'] = ArProblemaForm()
                    data['pry'] = request.GET['pry']
                    data['id'] = request.GET['id']
                    return render(request, "proyectovinculaciondocente/addsubcausa.html", data)
                except Exception as ex:
                    pass

            elif action == 'addCausaEfecto':
                try:
                    data['title'] = u'Añadir causa efecto'
                    data['form'] = ArProb_CausaEfectoForm()
                    data['pry'] = request.GET['pry']
                    return render(request, "proyectovinculaciondocente/addcausaefecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'addDatoSecundario':
                    try:
                        data['title'] = u'Añadir dato secundario'
                        data['form'] = DatoSecundarioForm()
                        data['pry'] = request.GET['id']
                        return render(request, "proyectovinculaciondocente/adddatosecundario.html", data)
                    except Exception as ex:
                        pass

            elif action == 'addcronograma':
                    try:
                        data['title'] = u'Añadir cronograma'
                        data['form'] = form = CronogramaForm()
                        data['aObj'] = request.GET['aObj']
                        aobj = ArbolObjetivo.objects.get(pk=request.GET['aObj'])
                        data['pry'] = aobj.proyecto.pk
                        docentes = ParticipantesMatrices.objects.values_list('profesor__pk',flat=True).filter(status=True, proyecto=aobj.proyecto)
                        form.fields["responsable"].queryset = Profesor.objects.filter(status=True,pk__in=docentes)
                        return render(request, "proyectovinculaciondocente/addcronograma.html", data)
                    except Exception as ex:
                        pass

            elif action == 'editDatoSecundario':
                    try:
                        data['title'] = u'Editar dato secundario'
                        datos = DatoSecundario.objects.get(pk= request.GET['id'])
                        data['form'] = DatoSecundarioForm(
                            initial={
                                'descripcion':datos.descripcion,
                            }
                        )
                        data['id'] = request.GET['id']
                        data['pry'] = datos.proyecto.pk
                        return render(request, "proyectovinculaciondocente/edidatosecundario.html", data)
                    except Exception as ex:
                        pass

            elif action == 'editLineaBase':
                    try:
                        data['title'] = u'Editar dato primario'
                        data['id'] = id =  request.GET['id']
                        datos = MatrizLineaBase.objects.get(pk= id)
                        data['form'] = LineaBaseForm(
                            initial={
                                'item': datos.arbolProblema.detalle,
                                'descripcion': datos.descripcion,
                                'metodo': datos.metodo,
                                'fuente': datos.fuente,
                                'linea_base': datos.datos_linea_base,
                            }
                        )

                        data['pry'] = datos.proyecto.pk
                        return render(request, "proyectovinculaciondocente/editlineabase.html", data)
                    except Exception as ex:
                        pass

            elif action == 'editArbolObjetivo':
                    try:
                        data['title'] = u'Editar árbol de objetivo'
                        data['id'] = id =  request.GET['id']
                        datos = ArbolObjetivo.objects.get(id=id)
                        data['form'] = ArObjetivoForm(
                            initial={
                                 'detalle': datos.detalle,
                            }
                        )

                        data['pry'] = datos.proyecto.pk
                        return render(request, "proyectovinculaciondocente/editarbolobjetivo.html", data)
                    except Exception as ex:
                        pass

            elif action == 'editMarcoLogico':
                    try:
                        data['title'] = u'Editar marco lógico'
                        data['id'] = id =  request.GET['id']
                        datos = MarcoLogico.objects.get(id=id)
                        if request.GET['bool'] == 'True':
                            data['bool_marLogi'] = True
                        data['form']= form = MarcoLogicoForm2(
                            initial={
                                'resumen_narrativo': datos.resumen_narrativo,
                                'dato': MatrizLineaBase.objects.get(arbolProblema=datos.arbolObjetivo.arbolProblema).datos_linea_base  if MatrizLineaBase.objects.get(arbolProblema=datos.arbolObjetivo.arbolProblema).datos_linea_base else "No existe línea base",
                                'indicador': datos.indicador,
                                'fuente': datos.fuente,
                                'supuestos': datos.supuestos,
                                'cumplimiento': datos.cumplimiento,
                            }
                        )
                        if datos.arbolObjetivo.parentID:
                            form.deshabilitar_campo('cumplimiento')
                        data['pry'] = datos.proyecto.pk
                        return render(request, "proyectovinculaciondocente/editmarcologico2.html", data)
                    except Exception as ex:
                        pass

            elif action == 'deleteArbolProblema':
                try:
                    data['title'] = u'Eliminar detalle arbol de problema'
                    data['detalle'] = ArbolProblema.objects.get(id=request.GET['id'])
                    return render(request, "proyectovinculaciondocente/deletearbolproblema.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteDatoSecundario':
                try:
                    data['title'] = u'Eliminar dato secundario'
                    data['detalle'] = DatoSecundario.objects.get(id=request.GET['id'])
                    return render(request, "proyectovinculaciondocente/deletedatosecundario.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcronograma':
                    try:
                        data['title'] = u'Editar cronograma'
                        data['id'] = id = request.GET['id']
                        datos = Cronograma.objects.get(pk=id)
                        data['form'] = form = CronogramaForm(
                            initial={
                                'responsable': [i.id for i in datos.responsable.all()],
                                'descripcion': datos.descripcion,
                                'fecha_inicio': datos.fecha_inicio,
                                'fecha_fin': datos.fecha_fin,
                            }
                        )
                        data['pry'] = datos.proyecto.pk
                        docentes = ParticipantesMatrices.objects.values_list('profesor__pk',flat=True).filter(status=True, proyecto=datos.proyecto)
                        form.fields["responsable"].queryset = Profesor.objects.filter(status=True,pk__in=docentes)
                        return render(request, "proyectovinculaciondocente/editcronograma.html", data)
                    except Exception as ex:
                        pass

            elif action == 'deletecronograma':
                try:
                    data['title'] = u'Eliminar cronograma'
                    data['detalle'] = Cronograma.objects.get(pk=request.GET['id'])
                    return render(request, "proyectovinculaciondocente/deletecronograma.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpresupuesto':
                    try:
                        data['title'] = u'Añadir presupuesto'
                        data['form'] = form = PresupuestoForm()
                        data['pry'] = ArbolObjetivo.objects.get(pk=request.GET['aObj']).proyecto.pk
                        data['aObj'] = request.GET['aObj']
                        return render(request, "proyectovinculaciondocente/addpresupuesto.html", data)
                    except Exception as ex:
                        pass

            elif action == 'editpresupuesto':
                    try:
                        data['title'] = u'Editar presupuesto'
                        data['id'] = id = request.GET['id']
                        datos = Presupuesto.objects.get(pk=id)

                        data['form'] = form = PresupuestoForm(initial={
                            'cantidad': datos.cantidad,
                            'suministro': datos.suministro,
                            'costo_unitario': datos.costo_unitario,
                            'subtotal': datos.subtotal,
                            'iva': datos.iva,
                            'total': datos.total,
                            'especificaciones': datos.especificaciones,
                            'aplica_iva': datos.suministro.aplicaIva if datos.suministro else False
                        })
                        data['pry'] = datos.proyecto.pk
                        return render(request, "proyectovinculaciondocente/editpresupuesto.html", data)
                    except Exception as ex:
                        pass

            elif action == 'deletepresupuesto':
                try:
                    data['title'] = u'Eliminar Presupuesto'
                    data['detalle'] = Presupuesto.objects.get(pk=request.GET['id'])
                    return render(request, "proyectovinculaciondocente/deletepresupuesto.html", data)
                except Exception as ex:
                    pass

            elif action == 'addredaccion':
                    try:
                        data['title'] = u'Añadir redacción'
                        data['form'] = form = RedaccionForm()
                        data['pry'] = request.GET['idproyecto']
                        return render(request, "proyectovinculaciondocente/addredaccion.html", data)
                    except Exception as ex:
                        pass

            elif action == 'editredaccion':
                    try:
                        data['title'] = u'Editar redacción'
                        data['id'] = id = request.GET['id']
                        datos = Problema.objects.get(pk=id)
                        data['form'] = form = RedaccionForm(
                            initial={
                                'proyecto': datos.proyecto,
                                'antecedentes': datos.antecedentes,
                                'descripcion': datos.descripcion,
                                'deteccion_necesidades': datos.deteccion_necesidades,
                                'justificacion': datos.justificacion,
                                'Pertinencia': datos.Pertinencia,
                                'metodologia': datos.metodologia,
                                'seguimiento': datos.seguimiento,
                                'evaluacion': datos.evaluacion,
                                'producto': datos.producto,
                                'Bibliografia': datos.Bibliografia,
                                'objetivo_general': datos.objetivo_general,
                                'objetivos_especificos': datos.objetivos_especificos,
                                'convenio': datos.convenio,
                            }
                        )
                        data['pry'] = datos.proyecto.pk
                        return render(request, "proyectovinculaciondocente/editredaccion.html", data)
                    except Exception as ex:
                        pass

            elif action == 'addanexo':
                    try:
                        data['title'] = u'Añadir anexos'
                        data['form'] = form = AnexosForm()
                        data['pry'] = request.GET['idproyecto']
                        return render(request, "proyectovinculaciondocente/addanexo.html", data)
                    except Exception as ex:
                        pass

            elif action == 'editanexo':
                    try:
                        data['title'] = u'Editar anexos'
                        data['id'] = id= request.GET['id']
                        datos = Anexos.objects.get(pk=id)
                        data['form'] = form = AnexosForm(
                            initial={
                                'titulo': datos.titulo,
                            }
                        )
                        data['pry'] = datos.proyecto.pk
                        return render(request, "proyectovinculaciondocente/editanexo.html", data)
                    except Exception as ex:
                        pass

            elif action == 'deleteanexo':
                try:
                    data['title'] = u'Eliminar anexo'
                    data['detalle'] = Anexos.objects.get(pk=request.GET['id'])
                    return render(request, "proyectovinculaciondocente/deleteanexo.html", data)
                except Exception as ex:
                    pass

            elif action == 'costo':
                try:
                    suministro = Suministro.objects.get(status=True, pk=request.GET['id'])
                    costo = suministro.costo_unitario
                    coninva = suministro.aplicaIva
                    especificacion = suministro.especificacion
                    return JsonResponse({"result": "ok", "costo": costo, 'aplicaIva': coninva, 'especificacion': especificacion})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

            elif action == 'editmarcologico':
                try:
                    data['title'] = u'Editar'
                    data['marcologicoproyectosinvestigacion'] = marcologicoproyectosinvestigacion = MarcoLogicoProyectosInvestigacion.objects.get(pk=request.GET['id'])
                    form = MarcoLogicoForm(initial={'tipo': marcologicoproyectosinvestigacion.tipo,
                                                    'resumen': marcologicoproyectosinvestigacion.resumen,
                                                    'indicadores': marcologicoproyectosinvestigacion.indicadores,
                                                    'fuentes': marcologicoproyectosinvestigacion.fuentes,
                                                    'numero': marcologicoproyectosinvestigacion.numero,
                                                    'supuestos': marcologicoproyectosinvestigacion.supuestos})
                    form.editar()
                    data['form'] = form
                    return render(request, "proyectovinculaciondocente/editmarcologico.html", data)
                except Exception as ex:
                    pass

            elif action == 'evidencias':
                try:
                    if 'id' in request.GET:
                        data['detalleevidenciasinformes'] = DetalleEvidenciasInformes.objects.filter(detalleinforme__id=int(request.GET['id']), status=True)
                        template = get_template("proyectovinculaciondocente/evidencias.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'ejecucion':
                try:
                    est, search, desde, hasta, mdesde, mhasta, filtros, url = \
                        request.GET.get('est', ''), \
                        request.GET.get('s', ''), \
                        request.GET.get('desde', ''), \
                        request.GET.get('hasta', ''), \
                        request.GET.get('mdesde', ''),\
                        request.GET.get('mhasta', ''),\
                        Q(status=True), \
                        ''
                    if est:
                        data['ejec_estado'] = estado = int(est)
                        url += "&est={}".format(estado)
                        if estado == 1:
                            filtros = filtros & Q(estado_finalizado=False)
                        elif estado == 2:
                            filtros = filtros & Q(estado_finalizado=True)
                    if desde and hasta:
                        data['ejec_desde'] = desde
                        data['ejec_hasta'] = hasta
                        url += "&desde={}".format(desde)
                        url += "&hasta={}".format(hasta)
                        filtros = filtros & (Q(fecha_inicio__gte=desde) & Q(fecha_fin__lte=hasta))

                    elif desde:
                        data['ejec_desde'] = desde
                        url += "&desde={}".format(desde)
                        filtros = filtros & Q(fecha_inicio__gte=desde)
                    elif hasta:
                        data['ejec_hasta'] = hasta
                        url += "&hasta={}".format(hasta)
                        filtros = filtros & Q(fecha_fin__lte=hasta)

                    if mdesde and mhasta:
                        data['ejec_mes_desde'] = mdesde
                        data['ejec_mes_hasta'] = mhasta
                        url += "&mdesde={}".format(mdesde)
                        url += "&mhasta={}".format(mhasta)
                        filtros = filtros & (Q(fecha_inicio__month__gte=datetime.strptime(mdesde, '%Y-%m').date().month) &
                                             Q(fecha_fin__month__lte=datetime.strptime(mhasta, '%Y-%m').date().month)&
                                             Q(fecha_inicio__year=datetime.strptime(mdesde, '%Y-%m').date().year) &
                                             Q(fecha_fin__year=datetime.strptime(mhasta, '%Y-%m').date().year))

                    elif mdesde:
                        data['ejec_mes_desde'] = mdesde
                        url += "&mdesde={}".format(mdesde)
                        filtros = filtros & (Q(fecha_inicio__month__lte=datetime.strptime(mdesde, '%Y-%m').date().month) &
                                             Q(fecha_fin__month__gte=datetime.strptime(mdesde, '%Y-%m').date().month) &
                                             Q(fecha_inicio__year=datetime.strptime(mdesde, '%Y-%m').date().year)

                                             )

                    elif mhasta:
                        data['ejec_mes_hasta'] = mhasta
                        url += "&mhasta={}".format(mhasta)
                        filtros = filtros & (Q(fecha_fin__month__lte=datetime.strptime(mhasta, '%Y-%m').date().month) &
                                             Q(fecha_fin__year=datetime.strptime(mhasta, '%Y-%m').date().year))

                    if search:
                        data['search'] = search
                        s = search.split()
                        if len(s) == 1:
                            filtros = filtros & (Q(responsable__persona__apellido1__icontains=search) |
                                                 Q(responsable__persona__apellido2__icontains=search) |
                                                 Q(responsable__persona__cedula__icontains=search) |
                                                 Q(responsable__persona__nombres__icontains=search))
                            url += '&search={}'.format(search)
                        else:
                            filtros = filtros & (Q(responsable__persona__apellido1__icontains=s[0]) &
                                                 Q(responsable__persona__apellido2__icontains=s[1]))
                            url += '&search={}'.format(search)
                    data['url'] = url
                    data['title'] = u'Cronograma de ejecución'
                    data['proyecto'] = proyecto = ProyectosInvestigacion.objects.get(pk=request.GET['id'],tipo=1)
                    data['lider'] = ParticipantesMatrices.objects.filter(status=True, proyecto=proyecto, tipoparticipante__pk=1,profesor=profesor).exists()
                    data['cronograma'] = cronograma = Cronograma.objects.filter(filtros, status=True, proyecto=proyecto)
                    data['misactividades'] = micronograma =  Cronograma.objects.filter(filtros, status=True, proyecto=proyecto, responsable__persona__usuario=request.user)
                    data['hoy'] = datetime.now().date()
                    data['aPro_marcoLogico_acciones'] = MarcoLogico.objects.filter(status=True, proyecto=proyecto,arbolObjetivo__tipo=2,arbolObjetivo__parentID__isnull=False)
                    data['aPro_marcoLogico_componentes'] = MarcoLogico.objects.filter(status=True, proyecto=proyecto,arbolObjetivo__tipo=2,arbolObjetivo__parentID__isnull=True).order_by('arbolObjetivo__orden')
                    data['total_pendientes'] = cronograma.filter(estado_finalizado=False).count()
                    data['total_finalizados'] = cronograma.filter(estado_finalizado=True).count()
                    data['mis_pendientes'] = micronograma.filter(estado_finalizado=False, responsable = profesor).count()
                    data['mis_finalizados'] = micronograma.filter(estado_finalizado=True, responsable=profesor).count()
                    return render(request, "proyectovinculaciondocente/ejecucionCronograma.html", data)
                except Exception as ex:
                    pass

            elif action == 'addavance':
                try:
                    data['title'] = u'Ingresar avance'
                    data['id'] = id = request.GET['id']
                    data['tarea'] = tarea = Cronograma.objects.get(pk=id)
                    detalle = DetalleCumplimiento.objects.filter(status=True, tarea=tarea, aprobacion=False, usuario_creacion = request.user)
                    if detalle.exists():
                        return JsonResponse({"result": 'bad', "mensaje": u"Tiene avances pendientes de aprobación."})

                    avance = DetalleCumplimiento.objects.filter(status=True, tarea=tarea, aprobacion=True, usuario_creacion=request.user).aggregate(avance=Sum('avance'))['avance']
                    if avance:
                        avance = int(avance)
                    else:
                        avance = 0
                    data['avance'] = avance
                    data['faltante'] = faltante = 100 - avance
                    data['form'] = AvanceEjecucionForm(initial={
                        'porcentaje': faltante,
                    })

                    template = get_template("inv_vinculacion/addavance.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'editavance':
                try:
                    data['title'] = u'Editar avance'
                    data['id'] = id = request.GET['id']
                    data['tarea'] = tarea = DetalleCumplimiento.objects.get(pk=id)
                    #data['avance'] = avance  = tarea.tarea.avance()
                    avance = DetalleCumplimiento.objects.filter(status=True, tarea=tarea.tarea, aprobacion=True,usuario_creacion=request.user).aggregate(avance=Sum('avance'))['avance']
                    if avance:
                        avance = int(avance)
                    else:
                        avance = 0
                    data['avance'] = avance
                    data['faltante'] = faltante = 100 - int(avance)
                    data['form'] = AvanceEjecucionForm(initial={
                        'porcentaje': int(tarea.avance),
                        'fecha': tarea.fecha_ingreso,
                        'observacion': tarea.observacion,
                        'evidencia': tarea.evidencia,
                    })

                    template = get_template("inv_vinculacion/editavance.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'veravance':
                try:
                    data['title'] = u'Ver avance'
                    data['id'] = id = request.GET['id']
                    data['tarea'] = tarea = Cronograma.objects.get(pk=id)
                    data['lider'] = lider = ParticipantesMatrices.objects.filter(status=True, proyecto=tarea.proyecto,tipoparticipante__pk=1,profesor=profesor).exists()
                    if lider:
                        data['avance'] = DetalleCumplimiento.objects.filter(status=True, tarea=tarea).order_by('fecha_ingreso')
                    else:
                        data['avance'] = DetalleCumplimiento.objects.filter(status=True, tarea=tarea, usuario_creacion = request.user).order_by('fecha_ingreso')

                    template = get_template("inv_vinculacion/veravance.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'configurarinforme':
              try:
                  data['title'] = u'Configurar Informe'
                  data['proyecto'] = proyecto= ProyectosInvestigacion.objects.get(pk=request.GET['id'])
                  data['lider'] = ParticipantesMatrices.objects.filter(status=True, proyecto=proyecto,tipoparticipante__pk=1,profesor=profesor).exists()
                  data['configuraciones'] = ConfiguracionInformeVinculacion.objects.filter(status=True, proyecto= proyecto, usuario_creacion=request.user).order_by('-fecha_inicio')
                  data['informePromotor'] = ConfiguracionInformeVinculacion.objects.filter(status=True, proyecto= proyecto).exclude(usuario_creacion=request.user).order_by('-fecha_inicio')
                  data['tecnico'] = TecnicoAsociadoProyectoVinculacion.objects.filter(proyecto=proyecto, activo=True).first()
                  return render(request, "proyectovinculaciondocente/configurar_informe.html", data)
              except Exception as ex:
                  pass


            if action == 'firmainformevinculacion':
                try:
                    data['form2'] = FirmaElectronicaIndividualForm()
                    data['id'] = request.GET.get('id')
                    data['revision'] = int(request.GET.get('revision', 0))
                    data['modal'] = request.GET.get('modal', None)
                    data['action'] = action if not request.GET.get('masivo', None) else 'firmainformevinculacionmasivo'
                    data['pks'] = ', '.join(request.GET.getlist('pks[]'))
                    template = get_template("proyectovinculaciondocente/modal/firmardocumentoauto.html")
                    return JsonResponse({"result": "ok", 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'actividadExtra':
                try:
                    data['title'] = u'Actividades extras'
                    data['configuracion'] = conf = ConfiguracionInformeVinculacion.objects.get(pk=request.GET['id'])
                    data['actividades'] = ActividadExtraVinculacion.objects.filter(status=True, configuracion=conf)

                    return render(request, "proyectovinculaciondocente/actividades_extras.html", data)
                except Exception as ex:
                    pass

            elif action == 'addconfigurarinforme':
                 try:
                    data['title'] = u'Añadir Configuracion Informe'
                    data['form'] = form = Configuracion_Informe_VinculacionForm()
                    data['proyectos'] = proyecto = ProyectosInvestigacion.objects.get(pk=request.GET['id'])
                    if ConfiguracionInformeVinculacion.objects.filter(status=True, proyecto=proyecto, usuario_creacion=request.user ).exclude(aprobacion=3).exists():
                        return HttpResponseRedirect("/proyectovinculaciondocente?action=configurarinforme&id="+str(proyecto.pk)+"&info=Tiene un informe pendiente de aprobación.")

                    return render(request, "proyectovinculaciondocente/addconfigurar_informe.html", data)
                 except Exception as ex:
                      pass

            elif action == 'editconfigurarinforme':
                try:
                    data['title'] = u'Editar Configuracion de Informe'
                    data['configuracion'] = configuracion = ConfiguracionInformeVinculacion.objects.get(pk=request.GET['id'])
                    form = Configuracion_Informe_VinculacionForm(initial={'fecha_inicio': configuracion.fecha_inicio,
                                                                             'fecha_fin': configuracion.fecha_fin,
                                                                             'observacion': configuracion.observacion,
                                                                          'actividades_extras':configuracion.actividades_extras})
                    data['form'] = form
                    return render(request, "proyectovinculaciondocente/editconfigurar_informe.html", data)
                except Exception as ex:
                    pass

            elif action == 'generar':
                try:
                    with transaction.atomic():
                        data['title'] = u"Generar informe"
                        data['configuracion'] = conf = ConfiguracionInformeVinculacion.objects.get(id=request.GET['id'])
                        lider = ParticipantesMatrices.objects.filter(status=True, proyecto=conf.proyecto,tipoparticipante__pk=1,profesor=profesor).exists()
                        if not DetalleInformeVinculacion.objects.filter(configuracion=conf, status=True).exists():
                            if not MarcoLogicoReporte.objects.filter(configuracion=conf, status=True).exists():
                                for m in MarcoLogico.objects.filter(status=True, proyecto=conf.proyecto):
                                    if m.arbolObjetivo.parentID:
                                        avance = m.avance()
                                        avancemensual = m.avancemensual(conf.fecha_inicio, conf.fecha_fin)
                                    else:
                                        avance = m.avancecomponente()
                                        avancemensual = m.avancecomponentemensual(conf.fecha_inicio, conf.fecha_fin)
                                    marcologico = MarcoLogicoReporte(
                                            proyecto=m.proyecto,
                                            configuracion=conf,
                                            arbolObjetivo=m.arbolObjetivo,
                                            cumplimiento=m.cumplimiento,
                                            avancemensual=avancemensual,
                                            avance = avance
                                        )
                                    marcologico.save(request)
                            if lider:
                                tareas = DetalleCumplimiento.objects.filter(tarea__proyecto=conf.proyecto, fecha_ingreso__gte=conf.fecha_inicio,fecha_ingreso__lte=conf.fecha_fin, status=True,aprobacion_adm=True).distinct('tarea')
                            else:
                                tareas = DetalleCumplimiento.objects.filter(usuario_creacion=request.user, tarea__proyecto=conf.proyecto, fecha_ingreso__gte=conf.fecha_inicio,fecha_ingreso__lte=conf.fecha_fin, status=True,aprobacion_adm=True).distinct('tarea')
                            for t in tareas:
                                marco = MarcoLogico.objects.get(status=True,arbolObjetivo=t.tarea.aobjetivo)
                                infor = DetalleInformeVinculacion(
                                    proyecto=conf.proyecto,
                                    configuracion=conf,
                                    actividad=marco,
                                    tarea=Cronograma.objects.get(pk=t.tarea.pk),
                                    resumen_narrativo=marco.resumen_narrativo,
                                    indicador=marco.indicador,
                                    fuente=marco.fuente,
                                    porcentaje_avance=t.tarea.avancerangofecha(conf.fecha_inicio, conf.fecha_fin),
                                    avanceacumulado=t.tarea.avance(),
                                )
                                infor.save(request)
                            finalidad = MarcoLogico.objects.filter(status=True,proyecto_id=conf.proyecto.pk, arbolObjetivo__tipo=3)
                            for fin in finalidad:
                                infor = DetalleInformeVinculacion(
                                    proyecto=conf.proyecto,
                                    configuracion=conf,
                                    actividad=fin,
                                    resumen_narrativo=fin.resumen_narrativo,
                                    indicador=fin.indicador,
                                    fuente=fin.fuente,
                                )
                                infor.save(request)
                            proposito = MarcoLogico.objects.filter(status=True, proyecto_id=conf.proyecto.pk, arbolObjetivo__tipo=1).order_by('arbolObjetivo__orden')
                            for pro in proposito:
                                infor = DetalleInformeVinculacion(
                                    proyecto=conf.proyecto,
                                    configuracion=conf,
                                    actividad=pro,
                                    resumen_narrativo=pro.resumen_narrativo,
                                    indicador=pro.indicador,
                                    fuente=pro.fuente,
                                    porcentaje_avance=conf.proyecto.totalavance(),
                                )
                                infor.save(request)
                        if not conf.avance_registro:
                            conf.avance_registro = conf.avancemensual()
                            conf.save(request)
                        if lider:
                            data['acciones'] = DetalleInformeVinculacion.objects.filter(status=True, configuracion__id=(request.GET['id']))
                        else:
                            data['acciones'] = DetalleInformeVinculacion.objects.filter(status=True, usuario_creacion=request.user, configuracion__id=(request.GET['id']))
                        data['componentes'] = MarcoLogico.objects.filter(status=True, proyecto=conf.proyecto, arbolObjetivo__tipo=2, arbolObjetivo__parentID__isnull=True)
                        data['proyecto'] = conf.proyecto
                        proyecto = ProyectosInvestigacion.objects.get(pk=conf.proyecto.pk)
                        data['fines'] = DetalleInformeVinculacion.objects.filter(status=True, configuracion=conf, proyecto=proyecto, usuario_creacion=request.user, actividad__arbolObjetivo__tipo=3)
                        data['propositos'] = DetalleInformeVinculacion.objects.filter(status=True, configuracion=conf, proyecto=proyecto, usuario_creacion=request.user, actividad__arbolObjetivo__tipo=1)
                        data['aPro_marcoLogico_acciones'] = MarcoLogicoReporte.objects.filter(status=True, configuracion=conf, proyecto=proyecto, arbolObjetivo__tipo=2, arbolObjetivo__parentID__isnull=False)
                        data['aPro_marcoLogico_componentes'] = MarcoLogicoReporte.objects.filter(status=True, configuracion=conf, proyecto=proyecto,arbolObjetivo__tipo=2, arbolObjetivo__parentID__isnull=True)

                        owner = conf.profesor.persona
                        lider = conf.proyecto.lider()

                        pk_criterio = [151, 150][owner == lider]
                        data['criterio'] = c = CriterioDocencia.objects.filter(pk=pk_criterio).first()
                        data['tieneactividadasignada'] = DetalleDistributivo.objects.values('id').filter(criteriodocenciaperiodo__periodo=periodo, criteriodocenciaperiodo__criterio=c, distributivo__profesor__persona=owner, distributivo__periodo=periodo, status=True).exists()
                        data['ES_ACTIVIDAD_MACRO'] = DetalleDistributivo.objects.values('id').filter(criteriodocenciaperiodo__periodo=periodo, criteriodocenciaperiodo__criterio=variable_valor('ACTIVIDAD_MACRO_VINCULACION'), distributivo__profesor__persona=owner, distributivo__periodo=periodo, status=True).exists()
                        return render(request, 'proyectovinculaciondocente/GenerarInforme.html', data)
                except Exception as ex:
                    pass

            elif action == 'editgenerar':
                try:
                    data['title'] = u'Editar Informe'
                    data['registro'] = registro = DetalleInformeVinculacion.objects.get(pk=request.GET['id'])
                    data['form'] = form = Detalle_InformeForm(initial={'resumen_narrativo': registro.resumen_narrativo,
                                                                       'indicador': registro.indicador,
                                                                       'fuente': registro.fuente,
                                                                       'tarea': registro.tarea.descripcion if registro.tarea else "S/D",
                                                                       'factor_exito': registro.factor_exito,
                                                                       'factor_problema': registro.factor_problema,
                                                                       'porcentaje': registro.porcentaje_avance})
                    return render(request, 'proyectovinculaciondocente/editgenerar.html', data)
                except Exception as ex:
                    pass

            elif action == 'generarinformepdf':
                try:
                    filtrodetalle = Q(status=True, configuracion__id=request.GET['id'])
                    conf = ConfiguracionInformeVinculacion.objects.get(id=request.GET['id'])
                    detalleinfo = DetalleInformeVinculacion.objects.filter(status=True, configuracion=conf)
                    data['lider'] = ParticipantesMatrices.objects.get(status=True, proyecto=conf.proyecto,tipoparticipante__pk=1, activo=True)
                    detalle = DetalleInformeVinculacion.objects.filter(status=True, configuracion=conf, editado=False).exclude(actividad__arbolObjetivo__tipo=3)
                    eslider = ParticipantesMatrices.objects.values('id').filter(status=True, proyecto=conf.proyecto, tipoparticipante__pk=1, profesor=conf.profesor, activo=True).exists()

                    if detalle.exists() or not detalleinfo.exists():
                        return JsonResponse({'result': 'bad', 'mensaje': f"Debe completar la información del informe."})

                    if not eslider:
                        filtrodetalle &= Q(usuario_creacion=request.user)

                    data['eslider'] = eslider
                    data['configuracion'] = conf
                    data['proyecto'] = proyecto = conf.proyecto
                    data['responsablevinculacion'] = responsablevinculacion
                    data['acciones'] = DetalleInformeVinculacion.objects.filter(filtrodetalle)
                    data['extras'] = ActividadExtraVinculacion.objects.filter(configuracion=conf, status=True)
                    data['revisor'] = 'LÍDER DE PROYECTO' if conf.personaaprueba == proyecto.lider() else 'TÉCNICO DOCENTE DE VINCULACIÓN'
                    data['fines'] = DetalleInformeVinculacion.objects.filter(status=True, configuracion=conf, proyecto=proyecto, usuario_creacion=request.user,actividad__arbolObjetivo__tipo=3)
                    data['propositos'] = DetalleInformeVinculacion.objects.filter(status=True, configuracion=conf, proyecto=proyecto, usuario_creacion=request.user,actividad__arbolObjetivo__tipo=1)
                    data['componentes'] = MarcoLogico.objects.filter(status=True, proyecto=conf.proyecto,arbolObjetivo__tipo=2, arbolObjetivo__parentID__isnull=True).order_by('arbolObjetivo__orden')
                    data['aPro_marcoLogico_acciones'] = MarcoLogicoReporte.objects.filter(status=True, configuracion=conf, proyecto=proyecto,arbolObjetivo__tipo=2,arbolObjetivo__parentID__isnull=False)
                    data['aPro_marcoLogico_componentes'] = MarcoLogicoReporte.objects.filter(status=True, configuracion=conf, proyecto=proyecto, arbolObjetivo__tipo=2,arbolObjetivo__parentID__isnull=True).order_by('arbolObjetivo__orden')

                    liderproyecto = conf.proyecto.lider()
                    tecnicoasociado = conf.proyecto.get_tecnicoasociado()
                    filename = generar_nombre(f'{persona.usuario}_', 'file.pdf')
                    nombrerevisor, cargorevisor = liderproyecto, 'LÍDER DEL PROYECTO'
                    folder_pdf = os.path.join(SITE_STORAGE, 'media', 'informeProyectoVinculacion', '')

                    if persona == liderproyecto and tecnicoasociado:
                        nombrerevisor, cargorevisor = tecnicoasociado.persona, tecnicoasociado.cargo

                    data['cargorevisor'] = cargorevisor
                    data['nombrerevisor'] = nombrerevisor
                    data['tecnicoasociado'] = tecnicoasociado

                    if request.GET.get('json', None):
                        if convert_html_to_pdf('proyectovinculaciondocente/generarinformepdf.html', {'data': data}, filename, folder_pdf):
                            conf.archivo = f'informeProyectoVinculacion{os.sep}{filename}'
                            conf.save(request)
                    else:
                        return conviert_html_to_pdf('proyectovinculaciondocente/generarinformepdf.html', {'pagesize': 'A4','data': data})

                    # Respuesta del backend para firma de archivo
                    data['form2'] = FirmaElectronicaIndividualForm()
                    data['id'] = conf.pk
                    data['revision'] = 1
                    data['action'] = 'firmainformevinculacion'
                    template = get_template("proyectovinculaciondocente/modal/firmardocumentoauto.html")
                    # --------------------------------------------

                    log(f'Generó un informe de vinculacion {conf.pk}', request, "add")
                    return JsonResponse({'result': 'ok', 'id': conf.pk, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': 'bad', 'mensaje': f"Error de conexión, {ex.__str__()}"})

            elif action == 'addactividad':
                try:
                    data['title'] = u'Ingresar actividad extra'
                    data['id'] = id = request.GET['id']
                    data['conf'] = conf = ConfiguracionInformeVinculacion.objects.get(pk=id)
                    data['form'] = ActividadExtraForm()

                    template = get_template("proyectovinculaciondocente/addactividadextra.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'editactividad':
                try:
                    data['title'] = u'Editar actividad extra'
                    data['id'] = id = request.GET['id']
                    actividad = ActividadExtraVinculacion.objects.get(pk=id)
                    data['conf'] = actividad.pk
                    data['form'] = ActividadExtraForm(initial={
                                    'descripcion':actividad.descripcion,
                                    'fecha_inicio':actividad.fecha_inicio,
                                    'fecha_fin':actividad.fecha_fin,
                    })

                    template = get_template("proyectovinculaciondocente/editactividadextra.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'aprobarInforme':
                try:
                    data['title'] = u'Aprobacion de Configuraciones '
                    data['form2'] = AprobacionInformeForm()
                    data['id'] = int(request.GET['id'])
                    data['proyecto'] = request.GET['idproyecto']
                    template = get_template("proyectovinculaciondocente/aprobacionInforme.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'inscripcion':
                try:
                    data['title'] = u'Inscripcion de estudiantes'
                    search = None
                    id = request.GET['id']
                    if 's' in request.GET:
                        search = request.GET['s']
                        periodoinscripcion = PeriodoInscripcionVinculacion.objects.select_related().filter(status=True, proyecto__pk = id, observacion__contains=search)
                    elif 'id' in request.GET:
                        periodoinscripcion = PeriodoInscripcionVinculacion.objects.select_related().filter(status=True, proyecto__pk=id)
                    paging = MiPaginador(periodoinscripcion, 25)
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
                    data['periodos'] = page.object_list
                    data['proyecto'] = id
                    data['search'] = search if search else ""

                    return render(request, "proyectovinculaciondocente/periodoInscripcion.html", data)
                except Exception as ex:
                    pass

            elif action == 'verdetalle':

                try:
                    data['title'] = u'Detalle carrera'

                    data['periodoinscrip'] = periodovinculacion = PeriodoInscripcionVinculacion.objects.get(pk=request.GET['id'])
                    data['carreras'] = CarreraInscripcionVinculacion.objects.select_related().filter(status=True, periodo = periodovinculacion)
                    template = get_template("proyectovinculaciondocente/detalleinscripcion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'addperiodoinscripcion':
                try:
                    data['title'] = u'Adicionar periodo inscripción'
                    data['form'] = PeriodoInscripcionFrom
                    data['id'] = request.GET['id']
                    template = get_template("proyectovinculaciondocente/addperiodoinscripcion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'editperiodoinscripcion':
                try:
                    data['title'] = u'Editar periodo inscripción'
                    periodo = PeriodoInscripcionVinculacion.objects.get(pk= request.GET['id'])
                    data['form'] = PeriodoInscripcionFrom(initial={
                        'observacion': periodo.observacion,
                        'fechainicio': periodo.fechainicio,
                        'fechafin': periodo.fechafin,
                    })
                    data['id'] = request.GET['id']
                    data['proyecto'] = periodo.proyecto.pk
                    template = get_template("proyectovinculaciondocente/editperiodoinscripcion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'habilitarcargainforme':
                try:
                    data['title'] = u'Informes Para Proyecto de Vinculación'
                    data['id'] = id = request.GET['id']
                    data['proyecto'] = proyecto = ProyectosInvestigacion.objects.get(pk=request.GET['id'], tipo = 1)
                    data['fechaactual'] =  datetime.now().date()
                    data['informes_habilitados'] = InformesProyectoVinculacionDocente.objects.filter(status=True, proyecto=proyecto).order_by('fecha_creacion')
                    return render(request, 'proyectovinculaciondocente/listadoinformeshabilitados.html', data)
                except Exception as ex:
                    pass

            elif action == 'addhabilitacioninforme':
                try:
                    data['id'] = id = request.GET['id']
                    data['proyecto'] = ProyectosInvestigacion.objects.get(pk=request.GET['id'], tipo = 1)
                    data['formulario'] = InformeProyectoVinculacionForm()
                    template = get_template("proyectovinculaciondocente/modal/modal_habilitarinforme.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            # elif action == 'editarhabilitacioninforme':
            #     try:
            #         data['id'] = request.GET['id']
            #
            #         data['informe'] = informe = InformesProyectoVinculacionDocente.objects.get(pk=int(request.GET['id']))
            #         data['formulario'] = InformeProyectoVinculacionForm(initial=model_to_dict(informe))
            #         template = get_template("proyectovinculaciondocente/modal/modal_habilitarinforme.html")
            #         return JsonResponse({"result": True, 'data': template.render(data)})
            #     except Exception as ex:
            #         pass

            elif action == 'editarhabilitacioninforme':
                try:
                    data['id'] = request.GET['id']

                    data['informe'] = informe = InformesProyectoVinculacionDocente.objects.get(pk=int(request.GET['id']))
                    data['formulario'] = InformeProyectoVinculacionFechaForm(initial=model_to_dict(informe))
                    template = get_template("proyectovinculaciondocente/modal/modal_habilitarinforme.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'eliminarhabilitacioninforme':
                try:
                    data['title'] = u'Eliminar informe habilitado'
                    data['informe'] = InformesProyectoVinculacionDocente.objects.get(pk=int(request.GET['id']))
                    return render(request, "proyectovinculaciondocente/modal/modal_eliminarinformehabilitado.html", data)
                except Exception as ex:
                    pass

            elif action == 'registrarhoras':
                try:
                    data['form'] = RegistrarHorasViculacionForm()
                    data['idparticipacion'] = request.GET['idparticipacion']
                    data['idparticipante'] = request.GET['idparticipante']
                    data['idproyecto'] = request.GET['idproyecto']
                    template = get_template("proyectovinculaciondocente/modal/modal_registrarhoras.html")
                    # json_content = template.render(data)
                    return JsonResponse({"result": True, "data": template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'adddocenteexterno':
                try:
                    data['title'] = u'Agregar Docente Externo'
                    proyecto = ProyectosInvestigacion.objects.get(pk=request.GET['idp'])
                    form = DocenteExternoForm(initial = {'funcionproyecto' : ParticipantesTipo.objects.get(pk=5).nombre})
                    data['proyecto'] = proyecto
                    data['form'] = form
                    return render(request, "proyectovinculaciondocente/adddocenteexterno.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscarpersona':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    filtro = Q(usuario__isnull=False, status=True)
                    if len(s) == 1:
                        filtro &= ((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) | Q(apellido2__icontains=q) | Q(cedula__contains=q)))
                    elif len(s) == 2:
                        filtro &= ((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) | (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) | (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1])))
                    else:
                        filtro &= ((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) | (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2])))

                    per = Persona.objects.filter(filtro).exclude(Q(cedula='') & Q(Q(administrativo__id__isnull=True) | Q(profesor__id__isnull=True))).order_by('apellido1', 'apellido2', 'nombres').distinct()[:15]
                    return JsonResponse({"result": "ok", "results": [{"id": x.id, "name": "%s %s" % (f"<img src='{x.get_foto()}' width='25' height='25' style='border-radius: 20%;' alt='...'>", x.nombre_completo_inverso())} for x in per]})
                except Exception as ex:
                    pass

            elif action == 'update-estado-revision':
                try:
                    conf = ConfiguracionInformeVinculacion.objects.get(id=request.GET['id'])
                    conf.aprobacion = int(request.GET['e'])
                    conf.save(request, update_fields=['aprobacion'])
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Listado de Proyectos'
                filtros = Q(status=True, tipo=1)
                # data['proyectos'] = ProyectosInvestigacion.objects.filter(status=True)
                data['estadoproyectos'] = ESTADOS_PROYECTO_VINCULACION_INVESTIGACION
                search = None
                ids = None
                tipobus = None
                inscripcionid = None
                fechaproyecto = FechaProyectos.objects.filter(status=True).last()
                if 'id' in request.GET:
                    ids = request.GET['id']
                    programasinvestigacion = ProyectosInvestigacion.objects.select_related().filter(pk=ids,tipo=1).order_by('nombre')
                elif 'inscripcionid' in request.GET:
                    inscripcionid = request.GET['inscripcionid']
                    programasinvestigacion = Graduado.objects.filter(inscripcion__carrera__in=miscarreras).filter(inscripcion__id=inscripcionid)
                if 's' in request.GET:
                    search = request.GET['s']
                    if search.isdigit():
                        filtros = filtros & Q(fechainicio__year=search) | Q(id=search)
                    else:
                        filtros = filtros & Q(nombre__icontains=search)
                if 'estado' in request.GET:
                    estado = request.GET['estado']
                    data['estado'] = int(estado)
                    filtros = filtros & Q(aprobacion=estado)
                #     if estado == "0":
                #         if search.isdigit():
                #             programasinvestigacion = ProyectosInvestigacion.objects.select_related().filter(Q(fechainicio__year=search) | Q(id=search), tipo=1, status=True, participantesmatrices__profesor=profesor)
                #         else:
                #             programasinvestigacion = ProyectosInvestigacion.objects.select_related().filter(nombre__icontains=search, tipo=1, status=True, participantesmatrices__profesor=profesor)
                #     else:
                #         if search.isdigit():
                #             programasinvestigacion = ProyectosInvestigacion.objects.select_related().filter(Q(fechainicio__year=search) | Q(id=search), tipo=1, status=True, aprobacion=estado, participantesmatrices__profesor=profesor)
                #         else:
                #             programasinvestigacion = ProyectosInvestigacion.objects.select_related().filter(nombre__icontains=search, tipo=1, status=True, aprobacion=estado, participantesmatrices__profesor=profesor)
                # else:
                #
                #     programasinvestigacion = ProyectosInvestigacion.objects.select_related().filter(status=True, tipo=1, participantesmatrices__profesor=profesor).order_by(
                #         '-aprobacion', '-programa__fecha_creacion', 'nombre')

                participante = ParticipantesMatrices.objects.values_list('proyecto_id', flat=True).filter(status=True, profesor = profesor)
                programasinvestigacion = ProyectosInvestigacion.objects.select_related().filter(filtros, id__in=participante).order_by('-aprobacion', '-programa__fecha_creacion', 'nombre')

                paging = MiPaginador(programasinvestigacion, 25)
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
                # fechaactual=datetime.now().date()
                # data['fechaactual']=fechaactual
                data['rangospaging'] = paging.rangos_paginado(p)
                data['proyectos'] = page.object_list
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                conv = FechaProyectos.objects.filter(status=True, fechainicio__lte=datetime.now(),fechafin__gte=datetime.now())
                if conv.exists():
                    data['convocatoria'] = conv.last()
                    if not ProyectosInvestigacion.objects.filter(status=True,convocatoria=conv.last(),usuario_creacion=request.user).exists():
                        data['conv_activa']=True
                return render(request, "proyectovinculaciondocente/view.html", data)
            except Exception as ex:
                pass


def migrar_evidencia_proyecto_vinculacion(request, solicitud, estadoaprobacion=1, evidencia=None):
    try:
        from sga.models import ProfesorDistributivoHoras
        from sga.templatetags.sga_extras import nombremes
        from inno.models import SubactividadDetalleDistributivo, Criterio
        from sga.pro_cronograma import CRITERIO_ASOCIADO_VIN, CRITERIO_DIRECTOR_VIN
        ACTIVIDAD_MACRO_VINCULACION = variable_valor('ACTIVIDAD_MACRO_VINCULACION')
        persona, periodo, migracion = request.session.get('persona'), request.session.get('periodo'), None
        if not evidencia:
            owner = solicitud.profesor.persona
            lider = solicitud.proyecto.lider()
            es_lider = owner == lider
            hoy = datetime.now().date()
            pk_criterio = [151, 150][es_lider]
            detalledistributivomacroact, detalledistributivoregular1 = None, None
            pk_subactividad = [CRITERIO_ASOCIADO_VIN, CRITERIO_DIRECTOR_VIN][es_lider]
            if distributivo := ProfesorDistributivoHoras.objects.filter(profesor=solicitud.profesor, periodo=periodo, activo=True, status=True).first():
                detalledistributivomacroact = distributivo.detalle_horas_vinculacion().filter(criteriodocenciaperiodo__es_actividadmacro=True, actividaddetalledistributivo__subactividaddetalledistributivo__subactividaddocenteperiodo__criterio=pk_subactividad, criteriodocenciaperiodo__criterio=ACTIVIDAD_MACRO_VINCULACION, status=True).first()
                detalledistributivoregular1 = distributivo.detalle_horas_vinculacion().filter(criteriodocenciaperiodo=pk_criterio).first()
            if detalledistributivomacroact or detalledistributivoregular1:
                criterio = detalledistributivomacroact if detalledistributivomacroact else detalledistributivoregular1
                subactividaddistributivo = SubactividadDetalleDistributivo.objects.filter(actividaddetalledistributivo__criterio=criterio, subactividaddocenteperiodo__criterio__status=True, subactividaddocenteperiodo__criterio=pk_subactividad, status=True).first()
                if temp := solicitud.migracionevidenciaactividad_set.filter(status=True).first():
                    evidencia = temp.evidencia
                else:
                    filtro = Q(criterio=criterio, desde=solicitud.fecha_inicio, hasta=solicitud.fecha_fin, status=True, generado=True) if not detalledistributivomacroact else Q(subactividad=subactividaddistributivo, criterio=criterio, desde=solicitud.fecha_inicio, hasta=solicitud.fecha_fin, status=True, generado=True)
                    evidencia = solicitud.proyecto.evidenciaactividaddetalledistributivo_set.filter(filtro).first()
                if not evidencia:
                    evidencia = EvidenciaActividadDetalleDistributivo(subactividad=subactividaddistributivo, proyectovinculacion=solicitud.proyecto, criterio=criterio, desde=solicitud.fecha_inicio, hasta=solicitud.fecha_fin, actividad=f'INFORMAR SOBRE LAS ACTIVIDADES REALIZADAS EN EL MES DE {nombremes(solicitud.fecha_fin.month).upper()}', generado=True)
                    evidencia.save(request)
                    migracion = MigracionEvidenciaActividad(evidencia=evidencia, informevinculacion=solicitud)
                    migracion.save(request)
                ultimoestado = evidencia.historialaprobacionevidenciaactividad_set.filter(status=True).order_by('-fecha_creacion').first()
                if ultimoestado and estadoaprobacion == 4 and not ultimoestado.estadoaprobacion == 2:
                    evidencia.usuarioaprobado = persona.usuario
                    evidencia.fechaaprobado = hoy
                    evidencia.archivofirmado = solicitud.archivo
                    historial = HistorialAprobacionEvidenciaActividad(evidencia=evidencia, observacion=u'Cumple con lo solicitado', estadoaprobacion=2, aprobacionpersona=persona, fechaaprobacion=hoy)
                    historial.save(request)
                else:
                    evidencia.archivo = solicitud.archivo
                evidencia.estadoaprobacion = estadoaprobacion
                historial = HistorialAprobacionEvidenciaActividad(evidencia=evidencia, observacion=f"{solicitud.detalle_aprobacion}", estadoaprobacion=estadoaprobacion, aprobacionpersona=persona if estadoaprobacion == 4 else None, fechaaprobacion=hoy if estadoaprobacion == 4 else None)
                historial.save(request)
                evidencia.save(request)
                if solicitud.aprobacion == 5:
                    mes = solicitud.fecha_fin.month
                    cuerpo = f"Se informa que {'la' if owner.es_mujer() else 'el'} docente {owner.__str__().title()} registró la evidencia del proyecto de vinculación denominado {solicitud.proyecto.nombre.__str__().title()} correspondiente al avance del mes de {nombremes(mes).lower()}."
                    notificacion2('Carga de informe mensual para proyecto de vinculación', cuerpo, lider, None, f'/proyectovinculaciondocente?action=configurarinforme&id={solicitud.proyecto.pk}', evidencia.pk, 1, 'sga', EvidenciaActividadDetalleDistributivo)
            else:
                criteriosubactividad, criteriodocencia = Criterio.objects.get(id=pk_subactividad), CriterioDocencia.objects.get(id=pk_criterio)
                return False, u'No se realizó la migración de la evidencia al módulo Mi cronograma'
        else:
            if temp := evidencia.migracionevidenciaactividad_set.filter(status=True).first():
                solicitud = temp.informevinculacion
            else:
                solicitud = ConfiguracionInformeVinculacion.objects.filter(proyecto=evidencia.proyectovinculacion, profesor=evidencia.criterio.distributivo.profesor, fecha_inicio=evidencia.desde, fecha_fin__month=evidencia.hasta.month, status=True).first()

            if solicitud:
                if evidencia.estadoaprobacion in (2, 4, 5):
                    solicitud.aprobacion = 3
                if evidencia.estadoaprobacion == 3:
                    solicitud.aprobacion = 4

                solicitud.archivo = evidencia.archivofirmado if evidencia.archivofirmado else evidencia.archivo
                solicitud.save(request)
        return True, ''
    except Exception as ex:
        return False, ex.__str__()