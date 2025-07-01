# -*- coding: latin-1 -*-
import sys
import io
import json
import random
import unicodedata
from datetime import datetime
from googletrans import Translator
import xlsxwriter
import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.db.models import Sum, Exists, OuterRef
from django.db.models.functions import Coalesce
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.template import Context
from django.template.loader import get_template
from xlwt import *
from inno.models import RequisitoIngresoUnidadIntegracionCurricular
from decorators import secure_module, last_access
from settings import ARCHIVO_TIPO_SYLLABUS, COSTO_EN_MALLA, VER_PLAN_ESTUDIO, VER_SILABO_MALLA
from sga.commonviews import adduserdata
from sga.forms import MallaForm, AsignaturaMallaForm, RequisitoMallaForm, ArchivoSyllabusMallaForm, \
    AsignaturaMallaPredecesoraForm, AsignaturaModuloForm, ProgramaAnaliticoMallaForm, \
    ProgramaAnaliticoAsignaturaMallaForm, ProgramaAnaliticoAsignaturaForm, ObjetivoProgramaAnaliticoAsignaturaForm, \
    MetodologiaProgramaAnaliticoAsignaturaForm, BibliografiaProgramaAnaliticoAsignaturaForm, \
    ResultadoAprendizajeRaiForm, ResultadoAprendizajeRacForm, \
    CamposOcupacionalesForm, CamposRotacionesForm, ProgramaAnaliticoAsignaturaArchivoForm, \
    AsignaturaMallaCoRequisitoForm, CamposItinerariosForm, SolicitudCompraLibroForm, \
    BibliografiaApaProgramaAnaliticoAsignaturaForm, ContenidoSubtema, ArchivoTemaPlanForm, AutorprogramaAnaliticoForm, \
    ProgramaAnaliticoAsignaturaPosgradoForm, ProgramaAnaliticoPosgradoAsignaturaArchivoForm, CambioAsignaturaMallaForm, \
    MallaLineaForm, MecanismoTitulacionPosgradoMallaForm, AsignaturaMallaHomologacionForm, \
    DocumentoRequeridoCarreraForm, \
    ItinerarioMallaEspecilidadForm, ModalidadForm, MallaLineaForm, MecanismoTitulacionPosgradoMallaForm, \
    AsignaturaMallaHomologacionForm, DocumentoRequeridoCarreraForm, ItinerarioMallaEspecilidadForm, \
    ModalidadForm, EditarNombreCarreraForm, CamposItinerariosVinculacionForm, AsignaturaMallaModalidadForm, \
    UnidadOrganizacionCurricularForm, IntegracionCurricularForm, ArchivoMallasForm, CabProcedimietoEvaForm, DetProcedimietoEvaForm
from sga.funciones import log, generar_nombre, puede_realizar_accion, variable_valor, MiPaginador, \
    puede_realizar_accion_afirmativo
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from bd.models import FuncionRequisitoIngresoUnidadIntegracionCurricular
from sga.models import Malla, NivelMalla, EjeFormativo, AsignaturaMalla, Asignatura, RequisitosMalla, Archivo, \
    AsignaturaMallaPredecesora, ModuloMalla, Materia, ProgramaAnaliticoMalla, ProgramaAnaliticoAsignaturaMalla, \
    ProgramaAnaliticoAsignatura, ObjetivoProgramaAnaliticoAsignatura, MetodologiaProgramaAnaliticoAsignatura, \
    BibliografiaProgramaAnaliticoAsignatura, RecordAcademico, HistoricoRecordAcademico, \
    ContenidoResultadoProgramaAnalitico, UnidadResultadoProgramaAnalitico, TemaUnidadResultadoProgramaAnalitico, \
    ResultadoAprendizajeRai, ResultadoAprendizajeRac, SubtemaUnidadResultadoProgramaAnalitico, Titulo, \
    AsignaturaMallaTituloAFin, CamposOcupacionalesMalla, RotacionesMalla, \
    AsignaturaMallaCoRequisito, ItinerariosMalla, SolicitudCompraLibro, NivelTitulacion, Coordinacion, \
    BibliografiaApaProgramaAnaliticoAsignatura, AutorprogramaAnalitico, Modalidad, Carrera, Inscripcion, \
    HorarioVirtual, ParticipantesHorarioVirtual, DiaSemana, TurnoVirtual, \
    LaboratorioVirtual, DetalleHorarioVirtual, Matricula, MecanismoTitulacionPosgrado, \
    MecanismoTitulacionPosgradoMalla, TemaTitulacionPosgradoMatricula, AsignaturaMallaHomologacion, \
    TIPO_DOCUMENTO_HOMOLOGACION, ItinerariosMallaDocumentosBase, ItinerarioMallaEspecilidad, \
    RequisitosHomologacionPracticas, ItinerariosVinculacionMalla, DetalleAsignaturaMallaModalidad, UnidadOrganizacionCurricular, HomologacionAsignatura, \
    RequisitoTitulacionMalla, TransversalAsignatura, CabProcedimientoEvaluacionPa, ProcedimientoEvaluacionProgramaAnalitico, AsignaturaMallaOrden, ResponsableCoordinacion
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.templatetags.sga_extras import encrypt
from inno.models import ActaResponsabilidad, MallaHorasSemanalesComponentes, ItinerarioAsignaturaMalla, AsignaturamallaContenidoMinimo, UnidadResultadoProgramaAnaliticoContenidoMinimo
from inno.forms import ActaResponsabilidadForm, ItinerarioAsignaturaMallaForm
from datetime import date

unicode =str

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['periodo']= periodo = request.session['periodo']
    miscarreras = persona.mis_carreras()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addrequisitoscarrera':
            try:
                with transaction.atomic():
                    form = DocumentoRequeridoCarreraForm(request.POST)
                    if form.is_valid():
                        pk = request.POST['id']
                        tipo = request.POST['tipo']
                        itinerario = ItinerariosMalla.objects.get(pk=int(pk))
                        for dc in form.cleaned_data['documento']:
                            filtro = ItinerariosMallaDocumentosBase(documento=dc, tipo=tipo, itinerario=itinerario)
                            filtro.save(request)
                            log(u'Adiciono Requisito Base Carrera Homologación: %s' % filtro, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'deletedocumentocarrera':
            try:
                with transaction.atomic():
                    instancia = ItinerariosMallaDocumentosBase.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Requisito Base Documento Homologación: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'editrequisito':
            try:
                f = RequisitoMallaForm(request.POST)
                requisito = RequisitosMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                if f.is_valid():
                    requisito.nombre = f.cleaned_data['nombre']
                    requisito.cantidad = f.cleaned_data['cantidad']
                    requisito.save(request)
                    requisito.requisitos.clear()
                    for dato in f.cleaned_data['requisitos']:
                        requisito.requisitos.add(dato)

                    log(u'Modifico requisitos malla: %s' % requisito, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editintegracioncurricular':
            try:
                f = IntegracionCurricularForm(request.POST)
                requisito = RequisitoIngresoUnidadIntegracionCurricular.objects.get(pk=int(encrypt(request.POST['id'])))
                eAsignaturaMalla = requisito.asignaturamalla
                if not f.is_valid():
                    raise NameError('Formulario incorrecto')
                if RequisitoIngresoUnidadIntegracionCurricular.objects.filter(status=True, asignaturamalla=eAsignaturaMalla, requisito=f.cleaned_data['funcion']).exclude(pk=requisito.pk).exists():
                    raise NameError(u"Requisito ya se encuentra adicionado.")
                requisito.requisito = f.cleaned_data['funcion']
                requisito.orden = f.cleaned_data['orden']
                requisito.activo = f.cleaned_data['activo']
                requisito.obligatorio = f.cleaned_data['obligatorio']
                requisito.enlineamatriculacion = f.cleaned_data['enlineamatriculacion']
                requisito.save(request)
                log(u'Modifico requisitos integracion curricular malla: %s' % requisito, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'editcampoocupacional':
            try:
                f = CamposOcupacionalesForm(request.POST)
                campoocupacional = CamposOcupacionalesMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                if f.is_valid():
                    campoocupacional.nombre = f.cleaned_data['nombre']
                    campoocupacional.save(request)
                    log(u'Modifico campo ocupacional: %s' % campoocupacional, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcamporotacion':
            try:
                f = CamposRotacionesForm(request.POST)
                camporotacion = RotacionesMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                if f.is_valid():
                    camporotacion.nombre = f.cleaned_data['nombre']
                    camporotacion.save(request)
                    log(u'Modifico campo rotacion: %s' % camporotacion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addhoraaprendizaje':
            try:
                asignaturamalla = AsignaturaMalla.objects.get(pk=request.POST['idcodigo'])
                asignaturamalla.horasaprendizajeingles = request.POST['idhoraaprendizaje']
                asignaturamalla.save(request)
                log(u'Modifico horaaprendizaje: %s' % asignaturamalla, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcampoitinerario':
            try:
                f = CamposItinerariosForm(request.POST)
                campoitinerario = ItinerariosMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                if f.is_valid():
                    totalitinerarios = ItinerariosMalla.objects.filter(status=True, malla=campoitinerario.malla).exclude(id=int(encrypt(request.POST['id']))).aggregate(total=Coalesce(Sum('horas_practicas'), 0))['total'] + f.cleaned_data['horas_practicas']
                    totalmalla = campoitinerario.malla.horas_practicas
                    if totalitinerarios > totalmalla:
                        raise NameError('Las horas ingresadas sobrepasan a las horas totales en la malla, horas en la malla {}'.format(totalmalla))
                    campoitinerario.nombre = f.cleaned_data['nombre']
                    campoitinerario.nivel = f.cleaned_data['nivel']
                    campoitinerario.horas_practicas = f.cleaned_data['horas_practicas']
                    campoitinerario.save(request)
                    log(u'Modifico campo itinerario: %s' % campoitinerario, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Formulario no valido')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. {}".format(ex)})

        elif action == 'addsyllabus':
            form = ArchivoSyllabusMallaForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("silabomalla_", newfile._name)
                    asignaturamalla = AsignaturaMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                    archivo = Archivo(nombre=form.cleaned_data['nombre'],
                                      fecha=form.cleaned_data['fecha'],
                                      archivo=newfile,
                                      asignaturamalla=asignaturamalla,
                                      tipo_id=ARCHIVO_TIPO_SYLLABUS)
                    archivo.save(request)
                    log(u'Adiciono silabo en malla: %s - %s' % (asignaturamalla, archivo.nombre), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editsyllabus':
            form = ArchivoSyllabusMallaForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    archivo = Archivo.objects.get(pk=int(encrypt(request.POST['id'])))
                    archivo.nombre = form.cleaned_data['nombre']
                    archivo.fecha = form.cleaned_data['fecha']
                    archivo.save(request)
                    log(u'Modifico silabo: %s - %s' % (archivo.asignaturamalla, archivo), request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delcampoocupacional':
            try:
                campoocupacional = CamposOcupacionalesMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                campoocupacional.status = False
                campoocupacional.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delcampoitinerario':
            try:
                campoitinerario = ItinerariosMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                campoitinerario.status = False
                campoitinerario.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delcampoitinerariovinculacion':
            try:
                campoitinerariovinculacion = ItinerariosVinculacionMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                campoitinerariovinculacion.status = False
                campoitinerariovinculacion.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delcamporotacion':
            try:
                camporotacion = RotacionesMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                camporotacion.status = False
                camporotacion.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addrequisito':
            try:
                f = RequisitoMallaForm(request.POST)
                malla = Malla.objects.get(pk=int(encrypt(request.POST['id'])))
                if f.is_valid():
                    requisitos = RequisitosMalla(malla=malla,
                                                 nombre=f.cleaned_data['nombre'],
                                                 cantidad=f.cleaned_data['cantidad'])
                    requisitos.save(request)
                    for dato in f.cleaned_data['requisitos']:
                        requisitos.requisitos.add(dato)
                    log(u'Adiciono requisito malla: %s' % requisitos, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addintegracioncurricular':
            try:
                f = IntegracionCurricularForm(request.POST)
                asignaturamalla = AsignaturaMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                if not f.is_valid():
                    raise NameError('Formulario incorrecto')
                if RequisitoIngresoUnidadIntegracionCurricular.objects.filter(status=True, asignaturamalla=asignaturamalla, requisito=f.cleaned_data['funcion']).exists():
                    raise NameError(u"Requisito ya se encuentra adicionado.")
                requisitos = RequisitoIngresoUnidadIntegracionCurricular(asignaturamalla=asignaturamalla,
                                                                         requisito=f.cleaned_data['funcion'],
                                                                         orden=f.cleaned_data['orden'],
                                                                         activo=f.cleaned_data['activo'],
                                                                         obligatorio=f.cleaned_data['obligatorio'],
                                                                         enlineamatriculacion=f.cleaned_data['enlineamatriculacion'])
                requisitos.save(request)
                log(u'Adiciono requisito integracion curricular malla: %s' % requisitos, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'adicionarbibliografia':
            try:
                f = BibliografiaProgramaAnaliticoAsignaturaForm(request.POST)
                if f.is_valid():
                    if BibliografiaProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura_id=int(encrypt(request.POST['id'])), librokohaprogramaanaliticoasignatura_id=f.cleaned_data['bibliografia']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra registrada."})
                    bibliografia = BibliografiaProgramaAnaliticoAsignatura(programaanaliticoasignatura_id=int(encrypt(request.POST['id'])),
                                                                           librokohaprogramaanaliticoasignatura_id=f.cleaned_data['bibliografia'])
                    bibliografia.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'adicionarbibliografiaposgrado':
            try:
                f = BibliografiaProgramaAnaliticoAsignaturaForm(request.POST)
                if f.is_valid():
                    if BibliografiaProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura_id=int(encrypt(request.POST['id'])), librokohaprogramaanaliticoasignatura_id=f.cleaned_data['bibliografia']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra registrada."})
                    bibliografia = BibliografiaProgramaAnaliticoAsignatura(programaanaliticoasignatura_id=int(encrypt(request.POST['id'])),
                                                                           librokohaprogramaanaliticoasignatura_id=f.cleaned_data['bibliografia'])
                    bibliografia.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'add':
            try:
                f = MallaForm(request.POST, request.FILES)
                newfile = None
                newfile_archivo_proyecto = None
                newfile_proyecto_rediseñado = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if newfile.size > 153600000:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 150 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("archivo_malla_", newfile._name)

                if 'archivo_proyecto' in request.FILES:
                    newfile_archivo_proyecto = request.FILES['archivo_proyecto']
                    if newfile_archivo_proyecto:
                        newfilesd = newfile_archivo_proyecto._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if newfile_archivo_proyecto.size > 153600000:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 150 Mb."})
                        if newfile_archivo_proyecto:
                            newfile_archivo_proyecto._name = generar_nombre("archivo_proyecto_malla_", newfile_archivo_proyecto._name)

                if 'archivo_proyectorediseñado' in request.FILES:
                    newfile_proyecto_rediseñado = request.FILES['archivo_proyectorediseñado']
                    if newfile_proyecto_rediseñado:
                        newfilesd = newfile_proyecto_rediseñado._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if newfile_proyecto_rediseñado.size > 153600000:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 150 Mb."})
                        if newfile_proyecto_rediseñado:
                            newfile_proyecto_rediseñado._name = generar_nombre("archivo_malla_", newfile_proyecto_rediseñado._name)

                if not f.is_valid():
                    # [(k, v[0]) for k, v in f.errors.items()]
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if Malla.objects.filter(carrera=f.cleaned_data['carrera'], inicio=f.cleaned_data['inicio'], modalidad=f.cleaned_data['modalidad']).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existe un registro con la misma carrera, inicio, y modalidad."})
                malla = Malla(carrera=f.cleaned_data['carrera'],
                              modalidad=f.cleaned_data['modalidad'],
                              inicio=f.cleaned_data['inicio'],
                              fin=f.cleaned_data['fin'],
                              optativas=f.cleaned_data['optativas'],
                              vigente=f.cleaned_data['vigente'],
                              nivelsuficiencia=f.cleaned_data['nivelsuficiencia'],
                              libre_opcion=f.cleaned_data['libre_opcion'],
                              materias_completar=f.cleaned_data['materias_completar'],
                              creditos_completar=f.cleaned_data['creditos_completar'],
                              porciento_nivel=f.cleaned_data['porciento_nivel'],
                              niveles_regulares=f.cleaned_data['niveles_regulares'],
                              creditos_vinculacion=f.cleaned_data['creditos_vinculacion'],
                              horas_vinculacion=f.cleaned_data['horas_vinculacion'],
                              creditos_practicas=f.cleaned_data['creditos_practicas'],
                              horas_practicas=f.cleaned_data['horas_practicas'],
                              creditos_titulacion=f.cleaned_data['creditos_titulacion'],
                              creditos_computacion=f.cleaned_data['creditos_computacion'],
                              perfilegreso=f.cleaned_data['perfilegreso'],
                              perfilprofesional=f.cleaned_data['perfilprofesional'],
                              resolucion = f.cleaned_data['resolucion'],
                              misioncarrera=f.cleaned_data['misioncarrera'],
                              objetivocarrera=f.cleaned_data['objetivocarrera'],
                              semanas=f.cleaned_data['semanas'],
                              tituloobtenidohombre=f.cleaned_data['tituloobtenidohombre'],
                              tituloobtenidomujer=f.cleaned_data['tituloobtenidomujer'],
                              codigo=f.cleaned_data['codigo'],
                              archivo = newfile,
                              archivo_proyecto = newfile_archivo_proyecto,
                              archivo_proyectorediseñado = newfile_proyecto_rediseñado,
                              maxhoras_contactodocente_matricula = f.cleaned_data['maxhoras_contactodocente_matricula'],
                              maxhoras_semanal_matricula = f.cleaned_data['maxhoras_semanal_matricula']
                              )
                malla.save(request)
                if puede_realizar_accion_afirmativo(request, 'sga.puede_modificar_campo_especifico_malla'):
                    malla.campo_especifico = f.cleaned_data['campo_especifico']
                    malla.save(request)
                    # for mallaexistente in Malla.objects.filter(carrera=malla.carrera, modalidad=malla.modalidad):
                #     mallaexistente.vigente = False
                #     mallaexistente.save(request)
                # mallavigente = Malla.objects.filter(carrera=malla.carrera, modalidad=malla.modalidad).order_by('-inicio')[0]
                # mallavigente.vigente = True
                # mallavigente.save(request)
                log(u'Adiciono malla: %s' % malla, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'addcampoocupacional':
            try:
                f = CamposOcupacionalesForm(request.POST)
                if f.is_valid():
                    campoocupacional = CamposOcupacionalesMalla(malla_id=int(encrypt(request.POST['id'])),
                                                                nombre=f.cleaned_data['nombre'])
                    campoocupacional.save(request)
                    log(u'Adiciono campo ocupacional: %s' % campoocupacional, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addcamporotacion':
            try:
                f = CamposRotacionesForm(request.POST)
                if f.is_valid():
                    camporotacion = RotacionesMalla(malla_id=int(encrypt(request.POST['id'])),
                                                    nombre=f.cleaned_data['nombre'])
                    camporotacion.save(request)
                    log(u'Adiciono campo rotacion: %s' % camporotacion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasignaturaitinerario':
            try:
                with transaction.atomic():
                    f = ItinerarioAsignaturaMallaForm(request.POST)
                    iti = ItinerariosMalla.objects.get(pk=int(request.POST['idp']))
                    f.iniciar(iti)
                    if f.is_valid():
                        registro = ItinerarioAsignaturaMalla(itinerariomalla=iti, asignaturamalla=f.cleaned_data['asignaturamalla'])
                        registro.save(request)
                        log(u'Adicionó itinerario asignatura malla: %s' % (registro), request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'deleteasignaturaitinerario':
            try:
                with transaction.atomic():
                    registro = ItinerarioAsignaturaMalla.objects.get(pk=int(request.POST['id']))
                    log(u'Eliminó registro itinerario asignatura malla: %s' % registro, request, "delete")
                    registro.delete()
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addcampoitinerario':
            try:
                f = CamposItinerariosForm(request.POST)
                if f.is_valid():
                    totalitinerarios = ItinerariosMalla.objects.filter(status=True, malla_id=int(encrypt(request.POST['id']))).aggregate(total=Coalesce(Sum('horas_practicas'),0))['total'] + f.cleaned_data['horas_practicas']
                    totalmalla = Malla.objects.get(id=int(encrypt(request.POST['id']))).horas_practicas
                    if totalitinerarios > totalmalla:
                        raise NameError('Las horas ingresadas sobrepasan a las horas totales en la malla, horas en la malla {}'.format(totalmalla))
                    campoitinerario = ItinerariosMalla(malla_id=int(encrypt(request.POST['id'])),
                                                       nombre=f.cleaned_data['nombre'],
                                                       nivel=f.cleaned_data['nivel'],
                                                       horas_practicas=f.cleaned_data['horas_practicas'])
                    campoitinerario.save(request)
                    log(u'Adiciono campo itinerario: %s' % campoitinerario, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Formulario no valido')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos. {}".format(ex)})

        elif action == 'addcampoitinerariovinculacion':
            try:
                f = CamposItinerariosVinculacionForm(request.POST)
                if f.is_valid():
                    campoitinerariovinculacion = ItinerariosVinculacionMalla(malla_id=int(encrypt(request.POST['id'])),
                                                                             nombre=f.cleaned_data['nombre'],
                                                                             nivel=f.cleaned_data['nivel'],
                                                                             horas_vinculacion=f.cleaned_data['horas_vinculacion'])
                    campoitinerariovinculacion.save(request)
                    log(u'Adicionó campo itinerario: %s' % campoitinerariovinculacion, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addcontenidosminimos':
            try:
                if 'id' in request.POST and 'contenido_minimo' in request.POST:
                    id = int(encrypt(request.POST['id']))
                    contenido_minimo = request.POST['contenido_minimo']
                    if not contenido_minimo:
                        raise NameError('Debe ingresar un contenido')
                    if AsignaturamallaContenidoMinimo.objects.filter(
                            status=True,
                            asignaturamalla_id=id,
                            descripcioncontenido__iexact=contenido_minimo.strip().lower()
                    ).exists():
                        raise NameError('El registro ya existe')
                    contenidominimo = AsignaturamallaContenidoMinimo(asignaturamalla_id=id,
                                                                             descripcioncontenido=contenido_minimo)
                    contenidominimo.save(request)
                    log(u'Adicionó campo itinerario: %s' % contenidominimo, request, "add")
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con exito'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'editcontenidosminimos':
            try:
                if 'id' in request.POST and 'contenido_minimo' in request.POST and 'idp' in request.POST:
                    id = int(request.POST['id'])
                    contenido_minimo = request.POST['contenido_minimo']
                    idp = int(request.POST['idp'])
                    # Verificar si ya existe el contenido con la misma asignatura
                    if AsignaturamallaContenidoMinimo.objects.filter(pk=id, status=True, asignaturamalla_id=idp, descripcioncontenido__iexact=contenido_minimo.strip().lower()).exists():
                        return JsonResponse({'result': False, 'mensaje': 'No se aplicó ningún cambio'})
                    if AsignaturamallaContenidoMinimo.objects.filter(status=True, asignaturamalla_id=idp, descripcioncontenido__iexact=contenido_minimo.strip().lower()).exists():
                        raise NameError('El registro ya existe')
                    # Actualizar el contenido
                    contenidominimo = AsignaturamallaContenidoMinimo.objects.get(pk=id, status=True)
                    contenidominimo.descripcioncontenido=contenido_minimo
                    contenidominimo.save(request)
                    log(u'Actualizo campo itinerario: %s' % contenidominimo, request, "edit")
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
                else:
                    raise NameError('Error en el formulario')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'delcontenido':
            try:
                contenidominimo = AsignaturamallaContenidoMinimo.objects.get(pk=int(encrypt(request.POST['id'])), status = True)
                unidades_usadas = contenidominimo.unidadresultadoprogramaanaliticocontenidominimo_set.filter(status=True)
                if unidades_usadas.exists():
                    unidades_list = [
                        f"<b>Unidad {unidad.unidadresultadoprogramaanalitico.orden}:</b> {unidad.unidadresultadoprogramaanalitico.descripcion}"
                        for unidad in unidades_usadas
                    ]
                    unidades_str = '<br>- '.join(unidades_list)
                    raise NameError(
                        f"No se puede eliminar.<br>El registro está configurado en el plan analítico:<br>- {unidades_str}")
                log(u'Eliminó el contenido minimo: %s de la asignatura: %s' % (contenidominimo, contenidominimo.asignaturamalla.asignatura.nombre), request, "del")
                contenidominimo.status = False
                contenidominimo.save(request)
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "{}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'editcampoitinerariovinculacion':
            try:
                with transaction.atomic():
                    campoitinerariovinculacion = ItinerariosVinculacionMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = CamposItinerariosVinculacionForm(request.POST)
                    if f.is_valid():
                        campoitinerariovinculacion.nombre = f.cleaned_data['nombre'].upper()
                        campoitinerariovinculacion.nivel = f.cleaned_data['nivel']
                        campoitinerariovinculacion.horas_vinculacion = f.cleaned_data['horas_vinculacion']
                        campoitinerariovinculacion.save(request)
                        log(u'Campos de itinerario de vinculación modificados: %s' % campoitinerariovinculacion, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Error al guardar los datos. {}".format(ex)}, safe=False)

        elif action == 'editmalla':
            try:
                f = MallaForm(request.POST, request.FILES)
                newfile = None
                newfile_archivo_proyecto = None
                newfile_proyecto_rediseñado = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if newfile.size > 153600000:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 150 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("archivo_malla_", newfile._name)
                if 'archivo_proyecto' in request.FILES:
                    newfile_archivo_proyecto = request.FILES['archivo_proyecto']
                    if newfile_archivo_proyecto:
                        newfilesd = newfile_archivo_proyecto._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if newfile_archivo_proyecto.size > 153600000:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 150 Mb."})
                        if newfile_archivo_proyecto:
                            newfile_archivo_proyecto._name = generar_nombre("archivo_proyecto_malla_", newfile_archivo_proyecto._name)

                if 'archivo_proyectorediseñado' in request.FILES:
                    newfile_proyecto_rediseñado = request.FILES['archivo_proyectorediseñado']
                    if newfile_proyecto_rediseñado:
                        newfilesd = newfile_proyecto_rediseñado._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if newfile_proyecto_rediseñado.size > 153600000:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 150 Mb."})
                        if newfile_proyecto_rediseñado:
                            newfile_proyecto_rediseñado._name = generar_nombre("archivo_malla_", newfile_proyecto_rediseñado._name)

                malla = Malla.objects.get(pk=int(encrypt(request.POST['id'])))
                if not f.is_valid():
                    # [(k, v[0]) for k, v in f.errors.items()]
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if Malla.objects.filter(carrera=f.cleaned_data['carrera'], inicio=f.cleaned_data['inicio'], modalidad=f.cleaned_data['modalidad']).exclude(pk=malla.id).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existe un registro con la misma carrera, inicio, y modalidad."})
                if not malla.cerrado:
                    malla.codigo = f.cleaned_data['codigo']
                    malla.modalidad = f.cleaned_data['modalidad']
                    malla.vigente = f.cleaned_data['vigente']
                    malla.inicio = f.cleaned_data['inicio']
                    malla.fin = f.cleaned_data['fin']
                    malla.creditoporhora = f.cleaned_data['creditoporhora']
                    malla.libre_opcion = f.cleaned_data['libre_opcion']
                    malla.optativas = f.cleaned_data['optativas']
                    malla.creditos_completar = f.cleaned_data['creditos_completar']
                    malla.materias_completar = f.cleaned_data['materias_completar']
                    malla.niveles_regulares = f.cleaned_data['niveles_regulares']
                    malla.porciento_nivel = f.cleaned_data['porciento_nivel']
                    malla.creditos_vinculacion = f.cleaned_data['creditos_vinculacion']
                    malla.horas_vinculacion = f.cleaned_data['horas_vinculacion']
                    malla.creditos_practicas = f.cleaned_data['creditos_practicas']
                    malla.horas_practicas = f.cleaned_data['horas_practicas']
                    malla.creditos_titulacion = f.cleaned_data['creditos_titulacion']
                    malla.horas_titulacion = f.cleaned_data['horas_titulacion']
                    malla.creditos_computacion = f.cleaned_data['creditos_computacion']
                    malla.semanas = f.cleaned_data['semanas']
                    malla.maxhoras_contactodocente_matricula = f.cleaned_data['maxhoras_contactodocente_matricula']
                    malla.maxhoras_semanal_matricula = f.cleaned_data['maxhoras_semanal_matricula']
                malla.nivelsuficiencia = f.cleaned_data['nivelsuficiencia']
                malla.perfilegreso = f.cleaned_data['perfilegreso']
                malla.perfilprofesional = f.cleaned_data['perfilprofesional']
                malla.misioncarrera = f.cleaned_data['misioncarrera']
                malla.objetivocarrera = f.cleaned_data['objetivocarrera']
                malla.resolucion = f.cleaned_data['resolucion']
                malla.tituloobtenidohombre = f.cleaned_data['tituloobtenidohombre']
                malla.tituloobtenidomujer = f.cleaned_data['tituloobtenidomujer']
                if puede_realizar_accion_afirmativo(request, 'sga.puede_modificar_campo_especifico_malla'):
                    malla.campo_especifico = f.cleaned_data['campo_especifico']

                if newfile:
                    malla.archivo = newfile
                if newfile_archivo_proyecto:
                    malla.archivo_proyecto = newfile_archivo_proyecto
                if newfile_proyecto_rediseñado:
                    malla.archivo_proyectorediseñado = newfile_proyecto_rediseñado
                malla.save(request)
                # for mallaexistente in Malla.objects.filter(carrera=malla.carrera, modalidad=malla.modalidad):
                #     mallaexistente.vigente = False
                #     mallaexistente.save(request)
                # mallavigente = Malla.objects.filter(carrera=malla.carrera, modalidad=malla.modalidad).order_by('-inicio')[0]
                # mallavigente.vigente = True
                # mallavigente.save(request)
                log(u'Modifico malla: %s' % malla, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'editlineainvestigacion':
            try:
                f = MallaLineaForm(request.POST)
                malla = Malla.objects.get(pk=int(encrypt(request.POST['id'])))
                if f.is_valid():
                    malla.lineainvestigacion = f.cleaned_data['lineainvestigacion']
                    malla.save(request)
                    log(u'Modifico malla linea: %s' % malla, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editarchivosilabotema':
            try:
                form = ArchivoTemaPlanForm(request.POST, request.FILES)
                arch = request.FILES['archivo']
                extencion = arch._name.split('.')
                exte = extencion[1]
                if arch.size > 10485760:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                if not exte.lower() == 'pdf':
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if form.is_valid():
                    tema = TemaUnidadResultadoProgramaAnalitico.objects.get(pk=int(encrypt(request.POST['id'])))
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivotemaplansilabo_", newfile._name)
                        tema.archivo = newfile
                        tema.save(request)
                    log(u'Ingreso archivo tema: %s' % tema, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, Al guadar los datos"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addprogramaanaliticomalla':
            try:
                form = ProgramaAnaliticoMallaForm(request.POST, request.FILES)
                if form.is_valid():
                    newfileword = request.FILES['archivoword']
                    newfileword._name = generar_nombre("programaanaliticomalla_", newfileword._name)
                    newfilepdf = request.FILES['archivopdf']
                    newfilepdf._name = generar_nombre("programaanaliticomalla_", newfilepdf._name)
                    malla = Malla.objects.get(pk=request.POST['id'])
                    ProgramaAnaliticoMalla.objects.filter(malla=malla).update(aprobado=False)
                    programaanaliticomalla = ProgramaAnaliticoMalla(descripcion=form.cleaned_data['descripcion'],
                                                                    malla=malla,
                                                                    fecha=form.cleaned_data['fecha'],
                                                                    archivoword=newfileword,
                                                                    archivopdf=newfilepdf,
                                                                    aprobado=True)
                    programaanaliticomalla.save(request)
                    log(u'Adiciono Plan de Estudio Malla: %s - %s' % (malla, programaanaliticomalla.fecha), request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editprogramaanaliticomalla':
            try:
                form = ProgramaAnaliticoMallaForm(request.POST, request.FILES)
                if form.is_valid():

                    # nombres de los archivos
                    newfileword = request.FILES['archivoword']
                    newfileword._name = generar_nombre("programaanaliticomalla_", newfileword._name)
                    newfilepdf = request.FILES['archivopdf']
                    newfilepdf._name = generar_nombre("programaanaliticomalla_", newfilepdf._name)

                    programaanaliticomalla = ProgramaAnaliticoMalla.objects.get(pk=request.POST['id'])
                    programaanaliticomalla.archivoword = newfileword
                    programaanaliticomalla.archivopdf = newfilepdf
                    programaanaliticomalla.save(request)
                    log(u'Modifico Plan de Estudio Malla : %s ' % programaanaliticomalla, request, "edit")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al Modificar los datos."})

        elif action == 'editprogramanaliticomet':
            try:
                metodologia = MetodologiaProgramaAnaliticoAsignatura.objects.get(pk=request.POST['codimetodologia'])
                metodologia.descripcion = request.POST['descripcion']
                metodologia.save(request)
                log(u'Modifico metodología del programa analítico : %s ' % metodologia, request, "edit")
                return JsonResponse({"result": "ok", "descripcion": metodologia.descripcion})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editprogramanaliticoobj':
            try:
                objetivo = ObjetivoProgramaAnaliticoAsignatura.objects.get(pk=request.POST['codiobjetivo'])
                objetivo.descripcion = request.POST['descripcion']
                objetivo.save(request)
                log(u'Modifico objetivo del programa analítico : %s ' % objetivo, request, "edit")
                return JsonResponse({"result": "ok", "descripcion": objetivo.descripcion})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editprogramanaliticorac':
            try:
                rac = ResultadoAprendizajeRac.objects.get(pk=request.POST['codirac'])
                rac.descripcion = request.POST['descripcion']
                rac.save(request)
                log(u'Modifico resultado de aprendizaje rac: %s ' % rac, request, "edit")
                return JsonResponse({"result": "ok", "descripcion": rac.descripcion})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editprogramanaliticorai':
            try:
                rai = ResultadoAprendizajeRai.objects.get(pk=request.POST['codirai'])
                rai.descripcion = request.POST['descripcion']
                rai.save(request)
                log(u'Modifico objetivo del de aprendizaje rai: %s ' % rai, request, "edit")
                return JsonResponse({"result": "ok", "descripcion": rai.descripcion})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addarchivoprogramanalitico':
            try:
                asignaturamallaid = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.POST['id'])))
                f = ProgramaAnaliticoAsignaturaArchivoForm(request.POST, request.FILES)
                proanalitico = ProgramaAnaliticoAsignatura(asignaturamalla=asignaturamallaid,motivo=request.POST['motivo'])
                if 'archivoconsejo' in request.FILES:
                    newfile = request.FILES['archivoconsejo']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_consejo_", newfile._name)
                                proanalitico.archivoconsejo = newfile
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No existe archivo"})

                if 'archivocomision' in request.FILES:
                    newfile = request.FILES['archivocomision']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_consejo_", newfile._name)
                                proanalitico.archivocomision = newfile
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No existe archivo"})

                if 'archivopafirma' in request.FILES:
                    newfile = request.FILES['archivopafirma']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_consejo_", newfile._name)
                                proanalitico.archivopafirma = newfile
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No existe archivo"})

                if 'actaempresa' in request.FILES:
                    newfile = request.FILES['actaempresa']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_actaempresa_", newfile._name)
                                proanalitico.actaempresa = newfile
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if 'actagraduado' in request.FILES:
                    newfile = request.FILES['actagraduado']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_actagraduado_", newfile._name)
                                proanalitico.actagraduado = newfile
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if 'actadocente' in request.FILES:
                    newfile = request.FILES['actadocente']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_actadocente_", newfile._name)
                                proanalitico.actadocente = newfile
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if 'informebenchmarking' in request.FILES:
                    newfile = request.FILES['informebenchmarking']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_informebenchmarking_", newfile._name)
                                proanalitico.informebenchmarking = newfile
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if 'informepractica' in request.FILES:
                    newfile = request.FILES['informepractica']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_informepractica_", newfile._name)
                                proanalitico.informepractica = newfile
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if f.is_valid():
                    proanalitico.save(request)
                    log(u'Adiciono programa analitico vacio con archivos de consejo, comision, firma de programaanalitico y motivo: Asig. %s -- Archivo: %s - %s - %s' % (asignaturamallaid, proanalitico.archivocomision, proanalitico.archivoconsejo, proanalitico.archivopafirma), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editarchivoprogramanalitico':
            try:
                f = ProgramaAnaliticoAsignaturaArchivoForm(request.POST, request.FILES)
                proanalitico = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['id'])))
                editoarchivo_1 = False
                editoarchivo_2 = False
                editoarchivo_3 = False
                editoarchivo_4 = False
                editoarchivo_5 = False
                editoarchivo_6 = False
                editoarchivo_7 = False
                editoarchivo_8 = False
                if 'archivoconsejo' in request.FILES:
                    newfile = request.FILES['archivoconsejo']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_consejo_", newfile._name)
                                proanalitico.archivoconsejo = newfile
                                editoarchivo_1 = True
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})

                if 'archivocomision' in request.FILES:
                    newfile = request.FILES['archivocomision']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_consejo_", newfile._name)
                                proanalitico.archivocomision = newfile
                                editoarchivo_2 = True
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})

                if 'archivopafirma' in request.FILES:
                    newfile = request.FILES['archivopafirma']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_consejo_", newfile._name)
                                proanalitico.archivopafirma = newfile
                                editoarchivo_3 = True
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})

                if 'actaempresa' in request.FILES:
                    newfile = request.FILES['actaempresa']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_actaempresa_", newfile._name)
                                proanalitico.actaempresa = newfile
                                editoarchivo_4 = True
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if 'actagraduado' in request.FILES:
                    newfile = request.FILES['actagraduado']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_actagraduado_", newfile._name)
                                proanalitico.actagraduado = newfile
                                editoarchivo_5 = True
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if 'actadocente' in request.FILES:
                    newfile = request.FILES['actadocente']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_actadocente_", newfile._name)
                                proanalitico.actadocente = newfile
                                editoarchivo_6 = True
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if 'informebenchmarking' in request.FILES:
                    newfile = request.FILES['informebenchmarking']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_informebenchmarking_", newfile._name)
                                proanalitico.informebenchmarking = newfile
                                editoarchivo_7 = True
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if 'informepractica' in request.FILES:
                    newfile = request.FILES['informepractica']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_informepractica_", newfile._name)
                                proanalitico.informepractica = newfile
                                editoarchivo_8 = True
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                proanalitico.motivo = request.POST['motivo'].upper()
                proanalitico.save(request)
                log(u'Edito programa analitico vacio con archivos de consejo, comision, firma de programaanalitico y motivo: Asig. %s -- Archivo: %s - %s - %s - %s - %s - %s - %s - %s' % (proanalitico.asignaturamalla, proanalitico.archivocomision if editoarchivo_2 else "", proanalitico.archivoconsejo if editoarchivo_1 else "", proanalitico.archivopafirma if editoarchivo_3 else "", proanalitico.actaempresa if editoarchivo_4 else "", proanalitico.actagraduado if editoarchivo_5 else "", proanalitico.actadocente if editoarchivo_6 else "", proanalitico.informebenchmarking if editoarchivo_7 else "", proanalitico.informepractica if editoarchivo_8 else ""), request, "edit")
                return JsonResponse({"result": "ok"})
                # else:
                #     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editarchivoprogramanaliticoposgrado':
            try:
                f = ProgramaAnaliticoAsignaturaArchivoForm(request.POST, request.FILES)
                proanalitico = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['id'])))
                editoarchivo_1 = False
                editoarchivo_2 = False
                editoarchivo_3 = False
                editoarchivo_4 = False
                editoarchivo_5 = False
                editoarchivo_6 = False
                editoarchivo_7 = False
                editoarchivo_8 = False

                # if 'archivocomision' in request.FILES:
                #     newfile = request.FILES['archivocomision']
                #     if newfile:
                #         if newfile.size > 6291456:
                #             return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                #         else:
                #             newfilesd = newfile._name
                #             ext = newfilesd[newfilesd.rfind("."):]
                #             if ext == '.pdf':
                #                 newfile._name = generar_nombre("Archivo_consejo_", newfile._name)
                #                 proanalitico.archivocomision = newfile
                #                 editoarchivo_2 = True
                #             else:
                #                 return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})

                if 'archivopafirma' in request.FILES:
                    newfile = request.FILES['archivopafirma']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_consejo_", newfile._name)
                                proanalitico.archivopafirma = newfile
                                editoarchivo_3 = True
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})

                if 'informepractica' in request.FILES:
                    newfile = request.FILES['informepractica']
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("Archivo_informepractica_", newfile._name)
                                proanalitico.informepractica = newfile
                                editoarchivo_8 = True
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                proanalitico.motivo = request.POST['motivo'].upper()
                proanalitico.save(request)
                log(u'Edito programa analitico posgrado vacio con archivos de consejo, comision, firma de programaanalitico y motivo: Asig. %s -- Archivo: %s - %s - %s - %s - %s - %s - %s - %s' % (proanalitico.asignaturamalla, proanalitico.archivocomision if editoarchivo_2 else "", proanalitico.archivoconsejo if editoarchivo_1 else "", proanalitico.archivopafirma if editoarchivo_3 else "", proanalitico.actaempresa if editoarchivo_4 else "", proanalitico.actagraduado if editoarchivo_5 else "", proanalitico.actadocente if editoarchivo_6 else "", proanalitico.informebenchmarking if editoarchivo_7 else "", proanalitico.informepractica if editoarchivo_8 else ""), request, "edit")
                return JsonResponse({"result": "ok"})
                # else:
                #     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addprogramanalitico':
            try:
                if int(request.POST['integranteuno']) == 0 and int(request.POST['integrantedos']) == 0 and int(request.POST['integrantetres']) == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"No ha registrado quien elaboro el programa analítico."})
                listarai = ''
                listarac = ''
                listaobjetivos = ''
                listaometodologia = ''
                listabibliografia = ''
                asignaturamallaid = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.POST['id'])))
                f = ProgramaAnaliticoAsignaturaForm(request.POST)
                if f.is_valid():
                    if 'lista_items4' in request.POST:
                        listarai = json.loads(request.POST['lista_items4'])
                    if 'lista_items5' in request.POST:
                        listarac = json.loads(request.POST['lista_items5'])
                    if 'lista_items1' in request.POST:
                        listaobjetivos = json.loads(request.POST['lista_items1'])
                    if 'lista_items2' in request.POST:
                        listaometodologia = json.loads(request.POST['lista_items2'])
                    if 'lista_items3' in request.POST:
                        listabibliografia = json.loads(request.POST['lista_items3'])
                    if f.cleaned_data['integranteuno'] == 0:
                        uno = None
                    else:
                        uno = f.cleaned_data['integranteuno']
                    if f.cleaned_data['integrantedos'] == 0:
                        dos= None
                    else:
                        dos = f.cleaned_data['integrantedos']
                    if f.cleaned_data['integrantetres'] == 0:
                        tres = None
                    else:
                        tres = f.cleaned_data['integrantetres']
                    proanalitico = ProgramaAnaliticoAsignatura(asignaturamalla=asignaturamallaid,
                                                               descripcion=f.cleaned_data['descripcion'],
                                                               compromisos=f.cleaned_data['compromisos'],
                                                               caracterinvestigacion=f.cleaned_data['caracterinvestigacion'],
                                                               integranteuno_id=uno,
                                                               integrantedos_id=dos,
                                                               integrantetres_id=tres)
                    proanalitico.save(request)
                    if listarai:
                        for lisrai in listarai:
                            ingresorai = ResultadoAprendizajeRai(programaanaliticoasignatura_id=proanalitico.id,
                                                                 descripcion=lisrai['resultadorai'])
                            ingresorai.save(request)
                    if listarac:
                        for lisrac in listarac:
                            ingresorac = ResultadoAprendizajeRac(programaanaliticoasignatura_id=proanalitico.id,
                                                                 descripcion=lisrac['resultadorac'])
                            ingresorac.save(request)
                    if listaobjetivos:
                        for lisobj in listaobjetivos:
                            objetivoanalitico = ObjetivoProgramaAnaliticoAsignatura(programaanaliticoasignatura_id=proanalitico.id,
                                                                                    descripcion=lisobj['objetivos'])
                            objetivoanalitico.save(request)
                    if listaometodologia:
                        for lismet in listaometodologia:
                            metodologiaanalitico = MetodologiaProgramaAnaliticoAsignatura(programaanaliticoasignatura_id=proanalitico.id,
                                                                                          descripcion=lismet['metodologia'])
                            metodologiaanalitico.save(request)
                    # if listabibliografia:
                    #     for lislib in listabibliografia:
                    #         bibliografiaanalitico = BibliografiaProgramaAnaliticoAsignatura(programaanaliticoasignatura_id=proanalitico.id,
                    #                                                                         descripcion=lislib['bibliografia'])
                    #         bibliografiaanalitico.save(request)

                    log(u'Adiciono programa analitico: %s %s' % (proanalitico.asignaturamalla.asignatura.nombre,proanalitico), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addprogramanaliticoposgrado':
            try:
                if int(request.POST['integranteuno']) == 0 and int(request.POST['integrantedos']) == 0 and int(request.POST['integrantetres']) == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"No ha registrado quien elaboro el programa analítico."})
                listarai = ''
                listarac = ''
                asignaturamallaid = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.POST['id'])))
                f = ProgramaAnaliticoAsignaturaForm(request.POST)
                if f.is_valid():
                    if 'lista_items4' in request.POST:
                        listarai = json.loads(request.POST['lista_items4'])
                    if 'lista_items5' in request.POST:
                        listarac = json.loads(request.POST['lista_items5'])
                    if f.cleaned_data['integranteuno'] == 0:
                        uno = None
                    else:
                        uno = f.cleaned_data['integranteuno']
                    if f.cleaned_data['integrantedos'] == 0:
                        dos= None
                    else:
                        dos = f.cleaned_data['integrantedos']
                    tres = None
                    proanalitico = ProgramaAnaliticoAsignatura(asignaturamalla=asignaturamallaid,
                                                               descripcion=f.cleaned_data['descripcion'],
                                                               # compromisos=f.cleaned_data['compromisos'],
                                                               # caracterinvestigacion=f.cleaned_data['caracterinvestigacion'],
                                                               integranteuno_id=uno,
                                                               integrantedos_id=dos,
                                                               integrantetres_id=tres)
                    proanalitico.save(request)
                    if listarai:
                        for lisrai in listarai:
                            ingresorai = ResultadoAprendizajeRai(programaanaliticoasignatura_id=proanalitico.id,
                                                                 descripcion=lisrai['resultadorai'])
                            ingresorai.save(request)
                    if listarac:
                        for lisrac in listarac:
                            ingresorac = ResultadoAprendizajeRac(programaanaliticoasignatura_id=proanalitico.id,
                                                                 descripcion=lisrac['resultadorac'])
                            ingresorac.save(request)

                    log(u'Adiciono programa analitico: %s %s' % (proanalitico.asignaturamalla.asignatura.nombre,proanalitico), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editprogramanalitico':
            if int(request.POST['integranteuno']) == 0 and int(request.POST['integrantedos']) == 0 and int(request.POST['integrantetres']) == 0:
                return JsonResponse({"result": "bad", "mensaje": u"No ha registrado quien elaboro el programa analítico."})
            f = ProgramaAnaliticoAsignaturaForm(request.POST)
            if f.is_valid():
                try:
                    programa = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['id'])))
                    programa.descripcion = f.cleaned_data['descripcion']
                    programa.compromisos = f.cleaned_data['compromisos']
                    programa.caracterinvestigacion = f.cleaned_data['caracterinvestigacion']
                    if f.cleaned_data['integranteuno'] == 0:
                        programa.integranteuno_id = None
                    else:
                        programa.integranteuno_id = f.cleaned_data['integranteuno']
                    if f.cleaned_data['integrantedos'] == 0:
                        programa.integrantedos_id = None
                    else:
                        programa.integrantedos_id = f.cleaned_data['integrantedos']
                    if f.cleaned_data['integrantetres'] == 0:
                        programa.integrantetres_id = None
                    else:
                        programa.integrantetres_id = f.cleaned_data['integrantetres']
                    programa.save(request)
                    log(u'Editó programa analitico: %s %s' % (programa.asignaturamalla.asignatura.nombre,programa), request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            else:
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editprogramanaliticoposgrado':
            if int(request.POST['integranteuno']) == 0 and int(request.POST['integrantedos']) == 0:
                return JsonResponse({"result": "bad", "mensaje": u"No ha registrado quien elaboro el programa analítico."})
            f = ProgramaAnaliticoAsignaturaForm(request.POST)
            if f.is_valid():
                try:
                    programa = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['id'])))
                    programa.descripcion = f.cleaned_data['descripcion']
                    programa.caracterinvestigacion = f.cleaned_data['caracterinvestigacion']
                    if f.cleaned_data['integranteuno'] == 0:
                        programa.integranteuno_id = None
                    else:
                        programa.integranteuno_id = f.cleaned_data['integranteuno']
                    if f.cleaned_data['integrantedos'] == 0:
                        programa.integrantedos_id = None
                    else:
                        programa.integrantedos_id = f.cleaned_data['integrantedos']
                    programa.integrantetres_id = None
                    programa.save(request)
                    log(u'Editó programa analitico: %s %s' % (programa.asignaturamalla.asignatura.nombre,programa), request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            else:
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'listadelprogramanaliticoobj':
            try:
                objetivo = ObjetivoProgramaAnaliticoAsignatura.objects.get(pk=request.POST['id'])
                descripcion = objetivo.descripcion
                idobjetivo = objetivo.id
                return JsonResponse({"result": "ok", 'descripcion': descripcion, 'idobjetivo': idobjetivo})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'editcontenidosilabosubtema':
            try:
                f = ContenidoSubtema(request.POST)
                subtema = SubtemaUnidadResultadoProgramaAnalitico.objects.get(pk=int(encrypt(request.POST['id'])))
                if f.is_valid():
                    subtema.contenido = f.cleaned_data['contenido']
                    subtema.save(request)
                    log(u'Editó contenidosubtema: %s' % subtema, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'listadelprogramanaliticorai':
            try:
                objetivo = ResultadoAprendizajeRai.objects.get(pk=request.POST['id'])
                descripcion = objetivo.descripcion
                idobjetivo = objetivo.id
                return JsonResponse({"result": "ok", 'descripcion': descripcion, 'codigorai': idobjetivo})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'listadelprogramanaliticorac':
            try:
                objetivo = ResultadoAprendizajeRac.objects.get(pk=request.POST['id'])
                descripcion = objetivo.descripcion
                idobjetivo = objetivo.id
                return JsonResponse({"result": "ok", 'descripcion': descripcion, 'codigorac': idobjetivo})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'listadelprogramanaliticomet':
            try:
                metodologia = MetodologiaProgramaAnaliticoAsignatura.objects.get(pk=request.POST['id'])
                descripcion = metodologia.descripcion
                idmetodologia = metodologia.id
                return JsonResponse({"result": "ok", 'descripcion': descripcion, 'idmetodologia': idmetodologia})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'listadelprogramanaliticolib':
            try:
                bibliografia = BibliografiaProgramaAnaliticoAsignatura.objects.get(pk=request.POST['id'])
                descripcion = bibliografia.librokohaprogramaanaliticoasignatura.nombre
                idbibliografia = bibliografia.id
                return JsonResponse({"result": "ok", 'descripcion': descripcion, 'idbibliografia': idbibliografia})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'listadelprogramanaliticounidad':
            try:
                unidad = UnidadResultadoProgramaAnalitico.objects.get(pk=request.POST['id'])
                descripcion = unidad.descripcion
                codigounidad = unidad.id
                return JsonResponse({"result": "ok", 'descripcion': descripcion, 'codigounidad': codigounidad})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'listadelprogramanaliticoresultado':
            try:
                resultado = ContenidoResultadoProgramaAnalitico.objects.get(pk=request.POST['id'])
                descripcion = resultado.descripcion
                codigoresultado = resultado.id
                return JsonResponse({"result": "ok", 'descripcion': descripcion, 'codigoresultado': codigoresultado})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'listadelprogramanaliticotemas':
            try:
                tema = TemaUnidadResultadoProgramaAnalitico.objects.get(pk=request.POST['id'])
                descripcion = tema.descripcion
                codigotema = tema.id
                return JsonResponse({"result": "ok", 'descripcion': descripcion, 'codigotema': codigotema})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'listadelprogramanaliticosubtemas':
            try:
                subtema = SubtemaUnidadResultadoProgramaAnalitico.objects.get(pk=request.POST['id'])
                descripcion = subtema.descripcion
                codigosubtema = subtema.id
                return JsonResponse({"result": "ok", 'descripcion': descripcion, 'codigosubtema': codigosubtema})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'listadelbibliografia':
            try:
                lib = BibliografiaProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['id'])))
                if lib.odilo:
                    nombrelibro = lib.titulo
                else:
                    nombrelibro = lib.librokohaprogramaanaliticoasignatura.nombre
                codigolibro = encrypt(lib.id)
                return JsonResponse({"result": "ok", 'descripcion': nombrelibro, 'codigolibro': codigolibro})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addlibrouteca':
            try:
                if 'lista_odilo_libros' in request.session:
                    lista_odilo_libros = request.session['lista_odilo_libros']
                    if lista_odilo_libros:
                        for odil in lista_odilo_libros:
                            if not BibliografiaProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura_id=int(encrypt(request.POST['idprogramanalitico'])), codigo=odil[1]['id'], status=True).exists():
                                bibliografia = BibliografiaProgramaAnaliticoAsignatura(programaanaliticoasignatura_id=int(encrypt(request.POST['idprogramanalitico'])),
                                                                                       codigo=odil[1]['id'],
                                                                                       titulo=odil[1]['title'],
                                                                                       isbm=odil[1]['isbn'],
                                                                                       fpublicacion=odil[1]['publicationDate'],
                                                                                       small=odil[1]['coverUrls']['small'],
                                                                                       autor=odil[1]['author'],
                                                                                       odilo=True)
                                bibliografia.save(request)
                        del request.session['lista_odilo_libros']
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addresultadoprogramanalitico':
            try:
                resultado = ContenidoResultadoProgramaAnalitico(programaanaliticoasignatura_id=request.POST['programanalitico'],
                                                                descripcion=request.POST['descripcion'],
                                                                orden=request.POST['ordenresultado'])
                resultado.save(request)
                log(u'Adicionó resultado de programa analitico: %s %s' % (resultado.programaanaliticoasignatura.asignaturamalla.asignatura.nombre,resultado), request, "edit")
                return JsonResponse({"result": "ok", 'idresultado': resultado.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'conresultadoprogramanalitico':
            try:
                resultado = ContenidoResultadoProgramaAnalitico.objects.get(pk=request.POST['id'])
                return JsonResponse({"result": "ok", 'idresultado': resultado.id, 'orden': resultado.orden, 'nombre': resultado.descripcion})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editresultadoprogramanalitico':
            try:
                resultado = ContenidoResultadoProgramaAnalitico.objects.get(pk=request.POST['idresuledit'])
                resultado.descripcion = request.POST['descripcion']
                resultado.orden = request.POST['ordenresultadoedit']
                resultado.save(request)
                log(u'Editó resultado de programa analitico: %s %s' % (resultado.programaanaliticoasignatura.asignaturamalla.asignatura.nombre,resultado), request, "edit")
                return JsonResponse({"result": "ok", 'idresultado': resultado.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addunidadesprogramanalitico':
            try:
                unidades = UnidadResultadoProgramaAnalitico(contenidoresultadoprogramaanalitico_id=request.POST['idunid'],
                                                            descripcion=request.POST['descripcion'],
                                                            orden=request.POST['ordenunidades'])
                unidades.save(request)
                if 'contmin' in request.POST:
                    contenidos_minimos = json.loads(request.POST['contmin'])
                    if not contenidos_minimos:
                        raise NameError(u"Debe seleccionar contenidos minimos")
                    with transaction.atomic():
                        for contenido_id in contenidos_minimos:
                            if AsignaturamallaContenidoMinimo.objects.filter(pk= contenido_id, status=True).exists():
                                detalle = UnidadResultadoProgramaAnaliticoContenidoMinimo(
                                    unidadresultadoprogramaanalitico=unidades,
                                    asignaturamallacontenidominimo_id=contenido_id
                                )
                                detalle.save(request)
                log(u'Adicionó unidad de resultado de programa analitico: %s %s' % (unidades.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre,unidades), request, "add")
                return JsonResponse({"result": "ok", 'idunidades': unidades.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

        elif action == 'conunidadesprogramanalitico':
            try:
                unidades = UnidadResultadoProgramaAnalitico.objects.get(pk=request.POST['id'])
                # Obtener los IDs de los contenidos mínimos seleccionados
                contenidos_minimos_ids = list(
                    UnidadResultadoProgramaAnaliticoContenidoMinimo.objects.filter(
                        unidadresultadoprogramaanalitico=unidades,
                        status=True
                    ).values_list('asignaturamallacontenidominimo_id', flat=True)
                )
                # Obtener todos los contenidos disponibles para el select múltiple
                todos_contenidos = list(
                    AsignaturamallaContenidoMinimo.objects.filter(
                        status=True,
                        asignaturamalla=unidades.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla
                    ).values('id', 'descripcioncontenido')  # Ajusta 'descripcioncontenido' al campo correcto que usas
                )
                return JsonResponse({
                    "result": "ok",
                    'idresultado': unidades.id,
                    'orden': unidades.orden,
                    'nombre': unidades.descripcion,
                    'id_resultadoaprendizaje': unidades.contenidoresultadoprogramaanalitico.id,
                    "contenidos_minimos": contenidos_minimos_ids,
                    "todos_contenidos": todos_contenidos
                })
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

        elif action == 'editunidadesprogramanalitico':
            try:
                unidades = UnidadResultadoProgramaAnalitico.objects.get(pk=request.POST['idunid'])
                unidades.descripcion = request.POST['descripcion']
                unidades.orden = request.POST['ordenunidadesedit']
                res = ContenidoResultadoProgramaAnalitico.objects.filter(id=request.POST['id_resultadoaprendizaje'], status=True)[0]
                if unidades.contenidoresultadoprogramaanalitico != res:
                    unidades.contenidoresultadoprogramaanalitico = res
                unidades.save(request)
                if 'contmin' in request.POST:
                    contenidos_minimos_ids = json.loads(request.POST['contmin'])
                    if not contenidos_minimos_ids:
                        raise NameError(u"Debe seleccionar contenidos minimos")
                    with transaction.atomic():
                        # Eliminar los registros de contenidos mínimos existentes para esta unidad
                        UnidadResultadoProgramaAnaliticoContenidoMinimo.objects.filter(unidadresultadoprogramaanalitico=unidades, status=True).update(status = False)
                        # UnidadResultadoProgramaAnaliticoContenidoMinimo.objects.filter(unidadresultadoprogramaanalitico=unidades, status=True).delete()
                        # Añadir los nuevos registros de contenidos mínimos seleccionados
                        for contenido_id in contenidos_minimos_ids:
                            if AsignaturamallaContenidoMinimo.objects.filter(pk=contenido_id, status=True).exists():
                                detalle = UnidadResultadoProgramaAnaliticoContenidoMinimo(
                                    unidadresultadoprogramaanalitico=unidades,
                                    asignaturamallacontenidominimo_id=contenido_id
                                )
                                detalle.save(request)
                log(u'Editó unidad de resultado de programa analitico: %s %s' % (unidades.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre, unidades), request, "edit")
                return JsonResponse({"result": "ok", 'idunidades': unidades.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

        elif action == 'addtemasprogramanalitico':
            try:
                temas = TemaUnidadResultadoProgramaAnalitico(unidadresultadoprogramaanalitico_id=request.POST['idtem'],
                                                             descripcion=request.POST['descripcion'],
                                                             orden=request.POST['ordentemas'])
                temas.save(request)
                log(u'Adicinó tema de unidad de resultado de programa analitico: %s %s' % (temas.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre,temas), request, "add")
                return JsonResponse({"result": "ok", 'idtemas': temas.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addsubtemasprogramanalitico':
            try:
                subtemas = SubtemaUnidadResultadoProgramaAnalitico(temaunidadresultadoprogramaanalitico_id=request.POST['idsubtem'],
                                                                   descripcion=request.POST['descripcion'],
                                                                   orden=request.POST['ordensubtemas'])
                subtemas.save(request)
                log(u'Adicinó sub tema de unidad de resultado de programa analitico: %s %s' % (subtemas.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre,subtemas), request, "add")
                return JsonResponse({"result": "ok", 'idsubtemas': subtemas.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'contemasprogramanalitico':
            try:
                lista = []
                temas = TemaUnidadResultadoProgramaAnalitico.objects.get(pk=request.POST['id'])
                unidades = UnidadResultadoProgramaAnalitico.objects.filter(contenidoresultadoprogramaanalitico=temas.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico, status=True).order_by('orden')
                for unidad in unidades:
                    lista.append([unidad.id, unidad.descripcion])
                return JsonResponse({"result": "ok", 'idresultado': temas.id, 'orden': temas.orden, 'nombre': temas.descripcion, 'lista': lista, 'unidadselec': temas.unidadresultadoprogramaanalitico_id})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edittemasprogramanalitico':
            try:
                temas = TemaUnidadResultadoProgramaAnalitico.objects.get(pk=request.POST['idtemedit'])
                temas.descripcion = request.POST['descripcion']
                temas.orden = request.POST['ordentemasedit']
                temas.unidadresultadoprogramaanalitico_id = request.POST['codigounidades']
                temas.save(request)
                log(u'Editó tema de unidad de resultado de programa analitico: %s %s' % (temas.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre,temas), request, "edit")
                return JsonResponse({"result": "ok", 'idtemas': temas.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'consubtemasprogramanalitico':
            try:
                subtemas = SubtemaUnidadResultadoProgramaAnalitico.objects.get(pk=request.POST['id'])
                return JsonResponse({"result": "ok", 'idresultado': subtemas.id, 'orden': subtemas.orden, 'nombre': subtemas.descripcion})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editsubtemasprogramanalitico':
            try:
                temas = SubtemaUnidadResultadoProgramaAnalitico.objects.get(pk=request.POST['idsubtemedit'])
                temas.descripcion = request.POST['descripcion']
                temas.orden = request.POST['ordensubtemasedit']
                temas.save(request)
                log(u'Editó sub tema de unidad de resultado de programa analitico: %s %s' % (temas.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre,temas), request, "edit")
                return JsonResponse({"result": "ok", 'idsubtemas': temas.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addprogramanaliticoobj':
            try:
                objetivos = ObjetivoProgramaAnaliticoAsignatura(programaanaliticoasignatura_id=request.POST['programanalitico'],descripcion=request.POST['descripcion'])
                objetivos.save(request)
                log(u'Adicinó objetivo del programa analitico asignatura: %s' % objetivos, request, "add")
                return JsonResponse({"result": "ok", 'idobjetivo': objetivos.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addprogramanaliticorai':
            try:
                objetivos = ResultadoAprendizajeRai(programaanaliticoasignatura_id=request.POST['programanalitico'],descripcion=request.POST['descripcion'])
                objetivos.save(request)
                log(u'Adicinó resultado de aprendizaje Rai: %s' % objetivos, request, "add")
                return JsonResponse({"result": "ok", 'codigorai': objetivos.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addprogramanaliticorac':
            try:
                objetivos = ResultadoAprendizajeRac(programaanaliticoasignatura_id=request.POST['programanalitico'],descripcion=request.POST['descripcion'])
                objetivos.save(request)
                log(u'Adicinó resultado de aprendizaje Rac: %s' % objetivos, request, "add")
                return JsonResponse({"result": "ok", 'codigorac': objetivos.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addprogramanaliticomet':
            try:
                metodologias = MetodologiaProgramaAnaliticoAsignatura(programaanaliticoasignatura_id=request.POST['programanalitico'],descripcion=request.POST['descripcion'])
                metodologias.save(request)
                log(u'Adicinó metodologia de programa analitico asignatura: %s' % metodologias, request, "add")
                return JsonResponse({"result": "ok", 'idmetodologia': metodologias.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addprogramanaliticolib':
            try:
                bibliografias = BibliografiaProgramaAnaliticoAsignatura(programaanaliticoasignatura_id=request.POST['programanalitico'],
                                                                        librokohaprogramaanaliticoasignatura_id=request.POST['idlibro'])
                bibliografias.save(request)
                log(u'Adicinó bibliografia de programa analitico asignatura: %s' % bibliografias, request, "add")
                return JsonResponse({"result": "ok", 'idbibliografia': bibliografias.id, 'nomlibro': bibliografias.librokohaprogramaanaliticoasignatura.nombre})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'eliminarprogramanaliticoobj':
            try:
                detalles = ObjetivoProgramaAnaliticoAsignatura.objects.get(pk=request.POST['idobjetivo'])
                log(u'Eliminó objetivo de programa analitico asignatura: %s' % detalles, request, "del")
                detalles.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'eliminarprogramanaliticorai':
            try:
                detalles = ResultadoAprendizajeRai.objects.get(pk=request.POST['idcodigorai'])
                log(u'Eliminó resultado de aprendizaje Rai: %s' % detalles, request, "del")
                detalles.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'eliminarprogramanaliticorac':
            try:
                detalles = ResultadoAprendizajeRac.objects.get(pk=request.POST['idcodigorac'])
                log(u'Eliminó resultado de aprendizaje Rac: %s' % detalles, request, "del")
                detalles.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'eliminarprogramanaliticomet':
            try:
                metodologia = MetodologiaProgramaAnaliticoAsignatura.objects.get(pk=request.POST['idmetodologia'])
                log(u'Eliminó metodología de programa analitico asignatura: %s' % metodologia, request, "del")
                metodologia.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'eliminarprogramanaliticolib':
            try:
                bibliografia = BibliografiaProgramaAnaliticoAsignatura.objects.get(pk=request.POST['idbibliografia'])
                log(u'Eliminó bibliografia de programa analitico asignatura: %s %s' % (bibliografia.programaanaliticoasignatura.asignaturamalla.asignatura.nombre,bibliografia), request, "del")
                bibliografia.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'eliminarprogramanaliticounidad':
            try:
                unidad = UnidadResultadoProgramaAnalitico.objects.get(pk=request.POST['codigounidad'])
                log(u'Eliminó unidad de resultado de programa analitico asignatura: %s %s' % (unidad.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre,unidad), request, "del")
                unidad.status=False
                unidad.save(request)
                #PONER EN STATUS FALSE LOS REGISTROS DE LA TABLA DONDE SE RELACIONAN LOS CONTENIDOS MINIMOS CON LA UNIDAD DEL PROGRAMA ANALITICO
                UnidadResultadoProgramaAnaliticoContenidoMinimo.objects.filter(unidadresultadoprogramaanalitico=unidad, status=True).update(status=False)
                if unidad.temaunidadresultadoprogramaanalitico_set.values('id').filter(status=True).exists():
                    for tema in unidad.temaunidadresultadoprogramaanalitico_set.filter(status=True):
                        tema.status = False
                        tema.save(request)
                    #unidad.temaunidadresultadoprogramaanalitico_set.update(status=True)
                if SubtemaUnidadResultadoProgramaAnalitico.objects.filter(temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico=unidad, status=True).exists():
                    # for subtema in SubtemaUnidadResultadoProgramaAnalitico.objects.values('id').filter(temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico=unidad, status=True):
                    for subtema in SubtemaUnidadResultadoProgramaAnalitico.objects.filter(temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico=unidad, status=True):
                        subtema.status=False
                        subtema.save(request)
                    #SubtemaUnidadResultadoProgramaAnalitico.objects.filter(temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico=unidad).update(status=True)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'eliminarprogramanaliticoresultado':
            try:
                resultado = ContenidoResultadoProgramaAnalitico.objects.get(pk=request.POST['codigoresultado'])
                log(u'Eliminó contenido resultado de programa analitico asignatura: %s %s' % (resultado.programaanaliticoasignatura.asignaturamalla.asignatura.nombre,resultado), request, "del")
                resultado.status=False
                resultado.save(request)
                # PONER EN STATUS FALSE LOS REGISTROS DE LA TABLA DONDE SE RELACIONAN LOS CONTENIDOS MINIMOS CON LA UNIDAD DEL PROGRAMA ANALITICO
                UnidadResultadoProgramaAnaliticoContenidoMinimo.objects.filter(unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico=resultado,status=True).update(status=False)
                if resultado.unidadresultadoprogramaanalitico_set.values('id').filter(status=True).exists():
                    for unidad in resultado.unidadresultadoprogramaanalitico_set.filter(status=True):
                        unidad.status = False
                        unidad.save(request)
                    #resultado.unidadresultadoprogramaanalitico_set.update(status=True)
                if TemaUnidadResultadoProgramaAnalitico.objects.values('id').filter(unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico=resultado, status=True).exists():
                    for tema in TemaUnidadResultadoProgramaAnalitico.objects.filter(unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico=resultado, status=True):
                        tema.status =False
                        tema.save(request)
                    #TemaUnidadResultadoProgramaAnalitico.objects.filter(unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico=resultado).update(status=True)
                if SubtemaUnidadResultadoProgramaAnalitico.objects.values('id').filter(temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico=resultado, status=True).exists():
                    for subtema in SubtemaUnidadResultadoProgramaAnalitico.objects.filter(temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico=resultado, status=True):
                        subtema.status = False
                        subtema.save(request)
                    #SubtemaUnidadResultadoProgramaAnalitico.objects.filter(temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico=resultado).update(status=False)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'eliminarprogramanaliticotema':
            try:
                tema = TemaUnidadResultadoProgramaAnalitico.objects.get(pk=request.POST['codigotema'])
                log(u'Eliminó tema unidad de resultado de programa analitico: %s %s' % (tema.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre ,tema), request, "del")
                tema.status=False
                tema.save(request)
                if tema.subtemaunidadresultadoprogramaanalitico_set.values('id').filter(status=True).exists():
                    for subtema in tema.subtemaunidadresultadoprogramaanalitico_set.all(status=True):
                        subtema.status = False
                        subtema.save(request)
                    #tema.subtemaunidadresultadoprogramaanalitico_set.all().update(status=False)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'eliminarprogramanaliticosubtema':
            try:
                subtema = SubtemaUnidadResultadoProgramaAnalitico.objects.get(pk=request.POST['codigosubtema'])
                log(u'Eliminó sub tema unidad de resultado de programa analitico: %s %s' % (subtema.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre,subtema), request, "del")
                subtema.status=False
                subtema.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'eliminarbibliografia':
            try:
                lib = BibliografiaProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['codigosubtema'])))
                log(u'Eliminó bibliografia de programa analitico asignatura: %s %s' % (lib.programaanaliticoasignatura.asignaturamalla.asignatura.nombre,lib), request, "del")
                lib.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'programanaliticopdf':
            try:
                data['proanalitico'] = pro = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['id'])))
                return conviert_html_to_pdf(
                    'mallas/programanalitico_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': pro.plananalitico_pdf(periodo),
                    }
                )
            except Exception as ex:
                pass

        elif action == 'programanaliticoposgradopdf':
            try:
                data['proanalitico'] = pro = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['id'])))
                return conviert_html_to_pdf(
                    'mallas/programanaliticoposgrado_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': pro.plananalitico_pdf(periodo),
                    }
                )
            except Exception as ex:
                pass

        elif action == 'cambiaestado':
            try:
                programaanalitico = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['idprogramaanalitico'])))
                ProgramaAnaliticoAsignatura.objects.filter(asignaturamalla=programaanalitico.asignaturamalla,status=True).update(activo=False)
                if programaanalitico.activo:
                    programaanalitico.activo = False
                else:
                    programaanalitico.activo = True
                programaanalitico.save(request)
                log(u'Modificó estado de programa analitico asignatura: %s' % programaanalitico, request, "edit")
                return JsonResponse({'result': 'ok', 'valor': programaanalitico.activo})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addprogramaanaliticoasignaturamalla':
            try:
                form = ProgramaAnaliticoAsignaturaMallaForm(request.POST, request.FILES)
                if form.is_valid():
                    newfileword = request.FILES['archivoword']
                    newfileword._name = generar_nombre("programaanaliticoasignaturamalla_", newfileword._name)
                    newfilepdf = request.FILES['archivopdf']
                    newfilepdf._name = generar_nombre("programaanaliticoasignaturamalla_", newfilepdf._name)
                    asignaturamalla = AsignaturaMalla.objects.get(pk=request.POST['id'])
                    ProgramaAnaliticoAsignaturaMalla.objects.filter(asignaturamalla=asignaturamalla).update(aprobado=False)
                    programaanaliticoasignaturamalla = ProgramaAnaliticoAsignaturaMalla(descripcion=form.cleaned_data['descripcion'],
                                                                                        asignaturamalla=asignaturamalla,
                                                                                        fecha=form.cleaned_data['fecha'],
                                                                                        archivoword=newfileword,
                                                                                        archivopdf=newfilepdf,
                                                                                        aprobado=True)
                    programaanaliticoasignaturamalla.save(request)
                    log(u'Adiciono Programa Analítico Asignatura Malla: %s - %s' % (asignaturamalla, programaanaliticoasignaturamalla.fecha), request, "add")
                    return JsonResponse({"result": "ok"}, )
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editprogramaanaliticoasignaturamalla':
            try:
                form = ProgramaAnaliticoAsignaturaMallaForm(request.POST, request.FILES)
                if form.is_valid():

                    # nombres de los archivos
                    newfileword = request.FILES['archivoword']
                    newfileword._name = generar_nombre("programaanaliticomateria_", newfileword._name)
                    newfilepdf = request.FILES['archivopdf']
                    newfilepdf._name = generar_nombre("programaanaliticomateria_", newfilepdf._name)

                    programaanaliticoasignaturamalla = ProgramaAnaliticoAsignaturaMalla.objects.get(pk=request.POST['id'])
                    programaanaliticoasignaturamalla.archivoword = newfileword
                    programaanaliticoasignaturamalla.archivopdf = newfilepdf
                    programaanaliticoasignaturamalla.save(request)
                    log(u'Modifico Programa Analítoco Asignatura Malla : %s ' % programaanaliticoasignaturamalla, request, "edit")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al Modificar los datos."})

        elif action == 'addasign':
            try:
                f = AsignaturaMallaForm(request.POST)
                if f.is_valid():
                    if AsignaturaMalla.objects.values('id').filter(malla_id=int(encrypt(request.POST['malla'])), asignatura=f.cleaned_data['asignatura']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe la malla con la asignatura seleccionada."})

                    if f.cleaned_data['horas'] <= 0:
                        return JsonResponse({"result": "bad", "mensaje": u"El total de Horas debe ser mayor que 0"})

                    horasacdtotal = f.cleaned_data['horasacdtotal'] if 'horasacdtotal' in f.cleaned_data and f.cleaned_data['horasacdtotal'] is not None and f.cleaned_data['horasacdtotal'] >= 0 else 0.0
                    horasapetotal = f.cleaned_data['horasapetotal'] if 'horasapetotal' in f.cleaned_data and f.cleaned_data['horasapetotal'] is not None and f.cleaned_data['horasapetotal'] >= 0 else 0.0
                    horasautonomas = f.cleaned_data['horasautonomas'] if 'horasautonomas' in f.cleaned_data and f.cleaned_data['horasautonomas'] is not None and f.cleaned_data['horasautonomas'] >= 0 else 0.0
                    horasvinculaciontotal = f.cleaned_data['horasvinculaciontotal'] if 'horasvinculaciontotal' in f.cleaned_data and f.cleaned_data['horasvinculaciontotal'] is not None and f.cleaned_data['horasvinculaciontotal'] >= 0 else 0.0
                    horasppptotal = f.cleaned_data['horasppptotal'] if 'horasppptotal' in f.cleaned_data and f.cleaned_data['horasppptotal'] is not None and f.cleaned_data['horasppptotal'] >= 0 else 0.0
                    horasteoriatitutotal = f.cleaned_data['horasteoriatitutotal'] if 'horasteoriatitutotal' in f.cleaned_data and f.cleaned_data['horasteoriatitutotal'] is not None and f.cleaned_data['horasteoriatitutotal'] >= 0 else 0.0
                    # sumahoras = f.cleaned_data['horasacdtotal'] + f.cleaned_data['horasapetotal'] + f.cleaned_data['horasautonomas'] + f.cleaned_data['horasvinculaciontotal'] + f.cleaned_data['horasppptotal']
                    sumahoras = horasacdtotal + horasapetotal + horasautonomas + horasvinculaciontotal + horasppptotal + horasteoriatitutotal
                    if sumahoras != f.cleaned_data['horas']:
                        if f.cleaned_data['tipomateria']:
                            if f.cleaned_data['tipomateria'].id !=3 :
                                return JsonResponse({"result": "bad", "mensaje": u"La sumatoria de los valores de los campos ACD Totales, APE Totales, AA Totales ( %.2f ), Horas Vinculación Totales y Horas Prácticas Pre-profesionales Totales, debe ser igual que el valor del campo Horas Totales ( %.2f )" % (sumahoras, f.cleaned_data['horas'])})
                        else:
                            return JsonResponse({"result": "bad","mensaje": u"La sumatoria de los valores de los campos ACD Totales, APE Totales, AA Totales ( %.2f ), Horas Vinculación Totales y Horas Prácticas Pre-profesionales Totales, debe ser igual que el valor del campo Horas Totales ( %.2f )" % (sumahoras, f.cleaned_data['horas'])})
                    asignaturamalla = AsignaturaMalla(malla_id=int(encrypt(request.POST['malla'])),
                                                      asignatura=f.cleaned_data['asignatura'],
                                                      nivelmalla_id=int(request.POST['nivel']),
                                                      #ejeformativo_id=int(encrypt(request.POST['eje'])),
                                                      ejeformativo=f.cleaned_data['ejeformativo'],
                                                      horas=f.cleaned_data['horas'],
                                                      creditos=f.cleaned_data['creditos'],
                                                      costo=f.cleaned_data['costo'] if 'costo' in request.POST else 0,
                                                      rectora=f.cleaned_data['rectora'],
                                                      reemplazo=f.cleaned_data['reemplazo'],
                                                      vigente=f.cleaned_data['vigente'],
                                                      practicas=f.cleaned_data['practicas'],
                                                      identificacion=f.cleaned_data['identificacion'],
                                                      areaconocimiento=f.cleaned_data['areaconocimiento'],
                                                      horaspresenciales=f.cleaned_data['horaspresenciales'] if 'horaspresenciales' in request.POST else 0,
                                                      horasautonomas=f.cleaned_data['horasautonomas'],
                                                      horaspresencialessemanales = f.cleaned_data['horaspresencialessemanales'] if 'horaspresencialessemanales' in request.POST else 0,
                                                      horasautonomassemanales = f.cleaned_data['horasautonomassemanales'],
                                                      horaspracticastotales=f.cleaned_data['horaspracticastotales'] if 'horaspracticastotales' in request.POST else 0,
                                                      horaspracticassemanales=f.cleaned_data['horaspracticassemanales'] if 'horaspracticassemanales' in request.POST else 0,
                                                      horasasistidas=f.cleaned_data['horasasistidas'] if 'horasasistidas' in request.POST else 0,
                                                      areaconocimientotitulacion=f.cleaned_data['areaconocimientotitulacion'],
                                                      subareaconocimiento=f.cleaned_data['subareaconocimiento'],
                                                      subareaespecificaconocimiento=f.cleaned_data['subareaespecificaconocimiento'],
                                                      horascolaborativas=f.cleaned_data['horascolaborativas'] if 'horascolaborativas' in request.POST else 0,
                                                      porcentajecalificacion=f.cleaned_data['porcentajecalificacion'] if 'porcentajecalificacion' in request.POST else 0,
                                                      horasacdtotal=f.cleaned_data['horasacdtotal'],
                                                      horasacdsemanal=f.cleaned_data['horasacdsemanal'],
                                                      horasvirtualtotal=f.cleaned_data['horasvirtualtotal'] if 'horasvirtualtotal' in request.POST else 0,
                                                      horasvirtualsemanal=f.cleaned_data['horasvirtualsemanal'] if 'horasvirtualsemanal' in request.POST else 0,
                                                      horasapetotal=f.cleaned_data['horasapetotal'],
                                                      horasapesemanal=f.cleaned_data['horasapesemanal'],
                                                      horasvinculaciontotal=f.cleaned_data['horasvinculaciontotal'],
                                                      horasvinculacionsemanal=f.cleaned_data['horasvinculacionsemanal'],
                                                      horasppptotal=f.cleaned_data['horasppptotal'],
                                                      horaspppsemanal=f.cleaned_data['horaspppsemanal'],
                                                      horasapeasistotal=f.cleaned_data['horasapeasistotal'],
                                                      horasapeasissemanal=f.cleaned_data['horasapeasissemanal'],
                                                      horasapeautototal=f.cleaned_data['horasapeautototal'],
                                                      horasapeautosemanal=f.cleaned_data['horasapeautosemanal'],
                                                      itinerario=f.cleaned_data['itinerario'],
                                                      unidad_organizacion_curricular=f.cleaned_data['unidad_organizacion_curricular'],
                                                      tipomateria=f.cleaned_data['tipomateria'],
                                                      itinerario_malla_especialidad=f.cleaned_data['itinerario_malla_especialidad'],
                                                      afinidaddoctorado=f.cleaned_data['afinidaddoctorado'],
                                                      horasteoriatitutotal=f.cleaned_data['horasteoriatitutotal'],
                                                      nivelsuficiencia=f.cleaned_data['nivelsuficiencia'],
                                                      asignaturapracticas=f.cleaned_data['asignaturapracticas']
                                                      )
                    asignaturamalla.save(request)
                    # if not f.cleaned_data['ejeformativo'] in [4, 9, 11,12]:
                    #     if registro_horas_semanales := MallaHorasSemanalesComponentes.objects.filter(status=True, malla_id = int(encrypt(request.POST['malla'])),nivelmalla_id = int(request.POST['nivel'])).first():
                    #         if not (int(f.cleaned_data['itinerario']) > 0 and MallaHorasSemanalesComponentes.objects.filter(status=True, malla_id = int(encrypt(request.POST['malla'])),nivelmalla_id = int(request.POST['nivel']),tiene_itinerario = True).exists()):
                    #             registro_horas_semanales.acd_horassemanales += round((f.cleaned_data['horasacdtotal']/16),1)
                    #             registro_horas_semanales.ape_aa_horassemanales += round((f.cleaned_data['horasapetotal']/16),1) + round((f.cleaned_data['horasautonomas']/16),1)
                    #             registro_horas_semanales.total_horassemanales += round((f.cleaned_data['horasacdtotal']/16),1) + round((f.cleaned_data['horasapetotal']/16),1) + round((f.cleaned_data['horasautonomas']/16),1)
                    #             if int(f.cleaned_data['itinerario']) > 0:
                    #                 registro_horas_semanales.tiene_itinerario = True
                    #             registro_horas_semanales.save(request)
                    #     else:
                    #         horas_semanales_malla = MallaHorasSemanalesComponentes(malla_id = int(encrypt(request.POST['malla'])),
                    #                                                                nivelmalla_id = int(request.POST['nivel']),
                    #                                                                acd_horassemanales = round((f.cleaned_data['horasacdtotal']/16),1),
                    #                                                                ape_aa_horassemanales = round((f.cleaned_data['horasapetotal']/16),1) + round((f.cleaned_data['horasautonomas']/16),1),
                    #                                                                total_horassemanales = round((f.cleaned_data['horasacdtotal']/16),1) + round((f.cleaned_data['horasapetotal']/16),1) + round((f.cleaned_data['horasautonomas']/16),1)
                    #                                                            )
                    #         if int(f.cleaned_data['itinerario']) > 0:
                    #             horas_semanales_malla.tiene_itinerario = True
                    #         horas_semanales_malla.save(request)
                    log(u'Adiciono asignatura malla: %s' % asignaturamalla, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'info':
            try:
                a = Asignatura.objects.get(pk=request.POST['aid'])
                return JsonResponse({'result': 'ok', 'creditos': a.creditos, 'codigo': a.codigo, 'horas': a.horas()})
            except Exception as ex:
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al obtener los datos."})

        elif action == 'addpredecesora':
            try:
                asignaturamalla = AsignaturaMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                f = AsignaturaMallaPredecesoraForm(request.POST)
                if f.is_valid():
                    predecesora = AsignaturaMallaPredecesora(asignaturamalla=asignaturamalla,
                                                             predecesora=f.cleaned_data['predecesora'])
                    predecesora.save(request)
                    log(u'Adiciono predecesora asignatura malla: %s' % asignaturamalla, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addpredecesora_v2':
            try:
                #NUEVA ADICION EN BASE A LA PLANTILLA V2
                # Desencriptar el ID de la asignaturamalla
                asignaturamalla_id = int(encrypt(request.POST['id']))
                asignaturamalla = AsignaturaMalla.objects.get(pk=asignaturamalla_id)
                # Obtener el ID de la asignatura predecesora del formulario
                predecesora_id = request.POST.get('asignatura_predecesora')
                # Verificar que el ID de la predecesora no esté vacío
                if predecesora_id:
                    # Crear y guardar la nueva predecesora
                    predecesora = AsignaturaMallaPredecesora(
                        asignaturamalla=asignaturamalla,
                        predecesora_id=predecesora_id  # Asumiendo que predecesora_id es el campo en el modelo
                    )
                    predecesora.save()
                    log(u'Adiciono predecesora asignatura malla: %s' % asignaturamalla, request, "edit")
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con exito'})
                else:
                    raise NameError('Debe seleccionar una asignatura predecesora')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'imparticionclase':
            try:
                f = AsignaturaMallaModalidadForm(request.POST)
                asignaturamalla = AsignaturaMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                if f.is_valid():
                    detalleasignmalla = DetalleAsignaturaMallaModalidad(
                        asignaturamalla=asignaturamalla,
                        modalidad=f.cleaned_data['modalidad'],
                    )
                    detalleasignmalla.save(request)
                    log(u'Adiciono Modalidad Imparticion Clase: %s' % detalleasignmalla, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cambiarmodalidadasignatura':
            try:
                asigmalla = AsignaturaMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                detasig = DetalleAsignaturaMallaModalidad.objects.get(status=True, asignaturamalla_id=asigmalla)
                f = AsignaturaMallaModalidadForm(request.POST)
                if f.is_valid():
                    detasig.modalidad =f.cleaned_data['modalidad']
                    detasig.save()
                    log(u'Modifico Modalidad Imparticion Clase: %s' % detasig, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addcorequisito':
            try:
                asignaturamalla = AsignaturaMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                f = AsignaturaMallaCoRequisitoForm(request.POST)
                if f.is_valid():
                    corequisito = AsignaturaMallaCoRequisito(asignaturamalla=asignaturamalla, corequisito=f.cleaned_data['corequisito'])
                    corequisito.save(request)
                    log(u'Adiciono un Co-Requisito a la  asignatura malla: %s la persona %s' % (asignaturamalla, persona), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addcorequisito_v2':
            try:
                # NUEVA ADICION EN BASE A LA PLANTILLA V2
                # Desencriptar el ID de la asignaturamalla
                asignaturamalla_id = int(encrypt(request.POST['id']))
                asignaturamalla = AsignaturaMalla.objects.get(pk=asignaturamalla_id)
                # Obtener el ID de la asignatura predecesora del formulario
                correquisito_id = request.POST.get('asignatura_correquisito')
                if correquisito_id:
                    # Crear y guardar la nueva predecesora
                    corequisito = AsignaturaMallaCoRequisito(asignaturamalla=asignaturamalla,
                                                             corequisito_id=correquisito_id)
                    corequisito.save(request)
                    log(u'Adiciono un Co-Requisito a la  asignatura malla: %s la persona %s' % (asignaturamalla, persona), request, "edit")
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con exito'})
                else:
                    raise NameError('Debe seleccionar una asignatura de correquisito')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delpredecesora_v2':
            try:
                puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                predecesora = AsignaturaMallaPredecesora.objects.filter(asignaturamalla__malla__carrera__in=miscarreras).get(pk=int(encrypt(request.POST['id'])))
                asignaturamalla = predecesora.asignaturamalla
                log(u'Elimino predecesora: %s' % asignaturamalla, request, "del")
                predecesora.delete()
                # return HttpResponseRedirect("/mallas?action=predecesora&id=" + str(encrypt(asignaturamalla.id)))
                return JsonResponse({'result': False, 'mensaje': 'Eliminado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delcorequisito':
            try:
                puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                corequisito = AsignaturaMallaCoRequisito.objects.filter(asignaturamalla__malla__carrera__in=miscarreras).get(pk=int(encrypt(request.POST['id'])))
                log(u'Elimino el Co-Requisito %s de la Asignatura: %s' % (corequisito.corequisito, corequisito.asignaturamalla), request, "del")
                corequisito.delete()
                # return JsonResponse({"result": "ok"})
                return JsonResponse({'result': False, 'mensaje': 'Eliminado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addhomologacion':
            try:
                asignaturamalla = AsignaturaMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                f = AsignaturaMallaHomologacionForm(request.POST)
                if f.is_valid():
                    homologacion = AsignaturaMallaHomologacion(asignaturamalla=asignaturamalla,
                                                               homologacion=f.cleaned_data['homologacion'])
                    homologacion.save(request)
                    log(u'Adiciono un Homologacion a la  asignatura malla: %s la persona %s' % (asignaturamalla, persona), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletehomologacion':
            try:
                puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                homologacion = AsignaturaMallaHomologacion.objects.get(pk=request.POST['id'])
                homologacion.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addmodulo':
            try:
                malla = Malla.objects.get(pk=int(encrypt(request.POST['id'])))
                f = AsignaturaModuloForm(request.POST)
                if not f.is_valid():
                    raise NameError('Formulario contiene errores')
                if ModuloMalla.objects.filter(asignatura=f.cleaned_data['asignatura'], malla=malla, status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra registrada."})
                if ModuloMalla.objects.filter(malla=malla,orden=f.cleaned_data['orden'], status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existe un modulo con el mismo orden en esta malla."})
                asignaturamodulo = ModuloMalla(asignatura=f.cleaned_data['asignatura'],
                                               malla=malla,
                                               tipo=f.cleaned_data['tipo'],
                                               horas=f.cleaned_data['horas'],
                                               creditos=f.cleaned_data['creditos'],
                                               orden=f.cleaned_data['orden'])
                asignaturamodulo.save(request)
                log(u'Adiciono asignatura modulo: %s' % asignaturamodulo, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'editmodulo':
            try:
                asignaturamodulo = ModuloMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                f = AsignaturaModuloForm(request.POST)
                if not f.is_valid():
                    raise NameError('Formulario contiene errores')
                if ModuloMalla.objects.filter(asignatura=f.cleaned_data['asignatura'], malla=asignaturamodulo.malla,orden=f.cleaned_data['orden']).exclude(pk=asignaturamodulo.id).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra registrada."})
                if ModuloMalla.objects.filter(malla=asignaturamodulo.malla,orden=f.cleaned_data['orden']).exclude(pk=asignaturamodulo.id).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existe un modulo con el mismo orden en esta malla."})
                asignaturamodulo.horas = f.cleaned_data['horas']
                asignaturamodulo.creditos = f.cleaned_data['creditos']
                asignaturamodulo.tipo = f.cleaned_data['tipo']
                asignaturamodulo.orden=f.cleaned_data['orden']
                asignaturamodulo.save(request)
                log(u'Edito asignatura modulo: %s' % asignaturamodulo, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'editasign':
            try:
                f = AsignaturaMallaForm(request.POST)
                asignaturamalla = AsignaturaMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                # horas_autonomas_antiguas = float(request.POST['horasautonomas_antiguas'])
                # horasacd_antiguas = float(request.POST['horasacd_antiguas'])
                # horasape_antiguas = float(request.POST['horasape_antiguas'])
                # tuvo_itinerario = int(request.POST['tuvo_itinerario'])
                if f.is_valid():
                    if f.cleaned_data['horas'] <= 0:
                        return JsonResponse({"result": "bad", "mensaje": u"El total de Horas debe ser mayor que 0"})
                    horasacdtotal = f.cleaned_data['horasacdtotal'] if 'horasacdtotal' in f.cleaned_data and f.cleaned_data['horasacdtotal'] is not None and f.cleaned_data['horasacdtotal'] >= 0 else 0.0
                    horasapetotal = f.cleaned_data['horasapetotal'] if 'horasapetotal' in f.cleaned_data and f.cleaned_data['horasapetotal'] is not None and f.cleaned_data['horasapetotal'] >= 0 else 0.0
                    horasautonomas = f.cleaned_data['horasautonomas'] if 'horasautonomas' in f.cleaned_data and f.cleaned_data['horasautonomas'] is not None and f.cleaned_data['horasautonomas'] >= 0 else 0.0
                    horasvinculaciontotal = f.cleaned_data['horasvinculaciontotal'] if 'horasvinculaciontotal' in f.cleaned_data and f.cleaned_data['horasvinculaciontotal'] is not None and f.cleaned_data['horasvinculaciontotal'] >= 0 else 0.0
                    horasppptotal = f.cleaned_data['horasppptotal'] if 'horasppptotal' in f.cleaned_data and f.cleaned_data['horasppptotal'] is not None and f.cleaned_data['horasppptotal'] >= 0 else 0.0
                    horasteoriatitutotal = f.cleaned_data['horasteoriatitutotal'] if 'horasteoriatitutotal' in f.cleaned_data and f.cleaned_data['horasteoriatitutotal'] is not None and f.cleaned_data['horasteoriatitutotal'] >= 0 else 0.0
                    # sumahoras = f.cleaned_data['horasacdtotal'] + f.cleaned_data['horasapetotal'] + f.cleaned_data['horasautonomas'] + f.cleaned_data['horasvinculaciontotal'] + f.cleaned_data['horasppptotal']
                    sumahoras = horasacdtotal + horasapetotal + horasautonomas + horasvinculaciontotal + horasppptotal + horasteoriatitutotal

                    if sumahoras != f.cleaned_data['horas']:
                        if f.cleaned_data['tipomateria']:
                            if f.cleaned_data['tipomateria'].id !=3:
                                return JsonResponse({"result": "bad", "mensaje": u"La sumatoria de los valores de los campos ACD Totales, APE Totales , AA Totales ( %.2f ), Horas Vinculación Totales y Horas Prácticas Pre-profesionales Totales, debe ser igual que el valor del campo Horas Totales ( %.2f )" % (sumahoras, f.cleaned_data['horas'])})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"La sumatoria de los valores de los campos ACD Totales, APE Totales , AA Totales ( %.2f ), Horas Vinculación Totales y Horas Prácticas Pre-profesionales Totales, debe ser igual que el valor del campo Horas Totales ( %.2f )" % (sumahoras, f.cleaned_data['horas'])})
                    if not asignaturamalla.malla.cerrado:
                        asignaturamalla.ejeformativo = f.cleaned_data['ejeformativo']
                        asignaturamalla.nivelmalla = f.cleaned_data['nivel']
                        asignaturamalla.tipomateria = f.cleaned_data['tipomateria']
                        asignaturamalla.identificacion = f.cleaned_data['identificacion']
                        asignaturamalla.itinerario = f.cleaned_data['itinerario']
                        if f.cleaned_data['itinerario_malla_especialidad']:
                            asignaturamalla.itinerario_malla_especialidad = f.cleaned_data['itinerario_malla_especialidad']
                        asignaturamalla.creditos = f.cleaned_data['creditos']
                        asignaturamalla.costo = f.cleaned_data['costo'] if 'costo' in request.POST else 0
                        asignaturamalla.horas = f.cleaned_data['horas']
                        asignaturamalla.horaspresenciales = f.cleaned_data['horaspresenciales']
                        asignaturamalla.horaspresencialessemanales = f.cleaned_data['horaspresencialessemanales']
                        asignaturamalla.horasautonomas = f.cleaned_data['horasautonomas']
                        asignaturamalla.horasapeasistotal = f.cleaned_data['horasapeasistotal']
                        asignaturamalla.horasapeautototal = f.cleaned_data['horasapeautototal']
                        asignaturamalla.horasvirtualtotal = f.cleaned_data['horasvirtualtotal']
                        asignaturamalla.horasvirtualsemanal = f.cleaned_data['horasvirtualsemanal']
                        asignaturamalla.horasapeasissemanal = f.cleaned_data['horasapeasissemanal']
                        asignaturamalla.horasapeautosemanal = f.cleaned_data['horasapeautosemanal']
                        asignaturamalla.horasautonomassemanales = f.cleaned_data['horasautonomassemanales']
                        asignaturamalla.horasvinculaciontotal = f.cleaned_data['horasvinculaciontotal']
                        asignaturamalla.horasvinculacionsemanal = f.cleaned_data['horasvinculacionsemanal']
                        asignaturamalla.horasppptotal = f.cleaned_data['horasppptotal']
                        asignaturamalla.horaspppsemanal = f.cleaned_data['horaspppsemanal']
                        asignaturamalla.horasacdtotal = f.cleaned_data['horasacdtotal']
                        asignaturamalla.horasacdsemanal = f.cleaned_data['horasacdsemanal']
                        asignaturamalla.horasapetotal = f.cleaned_data['horasapetotal']
                        asignaturamalla.horasapesemanal = f.cleaned_data['horasapesemanal']

                    asignaturamalla.validarequisitograduacion = f.cleaned_data['validarequisitograduacion']
                    asignaturamalla.transversal = f.cleaned_data['transversal']
                    asignaturamalla.reemplazo = f.cleaned_data['reemplazo']
                    asignaturamalla.rectora = f.cleaned_data['rectora']
                    asignaturamalla.practicas = f.cleaned_data['practicas']
                    asignaturamalla.areaconocimiento = f.cleaned_data['areaconocimiento']
                    asignaturamalla.opcional = f.cleaned_data['opcional']
                    asignaturamalla.vigente = f.cleaned_data['vigente']
                    asignaturamalla.nivelsuficiencia = f.cleaned_data['nivelsuficiencia']
                    asignaturamalla.afinidaddoctorado = f.cleaned_data['afinidaddoctorado']
                    asignaturamalla.nohomologa = f.cleaned_data['nohomologa']
                    if f.cleaned_data['horaspracticastotales']:
                        asignaturamalla.horaspracticastotales = f.cleaned_data['horaspracticastotales']
                        asignaturamalla.horaspracticassemanales = f.cleaned_data['horaspracticassemanales']

                    if f.cleaned_data['horasasistidas']:
                        asignaturamalla.horasasistidas = f.cleaned_data['horasasistidas']
                    if f.cleaned_data['horascolaborativas']:
                        asignaturamalla.horascolaborativas = f.cleaned_data['horascolaborativas']
                    if f.cleaned_data['horasteoriatitutotal']:
                        asignaturamalla.horasteoriatitutotal = f.cleaned_data['horasteoriatitutotal']

                    asignaturamalla.areaconocimientotitulacion = f.cleaned_data['areaconocimientotitulacion']
                    asignaturamalla.subareaconocimiento = f.cleaned_data['subareaconocimiento']
                    asignaturamalla.subareaespecificaconocimiento = f.cleaned_data['subareaespecificaconocimiento']
                    asignaturamalla.porcentajecalificacion = f.cleaned_data['porcentajecalificacion'] if 'porcentajecalificacion' in request.POST else 0
                    if f.cleaned_data['unidad_organizacion_curricular']:
                        asignaturamalla.unidad_organizacion_curricular = f.cleaned_data['unidad_organizacion_curricular']
                    asignaturamalla.asignaturapracticas = f.cleaned_data['asignaturapracticas']
                    asignaturamalla.save(request)
                    Materia.objects.filter(asignaturamalla=asignaturamalla, nivel__cerrado=False).update(horas=asignaturamalla.horas, creditos=asignaturamalla.creditos)
                    # if not f.cleaned_data['ejeformativo'] in [4, 9, 11,12]:
                    #     if registro_horas_semanales := MallaHorasSemanalesComponentes.objects.filter(status=True, malla_id = asignaturamalla.malla.id,nivelmalla_id = int(request.POST['nivel'])).first():
                    #         if tuvo_itinerario > 0:
                    #             if int(f.cleaned_data['itinerario']) > 0:
                    #                 asignatura_malla_itinerario = AsignaturaMalla.objects.filter(status=True,malla_id=asignaturamalla.malla.id,nivelmalla_id=asignaturamalla.nivelmalla.id,itinerario__gt=0).count()
                    #                 if asignatura_malla_itinerario == 1:
                    #                     # if not (int(f.cleaned_data['itinerario']) > 0 and MallaHorasSemanalesComponentes.objects.filter(status=True, malla_id = asignaturamalla.malla.id,nivelmalla_id = int(request.POST['nivel']),tiene_itinerario = True).exists()):
                    #                     ##RESTA DE HORAS ANTIGUAS
                    #                     registro_horas_semanales.acd_horassemanales -= horasacd_antiguas
                    #                     registro_horas_semanales.ape_aa_horassemanales -= horasape_antiguas + horas_autonomas_antiguas
                    #                     registro_horas_semanales.total_horassemanales -= horasacd_antiguas + horasape_antiguas + horas_autonomas_antiguas
                    #                     ##SUMA DE HORAS ACTUALIZADAS
                    #                     registro_horas_semanales.acd_horassemanales += round((f.cleaned_data['horasacdtotal']/16),1)
                    #                     registro_horas_semanales.ape_aa_horassemanales += round((f.cleaned_data['horasapetotal']/16),1) + round((f.cleaned_data['horasautonomas']/16),1)
                    #                     registro_horas_semanales.total_horassemanales += round((f.cleaned_data['horasacdtotal']/16),1) + round((f.cleaned_data['horasapetotal']/16),1) + round((f.cleaned_data['horasautonomas']/16),1)
                    #         asignatura_malla_itinerario = AsignaturaMalla.objects.filter(status=True, malla_id=asignaturamalla.malla.id, nivelmalla_id = int(request.POST['nivel']), itinerario__gt = 0).exclude(pk=int(encrypt(request.POST['id']))).exists()
                    #         if not asignatura_malla_itinerario:
                    #             if int(f.cleaned_data['itinerario']) > 0:
                    #                 registro_horas_semanales.tiene_itinerario = True
                    #             else:
                    #                 registro_horas_semanales.tiene_itinerario = False
                    #         # else:
                    #         #     registro_horas_semanales.acd_horassemanales -= round((f.cleaned_data['horasacdtotal']/16),1)
                    #         #     registro_horas_semanales.ape_aa_horassemanales -= round((f.cleaned_data['horasapetotal']/16),1) + round((f.cleaned_data['horasautonomas']/16),1)
                    #         #     registro_horas_semanales.total_horassemanales -= round((f.cleaned_data['horasacdtotal']/16),1) + round((f.cleaned_data['horasapetotal']/16),1) + round((f.cleaned_data['horasautonomas']/16),1)
                    #         registro_horas_semanales.save(request)
                    log(u'Modifico asignatura malla: %s' % asignaturamalla, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cambioasignatura':
            try:
                f = CambioAsignaturaMallaForm(request.POST)
                asignaturamalla = AsignaturaMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                if f.is_valid():

                    asignaturamalla.asignatura = f.cleaned_data['asignatura']
                    for mate in asignaturamalla.materia_set.filter(status=True):
                        mate.asignatura = f.cleaned_data['asignatura']
                        mate.save(request)

                    for recor in asignaturamalla.recordacademico_set.filter(status=True):
                        recor.asignatura = f.cleaned_data['asignatura']
                        recor.save(request)

                    for historirecor in asignaturamalla.historicorecordacademico_set.filter(status=True):
                        historirecor.asignatura = f.cleaned_data['asignatura']
                        historirecor.save(request)

                    asignaturamalla.save(request)
                    Materia.objects.filter(asignaturamalla=asignaturamalla, nivel__cerrado=False).update(horas=asignaturamalla.horas, creditos=asignaturamalla.creditos)
                    log(u'Modifico asignatura malla: %s' % asignaturamalla, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delrequisito':
            try:
                requisito = RequisitosMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Elimino requisito de malla: %s' % requisito, request, "del")
                requisito.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'deldetalleprocedimiento':
            try:
                detalle = ProcedimientoEvaluacionProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                detalle.status=False
                detalle.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delprocedimiento':
            try:
                cab = CabProcedimientoEvaluacionPa.objects.get(pk=int(request.POST['id']))
                cab.status=False
                cab.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delintegracioncurricular':
            try:
                requisito = RequisitoIngresoUnidadIntegracionCurricular.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Elimino requisito de integracion curricular de malla: %s' % requisito, request, "del")
                requisito.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delmodulo':
            try:
                modulo = ModuloMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Elimino asignatura modulo: %s' % modulo, request, "del")
                modulo.status=False
                modulo.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delete':
            try:
                malla = Malla.objects.get(pk=request.POST['id'])
                if malla.inscripcionmalla_set.exists():
                    return JsonResponse({"result": "bad", "mensaje": u"La malla se encuentra en uso."})
                log(u'Elimino malla: %s' % malla, request, "del")
                malla.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delarchivo':
            try:
                malla = Malla.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Elimino archivo en malla: nombre archivo (%s) - idmalla(%s)' % (malla.archivo, malla.id), request, "del")
                malla.archivo = None
                malla.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delarchivoproyecto':
            try:
                malla = Malla.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Elimino archivo de proyecto en malla: nombre archivo (%s) - idmalla(%s)' % (malla.archivo, malla.id), request, "del")
                malla.archivo_proyecto = None
                malla.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delarchivoproyectorediseñado':
            try:
                malla = Malla.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Elimino archivo de proyecto rediseñado en malla: nombre archivo (%s) - idmalla(%s)' % (malla.archivo_proyectorediseñado, malla.id), request, "del")
                malla.archivo_proyectorediseñado = None
                malla.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'tituloafin':
            try:
                titulos_seleccionados = json.loads(request.POST['lista_items1'])
                asignaturamalla = AsignaturaMalla.objects.get(pk=int(encrypt(request.POST['idasignaturamalla'])))
                AsignaturaMallaTituloAFin.objects.filter(status=True, asignaturamalla=asignaturamalla).delete()
                for d in titulos_seleccionados:
                    asignaturamallatituloafin = AsignaturaMallaTituloAFin(asignaturamalla = asignaturamalla,titulo_id = int(encrypt(d['id'])))
                    asignaturamallatituloafin.save(request)
                log(u'Edito Titulo a Fin en la Asignatura: %s' % asignaturamalla, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al editar los datos."})

        elif action == 'verdocente':
            try:
                data['materia'] = titulo = Titulo.objects.get(pk=request.POST['idtitulo'])
                data['title'] = u'Docentes'
                data['docentes'] = titulo.docentes()
                template = get_template("mallas/verdocente.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        elif action == 'duplicarprogramaanalitico':
            try:
                listapreguntas = request.POST['listapreguntas']
                programaanalitico = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['idprograma'])))
                for pregunta in listapreguntas.split(':'):
                    ingresoprogramaanalitico = ProgramaAnaliticoAsignatura(asignaturamalla_id=int(pregunta),
                                                                           descripcion=programaanalitico.descripcion,
                                                                           compromisos=programaanalitico.descripcion,
                                                                           caracterinvestigacion=programaanalitico.caracterinvestigacion,
                                                                           integranteuno=programaanalitico.integranteuno,
                                                                           integrantedos=programaanalitico.integrantedos,
                                                                           integrantetres=programaanalitico.integrantetres,
                                                                           activo=False,
                                                                           archivoconsejo =programaanalitico.archivoconsejo,
                                                                           archivocomision = programaanalitico.archivocomision,
                                                                           archivopafirma = programaanalitico.archivopafirma,
                                                                           actaempresa = programaanalitico.actaempresa,
                                                                           actagraduado =programaanalitico.actagraduado,
                                                                           actadocente = programaanalitico.actadocente,
                                                                           informebenchmarking = programaanalitico.informebenchmarking,
                                                                           informepractica = programaanalitico.informepractica,
                                                                           motivo=programaanalitico.motivo)
                    ingresoprogramaanalitico.save(request)
                    if BibliografiaProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura=programaanalitico,status=True).exists():
                        bibliografia = BibliografiaProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura=programaanalitico,status=True)
                        for biblio in bibliografia:
                            bibliografia = BibliografiaProgramaAnaliticoAsignatura(programaanaliticoasignatura=ingresoprogramaanalitico,
                                                                                   librokohaprogramaanaliticoasignatura=biblio.librokohaprogramaanaliticoasignatura)
                            bibliografia.save(request)
                    if ResultadoAprendizajeRai.objects.filter(programaanaliticoasignatura=programaanalitico,status=True).exists():
                        resultadorai = ResultadoAprendizajeRai.objects.filter(programaanaliticoasignatura=programaanalitico,status=True)
                        for resultado in resultadorai:
                            resulrai = ResultadoAprendizajeRai(programaanaliticoasignatura=ingresoprogramaanalitico,
                                                               descripcion=resultado.descripcion)
                            resulrai.save(request)
                    if ResultadoAprendizajeRac.objects.filter(programaanaliticoasignatura=programaanalitico,status=True).exists():
                        resultadorac = ResultadoAprendizajeRac.objects.filter(programaanaliticoasignatura=programaanalitico,status=True)
                        for resultado in resultadorac:
                            resulrac = ResultadoAprendizajeRac(programaanaliticoasignatura=ingresoprogramaanalitico,
                                                               descripcion=resultado.descripcion)
                            resulrac.save(request)
                    if ObjetivoProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura=programaanalitico,status=True).exists():
                        objetivo = ObjetivoProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura=programaanalitico,status=True)
                        for obje in objetivo:
                            objetivos = ObjetivoProgramaAnaliticoAsignatura(programaanaliticoasignatura=ingresoprogramaanalitico,
                                                                            descripcion=obje.descripcion)
                            objetivos.save(request)
                    if MetodologiaProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura=programaanalitico,status=True).exists():
                        metodologia = MetodologiaProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura=programaanalitico,status=True)
                        for resultado in metodologia:
                            metodologias = MetodologiaProgramaAnaliticoAsignatura(programaanaliticoasignatura=ingresoprogramaanalitico,
                                                                                  descripcion=resultado.descripcion)
                            metodologias.save(request)
                    if ContenidoResultadoProgramaAnalitico.objects.filter(programaanaliticoasignatura=programaanalitico,status=True).exists():
                        contenido = ContenidoResultadoProgramaAnalitico.objects.filter(programaanaliticoasignatura=programaanalitico,status=True)
                        for conte in contenido:
                            ingresocontenido = ContenidoResultadoProgramaAnalitico(programaanaliticoasignatura=ingresoprogramaanalitico,
                                                                                   descripcion=conte.descripcion,
                                                                                   orden=conte.orden)
                            ingresocontenido.save()
                            if UnidadResultadoProgramaAnalitico.objects.filter(contenidoresultadoprogramaanalitico=conte,status=True).exists():
                                unidad = UnidadResultadoProgramaAnalitico.objects.filter(contenidoresultadoprogramaanalitico=conte,status=True)
                                for uni in unidad:
                                    print(uni.descripcion)
                                    ingresounidad = UnidadResultadoProgramaAnalitico(
                                        contenidoresultadoprogramaanalitico=ingresocontenido,
                                        descripcion=uni.descripcion,
                                        orden=uni.orden)
                                    ingresounidad.save()
                                    if TemaUnidadResultadoProgramaAnalitico.objects.filter(unidadresultadoprogramaanalitico=uni,status=True).exists():
                                        tema = TemaUnidadResultadoProgramaAnalitico.objects.filter(unidadresultadoprogramaanalitico=uni,status=True)
                                        for tem in tema:
                                            print(tem.descripcion)
                                            ingresotema = TemaUnidadResultadoProgramaAnalitico(
                                                unidadresultadoprogramaanalitico=ingresounidad,
                                                descripcion=tem.descripcion,
                                                archivo=tem.archivo,
                                                orden=tem.orden)
                                            ingresotema.save()
                                            if SubtemaUnidadResultadoProgramaAnalitico.objects.filter(temaunidadresultadoprogramaanalitico=tem,status=True).exists():
                                                subtema = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(temaunidadresultadoprogramaanalitico=tem,status=True)
                                                for sub in subtema:
                                                    ingresosubtema = SubtemaUnidadResultadoProgramaAnalitico(
                                                        temaunidadresultadoprogramaanalitico=ingresotema,
                                                        descripcion=sub.descripcion,
                                                        contenido=sub.contenido,
                                                        orden=sub.orden)
                                                    ingresosubtema.save()

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'listamateriasmalla':
            try:
                programaanalitico = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['idprogramaanalitico'])))
                asignaturamalla = AsignaturaMalla.objects.filter(asignatura__nombre__icontains=programaanalitico.asignaturamalla.asignatura.nombre[0:10],status=True).exclude(pk=programaanalitico.asignaturamalla.id).order_by('-malla__carrera__nombre','asignatura__nombre')
                # cambio temporal, se debe borrar la funcion de elimniar tilde y dejar como antes (SE HA EJECUTADO ) POR JUSS

                # nombre = elimina_tildes(programaanalitico.asignaturamalla.asignatura.nombre[0:10])
                # nombre = elimina_tildes(programaanalitico.asignaturamalla.asignatura.nombre[0:7])

                # asignaturamalla = AsignaturaMalla.objects.filter(asignatura__nombre__icontains=nombre, status=True).exclude(pk=programaanalitico.asignaturamalla.id).order_by('-malla__carrera__nombre','asignatura__nombre')
                # preguntamaestria = PreguntaMaestria.objects.values_list('pregunta_id').filter(cohortes_id=idcohorte,status=True)
                # listapreguntas = PreguntasPrograma.objects.filter(status=True).exclude(pk__in=preguntamaestria).order_by('descripcion')
                lista = []
                for asig in asignaturamalla:
                    datadoc = {}
                    datadoc['id'] = asig.id
                    datadoc['descripcion'] = asig.asignatura.nombre
                    datadoc['malla'] = asig.malla.carrera.nombre
                    datadoc['nivel'] = asig.nivelmalla.nombre
                    datadoc['fechaaprobacion'] = asig.malla.inicio
                    lista.append(datadoc)
                return JsonResponse({'result': 'ok','lista':lista,'asignatura':'COPIAR: '+programaanalitico.asignaturamalla.asignatura.nombre })
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        #         Malla con diferente nombre
        elif action == 'listamateriasmalladif':
            try:
                term = request.POST['term']
                programaanalitico = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['idprogramaanalitico'])))
                search = term.strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    asignaturamalla = AsignaturaMalla.objects.filter(Q(status=True),
                                                                     Q(asignatura__nombre__icontains=search) | Q(
                                                                         malla__carrera__nombre__icontains=search)).exclude(
                        pk=programaanalitico.asignaturamalla.id).order_by('-malla__carrera__nombre',
                                                                          'asignatura__nombre')[0:100]
                else:
                    asignaturamalla = AsignaturaMalla.objects.filter(Q(status=True),
                                                                     Q(asignatura__nombre__icontains=ss[0]), Q(
                            malla__carrera__nombre__icontains=ss[1])).exclude(
                        pk=programaanalitico.asignaturamalla.id).order_by('-malla__carrera__nombre',
                                                                          'asignatura__nombre')[0:100]

                data = []
                for asig in asignaturamalla:
                    text = '{}  -  {} --- {}  - {} '.format(asig.asignatura.nombre, asig.nivelmalla.nombre, asig.malla.carrera.nombre, asig.malla.inicio)
                    data.append({'id': asig.id, 'text': text})
                return JsonResponse(data, safe=False)
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'duplicar_programaanalitico':
            try:
                programa = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['id'])))
                proanalitico = ProgramaAnaliticoAsignatura(asignaturamalla=programa.asignaturamalla,
                                                           descripcion=programa.descripcion,
                                                           compromisos=programa.compromisos,
                                                           integranteuno=programa.integranteuno,
                                                           integrantedos=programa.integrantedos,
                                                           integrantetres=programa.integrantetres,
                                                           activo=False)
                proanalitico.save(request)
                if programa.resultadoaprendizajerai_set.filter(status=True).exists():
                    rai = programa.resultadoaprendizajerai_set.filter(status = True)[0]
                    ri = ResultadoAprendizajeRai(programaanaliticoasignatura=proanalitico,descripcion=rai.descripcion)
                    ri.save(request)
                if programa.resultadoaprendizajerac_set.filter(status=True).exists():
                    rac = programa.resultadoaprendizajerac_set.filter(status=True)[0]
                    rc = ResultadoAprendizajeRac(programaanaliticoasignatura=proanalitico,descripcion=rac.descripcion)
                    rc.save(request)
                if programa.objetivoprogramaanaliticoasignatura_set.filter(status=True).exists():
                    obj = programa.objetivoprogramaanaliticoasignatura_set.filter(status=True)[0]
                    objt = ObjetivoProgramaAnaliticoAsignatura(programaanaliticoasignatura=proanalitico,descripcion=obj.descripcion)
                    objt.save(request)
                if programa.metodologiaprogramaanaliticoasignatura_set.filter(status=True).exists():
                    met = programa.metodologiaprogramaanaliticoasignatura_set.filter(status=True)[0]
                    mt = MetodologiaProgramaAnaliticoAsignatura(programaanaliticoasignatura=proanalitico,descripcion=met.descripcion)
                    mt.save(request)
                if programa.bibliografiaprogramaanaliticoasignatura_set.filter(status=True).exists():
                    for bli in programa.bibliografiaprogramaanaliticoasignatura_set.filter(status=True):
                        blio = BibliografiaProgramaAnaliticoAsignatura(programaanaliticoasignatura=proanalitico,librokohaprogramaanaliticoasignatura=bli.librokohaprogramaanaliticoasignatura)
                        blio.save(request)
                if programa.contenidoresultadoprogramaanalitico_set.filter(status=True).exists():
                    for cont in programa.contenidoresultadoprogramaanalitico_set.filter(status=True):
                        con = ContenidoResultadoProgramaAnalitico(programaanaliticoasignatura=proanalitico,descripcion=cont.descripcion,orden=cont.orden)
                        con.save(request)
                        if cont.unidadresultadoprogramaanalitico_set.filter(status=True).exists():
                            for uni in cont.unidadresultadoprogramaanalitico_set.filter(status=True):
                                un = UnidadResultadoProgramaAnalitico(contenidoresultadoprogramaanalitico=con,descripcion=uni.descripcion,orden=uni.orden)
                                un.save(request)
                                if uni.temaunidadresultadoprogramaanalitico_set.filter(status=True).exists():
                                    for tem in uni.temaunidadresultadoprogramaanalitico_set.filter(status=True):
                                        t = TemaUnidadResultadoProgramaAnalitico(unidadresultadoprogramaanalitico=un,descripcion=tem.descripcion,orden=tem.orden)
                                        t.save(request)
                                        if tem.subtemaunidadresultadoprogramaanalitico_set.filter(status=True).exists():
                                            for sub in tem.subtemaunidadresultadoprogramaanalitico_set.filter(status=True):
                                                s = SubtemaUnidadResultadoProgramaAnalitico(temaunidadresultadoprogramaanalitico=t,descripcion=sub.descripcion,orden=sub.orden)
                                                s.save(request)
                log(u'Duplico el Programa Analitíco %s al Programa Analitíco: %s' % (programa, proanalitico), request, "dupl")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delprogramaanalitico':
            try:
                programa = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['id'])))
                bib = programa.bibliografiaprogramaanaliticoasignatura_set.all()
                bib.delete()
                rc = programa.resultadoaprendizajerac_set.all()
                rc.delete()
                ri = programa.resultadoaprendizajerai_set.all()
                ri.delete()
                ob = programa.objetivoprogramaanaliticoasignatura_set.all()
                ob.delete()
                me = programa.metodologiaprogramaanaliticoasignatura_set.all()
                me.delete()
                if programa.contenidoresultadoprogramaanalitico_set.all().exists():
                    con = programa.contenidoresultadoprogramaanalitico_set.all()
                    if con:
                        uni = UnidadResultadoProgramaAnalitico.objects.filter(contenidoresultadoprogramaanalitico__in=con)
                        if uni:
                            tem = TemaUnidadResultadoProgramaAnalitico.objects.filter(unidadresultadoprogramaanalitico__in=uni)
                            if tem:
                                sub = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(temaunidadresultadoprogramaanalitico__in=tem)
                                sub.delete()
                                tem.delete()
                            uni.delete()
                        con.delete()
                log(u'Eliminó el Programa Analitíco: %s de la asignatura: %s fecha de creació: %s' % (programa, programa.asignaturamalla, programa.fecha_creacion), request,"del")
                programa.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delprogramaanaliticoposgrado':
            try:
                programa = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['id'])))
                bib = programa.bibliografiaprogramaanaliticoasignatura_set.all()
                bib.delete()
                rc = programa.resultadoaprendizajerac_set.all()
                rc.delete()
                ri = programa.resultadoaprendizajerai_set.all()
                ri.delete()
                ob = programa.objetivoprogramaanaliticoasignatura_set.all()
                ob.delete()
                me = programa.metodologiaprogramaanaliticoasignatura_set.all()
                me.delete()
                if programa.contenidoresultadoprogramaanalitico_set.all().exists():
                    con = programa.contenidoresultadoprogramaanalitico_set.all()
                    if con:
                        uni = UnidadResultadoProgramaAnalitico.objects.filter(contenidoresultadoprogramaanalitico__in=con)
                        if uni:
                            tem = TemaUnidadResultadoProgramaAnalitico.objects.filter(unidadresultadoprogramaanalitico__in=uni)
                            if tem:
                                sub = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(temaunidadresultadoprogramaanalitico__in=tem)
                                sub.delete()
                                tem.delete()
                            uni.delete()
                        con.delete()
                log(u'Eliminó el Programa Analitíco: %s de la asignatura: %s fecha de creació: %s' % (programa, programa.asignaturamalla, programa.fecha_creacion), request,"del")
                programa.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addsolicitudlibro':
            try:
                programa = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['id'])))
                f = SolicitudCompraLibroForm(request.POST)
                if f.is_valid():
                    solicitud = SolicitudCompraLibro(programa=programa,
                                                     nombre=f.cleaned_data['nombre'],
                                                     autor=f.cleaned_data['autor'],
                                                     aniopublicacion=f.cleaned_data['aniopublicacion'],
                                                     editorial=f.cleaned_data['editorial'],
                                                     cantidad=f.cleaned_data['cantidad'],
                                                     fecha=datetime.now(),
                                                     estadosolicitud=1,
                                                     persona=persona)
                    solicitud.save(request)
                    solicitud.email_notificacion_solicitud_libro(request.session['nombresistema'])
                    log(u'Adiciono una solicitud de adquisición de libro %s para progrma analítico de la asignatura malla: %s la persona %s' % (solicitud, solicitud.programa.asignaturamalla.asignatura, persona), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editsolicitudlibro':
            try:
                f = SolicitudCompraLibroForm(request.POST)
                if f.is_valid():
                    solicitud = SolicitudCompraLibro.objects.get(pk=int(encrypt(request.POST['id'])))
                    if not solicitud.programa.solicitudcompralibro_set.filter(nombre=f.cleaned_data['nombre'], estadosolicitud=1, status=True).exclude(pk=solicitud.id):
                        solicitud.nombre=f.cleaned_data['nombre']
                        solicitud.autor=f.cleaned_data['autor']
                        solicitud.aniopublicacion=f.cleaned_data['aniopublicacion']
                        solicitud.editorial=f.cleaned_data['editorial']
                        solicitud.cantidad=f.cleaned_data['cantidad']
                        solicitud.estadosolicitud=1
                        solicitud.save(request)
                        log(u'Adiciono una solicitud de adquisición de libro %s para progrma analítico de la asignatura: %s la persona %s' % (solicitud, solicitud.programa.asignaturamalla.asignatura, persona), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise JsonResponse({"result": "bad", "mensaje": u"El libro ya se encuentra solicitado."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delsolicitudlibro':
            try:
                solicitud = SolicitudCompraLibro.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Adiciono una solicitud de adquisición de libro %s para programa analítico de la asignatura malla: %s la persona %s' % (solicitud, solicitud.programa.asignaturamalla.asignatura, persona), request, "del")
                solicitud.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addapa':
            try:
                form = BibliografiaApaProgramaAnaliticoAsignaturaForm(request.POST)
                if form.is_valid():
                    bibliografia = BibliografiaApaProgramaAnaliticoAsignatura(programaanaliticoasignatura_id=int(encrypt(request.POST['id'])), bibliografia=form.cleaned_data['bibliografia'])
                    bibliografia.save(request)
                    log(u'Adicionó una Bibliografía: %s Apa al programa analítico: %s de la asignatura malla: %s la persona %s' % (bibliografia, bibliografia.programaanaliticoasignatura, bibliografia.programaanaliticoasignatura.asignaturamalla, persona), request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editapa':
            try:
                form = BibliografiaApaProgramaAnaliticoAsignaturaForm(request.POST)
                if 'id' in request.POST and 'idp' in request.POST:
                    if BibliografiaApaProgramaAnaliticoAsignatura.objects.filter(status=True, programaanaliticoasignatura_id=int(encrypt(request.POST['idp'])), id=int(encrypt(request.POST['id']))).exists():
                        bibliografia = BibliografiaApaProgramaAnaliticoAsignatura.objects.get(status=True, programaanaliticoasignatura_id=int(encrypt(request.POST['idp'])), id=int(encrypt(request.POST['id'])))
                        if form.is_valid():
                            bibliografia.bibliografia=form.cleaned_data['bibliografia']
                            bibliografia.save(request)
                            log(u'Editó la Bibliografía: %s Apa al programa analítico: %s de la asignatura malla: %s la persona %s' % (bibliografia, bibliografia.programaanaliticoasignatura, bibliografia.programaanaliticoasignatura.asignaturamalla, persona), request, "del")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delapa':
            try:
                bibliografia = BibliografiaApaProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Eliminó la Bibliografía: %s Apa al programa analítico: %s de la asignatura malla: %s la persona %s' % (bibliografia, bibliografia.programaanaliticoasignatura, bibliografia.programaanaliticoasignatura.asignaturamalla, persona), request, "del")
                bibliografia.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'relacionarcarrera':
            try:
                form = AutorprogramaAnaliticoForm(request.POST)
                if form.is_valid():
                    if not request.POST['autor']:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe ingresar el autor de la asignatura."})
                    pro = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.POST['id'])))
                    if not AutorprogramaAnalitico.objects.filter(programaanalitico=pro).exists():
                        autor = AutorprogramaAnalitico(autor_id=int(request.POST['autor']),
                                                       asignatura=pro.asignaturamalla.asignatura,
                                                       programaanalitico=pro,
                                                       periodo=periodo)
                        autor.save(request)
                    else:
                        autor = AutorprogramaAnalitico.objects.filter(status=True, periodo=periodo, programaanalitico=pro)[0]
                        autor.autor_id=int(request.POST['autor'])
                    autor.programaanaliticorelacion.clear()
                    for data in form.cleaned_data['programa']:
                        autor.programaanaliticorelacion.add(data)
                    autor.save()
                    log(u'Relacionó  el programa analitico %s' % (autor), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'imprimirmalla':
            try:
                __author__ = 'Unemi'
                title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet("HOJA1", cell_overwrite_ok=True)
                ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=reportes' + random.randint(1, 10000).__str__() + '.xls'
                columns = [
                    (u"No.", 1000),
                    (u"CARRERA", 9000),
                    (u"NIVEL", 6000),
                    (u"ASIGNATURA", 6000),
                    (u"CÓDIGO ASIGNATURA", 6000),
                    (u"HORAS TOTALES", 3000),
                    (u"Horas ACD Virtuales Semanales", 3000),
                    (u"Horas Aprendizaje Contacto Docente Semanales", 3000),
                    (u"Horas ACD Virtuales Totales", 3000),
                    (u"Horas Aprendizaje Contacto Docente (ACD) Totales", 3000),
                    (u"Creditos", 3000),
                    (u"Horas ACD Presenciales Totales", 3000),
                    (u"Horas ACD Presenciales Semanales", 3000),
                    (u"Horas Aprendizaje Práctico Experimental(APE) Totales", 3000),
                    (u"Horas Aprendizaje Práctico Experimental Semanales", 3000),
                    (u"Horas APE asistidas Totales", 3000),
                    (u"Horas APE asistidas Semanales", 3000),
                    (u"Horas APE no asistidas Totales", 3000),
                    (u"Horas APE no asistidas Semanales", 3000),
                    (u"Horas Aprendizaje Autónomo(AA) Totales", 3000),
                    (u"Horas Aprendizaje Autónomo Semanales", 3000),
                    (u"Horas Vinculación Totales", 3000),
                    (u"Horas Vinculación Semanales", 3000),
                    (u"Horas Prácticas Pre-profesionales Totales", 3000),
                    (u"Horas Prácticas Pre-profesionales semanales", 3000),
                    (u"Uso en el periodo", 6000),
                    (u"No título a fin", 3000),
                    (u"Mod. Impartición Clase", 4000),
                    (u"Cant. Asig. Presencial", 3000),
                    (u"Cant. Asig. Virtual", 3000),
                    (u"Tot. Hrs. Malla(sin PPP)", 3000),
                    (u"Tot. Hrs. Presencial", 3000),
                    (u"Tot. Hrs. Virtual", 3000),
                    (u"Tot. % Hrs. Virtual", 3000),
                    (u"Tot. % Hrs. Virtual", 3000),
                    (u"Malla Cerrada", 3000),
                ]
                row_num = 6
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                date_format = xlwt.XFStyle()
                date_format.num_format_str = 'yyyy/mm/dd'
                row_num = 7
                i = 0
                coordinaciones = Coordinacion.objects.filter(carrera__in=miscarreras).distinct()
                codigoscarrera = coordinaciones.values_list('carrera__id', flat=True).filter(status=True)
                coordinacionselect = nivelselect = modalidadcarreraselect = anioselect = carreraselect = 0
                if 'c' in request.POST:
                    coordinacionselect = int(request.POST['c'])
                if 'n' in request.POST:
                    nivelselect = int(request.POST['n'])
                if 'mc' in request.POST:
                    modalidadcarreraselect = int(request.POST['mc'])
                if 'a' in request.POST:
                    anioselect = int(request.POST['a'])
                if 'carr' in request.POST:
                    carreraselect = int(request.POST['carr'])
                malla = Malla.objects.filter(status=True, carrera__in=miscarreras).exclude(carrera__id=177).distinct().order_by('carrera__coordinacion__nombre', 'modalidad', '-inicio')
                if modalidadcarreraselect > 0:
                    malla = malla.filter(modalidad_id=modalidadcarreraselect)
                    codigoscarrera = malla.values_list('carrera__id', flat=True).filter(status=True)
                if anioselect > 0:
                    malla = malla.filter(inicio__year=anioselect)
                    codigoscarrera = malla.values_list('carrera__id', flat=True).filter(status=True)
                if coordinacionselect > 0:
                    malla = malla.filter(carrera__coordinacion__id=coordinacionselect)
                    codigoscarrera = malla.values_list('carrera__id', flat=True).filter(status=True)
                if nivelselect > 0:
                    malla = malla.filter(carrera__niveltitulacion__id=nivelselect)
                    codigoscarrera = malla.values_list('carrera__id', flat=True).filter(status=True)
                if carreraselect > 0:
                    malla = malla.filter(carrera_id=carreraselect)


                for detalle in malla:
                    campo1 = i
                    campo2 = str(detalle.carrera)
                    if detalle.carrera.mi_coordinacion2() == 1 or detalle.carrera.mi_coordinacion2() == 2 or detalle.carrera.mi_coordinacion2() == 3 or detalle.carrera.mi_coordinacion2() == 4  or detalle.carrera.mi_coordinacion2() == 5 :
                        campo36= u"%s"%("CERRADA" if detalle.cerrado==True else "ABIERTA")
                        ws.write(row_num, 35, campo36, font_style2)
                        if detalle.carrera.modalidad == 1 or detalle.carrera.id == 187:
                            campo29 = str(detalle.cantidad_total_materias_presenciales())
                            ws.write(row_num, 28, campo29, font_style2)
                            campo30 = str(detalle.cantidad_total_materias_virtuales())
                            ws.write(row_num, 29, campo30, font_style2)
                            campo31 = str(detalle.suma_horas_validacion_itinerario_sin_practica())
                            ws.write(row_num, 30, campo31, font_style2)
                            campo32 = str(detalle.suma_horas_materias_presenciales())
                            ws.write(row_num, 31, campo32, font_style2)
                            campo33 = str(detalle.suma_horas_materias_virtuales())
                            ws.write(row_num, 32, campo33, font_style2)
                            campo34 = str(detalle.porcentaje_horasp())
                            ws.write(row_num, 33, campo34 +'%', font_style2)
                            campo35 = str(detalle.porcentaje_horasv())
                            ws.write(row_num, 34, campo35 +'%', font_style2)

                    for asignatura in detalle.asignaturamalla_set.filter(status=True):
                        i += 1
                        campo3 = str(asignatura.nivelmalla)
                        campo4 = str(asignatura.asignatura.nombre)
                        campo5 = str(asignatura.asignatura.codigo)
                        campo6 = str(asignatura.horas)
                        campo7 = str(asignatura.horasvirtualsemanal)
                        campo8 = str(asignatura.horasacdsemanal)
                        campo9 = str(asignatura.horasvirtualtotal)
                        campo10 = str(asignatura.horasacdtotal)
                        campo11 = str(asignatura.creditos)

                        campo12 = str(asignatura.horaspresenciales)
                        campo13 = str(asignatura.horaspresencialessemanales)
                        campo14 = str(asignatura.horasapetotal)
                        campo15 = str(asignatura.horasapesemanal)
                        campo16 = str(asignatura.horasapeasistotal)
                        campo17 = str(asignatura.horasapeasissemanal)
                        campo18 = str(asignatura.horasapeautototal)
                        campo19 = str(asignatura.horasapeautosemanal)
                        campo20 = str(asignatura.horasautonomas)
                        campo21 = str(asignatura.horasautonomassemanales)
                        campo22 = str(asignatura.horasvinculaciontotal)
                        campo23 = str(asignatura.horasvinculacionsemanal)
                        campo24 = str(asignatura.horasppptotal)
                        campo25 = str(asignatura.horaspppsemanal)
                        campo26 = u"%s"%(periodo if detalle.uso_en_periodo(periodo) else "No esta siendo usado en el periodo seleccionado.")
                        campo27 = str(asignatura.contar_asignaturamallatituloafin())
                        # campo28 = str(asignatura.modalidad())
                        campo28 = u"%s"%("PRESENCIAL" if asignatura.modalidad() else "VIRTUAL")
                        campo36 = u"%s" % ("CERRADA" if asignatura.malla.cerrado == True else "ABIERTA")


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
                        ws.write(row_num, 16, campo17, font_style2)
                        ws.write(row_num, 17, campo18, font_style2)
                        ws.write(row_num, 18, campo19, font_style2)
                        ws.write(row_num, 19, campo20, font_style2)
                        ws.write(row_num, 20, campo21, font_style2)
                        ws.write(row_num, 21, campo22, font_style2)
                        ws.write(row_num, 22, campo23, font_style2)
                        ws.write(row_num, 23, campo24, font_style2)
                        ws.write(row_num, 24, campo25, font_style2)
                        ws.write(row_num, 25, campo26, font_style2)
                        ws.write(row_num, 26, campo27, font_style2)
                        ws.write(row_num, 27, campo28, font_style2)
                        ws.write(row_num, 35, campo36, font_style2)
                        # ws.write(row_num, 28, campo29, font_style2)
                        row_num += 1
                wb.save(response)
                return response
            except Exception as ex:
                pass

        elif action == 'imprimirmallapresencial':
            try:
                __author__ = 'Unemi'
                title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet("HOJA1", cell_overwrite_ok=True)
                ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=reportes' + random.randint(1, 10000).__str__() + '.xls'
                columns = [
                    (u"No.", 1000),
                    (u"CARRERA", 9000),
                    (u"NIVEL", 6000),
                    (u"ASIGNATURA", 6000),
                    (u"CÓDIGO ASIGNATURA", 6000),
                    (u"HORAS TOTALES", 3000),
                    (u"Horas ACD Virtuales Semanales", 3000),
                    (u"Horas Aprendizaje Contacto Docente Semanales", 3000),
                    (u"Horas ACD Virtuales Totales", 3000),
                    (u"Horas Aprendizaje Contacto Docente (ACD) Totales", 3000),
                    (u"Creditos", 3000),
                    (u"Horas ACD Presenciales Totales", 3000),
                    (u"Horas ACD Presenciales Semanales", 3000),
                    (u"Horas Aprendizaje Práctico Experimental(APE) Totales", 3000),
                    (u"Horas Aprendizaje Práctico Experimental Semanales", 3000),
                    (u"Horas APE asistidas Totales", 3000),
                    (u"Horas APE asistidas Semanales", 3000),
                    (u"Horas APE no asistidas Totales", 3000),
                    (u"Horas APE no asistidas Semanales", 3000),
                    (u"Horas Aprendizaje Autónomo(AA) Totales", 3000),
                    (u"Horas Aprendizaje Autónomo Semanales", 3000),
                    (u"Horas Vinculación Totales", 3000),
                    (u"Horas Vinculación Semanales", 3000),
                    (u"Horas Prácticas Pre-profesionales Totales", 3000),
                    (u"Horas Prácticas Pre-profesionales semanales", 3000),
                    (u"Uso en el periodo", 6000),
                    (u"No título a fin", 3000),
                    (u"Mod. Impartición Clase", 4000),
                    (u"Cant. Asig. Presencial", 3000),
                    (u"Cant. Asig. Virtual", 3000),
                    (u"Tot. Hrs. Malla(sin PPP)", 3000),
                    (u"Tot. Hrs. Presencial", 3000),
                    (u"Tot. Hrs. Virtual", 3000),
                    (u"Tot. % Hrs. Virtual", 3000),
                    (u"Tot. % Hrs. Virtual", 3000),
                    (u"Malla Cerrada", 3000),
                ]
                row_num = 6
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                date_format = xlwt.XFStyle()
                date_format.num_format_str = 'yyyy/mm/dd'
                row_num = 7
                i = 0
                malla = Malla.objects.filter(status=True, carrera__in=miscarreras, modalidad_id=1).exclude(carrera__id=177).distinct().order_by('carrera__coordinacion__nombre', 'modalidad', '-inicio')

                for detalle in malla:
                    campo1 = i
                    campo2 = str(detalle.carrera)
                    if detalle.carrera.mi_coordinacion2() == 1 or detalle.carrera.mi_coordinacion2() == 2 or detalle.carrera.mi_coordinacion2() == 3 or detalle.carrera.mi_coordinacion2() == 4  or detalle.carrera.mi_coordinacion2() == 5 :
                        campo36 = u"%s" % ("CERRADA" if detalle.cerrado == True else "ABIERTA")
                        ws.write(row_num, 35, campo36, font_style2)
                        if detalle.carrera.modalidad == 1 or detalle.carrera.id == 187:
                            campo29 = str(detalle.cantidad_total_materias_presenciales())
                            ws.write(row_num, 28, campo29, font_style2)
                            campo30 = str(detalle.cantidad_total_materias_virtuales())
                            ws.write(row_num, 29, campo30, font_style2)
                            campo31 = str(detalle.suma_horas_validacion_itinerario_sin_practica())
                            ws.write(row_num, 30, campo31, font_style2)
                            campo32 = str(detalle.suma_horas_materias_presenciales())
                            ws.write(row_num, 31, campo32, font_style2)
                            campo33 = str(detalle.suma_horas_materias_virtuales())
                            ws.write(row_num, 32, campo33, font_style2)
                            campo34 = str(detalle.porcentaje_horasp())
                            ws.write(row_num, 33, campo34 +'%', font_style2)
                            campo35 = str(detalle.porcentaje_horasv())
                            ws.write(row_num, 34, campo35 +'%', font_style2)

                    for asignatura in detalle.asignaturamalla_set.filter(status=True):
                        i += 1
                        campo3 = str(asignatura.nivelmalla)
                        campo4 = str(asignatura.asignatura.nombre)
                        campo5 = str(asignatura.asignatura.codigo)
                        campo6 = str(asignatura.horas)
                        campo7 = str(asignatura.horasvirtualsemanal)
                        campo8 = str(asignatura.horasacdsemanal)
                        campo9 = str(asignatura.horasvirtualtotal)
                        campo10 = str(asignatura.horasacdtotal)
                        campo11 = str(asignatura.creditos)

                        campo12 = str(asignatura.horaspresenciales)
                        campo13 = str(asignatura.horaspresencialessemanales)
                        campo14 = str(asignatura.horasapetotal)
                        campo15 = str(asignatura.horasapesemanal)
                        campo16 = str(asignatura.horasapeasistotal)
                        campo17 = str(asignatura.horasapeasissemanal)
                        campo18 = str(asignatura.horasapeautototal)
                        campo19 = str(asignatura.horasapeautosemanal)
                        campo20 = str(asignatura.horasautonomas)
                        campo21 = str(asignatura.horasautonomassemanales)
                        campo22 = str(asignatura.horasvinculaciontotal)
                        campo23 = str(asignatura.horasvinculacionsemanal)
                        campo24 = str(asignatura.horasppptotal)
                        campo25 = str(asignatura.horaspppsemanal)
                        campo26 = u"%s"%(periodo if detalle.uso_en_periodo(periodo) else "No esta siendo usado en el periodo seleccionado.")
                        campo27 = str(asignatura.contar_asignaturamallatituloafin())
                        # campo28 = str(asignatura.modalidad())
                        campo28 = u"%s"%("PRESENCIAL" if asignatura.modalidad() else "VIRTUAL")
                        campo36 = u"%s" % ("CERRADA" if asignatura.malla.cerrado == True else "ABIERTA")


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
                        ws.write(row_num, 16, campo17, font_style2)
                        ws.write(row_num, 17, campo18, font_style2)
                        ws.write(row_num, 18, campo19, font_style2)
                        ws.write(row_num, 19, campo20, font_style2)
                        ws.write(row_num, 20, campo21, font_style2)
                        ws.write(row_num, 21, campo22, font_style2)
                        ws.write(row_num, 22, campo23, font_style2)
                        ws.write(row_num, 23, campo24, font_style2)
                        ws.write(row_num, 24, campo25, font_style2)
                        ws.write(row_num, 25, campo26, font_style2)
                        ws.write(row_num, 26, campo27, font_style2)
                        ws.write(row_num, 27, campo28, font_style2)
                        ws.write(row_num, 35, campo36, font_style2)
                        # ws.write(row_num, 28, campo29, font_style2)
                        row_num += 1
                wb.save(response)
                return response
            except Exception as ex:
                pass

        if action == 'addparticipantes':
            try:
                idhorariovirtual = request.POST['idhorariovirtual']
                for lista in request.POST['listamatriculados'].split(','):
                    participantes = ParticipantesHorarioVirtual(horariovirtual_id=idhorariovirtual,
                                                                matricula_id=lista)
                    participantes.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addhorarioturno':
            try:
                horariovirtual = HorarioVirtual(laboratorio_id=request.POST['idlaboratorio'],
                                                malla_id=int(encrypt(request.POST['idmalla'])),
                                                nivel_id=request.POST['idnivel'],
                                                tipo=request.POST['idtipohorario'],
                                                periodo=periodo)
                horariovirtual.save(request)
                for lista in request.POST['listahorarios'].split(','):
                    cadena = lista.split('_')
                    fecha = cadena[0]
                    codigoturno = cadena[1]
                    codigoasignatura = cadena[2]
                    detalle = DetalleHorarioVirtual(horariovirtual=horariovirtual,
                                                    fecha=fecha,
                                                    turno_id=codigoturno,
                                                    asignatura_id=codigoasignatura)
                    detalle.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delparticipante':
            try:
                participante = ParticipantesHorarioVirtual.objects.get(pk=int(encrypt(request.POST['id'])))
                participante.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delturnohorario':
            try:
                horariovirtual = HorarioVirtual.objects.get(pk=int(encrypt(request.POST['id'])))
                horariovirtual.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'pdf_horarioexamen':
            try:
                data = {}
                data['fechaactual'] = datetime.now()
                data['detallehorario'] = detallehorario = DetalleHorarioVirtual.objects.get(pk=int(encrypt(request.POST['iddethorario'])))
                data['participantes'] = detallehorario.horariovirtual.participanteshorariovirtual_set.filter(status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                return conviert_html_to_pdf(
                    'mallas/pdf_horarioexamen.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        elif action == 'mecanismotitulacion':
            try:
                malla = Malla.objects.get(pk=request.POST['id'])
                form = MecanismoTitulacionPosgradoMallaForm(request.POST)
                if form.is_valid():
                    idmecanismos = malla.mecanismotitulacionposgradomalla_set.values_list('mecanismotitulacionposgrado_id', flat=True).filter(status=True)
                    if not TemaTitulacionPosgradoMatricula.objects.filter(matricula__inscripcion__inscripcionmalla__malla=malla, status=True,mecanismotitulacionposgrado_id__in=idmecanismos,mecanismotitulacionposgrado__status=True).exists():
                        malla.numerotutorias = form.cleaned_data['numerotutorias']
                        malla.save(request)
                        malla.mecanismotitulacionposgradomalla_set.all().delete()
                        datos = json.loads(request.POST['lista_items1'])
                        for elemento in datos:
                            mecanismotitulacionposgradomalla = MecanismoTitulacionPosgradoMalla(malla=malla,
                                                                                                mecanismotitulacionposgrado_id=int(elemento['id']))
                            mecanismotitulacionposgradomalla.save(request)
                            log(u'Actualizo mecanismo titulacion posgrado %s' % (mecanismotitulacionposgradomalla), request, "edit")
                    else:
                        malla.numerotutorias = form.cleaned_data['numerotutorias']
                        malla.save(request)
                        datos = json.loads(request.POST['lista_items1'])
                        for elemento in datos:
                            if not MecanismoTitulacionPosgradoMalla.objects.filter(malla=malla, mecanismotitulacionposgrado_id=int(elemento['id']), status=True).exists():
                                mecanismotitulacionposgradomalla = MecanismoTitulacionPosgradoMalla(malla=malla,
                                                                                                    mecanismotitulacionposgrado_id=int(elemento['id']))
                                mecanismotitulacionposgradomalla.save(request)
                                log(u'Actualizo mecanismo titulacion posgrado %s' % (mecanismotitulacionposgradomalla), request, "edit")
                        log(u'Actualizo numero tutorias malla %s' % (malla), request,"edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'additinerarioespecial':
            try:
                f = ItinerarioMallaEspecilidadForm(request.POST)
                if f.is_valid():
                    if ItinerarioMallaEspecilidad.objects.filter(status=True,malla_id=int(encrypt(request.POST['id'])), itinerario=f.cleaned_data['itinerario']).exists():
                        raise NameError('Ya existe un registro con el mismo itinerario')
                    if ItinerarioMallaEspecilidad.objects.values('id').filter(status=True,malla_id=int(encrypt(request.POST['id'])) ).count() >= 3:
                        raise NameError('Ya existen 3 registros de itinerarios para esta malla')
                    itinerarioespecial = ItinerarioMallaEspecilidad(malla_id=int(encrypt(request.POST['id'])),
                                                                    nombre=f.cleaned_data['nombre'],
                                                                    itinerario=f.cleaned_data['itinerario'],)
                    itinerarioespecial.save(request)
                    log(u'Adiciono itinerario de especialidad: %s' % itinerarioespecial, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s"%ex})

        elif action == 'edititinerarioespecial':
            try:
                f = ItinerarioMallaEspecilidadForm(request.POST)
                if f.is_valid():
                    itinerarioespecial = ItinerarioMallaEspecilidad.objects.get(pk=int(encrypt(request.POST['id'])))
                    if ItinerarioMallaEspecilidad.objects.filter(status=True, malla=itinerarioespecial.malla,
                                                                 itinerario=f.cleaned_data['itinerario']).exclude(
                        id=itinerarioespecial.id).exists():
                        raise NameError('Ya existe un registro con el mismo itinerario')
                    if ItinerarioMallaEspecilidad.objects.values('id').filter(status=True, malla_id=int(
                            encrypt(request.POST['id']))).exclude(id=itinerarioespecial.id).count() >= 3:
                        raise NameError('Ya existen 3 registros de itinerarios para esta malla')
                    itinerarioespecial.nombre = f.cleaned_data['nombre']
                    itinerarioespecial.itinerario = f.cleaned_data['itinerario']
                    itinerarioespecial.numeroresolucion = f.cleaned_data['numero']
                    itinerarioespecial.save(request)
                    log(u'Modifico itinerario de espcialidad: %s' % itinerarioespecial, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delitinerarioespecial':
            try:
                itinerarioespecial = ItinerarioMallaEspecilidad.objects.get(pk=int(encrypt(request.POST['id'])))
                itinerarioespecial.status = False
                itinerarioespecial.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'buscaritinerario':
            try:
                malla = Malla.objects.get(pk=int(request.POST['idmalla']))
                nombre=""
                itinerario=None
                if ItinerarioMallaEspecilidad.objects.values('id').filter(status=True,malla=malla,itinerario=int(request.POST['iditinerario'])).exists():
                    itinerario=ItinerarioMallaEspecilidad.objects.filter(status=True,malla=malla,itinerario=int(request.POST['iditinerario']))[0]
                return JsonResponse({"result": "ok","valor":itinerario.id if itinerario else 0})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'resumentotales':
            try:
                data['malla'] = Malla.objects.get(pk=request.POST['id'])
                template = get_template("mallas/resumentotales.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        elif action == 'horascomponentesnivel':
            try:
                data['listado'] = MallaHorasSemanalesComponentes.objects.filter(malla_id=request.POST['id'], status = True).order_by('nivelmalla__orden')
                template = get_template("mallas/horascomponentessemanal.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        elif action == 'cerrarmalla':
            try:
                malla = Malla.objects.get(pk=request.POST['id'])
                log(u'Cierra malla: %s' % malla, request, "edit")
                malla.cerrado=True
                malla.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'abrirmalla':
            try:
                malla = Malla.objects.get(pk=request.POST['id'])
                log(u'Abrir malla: %s' % malla, request, "edit")
                malla.cerrado=False
                malla.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addmodalidad':
            try:
                form=ModalidadForm(request.POST, request.FILES)
                registro=Modalidad()
                if form.is_valid():
                    if not Modalidad.objects.filter(nombre=request.POST['nombre'].upper(), status=True).exists():
                        registro.nombre = form.cleaned_data['nombre']
                        registro.autoinscripcion = form.cleaned_data['autoinscripcion']
                        registro.save(request)
                        log(u'Adicionar Modalidad: %s' % registro, request, "addmodalidad")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ingresado ya existe"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al adicionar el registro."})
            except Exception as ex:
                msg = str(ex)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al adicionar los datos."})

        elif action == 'editmodalidad':
            try:
                form = ModalidadForm(request.POST)
                modalidad=Modalidad.objects.get(pk=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    if not Modalidad.objects.filter(nombre=request.POST['nombre'].upper(), status=True).exclude(id=modalidad.pk).exists():
                        modalidad.nombre=form.cleaned_data['nombre']
                        modalidad.autoinscripcion = form.cleaned_data['autoinscripcion']
                        modalidad.save(request)
                        log(u'Edito Modalidad: %s' % modalidad, request, "editmodalidad")
                        return JsonResponse({"result":False}, safe=False)
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ingresado ya existe"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = str(ex)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'addasignatura':
            try:
                asignaturas = Asignatura.objects.filter(nombre=request.POST['nombre'].upper())
                if asignaturas.exists():
                    raise NameError('Ya existe una asignatura con ese mismo nombre')
                asignatura = Asignatura(nombre=request.POST['nombre'])
                asignatura.save(request)
                log(u'Adicionar Asignatura: %s' % asignatura, request, "addasignatura")
                return JsonResponse({"result": "ok", "asignatura": {"id": asignatura.id, "nombre": f'{asignatura.nombre} ({asignatura.id})'}}, safe=False)
            except Exception as ex:
                msg = str(ex)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: "+str(ex)})

        elif action == 'deletemodalidad':
            try:
                registro = Modalidad.objects.get(pk=request.POST['id'])
                if not registro.esta_en_malla():
                    registro.status = False
                    registro.save(request)
                    log(u'Elimino Modalidad: %s' % registro, request, "deletemodalidad")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar el registro por que ya se encuentra utilizado."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'cambiarasignatura':
            try:
                if not 'asigm' in request.POST:
                    raise NameError('No se existe el parámetro asigm')
                if not 'id' in request.POST:
                    raise NameError('No se existe el parámetro id')
                if not request.POST['id'].isdigit():
                    raise NameError('No es un código correcto el parámetro id')
                if not request.POST['asigm'].isdigit():
                    raise NameError('No es un código correcto el parámetro asigm')

                asignm = AsignaturaMalla.objects.get(pk=request.POST['asigm'])
                mimalla = asignm.malla
                asignaturasmimalla = AsignaturaMalla.objects.filter(malla=mimalla)
                asignaturanew = Asignatura.objects.get(pk=request.POST['id'])
                asignaturasmimalla = asignaturasmimalla.values_list('asignatura_id', flat=True)

                if asignaturanew.id in asignaturasmimalla:
                    raise NameError('La asignatura que estas  intentando cambiar ya se encuentra en la malla')

                records = RecordAcademico.objects.filter(asignaturamalla=asignm)
                if records.values('id').exists():
                    #log(u'Masivo de Record Academico: %s - Ejecuto persona: %s'% (", ".join([str(x.id) for x in records]), persona), request, "edit")
                    records.update(asignatura_id=asignaturanew.id, asignaturaold_id=asignm.asignatura.id)

                hisrecords = HistoricoRecordAcademico.objects.filter(asignaturamalla=asignm)
                if hisrecords.values('id').exists():
                    #log(u'Masivo de Historico Record Academico: %s - Ejecuto persona: %s' % (", ".join([str(x.id) for x in hisrecords]), persona), request, "edit")
                    hisrecords.update(asignatura_id=asignaturanew.id, asignaturaold_id=asignm.asignatura.id)

                materias = Materia.objects.filter(asignaturamalla=asignm)
                if materias.values('id').exists():
                    #log(u'Masivo de Materia: %s - Ejecuto persona: %s' % (", ".join([str(x.id) for x in materias]), persona), request, "edit")
                    materias.update(asignatura_id=asignaturanew.id, asignaturaold_id=asignm.asignatura.id)

                asignm.asignatura = asignaturanew
                asignm.asignaturaold = asignm.asignatura
                asignm.save(request)
                datajson = [{
                    'fecha': datetime.now().strftime('%Y%m%d_%H%M%S'),
                    'records': [x.id for x in records],
                    'materias': [x.id for x in materias],
                    'hitoricosrecors': [x.id for x in hisrecords],
                    'asignaturaold': asignm.asignaturaold.id,
                    'asignaturanew': asignm.asignatura.id,
                    'persona': {'id': persona.id, 'nombres': persona.__str__()}
                }]
                log(u'Masivo de Modificacion de la malla  %s, se Cambio Asignatura Malla: %s, Asignatura Antigua: %s por Asignatura: %s data afectada: %s' % (mimalla,  asignm, asignm.asignaturaold, asignm.asignatura, str(datajson)), request, "edit")
                mensaje = 'Cambio correctamente la asignatura'
                return JsonResponse({"result": True, "mensaje": mensaje}, safe=False)
            except Exception as ex:
                msg = str(ex)
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error: "+str(ex)})

        elif action == 'saveNombreCarrera':
            try:
                puede_realizar_accion(request, 'sga.puede_modificar_nombre_carrera')
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro parametro de carrera")
                if not Carrera.objects.filter(pk=request.POST['id']):
                    raise NameError(u"No se encontro la carrera a editar")
                eCarrera = Carrera.objects.get(pk=request.POST['id'])
                if not 'nombre' in request.POST:
                    raise NameError(u"No se encontro nombre de la carrera a editar")
                nombre = request.POST['nombre']
                eCarrera.nombrevisualizar = nombre
                eCarrera.save(request)
                log(u'Edito nombre de la Carrera: %s' % eCarrera, request, "edit")
                return JsonResponse({"result": "ok", "mensaje": u"Se edito correctamente el nombre de la carrera "})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al editar los datos. %s" % ex.__str__()})

        elif action == 'buscarmallas':
            try:
                item = []
                param = request.POST['term']
                modalidad=request.POST['modalidad']
                mallas = Malla.objects.filter(carrera__nombre__icontains=param,status=True, carrera__coordinacion__id__lte=5, modalidad=modalidad).exclude(id=int(request.POST['id']))
                for m in mallas:
                    text = str(m)
                    item.append({'id': m.id, 'text': text})
                return JsonResponse(item, safe=False)
            except Exception as ex:
                pass

        elif action == 'addhomologacionasignaturas':
            try:
                origen = AsignaturaMalla.objects.get(id=int(request.POST['id']))
                malladestino = Malla.objects.get(id=request.POST['idmalladestino'])
                lista=[]
                asignlist = []
                cont=0
                asignaturas = request.POST['ids'].split(',')
                for asignatura in asignaturas:
                    asignlist.append(asignatura)
                    cont += 1
                    if asignatura=='':
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Por favor llene todos los campos."})
                    if cont==3:
                        lista.append(asignlist)
                        cont=0
                        asignlist = []

                for asignaturadestino in lista:
                    if not HomologacionAsignatura.objects.filter(origen=origen, malladestino=malladestino, destino_id=int(asignaturadestino[0])).exists():
                        homologacion = HomologacionAsignatura(origen=origen,
                                                              malladestino=malladestino,
                                                              destino_id=int(asignaturadestino[0]),
                                                              calificacion=float(asignaturadestino[1]),
                                                              similitud=int(asignaturadestino[2]))
                        homologacion.save(request)
                    else:
                        homologacion = HomologacionAsignatura.objects.get(origen=origen, malladestino=malladestino, destino_id=int(asignaturadestino[0]))
                        if homologacion.status == False:
                            homologacion.status=True
                        homologacion.destino_id = asignaturadestino[0]
                        homologacion.calificacion = float(asignaturadestino[1])
                        homologacion.similitud = int(asignaturadestino[2])
                        homologacion.save(request)

                # if not HomologacionAsignatura.objects.filter(origen=origen, malladestino=destino).exists():
                #     homologacion = HomologacionAsignatura(origen=origen,
                #                                           malladestino=destino,)
                #     homologacion.save()
                # for asignaturadestino in lista:
                #     homologacion = HomologacionAsignatura.objects.get(origen=origen,
                #                                                       malladestino=destino)
                #     if not homologacion.status :
                #         homologacion.status=True
                #     asignatura=AsignaturaMalla.objects.get(id=asignaturadestino[0])
                #     homologacion.destino.add(asignatura)
                # homologacion.save(request)
                log(u'Adiciono asignaturas homolmologadas con de cambio de carrera: ', request,"add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'edithomologacionasignaturas':
            try:
                asignatura = HomologacionAsignatura.objects.get(origen=request.POST['origen'], malladestino=request.POST['malladestino'], destino_id=int(request.POST['id']))
                asignatura.calificacion = float(request.POST['calificacion'])
                asignatura.similitud = int(request.POST['similitud'])
                asignatura.save(request)
                log(u'Edito asignaturas de Homologacion de Asignaturas: %s' % asignatura.origen, request, "delete")
                return JsonResponse({"error": False})
            except Exception as e:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, 'mensaje': str(e)}, safe=False)

        elif action == 'deletehomologacionasignaturas':
            try:
                asignatura = HomologacionAsignatura.objects.get(origen=request.POST['origen'], malladestino=request.POST['malladestino'], destino_id=int(request.POST['id']))
                asignatura.status=False
                asignatura.save(request)
                # asignatura.destino.remove(AsignaturaMalla.objects.get(id=request.POST['id']))
                # if not asignatura.todas_asignaturasdestino():
                #     asignatura.status=False
                #     asignatura.save(request)
                log(u'Elimino asignaturas de Homologacion de Asignaturas: %s' % asignatura.origen, request, "delete")
                return JsonResponse({"error": False})
            except Exception as e:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, 'mensaje': str(e)}, safe=False)

        elif action == 'addunidadorganizacioncurricular':
            try:
                form = UnidadOrganizacionCurricularForm(request.POST, request.FILES)
                registro = UnidadOrganizacionCurricular()
                if form.is_valid():
                    if not UnidadOrganizacionCurricular.objects.filter(nombre=request.POST['nombre'].upper(), status=True).exists():
                        registro.nombre = form.cleaned_data['nombre']
                        registro.color = form.cleaned_data['color']
                        registro.save(request)
                        log(u'Adiciono Unidad Organizacional Curricular: %s' % registro, request, "add")
                        return JsonResponse({"result": True, "mensaje": u"Registro Guardado Correctamente"}, safe=False)
                    else:
                        return JsonResponse({"result": False, "mensaje": u"El nombre ingresado ya existe"})
                else:
                    return JsonResponse({"result":  False, "mensaje": u"Error al adicionar el registro."})
            except Exception as ex:
                msg = str(ex)
                transaction.set_rollback(True)
                return JsonResponse({"result":  False, "mensaje": u"Error al adicionar los datos."})

        elif action == 'editunidadorganizacioncurricular':
            try:
                form = UnidadOrganizacionCurricularForm(request.POST)
                modalidad = UnidadOrganizacionCurricular.objects.get(pk=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    if not Modalidad.objects.filter(nombre=request.POST['nombre'].upper(), status=True).exclude(id=modalidad.pk).exists():
                        modalidad.nombre = form.cleaned_data['nombre']
                        modalidad.color = form.cleaned_data['color']
                        modalidad.save(request)
                        log(u'Edito Unidad Organizacional Curricular: %s' % modalidad, request, "edit")

                        return JsonResponse({"result": True,  "mensaje": u"Registro Editado Correctamente"}, safe=False)
                    else:
                        return JsonResponse({"result": False, "mensaje": u"El nombre ingresado ya existe"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = str(ex)
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'deleteunidadorganizacioncurricular':
            try:
                registro = UnidadOrganizacionCurricular.objects.get(pk=int(encrypt(request.POST['id'])))
                if not registro.esta_en_asignaturamalla():
                    registro.status = False
                    registro.save(request)
                    log(u'Elimino Unidad Organizacional Curricular: %s' % registro, request, "del")
                    return JsonResponse({"result": True, "mensaje": u"Registro Eliminado Correctamente"})
                else:
                    return JsonResponse({"result": False, "mensaje": u"No se puede eliminar el registro por que ya se encuentra utilizado."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al eliminar los datos."})

        elif action == 'addarchivomalla':
            try:
                form = ArchivoMallasForm(request.POST,request.FILES)
                if form.is_valid():
                    mallaar = Malla.objects.get(pk=request.POST['id'])
                    newfile = request.FILES['archivo']
                    extension = newfile._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if newfile.size > 100194304:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {"result": 'bad', "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."},safe=False)
                    if not exte in ['pdf']:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": 'bad', "mensaje": u"Error, solo archivo .pdf"},safe=False)
                    if int(request.POST['tipo']) ==1:
                        if mallaar.archivo:
                            log('Edito el archivo resolucion de aprobacion del ces de la malla %s - id %s, archivo anterior %s archivo nuevo %s' % (mallaar, mallaar.id,mallaar.archivo.name,newfile), request, 'edit')
                        else:
                            log('Adiciono el archivo resolucion de aprobacion del ces de la malla %s - id %s, archivo %s' % (mallaar, mallaar.id,newfile), request, 'add')
                        mallaar.archivo = newfile
                    elif int(request.POST['tipo']) == 2:
                        if mallaar.archivo_proyecto:
                            log('Edito el archivo resolucion de aprobacion del ces de la malla %s - id %s, archivo anterior %s archivo nuevo %s' % (mallaar, mallaar.id,mallaar.archivo_proyecto.name,newfile), request, 'edit')
                        else:
                            log('Adiciono el archivo resolucion de aprobacion del ces de la malla %s - id %s, archivo %s' % (mallaar, mallaar.id,newfile), request, 'add')
                        mallaar.archivo_proyecto = newfile
                    else:
                        if mallaar.archivo_proyectorediseñado:
                            log('Edito el archivo resolucion de aprobacion del ces de la malla %s - id %s, archivo anterior %s archivo nuevo %s' % (mallaar, mallaar.id,mallaar.archivo_proyectorediseñado.name,newfile), request, 'edit')
                        else:
                            log('Adiciono el archivo resolucion de aprobacion del ces de la malla %s - id %s, archivo %s' % (mallaar, mallaar.id,newfile), request, 'add')
                        mallaar.archivo_proyectorediseñado = newfile
                    mallaar.save(request)
                    return JsonResponse({'result':'ok','mensaje':'Archivo guardado con éxito'},safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": u"Error al procesar los datos."},safe=False)

        elif action == 'importarrequisitos':
            try:
                idmalla = request.POST['idmalla']
                lista = request.POST['lista'].split(',')
                for elemento in lista:
                    if not RequisitoTitulacionMalla.objects.filter(requisito_id=elemento, malla_id=idmalla, status=True):
                        requisitomalla = RequisitoTitulacionMalla(requisito_id=elemento,
                                                                  malla_id=idmalla)
                        requisitomalla.save(request)
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleterequisitomalla':
            try:
                with transaction.atomic():
                    requisitomalla = RequisitoTitulacionMalla.objects.get(pk=int(request.POST['id']))
                    requisitomalla.delete()
                    log(u'elimino requisito malla: %s' % requisitomalla, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'estadoactivorequisitomalla':
            try:
                with transaction.atomic():
                    requisitomalla = RequisitoTitulacionMalla.objects.get(pk=int(request.POST['id']))
                    if requisitomalla.activo:
                        requisitomalla.activo = False
                    else:
                        requisitomalla.activo = True
                    requisitomalla.save(request)
                    log(u'cambio estado activo malla requisito titulacion: %s' % requisitomalla, request, "estadoactivar")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'estadoobligatoriorequisitomalla':
            try:
                with transaction.atomic():
                    requisitomalla = RequisitoTitulacionMalla.objects.get(pk=int(request.POST['id']))
                    if requisitomalla.obligatorio:
                        requisitomalla.obligatorio = False
                    else:
                        requisitomalla.obligatorio = True
                    requisitomalla.save(request)
                    log(u'cambio estado obligatorio requisito malla titulacion: %s' % requisitomalla, request, "estadoactivar")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addprocedimentoeva':
            try:
                f = CabProcedimietoEvaForm(request.POST)
                if f.is_valid():
                    cabproce = CabProcedimientoEvaluacionPa(descripcion=f.cleaned_data['descripcion'])
                    cabproce.save(request)
                    log(u'Adiciono cabecera procedimiento evaluacion: %s' % cabproce, request, "add")
                    return JsonResponse({"result": "ok"})
                return JsonResponse({'result': "bad", "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos." })

        elif action == 'editprocedimientoeva':
            try:
                form = CabProcedimietoEvaForm(request.POST)
                if form.is_valid():
                    proce = CabProcedimientoEvaluacionPa.objects.get(pk=int(request.POST['id']))
                    proce.descripcion = form.cleaned_data['descripcion']
                    proce.save(request)
                    log(u'Editar cabecera procedimiento evaluacion: %s - [%s]' % (proce,proce.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'adddetprocedimento':
            try:
                f = DetProcedimietoEvaForm(request.POST)
                if f.is_valid():
                    detproce = ProcedimientoEvaluacionProgramaAnalitico(cabprocedimiento_id = int(request.POST['cabprocedimiento']),
                                                                        referente = f.cleaned_data['referente'],
                                                                        porcentaje = f.cleaned_data['porcentaje'],
                                                                        calificacion = f.cleaned_data['calificacion'],
                                                                        descripcion = f.cleaned_data['descripcion'],
                                                                        articulo = f.cleaned_data['articulo'])
                    detproce.save(request)
                    log(u'Adiciono procedimiento evaluacion: %s' % detproce, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': "bad", "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos." })

        elif action == 'editdetalleproce':
            try:
                form = DetProcedimietoEvaForm(request.POST)
                if form.is_valid():
                    detp = ProcedimientoEvaluacionProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                    detp.referente = form.cleaned_data['referente']
                    detp.porcentaje = form.cleaned_data['porcentaje']
                    detp.calificacion = form.cleaned_data['calificacion']
                    detp.descripcion = form.cleaned_data['descripcion']
                    detp.articulo = form.cleaned_data['articulo']
                    detp.save(request)
                    log(u'Editar  procedimiento evaluacion: %s - [%s]' % (detp,detp.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'asigprocedimiento':
            try:
                programaanalitico = ProgramaAnaliticoAsignatura.objects.get(pk=int(request.POST['id']))
                cabecera = CabProcedimientoEvaluacionPa.objects.get(pk=int(request.POST['idc']))
                programaanalitico.procedimientoeva_id = cabecera.id
                programaanalitico.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addactaresponsabilidad':
            try:
                f = ActaResponsabilidadForm(request.POST, request.FILES)
                filter = Q(status=True)
                if f.is_valid():
                    newfile = None
                    if 'actaresponsabilidad' in request.FILES:
                        newfile = request.FILES['actaresponsabilidad']
                        if newfile:
                            if newfile.size > 2194304:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 2 Mb."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext in ['.pdf']:
                                    newfile._name = generar_nombre("actaresponsabilidad_", newfile._name)
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, Solo archivo con extención. pdf."})
                    # if ActaResponsabilidad.objects.filter(persona=persona,
                    #                                       malla_id=int(encrypt(request.POST['id'])),
                    #                                       fechainicio=date.today(),
                    #                                       status=True).exists():
                    #     return JsonResponse({"result": True, "mensaje": u"El registro ya existe."})
                    idacta = ActaResponsabilidad.objects.values_list('id', flat=True).filter(malla_id=int(encrypt(
                        request.POST['id'])),
                        status=True).order_by(
                        'id').last()
                    if idacta:
                        acta = ActaResponsabilidad.objects.get(pk=idacta)
                        if not acta.fechafin:
                            acta.fechafin = date.today()
                            acta.save(request)
                    acta = ActaResponsabilidad(persona=persona,
                                               malla_id=int(encrypt(request.POST['id'])),
                                               fechainicio=date.today(),
                                               archivoresponsabilidad=newfile,
                                               observacion=f.cleaned_data['observacion'])
                    acta.save(request)
                    log(u'Adicionó nueva acta: %s' % acta, request, "add")
                    return JsonResponse({"result": False, 'mensaje': 'Registro Exitoso'})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': "bad", "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editactaresponsabilidad':
            try:
                f = ActaResponsabilidadForm(request.POST, request.FILES)
                f.fields['actaresponsabilidad'].required = False
                if f.is_valid():
                    newfile = None
                    acta = ActaResponsabilidad.objects.get(pk=encrypt(request.POST['id']))
                    # if ActaResponsabilidad.objects.filter(persona=persona,
                    #                                       malla_id=int(encrypt(request.POST['id'])),
                    #                                       fechainicio=date.today(),
                    #                                       status=True).exists():
                    #     return JsonResponse({"result": True, "mensaje": u"El registro ya existe."})
                    if 'actaresponsabilidad' in request.FILES:
                        newfile = request.FILES['actaresponsabilidad']
                        if newfile:
                            if newfile.size > 2194304:
                                raise NameError(u"Error, archivo mayor a 2 Mb.")
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext in ['.pdf']:
                                    newfile._name = generar_nombre("actaresponsabilidad_", newfile._name)
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, Solo archivo con extención. pdf."})
                            acta.archivoresponsabilidad = newfile
                    acta.observacion = f.cleaned_data['observacion']
                    acta.save(request)
                    log(u'Modificó acta de responsabilidad: %s' % acta, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Error: {ex}"})

        elif action == 'saveAsignaturaMallaOrden':
            try:
                data['malla'] = malla = Malla.objects.get(pk=int(encrypt(request.POST['id'])))
                data['asignaturasmallas'] = asignaturasmallas = malla.asignaturamalla_set.filter(status=True)
                asignaturamalla = asignaturasmallas.get(pk=int(encrypt(request.POST['idam'])))
                asignaturamallaorden = asignaturamalla.obtener_asignaturamallaorden()
                orden = request.POST['orden']

                if not orden.isdigit():
                    raise NameError('El campo del orden no es un número válido')
                orden = int(request.POST['orden'])
                asignaturamalla_orden_existente = AsignaturaMallaOrden.objects.filter(asignaturamalla_id__in=asignaturasmallas.exclude(id=asignaturamalla.id).values_list('id', flat=True),
                                                                                      orden=orden).first()
                if asignaturamalla_orden_existente is not None:
                    name_asig = asignaturamalla_orden_existente.asignaturamalla.asignatura.__str__()
                    raise NameError(f'El campo del orden # {orden} existe en la {name_asig}')

                max_asi = asignaturasmallas.count()
                # if orden > max_asi or orden < 1:
                #     raise NameError(f'El campo del orden debe estar en el rango entre 1 y {max_asi}')
                if orden < 1:
                    raise NameError(f'El campo del orden no puede ser valor negativo')
                accion = 'edit'
                if asignaturamallaorden is None:
                    asignaturamallaorden = AsignaturaMallaOrden(
                        asignaturamalla=asignaturamalla,
                    )
                    accion = 'add'
                asignaturamallaorden.orden = orden
                asignaturamallaorden.save(request)
                template = get_template('mallas/modal/modalTablaAsignaturaMallaOrden.html')
                return JsonResponse({"result": "ok", 'html': template.render(data)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'add':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Adicionar malla curricular'
                    form = MallaForm(initial={"inicio": datetime.now().date()})
                    if not puede_realizar_accion_afirmativo(request, 'sga.puede_modificar_campo_especifico_malla'):
                        form.sin_campo_especifico()
                    form.por_miscarreras(miscarreras)
                    data['form'] = form
                    return render(request, "mallas/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcampoocupacional':
                try:
                    data['title'] = u'Adicionar campo ocupacional'
                    data['malla'] = Malla.objects.get(pk=int(encrypt(request.GET['idmalla'])))
                    form = CamposOcupacionalesForm()
                    data['form'] = form
                    return render(request, "mallas/addcampoocupacional.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcamporotacion':
                try:
                    data['title'] = u'Adicionar campo rotación'
                    data['malla'] = Malla.objects.get(pk=int(encrypt(request.GET['idmalla'])))
                    form = CamposRotacionesForm()
                    data['form'] = form
                    return render(request, "mallas/addcamporotacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcampoitinerario':
                try:
                    data['title'] = u'Adicionar itinerario'
                    data['malla'] = Malla.objects.get(pk=int(encrypt(request.GET['idmalla'])))
                    form = CamposItinerariosForm()
                    data['form'] = form
                    return render(request, "mallas/addcampoitinerario.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcampoitinerariovinculacion':
                try:
                    data['title'] = u'Adicionar itinerario de vinculación'
                    data['malla'] = Malla.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = CamposItinerariosVinculacionForm()
                    data['form'] = form
                    template = get_template("mallas/modal/modal_campoitinerariovinculacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'delasign':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    malla = asignaturamalla.malla
                    if not asignaturamalla.en_uso():
                        # if not asignaturamalla.ejeformativo in [4, 9, 11, 12]:
                        #     if registro_horas_semanales := MallaHorasSemanalesComponentes.objects.filter(status=True,malla_id=asignaturamalla.malla.id,nivelmalla_id=asignaturamalla.nivelmalla.id).first():
                        #         asignatura_malla_itinerario = AsignaturaMalla.objects.filter(status=True,malla_id=asignaturamalla.malla.id,nivelmalla_id=asignaturamalla.nivelmalla.id,itinerario__gt=0).exclude(pk=int(encrypt(request.GET['id']))).count()
                        #         if asignaturamalla.itinerario > 0:
                        #             if asignatura_malla_itinerario == 0:
                        #                 registro_horas_semanales.acd_horassemanales -= round((asignaturamalla.horasacdtotal/16),1)
                        #                 registro_horas_semanales.ape_aa_horassemanales -= round((asignaturamalla.horasapetotal/16),1) + round((asignaturamalla.horasautonomas/16),1)
                        #                 registro_horas_semanales.total_horassemanales -= round((asignaturamalla.horasacdtotal/16),1) + round((asignaturamalla.horasapetotal/16),1)  + round((asignaturamalla.horasautonomas/16),1)
                        #                 registro_horas_semanales.tiene_itinerario = False
                        #         else:
                        #             registro_horas_semanales.acd_horassemanales -= round((asignaturamalla.horasacdtotal / 16), 1)
                        #             registro_horas_semanales.ape_aa_horassemanales -= round((asignaturamalla.horasapetotal / 16), 1) + round((asignaturamalla.horasautonomas / 16), 1)
                        #             registro_horas_semanales.total_horassemanales -= round((asignaturamalla.horasacdtotal / 16), 1) + round((asignaturamalla.horasapetotal / 16), 1) + round((asignaturamalla.horasautonomas / 16), 1)
                        #         registro_horas_semanales.save(request)
                        log(u'Elimino asignatura malla: %s' % asignaturamalla, request, "del")
                        asignaturamalla.delete()
                    return HttpResponseRedirect('/mallas?action=edit&id=' + str(encrypt(malla.id)))
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Borrar malla curricular'
                    data['malla'] = Malla.objects.filter(carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "mallas/delete.html", data)
                except Exception as ex:
                    pass

            elif action == 'delarchivo':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Eliminar Archivo PDF Resolución de Aprobación del CES de malla curricular.'
                    data['malla'] = Malla.objects.filter(carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "mallas/delarchivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'delarchivoproyecto':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Eliminar Archivo PDF Proyecto Final cargado al CES de malla curricular.'
                    data['malla'] = Malla.objects.filter(carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "mallas/delarchivoproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'delarchivoproyectorediseñado':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Eliminar Archivo PDF Proyecto Rediseñado.'
                    data['malla'] = Malla.objects.filter(carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "mallas/delarchivoproyectoredi.html", data)
                except Exception as ex:
                    pass

            elif action == 'delrequisito':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Borrar requisito'
                    data['requisito'] = RequisitosMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "mallas/delrequisito.html", data)
                except Exception as ex:
                    pass

            elif action == 'delintegracioncurricular':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Borrar Requisito Ingreso de Unidad de Integración Curricular'
                    data['requisito'] = RequisitoIngresoUnidadIntegracionCurricular.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "mallas/delintegra.html", data)
                except Exception as ex:
                    pass

            elif action == 'delmodulo':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Borrar módulo'
                    data['modulo'] = ModuloMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "mallas/delmodulo.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar malla curricular'
                    idmallamoduloingles = variable_valor('ID_MALLAINGLES')
                    data['malla'] = malla = Malla.objects.filter(carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    if idmallamoduloingles == malla.id:
                        data['idmallamoduloingles'] = True
                    else:
                        data['idmallamoduloingles'] = False
                    data['nivelesdemallas'] = NivelMalla.objects.all().order_by('id')

                    ejesenuso = AsignaturaMalla.objects.values_list('ejeformativo_id', flat=True).filter(malla_id=int(encrypt(request.GET['id']))).distinct()

                    data['ejesformativos'] = EjeFormativo.objects.filter(id__in=ejesenuso).order_by('nombre')
                    # data['ejesformativos'] = EjeFormativo.objects.all().order_by('nombre')
                    # data['formdetasigmalla'] = AsignaturaMallaModalidadForm()
                    data['asignaturasmallas'] = AsignaturaMalla.objects.filter(malla=data['malla'],status=True)
                    # data['detasigmalla'] = DetalleAsignaturaMallaModalidad.objects.filter(asignaturamalla=data['asignaturasmallas'])
                    data['costo_en_malla'] = COSTO_EN_MALLA
                    data['asignaturaspresenciales'] = malla.cantidad_total_materias_presenciales
                    data['asignaturasvirtuales'] = malla.cantidad_total_materias_virtuales
                    data['horasasignaturasvirtuales'] = malla.suma_horas_materias_virtuales
                    data['porcentajepre'] = malla.porcentaje_horasp
                    data['porcentajevir'] = malla.porcentaje_horasv
                    data['horasasignaturaspresenciales'] = malla.suma_horas_materias_presenciales
                    puede_modificar_mallas = True
                    if not persona.usuario.is_superuser:
                        if not persona.usuario.has_perm('sga.puede_modificar_mallas'):
                            puede_modificar_mallas = False
                        elif malla.cerrado:
                            puede_modificar_mallas = False
                    data['puede_modificar_mallas'] = puede_modificar_mallas
                    data['resumenes'] = [{'id': x.id, 'horas': x.total_horas(data['malla']), 'creditos': x.total_creditos(data['malla']) , 'horasext': x.suma_horas_validacion_itinerario(data['malla']), 'creditosext': x.suma_creditos_validacion_itinerario(data['malla']), 'cant_mat': x.cantidad_materias(data['malla']), 'cant_mat_pres': x.cantidad_materias_presenciales(data['malla']), 'cant_mat_virt': x.cantidad_materias_virtuales(data['malla']) } for x in NivelMalla.objects.all().order_by('id')]
                    data['ver_silabo_malla'] = VER_SILABO_MALLA
                    return render(request, "mallas/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcampoocupacional':
                try:
                    data['title'] = u'Editar campo ocupacional'
                    data['campoocupacional'] = campoocupacional = CamposOcupacionalesMalla.objects.get(pk=int(encrypt(request.GET['idcampoocupacional'])))
                    form = CamposOcupacionalesForm(initial={'nombre': campoocupacional.nombre})
                    data['form'] = form
                    return render(request, "mallas/editcampoocupacional.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcamporotacion':
                try:
                    data['title'] = u'Editar campo ocupacional'
                    data['camporotacion'] = camporotacion = RotacionesMalla.objects.get(pk=int(encrypt(request.GET['idcamporotacion'])))
                    form = CamposRotacionesForm(initial={'nombre': camporotacion.nombre})
                    data['form'] = form
                    return render(request, "mallas/editcamporotacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcampoitinerario':
                try:
                    data['title'] = u'Editar itinerario'
                    data['campoitinerario'] = campoitinerario = ItinerariosMalla.objects.get(pk=int(encrypt(request.GET['idcampoitinerario'])))
                    form = CamposItinerariosForm(initial={'nombre': campoitinerario.nombre,
                                                          'nivel': campoitinerario.nivel,
                                                          'horas_practicas': campoitinerario.horas_practicas,
                                                          })
                    data['form'] = form
                    return render(request, "mallas/editcampoitinerario.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcampoitinerariovinculacion':
                try:
                    data['title'] = u'Editar itinerario de vinculación'
                    data['malla'] = campoitinerariovinculacion = ItinerariosVinculacionMalla.objects.get(pk=int(request.GET['id']))
                    data['form'] = CamposItinerariosVinculacionForm(initial=model_to_dict(campoitinerariovinculacion))
                    template = get_template("mallas/modal/modal_campoitinerariovinculacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'modulos':
                try:
                    data['title'] = u'Módulos anexos a la carrera'
                    data['malla'] = malla = Malla.objects.filter(carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    data['modulos'] = malla.modulomalla_set.filter(status=True).order_by('orden')
                    return render(request, "mallas/modulos.html", data)
                except Exception as ex:
                    pass

            elif action == 'editsyllabus':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Editar syllabus'
                    data['asignaturamalla'] = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['idm'])))
                    data['archivo'] = archivo = Archivo.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = ArchivoSyllabusMallaForm(initial={'nombre': archivo.nombre,
                                                             'fecha': archivo.fecha,
                                                             'archivo': archivo})
                    form.sin_archivo()
                    data['form'] = form
                    return render(request, "mallas/editsyllabus.html", data)
                except Exception as ex:
                    pass

            elif action == 'programanalitico':
                try:
                    data['title'] = u'Programa Analítico'
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    data['programanaliticoasignatura'] = ProgramaAnaliticoAsignatura.objects.filter(asignaturamalla=asignaturamalla,status=True).order_by('-fecha_creacion')
                    data['numero_evidencia'] = 8
                    data['creasilabo'] = variable_valor('PUEDE_CREAR_PLAN')
                    return render(request, "mallas/programanaliticoasignatura.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadotransversales':
                try:
                    data['title'] = u'Asignatura Transversales'
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    if not asignaturamalla.transversalasignatura_set.filter(status=True):
                        transversal = TransversalAsignatura(asignaturamalla=asignaturamalla,
                                                            asignatura=asignaturamalla.asignatura)
                        transversal.save()
                    data['listadoasignaturas'] = asignaturamalla.transversalasignatura_set.filter(status=True).order_by('asignatura__nombre')
                    return render(request, "mallas/listadotransversales.html", data)
                except Exception as ex:
                    pass

            if action == 'programanaliticoposgrado':
                try:
                    data['title'] = u'Programa Analítico'
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(
                        malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    data['programanaliticoasignatura'] = ProgramaAnaliticoAsignatura.objects.filter(
                        asignaturamalla=asignaturamalla, status=True).order_by('-fecha_creacion')
                    data['numero_evidencia'] = 8
                    return render(request, "mallas/programanaliticoasignaturaposgrado.html", data)
                except Exception as ex:
                    pass

            elif action == 'evidencias':
                try:
                    if 'id' in request.GET:
                        data['pa'] = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                        template = get_template("mallas/evidencias.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'evidenciasposgrado':
                try:
                    if 'id' in request.GET:
                        data['pa'] = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                        template = get_template("mallas/evidenciasposgrado.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'tituloafin':
                try:
                    ids = []
                    data['title'] = u'Títulos a fin'
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    data['titulosafin'] = tituloafin =  Titulo.objects.filter(asignaturamallatituloafin__isnull=False, asignaturamallatituloafin__status=True, asignaturamallatituloafin__asignaturamalla=asignaturamalla).distinct()
                    # for a in AsignaturaMallaTituloAFin.objects.filter(status=True, asignaturamalla=asignaturamalla):
                    #     ids.append(a.titulo.id)
                    data['titulos'] = Titulo.objects.filter(nivel__id=4, status=True).exclude(Q(grado__id__in=[3]) | Q(pk__in=tituloafin.values_list('id'))).distinct()
                    data['asignaturamallatituloafin'] = ids
                    return render(request, "mallas/tituloafin.html", data)
                except Exception as ex:
                    pass

            elif action == 'addprogramanalitico':
                try:
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = asignaturamalla
                    form = ProgramaAnaliticoAsignaturaForm()
                    data['formobjetivo'] = ObjetivoProgramaAnaliticoAsignaturaForm()
                    data['formrai'] = ResultadoAprendizajeRaiForm()
                    data['formrac'] = ResultadoAprendizajeRacForm()
                    data['formmetodologia'] = MetodologiaProgramaAnaliticoAsignaturaForm()
                    data['formbibliografia'] = BibliografiaProgramaAnaliticoAsignaturaForm()
                    data['form'] = form
                    return render(request, 'mallas/addprogramanalitico.html', data)
                except Exception as ex:
                    pass

            elif action == 'addprogramanaliticoposgrado':
                try:
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = asignaturamalla
                    form = ProgramaAnaliticoAsignaturaPosgradoForm()
                    data['formobjetivo'] = ObjetivoProgramaAnaliticoAsignaturaForm()
                    data['formrai'] = ResultadoAprendizajeRaiForm()
                    data['formrac'] = ResultadoAprendizajeRacForm()
                    data['formmetodologia'] = MetodologiaProgramaAnaliticoAsignaturaForm()
                    data['formbibliografia'] = BibliografiaProgramaAnaliticoAsignaturaForm()
                    data['form'] = form
                    return render(request, 'mallas/addprogramanaliticoposgrado.html', data)
                except Exception as ex:
                    pass

            elif action == 'addarchivoprogramanalitico':
                try:
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = asignaturamalla
                    data['form'] = ProgramaAnaliticoAsignaturaArchivoForm()
                    return render(request, 'mallas/addarchivoprogramanalitico.html', data)
                except Exception as ex:
                    pass

            elif action == 'editarchivoprogramanalitico':
                try:
                    data['title'] = u"Evidencias del programa analítico"
                    data['programaanalitico'] = pa = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = pa.asignaturamalla
                    data['form'] = ProgramaAnaliticoAsignaturaArchivoForm(initial={'motivo':pa.motivo})
                    return render(request, 'mallas/editarchivoprogramanalitico.html', data)
                except Exception as ex:
                    pass

            elif action == 'editarchivoprogramanaliticoposgraado':
                try:
                    data['title'] = u"Evidencias del programa analítico"
                    data['programaanalitico'] = pa = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = pa.asignaturamalla
                    data['form'] = ProgramaAnaliticoPosgradoAsignaturaArchivoForm(initial={'motivo':pa.motivo})
                    return render(request, 'mallas/editarchivoprogramanaliticoposgraado.html', data)
                except Exception as ex:
                    pass

            elif action == 'editprogramanalitico':
                try:
                    data['title'] = u'Editar Programa Analítico'
                    data['programanalitico'] = programanalitico = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['listarai'] = ResultadoAprendizajeRai.objects.filter(programaanaliticoasignatura=programanalitico).order_by('id')
                    data['listarac'] = ResultadoAprendizajeRac.objects.filter(programaanaliticoasignatura=programanalitico).order_by('id')
                    data['listaobjetivos'] = ObjetivoProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura=programanalitico).order_by('id')
                    data['listametodologia'] = MetodologiaProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura=programanalitico).order_by('id')
                    # data['contenido'] = ContenidoResultadoProgramaAnalitico.objects.filter(programaanaliticoasignatura=programanalitico, status=True).order_by('orden')
                    data['contenido'] = programanalitico.contenido_program_analitico()
                    data['formrai'] = ResultadoAprendizajeRaiForm()
                    data['formrac'] = ResultadoAprendizajeRacForm()
                    data['formobjetivo'] = ObjetivoProgramaAnaliticoAsignaturaForm()
                    data['formmetodologia'] = MetodologiaProgramaAnaliticoAsignaturaForm()
                    data['contenidos'] = AsignaturamallaContenidoMinimo.objects.filter(status=True, asignaturamalla = programanalitico.asignaturamalla)
                    if programanalitico.integranteuno_id is None:
                        data['intuno'] = 0
                    else:
                        data['intuno'] = programanalitico.integranteuno_id
                    if programanalitico.integrantedos_id is None:
                        data['intdos'] = 0
                    else:
                        data['intdos'] = programanalitico.integrantedos_id
                    if programanalitico.integrantetres_id is None:
                        data['inttres'] = 0
                    else:
                        data['inttres'] = programanalitico.integrantetres_id
                    form = ProgramaAnaliticoAsignaturaForm(initial={'descripcion': programanalitico.descripcion,'compromisos': programanalitico.compromisos, 'caracterinvestigacion': programanalitico.caracterinvestigacion})
                    data['form'] = form
                    return render(request, "mallas/editprogramanalitico.html", data)
                except Exception as ex:
                    pass

            elif action == 'obtener_contenidos_minimos':
                try:
                    # Obtener el ID de la unidad desde los parámetros de la solicitud GET
                    unidad_id = request.GET.get('id')
                    # Asegurarse de que el ID de la unidad sea válido
                    if not unidad_id:
                        raise NameError(u"No existe la unidad")
                    # Obtener la unidad por su ID
                    unidad = UnidadResultadoProgramaAnalitico.objects.get(pk=unidad_id, status=True)
                    if not unidad:
                        raise NameError(u"No existe la unidad")
                    # Obtener todos los contenidos mínimos asociados con esta unidad
                    contenidos_minimos = UnidadResultadoProgramaAnaliticoContenidoMinimo.objects.filter(unidadresultadoprogramaanalitico=unidad, status=True)
                    # Crear una lista de los contenidos mínimos
                    contenidos_minimos_list = [
                        {'id': contenido.asignaturamallacontenidominimo.id, 'descripcion': contenido.asignaturamallacontenidominimo.descripcioncontenido} for
                        contenido in contenidos_minimos]

                    # Devolver los contenidos mínimos en formato JSON
                    return JsonResponse({"result": "ok", 'contenidos_minimos': contenidos_minimos_list})
                except Exception as ex:
                    # Manejar cualquier otra excepción
                    return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

            elif action == 'cargarselectcontenidosminimos':
                try:
                    resultado_aprendizaje = ContenidoResultadoProgramaAnalitico.objects.get(pk=int(request.GET['id']), status=True)
                    contenidos = list(AsignaturamallaContenidoMinimo.objects.filter(status=True, asignaturamalla = resultado_aprendizaje.programaanaliticoasignatura.asignaturamalla).values('id', 'descripcioncontenido'))
                    # Devolver los contenidos mínimos en formato JSON
                    return JsonResponse({"result": "ok", 'contenidos_minimos': contenidos})
                except Exception as ex:
                    # Manejar cualquier otra excepción
                    return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

            elif action == 'editprogramanaliticoposgrado':
                try:
                    data['title'] = u'Editar Programa Analítico'
                    data['programanalitico'] = programanalitico = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['listarai'] = ResultadoAprendizajeRai.objects.filter(programaanaliticoasignatura=programanalitico).order_by('id')
                    data['listarac'] = ResultadoAprendizajeRac.objects.filter(programaanaliticoasignatura=programanalitico).order_by('id')
                    # data['contenido'] = ContenidoResultadoProgramaAnalitico.objects.filter(programaanaliticoasignatura=programanalitico, status=True).order_by('orden')
                    data['contenido'] = programanalitico.contenido_program_analitico()
                    data['formrai'] = ResultadoAprendizajeRaiForm()
                    data['formrac'] = ResultadoAprendizajeRacForm()

                    if programanalitico.integranteuno_id is None:
                        data['intuno'] = 0
                    else:
                        data['intuno'] = programanalitico.integranteuno_id
                    if programanalitico.integrantedos_id is None:
                        data['intdos'] = 0
                    else:
                        data['intdos'] = programanalitico.integrantedos_id

                    form = ProgramaAnaliticoAsignaturaPosgradoForm(initial={'descripcion': programanalitico.descripcion, 'caracterinvestigacion': programanalitico.caracterinvestigacion})
                    data['form'] = form
                    return render(request, "mallas/editprogramanaliticoposgrado.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcontenidosilabosubtema':
                try:
                    data['title'] = u'Editar Subtema'
                    data['subtema'] = subtema = SubtemaUnidadResultadoProgramaAnalitico.objects.get(pk=request.GET['subtemaid'])
                    data['idprogramanalitico'] = request.GET['idprogramanalitico']
                    form = ContenidoSubtema(initial={'contenido': subtema.contenido })
                    data['form'] = form
                    return render(request, "mallas/editcontenidosilabosubtema.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarchivosilabotema':
                try:
                    data['title'] = u'Subir archivo de tema'
                    data['tema'] = TemaUnidadResultadoProgramaAnalitico.objects.get(pk=request.GET['temaid'])
                    data['idprogramanalitico'] = request.GET['idprogramanalitico']
                    form = ArchivoTemaPlanForm()
                    data['form'] = form
                    return render(request, "mallas/editarchivosilabotema.html", data)
                except Exception as ex:
                    pass

            elif action == 'delprogramaanalitico':
                try:
                    data['title'] = u'Eliminar Programa Analítico'
                    data['programa'] = programa = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['asignaturamalla'] = programa.asignaturamalla.id
                    return render(request, "mallas/delprogramaanalitico.html", data)
                except Exception as ex:
                    pass

            elif action == 'delprogramaanaliticoposgrado':
                try:
                    data['title'] = u'Eliminar Programa Analítico'
                    data['programa'] = programa = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['asignaturamalla'] = programa.asignaturamalla.id
                    return render(request, "mallas/delprogramaanaliticoposgrado.html", data)
                except Exception as ex:
                    pass

            elif action == 'addbibliografia':
                try:
                    data['title'] = u'Bibliografía básica'
                    data['programanalitico'] = programanalitico = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['bibliografia'] = BibliografiaProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura=programanalitico)
                    return render(request, "mallas/listadobibliografia.html", data)
                except Exception as ex:
                    pass

            elif action == 'addbibliografiaposgrado':
                try:
                    data['title'] = u'Bibliografía básica'
                    data['programanalitico'] = programanalitico = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['bibliografia'] = BibliografiaProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura=programanalitico)
                    return render(request, "mallas/listadobibliografiaposgrado.html", data)
                except Exception as ex:
                    pass

            elif action == 'adicionarbibliografia':
                try:
                    data['title'] = u'Adicionar Bibliografía básica'
                    data['programanalitico'] = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = BibliografiaProgramaAnaliticoAsignaturaForm()
                    data['form'] = form
                    return render(request, "mallas/addbibliografia.html", data)
                except Exception as ex:
                    pass

            elif action == 'adicionarbibliografiaposgrado':
                try:
                    data['title'] = u'Adicionar Bibliografía básica'
                    data['programanalitico'] = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = BibliografiaProgramaAnaliticoAsignaturaForm()
                    data['form'] = form
                    return render(request, "mallas/addbibliografiaposgrado.html", data)
                except Exception as ex:
                    pass

            elif action == 'predecesora':
                try:
                    data['title'] = u'Predecesora de asignatura'
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    data['predecesoras'] = predecesoras = asignaturamalla.asignaturamallapredecesora_set.all().order_by('id')
                    puede_modificar_mallas = True
                    if not persona.usuario.is_superuser:
                        if not persona.usuario.has_perm('sga.puede_modificar_mallas'):
                            puede_modificar_mallas = False
                        elif asignaturamalla.malla.cerrado:
                            puede_modificar_mallas = False
                    data['puede_modificar_mallas'] = puede_modificar_mallas
                    # return render(request, "mallas/predecesora.html", data)
                    ## MODIFICACION PARA PANTALLA NUEVA V2
                    if asignaturamalla.malla.carrera.coordinacion_carrera():
                        if asignaturamalla.malla.carrera.coordinacion_carrera().id == 7:
                            data['select_predecesoras'] = asignaturamalla.malla.asignaturamalla_set.filter(status=True).exclude(pk__in = predecesoras.values_list('id',flat=True)).order_by('nivelmalla__orden')
                        else:
                            data['select_predecesoras'] = asignaturamalla.malla.asignaturamalla_set.filter(status=True, nivelmalla_id__lt=asignaturamalla.nivelmalla.id).exclude(pk__in = predecesoras.values_list('predecesora_id',flat=True)).order_by('nivelmalla__orden')
                    return render(request, "mallas/predecesora_v2.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewcontenidosminimos':
                try:
                    data['title'] = u'Contenidos mínimos de la asignatura'
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    data['contenidos'] = contenidos = asignaturamalla.asignaturamallacontenidominimo_set.filter(status=True).order_by('id')
                    puede_modificar_mallas = True
                    if not persona.usuario.is_superuser:
                        if not persona.usuario.has_perm('sga.puede_modificar_mallas'):
                            puede_modificar_mallas = False
                        elif asignaturamalla.malla.cerrado:
                            puede_modificar_mallas = False
                    data['puede_modificar_mallas'] = puede_modificar_mallas
                    return render(request, "mallas/contenidominimo.html", data)
                except Exception as ex:
                    pass

            # elif action == 'addcontenidosminimos':
            #     try:
            #         data['title'] = u'Adicionar contenido mínimo'
            #         data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
            #         form = ContenidoMinimoForm()
            #         data['id'] = asignaturamalla.id
            #         data['form'] = form
            #         template = get_template('ajaxformmodal.html')
            #         return JsonResponse({"result": True, 'data': template.render(data)})
            #     except Exception as ex:
            #         pass

            # elif action == 'editcontenidosminimos':
            #     try:
            #         data['title'] = u'Actualizar contenido mínimo'
            #         cont_minimo = AsignaturamallaContenidoMinimo.objects.get(pk=int(encrypt(request.GET['id'])), status = True)
            #         form = ContenidoMinimoForm(initial={'contenido_minimo': cont_minimo.descripcioncontenido})
            #         data['id'] = cont_minimo.id
            #         data['idp'] = cont_minimo.asignaturamalla.id
            #         data['asignaturamalla_id'] = cont_minimo.asignaturamalla.id
            #         data['form'] = form
            #         template = get_template('ajaxformmodal.html')
            #         return JsonResponse({"result": True, 'data': template.render(data)})
            #     except Exception as ex:
            #         pass

            elif action == 'addpredecesora':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Predecesora de asignatura'
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    form = AsignaturaMallaPredecesoraForm()
                    form.for_exclude_asignatura(asignaturamalla)
                    data['form'] = form
                    data['predecesoras'] = asignaturamalla.asignaturamallapredecesora_set.all().order_by('asignaturamalla__asignatura')
                    return render(request, "mallas/addpredecesora.html", data)
                except Exception as ex:
                    pass

            elif action == 'corequisitos':
                try:
                    data['title'] = u'Correquisitos'
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    data['corequisitos'] = corequisitos = asignaturamalla.asignaturamallacorequisito_set.all().order_by('id')
                    puede_modificar_mallas = True
                    if not persona.usuario.is_superuser:
                        if not persona.usuario.has_perm('sga.puede_modificar_mallas'):
                            puede_modificar_mallas = False
                        elif asignaturamalla.malla.cerrado:
                            puede_modificar_mallas = False
                    data['puede_modificar_mallas'] = puede_modificar_mallas
                    # return render(request, "mallas/corequisitos.html", data)
                    ## ACTUALIZACIÓN DE PANTALLA V2
                    data['select_correquisitos'] = asignaturamalla.malla.asignaturamalla_set.filter(nivelmalla_id=asignaturamalla.nivelmalla.id).exclude(Q(id__in=corequisitos.values_list('corequisito_id',flat=True)) | Q(id=asignaturamalla.id))
                    return render(request, "mallas/corequisitos_v2.html", data)
                except Exception as ex:
                    pass

            elif action == 'homologacion':
                try:
                    data['title'] = u'Homologacion'
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    data['homologacion'] = asignaturamalla.asignaturamallahomologacion_set.filter(status=True).order_by('homologacion__asignatura')
                    return render(request, "mallas/homologacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcorequisito':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Correquisitos'
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    form = AsignaturaMallaCoRequisitoForm()
                    # corequisitos = AsignaturaMallaCoRequisito.objects.values("corequisito_id").filter(status=True)
                    corequisitos = AsignaturaMallaCoRequisito.objects.values("corequisito_id").filter(status=True,asignaturamalla=asignaturamalla)
                    form.select_asignatura(asignaturamalla,corequisitos, asignaturamalla.id)
                    data['form'] = form
                    return render(request, "mallas/addcorequisito.html", data)
                except Exception as ex:
                    pass

            elif action == 'addhomologacion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Homologaciones'
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    # data['asignaturamallahomologar'] = asignaturamallahomologar = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras)
                    form = AsignaturaMallaHomologacionForm()
                    form.fields['homologacion'].queryset = AsignaturaMalla.objects.filter(malla__carrera=asignaturamalla.malla.carrera).exclude(malla=asignaturamalla.malla)
                    # homologaciones = AsignaturaMallaHomologacion.objects.values("homologacion_id").filter(status=True)
                    # form.select_asignatura(asignaturamalla,homologaciones, asignaturamalla.id)
                    data['form'] = form
                    return render(request, "mallas/addhomologacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'delcorequisito':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['corequisito'] = AsignaturaMallaCoRequisito.objects.filter(asignaturamalla__malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "mallas/delcorequisito.html", data)
                except Exception as ex:
                    pass

            elif action == 'solicitudeslibros':
                try:
                    data['title'] = u'Solicitud de adquisición de Libros'
                    data['programa'] = programaanalitico = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitudes'] = programaanalitico.solicitudcompralibro_set.filter(status=True)
                    return render(request, "mallas/solicitudeslibros.html", data)
                except Exception as ex:
                    pass

            elif action == 'addsolicitudlibro':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Adicionar Solicitud de adquisición de libro'
                    data['programa'] = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = SolicitudCompraLibroForm()
                    data['form'] = form
                    return render(request, "mallas/addsolicitudlibro.html", data)
                except Exception as ex:
                    pass

            elif action == 'editsolicitudlibro':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Editar Solicitud de adquisición de libro'
                    data['solicitud'] = solicitud = SolicitudCompraLibro.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = SolicitudCompraLibroForm(initial={'nombre':solicitud.nombre, 'autor':solicitud.autor, 'aniopublicacion':solicitud.aniopublicacion, 'editorial': solicitud.editorial, 'cantidad': solicitud.cantidad})
                    return render(request, "mallas/editsolicitudlibro.html", data)
                except Exception as ex:
                    pass

            elif action == 'delsolicitudlibro':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['solicitud'] = SolicitudCompraLibro.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "mallas/delsolicitudlibro.html", data)
                except Exception as ex:
                    pass

            elif action == 'addmodulo':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Adicionar módulo'
                    data['malla'] = Malla.objects.filter(carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = AsignaturaModuloForm()
                    return render(request, "mallas/addmodulo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editmodulo':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Editar módulo'
                    data['malla'] = Malla.objects.filter(carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    data['modulo'] = modulo = ModuloMalla.objects.get(pk=int(encrypt(request.GET['idm'])))
                    f = AsignaturaModuloForm(initial={"asignatura":modulo.asignatura,
                                                      "horas": modulo.horas,
                                                      "tipo": modulo.tipo,
                                                      "creditos": modulo.creditos,
                                                      "orden": modulo.orden,
                                                      })
                    f.editar()
                    data['form'] = f
                    return render(request, "mallas/editmodulo.html", data)
                except Exception as ex:
                    pass

            elif action == 'aprobarsyllabus':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    archivo = Archivo.objects.filter(asignaturamalla__malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    archivo.aprobado = True
                    archivo.save(request)
                    log(u'Aprobo silabo asignatura malla: %s' % archivo.asignaturamalla, request, "edit")
                    return HttpResponseRedirect("/mallas?action=syllabus&id=" + request.GET['idm'])
                except Exception as ex:
                    pass

            elif action == 'desaprobarsyllabus':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    archivo = Archivo.objects.filter(asignaturamalla__malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    archivo.aprobado = False
                    archivo.save(request)
                    log(u'Desaprobado silabo asignatura malla: %s' % archivo.asignaturamalla, request, "edit")
                    return HttpResponseRedirect("/mallas?action=syllabus&id=" + request.GET['idm'])
                except Exception as ex:
                    pass

            elif action == 'delsyllabus':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    archivo = Archivo.objects.filter(asignaturamalla__malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    asignaturamalla = archivo.asignaturamalla
                    log(u'Elimino silabo: %s' % asignaturamalla, request, "del")
                    archivo.delete()
                    return HttpResponseRedirect("/mallas?action=syllabus&id=" + request.GET['idm'])
                except Exception as ex:
                    pass

            elif action == 'addsyllabus':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Adicionar silabo'
                    asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    data['asignaturamalla'] = asignaturamalla
                    data['form'] = ArchivoSyllabusMallaForm(initial={'fecha': datetime.now().date(),
                                                                     'nombre': unicode(asignaturamalla.asignatura)})
                    return render(request, "mallas/addsyllabus.html", data)
                except Exception as ex:
                    pass

            elif action == 'delcampoocupacional':
                try:
                    data['title'] = u'Eliminar campo ocupacional'
                    data['campoocupacional'] = CamposOcupacionalesMalla.objects.get(pk=int(encrypt(request.GET['idcampoocupacional'])))
                    return render(request, "mallas/delcampoocupacional.html", data)
                except Exception as ex:
                    pass

            elif action == 'delcampoitinerario':
                try:
                    data['title'] = u'Eliminar itinerario'
                    data['campoitinerario'] = ItinerariosMalla.objects.get(pk=int(encrypt(request.GET['idcampoitinerario'])))
                    return render(request, "mallas/delcampoitinerario.html", data)
                except Exception as ex:
                    pass

            elif action == 'delcampoitinerariovinculacion':
                try:
                    data['title'] = u'Eliminar itinerario de vinculación'
                    data['campoitinerariovinculacion'] = ItinerariosVinculacionMalla.objects.get(pk=int(encrypt(request.GET['idcampoitinerariovinculacion'])))
                    return render(request, "mallas/modal/modal_delcampoitinerariovinculacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'delturnohorario':
                try:
                    data['title'] = u'Eliminar turno horario'
                    data['horariovirtual'] = HorarioVirtual.objects.get(pk=int(encrypt(request.GET['idturnohorario'])))
                    return render(request, "mallas/delturnohorario.html", data)
                except Exception as ex:
                    pass

            elif action == 'delparticipante':
                try:
                    data['title'] = u'Eliminar Estudiante'
                    data['participante'] = ParticipantesHorarioVirtual.objects.get(pk=int(encrypt(request.GET['idparticipante'])))
                    return render(request, "mallas/delparticipante.html", data)
                except Exception as ex:
                    pass

            elif action == 'delcamporotacion':
                try:
                    data['title'] = u'Eliminar campo rotación'
                    data['camporotacion'] = RotacionesMalla.objects.get(pk=int(encrypt(request.GET['idcamporotacion'])))
                    return render(request, "mallas/delcamporotacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editmalla':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Editar malla curricular'
                    data['malla'] = malla = Malla.objects.filter(carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    # form = MallaForm(initial={"carrera": malla.carrera,
                    #                           "modalidad": malla.modalidad,
                    #                           "vigente": malla.vigente,
                    #                           "inicio": malla.inicio,
                    #                           "fin": malla.fin,
                    #                           "creditos_completar": malla.creditos_completar,
                    #                           "materias_completar": malla.materias_completar,
                    #                           "optativas": malla.optativas,
                    #                           "niveles_regulares": malla.niveles_regulares,
                    #                           "porciento_nivel": malla.porciento_nivel,
                    #                           "libre_opcion": malla.libre_opcion,
                    #                           "creditos_vinculacion": malla.creditos_vinculacion,
                    #                           "horas_vinculacion": malla.horas_vinculacion,
                    #                           "creditos_practicas": malla.creditos_practicas,
                    #                           "horas_practicas": malla.horas_practicas,
                    #                           "creditos_titulacion": malla.creditos_titulacion,
                    #                           "horas_titulacion": malla.horas_titulacion,
                    #                           "creditos_computacion": malla.creditos_computacion,
                    #                           "perfilegreso": malla.perfilegreso,
                    #                           "perfilprofesional": malla.perfilprofesional,
                    #                           "resolucion": malla.resolucion,
                    #                           "misioncarrera": malla.misioncarrera,
                    #                           "semanas": malla.semanas,
                    #                           "objetivocarrera":malla.objetivocarrera,
                    #                           "tituloobtenidohombre": malla.tituloobtenidohombre,
                    #                           "tituloobtenidomujer": malla.tituloobtenidomujer,
                    #                           "codigo": malla.codigo,
                    #                           "campo_especifico": malla.campo_especifico,
                    #                           "creditoporhora": malla.creditoporhora,
                    #                           "archivo": malla.archivo.url if malla.archivo else '',
                    #                           "archivo_proyecto": malla.archivo_proyecto.url if malla.archivo_proyecto else '',
                    #                           })
                    initial = model_to_dict(malla)
                    form = MallaForm(initial=initial)
                    data['form'] = form
                    form.editar()
                    if not puede_realizar_accion_afirmativo(request, 'sga.puede_modificar_campo_especifico_malla'):
                        form.sin_campo_especifico()
                    if malla.cerrado:
                        form.malla_cerrada()
                    data['form'] = form
                    coordinacionselect = nivelselect = s = None
                    if 'c' in request.GET:
                        coordinacionselect = int(request.GET['c'])
                    if 'n' in request.GET:
                        nivelselect = int(request.GET['n'])
                    if 's' in request.GET:
                        s = request.GET['s']
                    data['coordinacionselect'] = coordinacionselect
                    data['nivelselect'] = nivelselect
                    data['search'] = s
                    data['busqueda']=True if coordinacionselect or nivelselect or s else False
                    return render(request, "mallas/editmalla.html", data)
                except Exception as ex:
                    pass

            elif action == 'editlineainvestigacion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Editar linea de investigación'
                    data['malla'] = malla = Malla.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = MallaLineaForm(initial={"lineainvestigacion": malla.lineainvestigacion})
                    data['form'] = form
                    return render(request, "mallas/editlineinvestigacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addasign':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Adicionar asignatura a malla curricular'
                    data['malla'] = malla = Malla.objects.filter(carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    #data['eje'] = EjeFormativo.objects.get(pk=int(encrypt(request.GET['eje'])))
                    data['nivel'] = NivelMalla.objects.get(pk=int(encrypt(request.GET['nivel'])))
                    form = AsignaturaMallaForm()
                    form.adicionar([x.id for x in Asignatura.objects.filter(asignaturamalla__malla=malla)], malla)
                    form.fields['creditos'].widget.attrs['required'] = True
                    data['form'] = form
                    if malla.carrera.mi_coordinacion2() == 9:
                        form.sin_reemplazo()
                        return render(request, "mallas/addasign_pregrado.html", data)
                    if malla.carrera.mi_coordinacion2() != 7:
                        return render(request, "mallas/addasign_pregrado.html", data)
                    else:
                        return render(request, "mallas/addasign.html", data)
                except Exception as ex:
                    pass

            elif action == 'editasign':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Editar asignatura de malla curricular'
                    data['asignaturamalla'] = am = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    form = AsignaturaMallaForm(initial={"ejeformativo": am.ejeformativo,
                                                        "asignatura": am.asignatura,
                                                        "nivel": am.nivelmalla,
                                                        "horas": int(am.horas),
                                                        "tipomateria": am.tipomateria,
                                                        "creditos": am.creditos,
                                                        "costo": am.costo,
                                                        "rectora": am.rectora,
                                                        "validarequisitograduacion": am.validarequisitograduacion,
                                                        "transversal": am.transversal,
                                                        "reemplazo": am.reemplazo,
                                                        "vigente": am.vigente,
                                                        "practicas": am.practicas,
                                                        "areaconocimiento": am.areaconocimiento,
                                                        "identificacion": am.identificacion,
                                                        "horaspresenciales": am.horaspresenciales,
                                                        "horasautonomas": am.horasautonomas,
                                                        "opcional": am.opcional,
                                                        "horaspresencialessemanales": am.horaspresencialessemanales,
                                                        "horasautonomassemanales": am.horasautonomassemanales,
                                                        "horaspracticastotales": am.horaspracticastotales,
                                                        "horaspracticassemanales": am.horaspracticassemanales,
                                                        "horasasistidas":am.horasasistidas,
                                                        "areaconocimientotitulacion":am.areaconocimientotitulacion,
                                                        "subareaconocimiento":am.subareaconocimiento,
                                                        "subareaespecificaconocimiento":am.subareaespecificaconocimiento,
                                                        "horascolaborativas":am.horascolaborativas,
                                                        "porcentajecalificacion":am.porcentajecalificacion if am.porcentajecalificacion else "",
                                                        "horasacdtotal": am.horasacdtotal,
                                                        "horasacdsemanal": am.horasacdsemanal,
                                                        "horasvirtualtotal": am.horasvirtualtotal,
                                                        "horasvirtualsemanal": am.horasvirtualsemanal,
                                                        "horasapetotal": am.horasapetotal,
                                                        "horasapesemanal": am.horasapesemanal,
                                                        "horasvinculaciontotal": am.horasvinculaciontotal,
                                                        "horasvinculacionsemanal": am.horasvinculacionsemanal,
                                                        "horasppptotal": am.horasppptotal,
                                                        "horaspppsemanal": am.horaspppsemanal,
                                                        "horasapeasistotal": am.horasapeasistotal,
                                                        "horasapeasissemanal": am.horasapeasissemanal,
                                                        "horasapeautototal": am.horasapeautototal,
                                                        "horasapeautosemanal": am.horasapeautosemanal,
                                                        "itinerario": am.itinerario,
                                                        "unidad_organizacion_curricular": am.unidad_organizacion_curricular,
                                                        "itinerario_malla_especialidad": am.itinerario_malla_especialidad,
                                                        "afinidaddoctorado": am.afinidaddoctorado,
                                                        "horasteoriatitutotal": am.horasteoriatitutotal,
                                                        "nivelsuficiencia": am.nivelsuficiencia,
                                                        "asignaturapracticas": am.asignaturapracticas,
                                                        "nohomologa":am.nohomologa
                                                        })
                    form.editar(am)
                    data['form'] = form
                    # data['horasautonomas_antiguas'] = round((am.horasautonomas/16),1)
                    # data['horasacd_antiguas'] = round((am.horasacdtotal/16),1)
                    # data['horasape_antiguas'] = round((am.horasapetotal/16),1)
                    # data['tuvo_itinerario'] = am.itinerario
                    if am.malla.carrera.mi_coordinacion2() == 9:
                        form.sin_reemplazo()
                        return render(request, "mallas/editasign_pregrado.html", data)
                    if am.malla.carrera.mi_coordinacion2() != 7:
                        return render(request, "mallas/editasign_pregrado.html", data)
                    else:
                        return render(request, "mallas/editasign.html", data)
                except Exception as ex:
                    pass

            elif action == 'reporteasignaturas':
                try:
                    malla = Malla.objects.get(pk=int(encrypt(request.GET['id'])))
                    asignaturas = AsignaturaMalla.objects.filter(malla=malla)
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('asignaturas')
                    ws.set_column(1,21, 40)

                    formatoceldagris = workbook.add_format(
                        {'align': 'center', 'border': 1, 'text_wrap': True, 'fg_color': '#B6BFC0'})
                    formatocelda = workbook.add_format(
                        {'align': 'left', 'border': 1, 'text_wrap': True})

                    formatotitulo = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 12,'border': 1,'text_wrap': True,'font_color': 'blue'})


                    ws.merge_range(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO',formatotitulo)
                    ws.merge_range('A2:I2', 'MALLA - ' + str(malla.codigo) + ' - ' + str(malla.carrera),formatotitulo)

                    ws.write('A4','ORD.',formatoceldagris)
                    ws.write('B4','NOMBRE.',formatoceldagris)
                    ws.write('C4','TIPO DE ASIGNATURA.',formatoceldagris)
                    ws.write('D4','NIVEL.',formatoceldagris)
                    ws.write('E4','HORAS APRENDIZAJE CONTACTO \n DOCENTE (ACD) TOTALES.',formatoceldagris)
                    ws.write('F4','HORAS APRENDIZAJE PRÁCTICO \n EXPERIMENTAL (APE) TOTALES.',formatoceldagris)
                    ws.write('G4','HORAS APRENDIZAJE AUNTÓNOMO \n EXPERIMENTAL (AA) TOTALES.',formatoceldagris)
                    ws.write('H4','HORAS TOTALES',formatoceldagris)
                    ws.write('I4','ASIGNATURA PRÁCTICA',formatoceldagris)

                    ws.write('J4', 'HORAS APRENDIZAJE \n CONTACTO DOCENTE SEMANALES', formatoceldagris)
                    ws.write('K4', 'HORAS ACD \n PRESENCIALES SEMANALES', formatoceldagris)
                    ws.write('L4', 'HORAS ACD \n VIRTUALES SEMANALES', formatoceldagris)
                    ws.write('M4', 'HORAS APRENDIZAJE \n PRÁCTICO EXPERIMENTAL SEMANALES', formatoceldagris)
                    ws.write('N4', 'HORAS APE ASISTIDAS \n SEMANALES', formatoceldagris)
                    ws.write('O4', 'HORAS APE \n NO ASISTIDAS SEMANALES', formatoceldagris)
                    ws.write('P4', 'HORAS APRENDIZAJE \n AUTÓNOMO SEMANALES', formatoceldagris)
                    ws.write('Q4', 'HORAS VINCULACIÓN \n SEMANALES', formatoceldagris)
                    ws.write('R4', 'HORAS VINCULACIÓN \n TOTALES', formatoceldagris)
                    ws.write('S4', 'HORAS PRÁCTICAS \n PRE-PROFESIONALES SEMANALES', formatoceldagris)
                    ws.write('T4', 'HORAS PRÁCTICAS \n PRE-PROFESIONALES TOTALES', formatoceldagris)
                    ws.write('U4', 'PRE REQUISITOS \n DE LA ASIGNATURA', formatoceldagris)
                    ws.write('V4', 'CO REQUISITOS \n DE LA ASIGNATURA', formatoceldagris)

                    cont=5
                    i=1

                    for asi in asignaturas:
                        ws.write('A%s'%(cont), str(i), formatocelda)
                        ws.write('B%s'%(cont), asi.asignatura.nombre, formatocelda)
                        ws.write('C%s'%(cont), str(asi.tipomateria) if asi.tipomateria else '', formatocelda)
                        ws.write('D%s'%(cont), str(asi.nivelmalla), formatocelda)
                        ws.write('E%s'%(cont), str(asi.horasacdtotal), formatocelda)
                        ws.write('F%s'%(cont), str(asi.horasapetotal), formatocelda)
                        ws.write('G%s'%(cont), str(asi.horasautonomas), formatocelda)
                        ws.write('H%s'%(cont), str(asi.horas), formatocelda)
                        prac = 'NO'
                        if asi.practicas:
                            prac = 'SI'
                        ws.write('I%s'%(cont), prac, formatocelda)

                        ws.write('J%s'%(cont), str(asi.horasacdsemanal), formatocelda)
                        ws.write('K%s'%(cont), str(asi.horaspresencialessemanales), formatocelda)
                        ws.write('L%s'%(cont), str(asi.horasvirtualsemanal), formatocelda)
                        ws.write('M%s'%(cont), str(asi.horasapesemanal), formatocelda)
                        ws.write('N%s'%(cont), str(asi.horasapeasissemanal), formatocelda)
                        ws.write('O%s'%(cont), str(asi.horasapeautosemanal), formatocelda)
                        ws.write('P%s'%(cont), str(asi.horasautonomassemanales), formatocelda)
                        ws.write('Q%s'%(cont), str(asi.horasvinculacionsemanal), formatocelda)
                        ws.write('R%s'%(cont), str(asi.horasvinculaciontotal), formatocelda)
                        ws.write('S%s'%(cont), str(asi.horaspppsemanal), formatocelda)
                        ws.write('T%s'%(cont), str(asi.horasppptotal), formatocelda)
                        pre = ', '.join([p.predecesora.asignatura.nombre for p in AsignaturaMallaPredecesora.objects.filter(asignaturamalla=asi)])
                        co = ', '.join([c.corequisito.asignatura.nombre for c in AsignaturaMallaCoRequisito.objects.filter(asignaturamalla=asi)])
                        ws.write('U%s'%(cont), pre, formatocelda)
                        ws.write('V%s'%(cont), co, formatocelda)
                        i+=1
                        cont+=1
                    workbook.close()
                    output.seek(0)
                    filename = 'asignaturas_%s.xlsx' % (malla.codigo)
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteasignaturamalla':
                try:
                    malla = Malla.objects.get(pk=int(encrypt(request.GET['id'])))
                    asignaturas = AsignaturaMalla.objects.filter(malla=malla)
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('asignaturas')
                    # ws.set_column(1,10, 40)

                    formatoceldagris = workbook.add_format(
                        {'align': 'center', 'border': 1, 'text_wrap': True, 'fg_color': '#B6BFC0'})
                    formatocelda = workbook.add_format(
                        {'align': 'left', 'border': 1, 'text_wrap': True})
                    formatocelda2 = workbook.add_format(
                        {'align': 'left', 'border': 1, 'bold': 1, 'font_size': 12, 'text_wrap': True})

                    formatotitulo = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 12,'border': 1,'text_wrap': True,'font_color': 'blue'})

                    ws.set_column('A:J', 20, formatoceldagris)
                    ws.set_column('A:J', 20, formatocelda)


                    ws.merge_range(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO',formatotitulo)
                    ws.merge_range(1, 0, 1, 9, 'CANTIDAD ASIGNATURAS PRESENCIALES: '  + str(malla.cantidad_total_materias_presenciales()), formatocelda2)
                    ws.merge_range(2, 0, 2, 9, 'CANTIDAD ASIGNATURAS VIRTUALES: '  + str(malla.cantidad_total_materias_virtuales()), formatocelda2)
                    ws.merge_range(3, 0, 3, 9, 'TOTAL HORAS MALLA (SIN HORAS DE PRÁCTICAS PRE PROFESIONALES): '  + str(malla.suma_horas_validacion_itinerario_sin_practica()), formatocelda2)
                    ws.merge_range(4, 0, 4, 9, 'TOTAL HORAS PRESENCIALES: '  + str(malla.suma_horas_materias_presenciales()), formatocelda2)
                    ws.merge_range(5, 0, 5, 9, 'TOTAL HORAS VIRTUALES: '  + str(malla.suma_horas_materias_virtuales()), formatocelda2)
                    ws.merge_range(6, 0, 6, 9, 'TOTAL PORCENTAJE HORAS PRESENCIALES: '  + str(malla.porcentaje_horasp())+'%' , formatocelda2)
                    ws.merge_range(7, 0, 7, 9, 'TOTAL PORCENTAJE HORAS VIRTUALES: '  + str(malla.porcentaje_horasv())+'%', formatocelda2)



                    ws.write('A9','ORD.',formatoceldagris)
                    ws.write('B9','NOMBRE.',formatoceldagris)
                    ws.write('C9','TIPO DE ASIGNATURA.',formatoceldagris)
                    ws.write('D9','NIVEL.',formatoceldagris)
                    ws.write('E9','MODALIDAD IMPARTICIÓN CLASE.',formatoceldagris)
                    ws.write('F9','HORAS APRENDIZAJE CONTACTO \n DOCENTE (ACD) TOTALES.',formatoceldagris)
                    ws.write('G9','HORAS APRENDIZAJE PRÁCTICO \n EXPERIMENTAL (APE) TOTALES.',formatoceldagris)
                    ws.write('H9','HORAS APRENDIZAJE AUNTÓNOMO \n EXPERIMENTAL (AA) TOTALES.',formatoceldagris)
                    ws.write('I9','HORAS TOTALES',formatoceldagris)
                    ws.write('J9','ASIGNATURA PRÁCTICA',formatoceldagris)
                    cont=10
                    i=1

                    for asi in asignaturas:
                        ws.write('A%s'%(cont), str(i), formatocelda)
                        ws.write('B%s'%(cont), asi.asignatura.nombre, formatocelda)
                        ws.write('C%s'%(cont), str(asi.tipomateria) if asi.tipomateria else '', formatocelda)
                        ws.write('D%s'%(cont), str(asi.nivelmalla), formatocelda)
                        ws.write('E%s'%(cont), 'Presencial' if asi.modalidad() else 'Virtual', formatocelda)
                        ws.write('F%s' % (cont), str(asi.horasacdtotal), formatocelda)
                        ws.write('G%s'%(cont), str(asi.horasapetotal), formatocelda)
                        ws.write('H%s'%(cont), str(asi.horasautonomas), formatocelda)
                        ws.write('I%s'%(cont), str(asi.horas), formatocelda)
                        prac = 'NO'
                        if asi.practicas:
                            prac = 'SI'
                        ws.write('J%s'%(cont), prac, formatocelda)
                        i+=1
                        cont+=1
                    workbook.close()
                    output.seek(0)
                    filename = 'asignaturas_%s.xlsx' % (malla.codigo)
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteasignaturaspdf':
                try:
                    data['malla'] = malla = Malla.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['asignaturas'] = asignaturas = AsignaturaMalla.objects.filter(malla=malla)

                    return conviert_html_to_pdf(
                        'mallas/reporteasignaturas.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'cambioasignatura':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Editar asignatura de malla curricular'
                    data['asignaturamalla'] = am = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    form = CambioAsignaturaMallaForm(initial={"asignatura": am.asignatura})
                    data['form'] = form
                    return render(request, "mallas/cambioasignatura.html", data)
                except Exception as ex:
                    pass

            elif action == 'alumnosmalla':
                try:
                    mallaid = request.GET['id']

                    malla = Malla.objects.get(pk=mallaid)
                    facultad = malla.carrera.mi_coordinacion()
                    codigomalla = malla.codigo if malla.codigo else ''
                    carreramalla = malla.carrera.nombre

                    __author__ = 'Unemi'
                    title2 = easyxf(
                        'font: name Verdana, color-index black, bold on , height 270; alignment: horiz centre')

                    stylec = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre', num_format_str='yyyy-mm-dd')
                    styler2 = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
                    stylel = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz left')
                    styler = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str='#,##0.00')

                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title2)
                    ws.write_merge(1, 1, 0, 6, facultad, title2)
                    ws.write_merge(2, 2, 0, 6, 'MALLA - ' + codigomalla + ' - ' + carreramalla, title2)
                    ws.write_merge(3, 3, 0, 6, 'Listado de Alumnos vinculados a la malla', title2)

                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=ALUMNOS_MALLA_' + mallaid.__str__() + '.xls'
                    columns = [
                        (u"#",1100),
                        (u"CÉDULA", 4000),
                        (u"NOMBRES/APELLIDOS", 9000),
                        (u"CARRERA", 9000),
                        (u"AÑO DE MALLA", 3200),
                        (u"SEXO", 3000),
                        (u"F.INGRESO 1ER NIVEL", 3800)
                    ]

                    row_num = 4
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    inscripciones = Inscripcion.objects.filter(inscripcionmalla__malla=mallaid).order_by('persona__apellido1','persona__apellido2','persona__nombres')

                    row_num += 1
                    cont = 0

                    for a in inscripciones:
                        cont += 1
                        ws.write(row_num, 0, cont, styler2)
                        ws.write(row_num, 1, a.persona.cedula, stylec)
                        ws.write(row_num, 2, (a.persona.apellido1 + ' ' + a.persona.apellido2 + ' ' + a.persona.nombres), stylel)
                        ws.write(row_num, 3, a.carrera.nombre, stylel)
                        insmalla = a.inscripcionmalla_set.filter(status=True)[0]
                        ws.write(row_num, 4, insmalla.malla.inicio.year, stylel)
                        ws.write(row_num, 5, a.persona.sexo.nombre, stylel)
                        ws.write(row_num, 6, a.fechainicioprimernivel, stylec)
                        row_num += 1

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'requisitos':
                try:
                    data['title'] = u'Requisitos de mallas curriculares'
                    data['malla'] = malla = Malla.objects.filter(carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    data['requisitos'] = malla.requisitosmalla_set.all()
                    return render(request, "mallas/requisitos.html", data)
                except Exception as ex:
                    pass

            elif action == 'integracioncurricular':
                try:
                    data['title'] = u'Requisitos de Ingreso Unidad Integración Curricular'
                    data['eAsignaturaMalla'] = eAsignaturaMalla = AsignaturaMalla.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['malla'] = eAsignaturaMalla.malla
                    data['integracioncurricular'] = eAsignaturaMalla.requisitoingresounidadintegracioncurricular_set.all()
                    puede_modificar_mallas = True
                    if not persona.usuario.is_superuser:
                        if not persona.usuario.has_perm('sga.puede_modificar_mallas'):
                            puede_modificar_mallas = False
                        elif not persona.usuario.has_perm('sga.puede_editar_requisitos_ingreso_integracion_curricular'):
                            puede_modificar_mallas = False
                        elif eAsignaturaMalla.malla.cerrado:
                            puede_modificar_mallas = False
                    data['puede_modificar_mallas'] = puede_modificar_mallas
                    return render(request, "mallas/integracioncurricular.html", data)
                except Exception as ex:
                    pass

            elif action == 'editrequisito':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Editar requisito'
                    data['requisito'] = requisito = RequisitosMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    form = RequisitoMallaForm(initial={'nombre': requisito.nombre,
                                                       'cantidad': requisito.cantidad,
                                                       'requisitos': requisito.requisitos.all()})
                    data['form'] = form
                    return render(request, "mallas/editrequisito.html", data)
                except Exception as ex:
                    pass

            elif action == 'editintegracioncurricular':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Editar Requisitos de Ingreso Unidad Integración Curricular'
                    data['requisito'] = requisito = RequisitoIngresoUnidadIntegracionCurricular.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = IntegracionCurricularForm(initial={'funcion': requisito.requisito,
                                                              'orden': requisito.orden,
                                                              'activo': requisito.activo,
                                                              'obligatorio': requisito.obligatorio,
                                                              'enlineamatriculacion': requisito.enlineamatriculacion})
                    data['form'] = form
                    return render(request, "mallas/editintegracioncurricular.html", data)
                except Exception as ex:
                    pass

            elif action == 'syllabus':
                try:
                    data['title'] = u'Sílabo de la materia:'
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    data['archivos'] = asignaturamalla.archivo_set.all().order_by('-fecha')
                    return render(request, "mallas/syllabus.html", data)
                except Exception as ex:
                    pass

            elif action == 'addrequisito':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Adicionar requisito'
                    data['malla'] = malla = Malla.objects.filter(carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    form = RequisitoMallaForm(initial={"malla": malla,
                                                       "cantidad": 1})
                    data['form'] = form
                    return render(request, "mallas/addrequisito.html", data)
                except Exception as ex:
                    pass

            elif action == 'addintegracioncurricular':
                try:
                    orden = 1
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Adicionar Integración Curricular'
                    data['eAsignaturaMalla'] = eAsignaturaMalla = AsignaturaMalla.objects.get(pk=int(encrypt(request.GET['id'])))
                    if eAsignaturaMalla:
                        if RequisitoIngresoUnidadIntegracionCurricular.objects.filter(status=True, asignaturamalla=eAsignaturaMalla).exists():
                            requisito = RequisitoIngresoUnidadIntegracionCurricular.objects.filter(status=True, asignaturamalla=eAsignaturaMalla).order_by('id').last()
                            orden = int(requisito.orden) + 1
                    form = IntegracionCurricularForm(initial={"orden": orden})
                    data['form'] = form
                    return render(request, "mallas/addintegracioncurricular.html", data)
                except Exception as ex:
                    pass

            elif action == 'delpredecesora':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    predecesora = AsignaturaMallaPredecesora.objects.filter(asignaturamalla__malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    asignaturamalla = predecesora.asignaturamalla
                    log(u'Elimino predecesora: %s' % asignaturamalla, request, "del")
                    predecesora.delete()
                    return HttpResponseRedirect("/mallas?action=predecesora&id=" + str(encrypt(asignaturamalla.id)))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'programaanaliticomalla':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Plan de Estudio Malla'
                    data['malla'] = malla = Malla.objects.filter(pk=request.GET['id'])[0]
                    data['programaanaliticomalla'] = programaanaliticomalla = ProgramaAnaliticoMalla.objects.filter(malla=malla)
                    return render(request, "mallas/programaanaliticomalla.html", data)
                except Exception as ex:
                    pass

            elif action == 'addprogramaanaliticomalla':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Adicionar Plan de Estudio Malla'
                    data['malla'] = malla = Malla.objects.filter(pk=request.GET['id'])[0]
                    data['form'] = ProgramaAnaliticoMallaForm(initial={'fecha': datetime.now().date()})
                    return render(request, "mallas/addprogramaanaliticomalla.html", data)
                except Exception as ex:
                    pass

            elif action == 'editprogramaanaliticomalla':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Editar Plan de Estudio Malla'
                    data['programaanaliticomalla'] = programaanaliticomalla = ProgramaAnaliticoMalla.objects.filter(pk=request.GET['id'])[0]
                    form = ProgramaAnaliticoMallaForm(initial={'descripcion': programaanaliticomalla.descripcion,
                                                               'fecha': programaanaliticomalla.fecha})
                    form.editar()
                    data['form'] = form
                    return render(request, "mallas/editprogramaanaliticomalla.html", data)
                except Exception as ex:
                    pass

            elif action == 'aprobarprogramaanaliticomalla':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    malla = Malla.objects.filter(pk=request.GET['idm'])[0]
                    ProgramaAnaliticoMalla.objects.filter(malla=malla).update(aprobado=False)
                    programaanaliticomalla = ProgramaAnaliticoMalla.objects.filter(pk=request.GET['id'])[0]
                    programaanaliticomalla.aprobado = True
                    programaanaliticomalla.save(request)
                    log(u'Aprobo Plan de Estudio Malla: %s' % programaanaliticomalla, request, "edit")
                    return HttpResponseRedirect("/mallas?action=programaanaliticomalla&id=" + request.GET['idm'])
                except Exception as ex:
                    pass

            elif action == 'programaanaliticoasignaturamalla':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Programa Analítico Asignatura Malla'
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(pk=int(encrypt(request.GET['id'])))[0]
                    data['programaanaliticoasignaturamalla'] = programaanaliticoasignaturamalla = ProgramaAnaliticoAsignaturaMalla.objects.filter(asignaturamalla=asignaturamalla)
                    return render(request, "mallas/programaanaliticoasignaturamalla.html", data)
                except Exception as ex:
                    pass

            elif action == 'addprogramaanaliticoasignaturamalla':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Adicionar Programa Analítico Asignatura Malla'
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(pk=request.GET['id'])[0]
                    data['form'] = ProgramaAnaliticoAsignaturaMallaForm(initial={'fecha': datetime.now().date()})
                    return render(request, "mallas/addprogramaanaliticoasignaturamalla.html", data)
                except Exception as ex:
                    pass

            elif action == 'editprogramaanaliticoasignaturamalla':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Editar Programa Analítico Asignatura Malla'
                    data['programaanaliticoasignaturamalla'] = programaanaliticoasignaturamalla = ProgramaAnaliticoAsignaturaMalla.objects.filter(pk=request.GET['id'])[0]
                    form = ProgramaAnaliticoAsignaturaMallaForm(initial={'descripcion': programaanaliticoasignaturamalla.descripcion,
                                                                         'fecha': programaanaliticoasignaturamalla.fecha})
                    form.editar()
                    data['form'] = form
                    return render(request, "mallas/editprogramaanaliticoasignaturamalla.html", data)
                except Exception as ex:
                    pass

            elif action == 'listacamposocupacionales':
                try:
                    data['title'] = u'Listado campos ocupacionales'
                    data['malla'] = malla = Malla.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['listacampos'] = CamposOcupacionalesMalla.objects.filter(malla=malla,status=True).order_by('id')
                    return render(request, "mallas/listacamposocupacionales.html", data)
                except Exception as ex:
                    pass

            elif action == 'listarotacion':
                try:
                    data['title'] = u'Listado campos rotación'
                    data['malla'] = malla = Malla.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['listacampos'] = RotacionesMalla.objects.filter(malla=malla,status=True).order_by('id')
                    return render(request, 'mallas/listarotacion.html', data)
                except Exception as ex:
                    pass

            elif action == 'listaitinerarios':
                try:
                    data['title'] = u'Listado itinerarios para prácticas preprofesionales'
                    data['malla'] = malla = Malla.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['listacampos'] = ItinerariosMalla.objects.filter(malla=malla,status=True).order_by('id')
                    return render(request, "mallas/listaitinerarios.html", data)
                except Exception as ex:
                    pass

            elif action == 'addasignaturaitinerario':
                try:
                    data['action'] = request.GET['action']
                    data['title'] = u'Adicionar turno'
                    data['idp'] = idp = int(request.GET['idp'])
                    iti = ItinerariosMalla.objects.get(pk=idp)
                    form = ItinerarioAsignaturaMallaForm()
                    form.iniciar(iti)
                    data['form'] = form
                    template = get_template("mallas/modal/formasignaturamalla.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'listaritinerariosvinculacion':
                try:
                    data['title'] = u'Listado itinerarios para proyectos de vinculación'
                    data['malla'] = malla = Malla.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['listacamposvinculacion'] = ItinerariosVinculacionMalla.objects.filter(malla=malla, status=True).order_by('id')
                    return render(request, "mallas/listaitinerariosvinculacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addrequisitoscarrera':
                try:
                    data['action'] = action
                    data['id'] = id = request.GET['id']
                    data['tipoid'] = tipoid = request.GET['tipo']
                    data['itinerario'] = itinerario = ItinerariosMalla.objects.get(pk=id)
                    excluir = ItinerariosMallaDocumentosBase.objects.filter(itinerario=itinerario, tipo=tipoid, status=True).values_list('documento_id', flat=True)
                    form = DocumentoRequeridoCarreraForm()
                    form.fields['documento'].queryset = RequisitosHomologacionPracticas.objects.filter(status=True).exclude(id__in=excluir)
                    data['form2'] = form
                    template = get_template("alu_practicaspreprofesionalesinscripcion/modal/formdocumentositinerarios.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'requisitoshomologacion':
                try:
                    data['title'] = u'Requisitos Homologación Practicas'
                    data['malla'] = malla = Malla.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['tipos'] = TIPO_DOCUMENTO_HOMOLOGACION
                    data['listacampos'] = ItinerariosMalla.objects.filter(malla=malla,status=True).order_by('id')
                    return render(request, "mallas/requisitositinerarios.html", data)
                except Exception as ex:
                    pass

            elif action == 'turnoshorarios':
                try:
                    data['title'] = u'Listado Horarios'
                    data['malla'] = malla = Malla.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['listadohorarios'] = malla.horariovirtual_set.filter(periodo=periodo, status=True).order_by('-id')
                    return render(request, "mallas/turnoshorarios.html", data)
                except Exception as ex:
                    pass

            elif action == 'estudianteshorarios':
                try:
                    data['title'] = u'Listado Estudiantes'
                    data['horario'] = horario = HorarioVirtual.objects.get(pk=int(encrypt(request.GET['idhorario'])))
                    data['listadoparticipantes'] = horario.participanteshorariovirtual_set.filter(status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    return render(request, "mallas/estudianteshorarios.html", data)
                except Exception as ex:
                    pass

            elif action == 'addhorarioturno':
                try:
                    data['title'] = u'Adicionar Horario'
                    idnivel = 1
                    data['malla'] = malla = Malla.objects.get(pk=int(encrypt(request.GET['idmalla'])))
                    data['laboratorio'] = LaboratorioVirtual.objects.filter(status=True).order_by('sedevirtual_id')
                    data['dias'] = DiaSemana.objects.filter(status=True)
                    data['turnos'] = TurnoVirtual.objects.filter(status=True).order_by('comienza')
                    data['listaniveles'] = NivelMalla.objects.filter(status=True).order_by('id')
                    if 'idnivel' in request.GET:
                        idnivel = request.GET['idnivel']
                    data['idnivel'] = int(idnivel)
                    data['listadoasignaturas'] = listadoasignaturas = malla.asignaturamalla_set.filter(nivelmalla_id=idnivel, status=True).order_by('nivelmalla_id')
                    data['totalasignaturas'] = listadoasignaturas.count()
                    return render(request, "mallas/addhorarioturno.html", data)
                except Exception as ex:
                    pass

            elif action == 'alumnoscarrera':
                try:
                    data['title'] = u'Listado'
                    data['horariovirtual'] = horariovirtual = HorarioVirtual.objects.get(pk=int(encrypt(request.GET['idhorario'])))
                    ida=DetalleHorarioVirtual.objects.values_list('asignatura__id',flat=True).filter(status=True,horariovirtual=horariovirtual)
                    data['matriculados'] = Matricula.objects.filter(inscripcion__inscripcionmalla__malla=horariovirtual.malla, materiaasignada__materia__asignatura__id__in =ida,
                                                                    nivel__periodo=periodo, nivel__sesion_id=13).exclude(pk__in=ParticipantesHorarioVirtual.objects.values_list('matricula_id').filter(horariovirtual=horariovirtual)).order_by('nivelmalla_id', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2').distinct()
                    # InscripcionMalla.
                    # codigomatricula = MateriaAsignada.objects.values_list('matricula_id').filter(materia__asignaturamalla__malla=horariovirtual.malla, materia__nivel__periodo=periodo, materia__nivel__sesion_id=13,  status=True).exclude(matricula_id__in=ParticipantesHorarioVirtual.objects.values_list('matricula_id')).distinct()
                    # data['matriculados'] = Matricula.objects.filter(pk__in=codigomatricula, status=True).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')
                    return render(request, "mallas/alumnoscarrera.html", data)
                except Exception as ex:
                    pass

            elif action == 'aprobarprogramaanaliticoasignaturamalla':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    asignaturamalla = AsignaturaMalla.objects.filter(pk=request.GET['idm'])[0]
                    ProgramaAnaliticoAsignaturaMalla.objects.filter(asignaturamalla=asignaturamalla).update(aprobado=False)
                    programaanaliticoasignaturamalla = ProgramaAnaliticoAsignaturaMalla.objects.filter(pk=request.GET['id'])[0]
                    programaanaliticoasignaturamalla.aprobado = True
                    programaanaliticoasignaturamalla.save(request)
                    log(u'Aprobo Programa Analítico Asignatura Malla: %s' % programaanaliticoasignaturamalla, request, "edit")
                    return HttpResponseRedirect("/mallas?action=programaanaliticoasignaturamalla&id=" + encrypt(request.GET['idm']))
                except Exception as ex:
                    pass

            elif action == 'titulosafin':
                try:
                    data['title'] = u'Mallas curriculares'
                    data['mallas'] = mallas = Malla.objects.filter(status=True, vigente=True).exclude(carrera__id__in=[34,37]).order_by('carrera')
                    if 'idmallaselect' in request.GET:
                        idmallaselect = request.GET['idmallaselect']
                    else:
                        idmallaselect = mallas[0].id
                    data['mallaselect'] = Malla.objects.filter(status=True, vigente=True, id=idmallaselect).order_by('carrera')
                    data['idmallaselect'] = int(idmallaselect)
                    data['permite_modificar'] = False
                    return render(request, "mallas/titulosafin.html", data)
                except Exception as ex:
                    pass

            elif action == 'addbibliografiaapa':
                try:
                    data['title'] = u'Bibliografía básica formato APA'
                    data['programanalitico'] = programanalitico = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['bibliografias'] = programanalitico.bibliografiaapaprogramaanaliticoasignatura_set.filter(status=True)
                    return render(request, "mallas/listadobibliografiaapa.html", data)
                except Exception as ex:
                    pass

            elif action == 'addapa':
                try:
                    data['title'] = u'Adicionar Bibliografía básica formato APA'
                    data['programanalitico'] = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = BibliografiaApaProgramaAnaliticoAsignaturaForm()
                    return render(request, "mallas/addapa.html", data)
                except Exception as ex:
                    pass

            elif action == 'editapa':
                try:
                    data['title'] = u'Editar Bibliografía básica formato APA'
                    data['bibliografia'] = bibliografia = BibliografiaApaProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])), programaanaliticoasignatura_id=int(encrypt(request.GET['idp'])))
                    data['form'] = BibliografiaApaProgramaAnaliticoAsignaturaForm(initial={'bibliografia':bibliografia.bibliografia})
                    return render(request, "mallas/editapa.html", data)
                except Exception as ex:
                    pass

            elif action == 'delapa':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Eliminar la Bibliografía APA'
                    data['bibliografia'] = BibliografiaApaProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "mallas/delapa.html", data)
                except Exception as ex:
                    pass

            elif action == 'relacionarcarrera':
                try:
                    data['title'] = u'Relacionar carrera'
                    data['pro'] = pro = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    autor = None
                    if AutorprogramaAnalitico.objects.filter(status=True, periodo=periodo, programaanalitico=pro).exists():
                        autor = AutorprogramaAnalitico.objects.filter(status=True, periodo=periodo, programaanalitico=pro)[0]
                        form = AutorprogramaAnaliticoForm(initial={'autor':autor.autor.id, 'programa':autor.programasanaliticos_relacionados()})
                        form.editar(autor)
                    else:
                        form = AutorprogramaAnaliticoForm()
                    form.cargar_programaanalitico(pro)
                    data['autor'] = autor
                    data['form'] = form
                    return render(request, "mallas/relacionarcarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'asigprocedimiento':
                try:
                    data['title'] = u'Asignar procedimiento de evaluación'
                    data['pro'] = pro = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['procedimientos'] = procedimientos = CabProcedimientoEvaluacionPa.objects.filter(status=True)
                    return render(request, "mallas/asignarprocedimiento.html", data)
                except Exception as ex:
                    pass

            elif action == 'mecanismotitulacion':
                try:
                    data['title'] = u'Titulación PosGrado'
                    malla = Malla.objects.get(pk=int(request.GET['id']))
                    form = MecanismoTitulacionPosgradoMallaForm(initial={'malla': malla,
                                                                         'numerotutorias': malla.numerotutorias})
                    form.mecanismo()
                    data['malla'] = malla
                    data['mecanismos'] = MecanismoTitulacionPosgrado.objects.filter(status=True)
                    data['form'] = form
                    data['c'] = int(request.GET['c'])
                    data['n'] = int(request.GET['n'])
                    data['mc'] = int(request.GET['mc'])
                    data['a'] = int(request.GET['a'])
                    data['carr'] = int(request.GET['carr'])
                    idmecanismos = malla.mecanismotitulacionposgradomalla_set.values_list('mecanismotitulacionposgrado_id', flat=True).filter(status=True)
                    data['enuso'] = TemaTitulacionPosgradoMatricula.objects.filter(matricula__inscripcion__inscripcionmalla__malla=malla ,status=True, mecanismotitulacionposgrado_id__in=idmecanismos, mecanismotitulacionposgrado__status=True).exists()
                    return render(request, "mallas/mecanismotitulacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'requisitostitulacionmalla':
                try:
                    data['title'] = u'Listado de requisitos para proceso de titulación'
                    malla = Malla.objects.get(pk=int(request.GET['id']))
                    data['malla'] = malla
                    data['c'] = int(request.GET['c'])
                    data['n'] = int(request.GET['n'])
                    data['mc'] = int(request.GET['mc'])
                    data['a'] = int(request.GET['a'])
                    data['carr'] = int(request.GET['carr'])
                    data['listadorequisitos'] = malla.requisitotitulacionmalla_set.filter(status=True).order_by('requisito__nombre')
                    return render(request, "mallas/requisitostitulacionmalla.html", data)
                except Exception as ex:
                    pass

            if action == 'listadorequisitostitulacion':
                try:
                    lista = []
                    idmalla = int(request.GET['idmalla'])
                    listadorequisitostitulacion = FuncionRequisitoIngresoUnidadIntegracionCurricular.objects.filter(status=True).exclude(pk__in=RequisitoTitulacionMalla.objects.values_list('requisito_id').filter(malla_id=idmalla, status=True)).order_by('id')
                    for lis in listadorequisitostitulacion:
                        lista.append([lis.id, lis.nombre])
                    data = {"results": "ok", 'listado': lista}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'listaitinerariosespecialidad':
                try:
                    data['title'] = u'Listado itinerarios para asignaturas'
                    data['malla'] = malla = Malla.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['itinerarios'] = ItinerarioMallaEspecilidad.objects.filter(malla=malla,status=True).order_by('id')
                    return render(request, "mallas/listaitinerariosespecialidad.html", data)
                except Exception as ex:
                    pass

            elif action == 'additinerarioespecial':
                try:
                    data['title'] = u'Adicionar itinerario'
                    data['malla'] = Malla.objects.get(pk=int(encrypt(request.GET['idmalla'])))
                    form = ItinerarioMallaEspecilidadForm()
                    data['form'] = form
                    return render(request, "mallas/additinerarioespecial.html", data)
                except Exception as ex:
                    pass

            elif action == 'edititinerarioespecial':
                try:
                    data['title'] = u'Editar itinerario'
                    data['itinerarioespecial'] = itinerarioespecial = ItinerarioMallaEspecilidad.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = ItinerarioMallaEspecilidadForm(initial={'nombre': itinerarioespecial.nombre,
                                                                   'itinerario': itinerarioespecial.itinerario,
                                                                   'numero':itinerarioespecial.numeroresolucion
                                                                   })
                    data['form'] = form
                    return render(request, "mallas/edititinerarioespecial.html", data)
                except Exception as ex:
                    pass

            elif action == 'delitinerarioespecial':
                try:
                    data['title'] = u'Eliminar itinerario'
                    data['itinerarioespecial'] = ItinerarioMallaEspecilidad.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "mallas/delitinerarioespecial.html", data)
                except Exception as ex:
                    pass

            elif action == 'cerrarmalla':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Cerrar malla curricular'
                    data['malla'] = Malla.objects.filter(carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "mallas/cerrarmalla.html", data)
                except Exception as ex:
                    pass

            elif action == 'abrirmalla':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_mallas')
                    data['title'] = u'Abrir malla curricular'
                    data['malla'] = Malla.objects.filter(carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "mallas/abrimalla.html", data)
                except Exception as ex:
                    pass

            elif action == 'listamodalidad':
                data['title'] = u'Modalidad'
                search = None
                modalidade = Modalidad.objects.filter(status=True)
                if 's' in request.GET:
                    search = request.GET['s']
                    modalidade= modalidade.filter(Q(nombre__icontains=search))

                paging = MiPaginador(modalidade, 20)
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
                data['modalidad'] = page.object_list
                return render(request, 'mallas/listamodalidad.html', data)

            elif action == 'addmodalidad':
                try:
                    data['title']=u'Adicionar Modalidad'
                    data['form2'] = ModalidadForm()
                    data['action'] = action
                    template = get_template("mallas/modal/modal_modalidad.html")
                    return JsonResponse({"result":True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al adicionar los datos."})

            elif action == 'editmodalidad':
                try:
                    data['title'] = u'Editar Modalidad '
                    data['modalidad'] = modalidad = Modalidad.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['id'] = int(encrypt(request.GET['id']))
                    data['form2'] = ModalidadForm(initial=model_to_dict(modalidad))
                    data['action'] = action
                    template = get_template("mallas/modal/modal_modalidad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al editar los datos."})

            elif action == 'deletemodalidad':
                try:
                    data['title'] = u'Eliminar Modalidad '
                    data['modalidad'] = Modalidad.objects.get(pk=encrypt(request.GET['id']))
                    data['action'] = action
                    return render(request, 'mallas/deletemodalidad.html', data)
                except Exception as ex:
                    pass

            elif action == 'imparticionclase':
                try:
                    data['title'] = u'Adicionar Modalidad Impartición Clase'
                    data['asigmalla'] = asigmalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(encrypt(request.GET['id'])))
                    detasig = DetalleAsignaturaMallaModalidad.objects.get(status=True, asignaturamalla_id = asigmalla)
                    data['form'] = AsignaturaMallaModalidadForm(initial=model_to_dict(detasig))
                    return render(request, "mallas/addimparticion.html", data)
                except Exception as ex:
                    pass

            elif action == 'cambiarasignatura':
                try:

                    data['asigm'] = asignm = AsignaturaMalla.objects.get(pk=request.GET['id'])
                    data['total_record'] = RecordAcademico.objects.filter(asignaturamalla=asignm).count()
                    data['total_hrecord'] = HistoricoRecordAcademico.objects.filter(asignaturamalla=asignm).count()
                    data['total_materia'] = Materia.objects.filter(asignaturamalla=asignm).count()
                    data['title'] = u'Cambiar Asignatura:{} de la malla {}'.format(asignm.asignatura.nombre, asignm.malla.__str__())
                    asignmall = AsignaturaMalla.objects.filter(asignatura=asignm.asignatura).exclude(pk=asignm.id)
                    data['mallas'] = Malla.objects.filter(pk__in=asignmall.values_list('malla_id',flat=True))
                    data['action'] = action
                    template = get_template("mallas/modal/modal_cambiarasignatura.html")
                    return JsonResponse({"result": True, 'data': template.render(data), 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al editar los datos."})

            elif action == 'cambiarmodalidadasignatura':
                try:

                    data['asigmalla'] = asigmalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=int(request.GET['id']))
                    detasig = DetalleAsignaturaMallaModalidad.objects.get(status=True, asignaturamalla_id=asigmalla)
                    data['form'] = AsignaturaMallaModalidadForm(initial=model_to_dict(detasig))
                    template = get_template("mallas/modal/modal_cambiarmodalidadasignatura.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al editar los datos."})

            elif action == 'loadFormEditarCarrera':
                try:
                    f = EditarNombreCarreraForm()
                    id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                    if not Malla.objects.filter(pk=id).exists():
                        raise NameError(u"No existe carrera a editar")
                    eMalla = Malla.objects.get(pk=id)
                    eCarrera = eMalla.carrera
                    f.set_initial(eCarrera)
                    puede_realizar_accion(request, 'sga.puede_modificar_nombre_carrera')
                    data['eCarrera'] = eCarrera
                    data['form'] = f
                    data['frmName'] = "frmCarrera"
                    template = get_template("mallas/editarNombreCarrera.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content, 'malla_str': eMalla.__str__()})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'homologacionmalla':
                try:
                    # Malla Seleccionada
                    data['title']='Homologacion Malla'
                    data['malla'] = Malla.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['modalidades']=Modalidad.objects.filter(status=True).exclude(id=4)
                    if 'iddestino' in request.GET:
                        data['malladestino']=Malla.objects.get(pk=int(request.GET['iddestino']))
                    return render(request, "mallas/homologacionmalla.html", data)
                except  Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al cargar los datos."})

            elif action == 'tablahomologacion':
                try:
                    # Visualizar asignaturas y sus homologaciones
                    data['malladestino'] = False
                    if 'iddestino' in request.GET:
                        data['malladestino'] = Malla.objects.get(pk=request.GET['iddestino'])
                    data['malla'] = malla = Malla.objects.get(pk=request.GET['origen'])
                    ejesenuso = AsignaturaMalla.objects.values_list('ejeformativo_id', flat=True).filter(malla_id=malla).distinct()
                    data['nivelesdemallas'] = NivelMalla.objects.all().order_by('id')
                    data['ejesformativos'] = EjeFormativo.objects.filter(id__in=ejesenuso).order_by('nombre')
                    data['asignaturasmallas'] = AsignaturaMalla.objects.filter(malla=malla)
                    data['costo_en_malla'] = COSTO_EN_MALLA
                    template = get_template("mallas/modal/listartablahomologacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            elif action == 'malladestino':
                try:
                    # Visualizar asignaturas de malladestino
                    id=request.GET['id']
                    iddestino=int(request.GET['iddestino'])
                    data['idorigen']=id
                    data['malla'] = malla = Malla.objects.get(pk=iddestino)
                    ejesenuso = AsignaturaMalla.objects.values_list('ejeformativo_id', flat=True).filter(malla_id=malla).distinct()
                    asignaturas=AsignaturaMalla.objects.filter(malla=malla, status=True)
                    data['niveles']=niveles=NivelMalla.objects.all().order_by('id')

                    nivel, search, url_vars=request.GET.get('nivel', ''),request.GET.get('search', ''), ''

                    if nivel:
                        niveles=niveles.filter(id=int(nivel))
                        data['nivelselect']=int(nivel)
                    if search:
                        data['search'] = search
                        asignaturas = asignaturas.filter(asignatura__nombre__icontains=search)
                    if nivel or search:
                        url_vars += '?action={}&id={}&iddestino={}'.format(action, id, iddestino)
                        data["url_vars"] = url_vars
                    data['iddestino'] = encrypt(iddestino)
                    data['nivelesdemallas'] = niveles
                    data['ejesformativos'] = EjeFormativo.objects.filter(id__in=ejesenuso).order_by('nombre')
                    data['asignaturasmallas'] = asignaturas
                    data['costo_en_malla'] = COSTO_EN_MALLA
                    return render(request, "mallas/asignaturas.html", data)
                    # template = get_template("mallas/asignaturas.html")
                    # return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            elif action == 'addhomologacionasignaturas':
                try:
                    idm=request.GET['idmalladestino']
                    ida=request.GET['idasignaturaorigen']
                    data['action']=action
                    data['malladestino'] = Malla.objects.get(id=idm)
                    data['asignaturaorigen'] = AsignaturaMalla.objects.get(id=ida)
                    data['asignaturasdestino']= AsignaturaMalla.objects.filter(malla=idm, status=True)
                    template = get_template("mallas/modal/modal_asignaturasmalladestino.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            elif action == 'listaunidadorganizacioncurricular':
                data['title'] = u'Unidades Organizaciones Curriculares'
                search = None
                unidadescurriculares = UnidadOrganizacionCurricular.objects.filter(status=True)
                if 's' in request.GET:
                    search = request.GET['s']
                    unidadescurriculares = unidadescurriculares.filter(Q(nombre__icontains=search))

                paging = MiPaginador(unidadescurriculares, 20)
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
                data['listado'] = page.object_list
                return render(request, 'mallas/listaunidadorganizacioncurricular.html', data)

            elif action == 'addunidadorganizacioncurricular':
                try:
                    data['title'] = u'Adicionar Unidad Organización Curricular'
                    data['form2'] = UnidadOrganizacionCurricularForm()
                    data['action'] = action
                    template = get_template("mallas/modal/modal_unidadorganizacioncurricular.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al adicionar los datos."})

            elif action == 'editunidadorganizacioncurricular':
                try:
                    data['title'] = u'Editar Unidad Organización Curricular'
                    data['unidadorganizacioncurricular'] = unidadorganizacioncurricular = UnidadOrganizacionCurricular.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['id'] = int(encrypt(request.GET['id']))
                    data['form2'] = UnidadOrganizacionCurricularForm(initial=model_to_dict(unidadorganizacioncurricular))
                    data['action'] = action
                    template = get_template("mallas/modal/modal_unidadorganizacioncurricular.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al editar los datos."})

            elif action == 'showmallacurricular':
                try:
                    data['malla'] = malla = Malla.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Malla del alumno'
                    data['nivelesdemallas'] = nivelesmalla = malla.niveles_malla()
                    data['colspan_general'] = nivelesmalla.count() - 2
                    data['ejesformativos'] = ejesformativos = malla.ejesformativos_malla()
                    data['coordinacion'] = malla.carrera.coordinacion_carrera() if malla.carrera else None
                    data['pagesize'] = 'A4'
                    data['rowasignaturas'] = [i for i in range(0, malla.obtner_numero_mayor_asignaturamalla())]
                    return conviert_html_to_pdf(

                        'mallas/pdf/newmallacurricular.html',

                        data

                    )

                except Exception as ex:

                    pass

            elif action == 'addarchivomalla':
                try:

                    activo = Malla.objects.get(pk=int(encrypt(request.GET['id'])))
                    if activo.archivo:
                        data['filtro'] = filtro = Malla.objects.get(pk=int(encrypt(request.GET['id'])))
                        data['idmalla'] = encrypt(request.GET['id'])
                        data['tipo'] = request.GET['tipo']
                        if int(request.GET['tipo']) ==1:
                            data['form2'] = ArchivoMallasForm(initial={'archivo':filtro.archivo})
                        elif int(request.GET['tipo']) ==2:
                            data['form2'] = ArchivoMallasForm(initial={'archivo': filtro.archivo_proyecto})
                        else:
                            data['form2'] = ArchivoMallasForm(initial={'archivo': filtro.archivo_proyectorediseñado})
                    else:
                        form2 = ArchivoMallasForm()
                        data['idmalla'] = encrypt(request.GET['id'])
                        data['tipo'] = request.GET['tipo']
                        data['form2'] = form2

                    template = get_template("mallas/addarchivomallas.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'listaplanes':
                try:
                    data['title'] = 'Lista de Planes Analíticos'
                    data['niveles'] = niveles = NivelMalla.objects.filter(status=True)
                    data['coordinaciones'] = coordinaciones = Coordinacion.objects.filter(status=True)
                    data['carreras'] = carreras = Carrera.objects.filter(status=True)
                    data['modalidadcarrera'] = modalidadcarrera = Modalidad.objects.filter(status=True)

                    search = None
                    modalidadcarreraselect = int(request.GET['mc']) if 'mc' in request.GET else 0
                    coordinacionselect = int(request.GET['c']) if 'c' in request.GET else 0
                    carreraselect = int(request.GET['carr']) if 'carr' in request.GET else 0
                    nivelselect = int(request.GET['n']) if 'n' in request.GET else 0
                    anioselect = int(request.GET['a']) if 'a' in request.GET else 0
                    malla = Malla.objects.filter(status=True).distinct()
                    aniosmalla = malla.values_list('inicio').distinct().order_by('-inicio')
                    anios = []
                    for anio in aniosmalla:
                        if anio[0].year not in anios:
                            anios.append(anio[0].year)
                    url_vars = ''
                    if anioselect > 0:
                        malla = malla.filter(inicio__year=anioselect)
                        codigoscarrera = malla.values_list('carrera__id', flat=True).filter(status=True, carrera__isnull=False)
                        codigocoordinaciones = codigoscarrera.values_list('carrera__coordinacion__id', flat=True).filter(status=True, carrera__coordinacion__isnull=False)
                        carreras = carreras.filter(id__in=codigoscarrera)
                        coordinaciones = coordinaciones.filter(id__in=codigocoordinaciones)
                        url_vars += "&a={}".format(anioselect)
                    if modalidadcarreraselect > 0:
                        malla = malla.filter(modalidad_id=modalidadcarreraselect)
                        codigoscarrera = malla.values_list('carrera__id', flat=True).filter(status=True, carrera__isnull=False)
                        codigocoordinaciones = codigoscarrera.values_list('carrera__coordinacion__id', flat=True).filter(status=True, carrera__coordinacion__isnull=False)
                        carreras = carreras.filter(id__in=codigoscarrera)
                        coordinaciones = coordinaciones.filter(id__in=codigocoordinaciones)
                        url_vars += "&mc={}".format(modalidadcarreraselect)
                    if coordinacionselect > 0:
                        malla = malla.filter(carrera__coordinacion__id=coordinacionselect)
                        codigoscarrera = malla.values_list('carrera__id', flat=True).filter(status=True)
                        carreras = carreras.filter(id__in=codigoscarrera)
                        url_vars += "&c={}".format(coordinacionselect)
                    if carreraselect > 0:
                        malla = malla.filter(carrera_id=carreraselect)
                        url_vars += "&carr={}".format(carreraselect)
                    asignaturas = AsignaturaMalla.objects.filter(status=True, malla_id__in=malla.values_list('id', flat=True))
                    if nivelselect > 0:
                        asignaturas = asignaturas.filter(nivelmalla_id=nivelselect).distinct('asignatura')
                        url_vars += "&n={}".format(nivelselect)
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            asignaturas = asignaturas.filter(asignatura__nombre__unaccent__icontains=ss[0]).distinct().order_by('asignatura__nombre')
                        elif len(ss) == 2:
                            asignaturas = asignaturas.filter(Q(asignatura__nombre__unaccent__icontains=ss[0])|Q(asignatura__nombre__unaccent__icontains=ss[1])).distinct().order_by('asignatura__nombre')
                        url_vars += "&s={}".format(search)
                    data['niveles'] = niveles
                    data['coordinaciones'] = coordinaciones
                    data['carreras'] = carreras
                    data['modalidadcarrera'] = modalidadcarrera
                    data['coordinacionselect'] = coordinacionselect
                    data['nivelselect'] = nivelselect
                    data['modalidadcarreraselect'] = modalidadcarreraselect
                    data['carreras'] = carreras
                    data['carreraselect'] = carreraselect
                    data['url_vars'] = url_vars
                    data['anios'] = anios
                    data['anioselect'] = anioselect
                    paging = MiPaginador(asignaturas, 20)
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
                    data['asignaturas'] = page.object_list
                    return render(request, 'mallas/listaplanes.html', data)
                except Exception as e:
                    print(e)

            elif action == 'procedimientoeva':
                try:
                    data['title'] = u'Procedimiento de evaluación'
                    data['procedimientos'] = CabProcedimientoEvaluacionPa.objects.filter(status=True)
                    return render(request, "mallas/procedimientoeva.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalleproce':
                try:
                    data['cabprocedimiento'] = cabecera =int(request.GET['id'])
                    data['title'] = u'Detalle de procedimiento de evaluación'
                    data['detprocedimientos'] = ProcedimientoEvaluacionProgramaAnalitico.objects.filter(status=True, cabprocedimiento_id=cabecera)
                    return render(request, "mallas/detalleproce.html", data)
                except Exception as ex:
                    pass

            elif action == 'adddetprocedimento':
                try:
                    data['title'] = u'Adicionar detalle de procedimiento'
                    data['form'] = DetProcedimietoEvaForm()
                    data['cabprocedimiento'] = int(request.GET['id'])
                    return render(request, "mallas/adddetprocedimento.html", data)
                except Exception as ex:
                    pass

            elif action == 'programanaliticopdf':
                try:
                    data['proanalitico'] = pro = ProgramaAnaliticoAsignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    return conviert_html_to_pdf(
                        'mallas/programanalitico_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': pro.plananalitico_pdf(periodo),
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'addprocedimentoeva':
                try:
                    data['title'] = u'Adicionar procedimiento de evaluación'
                    form = CabProcedimietoEvaForm()
                    data['form'] = form
                    return render(request, "mallas/addprocedimentoeva.html", data)
                except Exception as ex:
                    pass

            elif action == 'editprocedimientoeva':
                try:
                    data['title'] = u'Editar procedimiento de evaluación'
                    data['procedimiento'] = proce =CabProcedimientoEvaluacionPa.objects.get(pk=int(request.GET['id']))
                    form = CabProcedimietoEvaForm(initial={'descripcion':proce.descripcion})
                    data['form'] = form
                    return render(request, "mallas/editprocedimientoeva.html", data)
                except Exception as ex:
                    pass

            elif action == 'editdetalleproce':
                try:
                    data['title'] = u'Editar detalle de procedimiento de evaluación'
                    data['detalle'] = detalle =ProcedimientoEvaluacionProgramaAnalitico.objects.get(pk=int(request.GET['id']))
                    form = DetProcedimietoEvaForm(initial=model_to_dict(detalle))
                    data['form'] = form
                    return render(request, "mallas/editdetalleproce.html", data)
                except Exception as ex:
                    pass

            elif action == 'veractasresponsabilidad':
                try:
                    data['title'] = u'Listado de actas'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    search, filtro, url_vars = request.GET.get('s', ''), (
                        Q(malla_id=id, status=True)), f'&action={action}&id={request.GET["id"]}'
                    if search:
                        data['search'] = search
                        url_vars += "&s={}".format(search)
                        filtro = filtro & (Q(persona__nombres__icontains=search) |
                                           Q(persona__apellido1__icontains=search) |
                                           Q(persona__apellido2__icontains=search) |
                                           Q(persona__cedula__icontains=search))
                    actas = ActaResponsabilidad.objects.filter(filtro).order_by('-id')
                    data['carr'] = malla = Malla.objects.get(id=id)
                    if malla.carrera.get_director(periodo).persona == persona:
                        data['es_director'] = True
                    else:
                        data['es_director'] = False
                    paging = MiPaginador(actas, 20)
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
                    data['listado'] = page.object_list
                    data["url_vars"] = url_vars
                    return render(request, "mallas/veractas.html", data)
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'addactaresponsabilidad':
                try:
                    data['title'] = u'Adicionar Acta de Responsabilidad'
                    data['id'] = request.GET['id']
                    data['action'] = request.GET['action']
                    data['form'] = ActaResponsabilidadForm()
                    template = get_template("mallas/modal/formActaResponsabilidad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'editactaresponsabilidad':
                try:
                    data['title'] = u'Modificar acta'
                    data['action'] = request.GET['action']
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['acta'] = acta = ActaResponsabilidad.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = ActaResponsabilidadForm(initial={'actaresponsabilidad': acta.archivoresponsabilidad,
                                                            'observacion': acta.observacion})
                    data['form'] = form
                    template = get_template("mallas/modal/formActaResponsabilidad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'LoadTableAsignaturaMallaOrden':
                try:
                    data['title'] = u'Editar detalle de procedimiento de evaluación'
                    data['malla'] = malla = Malla.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['asignaturasmallas'] = malla.asignaturamalla_set.filter(status=True)
                    template = get_template('mallas/modal/modalTablaAsignaturaMallaOrden.html')
                    return JsonResponse({"result": 'ok', 'html': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": 'bad', 'mensaje': ex.__str__()})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Mallas curriculares'
                data['ver_plan_estudio'] = VER_PLAN_ESTUDIO
                coordinaciones = Coordinacion.objects.filter(carrera__in=miscarreras).distinct()
                codigoscarrera = coordinaciones.values_list('carrera__id', flat=True).filter(status=True)
                nivelestitulacion = NivelTitulacion.objects.filter(pk__in=[3,4])
                modalidadcarrera = Modalidad.objects.filter(status=True)
                carreras = Carrera.objects.filter(id__in=codigoscarrera)

                search = None
                coordinacionselect = nivelselect = modalidadcarreraselect = anioselect = carreraselect = 0
                if 'c' in request.GET:
                    coordinacionselect = int(request.GET['c'])
                if 'n' in request.GET:
                    nivelselect = int(request.GET['n'])
                if 'mc' in request.GET:
                    modalidadcarreraselect = int(request.GET['mc'])
                if 'a' in request.GET:
                    anioselect = int(request.GET['a'])
                if 'carr' in request.GET:
                    carreraselect = int(request.GET['carr'])

                malla = Malla.objects.filter(status=True, carrera__in=miscarreras).distinct().order_by('carrera__coordinacion__nombre', 'modalidad', '-inicio')
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        malla = malla.filter((Q(modalidad__nombre__icontains=search) | Q(carrera__nombre__icontains=search)| Q(codigo__icontains=search))& Q(status=True)).distinct().order_by('carrera__coordinacion__nombre','modalidad', '-inicio')
                    elif len(ss) == 2:
                        malla = malla.filter((Q(carrera__nombre__icontains=ss[0]) & Q(carrera__nombre__icontains=ss[1]))| (Q(carrera__alias__icontains=ss[0])& Q(carrera__alias__icontains=ss[1]))& Q(status=True)).distinct().order_by('carrera__coordinacion__nombre','modalidad', '-inicio')
                    else:
                        malla = malla.filter((Q(carrera__nombre__icontains=ss[0]) & Q(carrera__nombre__icontains=ss[1]) & Q(carrera__nombre__icontains=ss[1])) | (Q(carrera__alias__icontains=ss[0]) & Q(carrera__alias__icontains=ss[1]) & Q(carrera__alias__icontains=ss[0])) & Q(status=True)).distinct().order_by('carrera__coordinacion__nombre', 'modalidad', '-inicio')

                aniosmalla = malla.values_list('inicio').distinct().order_by('-inicio')
                anios = []
                for anio in aniosmalla:
                    if anio[0].year not in anios:
                        anios.append(anio[0].year)

                if modalidadcarreraselect > 0:
                    malla = malla.filter(modalidad_id=modalidadcarreraselect)
                    codigoscarrera = malla.values_list('carrera__id', flat=True).filter(status=True)
                    carreras = carreras.filter(id__in=codigoscarrera)
                if anioselect > 0:
                    malla = malla.filter(inicio__year=anioselect)
                    codigoscarrera = malla.values_list('carrera__id', flat=True).filter(status=True)
                    carreras = carreras.filter(id__in=codigoscarrera)
                if coordinacionselect > 0:
                    malla = malla.filter(carrera__coordinacion__id=coordinacionselect)
                    codigoscarrera = malla.values_list('carrera__id', flat=True).filter(status=True)
                    carreras = carreras.filter(id__in=codigoscarrera)
                if nivelselect > 0:
                    malla = malla.filter(carrera__niveltitulacion__id=nivelselect)
                    codigoscarrera = malla.values_list('carrera__id', flat=True).filter(status=True)
                    carreras = carreras.filter(id__in=codigoscarrera)

                if carreraselect not in codigoscarrera:
                    carreraselect = 0

                if carreraselect > 0:
                    malla = malla.filter(carrera_id=carreraselect)
                    # codigoscarrera = malla.values_list('carrera__id', flat=True).filter(status=True)
                    # carreras = carreras.filter(id__in=codigoscarrera)

                paging = MiPaginador(malla, 20)
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
                ids_malla_pagina = [malla.id for malla in page.object_list]
                listadomallas = Malla.objects.filter(id__in=ids_malla_pagina).\
                    annotate(enusoperiodo=Exists(Materia.objects.filter(status=True, nivel__periodo=periodo, asignaturamalla__malla_id=OuterRef('id'))))
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['mallas'] = listadomallas
                data['coordinacionselect'] = coordinacionselect
                data['nivelselect'] = nivelselect
                data['coordinaciones'] = coordinaciones
                data['nivelestitulacion'] = nivelestitulacion
                data['modalidadcarrera'] = modalidadcarrera
                data['modalidadcarreraselect'] = modalidadcarreraselect
                data['anios'] = anios
                data['anioselect'] = anioselect
                data['carreras'] = carreras
                data['carreraselect'] = carreraselect
                return render(request, "mallas/view.html", data)
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return HttpResponseRedirect(f"/?info={ex.__str__()}")


def elimina_tildes(cadena):
    s = ''.join((c for c in unicodedata.normalize('NFD',cadena) if unicodedata.category(c) != 'Mn'))
    return s
