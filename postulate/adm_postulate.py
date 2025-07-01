import json
import os
import random
import sys

# decoradores
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from django.forms import model_to_dict, TimeInput
from decorators import last_access, secure_module

from django.template import Context
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime,date

from poli.forms import TurnoPolideportivoForm
from postulate.commonviews import actualizar_nota_postulante
from postulate.models import PeriodoPlanificacion, Convocatoria, Partida, ConvocatoriaTerminosCondiciones, \
    PartidaAsignaturas, ConvocatoriaCalificacion, PartidaTribunal, PersonaAplicarPartida, ConvocatoriaPostulante, \
    PersonaIdiomaPartida, PersonaFormacionAcademicoPartida, PersonaExperienciaPartida, PersonaCapacitacionesPartida, \
    PersonaPublicacionesPartida, CARGOS_TRIBUNAL, RequisitoDocumentoContrato, PersonaAplicarPartida, \
    PeriodoAcademicoConvocatoria, RequisitoCompetenciaPeriodo, PreguntaPeriodoPlanificacion, TurnoConvocatoria, \
    HorarioConvocatoria, TipoTurnoConvocatoria, ModeloEvaluativoConvocatoria, DetalleModeloEvaluativoConvocatoria, \
    PartidaArmonizacionNomenclaturaTitulo, EvaluacionPostulante, HorarioPersonaPartida, TIPO_TRIBUNAL, ActaPartida, \
    HistorialActaFirma, ConfiguraRenuncia
from postulate.postular import validar_campos
from sagest.funciones import encrypt_id
from settings import EMAIL_INSTITUCIONAL_AUTOMATICO, ACTUALIZAR_FOTO_ALUMNOS, MEDIA_ROOT
from sga.commonviews import adduserdata
from postulate.forms import PartidaPlanificacionForm, PeriodoPlanificacionForm, \
    ConvocatoriaForm, PartidaForm, ConvocatoriaTerminosForm, CustomDateInput, TribunalForm, AgendaDisertacionForm, \
    RequisitoDocumentoContratoForm, ImportPartidaForm, EnvioCorreoForm, ImportarPostulantesForm, \
    PeriodoAcademicoConvocatoriaForm, MoverPeriodoPlanificacionForm, RequisitoCompetenciaPeriodoForm, \
    PreguntaPeriodoPlanificacionForm, HorarioConvocatoriaForm, NumMejoresPuntuados, TurnoConvocatoriaForm, \
    TipoTurnoConvocatoriaForm, ModeloEvaluativoConvocatoriaForm, DetalleModeloEvaluativoConvocatoriaForm, \
    LogicaModeloEvaluativoConvocatoriaForm, ConfiguraRenunciaForm
from sga.funciones import log, MiPaginador, numero_a_letras,remover_caracteres_especiales_unicode, logobjeto,generar_nombre
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdfsave_generic_lotes, conviert_html_to_pdf_save_file_model

from sga.models import AreaConocimientoTitulacion, SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion, Carrera, Asignatura, Titulo, Persona, CUENTAS_CORREOS
from sga.templatetags.sga_extras import encrypt
from xlwt import *
from sga.tasks import send_html_mail
import xlwt
import xlsxwriter
import io

@login_required(redirect_field_name='ret', login_url='/loginpostulate')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    perfilprincipal = request.session['perfilprincipal']
    persona = request.session['persona']
    periodo = request.session['periodo']
    data['hoy'] = hoy = datetime.now().date()
    data['currenttime'] = datetime.now()
    data['perfil'] = persona.mi_perfil()
    data['periodo'] = periodo

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addconvocatoria':
            try:
                form = ConvocatoriaForm(request.POST)
                if form.is_valid():
                    convocatoria = Convocatoria(descripcion=form.cleaned_data['descripcion'],
                                                finicio=form.cleaned_data['fechainicio'],
                                                ffin=form.cleaned_data['fechafin'],
                                                tipocontrato=form.cleaned_data['tipocontrato'],
                                                denominacionpuesto=form.cleaned_data['denominacionpuesto'],
                                                modeloevaluativo = form.cleaned_data['modeloevaluativo'],
                                                modeloevaluativoconvocatoria = form.cleaned_data['modeloevaluativoconvocatoria'],
                                                vigente=form.cleaned_data['vigente'],
                                                nummejorespuntuados=form.cleaned_data['nummejorespuntuados'])
                    convocatoria.valtercernivel = form.cleaned_data['valtercernivel']
                    convocatoria.departamento = form.cleaned_data['departamento']
                    convocatoria.valposgrado = form.cleaned_data['valposgrado']
                    convocatoria.valdoctorado = form.cleaned_data['valdoctorado']
                    convocatoria.valcapacitacionmin = form.cleaned_data['valcapacitacionmin']
                    convocatoria.valcapacitacionmax = form.cleaned_data['valcapacitacionmax']
                    convocatoria.valexpdocentemin = form.cleaned_data['valexpdocentemin']
                    convocatoria.valexpdocentemax = form.cleaned_data['valexpdocentemax']
                    convocatoria.valexpadminmin = form.cleaned_data['valexpadminmin']
                    convocatoria.valexpadminmax = form.cleaned_data['valexpadminmax']
                    archivo = None
                    if 'archivo' in request.FILES:
                        archivo = request.FILES['archivo']
                        archivo._name = remover_caracteres_especiales_unicode(archivo._name)
                        ext = archivo._name.split('.')[-1]
                        if not ext in ['pdf']:
                            raise NameError(u'Formato de archivo incorrecto, subir en formato .pdf')
                        if archivo.size > 10194304:
                            raise NameError(u'Tamaño maximo permitod es 10Mb')
                    convocatoria.archivo=archivo
                    convocatoria.save(request)
                    log(u'Adicion de convocatoria: %s' % convocatoria, request, "addconvocatoria")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        if action == 'editconvocatoria':
            try:
                form = ConvocatoriaForm(request.POST)
                convocatoria = Convocatoria.objects.get(id=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    convocatoria.descripcion = form.cleaned_data['descripcion']
                    convocatoria.finicio = form.cleaned_data['fechainicio']
                    convocatoria.ffin = form.cleaned_data['fechafin']
                    convocatoria.tipocontrato = form.cleaned_data['tipocontrato']
                    convocatoria.denominacionpuesto = form.cleaned_data['denominacionpuesto']
                    convocatoria.modeloevaluativo = form.cleaned_data['modeloevaluativo']
                    convocatoria.vigente = form.cleaned_data['vigente']
                    convocatoria.nummejorespuntuados = form.cleaned_data['nummejorespuntuados']
                    convocatoria.valtercernivel = form.cleaned_data['valtercernivel']
                    convocatoria.valposgrado = form.cleaned_data['valposgrado']
                    convocatoria.valdoctorado = form.cleaned_data['valdoctorado']
                    convocatoria.valcapacitacionmin = form.cleaned_data['valcapacitacionmin']
                    convocatoria.valcapacitacionmax = form.cleaned_data['valcapacitacionmax']
                    convocatoria.valexpdocentemin = form.cleaned_data['valexpdocentemin']
                    convocatoria.valexpdocentemax = form.cleaned_data['valexpdocentemax']
                    convocatoria.valexpadminmin = form.cleaned_data['valexpadminmin']
                    convocatoria.valexpadminmax = form.cleaned_data['valexpadminmax']
                    convocatoria.departamento = form.cleaned_data['departamento']
                    if 'archivo' in request.FILES:
                        archivo = request.FILES['archivo']
                        archivo._name = remover_caracteres_especiales_unicode(archivo._name)
                        ext = archivo._name.split('.')[-1]
                        if not ext in ['pdf']:
                            raise NameError(u'Formato de archivo incorrecto, subir en formato .pdf')
                        if archivo.size > 10194304:
                            raise NameError(u'Tamaño maximo permitod es 10Mb')
                        convocatoria.archivo=archivo
                    convocatoria.save(request)

                    if not convocatoria.modeloevaluativoconvocatoria == form.cleaned_data['modeloevaluativoconvocatoria']:
                        convocatoria.modeloevaluativoconvocatoria = form.cleaned_data['modeloevaluativoconvocatoria']
                        convocatoria.save(request)
                        actualizar_modelo_evaluativo(request,convocatoria)
                        log(u"Actualizo el modelo evaluativo de la convocatoria: %s" % (convocatoria.__str__()), request, 'change')
                    log(u'Edicion de convocatoria: %s' % convocatoria, request, "editconvocatoria")
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        if action == 'delconvocatoria':
            try:
                with transaction.atomic():
                    convocatoria = Convocatoria.objects.get(id=int(encrypt(request.POST['id'])))
                    convocatoria.status = False
                    convocatoria.save(request)
                    log(u'Elimincion de convocatoria: %s' % convocatoria, request, "delconvocatoria")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'deltribunalsegundaetapa':
            try:
                with transaction.atomic():
                    convocatoria = Convocatoria.objects.get(id=int(request.POST['id']))
                    for trib in PartidaTribunal.objects.filter(status=True, partida__convocatoria=convocatoria, tipo=2):
                        trib.status = False
                        trib.save(request)
                    convocatoria.save(request)
                    log(u'Elimincion de tribunal segunda etapa: %s' % convocatoria, request, "deltribunalsegundaetapa")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'deltribunalprimeraetapa':
            try:
                with transaction.atomic():
                    convocatoria = Convocatoria.objects.get(id=int(request.POST['id']))
                    for trib in PartidaTribunal.objects.filter(status=True, partida__convocatoria=convocatoria, tipo=1):
                        trib.status = False
                        trib.save(request)
                    convocatoria.save(request)
                    log(u'Elimincion de tribunal segunda etapa: %s' % convocatoria, request, "deltribunalsegundaetapa")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'editvigente':
            try:
                convocatoria = Convocatoria.objects.get(id=int(encrypt(request.POST['id'])))
                convocatoria.vigente = request.POST['vigente']
                convocatoria.save(request)
                log(u'Edicion de estado Vigencia de convocatoria: %s' % convocatoria, request, "edit")
                return JsonResponse({'result': 'ok', 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'activamodelo':
            try:
                modelo = ModeloEvaluativoConvocatoria.objects.get(id=int(encrypt(request.POST['id'])))
                modelo.activo = request.POST['activo']
                modelo.save(request)
                log(u'Edicion de estado activo de modelo evaluativo: %s' % modelo, request, "edit")
                return JsonResponse({'result': 'ok', 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'activamodelodetalle':
            try:
                detalle = DetalleModeloEvaluativoConvocatoria.objects.get(id=int(encrypt(request.POST['id'])))
                estado=request.POST['activo']
                tipo = int(encrypt(request.POST['tipo']))
                if tipo==1:
                    detalle.actualizaestado = estado
                elif tipo==2:
                    detalle.determinaestadofinal = estado
                elif tipo==3:
                    detalle.dependiente = estado
                elif tipo==4:
                    detalle.subearchivo = estado
                detalle.save(request)
                log(u'Edicion de detalle modelo evaluativo: %s' % detalle, request, "edit")
                return JsonResponse({'result': 'ok', 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'editapelacion':
            try:
                convocatoria = Convocatoria.objects.get(id=int(encrypt(request.POST['id'])))
                convocatoria.apelacion = request.POST['apelacion']
                convocatoria.save(request)
                log(u'Edicion de estado Apelación de convocatoria: %s' % convocatoria, request, "edit")
                return JsonResponse({'result': 'ok', 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'editsegundaetapa':
            try:
                convocatoria = Convocatoria.objects.get(id=int(encrypt(request.POST['id'])))
                convocatoria.segundaetapa = request.POST['segundaetapa']
                convocatoria.save(request)
                log(u'Edicion de estado Disertación/Apelación de convocatoria: %s' % convocatoria, request, "edit")
                return JsonResponse({'result': 'ok', 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)

        if action == 'editcalificacion':
            try:
                convocatoria = Convocatoria.objects.get(id=int(encrypt(request.POST['id'])))
                convocatoria.muestracalificacion = request.POST['calificacion']
                convocatoria.save(request)
                log(u'Edicion de estado mostrar calificacion de convocatoria: %s' % convocatoria, request, "edit")
                return JsonResponse({'result': 'ok', 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'addperiodoplanificacion':
            try:
                data['title'] = u'Adicionar Periodo de planificación'
                form = PeriodoPlanificacionForm(request.POST)
                periodo = PeriodoAcademicoConvocatoria.objects.get(id=int(encrypt(request.POST['idp'])))
                if form.is_valid():
                    periodoplanificacion = PeriodoPlanificacion(nombre=form.cleaned_data['nombre'],
                                                                finicio=form.cleaned_data['fechainicio'],
                                                                periodo=periodo,
                                                                ffin=form.cleaned_data['fechafin'],
                                                                vigente=form.cleaned_data['vigente'])
                    periodoplanificacion.save(request)
                    log(u'Adicion de periodo de planificacion: %s' % periodoplanificacion, request, "addperiodoplanificacion")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        if action == 'editperiodoplanificacion':
            try:
                form = PeriodoPlanificacionForm(request.POST)
                pplanificacion = PeriodoPlanificacion.objects.get(id=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    pplanificacion.nombre = form.cleaned_data['nombre']
                    pplanificacion.finicio = form.cleaned_data['fechainicio']
                    pplanificacion.ffin = form.cleaned_data['fechafin']
                    pplanificacion.vigente = form.cleaned_data['vigente']
                    pplanificacion.save(request)
                    log(u'Edicion de periodo de planificacion: %s' % pplanificacion, request, "editperiodoplanificacion")
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        if action == 'logica':
            try:
                form = LogicaModeloEvaluativoConvocatoriaForm(request.POST)
                modelo = ModeloEvaluativoConvocatoria.objects.get(id=int(request.POST['id']))
                if form.is_valid():
                    modelo.logicamodelo = form.cleaned_data['logica']
                    modelo.save(request)
                    log(u'Edicion de logica en modelo: %s' % modelo, request, "edit")
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        if action == 'editperiodo':
            try:
                form = PeriodoAcademicoConvocatoriaForm(request.POST)
                periodo = PeriodoAcademicoConvocatoria.objects.get(id=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    periodo.nombre = form.cleaned_data['nombre']
                    periodo.vigente = form.cleaned_data['vigente']
                    periodo.save(request)
                    log(u'Editó periodo en planificación: %s' % periodo, request, "edit")
                    return JsonResponse({'result': False, 'mensaje': 'Edición Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        if action == 'delperiodoplanificacion':
            try:
                with transaction.atomic():
                    pplanificacion = PeriodoPlanificacion.objects.get(id=int(encrypt(request.POST['id'])))
                    pplanificacion.status = False
                    pplanificacion.save(request)
                    log(u'Elimincion de periodo de planificacion: %s' % pplanificacion, request, "delperiodoplanificacion")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'editvigentepplanificacion':
            try:
                pplanificacion = PeriodoPlanificacion.objects.get(id=int(encrypt(request.POST['id'])))
                pplanificacion.vigente = request.POST['vigente']
                pplanificacion.save(request)
                log(u'Edicion de vigencia de periodo de planificacion: %s' % pplanificacion, request, "editvigentepplanificacion")
                return JsonResponse({'result': 'ok', 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'addpartida':
            try:
                form = PartidaForm(request.POST)
                idc = int(encrypt(request.POST['idc']))
                convocatoria = Convocatoria.objects.get(id=idc)
                if form.is_valid():
                    partida = Partida(
                        convocatoria_id=idc,
                        codpartida=form.cleaned_data['codpartida'],
                        # titulo=form.cleaned_data['titulo'],
                        observacion=form.cleaned_data['observacion'],
                        # descripcion=form.cleaned_data['descripcion'],
                        carrera=form.cleaned_data['carrera'],
                        denominacionpuesto=form.cleaned_data['denominacionpuesto'],
                        nivel=form.cleaned_data['nivel'],
                        modalidad=form.cleaned_data['modalidad'],
                        dedicacion=form.cleaned_data['dedicacion'],
                        jornada=form.cleaned_data['jornada'],
                        rmu=form.cleaned_data['rmu'],
                        vigente=form.cleaned_data['vigente'],
                        minhourcapa = form.cleaned_data['minhourcapa'],
                        minmesexp = form.cleaned_data['minmesexp']
                    )
                    partida.save(request)
                    for ca in form.cleaned_data['campoamplio']:
                        partida.campoamplio.add(ca)
                    for caesp in form.cleaned_data['campoespecifico']:
                        partida.campoespecifico.add(caesp)
                    for campdet in form.cleaned_data['campodetallado']:
                        partida.campodetallado.add(campdet)
                    for tit in form.cleaned_data['titulos']:
                        partida.titulos.add(tit)
                    partida.save(request)

                    for arm in form.cleaned_data['armonizacion']:
                        partarmonizacion = PartidaArmonizacionNomenclaturaTitulo(
                                combinacion=arm,
                                partida=partida
                            )
                        partarmonizacion.save(request)

                    for asignatura in form.cleaned_data['asignatura']:
                        partidaasignatura = PartidaAsignaturas(partida=partida,
                                                               asignatura=asignatura)
                        partidaasignatura.save(request)
                    if not partida.partidaarmonizacionnomenclaturatitulo_set.filter(status=True):
                        partida.vigente = False
                        partida.save(request)
                        messages.warning(request,'La partida no se le ha configurado la armonización')
                    log(u'Adicion de partida y partida asignatura: %s' % partida, request, "addpartida")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'editpartida':
            try:
                form = PartidaForm(request.POST)
                partida = Partida.objects.get(id=request.POST['id'])
                partidaasignaturas = PartidaAsignaturas.objects.filter(partida=partida, status=True)
                exclude_borrar_armonizacion = []
                if form.is_valid():
                    partida.codpartida = form.cleaned_data['codpartida']
                    # partida.titulo = form.cleaned_data['titulo']
                    # partida.descripcion = form.cleaned_data['descripcion']
                    partida.observacion = form.cleaned_data['observacion']
                    partida.denominacionpuesto = form.cleaned_data['denominacionpuesto']
                    partida.carrera = form.cleaned_data['carrera']
                    partida.nivel = form.cleaned_data['nivel']
                    partida.modalidad = form.cleaned_data['modalidad']
                    partida.dedicacion = form.cleaned_data['dedicacion']
                    partida.jornada = form.cleaned_data['jornada']
                    partida.rmu = form.cleaned_data['rmu']
                    partida.vigente = form.cleaned_data['vigente']
                    partida.minhourcapa = form.cleaned_data['minhourcapa']
                    partida.minmesexp = form.cleaned_data['minmesexp']
                    partida.save(request)

                    partida.campoamplio.clear()
                    partida.campoespecifico.clear()
                    partida.campodetallado.clear()
                    partida.titulos.clear()
                    for ca in form.cleaned_data['campoamplio']:
                        partida.campoamplio.add(ca)
                    for caesp in form.cleaned_data['campoespecifico']:
                        partida.campoespecifico.add(caesp)
                    for campdet in form.cleaned_data['campodetallado']:
                        partida.campodetallado.add(campdet)
                    for tit in form.cleaned_data['titulos']:
                        partida.titulos.add(tit)
                    partida.save(request)

                    for arm in form.cleaned_data['armonizacion']:
                        if not PartidaArmonizacionNomenclaturaTitulo.objects.filter(status=True, combinacion=arm,partida=partida).exists():
                            partarmonizacion = PartidaArmonizacionNomenclaturaTitulo(
                                combinacion=arm,
                                partida=partida
                            )
                            partarmonizacion.save(request)
                            exclude_borrar_armonizacion.append(partarmonizacion.id)
                        else:
                            partarmonizacion = PartidaArmonizacionNomenclaturaTitulo.objects.get(status=True, combinacion=arm,partida=partida)
                            exclude_borrar_armonizacion.append(partarmonizacion.id)
                    armo_delete = PartidaArmonizacionNomenclaturaTitulo.objects.filter(status=True,partida=partida).exclude(id__in=exclude_borrar_armonizacion)
                    for dele in armo_delete:
                        dele.status = False
                        dele.save(request)
                    for partidaasignatura in partidaasignaturas:
                        partidaasignatura.status = False
                        partidaasignatura.save(request)

                    if not partida.partidaarmonizacionnomenclaturatitulo_set.filter(status=True):
                        partida.vigente = False
                        partida.save(request)
                        messages.warning(request,'La partida no se le ha configurado la armonización')

                    for asignatura in form.cleaned_data['asignatura']:
                        if not PartidaAsignaturas.objects.filter(partida=partida, asignatura=asignatura, status=True).exists():
                            partidasave = PartidaAsignaturas(partida=partida,
                                                             asignatura=asignatura, )
                            partidasave.save(request)
                    log(u'Edicion de partida y partidaasignatura: %s' % partida, request, "editpartida")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'delpartida':
            try:
                with transaction.atomic():
                    partida = Partida.objects.get(id=int(encrypt(request.POST['id'])))
                    if partida.periodoplanificacion:
                        partida.convocatoria=None
                    else:
                        partida.status = False
                        for partidaasignatura in PartidaAsignaturas.objects.filter(partida=partida, status=True):
                            partidaasignatura.status = False
                            partidaasignatura.save(request)
                    partida.save(request)

                    log(u'Elimincion de partida: %s' % partida, request, "delpartida")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'editvigentepartida':
            try:
                partida = Partida.objects.get(id=int(encrypt(request.POST['id'])))
                if not partida.partidaarmonizacionnomenclaturatitulo_set.filter(status=True):
                    messages.warning(request,'No se ha configurado los titulos Armonizacion')
                else:
                    partida.vigente = request.POST['vigente']
                    partida.save(request)
                log(u'Edicion de vigencia de partida: %s' % partida, request, "editvigentepartida")
                return JsonResponse({'result': 'ok', 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'editvigentefirma':
            try:
                partida = PartidaTribunal.objects.get(id=int(encrypt(request.POST['id'])))
                partida.firma = request.POST['firma']
                partida.save(request)
                log(u'Edicion de firma de tritunal: %s' % partida, request, "editvigentefirma")
                return JsonResponse({'result': 'ok', 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'addpartidaplanificacion':
            try:
                form = PartidaForm(request.POST)
                idc = int(encrypt(request.POST['idc']))
                periodoplanificacion = PeriodoPlanificacion.objects.get(id=idc)
                if form.is_valid():
                    partida = Partida(
                        periodoplanificacion_id=idc,
                        codpartida=form.cleaned_data['codpartida'],
                        observacion=form.cleaned_data['observacion'],
                        carrera=form.cleaned_data['carrera'],
                        nivel=form.cleaned_data['nivel'],
                        modalidad=form.cleaned_data['modalidad'],
                        dedicacion=form.cleaned_data['dedicacion'],
                        jornada=form.cleaned_data['jornada'],
                        rmu=form.cleaned_data['rmu'],
                        vigente=form.cleaned_data['vigente'],
                        estado=1)
                    partida.save()
                    for ca in form.cleaned_data['campoamplio']:
                        partida.campoamplio.add(ca)
                    for caesp in form.cleaned_data['campoespecifico']:
                        partida.campoespecifico.add(caesp)
                    for campdet in form.cleaned_data['campodetallado']:
                        partida.campodetallado.add(campdet)
                    for tit in form.cleaned_data['titulos']:
                        partida.titulos.add(tit)
                    partida.save(request)

                    for asignatura in form.cleaned_data['asignatura']:
                        partidaasignatura = PartidaAsignaturas(partida=partida,
                                                               asignatura=asignatura)
                        partidaasignatura.save(request)
                    log(u'Adicion de partida de planificacion y partida asignatura: %s' % partida, request, "addpartidaplanificacion")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'editpartidaplanificacion':
            try:
                form = PartidaPlanificacionForm(request.POST)
                partida = Partida.objects.get(id=request.POST['id'])
                partidaasignaturas = PartidaAsignaturas.objects.filter(partida=partida, status=True)
                if form.is_valid():
                    partida.codpartida = form.cleaned_data['codpartida']
                    partida.denominacionpuesto = form.cleaned_data['denominacionpuesto']
                    # partida.titulo = form.cleaned_data['titulo']
                    # partida.descripcion = form.cleaned_data['descripcion']
                    partida.observacion = form.cleaned_data['observacion']
                    partida.carrera = form.cleaned_data['carrera']
                    partida.nivel = form.cleaned_data['nivel']
                    partida.modalidad = form.cleaned_data['modalidad']
                    partida.dedicacion = form.cleaned_data['dedicacion']
                    partida.jornada = form.cleaned_data['jornada']
                    partida.rmu = form.cleaned_data['rmu']
                    partida.save(request)

                    partida.campoamplio.clear()
                    partida.campoespecifico.clear()
                    partida.campodetallado.clear()
                    partida.titulos.clear()
                    for ca in form.cleaned_data['campoamplio']:
                        partida.campoamplio.add(ca)
                    for caesp in form.cleaned_data['campoespecifico']:
                        partida.campoespecifico.add(caesp)
                    for campdet in form.cleaned_data['campodetallado']:
                        partida.campodetallado.add(campdet)
                    for tit in form.cleaned_data['titulos']:
                        partida.titulos.add(tit)
                    partida.save(request)

                    for partidaasignatura in partidaasignaturas:
                        partidaasignatura.status = False
                        partidaasignatura.save(request)

                    for asignatura in form.cleaned_data['asignatura']:
                        if not PartidaAsignaturas.objects.filter(partida=partida, asignatura=asignatura, status=True).exists():
                            partidasave = PartidaAsignaturas(partida=partida,
                                                             asignatura=asignatura, )
                            partidasave.save(request)
                    log(u'Edicion de partida y partidaasignatura: %s' % partida, request, "editpartidaplanificacion")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'delpartidaplanificacion':
            try:
                with transaction.atomic():
                    partida = Partida.objects.get(id=int(encrypt(request.POST['id'])))
                    partida.status = False
                    partida.save(request)

                    for partidaasignatura in PartidaAsignaturas.objects.filter(partida=partida, status=True):
                        partidaasignatura.status = False
                        partidaasignatura.save(request)

                    log(u'Eliminacion de partida de planificacion: %s' % partida, request, "delpartidaplanificacion")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        # if action == 'revisarpartidaplanificacion':
        #     with transaction.atomic():
        #         try:
        #             partida = Partida.objects.get(pk=int(request.POST['id']))
        #             historialbase = HistorialAprobacionPartida.objects.filter(partida=partida).last()
        #             f = HistorialAprobacionPartidaForm(request.POST)
        #             if f.is_valid():
        #                 partida.estado = int(f.cleaned_data['estado'])
        #                 partida.save(request)
        #                 log(u'Se revisó la partida de planificacion: %s' % partida, request, "edit")
        #                 nota = HistorialAprobacionPartida(partida=partida,
        #                                           observacion=f.cleaned_data['observacion'],
        #                                           estado=int(f.cleaned_data['estado']))
        #                 nota.save(request)
        #                 log(u'Se guard{o historial de aprobación la partida de planificacion: %s' % nota, request, "add")
        #                 return JsonResponse({"result": False}, safe=False)
        #             else:
        #                 transaction.set_rollback(True)
        #                 return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)
        #         except Exception as ex:
        #             transaction.set_rollback(True)
        #             return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editestadopartida':
            try:
                partida = Partida.objects.get(id=int(encrypt(request.POST['id'])))
                partida.estado = request.POST['estado']
                partida.save(request)
                log(u'Edicion de estado de partida de planificacion: %s' % partida, request, "editestadopartida")
                return JsonResponse({'result': 'ok', 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})


        if action == 'importpartidaplanificacion':
            try:
                form = ImportPartidaForm(request.POST)
                idc = int(encrypt(request.POST['id']))
                if form.is_valid():
                    partidas = form.cleaned_data['partida']
                    for x in partidas:
                        partida = Partida.objects.get(id=x.id)
                        partida.convocatoria_id=idc
                        partida.save()
                    log(u'Importar partida en convocatoria: %s' % partida, request, "importpartidaplanificacion")
                    return JsonResponse({"result": False, 'mensaje': f'Partidas importadas'})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos'})

        if action == 'enviarcorreomasivo':
            try:
                form = EnvioCorreoForm(request.POST)
                destinatarios = request.POST['destinatarios'].split(',')
                emails = []
                if form.is_valid():
                    asunto = form.cleaned_data['asunto']
                    mensaje = form.cleaned_data['mensaje']
                    for idp in destinatarios:
                        if idp:
                            persona = Persona.objects.get(pk=idp)
                            if persona.emails():
                                emails.append(persona.emails())

                    send_html_mail(asunto, "emails/convocatorias_postulate.html",
                                   {'sistema': request.session['nombresistema'],
                                    'fecha': datetime.now().date(),
                                    'hora': datetime.now().time(),
                                    'asunto': asunto,
                                    'mensaje': mensaje},
                                    emails, [],
                                    cuenta=CUENTAS_CORREOS[30][1])

                    log(u'Envio correo masivo Postulate: %s' % asunto, request, "enviarcorreomasivo")
                    messages.success(request, 'Correos enviados con éxito.')
                    return JsonResponse({"result": True, 'msg': f'Correos Enviados'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': False, 'msg': f'Error al enviar los datos'})

        if action == 'addtermino':
            try:
                form = ConvocatoriaTerminosForm(request.POST)
                if form.is_valid():
                    termino = ConvocatoriaTerminosCondiciones(descripcion=form.cleaned_data['descripcion'], convocatoria_id=int(encrypt(request.POST['id'])))
                    termino.save(request)
                    log(u'Adicion Terminos y Condiciones: %s' % termino, request, "addtermino")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        if action == 'edittermino':
            try:
                form = ConvocatoriaTerminosForm(request.POST)
                termino = ConvocatoriaTerminosCondiciones.objects.get(id=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    termino.descripcion = form.cleaned_data['descripcion']
                    termino.save(request)
                    log(u'Edicion de Termino y Condiciones: %s' % termino, request, "edittermino")
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        if action == 'deltermino':
            try:
                with transaction.atomic():
                    termino = ConvocatoriaTerminosCondiciones.objects.get(id=int(encrypt(request.POST['id'])))
                    termino.status = False
                    termino.save(request)
                    log(u'Elimincion de Terminos y Condiciones: %s' % termino, request, "deltermino")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        # ADICIONAR PERSONAS PARA CONFIGURACION DE TRIBUNALES

        if action == 'addtribunal':
            try:
                dat = request.POST
                partidas = request.POST.getlist('partida')
                item_id = None
                if not dat['item'] == '':
                    item_id = int(dat['item'])
                if len(partidas) > 1:
                    for p in partidas:
                        part = Partida.objects.get(id=p)
                        if PartidaTribunal.objects.filter(status=True, partida=part, cargos=int(dat['cargo']), tipo=int(dat['tipo'])).exists():
                            return JsonResponse({'result': True, "mensaje": u"Cargo ya ocupado en la partida " + str(part.__str__())})
                        if PartidaTribunal.objects.filter(status=True, partida=part, persona_id=int(dat['persona']), tipo=int(dat['tipo'])).exists():
                            return JsonResponse({'result': True, "mensaje": u"Esta persona ya existe en la partida " + str(part.__str__())})

                        persona_ = Persona.objects.get(id=dat['persona'])
                        user_ = persona_.usuario
                        if int(dat['tipo']) == 1:
                            if not user_.groups.filter(id=360).exists():
                                user_.groups.add(360)
                        else:
                            if not user_.groups.filter(id=362).exists():
                                user_.groups.add(362)

                        ptribunal = PartidaTribunal(partida_id=int(p), persona_id=int(dat['persona']), cargos=int(dat['cargo']), tipo=int(dat['tipo']),item_id=item_id)
                        if 'firma' in dat:
                            ptribunal.firma = True if dat['firma'] == 'on' else False
                        ptribunal.save(request)
                        log(u'Agrego personas al tribunal: %s' % ptribunal, request, "add")
                else:
                    part = Partida.objects.get(id=partidas[0])
                    if PartidaTribunal.objects.filter(status=True, partida=part, cargos=int(dat['cargo']), tipo=int(dat['tipo'])).exists():
                        return JsonResponse({'result': True, "mensaje": u"Cargo ya ocupado en la partida " + str(part.__str__())})
                    if PartidaTribunal.objects.filter(status=True, partida=part, persona_id=int(dat['persona']), tipo=int(dat['tipo'])).exists():
                        return JsonResponse({'result': True, "mensaje": u"Esta persona ya existe en la partida " + str(part.__str__())})
                    ptribunal = PartidaTribunal(partida_id=int(partidas[0]), persona_id=int(dat['persona']), cargos=int(dat['cargo']), tipo=int(dat['tipo']),item_id=item_id)
                    if 'firma' in dat:
                        ptribunal.firma = True if dat['firma'] == 'on' else False
                    ptribunal.save(request)
                    log(u'Agrego personas al tribunal: %s' % ptribunal, request, "add")
                return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': str(ex)})

        if action == 'delmiembrotribunal':
            try:
                with transaction.atomic():
                    partida = PartidaTribunal.objects.get(id=int(encrypt(request.POST['id'])))
                    partida.status = False
                    partida.save(request)
                    log(u'Eliminacion miembro de tribunal: %s' % partida, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'agendardisertacion':
            try:
                form = AgendaDisertacionForm(request.POST)
                if form.is_valid():
                    postulacion = PersonaAplicarPartida.objects.get(pk=request.POST['idp'])
                    if 'id' in request.POST:
                        convocatoria = ConvocatoriaPostulante.objects.get(id=int(encrypt(request.POST['id'])))
                    else:
                        convocatoria = ConvocatoriaPostulante(persona=postulacion)
                    convocatoria.tema = form.cleaned_data['tema']
                    convocatoria.fechaasistencia = form.cleaned_data['fechaasistencia']
                    convocatoria.horasistencia = form.cleaned_data['horasistencia']
                    convocatoria.lugar = form.cleaned_data['lugar']
                    convocatoria.observacion = form.cleaned_data['observacion']
                    convocatoria.save(request)
                    log(u'Edicion de Agenda Convocatoria Disertación: %s' % convocatoria, request, "add")
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        elif action == 'addrequisito':
            try:
                form = RequisitoDocumentoContratoForm(request.POST,request.FILES)
                if not form.is_valid():
                    raise NameError(str([{k: v[0]} for k, v in form.errors.items()][0]))
                archivo = None
                if 'archivo' in request.FILES:
                    archivo = request.FILES['archivo']
                    archivo._name = remover_caracteres_especiales_unicode(archivo._name)
                    ext = archivo._name.split('.')[-1]
                    if not ext in ['pdf']:
                        raise NameError(u'Formato de archivo incorrecto, subir en formato .pdf')
                    if archivo.size > 10194304:
                        raise NameError(u'Tamaño maximo permitod es 10Mb')
                anio = form.cleaned_data['anio']
                requisito = RequisitoDocumentoContrato(
                    nombre = form.cleaned_data['nombre'],
                    descripcion = form.cleaned_data['descripcion'],
                    anio = anio.date(),
                    obligatorio = form.cleaned_data['obligatorio'],
                    activo=form.cleaned_data['activo'],
                    tipo = form.cleaned_data['tipo'],
                    archivo=archivo
                )
                requisito.save(request)
                log(u'Agregó requisito: %s'%(requisito),request,'add')
                return JsonResponse({'result':False, 'mensaje': 'Registro guardado'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos. Detalle: %s'%(ex.__str__())})

        elif action == 'editobligatorio':
            try:
                if not 'id' in request.POST:
                    raise NameError()
                id = int(encrypt(request.POST['id']))
                requi = RequisitoDocumentoContrato.objects.get(pk=id)
                requi.obligatorio = request.POST['obligatorio']
                requi.save(request)
                log('Edito el esto de obligatoriedad %s'%(requi.__str__()),request,'edit')
                return JsonResponse({'result':False, 'mensaje': 'Registro editado'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos. Detalle: %s'%(ex.__str__())})

        elif action == 'editactivo':
            try:
                if not 'id' in request.POST:
                    raise NameError()
                id = int(encrypt(request.POST['id']))
                requi = RequisitoDocumentoContrato.objects.get(pk=id)
                requi.activo = request.POST['activo']
                requi.save(request)
                log('Edito el esto de obligatoriedad %s'%(requi.__str__()),request,'edit')
                return JsonResponse({'result':False, 'mensaje': 'Registro editado'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos. Detalle: %s'%(ex.__str__())})

        elif action == 'editrequisito':
            try:
                form = RequisitoDocumentoContratoForm(request.POST, request.FILES)
                requisito = RequisitoDocumentoContrato.objects.get(id =int(encrypt(request.POST['id'])))
                if not form.is_valid():
                    raise NameError(str([{k: v[0]} for k, v in form.errors.items()][0]))
                archivo = None
                if 'archivo' in request.FILES:
                    archivo = request.FILES['archivo']
                    archivo._name = remover_caracteres_especiales_unicode(archivo._name)
                    ext = archivo._name.split('.')[-1]
                    if not ext in ['pdf']:
                        raise NameError(u'Formato de archivo incorrecto, subir en formato .pdf')
                    if archivo.size > 10194304:
                        raise NameError(u'Tamaño maximo permitod es 10Mb')

                    requisito.archivo = archivo
                anio = form.cleaned_data['anio']
                requisito.nombre = form.cleaned_data['nombre']
                requisito.descripcion = form.cleaned_data['descripcion']
                requisito.anio = anio.date()
                requisito.obligatorio = form.cleaned_data['obligatorio']
                requisito.activo = form.cleaned_data['activo']
                requisito.tipo = form.cleaned_data['tipo']
                requisito.save(request)
                log(u'Editó requisito: %s' % (requisito), request, 'edit')
                return JsonResponse({'result': False, 'mensaje': 'Registro guardado'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. Detalle: {ex.__str__()}'})

        elif action == 'addperiodo':
            try:
                form = PeriodoAcademicoConvocatoriaForm(request.POST,request.FILES)
                if form.is_valid():
                    periodo = PeriodoAcademicoConvocatoria(
                        nombre = form.cleaned_data['nombre'],
                        vigente = form.cleaned_data['vigente']
                    )
                    periodo.save(request)
                    log(u'Agregó periodo: %s'%(periodo),request,'add')
                    return JsonResponse({'result': False, 'mensaje': 'Registro guardado'})

                return JsonResponse(
                    {'result': True, 'mensaje': u'Error al guardar los datos.'})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos. Detalle: %s'%(ex.__str__())})

        elif action == 'moverperiodoplanificacion':
            try:
                form = MoverPeriodoPlanificacionForm(request.POST)
                planificacion = PeriodoPlanificacion.objects.get(id=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    planificacion.periodo=form.cleaned_data['periodoacademico']
                    planificacion.save(request)
                    log(u'movió periodo: %s'%(planificacion),request,'add')
                    return JsonResponse({'result': False, 'mensaje': 'Registro guardado'})

                return JsonResponse(
                    {'result': True, 'mensaje': u'Error al guardar los datos.'})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos. Detalle: %s'%(ex.__str__())})


        if action == 'importarparticipante':
            try:
                with transaction.atomic():
                    form = ImportarPostulantesForm(request.POST, request.FILES)
                    #idpartida = Partida.objects.get(id=request.POST['id'])
                    if 'archivo' in request.FILES:
                        archivo = request.FILES['archivo']
                        archivo._name = generar_nombre("documento_", archivo._name)
                        ext = archivo._name.split('.')[-1]
                        if not ext in ['pdf']:
                            raise NameError(u'Formato de archivo incorrecto, subir en formato .pdf')
                        if archivo.size > 1055555194304:
                            raise NameError(u'Tamaño máximo permitido es 10Mb')
                        postulante = PersonaAplicarPartida.objects.filter(id=int(encrypt(request.POST['id'])))
                        newpartida = Partida.objects.get(id=request.POST['partidaimp'])

                        postulanteimportado = PersonaAplicarPartida( persona_id = postulante,
                                                                     partida_id=newpartida,
                                                                     observacion= form.cleaned_data['observacion'],
                                                                     archivojustificacion= form.cleaned_data['archivo']
                        )
                        postulanteimportado.archivojustificacion=request.FILES['archivo']
                        postulanteimportado.save(request)
                        return JsonResponse({'result': 'ok', 'mensaje': 'Registro guardado'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos. Detalle: %s' % (ex.__str__())})


        if action == 'addrequisitoperiodo':
            with transaction.atomic():
                try:
                    form = RequisitoCompetenciaPeriodoForm(request.POST)
                    if form.is_valid():
                        requisito = RequisitoCompetenciaPeriodo(
                            periodo_id=encrypt(form.data.get('id')),
                            requisito_competencia=form.cleaned_data.get('requisito_competencia'),
                            tipo_competencia=form.cleaned_data.get('tipo_competencia'),
                        )
                        requisito.save(request)
                        logobjeto(u'Agrego requisito en requisito {}'.format(requisito.__str__()), request, "add", None, requisito)
                        return JsonResponse({'error': False, 'mensaje': 'Registro guardado', 'data_return': True, 'data': model_to_dict(requisito)})
                    else:
                        raise NameError("El formulario contiene errores\n %s" % form.errors.as_ul())
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'error': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'delrequisitoperiodo':
            with transaction.atomic():
                try:
                    instancia = RequisitoCompetenciaPeriodo.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    logobjeto(u'Agrego requisito en requisito {}'.format(instancia.__str__()), request, "del", None, instancia)
                    res_json = {"error": False, "mensaje": 'Registro eliminado'}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)


        if action == 'addpregunta':
            with transaction.atomic():
                try:
                    id_periodo = int(encrypt(request.POST['id']))
                    form = PreguntaPeriodoPlanificacionForm(request.POST)
                    if form.is_valid() and form.validador(id_periodo):
                        pregunta_pp = PreguntaPeriodoPlanificacion(periodo_id=id_periodo,
                                                                  pregunta=form.cleaned_data['pregunta'])
                        pregunta_pp.save(request)
                        diccionario = {'id': pregunta_pp.id,
                                       'id_periodo': id_periodo,
                                       'pregunta': pregunta_pp.pregunta,
                                       'requerido': pregunta_pp.requerido
                                       }
                        log(u'Agrego pregunta de periodo planificacion: %s' % pregunta_pp, request, "add")
                        return JsonResponse({'result': True, 'data_return': True, 'mensaje': u'Guardado con exito', 'data': diccionario})
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'editpregunta':
            with transaction.atomic():
                try:
                    pregunta = PreguntaPeriodoPlanificacion.objects.get(pk=int(request.POST['id']))
                    if request.POST['name'] == 'requerido':
                        pregunta.requerido = eval(request.POST['val'].capitalize())
                        pregunta.save(request)
                        log(u'Edito estado mostrar de requisito : %s' % (pregunta), request,
                            "editrequisito")

                    if request.POST['name'] == 'pregunta':
                        pregunta.pregunta = eval(request.POST['val'].capitalize())
                        pregunta.save(request)
                        log(u'Edito estado opcional de requisito : %s' % (pregunta), request,
                            "editrequisito")

                    return JsonResponse({"result": True, 'mensaje': 'Cambios guardados'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': False, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'delpregunta':
            with transaction.atomic():
                try:
                    instancia = PreguntaPeriodoPlanificacion.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino pregunta de la planificacion: %s' % instancia, request, "del")
                    res_json = {"error": False, "mensaje": 'Registro eliminado'}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        if action == 'nummejorespuntuados':
            with transaction.atomic():
                try:
                    f = NumMejoresPuntuados(request.POST)
                    convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.POST['id'])))
                    if f.is_valid():
                        convocatoria.nummejorespuntuados = f.cleaned_data['nummejorespuntuados']
                        if convocatoria.nummejorespuntuados == 0:
                            return JsonResponse({'result': True, 'mensaje': u'Ingrese un número diferente de 0.'})
                        else:
                            convocatoria.save(request)
                            log(u'Configuró numero de mejores puntuados: %s' % convocatoria, request, "edit")
                            return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
                    else:
                        return JsonResponse({'result': True, 'mensaje': u'Ingrese datos válidos'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        elif action == 'addhorario':
            try:
                form = HorarioConvocatoriaForm(request.POST)
                if form.is_valid():
                    if HorarioConvocatoria.objects.filter(convocatoria_id=int(encrypt(request.POST['convocatoria'])),
                                                   turno=form.cleaned_data['turno'],
                                                   cupo=form.cleaned_data['cupo'],
                                                   tipo=form.cleaned_data['tipo'],
                                                   fecha=form.cleaned_data['fecha'], status=True).exists():
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Existe un horario con la misma fecha y turno."})
                    # solicitud.horario.dia == d.isoweekday():
                    clase = HorarioConvocatoria(convocatoria_id=int(encrypt(request.POST['convocatoria'])),
                                         turno=form.cleaned_data['turno'],
                                         tipo=form.cleaned_data['tipo'],
                                         dia=form.cleaned_data['fecha'].isoweekday(),
                                         fecha=form.cleaned_data['fecha'],
                                         detalle=form.cleaned_data['detalle'],
                                         cupo=form.cleaned_data['cupo'],
                                         lugar=form.cleaned_data['lugar'],
                                         mostrar=form.cleaned_data['mostrar'])
                    clase.save(request)
                    log(u'Adiciono horario en convocatoria: %s [%s]' % (clase, clase.id), request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'edithorario':
            try:
                with transaction.atomic():
                    filtro = HorarioConvocatoria.objects.get(pk=request.POST['id'])
                    f = HorarioConvocatoriaForm(request.POST)
                    if f.is_valid():
                        filtro.turno = f.cleaned_data['turno']
                        filtro.dia = f.cleaned_data['fecha'].isoweekday()
                        filtro.fecha = f.cleaned_data['fecha']
                        filtro.cupo = f.cleaned_data['cupo']
                        filtro.tipo = f.cleaned_data['tipo']
                        filtro.lugar = f.cleaned_data['lugar']
                        filtro.detalle = f.cleaned_data['detalle']
                        filtro.mostrar = f.cleaned_data['mostrar']
                        filtro.save(request)

                        log(u'Edito horario: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deletehorario':
            try:
                with transaction.atomic():
                    instancia = HorarioConvocatoria.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó horario de convocatoria: %s' % instancia, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addrenuncia':
            try:
                with transaction.atomic():
                    instance = None
                    if ConfiguraRenuncia.objects.filter(status=True, nombre=request.POST['nombre'],meses=request.POST['meses']).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "mensaje": 'La configuración ya existe.'}, safe=False)
                    else:
                        form = ConfiguraRenunciaForm(request.POST)
                        if form.is_valid():
                            instance = ConfiguraRenuncia(nombre=form.cleaned_data['nombre'],
                                                          meses=form.cleaned_data['meses'],
                                                          motivo=form.cleaned_data['motivo'],
                                                          activo=form.cleaned_data['activo'])
                            instance.save(request)
                            instance.cargos.clear()
                            instance.cargos.set(form.cleaned_data['cargos'])
                            instance.save(request)

                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "mensaje": "Error en el formulario"})
                    log(u'Adiciono Turno convocatoria: %s' % instance, request, "add")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, "mensaje": 'Intentelo más tarde.'}, safe=False)

        elif action == 'editrenuncia':
            try:
                with transaction.atomic():
                    filtro = ConfiguraRenuncia.objects.get(pk=encrypt(request.POST['id']))
                    f = ConfiguraRenunciaForm(request.POST)
                    if f.is_valid():
                        filtro.nombre = f.cleaned_data['nombre']
                        filtro.meses = f.cleaned_data['meses']
                        filtro.activo = f.cleaned_data['activo']
                        filtro.motivo=f.cleaned_data['motivo']
                        filtro.cargos.clear()
                        filtro.cargos.set(form.cleaned_data['cargos'])
                        filtro.save(request)
                        log(u'Edito configuración de renuncia: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)


        elif action == 'addturno':
            try:
                with transaction.atomic():
                    instance = None
                    if TurnoConvocatoria.objects.filter(status=True, comienza=request.POST['comienza'],termina=request.POST['termina']).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "mensaje": 'El turno que intenta ingresar ya existe.'}, safe=False)
                    else:
                        form = TurnoConvocatoriaForm(request.POST)
                        if form.is_valid():
                            instance = TurnoConvocatoria(turno=form.cleaned_data['turno'],
                                                          comienza=form.cleaned_data['comienza'],
                                                          termina=form.cleaned_data['termina'],
                                                          mostrar=form.cleaned_data['mostrar'])
                            instance.save(request)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "mensaje": "Error en el formulario"})
                    log(u'Adiciono Turno convocatoria: %s' % instance, request, "add")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, "mensaje": 'Intentelo más tarde.'}, safe=False)

        elif action == 'editturno':
            try:
                with transaction.atomic():
                    filtro = TurnoConvocatoria.objects.get(pk=request.POST['id'])
                    f = TurnoConvocatoriaForm(request.POST)
                    if f.is_valid():
                        filtro.turno = f.cleaned_data['turno']
                        filtro.comienza = f.cleaned_data['comienza']
                        filtro.termina = f.cleaned_data['termina']
                        filtro.mostrar=f.cleaned_data['mostrar']
                        filtro.save(request)
                        log(u'Edito turno convocatoria: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deleteturno':
            try:
                with transaction.atomic():
                    instancia = TurnoConvocatoria.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Turno de convocatori: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addtipoturno':
            try:
                with transaction.atomic():
                    instance = None
                    if TipoTurnoConvocatoria.objects.filter(status=True, nombre=request.POST['nombre']).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "mensaje": 'El tipo de turno que intenta ingresar ya existe.'}, safe=False)
                    else:
                        form = TipoTurnoConvocatoriaForm(request.POST)
                        if form.is_valid():
                            instance = TipoTurnoConvocatoria(nombre=form.cleaned_data['nombre'],
                                                          mostrar=form.cleaned_data['mostrar'])
                            instance.save(request)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "mensaje": "Error en el formulario"})
                    log(u'Adiciono tipo de turno convocatoria: %s' % instance, request, "add")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, "mensaje": 'Intentelo más tarde.'}, safe=False)

        elif action == 'edittipoturno':
            try:
                with transaction.atomic():
                    filtro = TipoTurnoConvocatoria.objects.get(pk=request.POST['id'])
                    f = TipoTurnoConvocatoriaForm(request.POST)
                    if f.is_valid():
                        filtro.nombre = f.cleaned_data['nombre']
                        filtro.mostrar=f.cleaned_data['mostrar']
                        filtro.save(request)
                        log(u'Edito tipo de turno en convocatoria: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deletetipoturno':
            try:
                with transaction.atomic():
                    instancia = TipoTurnoConvocatoria.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Turno de convocatori: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addmodelo':
            try:
                with transaction.atomic():
                    instance = None
                    if ModeloEvaluativoConvocatoria.objects.filter(status=True, nombre=request.POST['nombre']).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "mensaje": 'El modelo evaluativo que intenta ingresar ya existe.'}, safe=False)
                    else:
                        form = ModeloEvaluativoConvocatoriaForm(request.POST)
                        if form.is_valid():
                            instance = ModeloEvaluativoConvocatoria(nombre=form.cleaned_data['nombre'],
                                                          fecha=datetime.now(),
                                                          notamaxima=form.cleaned_data['notamaxima'],
                                                          notaaprobar=form.cleaned_data['notaaprobar'],
                                                          notarecuperacion=form.cleaned_data['notaaprobar'],
                                                          observaciones=form.cleaned_data['observaciones'],
                                                          activo=form.cleaned_data['activo']
                                                                    )
                            instance.save(request)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "mensaje": "Error en el formulario"})
                    log(u'Adiciono modelo evaluativo convocatoria: %s' % instance, request, "add")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, "mensaje": 'Intentelo más tarde.'}, safe=False)

        elif action == 'editmodelo':
            try:
                with transaction.atomic():
                    filtro = ModeloEvaluativoConvocatoria.objects.get(pk=request.POST['id'])
                    f = ModeloEvaluativoConvocatoriaForm(request.POST)
                    if f.is_valid():
                        filtro.nombre = f.cleaned_data['nombre']
                        filtro.activo=f.cleaned_data['activo']
                        filtro.notamaxima=f.cleaned_data['notamaxima']
                        filtro.notaaprobar=f.cleaned_data['notaaprobar']
                        filtro.notarecuperacion=f.cleaned_data['notamaxima']
                        filtro.observaciones=f.cleaned_data['observaciones']
                        filtro.save(request)
                        log(u'Edito modelo evaluativo en convocatoria: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deletemodelo':
            try:
                with transaction.atomic():
                    instancia = ModeloEvaluativoConvocatoria.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino modelo evaluativo: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addmodelodetalle':
            try:
                with transaction.atomic():
                    instance = None
                    modelo = ModeloEvaluativoConvocatoria.objects.get(pk=int(request.POST['id']))
                    if DetalleModeloEvaluativoConvocatoria.objects.filter(status=True, nombre=request.POST['nombre'],modelo=modelo).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "mensaje": 'El detalle del modelo evaluativo que intenta ingresar ya existe.'}, safe=False)
                    else:
                        form = DetalleModeloEvaluativoConvocatoriaForm(request.POST)
                        if form.is_valid():
                            instance = DetalleModeloEvaluativoConvocatoria(nombre=form.cleaned_data['nombre'],
                                                          notamaxima=form.cleaned_data['notamaxima'],
                                                          notaminima=form.cleaned_data['notaminima'],
                                                          decimales=form.cleaned_data['decimales'],
                                                          actualizaestado=form.cleaned_data['actualizaestado'],
                                                          determinaestadofinal=form.cleaned_data['determinaestadofinal'],
                                                          subearchivo=form.cleaned_data['subearchivo'],
                                                          dependiente=form.cleaned_data['dependiente'],
                                                          orden=form.cleaned_data['orden'],
                                                          tipo=form.cleaned_data['tipo'],
                                                          cargo=form.cleaned_data['cargo'],
                                                          descripcion=form.cleaned_data['descripcion'],
                                                          modelo=modelo
                                                                    )
                            instance.save(request)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "mensaje": "Error en el formulario"})
                    log(u'Adiciono modelo evaluativo convocatoria: %s' % instance, request, "add")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, "mensaje": 'Intentelo más tarde.'}, safe=False)

        elif action == 'editmodelodetalle':
            try:
                with transaction.atomic():
                    filtro = DetalleModeloEvaluativoConvocatoria.objects.get(pk=request.POST['id'])
                    f = DetalleModeloEvaluativoConvocatoriaForm(request.POST)
                    if f.is_valid():
                        filtro.nombre = f.cleaned_data['nombre']
                        filtro.notaminima=f.cleaned_data['notaminima']
                        filtro.notamaxima=f.cleaned_data['notamaxima']
                        filtro.decimales=f.cleaned_data['decimales']
                        filtro.actualizaestado=f.cleaned_data['actualizaestado']
                        filtro.determinaestadofinal=f.cleaned_data['determinaestadofinal']
                        filtro.dependiente=f.cleaned_data['dependiente']
                        filtro.subearchivo=f.cleaned_data['subearchivo']
                        filtro.orden=f.cleaned_data['orden']
                        filtro.tipo=f.cleaned_data['tipo']
                        filtro.cargo = f.cleaned_data['cargo']
                        filtro.descripcion = f.cleaned_data['descripcion']
                        filtro.save(request)
                        log(u'Edito modelo evaluativo en convocatoria: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deletemodelodetalle':
            try:
                with transaction.atomic():
                    instancia = DetalleModeloEvaluativoConvocatoria.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino modelo evaluativo: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)


        elif action == 'recordattendance':
            try:
                id = encrypt(request.POST['id'])
                registro = HorarioPersonaPartida.objects.get(status=True,id=int(id))
                registro.asistio = not registro.asistio
                registro.save(request)
                log("Registro la asistencia: %s"%(registro.__str__()),request,'change')
                res_json = {"error": False}
            except Exception as ex:
                err_ = f"Error: {ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"
                res_json = {"error": True,"message": err_}
            return JsonResponse(res_json, safe=False)

        elif action == 'generaractas':
            try:
                generar_actas(request)
                return JsonResponse({"result": False, "mensaje": f"Guardado con éxito"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Error al generar actas: {ex}"}, safe=False)

        elif action == 'delactas':
            try:
                partida = Partida.objects.get(id=encrypt_id(request.POST['id']))
                actas = partida.actas_partida()
                actas.update(status=False)
                return JsonResponse({"result": False, "mensaje": f"Guardado con éxito"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Error al generar actas: {ex}"}, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        # fin get
        adduserdata(request, data)
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addconvocatoria':
                try:
                    data['title'] = u'Adiccionar Convocatoria'
                    form = ConvocatoriaForm()
                    form.fields['fechainicio'].widget = CustomDateInput(attrs={'type': 'date', 'class': 'form-control', 'formwidth': '50%'})
                    form.fields['fechafin'].widget = CustomDateInput(attrs={'type': 'date', 'class': 'form-control', 'formwidth': '50%'})
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formconvocatoria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editconvocatoria':
                try:
                    data['title'] = u'Editar Convocatoria'
                    data['convocatoria'] = convocatoria = Convocatoria.objects.get(id=int(encrypt(request.GET['id'])))
                    initial = model_to_dict(convocatoria)
                    form = ConvocatoriaForm(initial=initial)
                    form.fields['fechainicio'].widget = CustomDateInput(attrs={'type': 'date', 'class': 'form-control', 'formwidth': '50%'})
                    form.fields['fechafin'].widget = CustomDateInput(attrs={'type': 'date', 'class': 'form-control', 'formwidth': '50%'})
                    form.fields['fechainicio'].initial = str(convocatoria.finicio)
                    form.fields['fechafin'].initial = str(convocatoria.ffin)
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formconvocatoria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'listarperiodoplanificacion':
                try:
                    data['periodo'] = periodoacademico = PeriodoAcademicoConvocatoria.objects.get(id=int(encrypt(request.GET['id'])))
                    data['title'] = u'Periodos de planificación'
                    search, filtro, url_vars = request.GET.get('s', ''), (Q(status=True) & Q(periodo=periodoacademico)), ''
                    url_vars = 'action={}'.format(action)
                    if search:
                        data['search'] = search
                        url_vars += "&s={}".format(search)
                        filtro = filtro & (Q(nombre__icontains=search))
                    listado = PeriodoPlanificacion.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 20)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['list_count'] = len(listado)
                    return render(request, "postulate/adm_postulate/listarperiodosplanificacion.html", data)
                except Exception as ex:
                    pass
            elif action == 'preguntasinformativas':
                try:
                    form = PreguntaPeriodoPlanificacionForm()
                    data['filtro'] = periodo_p = PeriodoAcademicoConvocatoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['listado'] = periodo_p.preguntas()
                    data['form'] = form
                    template = get_template("postulate/adm_periodoplanificacion/modal/formpreguntas.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'buscainstructor':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if len(s) == 1:
                        per = Persona.objects.filter(((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(
                            apellido2__icontains=q) | Q(cedula__contains=q))),administrativo__isnull=False).distinct()[:15]
                    elif len(s) == 2:
                        per = Persona.objects.filter(((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) | (
                                Q(nombres__icontains=s[0]) & Q(
                            nombres__icontains=s[1])) | (
                                                             Q(nombres__icontains=s[0]) & Q(
                                                         apellido1__contains=s[1]))),administrativo__isnull=False).distinct()[:15]
                    else:
                        per = Persona.objects.filter(((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(
                            apellido2__contains=s[2])) | (Q(nombres__contains=s[0]) & Q(
                            nombres__contains=s[1]) & Q(apellido1__contains=s[2]))),administrativo__isnull=False).distinct()[:15]

                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": str(x.nombre_completo())}
                                        for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'listarperiodoacademico':
                try:
                    data['title'] = u'Periodos académicos de planificación'
                    search, filtro, url_vars = request.GET.get('s', ''), (Q(status=True)), ''
                    url_vars = 'action={}'.format(action)
                    if search:
                        data['search'] = search
                        url_vars += "&s={}".format(search)
                        filtro = filtro & (Q(nombre__icontains=search))
                    listado = PeriodoAcademicoConvocatoria.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 20)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['list_count'] = len(listado)
                    return render(request, "postulate/adm_postulate/viewperiodosacademicos.html", data)
                except Exception as ex:
                    pass

            if action == 'listarpartidasplanificacion':
                try:
                    data['title'] = u'Partidas'
                    data ['periodo'] = periodo = PeriodoAcademicoConvocatoria.objects.get(pk=int(encrypt(request.GET['idp'])))
                    idpplanificacion = int(encrypt(request.GET['id']))
                    data['periodoplanificacion'] = periodoplanificacion = PeriodoPlanificacion.objects.get(id=idpplanificacion)
                    search, filtro, url_vars = request.GET.get('s', ''), (Q(status=True) & Q(periodoplanificacion=periodoplanificacion)), ''
                    url_vars = '&id={}&action={}'.format(request.GET['id'], action)
                    if search:
                        data['search'] = search
                        url_vars += "&search={}".format(search)
                        filtro = filtro & (Q(codpartida__icontains=search) | Q(estado__icontains=search))
                    listado = Partida.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 20)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['list_count'] = len(listado)
                    return render(request, "postulate/adm_postulate/listarpartidasplanificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'listarpartidas':
                try:
                    data['title'] = u'Partidas'
                    idconvocatoria = int(encrypt(request.GET['id']))
                    data['convocatoria'] = convocatoria = Convocatoria.objects.get(id=idconvocatoria)
                    search, filtro, url_vars = request.GET.get('s', ''), (Q(status=True) & Q(convocatoria=convocatoria)), ''
                    url_vars = '&id={}&action={}'.format(request.GET['id'], action)
                    if search:
                        data['search'] = search
                        url_vars += "&search={}".format(search)
                        filtro = filtro & (Q(denominacionpuesto__descripcion__icontains=search) | Q(codpartida__icontains=search))

                    listado = Partida.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 20)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['list_count'] = len(listado)
                    return render(request, "postulate/adm_postulate/listarpartidas.html", data)
                except Exception as ex:
                    pass

            if action == 'buscarasignaturas':
                try:
                    # id = request.GET['id']
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    querybase = Asignatura.objects.filter(status=True)
                    # if len(s) == 1:
                    per = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[:30]
                    # elif len(s) == 2:
                    #     per = querybase.filter((Q(nombre__contains=s[0]) & Q(nombre__contains=s[1])) | (Q(abreviatura__icontains=s[0]) & Q(abreviatura__icontains=s[1]))).filter(status=True).distinct()[:30]
                    # else:
                    #     per = querybase.filter((Q(nombre__contains=s[0]) & Q(nombre__contains=s[1])) | (Q(abreviatura__contains=s[0]) & Q(abreviatura__contains=s[1]))).filter(status=True).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'buscartitulos':
                try:
                    # id = request.GET['id']
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    querybase = Titulo.objects.filter(nivel_id__in=[3, 4, 21, 22, 23,30], status=True)
                    per = querybase.filter((Q(nombre__icontains=q) | Q(abreviatura__icontains=q)), Q(status=True)).distinct()[:100]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.abreviatura, x.nombre)} for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'listcampoespecifico':
                try:
                    campoamplio = request.GET.get('campoamplio')
                    listcampoamplio = campoamplio
                    if len(campoamplio) > 1:
                        listcampoamplio = campoamplio.split(',')
                    querybase = SubAreaConocimientoTitulacion.objects.filter(status=True, areaconocimiento__in=listcampoamplio).order_by('codigo')
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "idca": x.areaconocimiento.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'listcampodetallado':
                try:
                    campoespecifico = request.GET.get('campoespecifico')
                    listcampoespecifico = campoespecifico
                    if len(campoespecifico) > 1:
                        listcampoespecifico = campoespecifico.split(',')
                    querybase = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, areaconocimiento__in=listcampoespecifico).order_by('codigo')
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass


            if action == 'addperiodoplanificacion':
                try:
                    data['title'] = u'Adicionar Periodo Planificación'
                    form = PeriodoPlanificacionForm()
                    form.fields['fechainicio'].widget = CustomDateInput(attrs={'type': 'date', 'class': 'form-control', 'formwidth': '50%'})
                    form.fields['fechafin'].widget = CustomDateInput(attrs={'type': 'date', 'class': 'form-control', 'formwidth': '50%'})
                    data['idp'] = request.GET['idp']
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formperiodoplanificacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editperiodoplanificacion':
                try:
                    data['title'] = u'Editar Periodo de planificacion'
                    data['pplanificacion'] = pplanificacion = PeriodoPlanificacion.objects.get(id=int(encrypt(request.GET['id'])))
                    initial = model_to_dict(pplanificacion)
                    form = PeriodoPlanificacionForm(initial=initial)
                    form.fields['fechainicio'].widget = CustomDateInput(attrs={'type': 'date', 'class': 'form-control', 'formwidth': '50%'})
                    form.fields['fechafin'].widget = CustomDateInput(attrs={'type': 'date', 'class': 'form-control', 'formwidth': '50%'})
                    form.fields['fechainicio'].initial = str(pplanificacion.finicio)
                    form.fields['fechafin'].initial = str(pplanificacion.ffin)
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formperiodoplanificacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editperiodo':
                try:
                    data['title'] = u'Editar Periodo'
                    data['periodo'] = periodo = PeriodoAcademicoConvocatoria.objects.get(id=int(encrypt(request.GET['id'])))
                    data['id'] = periodo.id
                    initial = model_to_dict(periodo)
                    form = PeriodoAcademicoConvocatoriaForm(initial=initial)
                    data['form'] = form
                    template = get_template("postulate/adm_periodoplanificacion/modal/formperiodo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            if action == 'addpartida':
                try:
                    data['title'] = u'Adiccionar Partida'
                    form = PartidaForm()
                    form.fields['asignatura'].queryset = Asignatura.objects.none()
                    form.fields['titulos'].queryset = Titulo.objects.none()
                    data['form'] = form
                    data['idc'] = request.GET['idc']
                    return render(request, "postulate/adm_postulate/formpartida.html", data)
                except Exception as ex:
                    pass

            if action == 'editpartida':
                try:
                    data['title'] = u'Editar Partida'
                    data['partida'] = partida = Partida.objects.get(id=int(encrypt(request.GET['id'])))
                    data['armonizacionpartida'] = armonizacionpartida = partida.obtener_armonizacion()
                    data['partidaasignatura'] = partidaasignatura = PartidaAsignaturas.objects.filter(partida=partida, status=True).values_list('asignatura_id')
                    asignatura = Asignatura.objects.filter(id__in=partidaasignatura)
                    data['idc'] = request.GET['idc']
                    form = PartidaForm(initial={'codpartida': partida.codpartida,
                                                # 'titulo': partida.titulo,
                                                'observacion': partida.observacion,
                                                'denominacionpuesto': partida.denominacionpuesto,
                                                'campoamplio': partida.campoamplio.all(),
                                                'campoespecifico': partida.campoespecifico.all(),
                                                'campodetallado': partida.campodetallado.all(),
                                                'carrera': partida.carrera,
                                                'titulos': partida.titulos.all(),
                                                'nivel': partida.nivel,
                                                'modalidad': partida.modalidad,
                                                'dedicacion': partida.dedicacion,
                                                'jornada': partida.jornada,
                                                'rmu': partida.rmu,
                                                'vigente': partida.vigente,
                                                'asignatura': asignatura,
                                                'armonizacion':armonizacionpartida,
                                                'minhourcapa':partida.minhourcapa,
                                                'minmesexp':partida.minmesexp})
                    form.editar(partidaasignatura, partida)
                    data['form'] = form
                    return render(request, "postulate/adm_postulate/formpartida.html", data)
                except Exception as ex:
                    pass

            if action == 'infopartida':
                try:
                    data['partida'] = partida = Partida.objects.get(pk=int(request.GET['id']))
                    data['partidaasignaturas'] = PartidaAsignaturas.objects.filter(partida=partida, status=True)
                    template = get_template("postulate/adm_postulate/modal/formdetallepartida.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'addpartidaplanificacion':
                try:
                    data['title'] = u'Adicionar Partida de periodo de planificacion'
                    form = PartidaPlanificacionForm()
                    form.fields['asignatura'].queryset = Asignatura.objects.none()
                    form.fields['titulos'].queryset = Titulo.objects.none()
                    data['form'] = form
                    data['idc'] = request.GET['idc']
                    return render(request, "postulate/adm_postulate/formpartidaplanificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'editpartidaplanificacion':
                try:
                    data['title'] = u'Editar Partida'
                    data['partida'] = partida = Partida.objects.get(id=int(encrypt(request.GET['id'])))
                    data['partidaasignatura'] = partidaasignatura = PartidaAsignaturas.objects.filter(partida=partida, status=True).values_list('asignatura_id')
                    asignatura = Asignatura.objects.filter(id__in=partidaasignatura)
                    data['idc'] = request.GET['idc']
                    form = PartidaPlanificacionForm(initial={'codpartida': partida.codpartida,
                                                # 'titulo': partida.titulo,
                                                'observacion': partida.observacion,
                                                'campoamplio': partida.campoamplio.all(),
                                                'campoespecifico': partida.campoespecifico.all(),
                                                'campodetallado': partida.campodetallado.all(),
                                                'carrera': partida.carrera,
                                                'titulos': partida.titulos.all(),
                                                'nivel': partida.nivel,
                                                'modalidad': partida.modalidad,
                                                'dedicacion': partida.dedicacion,
                                                'jornada': partida.jornada,
                                                'rmu': partida.rmu,
                                                'asignatura': asignatura})
                    form.editar(partidaasignatura, partida)
                    data['form'] = form
                    return render(request, "postulate/adm_postulate/formpartidaplanificacion.html", data)
                except Exception as ex:
                    pass

            # if action == 'revisarpartidaplanificacion':
            #     try:
            #         data['id'] = id = request.GET['id']
            #         data['partida'] = partida = Partida.objects.get(pk=int(id))
            #         data['partidaasignaturas'] = partidaasignatura = PartidaAsignaturas.objects.filter(partida=partida, status=True)
            #         data['form2'] = HistorialAprobacionPartidaForm()
            #         template = get_template("postulate/adm_postulate/modal/formrevisarpartida.html")
            #         return JsonResponse({"result": True, 'data': template.render(data)})
            #     except Exception as ex:
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})



            if action == 'importpartidaplanificacion':
                try:
                    data['title'] = u'Importar Partidas'
                    form = ImportPartidaForm()
                    data['form'] = form
                    data['id'] = int(encrypt(request.GET['id']))
                    template = get_template("postulate/adm_postulate/modal/formimportpartida.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'enviarcorreomasivo':
                try:
                    data['title'] = u'Enviar Correos'
                    form = EnvioCorreoForm()
                    data['form'] = form
                    convocatoriaselect = []
                    listaintegrantestribunal = []
                    idsintegrantes = ''
                    if 'ids' in request.GET:
                        convocatoriaselect = request.GET['ids'].split(',')
                    for con in convocatoriaselect:
                        partidas = Partida.objects.filter(status=True, convocatoria_id=con)
                        if partidas:
                            for p in partidas:
                                data['listado'] = tribunal = p.partidatribunal_set.values_list('persona', flat=True).filter(status=True).order_by('persona').distinct()
                                if tribunal:
                                    for t in tribunal:
                                        integrante = Persona.objects.get(pk=t)
                                        if integrante not in listaintegrantestribunal:
                                            listaintegrantestribunal.append(integrante)
                                            idsintegrantes += str(t)+','

                    data['listadoseleccion'] = listaintegrantestribunal
                    # data['count'] = listaintegrantestribunal.count()
                    data['idsseleccion'] = idsintegrantes

                    template = get_template("postulate/adm_postulate/modal/formenviocorreomasivo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'listpartidaplanificacion':
                try:
                    periodoplanificacion = request.GET.get('periodoplanificacion')
                    listpartidaplanificacion = periodoplanificacion
                    if len(periodoplanificacion) > 1:
                        listpartidaplanificacion = listpartidaplanificacion.split(',')
                    querybase = Partida.objects.filter(status=True, periodoplanificacion__id__in=listpartidaplanificacion, convocatoria_id__isnull=True)
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(denominacionpuesto__descripcion__icontains=q) | Q(codpartida__icontains=q) | Q(periodoplanificacion__nombre__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.codpartida, x.titulo)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'mejorespuntuados':
                try:
                    data['partida'] = partida = Partida.objects.get(id=int(encrypt(request.GET['id'])))
                    data['title'] = u'Mejores Puntuados {}'.format(partida.__str__())
                    nummejores = partida.convocatoria.nummejorespuntuados
                    listado = partida.personaaplicarpartida_set.filter(status=True, estado=1,esmejorpuntuado=True).order_by('-nota_final_meritos')
                    data['listado'] = listado
                    return render(request, "postulate/adm_postulate/mejorespuntuados.html", data)
                except Exception as ex:
                    pass

            elif action == 'addperiodo':
                try:
                    data['title'] = u'Adicionar Periodo'
                    form = PeriodoAcademicoConvocatoriaForm()
                    data['form'] = form
                    template = get_template("postulate/adm_periodoplanificacion/modal/formperiodo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'logica':
                try:
                    data['title'] = u'Logica del modelo'
                    data['filtro'] = modelo = ModeloEvaluativoConvocatoria.objects.get(id=int(encrypt(request.GET['id'])))
                    form = LogicaModeloEvaluativoConvocatoriaForm(initial={'logica': modelo.logicamodelo})
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formmodelodetalle.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'moverperiodoplanificacion':
                try:
                    data['title'] = u'Mover periodo'
                    data['id'] = int(encrypt(request.GET['id']))
                    form = MoverPeriodoPlanificacionForm()
                    data['form'] = form
                    template = get_template("postulate/adm_periodoplanificacion/modal/formmover.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'bancodatos':
                try:
                    data['partida'] = partida = Partida.objects.get(id=int(encrypt(request.GET['id'])))
                    data['title'] = u'Banco de Habilitantes {}'.format(partida.__str__())
                    if partida.ganador():
                        listado = partida.personaaplicarpartida_set.filter(status=True).exclude(esganador=True).order_by('-nota_final_meritos')
                    else:
                        nummejores = partida.convocatoria.nummejorespuntuados
                        listado = partida.personaaplicarpartida_set.filter(status=True, estado=1,esmejorpuntuado=True).order_by('-nota_final_meritos')
                    data['listado'] = listado
                    return render(request, "postulate/adm_postulate/bancopostulantes.html", data)
                except Exception as ex:
                    messages.error(request, 'No existen datos {}'.format(str(ex)))

            if action == 'agendardisertacion':
                try:
                    data['postulacion'] = postulacion = PersonaAplicarPartida.objects.get(id=int(encrypt(request.GET['id'])))
                    convocatoria = ConvocatoriaPostulante.objects.filter(persona=postulacion).first()
                    if convocatoria:
                        initial = model_to_dict(convocatoria)
                        form = AgendaDisertacionForm(initial=initial)
                        data['convocatoria'] = convocatoria
                    else:
                        form = AgendaDisertacionForm()
                        form.fields['tema'].initial = postulacion.partida.temadisertacion
                        form.fields['observacion'].initial = postulacion.partida.observacion
                    form.fields['fechaasistencia'].widget = CustomDateInput(attrs={'type': 'date', 'class': 'form-control', 'formwidth': '50%'})
                    form.fields['horasistencia'].widget = CustomDateInput(attrs={'type': 'time', 'class': 'form-control', 'formwidth': '50%'})
                    if convocatoria:
                        form.fields['fechaasistencia'].initial = str(convocatoria.fechaasistencia)
                        form.fields['horasistencia'].initial = str(convocatoria.horasistencia)
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/agendaconvocatoriapostulante.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'viewtribunalprimera':
                idpartida = int(encrypt(request.GET['id']))
                data['partida'] = partida = Partida.objects.get(id=idpartida)
                data['action'] = action
                data['listado'] = partida.partidatribunal_set.filter(status=True, tipo=1).order_by('id')
                template = get_template("postulate/adm_postulate/modal/viewtribunal.html")
                return JsonResponse({"result": True, 'data': template.render(data), 'footer': True})

            if action == 'viewtribunalsegunda':
                idpartida = int(encrypt(request.GET['id']))
                data['partida'] = partida = Partida.objects.get(id=idpartida)
                data['action'] = action
                data['listado'] = partida.partidatribunal_set.filter(status=True, tipo=2).order_by('id')
                template = get_template("postulate/adm_postulate/modal/viewtribunalsegunda.html")
                return JsonResponse({"result": True, 'data': template.render(data), 'footer': True})

            if action == 'addtribunal':
                try:
                    idconvocatoria = int(encrypt(request.GET['id']))
                    data['convocatoria'] = convocatoria = Convocatoria.objects.get(id=idconvocatoria)
                    form = TribunalForm()
                    form.cargar_partidas(convocatoria)
                    data['form'] = form
                    data['action'] = action

                    template = get_template("postulate/adm_postulate/modal/formtribunal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as e:
                    print(e)

            if action == 'buscar_persona':
                data = []
                term = request.GET['term'].upper().strip()
                s = term.split(" ")
                if len(s) == 1:
                    query = Persona.objects.filter(Q(apellido1__icontains=s[0]) | Q(cedula__icontains=s[0])).select_related().values('id', 'apellido1', 'apellido2', 'nombres', 'cedula')
                elif len(s) == 2:
                    query = Persona.objects.filter(Q(apellido1__icontains=s[0]) & Q(apellido2__icontains=s[1]) | Q(apellido1__icontains=s[0]) & Q(nombres__icontains=s[1])).select_related().values('id', 'apellido1', 'apellido2', 'nombres', 'cedula')
                else:
                    query = Persona.objects.filter(Q(apellido1__icontains=s[0]) & Q(apellido2__icontains=s[1]) & Q(nombres__icontains=s[2]) | Q(apellido1__icontains=s[0]) & Q(nombres__icontains=s[1]) | Q(apellido1__icontains=s[0]) & Q(nombres__icontains=s[2])).select_related().values('id', 'apellido1', 'apellido2', 'nombres', 'cedula')
                query = query.order_by('apellido1')
                for a in query[0:10]:
                    result = {'id': a['id'], 'text': str('{} {} {} - {}'.format(a['apellido1'], a['apellido2'], a['nombres'], a['cedula']))}
                    data.append(result)
                return HttpResponse(json.dumps(data), content_type='application/json')

            if action == 'actaconformacion':
                try:
                    fecha = datetime.now().date()
                    data['fecha_letra'] = fecha_letra(fecha.__str__())
                    if 'fecha' in request.GET:
                        fecha = request.GET['fecha']
                        if not fecha=='':
                            data['fecha_letra'] = fecha_letra(datetime.strptime(fecha, '%d-%m-%Y').date().__str__())
                    data['partida'] = partida = Partida.objects.get(id=int(request.GET['idp']))

                    data['firmas'] = PartidaTribunal.objects.filter(partida=partida, status=True, tipo=1,firma=True).order_by('id')

                    return conviert_html_to_pdf(
                        'postulate/actas/actaconformacion.html',
                        {
                            'pagesize': 'a4 landscape',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    messages.error(request, str(ex))

            if action == 'actacalificacionmerito':
                try:
                    data['partida'] = partida = Partida.objects.get(id=int(request.GET['idp']))
                    data['firmas'] = PartidaTribunal.objects.filter(partida=partida, status=True, tipo=1).order_by('id')
                    data['participantes'] = participantes = PersonaAplicarPartida.objects.filter(partida=partida, status=True).order_by('persona__apellido1', 'persona__nombres')
                    data['total'] = len(participantes)
                    if partida.convocatoria.modeloevaluativoconvocatoria:
                        return conviert_html_to_pdf(
                            'postulate/actas/actacalificacionmeritov2.html',
                            {'data': data}
                        )
                    return conviert_html_to_pdf(
                        'postulate/actas/actacalificacionmerito.html',
                        {'data': data}
                    )
                except Exception as ex:
                    messages.error(request, str(ex))

            if action == 'actacalificacionmerito2':
                try:
                    data['partida'] = partida = Partida.objects.get(id=int(request.GET['idp']))
                    data['firmas'] = PartidaTribunal.objects.filter(partida=partida, status=True, tipo=1).order_by('id')
                    data['participantes'] = participantes = PersonaAplicarPartida.objects.filter(partida=partida, status=True).order_by('persona__apellido1', 'persona__nombres')
                    data['total'] = len(participantes)
                    if partida.convocatoria.modeloevaluativoconvocatoria:
                        return conviert_html_to_pdf(
                            'postulate/actas/actacalificacionmeritodesempatev2.html',
                            {'data': data}
                        )
                    return conviert_html_to_pdf(
                        'postulate/actas/actacalificacionmeritodesempate.html',
                        {'data': data}
                    )
                except Exception as ex:
                    messages.error(request, str(ex))

            if action == 'actaentrevistatrib2':
                try:
                    data['partida'] = partida = Partida.objects.get(id=int(request.GET['idp']))
                    data['firmas'] = tribunal = PartidaTribunal.objects.filter(partida=partida, status=True, tipo=2).order_by('id')
                    data['participantes'] = participantes = partida.personaaplicarpartida_set.filter(status=True, estado__in=[1,4],esmejorpuntuado=True).order_by('-nota_final_entrevista')
                    data['total'] = len(participantes)
                    if partida.convocatoria.modeloevaluativoconvocatoria:
                        return conviert_html_to_pdf(
                            'postulate/actas/actaentrevistav2.html',
                            {'data': data}
                        )
                    return conviert_html_to_pdf(
                        'postulate/actas/actaentrevista.html',
                        {'data': data}
                    )
                except Exception as ex:
                    messages.error(request, str(ex))

            if action == 'actapuntajefinaltrib2':
                try:
                    data['partida'] = partida = Partida.objects.get(id=int(request.GET['idp']))
                    data['firmas'] = PartidaTribunal.objects.filter(partida=partida, status=True, tipo=2,firma=True).order_by('id')
                    data['participantes'] = participantes = partida.personaaplicarpartida_set.filter(status=True, esmejorpuntuado=True).order_by('-nota_final_entrevista')
                    data['total'] = len(participantes)
                    if partida.convocatoria.modeloevaluativoconvocatoria:
                        data['campos'] = partida.convocatoria.modeloevaluativoconvocatoria.campos()

                        return conviert_html_to_pdf(
                            'postulate/actas/actanotafinalv2.html',
                            {'data': data}
                        )
                    return conviert_html_to_pdf(
                        'postulate/actas/actanotafinal.html',
                        {'data': data}
                    )
                except Exception as ex:
                    messages.error(request, str(ex))

            if action == 'listarterminos':
                try:
                    data['id'] = id = encrypt(request.GET['id'])
                    idconvocatoria = int(encrypt(request.GET['id']))
                    data['title'] = u'Terminos y Condiciones'
                    data['convocatoria'] = convocatoria = Convocatoria.objects.get(id=idconvocatoria)
                    search, filtro, url_vars = request.GET.get('s', ''), (Q(status=True)), ''
                    url_vars = '&action={}'.format(action)
                    if search:
                        data['search'] = search
                        url_vars += "&s={}".format(search)
                        filtro = filtro & (Q(descripcion__icontains=search))

                    if id:
                        data['id'] = id
                        url_vars += "&id={}".format(request.GET['id'])
                        filtro = filtro & (Q(convocatoria_id=id))

                    listado = ConvocatoriaTerminosCondiciones.objects.filter(filtro).order_by('descripcion')
                    paging = MiPaginador(listado, 20)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['list_count'] = len(listado)
                    return render(request, "postulate/adm_postulate/listarterminos.html", data)
                except Exception as ex:
                    pass

            if action == 'addtermino':
                try:
                    data['termino'] = Convocatoria.objects.get(id=int(encrypt(request.GET['id'])))
                    data['title'] = u'Adicionar Terminos y Condiciones'
                    data['form'] = ConvocatoriaTerminosForm()
                    template = get_template("postulate/adm_postulate/modal/formterminoscondiciones.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'edittermino':
                try:
                    data['title'] = u'Editar Terminos y Condiciones'
                    data['termino'] = termino = ConvocatoriaTerminosCondiciones.objects.get(id=int(encrypt(request.GET['id'])))
                    initial = model_to_dict(termino)
                    data['form'] = ConvocatoriaTerminosForm(initial=initial)
                    template = get_template("postulate/adm_postulate/modal/formterminoscondiciones.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'exportarpartidas':
                try:
                    convocatoria = Convocatoria.objects.get(id=request.GET['id'])
                    response = HttpResponse(content_type='application/ms-excel')
                    nom_convocatoria = convocatoria.descripcion.replace(' ', '_').lower()
                    response['Content-Disposition'] = 'attachment; filename="partidas_convocatoria_{}.xls"'.format(nom_convocatoria)
                    title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf('font: name Calibri, color-index black, bold on , height 250; alignment: horiz centre')
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    fuentecabecera = easyxf('font: name Calibri, color-index black, bold on; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    wb = xlwt.Workbook(encoding='utf-8')
                    ws = wb.add_sheet('partidas')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, '{}'.format(convocatoria.descripcion), title2)
                    row_num = 2
                    columns = [
                        ('Cod. Partida', 10000),
                        ('Denominación puesto', 10000),
                        # ('Descripción', 10000),
                        ('Carrera', 10000),
                        ('Campo Amplio', 10000),
                        ('Campo Especifico', 10000),
                        ('Campo Detallado', 10000),
                        ('Títulos Relacionados', 6000),
                        ('Nivel', 20000),
                        ('Modalidad', 20000),
                        ('Dedicación', 20000),
                        ('Jornada', 20000),
                        ('RMU', 20000),
                        ('Vigente', 20000),
                        ('Total Postulantes', 20000), ]
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    listado = Partida.objects.filter(status=True, convocatoria=convocatoria).order_by('id')
                    for det in listado:
                        ws.write(row_num, 0, det.codpartida, style2)
                        ws.write(row_num, 1, str(det.denominacionpuesto), style2)
                        # ws.write(row_num, 2, det.descripcion, style2)
                        ws.write(row_num, 2, det.carrera.__str__() if det.carrera else '', style2)
                        campo_amplio = ''
                        for ca in det.campoamplio.all():
                            campo_amplio += '{}, '.format(ca.__str__())
                        ws.write(row_num, 3, campo_amplio, style2)
                        campo_especifico = ''
                        for ca in det.campoespecifico.all():
                            campo_especifico += '{}, '.format(ca.__str__())
                        ws.write(row_num, 4, campo_especifico, style2)
                        campo_detallado = ''
                        for ca in det.campodetallado.all():
                            campo_detallado += '{}, '.format(ca.__str__())
                        ws.write(row_num, 5, campo_detallado, style2)
                        titulos_relacionados = ''
                        for ca in det.titulos.all():
                            titulos_relacionados += '{}, '.format(ca.__str__())
                        ws.write(row_num, 6, titulos_relacionados, style2)
                        ws.write(row_num, 7, det.get_nivel_display(), style2)
                        ws.write(row_num, 8, det.get_modalidad_display(), style2)
                        ws.write(row_num, 9, det.get_dedicacion_display(), style2)
                        ws.write(row_num, 10, det.get_jornada_display(), style2)
                        ws.write(row_num, 11, det.rmu, style2)
                        ws.write(row_num, 12, 'SI' if det.vigente else 'NO', style2)
                        ws.write(row_num, 13, det.total_postulantes(), style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    messages.success(request, str(ex))

            if action == 'excel_postulantes__all':
                try:
                    response = HttpResponse(content_type='application/ms-excel')
                    response['Content-Disposition'] = 'attachment; filename="postulantes_all.xls"'
                    title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf('font: name Calibri, color-index black, bold on , height 250; alignment: horiz centre')
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    fuentecabecera = easyxf('font: name Calibri, color-index black, bold on; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    wb = xlwt.Workbook(encoding='utf-8')
                    ws = wb.add_sheet('postulantes')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'LISTADO DE POSTULANTES', title2)
                    row_num = 2
                    columns = [
                        ('Convocatoria', 10000),
                        ('Categoria', 10000),
                        ('Partida', 30000),
                        ('Carrera', 30000),
                        ('Asignaturas', 30000),
                        ('Dedicación', 10000),
                        ('RMU', 10000),
                        ('Nivel', 10000),
                        ('Modalidad', 10000),
                        ('Jornada', 10000),
                        ('Campo Amplio', 30000),
                        ('Campo Especifico', 30000),
                        ('Campo Detallado', 30000),
                        ('Cod. Unico', 10000),
                        ('Apellidos', 10000),
                        ('Nombres', 10000),
                        ('Titulo', 25000),
                        ('Archivo', 10000),
                        ('Identificación', 10000),
                        ('Correo', 10000),
                        ('Telf.', 10000),
                        ('Telf. Conv.', 10000),
                        ('Estado Calificación', 10000),
                        ('¿Tiene Formación?', 10000),
                        ('¿Tiene Experiencia?', 10000),
                        ('¿Tiene Capacitación?', 10000),
                        ('¿Tiene Publicaciones?', 10000),
                        ('¿Tiene Certificación Idiomas?', 10000),
                        ('Nota Formación', 10000),
                        ('Obs. Formación', 20000),
                        ('Nota Exp. Docente', 10000),
                        ('Obs. Exp. Docente', 20000),
                        ('Nota Exp. Administrativo', 10000),
                        ('Obs. Exp. Administrativo', 20000),
                        ('Nota Capacitación', 10000),
                        ('Obs. Capacitación', 20000),
                        ('¿Aplico Desempate?', 10000),
                        ('Nota Desempate', 10000),
                        ('Nota Final', 10000),
                        ('Obs. Final', 20000),
                        ('Estado', 10000),
                        ('¿Calificada?', 10000),
                        ('¿Apelo?', 10000),
                        ('Estado Apelación', 10000),
                        ('Obs. Apelación', 20000),
                        ('Usuario Revisión Meritos', 10000),
                        ('Fecha Revisión Meritos', 10000),
                        ('Usuario Revisión Apelación', 10000),
                        ('Fecha Revisión Apelación', 10000),
                        ('Usuario Revisión Desempate', 10000),
                        ('Fecha Revisión Desempate', 10000),
                    ]
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    convocatoria = Convocatoria.objects.get(status=True,pk = int(request.GET['id']))
                    listado = PersonaAplicarPartida.objects.filter(status=True, partida__convocatoria=convocatoria).order_by('partida__convocatoria__descripcion')
                    for det in listado:
                        if det.persona.mis_titulaciones().count() > 0:
                            row_count = row_num + det.persona.mis_titulaciones().count() - 1
                            titulos = det.persona.mis_titulaciones()
                            ws.write_merge(row_num, row_count, 0, 0, det.partida.convocatoria.descripcion, style2)
                            ws.write_merge(row_num, row_count, 1, 1, det.partida.convocatoria.tipocontrato.nombre if det.partida.convocatoria.tipocontrato else '', style2)
                            ws.write_merge(row_num, row_count, 2, 2, str(det.partida), style2)
                            ws.write_merge(row_num, row_count, 3, 3, det.partida.carrera.__str__() if det.partida.carrera else '', style2)
                            asignaturas_ = ''
                            for asig in det.partida.partidas_asignaturas():
                                asignaturas_ += '{}, '.format(asig.__str__())
                            ws.write_merge(row_num, row_count, 4, 4, asignaturas_, style2)
                            ws.write_merge(row_num, row_count, 5, 5, det.partida.get_dedicacion_display(), style2)
                            ws.write_merge(row_num, row_count, 6, 6, det.partida.rmu, style2)
                            ws.write_merge(row_num, row_count, 7, 7, det.partida.get_nivel_display(), style2)
                            ws.write_merge(row_num, row_count, 8, 8, det.partida.get_modalidad_display(), style2)
                            ws.write_merge(row_num, row_count, 9, 9, det.partida.get_jornada_display(), style2)
                            campo_amplio = ''
                            for ca in det.partida.campoamplio.all():
                                campo_amplio += '{}, '.format(ca.__str__())
                            ws.write_merge(row_num, row_count, 10, 10, campo_amplio, style2)
                            campo_especifico = ''
                            for ca in det.partida.campoespecifico.all():
                                campo_especifico += '{}, '.format(ca.__str__())
                            ws.write_merge(row_num, row_count, 11, 11, campo_especifico, style2)
                            campo_detallado = ''
                            for ca in det.partida.campodetallado.all():
                                campo_detallado += '{}, '.format(ca.__str__())
                            ws.write_merge(row_num, row_count, 12, 12, campo_detallado, style2)
                            ws.write_merge(row_num, row_count, 13, 13, det.pk, style2)
                            ws.write_merge(row_num, row_count, 14, 14, "{} {}".format(det.persona.apellido1, det.persona.apellido2), style2)
                            ws.write_merge(row_num, row_count, 15, 15, "{}".format(det.persona.nombres), style2)

                            ws.write_merge(row_num, row_count, 18, 18, det.persona.cedula, style2)
                            ws.write_merge(row_num, row_count, 19, 19, det.persona.email, style2)
                            ws.write_merge(row_num, row_count, 20, 20, det.persona.telefono, style2)
                            ws.write_merge(row_num, row_count, 21, 21, det.persona.telefono_conv, style2)
                            ws.write_merge(row_num, row_count, 22, 22, det.get_estado_display(), style2)
                            ws.write_merge(row_num, row_count, 23, 23, 'SI' if det.tiene_formacionacademica() else 'NO', style2)
                            ws.write_merge(row_num, row_count, 24, 24, 'SI' if det.tiene_experienciapartida() else 'NO', style2)
                            ws.write_merge(row_num, row_count, 25, 25, 'SI' if det.tiene_capacitaciones() else 'NO', style2)
                            ws.write_merge(row_num, row_count, 26, 26, 'SI' if det.tiene_publicaciones() else 'NO', style2)
                            ws.write_merge(row_num, row_count, 27, 27, 'SI' if det.tiene_idiomas() else 'NO', style2)
                            ws.write_merge(row_num, row_count, 28, 28, det.pgradoacademico, style2)
                            ws.write_merge(row_num, row_count, 29, 29, det.obsgradoacademico, style2)
                            ws.write_merge(row_num, row_count, 30, 30, det.pexpdocente, style2)
                            ws.write_merge(row_num, row_count, 31, 31, det.obsexperienciadoc, style2)
                            ws.write_merge(row_num, row_count, 32, 32, det.pexpadministrativa, style2)
                            ws.write_merge(row_num, row_count, 33, 33, det.obsexperienciaadmin, style2)
                            ws.write_merge(row_num, row_count, 34, 34, det.pcapacitacion, style2)
                            ws.write_merge(row_num, row_count, 35, 35, det.obscapacitacion, style2)
                            ws.write_merge(row_num, row_count, 36, 36, 'SI' if det.aplico_desempate else 'NO', style2)
                            ws.write_merge(row_num, row_count, 37, 37, det.nota_desempate, style2)
                            ws.write_merge(row_num, row_count, 38, 38, det.nota_final_meritos, style2)
                            ws.write_merge(row_num, row_count, 39, 39, det.obsgeneral, style2)
                            ws.write_merge(row_num, row_count, 40, 40, det.get_estado_display(), style2)
                            ws.write_merge(row_num, row_count, 41, 41, 'SI' if det.calificada else 'NO', style2)
                            ws.write_merge(row_num, row_count, 42, 42, 'SI' if det.solapelacion else 'NO', style2)
                            ws.write_merge(row_num, row_count, 43, 43, det.traer_apelacion().get_estado_display() if det.traer_apelacion() else '', style2)
                            obs_revisor, revisado_por, fecha_revision = '', '', ''
                            if det.traer_apelacion():
                                if det.traer_apelacion().estado != 0:
                                    obs_revisor = det.traer_apelacion().observacion_revisor
                                    revisado_por = det.traer_apelacion().revisado_por.username if det.traer_apelacion().revisado_por else ''
                                    fecha_revision = str(det.traer_apelacion().fecha_revision)
                            ws.write_merge(row_num, row_count, 44, 44, obs_revisor, style2)
                            ws.write_merge(row_num, row_count, 45, 45, revisado_por, style2)
                            ws.write_merge(row_num, row_count, 46, 46, fecha_revision, style2)
                            ws.write_merge(row_num, row_count, 47, 47, det.revisado_por.username if det.revisado_por else '', style2)
                            ws.write_merge(row_num, row_count, 48, 48, str(det.fecha_revision) if det.fecha_revision else '', style2)
                            ws.write_merge(row_num, row_count, 49, 49, det.desempate_revisado_por.username if det.desempate_revisado_por else '', style2)
                            ws.write_merge(row_num, row_count, 50, 50, str(det.desempate_fecha_revision) if det.desempate_fecha_revision else '', style2)
                            for dato in titulos:
                                ws.write(row_num, 16, "{}".format(dato.titulo), style2)
                                ws.write(row_num, 17, "https://sga.unemi.edu.ec/{}".format(dato.archivo.url) if dato.archivo else '', style2)
                                row_num += 1
                        else:
                            ws.write(row_num, 0, det.partida.convocatoria.descripcion, style2)
                            ws.write(row_num, 1, det.partida.convocatoria.tipocontrato.nombre if det.partida.convocatoria.tipocontrato else '', style2)
                            ws.write(row_num, 2, str(det.partida), style2)
                            ws.write(row_num, 3, det.partida.carrera.__str__() if det.partida.carrera else '', style2)
                            asignaturas_ = ''
                            for asig in det.partida.partidas_asignaturas():
                                asignaturas_ += '{}, '.format(asig.__str__())
                            ws.write(row_num, 4, asignaturas_, style2)
                            ws.write(row_num, 5, det.partida.get_dedicacion_display(), style2)
                            ws.write(row_num, 6, det.partida.rmu, style2)
                            ws.write(row_num, 7, det.partida.get_nivel_display(), style2)
                            ws.write(row_num, 8, det.partida.get_modalidad_display(), style2)
                            ws.write(row_num, 9, det.partida.get_jornada_display(), style2)
                            campo_amplio = ''
                            for ca in det.partida.campoamplio.all():
                                campo_amplio += '{}, '.format(ca.__str__())
                            ws.write(row_num, 10, campo_amplio, style2)
                            campo_especifico = ''
                            for ca in det.partida.campoespecifico.all():
                                campo_especifico += '{}, '.format(ca.__str__())
                            ws.write(row_num, 11, campo_especifico, style2)
                            campo_detallado = ''
                            for ca in det.partida.campodetallado.all():
                                campo_detallado += '{}, '.format(ca.__str__())
                            ws.write(row_num, 12, campo_detallado, style2)
                            ws.write(row_num, 13, det.pk, style2)
                            ws.write(row_num, 14, "{} {}".format(det.persona.apellido1, det.persona.apellido2), style2)
                            ws.write(row_num, 15, "{}".format(det.persona.nombres), style2)
                            ws.write(row_num, 16, "", style2)
                            ws.write(row_num, 17, "", style2)
                            ws.write(row_num, 18, det.persona.cedula, style2)
                            ws.write(row_num, 19, det.persona.email, style2)
                            ws.write(row_num, 20, det.persona.telefono, style2)
                            ws.write(row_num, 21, det.persona.telefono_conv, style2)
                            ws.write(row_num, 22, det.get_estado_display(), style2)
                            ws.write(row_num, 23, 'SI' if det.tiene_formacionacademica() else 'NO', style2)
                            ws.write(row_num, 24, 'SI' if det.tiene_experienciapartida() else 'NO', style2)
                            ws.write(row_num, 25, 'SI' if det.tiene_capacitaciones() else 'NO', style2)
                            ws.write(row_num, 26, 'SI' if det.tiene_publicaciones() else 'NO', style2)
                            ws.write(row_num, 27, 'SI' if det.tiene_idiomas() else 'NO', style2)
                            ws.write(row_num, 28, det.pgradoacademico, style2)
                            ws.write(row_num, 29, det.obsgradoacademico, style2)
                            ws.write(row_num, 30, det.pexpdocente, style2)
                            ws.write(row_num, 31, det.obsexperienciadoc, style2)
                            ws.write(row_num, 32, det.pexpadministrativa, style2)
                            ws.write(row_num, 33, det.obsexperienciaadmin, style2)
                            ws.write(row_num, 34, det.pcapacitacion, style2)
                            ws.write(row_num, 35, det.obscapacitacion, style2)
                            ws.write(row_num, 36, 'SI' if det.aplico_desempate else 'NO', style2)
                            ws.write(row_num, 37, det.nota_desempate, style2)
                            ws.write(row_num, 38, det.nota_final_meritos, style2)
                            ws.write(row_num, 39, det.obsgeneral, style2)
                            ws.write(row_num, 40, det.get_estado_display(), style2)
                            ws.write(row_num, 41, 'SI' if det.calificada else 'NO', style2)
                            ws.write(row_num, 42, 'SI' if det.solapelacion else 'NO', style2)
                            ws.write(row_num, 43, det.traer_apelacion().get_estado_display() if det.traer_apelacion() else '', style2)
                            obs_revisor, revisado_por, fecha_revision = '', '', ''
                            if det.traer_apelacion():
                                if det.traer_apelacion().estado != 0:
                                    obs_revisor = det.traer_apelacion().observacion_revisor
                                    revisado_por = det.traer_apelacion().revisado_por.username if det.traer_apelacion().revisado_por else ''
                                    fecha_revision = str(det.traer_apelacion().fecha_revision)
                            ws.write(row_num, 44, obs_revisor, style2)
                            ws.write(row_num, 45, revisado_por, style2)
                            ws.write(row_num, 46, fecha_revision, style2)
                            ws.write(row_num, 47, det.revisado_por.username if det.revisado_por else '', style2)
                            ws.write(row_num, 48, str(det.fecha_revision) if det.fecha_revision else '', style2)
                            ws.write(row_num, 49, det.desempate_revisado_por.username if det.desempate_revisado_por else '', style2)
                            ws.write(row_num, 50, str(det.desempate_fecha_revision) if det.desempate_fecha_revision else '', style2)
                            row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    messages.error(request, str(ex))

            if action == 'excel_postulantes__all_mejores_puntuados':
                try:
                    response = HttpResponse(content_type='application/ms-excel')
                    response['Content-Disposition'] = 'attachment; filename="postulantes_all_mejores_puntuados.xls"'
                    title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf('font: name Calibri, color-index black, bold on , height 250; alignment: horiz centre')
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    fuentecabecera = easyxf('font: name Calibri, color-index black, bold on; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    wb = xlwt.Workbook(encoding='utf-8')
                    ws = wb.add_sheet('postulantes')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'LISTADO DE POSTULANTES MEJORES PUNTUADOS', title2)
                    row_num = 2
                    columns = [
                        ('Convocatoria', 10000),
                        ('Categoria', 10000),
                        ('Partida', 30000),
                        ('Carrera', 30000),
                        ('Asignaturas', 30000),
                        ('Dedicación', 10000),
                        ('RMU', 10000),
                        ('Nivel', 10000),
                        ('Modalidad', 10000),
                        ('Jornada', 10000),
                        ('Campo Amplio', 30000),
                        ('Campo Especifico', 30000),
                        ('Campo Detallado', 30000),
                        ('Cod. Unico', 10000),
                        ('Apellidos', 10000),
                        ('Nombres', 10000),
                        ('Titulo', 25000),
                        ('Archivo', 10000),
                        ('Identificación', 10000),
                        ('Correo', 10000),
                        ('Telf.', 10000),
                        ('Telf. Conv.', 10000),
                        ('Estado Calificación', 10000),
                        ('¿Tiene Formación?', 10000),
                        ('¿Tiene Experiencia?', 10000),
                        ('¿Tiene Capacitación?', 10000),
                        ('¿Tiene Publicaciones?', 10000),
                        ('¿Tiene Certificación Idiomas?', 10000),
                        ('Nota Formación', 10000),
                        ('Obs. Formación', 20000),
                        ('Nota Exp. Docente', 10000),
                        ('Obs. Exp. Docente', 20000),
                        ('Nota Exp. Administrativo', 10000),
                        ('Obs. Exp. Administrativo', 20000),
                        ('Nota Capacitación', 10000),
                        ('Obs. Capacitación', 20000),
                        ('¿Aplico Desempate?', 10000),
                        ('Nota Desempate', 10000),
                        ('Nota Final', 10000),
                        ('Obs. Final', 20000),
                        ('Estado', 10000),
                        ('¿Calificada?', 10000),
                        ('¿Apelo?', 10000),
                        ('Estado Apelación', 10000),
                        ('Obs. Apelación', 20000),
                        ('Usuario Revisión Meritos', 10000),
                        ('Fecha Revisión Meritos', 10000),
                        ('Usuario Revisión Apelación', 10000),
                        ('Fecha Revisión Apelación', 10000),
                        ('Usuario Revisión Desempate', 10000),
                        ('Fecha Revisión Desempate', 10000),
                    ]
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    convocatoria = Convocatoria.objects.get(status=True, pk=int(request.GET['id']))
                    for partidas in Partida.objects.filter(status=True, convocatoria=convocatoria).order_by('convocatoria__descripcion'):
                        listado = partidas.personaaplicarpartida_set.filter(status=True,esmejorpuntuado=True).order_by('-nota_final_meritos')
                        for det in listado:
                            if det.persona.mis_titulaciones().count() >0:
                                row_count = row_num+det.persona.mis_titulaciones().count()-1
                                titulos = det.persona.mis_titulaciones()
                                ws.write_merge(row_num,row_count, 0,0, det.partida.convocatoria.descripcion, style2)
                                ws.write_merge(row_num,row_count, 1,1, det.partida.convocatoria.tipocontrato.nombre if det.partida.convocatoria.tipocontrato else '', style2)
                                ws.write_merge(row_num,row_count, 2,2, str(det.partida), style2)
                                ws.write_merge(row_num,row_count, 3,3, det.partida.carrera.__str__() if det.partida.carrera else '', style2)
                                asignaturas_ = ''
                                for asig in det.partida.partidas_asignaturas():
                                    asignaturas_ += '{}, '.format(asig.__str__())
                                ws.write_merge(row_num,row_count, 4,4, asignaturas_, style2)
                                ws.write_merge(row_num,row_count, 5,5, det.partida.get_dedicacion_display(), style2)
                                ws.write_merge(row_num,row_count, 6,6, det.partida.rmu, style2)
                                ws.write_merge(row_num,row_count, 7,7, det.partida.get_nivel_display(), style2)
                                ws.write_merge(row_num,row_count, 8,8, det.partida.get_modalidad_display(), style2)
                                ws.write_merge(row_num,row_count, 9,9, det.partida.get_jornada_display(), style2)
                                campo_amplio = ''
                                for ca in det.partida.campoamplio.all():
                                    campo_amplio += '{}, '.format(ca.__str__())
                                ws.write_merge(row_num,row_count ,10,10, campo_amplio, style2)
                                campo_especifico = ''
                                for ca in det.partida.campoespecifico.all():
                                    campo_especifico += '{}, '.format(ca.__str__())
                                ws.write_merge(row_num,row_count, 11,11, campo_especifico, style2)
                                campo_detallado = ''
                                for ca in det.partida.campodetallado.all():
                                    campo_detallado += '{}, '.format(ca.__str__())
                                ws.write_merge(row_num,row_count, 12,12, campo_detallado, style2)
                                ws.write_merge(row_num,row_count, 13,13, det.pk, style2)
                                ws.write_merge(row_num,row_count, 14,14, "{} {}".format(det.persona.apellido1, det.persona.apellido2), style2)
                                ws.write_merge(row_num,row_count, 15,15, "{}".format(det.persona.nombres), style2)

                                ws.write_merge(row_num,row_count, 18,18, det.persona.cedula, style2)
                                ws.write_merge(row_num,row_count, 19,19, det.persona.email, style2)
                                ws.write_merge(row_num,row_count, 20,20, det.persona.telefono, style2)
                                ws.write_merge(row_num,row_count, 21,21, det.persona.telefono_conv, style2)
                                ws.write_merge(row_num,row_count, 22,22, det.get_estado_display(), style2)
                                ws.write_merge(row_num,row_count, 23,23, 'SI' if det.tiene_formacionacademica() else 'NO', style2)
                                ws.write_merge(row_num,row_count, 24,24, 'SI' if det.tiene_experienciapartida() else 'NO', style2)
                                ws.write_merge(row_num,row_count, 25,25, 'SI' if det.tiene_capacitaciones() else 'NO', style2)
                                ws.write_merge(row_num,row_count, 26,26, 'SI' if det.tiene_publicaciones() else 'NO', style2)
                                ws.write_merge(row_num,row_count, 27,27, 'SI' if det.tiene_idiomas() else 'NO', style2)
                                ws.write_merge(row_num,row_count, 28,28, det.pgradoacademico, style2)
                                ws.write_merge(row_num,row_count, 29,29, det.obsgradoacademico, style2)
                                ws.write_merge(row_num,row_count, 30,30, det.pexpdocente, style2)
                                ws.write_merge(row_num,row_count, 31,31, det.obsexperienciadoc, style2)
                                ws.write_merge(row_num,row_count, 32,32, det.pexpadministrativa, style2)
                                ws.write_merge(row_num,row_count, 33,33, det.obsexperienciaadmin, style2)
                                ws.write_merge(row_num,row_count, 34,34, det.pcapacitacion, style2)
                                ws.write_merge(row_num,row_count, 35,35, det.obscapacitacion, style2)
                                ws.write_merge(row_num,row_count, 36,36, 'SI' if det.aplico_desempate else 'NO', style2)
                                ws.write_merge(row_num,row_count, 37,37, det.nota_desempate, style2)
                                ws.write_merge(row_num,row_count, 38,38, det.nota_final_meritos, style2)
                                ws.write_merge(row_num,row_count, 39,39, det.obsgeneral, style2)
                                ws.write_merge(row_num,row_count, 40,40, det.get_estado_display(), style2)
                                ws.write_merge(row_num,row_count, 41,41, 'SI' if det.calificada else 'NO', style2)
                                ws.write_merge(row_num,row_count, 42,42, 'SI' if det.solapelacion else 'NO', style2)
                                ws.write_merge(row_num,row_count, 43,43, det.traer_apelacion().get_estado_display() if det.traer_apelacion() else '', style2)
                                obs_revisor, revisado_por, fecha_revision = '', '', ''
                                if det.traer_apelacion():
                                    if det.traer_apelacion().estado != 0:
                                        obs_revisor = det.traer_apelacion().observacion_revisor
                                        revisado_por = det.traer_apelacion().revisado_por.username if det.traer_apelacion().revisado_por else ''
                                        fecha_revision = str(det.traer_apelacion().fecha_revision)
                                ws.write_merge(row_num,row_count, 44,44, obs_revisor, style2)
                                ws.write_merge(row_num,row_count, 45,45, revisado_por, style2)
                                ws.write_merge(row_num,row_count, 46,46, fecha_revision, style2)
                                ws.write_merge(row_num,row_count, 47,47, det.revisado_por.username if det.revisado_por else '', style2)
                                ws.write_merge(row_num,row_count, 48,48, str(det.fecha_revision) if det.fecha_revision else '', style2)
                                ws.write_merge(row_num,row_count, 49,49, det.desempate_revisado_por.username if det.desempate_revisado_por else '', style2)
                                ws.write_merge(row_num,row_count, 50,50, str(det.desempate_fecha_revision) if det.desempate_fecha_revision else '', style2)
                                for dato in titulos:
                                    ws.write(row_num, 16, "{}".format(dato.titulo), style2)
                                    ws.write(row_num, 17, "https://sga.unemi.edu.ec/{}".format(dato.archivo.url) if dato.archivo else '', style2)
                                    row_num += 1
                            else:
                                ws.write(row_num, 0, det.partida.convocatoria.descripcion, style2)
                                ws.write(row_num, 1, det.partida.convocatoria.tipocontrato.nombre if det.partida.convocatoria.tipocontrato else '', style2)
                                ws.write(row_num, 2, str(det.partida), style2)
                                ws.write(row_num, 3, det.partida.carrera.__str__() if det.partida.carrera else '', style2)
                                asignaturas_ = ''
                                for asig in det.partida.partidas_asignaturas():
                                    asignaturas_ += '{}, '.format(asig.__str__())
                                ws.write(row_num, 4, asignaturas_, style2)
                                ws.write(row_num, 5, det.partida.get_dedicacion_display(), style2)
                                ws.write(row_num, 6, det.partida.rmu, style2)
                                ws.write(row_num, 7, det.partida.get_nivel_display(), style2)
                                ws.write(row_num, 8, det.partida.get_modalidad_display(), style2)
                                ws.write(row_num, 9, det.partida.get_jornada_display(), style2)
                                campo_amplio = ''
                                for ca in det.partida.campoamplio.all():
                                    campo_amplio += '{}, '.format(ca.__str__())
                                ws.write(row_num, 10, campo_amplio, style2)
                                campo_especifico = ''
                                for ca in det.partida.campoespecifico.all():
                                    campo_especifico += '{}, '.format(ca.__str__())
                                ws.write(row_num, 11, campo_especifico, style2)
                                campo_detallado = ''
                                for ca in det.partida.campodetallado.all():
                                    campo_detallado += '{}, '.format(ca.__str__())
                                ws.write(row_num, 12, campo_detallado, style2)
                                ws.write(row_num, 13, det.pk, style2)
                                ws.write(row_num, 14, "{} {}".format(det.persona.apellido1, det.persona.apellido2), style2)
                                ws.write(row_num, 15, "{}".format(det.persona.nombres), style2)
                                ws.write(row_num, 16, "", style2)
                                ws.write(row_num, 17, "", style2)
                                ws.write(row_num, 18, det.persona.cedula, style2)
                                ws.write(row_num, 19, det.persona.email, style2)
                                ws.write(row_num, 20, det.persona.telefono, style2)
                                ws.write(row_num, 21, det.persona.telefono_conv, style2)
                                ws.write(row_num, 22, det.get_estado_display(), style2)
                                ws.write(row_num, 23, 'SI' if det.tiene_formacionacademica() else 'NO', style2)
                                ws.write(row_num, 24, 'SI' if det.tiene_experienciapartida() else 'NO', style2)
                                ws.write(row_num, 25, 'SI' if det.tiene_capacitaciones() else 'NO', style2)
                                ws.write(row_num, 26, 'SI' if det.tiene_publicaciones() else 'NO', style2)
                                ws.write(row_num, 27, 'SI' if det.tiene_idiomas() else 'NO', style2)
                                ws.write(row_num, 28, det.pgradoacademico, style2)
                                ws.write(row_num, 29, det.obsgradoacademico, style2)
                                ws.write(row_num, 30, det.pexpdocente, style2)
                                ws.write(row_num, 31, det.obsexperienciadoc, style2)
                                ws.write(row_num, 32, det.pexpadministrativa, style2)
                                ws.write(row_num, 33, det.obsexperienciaadmin, style2)
                                ws.write(row_num, 34, det.pcapacitacion, style2)
                                ws.write(row_num, 35, det.obscapacitacion, style2)
                                ws.write(row_num, 36, 'SI' if det.aplico_desempate else 'NO', style2)
                                ws.write(row_num, 37, det.nota_desempate, style2)
                                ws.write(row_num, 38, det.nota_final_meritos, style2)
                                ws.write(row_num, 39, det.obsgeneral, style2)
                                ws.write(row_num, 40, det.get_estado_display(), style2)
                                ws.write(row_num, 41, 'SI' if det.calificada else 'NO', style2)
                                ws.write(row_num, 42, 'SI' if det.solapelacion else 'NO', style2)
                                ws.write(row_num, 43, det.traer_apelacion().get_estado_display() if det.traer_apelacion() else '', style2)
                                obs_revisor, revisado_por, fecha_revision = '', '', ''
                                if det.traer_apelacion():
                                    if det.traer_apelacion().estado != 0:
                                        obs_revisor = det.traer_apelacion().observacion_revisor
                                        revisado_por = det.traer_apelacion().revisado_por.username if det.traer_apelacion().revisado_por else ''
                                        fecha_revision = str(det.traer_apelacion().fecha_revision)
                                ws.write(row_num, 44, obs_revisor, style2)
                                ws.write(row_num, 45, revisado_por, style2)
                                ws.write(row_num, 46, fecha_revision, style2)
                                ws.write(row_num, 47, det.revisado_por.username if det.revisado_por else '', style2)
                                ws.write(row_num, 48, str(det.fecha_revision) if det.fecha_revision else '', style2)
                                ws.write(row_num, 49, det.desempate_revisado_por.username if det.desempate_revisado_por else '', style2)
                                ws.write(row_num, 50, str(det.desempate_fecha_revision) if det.desempate_fecha_revision else '', style2)
                                row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    messages.error(request, str(ex))

            if action == 'excel_postulantes__all_banco_habilitados':
                try:
                    response = HttpResponse(content_type='application/ms-excel')
                    response['Content-Disposition'] = 'attachment; filename="postulantes_banco_habilitantes.xls"'
                    title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf('font: name Calibri, color-index black, bold on , height 250; alignment: horiz centre')
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    fuentecabecera = easyxf('font: name Calibri, color-index black, bold on; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    wb = xlwt.Workbook(encoding='utf-8')
                    ws = wb.add_sheet('postulantes')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'LISTADO DE POSTULANTES BANCO HABILITANTES', title2)
                    row_num = 2
                    columns = [
                        ('Convocatoria', 10000),
                        ('Categoria', 10000),
                        ('Partida', 30000),
                        ('Carrera', 30000),
                        ('Asignaturas', 30000),
                        ('Dedicación', 10000),
                        ('RMU', 10000),
                        ('Nivel', 10000),
                        ('Modalidad', 10000),
                        ('Jornada', 10000),
                        ('Campo Amplio', 30000),
                        ('Campo Especifico', 30000),
                        ('Campo Detallado', 30000),
                        ('Cod. Unico', 10000),
                        ('Apellidos', 10000),
                        ('Nombres', 10000),
                        ('Titulo', 25000),
                        ('Archivo', 10000),
                        ('Identificación', 10000),
                        ('Correo', 10000),
                        ('Telf.', 10000),
                        ('Telf. Conv.', 10000),
                        ('Estado Calificación', 10000),
                        ('¿Tiene Formación?', 10000),
                        ('¿Tiene Experiencia?', 10000),
                        ('¿Tiene Capacitación?', 10000),
                        ('¿Tiene Publicaciones?', 10000),
                        ('¿Tiene Certificación Idiomas?', 10000),
                        ('Nota Formación', 10000),
                        ('Obs. Formación', 20000),
                        ('Nota Exp. Docente', 10000),
                        ('Obs. Exp. Docente', 20000),
                        ('Nota Exp. Administrativo', 10000),
                        ('Obs. Exp. Administrativo', 20000),
                        ('Nota Capacitación', 10000),
                        ('Obs. Capacitación', 20000),
                        ('¿Aplico Desempate?', 10000),
                        ('Nota Desempate', 10000),
                        ('Nota Final', 10000),
                        ('Obs. Final', 20000),
                        ('Estado', 10000),
                        ('¿Calificada?', 10000),
                        ('¿Apelo?', 10000),
                        ('Estado Apelación', 10000),
                        ('Obs. Apelación', 20000),
                        ('Usuario Revisión Meritos', 10000),
                        ('Fecha Revisión Meritos', 10000),
                        ('Usuario Revisión Apelación', 10000),
                        ('Fecha Revisión Apelación', 10000),
                        ('Usuario Revisión Desempate', 10000),
                        ('Fecha Revisión Desempate', 10000),
                    ]
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    convocatoria = Convocatoria.objects.get(status=True,pk=int(request.GET['id']))
                    for partidas in Partida.objects.filter(status=True, convocatoria=convocatoria).order_by('convocatoria__descripcion'):
                        listado = partidas.personaaplicarpartida_set.filter(status=True).order_by('-nota_final_meritos')[3:]
                        for det in listado:
                            if det.persona.mis_titulaciones().count() > 0:
                                row_count = row_num + det.persona.mis_titulaciones().count() - 1
                                titulos = det.persona.mis_titulaciones()
                                ws.write_merge(row_num, row_count, 0, 0, det.partida.convocatoria.descripcion, style2)
                                ws.write_merge(row_num, row_count, 1, 1, det.partida.convocatoria.tipocontrato.nombre if det.partida.convocatoria.tipocontrato else '', style2)
                                ws.write_merge(row_num, row_count, 2, 2, str(det.partida), style2)
                                ws.write_merge(row_num, row_count, 3, 3, det.partida.carrera.__str__() if det.partida.carrera else '', style2)
                                asignaturas_ = ''
                                for asig in det.partida.partidas_asignaturas():
                                    asignaturas_ += '{}, '.format(asig.__str__())
                                ws.write_merge(row_num, row_count, 4, 4, asignaturas_, style2)
                                ws.write_merge(row_num, row_count, 5, 5, det.partida.get_dedicacion_display(), style2)
                                ws.write_merge(row_num, row_count, 6, 6, det.partida.rmu, style2)
                                ws.write_merge(row_num, row_count, 7, 7, det.partida.get_nivel_display(), style2)
                                ws.write_merge(row_num, row_count, 8, 8, det.partida.get_modalidad_display(), style2)
                                ws.write_merge(row_num, row_count, 9, 9, det.partida.get_jornada_display(), style2)
                                campo_amplio = ''
                                for ca in det.partida.campoamplio.all():
                                    campo_amplio += '{}, '.format(ca.__str__())
                                ws.write_merge(row_num, row_count, 10, 10, campo_amplio, style2)
                                campo_especifico = ''
                                for ca in det.partida.campoespecifico.all():
                                    campo_especifico += '{}, '.format(ca.__str__())
                                ws.write_merge(row_num, row_count, 11, 11, campo_especifico, style2)
                                campo_detallado = ''
                                for ca in det.partida.campodetallado.all():
                                    campo_detallado += '{}, '.format(ca.__str__())
                                ws.write_merge(row_num, row_count, 12, 12, campo_detallado, style2)
                                ws.write_merge(row_num, row_count, 13, 13, det.pk, style2)
                                ws.write_merge(row_num, row_count, 14, 14, "{} {}".format(det.persona.apellido1, det.persona.apellido2), style2)
                                ws.write_merge(row_num, row_count, 15, 15, "{}".format(det.persona.nombres), style2)

                                ws.write_merge(row_num, row_count, 18, 18, det.persona.cedula, style2)
                                ws.write_merge(row_num, row_count, 19, 19, det.persona.email, style2)
                                ws.write_merge(row_num, row_count, 20, 20, det.persona.telefono, style2)
                                ws.write_merge(row_num, row_count, 21, 21, det.persona.telefono_conv, style2)
                                ws.write_merge(row_num, row_count, 22, 22, det.get_estado_display(), style2)
                                ws.write_merge(row_num, row_count, 23, 23, 'SI' if det.tiene_formacionacademica() else 'NO', style2)
                                ws.write_merge(row_num, row_count, 24, 24, 'SI' if det.tiene_experienciapartida() else 'NO', style2)
                                ws.write_merge(row_num, row_count, 25, 25, 'SI' if det.tiene_capacitaciones() else 'NO', style2)
                                ws.write_merge(row_num, row_count, 26, 26, 'SI' if det.tiene_publicaciones() else 'NO', style2)
                                ws.write_merge(row_num, row_count, 27, 27, 'SI' if det.tiene_idiomas() else 'NO', style2)
                                ws.write_merge(row_num, row_count, 28, 28, det.pgradoacademico, style2)
                                ws.write_merge(row_num, row_count, 29, 29, det.obsgradoacademico, style2)
                                ws.write_merge(row_num, row_count, 30, 30, det.pexpdocente, style2)
                                ws.write_merge(row_num, row_count, 31, 31, det.obsexperienciadoc, style2)
                                ws.write_merge(row_num, row_count, 32, 32, det.pexpadministrativa, style2)
                                ws.write_merge(row_num, row_count, 33, 33, det.obsexperienciaadmin, style2)
                                ws.write_merge(row_num, row_count, 34, 34, det.pcapacitacion, style2)
                                ws.write_merge(row_num, row_count, 35, 35, det.obscapacitacion, style2)
                                ws.write_merge(row_num, row_count, 36, 36, 'SI' if det.aplico_desempate else 'NO', style2)
                                ws.write_merge(row_num, row_count, 37, 37, det.nota_desempate, style2)
                                ws.write_merge(row_num, row_count, 38, 38, det.nota_final_meritos, style2)
                                ws.write_merge(row_num, row_count, 39, 39, det.obsgeneral, style2)
                                ws.write_merge(row_num, row_count, 40, 40, det.get_estado_display(), style2)
                                ws.write_merge(row_num, row_count, 41, 41, 'SI' if det.calificada else 'NO', style2)
                                ws.write_merge(row_num, row_count, 42, 42, 'SI' if det.solapelacion else 'NO', style2)
                                ws.write_merge(row_num, row_count, 43, 43, det.traer_apelacion().get_estado_display() if det.traer_apelacion() else '', style2)
                                obs_revisor, revisado_por, fecha_revision = '', '', ''
                                if det.traer_apelacion():
                                    if det.traer_apelacion().estado != 0:
                                        obs_revisor = det.traer_apelacion().observacion_revisor
                                        revisado_por = det.traer_apelacion().revisado_por.username if det.traer_apelacion().revisado_por else ''
                                        fecha_revision = str(det.traer_apelacion().fecha_revision)
                                ws.write_merge(row_num, row_count, 44, 44, obs_revisor, style2)
                                ws.write_merge(row_num, row_count, 45, 45, revisado_por, style2)
                                ws.write_merge(row_num, row_count, 46, 46, fecha_revision, style2)
                                ws.write_merge(row_num, row_count, 47, 47, det.revisado_por.username if det.revisado_por else '', style2)
                                ws.write_merge(row_num, row_count, 48, 48, str(det.fecha_revision) if det.fecha_revision else '', style2)
                                ws.write_merge(row_num, row_count, 49, 49, det.desempate_revisado_por.username if det.desempate_revisado_por else '', style2)
                                ws.write_merge(row_num, row_count, 50, 50, str(det.desempate_fecha_revision) if det.desempate_fecha_revision else '', style2)
                                for dato in titulos:
                                    ws.write(row_num, 16, "{}".format(dato.titulo), style2)
                                    ws.write(row_num, 17, "https://sga.unemi.edu.ec/{}".format(dato.archivo.url) if dato.archivo else '', style2)
                                    row_num += 1
                            else:
                                ws.write(row_num, 0, det.partida.convocatoria.descripcion, style2)
                                ws.write(row_num, 1, det.partida.convocatoria.tipocontrato.nombre if det.partida.convocatoria.tipocontrato else '', style2)
                                ws.write(row_num, 2, str(det.partida), style2)
                                ws.write(row_num, 3, det.partida.carrera.__str__() if det.partida.carrera else '', style2)
                                asignaturas_ = ''
                                for asig in det.partida.partidas_asignaturas():
                                    asignaturas_ += '{}, '.format(asig.__str__())
                                ws.write(row_num, 4, asignaturas_, style2)
                                ws.write(row_num, 5, det.partida.get_dedicacion_display(), style2)
                                ws.write(row_num, 6, det.partida.rmu, style2)
                                ws.write(row_num, 7, det.partida.get_nivel_display(), style2)
                                ws.write(row_num, 8, det.partida.get_modalidad_display(), style2)
                                ws.write(row_num, 9, det.partida.get_jornada_display(), style2)
                                campo_amplio = ''
                                for ca in det.partida.campoamplio.all():
                                    campo_amplio += '{}, '.format(ca.__str__())
                                ws.write(row_num, 10, campo_amplio, style2)
                                campo_especifico = ''
                                for ca in det.partida.campoespecifico.all():
                                    campo_especifico += '{}, '.format(ca.__str__())
                                ws.write(row_num, 11, campo_especifico, style2)
                                campo_detallado = ''
                                for ca in det.partida.campodetallado.all():
                                    campo_detallado += '{}, '.format(ca.__str__())
                                ws.write(row_num, 12, campo_detallado, style2)
                                ws.write(row_num, 13, det.pk, style2)
                                ws.write(row_num, 14, "{} {}".format(det.persona.apellido1, det.persona.apellido2), style2)
                                ws.write(row_num, 15, "{}".format(det.persona.nombres), style2)
                                ws.write(row_num, 16, "", style2)
                                ws.write(row_num, 17, "", style2)
                                ws.write(row_num, 18, det.persona.cedula, style2)
                                ws.write(row_num, 19, det.persona.email, style2)
                                ws.write(row_num, 20, det.persona.telefono, style2)
                                ws.write(row_num, 21, det.persona.telefono_conv, style2)
                                ws.write(row_num, 22, det.get_estado_display(), style2)
                                ws.write(row_num, 23, 'SI' if det.tiene_formacionacademica() else 'NO', style2)
                                ws.write(row_num, 24, 'SI' if det.tiene_experienciapartida() else 'NO', style2)
                                ws.write(row_num, 25, 'SI' if det.tiene_capacitaciones() else 'NO', style2)
                                ws.write(row_num, 26, 'SI' if det.tiene_publicaciones() else 'NO', style2)
                                ws.write(row_num, 27, 'SI' if det.tiene_idiomas() else 'NO', style2)
                                ws.write(row_num, 28, det.pgradoacademico, style2)
                                ws.write(row_num, 29, det.obsgradoacademico, style2)
                                ws.write(row_num, 30, det.pexpdocente, style2)
                                ws.write(row_num, 31, det.obsexperienciadoc, style2)
                                ws.write(row_num, 32, det.pexpadministrativa, style2)
                                ws.write(row_num, 33, det.obsexperienciaadmin, style2)
                                ws.write(row_num, 34, det.pcapacitacion, style2)
                                ws.write(row_num, 35, det.obscapacitacion, style2)
                                ws.write(row_num, 36, 'SI' if det.aplico_desempate else 'NO', style2)
                                ws.write(row_num, 37, det.nota_desempate, style2)
                                ws.write(row_num, 38, det.nota_final_meritos, style2)
                                ws.write(row_num, 39, det.obsgeneral, style2)
                                ws.write(row_num, 40, det.get_estado_display(), style2)
                                ws.write(row_num, 41, 'SI' if det.calificada else 'NO', style2)
                                ws.write(row_num, 42, 'SI' if det.solapelacion else 'NO', style2)
                                ws.write(row_num, 43, det.traer_apelacion().get_estado_display() if det.traer_apelacion() else '', style2)
                                obs_revisor, revisado_por, fecha_revision = '', '', ''
                                if det.traer_apelacion():
                                    if det.traer_apelacion().estado != 0:
                                        obs_revisor = det.traer_apelacion().observacion_revisor
                                        revisado_por = det.traer_apelacion().revisado_por.username if det.traer_apelacion().revisado_por else ''
                                        fecha_revision = str(det.traer_apelacion().fecha_revision)
                                ws.write(row_num, 44, obs_revisor, style2)
                                ws.write(row_num, 45, revisado_por, style2)
                                ws.write(row_num, 46, fecha_revision, style2)
                                ws.write(row_num, 47, det.revisado_por.username if det.revisado_por else '', style2)
                                ws.write(row_num, 48, str(det.fecha_revision) if det.fecha_revision else '', style2)
                                ws.write(row_num, 49, det.desempate_revisado_por.username if det.desempate_revisado_por else '', style2)
                                ws.write(row_num, 50, str(det.desempate_fecha_revision) if det.desempate_fecha_revision else '', style2)
                                row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    msg_ex = 'Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, str(ex))
                    return JsonResponse({"result": False, 'data': str(msg_ex)})

            if action == 'excel_horarios':
                try:
                    response = HttpResponse(content_type='application/ms-excel')
                    response['Content-Disposition'] = 'attachment; filename="postulantes_horarios.xls"'
                    title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf('font: name Calibri, color-index black, bold on , height 250; alignment: horiz centre')
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    fuentecabecera = easyxf('font: name Calibri, color-index black, bold on; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    wb = xlwt.Workbook(encoding='utf-8')
                    ws = wb.add_sheet('postulantes')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'POSTULANTES Y HORARIOS', title2)
                    row_num = 2
                    columns = [
                        ('Convocatoria', 10000),
                        ('Categoria', 10000),
                        ('Partida', 10000),
                        ('Carrera', 20000),
                        ('Asignaturas', 30000),
                        ('Apellidos', 10000),
                        ('Nombres', 10000),
                        ('Identificación', 10000),
                        ('Correo', 10000),
                        ('Telf.', 10000),
                        ('Telf. Conv.', 10000),
                        ('Horario', 10000),

                    ]
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    convocatoria = Convocatoria.objects.get(status=True,pk=int(request.GET['id']))
                    for partidas in Partida.objects.filter(status=True, convocatoria=convocatoria).order_by('convocatoria__descripcion'):
                        listado = partidas.personaaplicarpartida_set.filter(status=True,estado=1)
                        for det in listado:
                                ws.write(row_num, 0, det.partida.convocatoria.descripcion, style2)
                                ws.write(row_num, 1, det.partida.convocatoria.tipocontrato.nombre if det.partida.convocatoria.tipocontrato else '', style2)
                                ws.write(row_num, 2, str(det.partida), style2)
                                ws.write(row_num, 3, det.partida.carrera.__str__() if det.partida.carrera else '', style2)
                                asignaturas_ = ''
                                for asig in det.partida.partidas_asignaturas():
                                    asignaturas_ += '{}, '.format(asig.__str__())
                                ws.write(row_num, 4, asignaturas_, style2)
                                ws.write(row_num, 5, "{} {}".format(det.persona.apellido1, det.persona.apellido2), style2)
                                ws.write(row_num, 6, "{}".format(det.persona.nombres), style2)
                                ws.write(row_num, 7, det.persona.cedula, style2)
                                ws.write(row_num, 8, det.persona.email, style2)
                                ws.write(row_num, 9, det.persona.telefono, style2)
                                ws.write(row_num, 10, det.persona.telefono_conv, style2)
                                tipohorarios = TipoTurnoConvocatoria.objects.filter(id__in=det.mis_horarios().values("horario__tipo_id")).order_by('id')
                                conth=11
                                mishorarios= det.mis_horarios()
                                for tipoh in tipohorarios:
                                    _horario = ''
                                    for horario in mishorarios.filter(horario__tipo=tipoh):
                                        _horario += '{}[{}-{}], '.format(horario.horario.fecha.__str__(),horario.horario.turno.comienza.__str__(),horario.horario.turno.termina.__str__())
                                    ws.write(row_num, conth, _horario, style2)
                                    conth+=1
                                row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    msg_ex = 'Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, str(ex))
                    return JsonResponse({"result": False, 'data': str(msg_ex)})

            if action == 'vercalificar':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(pk=id)
                    data['partida'] = partida = Partida.objects.get(pk=postulante.partida.pk)
                    data['resp_campos'] = validar_campos(request, persona, partida)
                    data['persona'] = postulante.persona
                    data['posidiomas'] = posidiomas = PersonaIdiomaPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['postitulacion'] = postitulacion = PersonaFormacionAcademicoPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['posexperiencia'] = posexperiencia = PersonaExperienciaPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['poscapacitacion'] = poscapacitacion = PersonaCapacitacionesPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['pospublicacion'] = pospublicacion = PersonaPublicacionesPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    template = get_template("postulate/mispostulaciones/vercalificacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'reportdesiertos':
                try:
                    sin_pos = Partida.objects.values_list('id', flat=True).filter(status=True,vigente=True,personaaplicarpartida__isnull=True)
                    pos_menor = PersonaAplicarPartida.objects.values_list('partida_id', flat=True).filter(status=True, nota_final__lt=70).distinct('partida_id')
                    re = sin_pos.union(pos_menor)
                    re = list(re)
                    listado = Partida.objects.filter(status=True, vigente=True, id__in=re).distinct('id')

                    __autor__ = 'unemi'
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('partidas')

                    ws.set_row(0,20)
                    title = workbook.add_format({'font_name':'Calibri','align':'center','bold':True,'font_size':18,'valign':'vcenter'})
                    title2 = workbook.add_format({'font_name':'Calibri','align':'center','bold':True,'font_size':14,'valign':'vcenter'})
                    fuentecabecera = workbook.add_format({'font_name':'Calibri','border':1,'align':'center','font_size':11,'valign':'vcenter','bg_color':'#E4E5DF'})
                    style2 = workbook.add_format({'text_wrap':True,'font_name': 'Calibri', 'border': 1, 'align': 'center', 'font_size': 11, 'valign': 'vcenter'})
                    ws.merge_range(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', title)
                    ws.merge_range(1, 1, 0, 8, '', title2)
                    row_num = 2
                    columns = [
                        ('Cod. Partida', 15),
                        ('Denominacion puesto', 120),
                        # ('Descripción', 120),
                        ('Carrera', 80),
                        ('Campo Amplio', 120),
                        ('Campo Especifico', 100),
                        ('Campo Detallado', 120),
                        ('Títulos Relacionados', 120),
                        ('Nivel', 35),
                        ('Modalidad', 30),
                        ('Dedicación', 40),
                        ('Jornada', 23),
                        ('RMU', 10),
                        ('Vigente', 10),
                        ('Total Postulantes', 10), ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.set_column(col_num,col_num,columns[col_num][1])
                    row_num += 1
                    for det in listado:
                        if det.participantes_mejores_puntuados():
                            pass
                        else:
                            ws.write(row_num, 0, det.codpartida, style2)
                            ws.write(row_num, 1, str(det.denominacionpuesto), style2)
                            # ws.write(row_num, 2, det.descripcion, style2)
                            ws.write(row_num, 2, det.carrera.__str__() if det.carrera else '', style2)
                            campo_amplio = ''
                            for ca in det.campoamplio.all():
                                campo_amplio += '{}, '.format(ca.__str__())
                            ws.write(row_num, 3, campo_amplio, style2)
                            campo_especifico = ''
                            for ca in det.campoespecifico.all():
                                campo_especifico += '{}, '.format(ca.__str__())
                            ws.write(row_num, 4, campo_especifico, style2)
                            campo_detallado = ''
                            for ca in det.campodetallado.all():
                                campo_detallado += '{}, '.format(ca.__str__())
                            ws.write(row_num, 5, campo_detallado, style2)
                            titulos_relacionados = ''
                            for ca in det.titulos.all():
                                titulos_relacionados += '{}, '.format(ca.__str__())
                            ws.write(row_num, 6, titulos_relacionados, style2)
                            ws.write(row_num, 7, det.get_nivel_display(), style2)
                            ws.write(row_num, 8, det.get_modalidad_display(), style2)
                            ws.write(row_num, 9, det.get_dedicacion_display(), style2)
                            ws.write(row_num, 10, det.get_jornada_display(), style2)
                            ws.write(row_num, 11, det.rmu, style2)
                            ws.write(row_num, 12, 'SI' if det.vigente else 'NO', style2)
                            ws.write(row_num, 13, det.total_postulantes(), style2)
                            row_num += 1
                    workbook.close()
                    output.seek(0)
                    filename = 'reporte_desiertos' + random.randint(1, 10000).__str__() + '.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            if action == 'reporttribunal':
                try:
                    partidas = Partida.objects.filter(status=True,convocatoria__vigente=True)
                    # tribunal = partidas.partidatribunal_set.filter(tipo =1)
                    etapa = int(request.GET['etapa'])

                    __autor__ = 'unemi'
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('partidas_tribunal')
                    ws.set_column(0,1,150)
                    ws.set_row(0,20)

                    title = workbook.add_format({'font_name': 'Calibri', 'align': 'center', 'bold': True, 'font_size': 18, 'valign': 'vcenter'})
                    title2 = workbook.add_format({'font_name': 'Calibri', 'align': 'center', 'bold': True, 'font_size': 14, 'valign': 'vcenter'})
                    fuentecabecera = workbook.add_format({'font_name': 'Calibri', 'border': 1, 'align': 'center', 'font_size': 11, 'valign': 'vcenter', 'bg_color': '#E4E5DF'})
                    style2 = workbook.add_format({'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'align': 'center', 'font_size': 11, 'valign': 'vcenter'})
                    ws.merge_range(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', title)
                    ws.merge_range(1, 1, 0, 8, '', title2)
                    row_num =3
                    columns = [
                        ('Convocatoria', 80),
                        ('Cod. Partida', 15),
                        ('Denominacion puesto', 90),
                    ]
                    for cargo in CARGOS_TRIBUNAL:
                        columns.append((cargo[1],70))
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.set_column(col_num,col_num,columns[col_num][1])
                    ws.merge_range(row_num-1,3,row_num-1,3+len(CARGOS_TRIBUNAL)-1,'CARGOS TRIBUNAL',fuentecabecera)
                    row_num+=1
                    for par in partidas:
                        ws.write(row_num,0,par.convocatoria.__str__(),style2)
                        ws.write(row_num,1,par.codpartida,style2)
                        ws.write(row_num,2,str(par.denominacionpuesto),style2)
                        aux = 2
                        for l in par.cargos_tribunal(etapa):
                            ws.write(row_num,aux+int(CARGOS_TRIBUNAL[l.cargos-1][0]),l.persona.__str__() if l.persona else ' ',style2)
                        row_num+=1

                    workbook.close()
                    output.seek(0)
                    filename = 'reporte_tribunal_partidas_' + random.randint(1, 10000).__str__() + '.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            if action == 'reportdesiertos':
                try:
                    sin_pos = Partida.objects.values_list('id', flat=True).filter(status=True,vigente=True,personaaplicarpartida__isnull=True)
                    pos_menor = PersonaAplicarPartida.objects.values_list('partida_id', flat=True).filter(status=True, nota_final__lt=70).distinct('partida_id')
                    re = sin_pos.union(pos_menor)
                    re = list(re)
                    listado = Partida.objects.filter(status=True, vigente=True, id__in=re).distinct('id')

                    __autor__ = 'unemi'
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('partidas')

                    ws.set_row(0,20)
                    title = workbook.add_format({'font_name':'Calibri','align':'center','bold':True,'font_size':18,'valign':'vcenter'})
                    title2 = workbook.add_format({'font_name':'Calibri','align':'center','bold':True,'font_size':14,'valign':'vcenter'})
                    fuentecabecera = workbook.add_format({'font_name':'Calibri','border':1,'align':'center','font_size':11,'valign':'vcenter','bg_color':'#E4E5DF'})
                    style2 = workbook.add_format({'text_wrap':True,'font_name': 'Calibri', 'border': 1, 'align': 'center', 'font_size': 11, 'valign': 'vcenter'})
                    ws.merge_range(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', title)
                    ws.merge_range(1, 1, 0, 8, '', title2)
                    row_num = 2
                    columns = [
                        ('Cod. Partida', 15),
                        ('Denominacion puesto', 120),
                        # ('Descripción', 120),
                        ('Carrera', 80),
                        ('Campo Amplio', 120),
                        ('Campo Especifico', 100),
                        ('Campo Detallado', 120),
                        ('Títulos Relacionados', 120),
                        ('Nivel', 35),
                        ('Modalidad', 30),
                        ('Dedicación', 40),
                        ('Jornada', 23),
                        ('RMU', 10),
                        ('Vigente', 10),
                        ('Total Postulantes', 10), ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.set_column(col_num,col_num,columns[col_num][1])
                    row_num += 1
                    for det in listado:
                        if det.participantes_mejores_puntuados():
                            pass
                        else:
                            ws.write(row_num, 0, det.codpartida, style2)
                            ws.write(row_num, 1, str(det.denominacionpuesto), style2)
                            # ws.write(row_num, 2, det.descripcion, style2)
                            ws.write(row_num, 2, det.carrera.__str__() if det.carrera else '', style2)
                            campo_amplio = ''
                            for ca in det.campoamplio.all():
                                campo_amplio += '{}, '.format(ca.__str__())
                            ws.write(row_num, 3, campo_amplio, style2)
                            campo_especifico = ''
                            for ca in det.campoespecifico.all():
                                campo_especifico += '{}, '.format(ca.__str__())
                            ws.write(row_num, 4, campo_especifico, style2)
                            campo_detallado = ''
                            for ca in det.campodetallado.all():
                                campo_detallado += '{}, '.format(ca.__str__())
                            ws.write(row_num, 5, campo_detallado, style2)
                            titulos_relacionados = ''
                            for ca in det.titulos.all():
                                titulos_relacionados += '{}, '.format(ca.__str__())
                            ws.write(row_num, 6, titulos_relacionados, style2)
                            ws.write(row_num, 7, det.get_nivel_display(), style2)
                            ws.write(row_num, 8, det.get_modalidad_display(), style2)
                            ws.write(row_num, 9, det.get_dedicacion_display(), style2)
                            ws.write(row_num, 10, det.get_jornada_display(), style2)
                            ws.write(row_num, 11, det.rmu, style2)
                            ws.write(row_num, 12, 'SI' if det.vigente else 'NO', style2)
                            ws.write(row_num, 13, det.total_postulantes(), style2)
                            row_num += 1
                    workbook.close()
                    output.seek(0)
                    filename = 'reporte_desiertos' + random.randint(1, 10000).__str__() + '.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            if action == 'verdetallepostulante':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['partida'] = partida = Partida.objects.get(pk=id, status=True)
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(partida = partida, esganador=True,finsegundaetapa=True)
                    data['resp_campos'] = validar_campos(request, persona, partida)
                    data['persona'] = postulante.persona
                    data['posidiomas'] = PersonaIdiomaPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['postitulacion'] = PersonaFormacionAcademicoPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['posexperiencia'] = PersonaExperienciaPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['poscapacitacion'] = PersonaCapacitacionesPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['pospublicacion'] = PersonaPublicacionesPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    template = get_template("postulate/adm_revisionpostulacion/verdetallepostulante.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'duplicarconvocatoria':
                try:
                    if 'id' in request.GET:
                        id = int(encrypt(request.GET['id']))
                    if Convocatoria.objects.values('id').filter(pk=id,status=True):
                        convocatoria = Convocatoria.objects.get(pk =id, status=True)
                        conv = Convocatoria(descripcion='Copia - {}'.format(convocatoria.descripcion),
                                                finicio=convocatoria.finicio,
                                                ffin=convocatoria.ffin,
                                                tipocontrato=convocatoria.tipocontrato,
                                                denominacionpuesto=convocatoria.denominacionpuesto,
                                                modeloevaluativo = convocatoria.modeloevaluativo,
                                                vigente=convocatoria.vigente)
                        conv.valtercernivel = convocatoria.valtercernivel
                        conv.valposgrado = convocatoria.valposgrado
                        conv.valdoctorado = convocatoria.valdoctorado
                        conv.valcapacitacionmin = convocatoria.valcapacitacionmin
                        conv.valcapacitacionmax = convocatoria.valcapacitacionmax
                        conv.valexpdocentemin = convocatoria.valexpdocentemin
                        conv.valexpdocentemax = convocatoria.valexpdocentemax
                        conv.valexpadminmin = convocatoria.valexpadminmin
                        conv.valexpadminmax = convocatoria.valexpadminmax
                        conv.save(request)
                        for condi in convocatoria.convocatoriaterminoscondiciones_set.filter(status=True):
                            termino = ConvocatoriaTerminosCondiciones(
                                convocatoria = conv,
                                descripcion = condi.descripcion
                            )
                            termino.save(request)
                        log('Ha duplicado la convocatoria {}, con terminos y condiciones'.format(conv.__str__()),request,'change')
                        return JsonResponse({"result": True, 'msg': 'Convocatoria Duplicada!'})
                    else:
                        return JsonResponse({"result":False,'msg':'No existe la convocatoria'})
                except Exception as ex:
                    pass

            if action == 'duplicarpartida':
                try:
                    if 'id' in request.GET:
                        id = int(encrypt(request.GET['id']))
                    if 'idc' in request.GET:
                        idc = int(encrypt(request.GET['idc']))
                    if Partida.objects.values('id').filter(pk=id, status=True, convocatoria_id=idc):
                        partida = Partida.objects.get(pk=id, status=True, convocatoria_id=idc)
                        partidaasignaturas = PartidaAsignaturas.objects.filter(partida=partida, status=True).values_list('asignatura_id')
                        part = Partida(
                                        convocatoria_id = idc,
                                        codpartida=partida.codpartida,
                                        denominacionpuesto=partida.denominacionpuesto,
                                        # titulo = partida.titulo,
                                        # descripcion='Copia - {}'.format(partida.descripcion),
                                        carrera=partida.carrera,
                                        nivel=partida.nivel,
                                        modalidad=partida.modalidad,
                                        dedicacion=partida.dedicacion,
                                        jornada=partida.jornada,
                                        rmu=partida.rmu,
                                        vigente=partida.vigente)
                        part.save()
                        for ca in partida.campoamplio.all():
                            part.campoamplio.add(ca)
                        for caesp in partida.campoespecifico.all():
                            part.campoespecifico.add(caesp)
                        for cadet in partida.campodetallado.all():
                            part.campodetallado.add(cadet)
                        for tit in partida.titulos.all():
                            part.titulos.add(tit)
                        part.save(request)
                        for asignatura in partidaasignaturas:
                            partasignatura = PartidaAsignaturas(partida=part, asignatura_id=asignatura[0])
                            partasignatura.save(request)
                        log('Ha duplicado la partida {}, con asignaturas'.format(part.__str__()),
                            request, 'change')
                        return JsonResponse({"result": True, 'msg': 'Partida Duplicada!'})
                    else:
                        return JsonResponse({"result": False, 'msg': 'No existe la partida'})
                except Exception as ex:
                    pass

            elif action == 'requisitos':
                try:
                    data['title'] = u'Requisitos para contratos'
                    search, url_vars, filtro = request.GET.get('s', ''), '',Q(status=True)
                    requisito = RequisitoDocumentoContrato.objects.filter(status=True)
                    if search:
                        data['search'] = search
                        url_vars += "&s={}".format(search)
                        filtro = filtro & (Q(descripcion__icontains=search)|Q(nombre__icontains=search))
                        requisito = requisito.filter(filtro).order_by('nombre','descripcion')
                    paging = MiPaginador(requisito, 20)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['list_count'] = len(requisito)
                    return render(request, "postulate/adm_postulate/viewrequisito.html", data)
                except Exception as ex:
                    pass

            elif action == 'addrequisito':
                try:
                    data['title'] = u'Adiccionar Requisito'
                    form = RequisitoDocumentoContratoForm()
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formrequisito.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            elif action == 'editrequisito':
                try:
                    data['title'] = u'Editar Requisito'
                    data['requisito'] = filtro = RequisitoDocumentoContrato.objects.get(id = int(encrypt(request.GET['id'])))
                    form = RequisitoDocumentoContratoForm(initial = {
                        'nombre':filtro.nombre,
                        'descripcion':filtro.descripcion,
                        'anio':filtro.anio,
                        'tipo':filtro.tipo,
                        'obligatorio':filtro.obligatorio,
                        'activo':filtro.activo,
                        'archivo':filtro.archivo
                    })
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formrequisito.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            elif action == "ganadores":
                try:
                    data['title'] = 'Ganadores'
                    data['personaaplica'] = personaaplica = PersonaAplicarPartida.objects.filter(status=True,esganador=True)
                    search, url_vars, filtro = request.GET.get('s', ''), '', Q(status=True)
                    if search:
                        data['search'] = search
                        s = search.split(' ')
                        url_vars += "&s={}".format(search)
                        if len(s)>1:
                            filtro = filtro & (Q(persona__apellido1__icontains=s[0]) | Q(persona__apellido2__icontains=s[1]))
                        else:
                            filtro = filtro & (Q(persona__cedula__icontains=s[0]))
                        personaaplica = personaaplica.filter(filtro).order_by('id')
                    paging = MiPaginador(personaaplica, 20)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    return render(request, "postulate/adm_postulate/viewganadores.html", data)
                except Exception as ex:
                    pass

            if action == 'listarparticipantespartida':
                try:
                    idpartida = Partida.objects.get(id=int(encrypt(request.GET['id'])))
                    data ['listado'] =  PersonaAplicarPartida.objects.filter(status=True, partida_id= idpartida)
                    template = get_template('postulate/adm_postulate/modal/listarparticipantes.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'viewimportarparticipantes':
                try:
                    data ['partidaimp'] = Partida.objects.get(id=request.GET['id'])
                    #form.fields['partida'].queryset = Partida.objects.filter(convocatoria_id= request.GET['pk'], status=True).exclude(id=request.GET['id']).order_by('-id')
                    data['partidas'] = Partida.objects.filter(convocatoria_id= request.GET['pk'], status=True).exclude(id=request.GET['id']).order_by('-id')
                    template = get_template('postulate/adm_postulate/modal/viewimportarparticipantes.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'buscarpostulantes':
                try:
                    data['partidaimp'] = Partida.objects.filter(id=request.GET['partidaimp'])
                    data['postulantes'] = PersonaAplicarPartida.objects.filter(partida=request.GET['partida'], status=True).order_by('id')
                    template = get_template('postulate/adm_postulate/modal/viewimportarparticipantes.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'importarparticipante':
                try:
                    data['form'] = ImportarPostulantesForm()
                    data['id'] = request.GET['id']
                    data['partidaimp'] = Partida.objects.get(id=request.GET['partidaimp'])
                    template = get_template('postulate/adm_postulate/modal/importarparticipantes.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'horarios':
                try:
                    id=int(encrypt(request.GET['id']))
                    data['convocatoria'] = convocatoria = Convocatoria.objects.get(id=int(encrypt(request.GET['id'])))
                    data['title'] = u'Horarios de %s' % (convocatoria.descripcion.lower())
                    data['semana'] = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
                    data['turnos'] = TurnoConvocatoria.objects.filter(status=True).order_by('comienza')
                    return render(request, "postulate/adm_postulate/viewhorario.html", data)
                except Exception as ex:
                    pass

            elif action == 'addhorario':
                try:
                    data['title'] = u'Adicionar horario'
                    convocatoria = Convocatoria.objects.get(id=int(encrypt(request.GET['convocatoria'])))
                    form = HorarioConvocatoriaForm(initial={
                        'turno': TurnoConvocatoria.objects.get(pk=request.GET['turno']),
                    })
                    data['convocatoria'] = request.GET['convocatoria']
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formhorario.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edithorario':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = HorarioConvocatoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['convocatoria'] = filtro.convocatoria
                    form = HorarioConvocatoriaForm(initial={'turno': filtro.turno,
                                                                 'fecha': filtro.fecha,
                                                                 'tipo': filtro.tipo,
                                                                 'lugar': filtro.lugar,
                                                                 'detalle': filtro.detalle,
                                                                 'mostrar': filtro.mostrar,
                                                                 'cupo': filtro.cupo,
                                                                      })
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formhorario.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'configrequisitosperiodo':
                try:
                    form = RequisitoCompetenciaPeriodoForm()
                    data['filtro'] = periodo_p = PeriodoAcademicoConvocatoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['listado'] = periodo_p.configuracion_tipocompetencias()
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formconfigrequisitosperiodo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'nummejorespuntuados':
                try:
                    data['convocatoria'] = convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    initial = model_to_dict(convocatoria)
                    data['form'] =  NumMejoresPuntuados(initial=initial)
                    template = get_template("postulate/adm_postulate/modal/formconvocatoria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'turnos':
                try:
                    data['title'] = 'Turnos'
                    search, filtros, url_vars = request.GET.get('s', ''), Q(status=True), f'&action={action}'
                    if search:
                        data['search'] = search
                        s = search.split()
                        if len(s) == 1:
                            filtros = filtros & (Q(comienza__icontains=search) |
                                                 Q(termina__icontains=search))
                        else:
                            filtros = filtros & (Q(comienza__icontains=s[0]) &
                                                 Q(termina__icontains=s[1]))
                        url_vars += '&search={}'.format(search)
                    turnos = TurnoConvocatoria.objects.filter(filtros).order_by('comienza')
                    paging = MiPaginador(turnos, 20)
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
                    data['url_vars']=url_vars
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['listado'] = page.object_list
                    request.session['viewactivo'] = 2
                    return render(request, 'postulate/adm_postulate/viewturno.html', data)
                except Exception as ex:
                    pass

            elif action == 'tipoturno':
                try:
                    data['title'] = 'Tipo de turnos'
                    search, filtros, url_vars = request.GET.get('s', ''), Q(status=True), f'&action={action}'
                    if search:
                        data['search'] = search
                        s = search.split()
                        if len(s) == 1:
                            filtros = filtros & (Q(nombre__icontains=search))
                        else:
                            filtros = filtros & (Q(nombre__icontains=s[0]) &
                                                 Q(nombre__icontains=s[1]))
                        url_vars += '&search={}'.format(search)
                    turnos = TipoTurnoConvocatoria.objects.filter(filtros).order_by('nombre')
                    paging = MiPaginador(turnos, 20)
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
                    data['url_vars']=url_vars
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['listado'] = page.object_list
                    request.session['viewactivo'] = 1
                    return render(request, 'postulate/adm_postulate/viewtipoturno.html', data)
                except Exception as ex:
                    pass

            elif action == 'modeloevaluativo':
                try:
                    data['title'] = 'Modelo evaluativo'
                    search, filtros, url_vars = request.GET.get('s', ''), Q(status=True), f'&action={action}'
                    if search:
                        data['search'] = search
                        s = search.split()
                        if len(s) == 1:
                            filtros = filtros & (Q(nombre__icontains=search))
                        else:
                            filtros = filtros & (Q(nombre__icontains=s[0]) &
                                                 Q(nombre__icontains=s[1]))
                        url_vars += '&search={}'.format(search)
                    turnos = ModeloEvaluativoConvocatoria.objects.filter(filtros).order_by('nombre')
                    paging = MiPaginador(turnos, 20)
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
                    data['url_vars']=url_vars
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['listado'] = page.object_list
                    request.session['viewactivo'] = 3
                    return render(request, 'postulate/adm_postulate/viewmodeloevaluativo.html', data)
                except Exception as ex:
                    pass

            elif action == 'modeloevaluativodetalle':
                try:
                    data['title'] = 'Detalle de modelo evaluativo'
                    search, filtros, url_vars = request.GET.get('s', ''), Q(status=True), f'&action={action}'
                    data['modelo'] = modelo = ModeloEvaluativoConvocatoria.objects.get(id=int(encrypt(request.GET['modelo'])))
                    if search:
                        data['search'] = search
                        s = search.split()
                        if len(s) == 1:
                            filtros = filtros & (Q(nombre__icontains=search))
                        else:
                            filtros = filtros & (Q(nombre__icontains=s[0]) &
                                                 Q(nombre__icontains=s[1]))
                        url_vars += '&search={}'.format(search)
                    detalles = DetalleModeloEvaluativoConvocatoria.objects.filter(filtros,modelo=modelo).order_by('nombre')
                    paging = MiPaginador(detalles, 20)
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
                    data['url_vars']=url_vars
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['listado'] = page.object_list
                    request.session['viewactivo'] = 3
                    return render(request, 'postulate/adm_postulate/viewmodeloevaluativodetalle.html', data)
                except Exception as ex:
                    pass

            elif action == 'renuncia':
                try:
                    data['title'] = 'Renuncia'
                    search, filtros, url_vars = request.GET.get('s', ''), Q(status=True), f'&action={action}'
                    if search:
                        data['search'] = search
                        s = search.split()
                        if len(s) == 1:
                            filtros = filtros & (Q(nombre__icontains=search) |
                                                 Q(meses__icontains=search)|
                                                 Q(cargos__descripcion__icontains=search))
                        else:
                            filtros = filtros & (Q(nombre__icontains=s[0]) &
                                                 Q(nombre__icontains=s[1]))
                        url_vars += '&search={}'.format(search)
                    turnos = ConfiguraRenuncia.objects.filter(filtros).order_by('-id')
                    paging = MiPaginador(turnos, 20)
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
                    data['url_vars']=url_vars
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['listado'] = page.object_list
                    request.session['viewactivo'] = 4
                    return render(request, 'postulate/adm_postulate/viewrenuncia.html', data)
                except Exception as ex:
                    pass

            elif action == 'addrenuncia':
                try:
                    form = ConfiguraRenunciaForm()
                    data['form'] = form
                    template = get_template("ajaxformmodalpos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            elif action == 'editrenuncia':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ConfiguraRenuncia.objects.get(pk=request.GET['id'])
                    form = ConfiguraRenunciaForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("ajaxformmodalpos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addturno':
                try:
                    form = TurnoConvocatoriaForm()
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formturno.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editturno':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = TurnoConvocatoria.objects.get(pk=request.GET['id'])
                    form = TurnoConvocatoriaForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formturno.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addtipoturno':
                try:
                    form = TipoTurnoConvocatoriaForm()
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formturno.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edittipoturno':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = TipoTurnoConvocatoria.objects.get(pk=request.GET['id'])
                    form = TipoTurnoConvocatoriaForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formturno.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addmodelo':
                try:
                    form = ModeloEvaluativoConvocatoriaForm()
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formmodelo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editmodelo':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ModeloEvaluativoConvocatoria.objects.get(pk=request.GET['id'])
                    form = ModeloEvaluativoConvocatoriaForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formmodelo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addmodelodetalle':
                try:
                    form = DetalleModeloEvaluativoConvocatoriaForm()
                    data['filtro'] = ModeloEvaluativoConvocatoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formmodelo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editmodelodetalle':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = DetalleModeloEvaluativoConvocatoria.objects.get(pk=request.GET['id'])
                    form = DetalleModeloEvaluativoConvocatoriaForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("postulate/adm_postulate/modal/formmodelo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'tomarasistencia':
                try:
                    data['title'] = 'Registro de asistencia'
                    id = encrypt(request.GET['id'])
                    search, filtro, url_vars = request.GET.get('s', ''), (Q(status=True)&Q(horario_id=id)), f'&action=tomarasistencia&id={request.GET["id"]}&idd={request.GET["idd"]}'
                    partida_id = request.GET.get('partida','')

                    if partida_id:
                        data['partida'] = int(partida_id)
                        url_vars += "&partida={}".format(partida_id)
                        filtro = filtro & (Q(partida__partida__id=partida_id))
                    if search:
                        data['search'] = search
                        url_vars += "&s={}".format(search)
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(partida__persona__cedula__icontains=search)|
                                                Q(partida__persona__nombres__icontains=search) |
                                                Q(partida__persona__apellido1__icontains=search) |
                                                Q(partida__persona__apellido2__icontains=search) |
                                                Q(partida__persona__cedula__icontains=search) |
                                                Q(partida__persona__pasaporte__icontains=search))
                        else:
                            filtro = filtro & (Q(partida__persona__apellido1__icontains=ss[0]) & Q(partida__persona__apellido2__icontains=ss[1]))
                    id_partidas = HorarioPersonaPartida.objects.values_list('partida__partida__id', flat=True).filter(status=True, horario_id=id).distinct()
                    data['partidas'] = partidas = Partida.objects.filter(status=True, id__in=id_partidas)

                    query = HorarioPersonaPartida.objects.filter(filtro)
                    paging = MiPaginador(query, 20)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['list_count'] = len(query)
                    data['id'] = request.GET['id']
                    data['idd'] = request.GET["idd"]
                    return render(request, "postulate/adm_postulate/viewreghorario.html", data)
                except Exception as ex:
                    err_ = f"Ocurrio un error: {ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"
                    return HttpResponseRedirect(f'{request.path}?info={err_}&action=horarios&id={request.GET["idd"]}')

            elif action == 'generaractas':
                try:
                    data['id'] = idpartida = encrypt_id(request.GET['id'])
                    data['partida'] = partida = Partida.objects.get(id=idpartida)
                    data['tipo'] = TIPO_TRIBUNAL
                    template = get_template("postulate/adm_postulate/modal/generaractas.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cargartribunal':
                try:
                    tipo = int(request.GET['value'])
                    idpartida = int(encrypt(request.GET['args']))
                    partida = Partida.objects.get(id=idpartida)
                    listado = partida.partidatribunal_set.filter(status=True, tipo=tipo).order_by('id')
                    lista=[]
                    for l in listado:
                        lista.append({'persona': str(l.persona),
                                      'cargo': l.get_cargos_display(),
                                      'firma': l.firma})
                    return JsonResponse({"results": True, 'data': lista})
                except Exception as ex:
                    pass


        else:
            try:
                data['title'] = u'Convocatorias'
                search, filtro, url_vars = request.GET.get('s', ''), (Q(status=True)), ''

                if search:
                    data['search'] = search
                    url_vars += "&s={}".format(search)
                    filtro = filtro & (Q(descripcion__icontains=search))

                listado = Convocatoria.objects.filter(filtro).order_by('-id')
                paging = MiPaginador(listado, 20)
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
                data["url_vars"] = url_vars
                data['listado'] = page.object_list
                data['list_count'] = len(listado)
                return render(request, "postulate/adm_postulate/view.html", data)
            except Exception as ex:
                pass


def fecha_letra(valor):
    mes = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    a = int(valor[0:4])
    m = int(valor[5:7])
    d = int(valor[8:10])
    if d == 1:
        return u"al %s día del mes de %s del año %s" % (numero_a_letras(d), str(mes[m - 1]),numero_a_letras(a))
    else:
        return u"a los %s días del mes de %s del año %s" % (numero_a_letras(d), str(mes[m - 1]),numero_a_letras(a))


def actualizar_modelo_evaluativo(request, convocatoria):
    try:
        partidapersona = PersonaAplicarPartida.objects.filter(status=True, partida__convocatoria=convocatoria)
        postulantes = EvaluacionPostulante.objects.filter(status=True,postulante_id__in=partidapersona)
        for post in postulantes:
            post.delete()
        # [part.verifica_evaluacion_postulante() for part in partidapersona]
    except Exception as ex:
        print(ex.__str__())


def generar_actas(request, partida=None):
    data = {}
    hoy = datetime.now().date()
    if not partida:
        idpartida = encrypt_id(request.POST['id'])
        partida = Partida.objects.get(id=idpartida)
    tipo = int(request.POST['tipo'])

    # Crear directorios recursivamente
    directory_p = os.path.join(MEDIA_ROOT, 'postulate')
    directory = os.path.join(directory_p, 'actaspartida')
    directory_o = os.path.join(directory, 'original')
    directory_f = os.path.join(directory, 'firmadas')
    os.makedirs(directory, exist_ok=True)
    os.makedirs(directory_o, exist_ok=True)
    os.makedirs(directory_f, exist_ok=True)

    data['firmas'] = firmas = PartidaTribunal.objects.filter(partida=partida, status=True, tipo=tipo).order_by('id')
    data['partida'] = partida
    if 'actaconformacion' in request.POST:
        acta = ActaPartida.objects.filter(partida=partida, tipo=1, status=True).first()
        if not acta or acta.estado == 1:
            nombre_archivo = generar_nombre(f'actaconformacion_{partida.id}_', 'generado') + '.pdf'
            fecha = request.POST.get('fecha', '')
            fecha = hoy if not fecha else fecha
            data['fecha_letra'] = fecha_letra(fecha.__str__())
            data['firmas'] = firmas.filter(firma=True).order_by('id')
            pdf, response = conviert_html_to_pdf_save_file_model(
                'postulate/actas/actaconformacion.html',
                {'pagesize': 'a4 landscape',
                 'data': data, }, nombre_archivo)
            if not acta:
                acta = ActaPartida(partida=partida, archivo=pdf, estado=1, tipo=1, tipotribunal=1)
                acta.save(request)
            else:
                acta.archivo = pdf
                acta.save(request)
            historial = HistorialActaFirma(acta=acta, archivo_original=pdf, estado=1)
            historial.save(request)

    if 'actacalificacionmerito' in request.POST:
        acta = ActaPartida.objects.filter(partida=partida, tipo=2, status=True).first()
        if not acta or acta.estado == 1:
            nombre_archivo = generar_nombre(f'actacalificacionmerito_{partida.id}_', 'generado') + '.pdf'
            data['participantes'] = participantes = PersonaAplicarPartida.objects.filter(partida=partida, status=True).order_by('persona__apellido1', 'persona__nombres')
            data['total'] = len(participantes)
            html='postulate/actas/actacalificacionmerito.html'
            if partida.convocatoria.modeloevaluativoconvocatoria:
                html='postulate/actas/actacalificacionmeritov2.html'

            pdf, response = conviert_html_to_pdf_save_file_model(html, {'data': data}, nombre_archivo)
            if not acta:
                acta = ActaPartida(partida=partida, archivo=pdf, estado=1, tipo=2, tipotribunal=1)
                acta.save(request)
            else:
                acta.archivo = pdf
                acta.save(request)
            historial = HistorialActaFirma(acta=acta, archivo_original=pdf, estado=1)
            historial.save(request)

    if 'actacalificacionmerito2' in request.POST:
        acta = ActaPartida.objects.filter(partida=partida, tipo=3, status=True).first()
        if not acta or acta.estado == 1:
            nombre_archivo = generar_nombre(f'actacalificacionmerito2_{partida.id}_', 'generado') + '.pdf'
            data['participantes'] = participantes = PersonaAplicarPartida.objects.filter(partida=partida, status=True).order_by('persona__apellido1', 'persona__nombres')
            data['total'] = len(participantes)
            data['firmas'] = PartidaTribunal.objects.filter(partida=partida, status=True, tipo=1).order_by('id')
            html='postulate/actas/actacalificacionmeritodesempate.html'
            if partida.convocatoria.modeloevaluativoconvocatoria:
                html='postulate/actas/actacalificacionmeritodesempatev2.html'
            pdf, response = conviert_html_to_pdf_save_file_model(html, {'data': data}, nombre_archivo)
            if not acta:
                acta = ActaPartida(partida=partida, archivo=pdf, estado=1, tipo=3, tipotribunal=1)
                acta.save(request)
            else:
                acta.archivo = pdf
                acta.save(request)
            historial = HistorialActaFirma(acta=acta, archivo_original=pdf, estado=1)
            historial.save(request)

    if 'actaentrevistatrib2' in request.POST:
        acta = ActaPartida.objects.filter(partida=partida, tipo=4, status=True).first()
        if not acta or acta.estado == 1:
            nombre_archivo = generar_nombre(f'actaentrevistatrib2_{partida.id}_', 'generado') + '.pdf'
            data['participantes'] = participantes = partida.personaaplicarpartida_set.filter(status=True, estado__in=[1, 4], esmejorpuntuado=True).order_by('-nota_final_entrevista')
            data['total'] = len(participantes)
            html = 'postulate/actas/actaentrevista.html'
            if partida.convocatoria.modeloevaluativoconvocatoria:
                html='postulate/actas/actaentrevistav2.html'
            pdf, response = conviert_html_to_pdf_save_file_model(html, {'data': data}, nombre_archivo)
            if not acta:
                acta = ActaPartida(partida=partida, archivo=pdf, estado=1, tipo=4, tipotribunal=2)
                acta.save(request)
            else:
                acta.archivo = pdf
                acta.save(request)
            historial = HistorialActaFirma(acta=acta, archivo_original=pdf, estado=1)
            historial.save(request)

    if 'actapuntajefinaltrib2' in request.POST:
        acta = ActaPartida.objects.filter(partida=partida, tipo=5, status=True).first()
        if not acta or acta.estado == 1:
            nombre_archivo = generar_nombre(f'actapuntajefinaltrib2_{partida.id}_', 'generado') + '.pdf'
            data['firmas'] = firmas.filter(firma=True).order_by('id')
            data['participantes'] = participantes = partida.personaaplicarpartida_set.filter(status=True, esmejorpuntuado=True).order_by('-nota_final_entrevista')
            data['total'] = len(participantes)
            html = 'postulate/actas/actanotafinal.html'
            if partida.convocatoria.modeloevaluativoconvocatoria:
                data['campos'] = partida.convocatoria.modeloevaluativoconvocatoria.campos()
                html='postulate/actas/actanotafinalv2.html'
            pdf, response = conviert_html_to_pdf_save_file_model(html, {'data': data}, nombre_archivo)
            if not acta:
                acta = ActaPartida(partida=partida, archivo=pdf, estado=1, tipo=5, tipotribunal=2)
                acta.save(request)
            else:
                acta.archivo = pdf
                acta.save(request)
            historial = HistorialActaFirma(acta=acta, archivo_original=pdf, estado=1)
            historial.save(request)