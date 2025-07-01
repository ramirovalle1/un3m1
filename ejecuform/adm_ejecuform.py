import io
import json
import os
import random
import sys
import uuid
from datetime import datetime, timedelta
import time
from decimal import Decimal

import pyqrcode
import xlsxwriter
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction, connections
from django.db.models import Q, Max
from django.forms import model_to_dict
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.shortcuts import render

# Create your views here.
from django.template.loader import get_template, render_to_string

# from arreglo_ruano_marcadas import horafin
from decorators import secure_module
from ejecuform.forms import PeriodoFormaEjecutivaForm, EventoFormaEjecutivaForm, EnfoqueFormaEjecutivaForm, \
    TurnoFormaEjecutivaForm, ModeloEvaluativoFormaEjecutivaForm, ConfiguracionFormaEjecutivaForm, \
    CapaEventoFormaEjecutivaForm, CapaEventoInscritoFormaEjecutivaForm, CapaEventoInscritoFormaEjecutivaManualForm, \
    InstructorFormaEjecutivaForm, TipoOtroRubroEjecutivaForm, ObservacionInscritoEventoFormaEjecutivaForm, \
    ModeloEvaluativoGeneralFormEjecutiva, GenerarRubrosForm, PagoFormacionEjecutivaForm
from ejecuform.models import PeriodoFormaEjecutiva, EventoFormaEjecutiva, EnfoqueFormaEjecutiva, TurnoFormaEjecutiva, \
    ModeloEvaluativoFormaEjecutiva, CapacitaEventoFormacionEjecutiva, ConfiguracionFormaEjecutiva, \
    CapaEventoInscritoFormaEjecutiva, InstructorFormaEjecutiva, CapRegistrarDatosInscritoFormaEjecutiva, \
    CapModeloEvaluativoGeneralFormaEjecutiva, CapNotaFormaEjecutiva, CapDetalleNotaFormaEjecutiva, \
    PagoFormacionEjecutiva
from sagest.adm_capacitacioneventoperiodoipec import migrar_crear_rubro_deunemi_aepunemi, \
    eliminar_y_migrar_rubro_deunemi_aepunemi, buscarPagosEpunemiRubroUnemi, buscarComprobantedeRubroEpunemi
from sagest.models import DistributivoPersona, Rubro, TipoOtroRubro, PersonaDepartamentoFirmas
from settings import PUESTO_ACTIVO_ID, EMAIL_INSTITUCIONAL_AUTOMATICO, EMAIL_DOMAIN, SITE_STORAGE, DEBUG
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, MiPaginador, log, calculate_username, variable_valor, generar_usuario, \
    salvaRubros, salvaRubrosEpunemiEdcon
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqrcertificado, conviert_html_to_pdf_name_bitacora
from sga.models import Administrativo, MESES_CHOICES, Persona, Matricula, RecordAcademico, FirmaPersona, CUENTAS_CORREOS
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt

def validaciones(data,persona):
    from ejecuform.models import InstructorFormaEjecutiva
    data['es_administrador'] = persona.usuario.groups.filter(pk__in=[423]).exists()
    data['es_instructor'] = InstructorFormaEjecutiva.objects.filter(instructor=persona,status=True).exists()
    return data

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    global ex
    data = {}
    lista = []
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema = 'https://sga.unemi.edu.ec' if not DEBUG else 'http://127.0.0.1:8000'
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'addperiodo':
            try:
                form = PeriodoFormaEjecutivaForm(request.POST,request.FILES)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                archivo = None
                instructivo = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    ext = newfile._name.split('.')[-1]
                    if not ext in ['pdf','jpg','png','jpeg']:
                        raise NameError("El formato del archivo no es el correcto (pdf,jpg,png,jpeg)")
                    if newfile.size > 20971520:# 20MB - 20971520
                        raise NameError("El tamaño del archivo excede los 20MB")
                    newfile._name = generar_nombre("periodo_archivo_", newfile._name)
                    archivo = newfile
                if 'instructivo' in request.FILES:
                    newfile = request.FILES['instructivo']
                    ext = newfile._name.split('.')[-1]
                    if not ext in ['pdf', 'jpg', 'png', 'jpeg']:
                        raise NameError("El formato del instructivo no es el correcto (pdf,jpg,png,jpeg)")
                    if newfile.size > 20971520:  # 20MB - 20971520
                        raise NameError("El tamaño del instructivo excede los 20MB")
                    newfile._name = generar_nombre("periodo_instructivo_", newfile._name)
                    instructivo = newfile
                performa = PeriodoFormaEjecutiva(
                    nombre=form.cleaned_data['nombre'],
                    descripcion=form.cleaned_data['descripcion'],
                    fechafin=form.cleaned_data['fechafin'],
                    fechainicio=form.cleaned_data['fechainicio'],
                    archivo=archivo,
                    instructivo=instructivo
                )
                performa.save(request)
                log(u"Agregó periodo de formación ejecutiva: %s"%(performa.__str__()),request,'add')
                res_js = {'result':False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'configuracion':
            try:
                form = ConfiguracionFormaEjecutivaForm(request.POST)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                if not form.cleaned_data['minasistencia'] > 0 or not form.cleaned_data['minnota'] > 0:
                    raise NameError(u"La minima nota y asistencia debe ser mayor a cero .")
                configuracion = ConfiguracionFormaEjecutiva.objects.filter()
                if configuracion.exists():
                    configuracion = configuracion[0]
                    log(u'Edito configuración de capacitación formacion ejecutiva: %s [%s]' % (configuracion, configuracion.id),request, "edit")
                else:
                    configuracion = ConfiguracionFormaEjecutiva()
                    log(u'Adiciono configuración de capacitación formacion ejecutiva: %s [%s]' % (configuracion, configuracion.id),request, "add")
                aprobado2 = Persona.objects.get(pk=form.cleaned_data['aprobado2'])
                aprobado3 = DistributivoPersona.objects.get(pk=form.cleaned_data['aprobado3'])
                configuracion.minasistencia = form.cleaned_data['minasistencia']
                configuracion.minnota = form.cleaned_data['minnota']
                configuracion.aprobado2 = aprobado2.persona
                configuracion.aprobado3 = aprobado3.persona
                # configuracion.denominacionaprobado2 = aprobado2.denominacionpuesto
                configuracion.denominacionaprobado3 = aprobado3.denominacionpuesto
                configuracion.save(request)
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'addeventocapacitacion':
            try:
                form = CapaEventoFormaEjecutivaForm(request.POST)
                # form.edit_persona_firma_certificado_1(request.POST['firma_certificado_1'],
                #                                       request.POST['cargo_firma_certificado_1'])
                # form.edit_persona_firma_certificado_2(request.POST['firma_certificado_2'],
                #                                       request.POST['cargo_firma_certificado_2'])
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                tipootrorubro = None
                generarubro = False
                fechacertificado = ''
                periodoevento = PeriodoFormaEjecutiva.objects.get(pk=int(request.POST['periodoevento']))
                if form.cleaned_data['fechacertificado']:
                    fechacertificado = form.cleaned_data['fechacertificado']
                if form.cleaned_data['tipootrorubro']:
                    tipootrorubro = form.cleaned_data['tipootrorubro']
                    generarubro = True
                if not form.cleaned_data['fechainicio'] >= periodoevento.fechainicio or not form.cleaned_data['fechafin'] <= periodoevento.fechafin:
                    raise NameError("Las fecha no puede ser mayor a las fecha del periodo.")
                if not form.cleaned_data['responsable']:
                    raise NameError("Debe ingresar el responsable del evento.")
                if not form.cleaned_data['fechainicio'] <= form.cleaned_data['fechafin']:
                    raise NameError("No puede ser mayor la fecha de inicio.")
                imagen = None
                brochure = None
                banner = None
                if 'imagen' in request.FILES:
                    newfile = request.FILES['imagen']
                    if newfile:
                        newfile._name = generar_nombre("imagen_", newfile._name)
                        imagen = newfile
                if 'brochure' in request.FILES:
                    newfile = request.FILES['brochure']
                    if newfile:
                        newfile._name = generar_nombre("brochure_", newfile._name)
                        brochure = newfile
                if 'banner' in request.FILES:
                    newfile = request.FILES['banner']
                    if newfile:
                        newfile._name = generar_nombre("banner_", newfile._name)
                        banner = newfile
                configuracion = ConfiguracionFormaEjecutiva.objects.all()
                evento = CapacitaEventoFormacionEjecutiva(periodo=periodoevento,
                    capevento=form.cleaned_data['capevento'],
                    tiporubro_id=tipootrorubro,
                    horas=form.cleaned_data['horas'],
                    costo=form.cleaned_data['costo'],
                    costoexterno=form.cleaned_data['costoexterno'],
                    objetivo=form.cleaned_data['objetivo'],
                    # firma_certificado_1=form.cleaned_data['firma_certificado_1'],
                    # cargo_firma_certificado_1=form.cleaned_data['cargo_firma_certificado_1'],
                    # firma_certificado_2=form.cleaned_data['firma_certificado_2'],
                    # cargo_firma_certificado_2=form.cleaned_data[ 'cargo_firma_certificado_2'],
                    observacion=form.cleaned_data['observacion'],
                    minasistencia=form.cleaned_data['minasistencia'],
                    minnota=form.cleaned_data['minnota'],
                    tipoparticipacion=form.cleaned_data['tipoparticipacion'],
                    contextocapacitacion=form.cleaned_data[
                    'contextocapacitacion'],
                    modalidad=form.cleaned_data['modalidad'],
                    tipocertificacion=form.cleaned_data['tipocertificacion'],
                    tipocapacitacion=form.cleaned_data['tipocapacitacion'],
                    areaconocimiento=form.cleaned_data['areaconocimiento'],
                    aula=form.cleaned_data['aula'],
                    fechainicio=form.cleaned_data['fechainicio'],
                    fechafin=form.cleaned_data['fechafin'],
                    fechainicioinscripcion=form.cleaned_data[
                    'fechainiinscripcion'],
                    fechafininscripcion=form.cleaned_data['fechafininscripcion'],
                    fechamaxpago=form.cleaned_data['fechamaxpago'],
                    cupo=form.cleaned_data['cupo'],
                    enfoque=form.cleaned_data['enfoque'],
                    visualizar=form.cleaned_data['visualizar'],
                    publicarinscripcion=form.cleaned_data['publicarinscripcion'],
                    contenido=form.cleaned_data['contenido'],
                    aprobado2=configuracion[0].aprobado2,
                    aprobado3=configuracion[0].aprobado3,
                    denominacionaprobado2=configuracion[0].denominacionaprobado2,
                    denominacionaprobado3=configuracion[0].denominacionaprobado3,
                    generarrubro=generarubro,
                    fechacertificado=fechacertificado,
                    modeloevaludativoindividual=form.cleaned_data[
                    'modeloevaludativoindividual'],
                    responsable=Administrativo.objects.get(
                    pk=form.cleaned_data['responsable']).persona,
                    mes=form.cleaned_data['mes'],
                    archivo=imagen,
                    brochure=brochure,
                    banner=banner,
                    rubroepunemi=form.cleaned_data['rubroepunemi'])
                evento.save(request)
                log(u"Agregó una capacitacion evento formación ejecutiva: %s"%(evento.__str__()),request,'add')
                res_js = {'result':'ok'}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': False, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'editeventocapacitacion':
            try:
                form = CapaEventoFormaEjecutivaForm(request.POST)
                # form.edit_persona_firma_certificado_1(request.POST['firma_certificado_1'],request.POST['cargo_firma_certificado_1'])
                # form.edit_persona_firma_certificado_2(request.POST['firma_certificado_2'],request.POST['cargo_firma_certificado_2'])
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                id = encrypt(request.POST['id'])
                evento = CapacitaEventoFormacionEjecutiva.objects.get(pk=int(id))
                # if not form.cleaned_data['fechainicio'] >= evento.fechainicio or not form.cleaned_data['fechafin'] <= evento.fechafin:
                #     raise NameError("Las fecha no puede ser mayor a las fecha del periodo.")
                if not form.cleaned_data['responsable']:
                    raise NameError("Debe ingresar el responsable del evento.")
                if not form.cleaned_data['fechainicio'] <= form.cleaned_data['fechafin']:
                    raise NameError("No puede ser mayor la fecha de inicio.")
                if 'imagen' in request.FILES:
                    newfile = request.FILES['imagen']
                    if newfile:
                        newfile._name = generar_nombre("imagen_", newfile._name)
                        evento.archivo = newfile
                if 'brochure' in request.FILES:
                    newfile = request.FILES['brochure']
                    if newfile:
                        newfile._name = generar_nombre("brochure_", newfile._name)
                        evento.brochure = newfile
                if 'banner' in request.FILES:
                    newfile = request.FILES['banner']
                    if newfile:
                        newfile._name = generar_nombre("banner_", newfile._name)
                        evento.banner = newfile
                evento.capevento = form.cleaned_data['capevento']
                evento.horas = form.cleaned_data['horas']
                evento.costo = form.cleaned_data['costo']
                evento.costoexterno = form.cleaned_data['costoexterno']
                evento.objetivo = form.cleaned_data['objetivo']
                evento.observacion = form.cleaned_data['observacion']
                if form.cleaned_data['fechacertificado']:
                    evento.fechacertificado = form.cleaned_data['fechacertificado']
                evento.minasistencia = form.cleaned_data['minasistencia']
                evento.minnota = form.cleaned_data['minnota']
                evento.aula = form.cleaned_data['aula']
                evento.fechainicio = form.cleaned_data['fechainicio']
                evento.fechafin = form.cleaned_data['fechafin']
                evento.fechainicioinscripcion = form.cleaned_data['fechainiinscripcion']
                evento.fechafininscripcion = form.cleaned_data['fechafininscripcion']
                evento.fechamaxpago = form.cleaned_data['fechamaxpago']
                evento.tipoparticipacion = form.cleaned_data['tipoparticipacion']
                evento.contextocapacitacion = form.cleaned_data['contextocapacitacion']
                evento.modalidad = form.cleaned_data['modalidad']
                evento.tipocertificacion = form.cleaned_data['tipocertificacion']
                evento.tipocapacitacion = form.cleaned_data['tipocapacitacion']
                evento.areaconocimiento = form.cleaned_data['areaconocimiento']
                evento.visualizar = form.cleaned_data['visualizar']
                evento.publicarinscripcion = form.cleaned_data['publicarinscripcion']
                evento.enfoque = form.cleaned_data['enfoque']
                evento.cupo = form.cleaned_data['cupo']
                evento.contenido = form.cleaned_data['contenido']
                evento.envionotaemail = form.cleaned_data['envionotaemail']
                evento.modeloevaludativoindividual = form.cleaned_data['modeloevaludativoindividual']
                evento.mes = form.cleaned_data['mes']
                evento.rubroepunemi = form.cleaned_data['rubroepunemi']
                # evento.firma_certificado_1 = form.cleaned_data['firma_certificado_1']
                # evento.cargo_firma_certificado_1 = form.cleaned_data['cargo_firma_certificado_1']
                # evento.firma_certificado_2 = form.cleaned_data['firma_certificado_2']
                # evento.cargo_firma_certificado_2 = form.cleaned_data['cargo_firma_certificado_2']
                if form.cleaned_data['tipootrorubro']:
                    evento.tiporubro_id = form.cleaned_data['tipootrorubro']
                    evento.generarrubro = True
                else:
                    evento.generarrubro = False
                evento.responsable = Administrativo.objects.get(pk=form.cleaned_data['responsable']).persona
                configuracion = ConfiguracionFormaEjecutiva.objects.all()
                evento.aprobado2 = configuracion[0].aprobado2
                evento.aprobado3 = configuracion[0].aprobado3
                evento.denominacionaprobado2 = configuracion[0].denominacionaprobado2
                evento.denominacionaprobado3 = configuracion[0].denominacionaprobado3
                evento.save(request)
                log(u'Edito Planificación de Evento en capacitacion Formación ejecutiva: %s - [%s] ' % (evento, evento.id),request, "change")
                res_js = {'result':'ok'}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': False, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'editperiodo':
            try:
                id = encrypt(request.POST['id'])
                preforma = PeriodoFormaEjecutiva.objects.get(status=True,id=int(id))
                form = PeriodoFormaEjecutivaForm(request.POST,request.FILES)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                archivo = None
                instructivo = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    ext = newfile._name.split('.')[-1]
                    if not ext in ['pdf','jpg','png','jpeg']:
                        raise NameError("El formato del archivo no es el correcto (pdf,jpg,png,jpeg)")
                    if newfile.size > 20971520:# 20MB - 20971520
                        raise NameError("El tamaño del archivo excede los 20MB")
                    newfile._name = generar_nombre("periodo_archivo_", newfile._name)
                    archivo = newfile
                    preforma.archivo=archivo
                if 'instructivo' in request.FILES:
                    newfile = request.FILES['instructivo']
                    ext = newfile._name.split('.')[-1]
                    if not ext in ['pdf', 'jpg', 'png', 'jpeg']:
                        raise NameError("El formato del instructivo no es el correcto (pdf,jpg,png,jpeg)")
                    if newfile.size > 20971520:  # 20MB - 20971520
                        raise NameError("El tamaño del instructivo excede los 20MB")
                    newfile._name = generar_nombre("periodo_instructivo_", newfile._name)
                    instructivo = newfile
                    preforma.instructivo=instructivo
                preforma.nombre=form.cleaned_data['nombre']
                preforma.descripcion=form.cleaned_data['descripcion']
                preforma.save(request)
                log(u"Editó periodo de formación ejecutiva: %s"%(preforma.__str__()),request,'change')
                res_js = {'result':False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'delperiodo':
            try:
                id = encrypt(request.POST['id'])
                preforma = PeriodoFormaEjecutiva.objects.get(status=True, id=int(id))
                preforma.status = False
                preforma.save(request)
                log(u"Eliminó periodo de formación ejecutiva: %s"%(preforma.__str__()),request,'del')
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'addevento':
            try:
                form = EventoFormaEjecutivaForm(request.POST)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                evento = EventoFormaEjecutiva(
                    nombre=form.cleaned_data['nombre']
                )
                evento.save(request)
                log(u"Agregó evento de formación ejecutiva: %s" % (evento.__str__()), request, 'change')
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'editevento':
            try:
                id = encrypt(request.POST['id'])
                evento = EventoFormaEjecutiva.objects.get(status=True, id=int(id))
                form = EventoFormaEjecutivaForm(request.POST)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                evento.nombre=form.cleaned_data['nombre']
                evento.save(request)
                evento.save(request)
                log(u"Editó evento de formación ejecutiva: %s" % (evento.__str__()), request, 'add')
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'delevento':
            try:
                id = encrypt(request.POST['id'])
                evento = EventoFormaEjecutiva.objects.get(status=True, id=int(id))
                evento.status = False
                evento.save(request)
                log(u"Eliminó evento de formación ejecutiva: %s"%(evento.__str__()),request,'del')
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'addenfoque':
            try:
                form = EnfoqueFormaEjecutivaForm(request.POST)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                enfoque = EnfoqueFormaEjecutiva(
                    nombre=form.cleaned_data['nombre']
                )
                enfoque.save(request)
                log(u"Agregó enfoque de formación ejecutiva: %s" % (enfoque.__str__()), request, 'change')
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'editenfoque':
            try:
                id = encrypt(request.POST['id'])
                enfoque = EnfoqueFormaEjecutiva.objects.get(status=True, id=int(id))
                form = EnfoqueFormaEjecutivaForm(request.POST)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                enfoque.nombre=form.cleaned_data['nombre']
                enfoque.save(request)
                enfoque.save(request)
                log(u"Editó enfoque de formación ejecutiva: %s" % (enfoque.__str__()), request, 'add')
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'delenfoque':
            try:
                id = encrypt(request.POST['id'])
                enfoque = EnfoqueFormaEjecutiva.objects.get(status=True, id=int(id))
                enfoque.status = False
                enfoque.save(request)
                log(u"Eliminó enfoque de formación ejecutiva: %s"%(enfoque.__str__()),request,'del')
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'addturno':
            try:
                form = TurnoFormaEjecutivaForm(request.POST)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                if TurnoFormaEjecutiva.objects.values('id').filter(turno=form.cleaned_data['turno'], status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"El Turno ya existe."})

                if form.cleaned_data['horainicio'] > form.cleaned_data['horafin']:
                    return JsonResponse({"result": True, "mensaje": u"Las hora fin no debe ser mayor."})
                datos = json.loads(request.POST['lista_items1'])
                horas = 0
                for elemento in datos:
                    horas = float(elemento['horas'])
                turno = TurnoFormaEjecutiva(
                    turno=form.cleaned_data['turno'],
                    horainicio=form.cleaned_data['horainicio'],
                    horafin=form.cleaned_data['horafin'],
                    horas=horas
                )
                turno.save(request)
                log(u"Agregó turno de formación ejecutiva: %s" % (turno.__str__()), request, 'change')
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'editturno':
            try:
                id = encrypt(request.POST['id'])
                turno = TurnoFormaEjecutiva.objects.get(status=True, id=int(id))
                form = TurnoFormaEjecutivaForm(request.POST)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                if form.cleaned_data['horainicio'] > form.cleaned_data['horafin']:
                    return JsonResponse({"result": True, "mensaje": u"Las hora fin no debe ser mayor."})
                datos = json.loads(request.POST['lista_items1'])
                horas = 0
                for elemento in datos:
                    horas = float(elemento['horas'])
                turno.horainicio=form.cleaned_data['horainicio']
                turno.horafin=form.cleaned_data['horafin']
                turno.horas=horas
                turno.save(request)
                log(u"Editó turno de formación ejecutiva: %s" % (turno.__str__()), request, 'add')
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'delturno':
            try:
                id = encrypt(request.POST['id'])
                turno = TurnoFormaEjecutiva.objects.get(status=True, id=int(id))
                turno.status = False
                turno.save(request)
                log(u"Eliminó turno de formación ejecutiva: %s"%(turno.__str__()),request,'del')
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'addmodelo':
            try:
                form = ModeloEvaluativoFormaEjecutivaForm(request.POST)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                modelo = ModeloEvaluativoFormaEjecutiva(
                    nombre=form.cleaned_data['nombre'],
                    notaminima=form.cleaned_data['notaminima'],
                    notamaxima=form.cleaned_data['notamaxima'],
                    principal=form.cleaned_data['principal'],
                    evaluacion=form.cleaned_data['evaluacion']
                )
                modelo.save(request)
                log(u"Agregó modelo de formación ejecutiva: %s" % (modelo.__str__()), request, 'change')
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'editmodelo':
            try:
                id = encrypt(request.POST['id'])
                modelo = ModeloEvaluativoFormaEjecutiva.objects.get(status=True, id=int(id))
                form = ModeloEvaluativoFormaEjecutivaForm(request.POST)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                modelo.nombre=form.cleaned_data['nombre']
                modelo.notaminima=form.cleaned_data['notaminima']
                modelo.notamaxima=form.cleaned_data['notamaxima']
                modelo.principal=form.cleaned_data['principal']
                modelo.evaluacion=form.cleaned_data['evaluacion']
                modelo.save(request)
                log(u"Editó modelo de formación ejecutiva: %s" % (modelo.__str__()), request, 'add')
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'delmodelo':
            try:
                id = encrypt(request.POST['id'])
                modelo = ModeloEvaluativoFormaEjecutiva.objects.get(status=True, id=int(id))
                modelo.status = False
                modelo.save(request)
                log(u"Eliminó modelo de formación ejecutiva: %s"%(modelo.__str__()),request,'del')
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'addinscrito':
            try:
                form = CapaEventoInscritoFormaEjecutivaForm(request.POST)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                participante = Persona.objects.get(pk=request.POST['participante'])

                if CapaEventoInscritoFormaEjecutiva.objects.filter(participante=participante,capeventoperiodo_id=int(encrypt(request.POST['id'])), status=True).exists():
                    raise NameError(u"Ya se encuentra inscrito")

                if not CapacitaEventoFormacionEjecutiva.objects.get(pk=int(encrypt(request.POST['id']))).hay_cupo_inscribir():
                    raise NameError(u"No hay cupo para continuar adicionando")

                inscribir = CapaEventoInscritoFormaEjecutiva(capeventoperiodo_id=int(encrypt(request.POST['id'])),participante=participante)
                inscribir.save(request)
                log(u"Agregó inscripción: %s"%(inscribir.__str__),request,'add')
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'addinscribir':
            try:
                f = CapaEventoInscritoFormaEjecutivaManualForm(request.POST)
                if f.is_valid():
                    participante = Persona.objects.get(pk=request.POST['idestudiante'])

                    if CapaEventoInscritoFormaEjecutiva.objects.filter(participante=participante,
                                                      capeventoperiodo_id=int(request.POST['id'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra inscrito"})
                    if not CapacitaEventoFormacionEjecutiva.objects.get(pk=int(request.POST['id'])).hay_cupo_inscribir():
                        return JsonResponse({"result": "bad", "mensaje": u"No hay cupo para continuar adicionando"})

                    inscribir = CapaEventoInscritoFormaEjecutiva(capeventoperiodo_id=int(request.POST['id']),
                                                participante=participante)
                    inscribir.save(request)

                    return JsonResponse(
                        {'result': 'ok', "mensaje": u"Estimado participante, se inscribió correctamente."})
                    # return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Llene todos los campos"})

        # PERSONA
        elif action == 'verificarcedula':
            try:
                if Persona.objects.values('id').filter(status=True,cedula=request.POST["cedula"]).exists():
                    return JsonResponse({"result": "no"})
                else:
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad"})

        elif action == 'addpersona':
            try:
                form = CapaEventoInscritoFormaEjecutivaManualForm(request.POST)
                if form.is_valid():
                    if Persona.objects.filter(status=True,cedula=request.POST["cedula"]).exists():
                        return JsonResponse({"result": "no", "mensaje": u"Existe un usuario con la cédula digitada."})
                    persona = Persona(nombres=form.cleaned_data['nombres'],
                                      apellido1=form.cleaned_data['apellido1'],
                                      apellido2=form.cleaned_data['apellido2'],
                                      cedula=form.cleaned_data['cedula'],
                                      nacimiento=form.cleaned_data['nacimiento'],
                                      sexo=form.cleaned_data['sexo'],
                                      telefono=form.cleaned_data['telefono'],
                                      telefono_conv=form.cleaned_data['telefono_conv'],
                                      email=form.cleaned_data['email'],
                                      direccion=form.cleaned_data['direccion'],
                                      tipopersona=1)
                    persona.save(request)
                    if int(request.POST['tipo']) == 1:
                        capeven = CapacitaEventoFormacionEjecutiva.objects.get(id=int(request.POST['id']))
                        instructor = InstructorFormaEjecutiva(capeventoperiodo_id=capeven.id, instructor=persona)
                        instructor.save(request)
                        log(u'Adicionó nuevo instructor %s para la Capacitacion IPEC: %s' % (instructor, capeven),
                            request, "add")
                    else:
                        registrodatos = CapRegistrarDatosInscritoFormaEjecutiva(persona=persona,
                                                                      lugarestudio=form.cleaned_data['lugarestudio'],
                                                                      carrera=form.cleaned_data['carrera'],
                                                                      profesion=form.cleaned_data['profesion'],
                                                                      institucionlabora=form.cleaned_data[
                                                                          'institucionlabora'],
                                                                      cargodesempena=form.cleaned_data[
                                                                          'cargodesempena'],
                                                                      esparticular=form.cleaned_data['esparticular'])
                        registrodatos.save(request)
                        log(
                            u'Adiciono Persona desde en Capacitacion IPEC: persona: %s [%s] - Registrodatosipec: %s [%s]' % (
                                persona, persona.id, registrodatos, registrodatos.id), request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'convalidar':
            try:
                evento = CapacitaEventoFormacionEjecutiva.objects.get(pk=request.POST['id'])
                evento.convalidar = True if request.POST['val'] == 'y' else False
                evento.save(request)
                log(u'Convalida evento periodo IPEC : %s (%s)' % (evento, evento.convalidar),
                    request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        elif action == 'bloqueopublicacion':
            try:
                evento = CapacitaEventoFormacionEjecutiva.objects.get(pk=request.POST['id'])
                evento.visualizar = True if request.POST['val'] == 'y' else False
                evento.save(request)
                log(u'Visualiza o no en capacitacion evento periodo IPEC : %s (%s)' % (evento, evento.visualizar),
                    request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        elif action == 'updatecupo':
            try:
                evento = CapacitaEventoFormacionEjecutiva.objects.get(pk=int(request.POST['eid']))
                valor = int(request.POST['vc'])
                if valor > 999:
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No puede establecer un cupo menor a" + str(999 + 1)})
                if valor < evento.contar_inscripcion_evento_periodo():
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"El cupo no puede ser menor a la cantidad de inscrito"})
                cupoanterior = evento.cupo
                evento.cupo = valor
                evento.save(request)
                log(u'Actualizo cupo a evento periodo capacitacion IPEC: %s cupo anterior: %s cupo actual: %s' % (
                    evento, str(cupoanterior), str(evento.cupo)), request, "add")
                return JsonResponse({'result': 'ok', 'valor': evento.cupo})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al eliminar los datos."})

        elif action == 'delinscrito':
            try:
                inscribir = CapaEventoInscritoFormaEjecutiva.objects.get(pk=int(request.POST['id']))
                inscribir.status = False
                inscribir.save(request)
                log(u"Eliminó inscripción: %s"%(inscribir.__str__()),request,'del')
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Error al eliminar los datos."})

        elif action == 'addinstructor':
            try:
                form = InstructorFormaEjecutivaForm(request.POST)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                if InstructorFormaEjecutiva.objects.filter(instructor=form.cleaned_data['instructor'],
                                                    capeventoperiodo_id=int(encrypt(request.POST['eventoperiodo'])),
                                                    status=True).exists():
                    return JsonResponse({"result": True, "mensaje": u"El nombre ya existe."})
                instructor = InstructorFormaEjecutiva(capeventoperiodo_id=int(encrypt(request.POST['eventoperiodo'])),
                                               instructor_id=form.cleaned_data['instructor'],
                                               instructorprincipal=form.cleaned_data['instructorprincipal'],
                                               nombrecurso=form.cleaned_data['nombrecurso'])
                instructor.save(request)
                if not InstructorFormaEjecutiva.objects.filter(instructor=instructor.instructor, activo=True).exists():
                    if instructor.instructorprincipal:
                        instructor.activo = True
                instructor.save(request)

                if not instructor.tiene_perfilusuario():
                    if not instructor.instructor.usuario:
                        persona = Persona.objects.get(pk=instructor.instructor.id)
                        username = calculate_username(persona)
                        generar_usuario(persona, username, variable_valor('INSTRUCTOR_GROUP_ID'))
                        if EMAIL_INSTITUCIONAL_AUTOMATICO:
                            persona.emailinst = username + '@' + EMAIL_DOMAIN
                        persona.save(request)
                    instructor.crear_eliminar_perfil_instructor(True)
                log(u'Adiciono Instructor en Capacitacion Formación Ejecutiva: %s - [%s]' % (instructor, instructor.id), request,"add")
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'updateprincipal':
            try:
                instructor = InstructorFormaEjecutiva.objects.get(pk=int(request.POST['id']))
                if instructor.instructorprincipal:
                    instructor.instructorprincipal = False
                else:
                    instructor.instructorprincipal = True

                instructor.save(request)
                log(u'Cambio el instructor principal %s Formación ejecutiva' % persona, request, "add")
                res_js = {'result': True, 'mensaje': u'Cambio el instructor principal %s Formación ejecutiva' % persona}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': False, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'editinstructor':
            try:
                id = encrypt(request.POST['id'])
                form = InstructorFormaEjecutivaForm(request.POST)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                instructor = InstructorFormaEjecutiva.objects.get(pk=int(id))
                instructor.instructor = Persona.objects.get(pk=form.cleaned_data['instructor'])
                instructor.instructorprincipal = form.cleaned_data['instructorprincipal']
                instructor.nombrecurso = form.cleaned_data['nombrecurso']
                if not InstructorFormaEjecutiva.objects.filter(instructor_id=form.cleaned_data['instructor'], activo=True,status=True).exists():
                    if instructor.instructorprincipal:
                        instructor.activo = True
                instructor.save(request)
                log(u'Editar Instructor Capacitación Formación ejecutiva: %s - [%s]' % (instructor, instructor.id), request,"change")
                res_js = {"result": False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'delinstructor':
            try:
                inscribir = InstructorFormaEjecutiva.objects.get(pk=int(request.POST['id']))
                inscribir.status = False
                inscribir.save(request)
                log(u'Elimino Instructor Capacitación Formacion ejecutvia : %s' % inscribir, request, "del")
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Error al eliminar los datos."})

        elif action == 'createinstructorperfil':
            try:
                instructor = InstructorFormaEjecutiva.objects.get(pk=int(request.POST['id']))
                if not instructor.tiene_perfilusuario():
                    if not instructor.instructor.usuario:
                        persona = Persona.objects.get(pk=instructor.instructor.id)
                        username = calculate_username(persona)
                        generar_usuario(persona, username, variable_valor('INSTRUCTOR_GROUP_ID'))
                        if EMAIL_INSTITUCIONAL_AUTOMATICO:
                            persona.emailinst = username + '@' + EMAIL_DOMAIN
                        persona.save(request)
                instructor.crear_eliminar_perfil_instructor(True)
                log(u'Se creo el perfil de usuario del instructor - Formación Ejecutiva: %s' % instructor, request, "add")
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Error al eliminar los datos."})

        elif action == 'activardesactivarperfil':
            try:
                instructor = InstructorFormaEjecutiva.objects.get(status=True,id=int(request.POST['id']))
                if instructor.estado_perfil():
                    instructor.activo = False
                    instructor.save(request)
                    log(u'Desactivo perfil de usuario de instructor: %s' % instructor, request, "desc")
                else:
                    if instructor.tiene_perfilusuario():
                        instructor.activo = True
                        instructor.save(request)
                        log(u'Desactivo perfil de usuario de instructor: %s' % instructor, request, "act")
                    else:
                        instructor.activo = True
                        instructor.save(request)
                        instructor.crear_eliminar_perfil_instructor(True)
                        log(u'Desactivo perfil de usuario de instructor: %s' % instructor, request, "act")
                        log(u'Se creo el perfil de usuario de instructor por activar perfil: %s' % instructor, request,
                            "add")
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'listacursos':
            try:
                lista = []
                c = 0
                for i in InstructorFormaEjecutiva.objects.filter(instructor_id=request.POST['id']):
                    c = c + 1
                    etiqueta = 'important'
                    if i.capeventoperiodo.estado_evento() == 'EN CURSO':
                        etiqueta = 'info'
                    elif i.capeventoperiodo.estado_evento() == 'PENDIENTE':
                        etiqueta = 'warning'
                    lista.append(
                        [i.id, c, str(i.capeventoperiodo.capevento.nombre), str(i.capeventoperiodo.estado_evento()),
                         str(i.capeventoperiodo.fechainicio.strftime("%d-%m-%Y")),
                         str(i.capeventoperiodo.fechafin.strftime("%d-%m-%Y")), etiqueta])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addtiporubro':
            try:
                form = TipoOtroRubroEjecutivaForm(request.POST)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                registro = TipoOtroRubro(nombre=form.cleaned_data['nombre'],
                                         partida_id=100,
                                         unidad_organizacional_id=115,
                                         programa_id=8,
                                         interface=True,
                                         valor=form.cleaned_data['valor'],
                                         ivaaplicado=form.cleaned_data['ivaaplicado'],
                                         activo=True,
                                         tiporubro=8,
                                         exportabanco=False,
                                         nofactura=False)
                registro.save(request)
                log(u'Registro nuevo rubro: %s' % registro, request, "add")
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'edittiporubro':
            try:
                id = encrypt(request.POST['id'])
                rubro = TipoOtroRubro.objects.get(status=True,id=int(id))
                form = TipoOtroRubroEjecutivaForm(request.POST)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                if rubro.se_usa():
                    return JsonResponse({"result": True, "mensaje": "El rubro se encuentra en uso."})
                if TipoOtroRubro.objects.filter(nombre=(request.POST['nombre'])).exclude(id=rubro.id).exists():
                    return JsonResponse({"result": True, "mensaje": "Existe un rubro con el mismo nombre."})
                rubro.nombre = form.cleaned_data['nombre']
                rubro.valor = form.cleaned_data['valor']
                rubro.ivaaplicado = form.cleaned_data['ivaaplicado']
                rubro.save(request)
                log(u'Registro modificado Rubro: %s' % rubro, request, "edit")
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'deltiporubro':
            try:
                id = encrypt(request.POST['id'])
                rubro = TipoOtroRubro.objects.get(status=True, id=int(id))
                rubro.status = False
                rubro.save(request)
                log(u'Eliminó rubro: %s' % rubro, request, "del")
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Error al eliminar los datos."})

        elif action == 'activar_inscrito':
            try:
                inscrito = CapaEventoInscritoFormaEjecutiva.objects.get(pk=int(encrypt(request.POST['id'])))
                inscrito.desactivado=False
                inscrito.save()
                log(u'Activó inscrito: %s' % (inscrito), request, "del")
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Error al activar inscrito. {} CodLine {}".format(ex,sys.exc_info()[-1].tb_lineno)})

        elif action == 'deleventocapform':
            try:
                id = encrypt(request.POST['id'])
                capaevento = CapacitaEventoFormacionEjecutiva.objects.get(status=True, id=int(id))
                capaevento.status = False
                capaevento.save(request)
                log(u'Eliminó el evento capacitación: %s' % capaevento, request, "del")
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Error al eliminar los datos."})

        elif action == 'addobservacion':
            try:
                id = encrypt(request.POST['id'])
                inscrito = CapaEventoInscritoFormaEjecutiva.objects.get(pk=int(id))
                form = ObservacionInscritoEventoFormaEjecutivaForm(request.POST,request.FILES)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                inscrito.observacionmanual = form.cleaned_data['observacionmanual']
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if not newfile._name.split('.')[-1] in ['pdf']:
                        raise NameError(f"Suba un formato de archivo valido (pdf)")
                    if newfile.size > 10485760:
                        raise NameError(u"El tamaño del fichero excede los 10MB")
                    newfile._name = generar_nombre("observacion_inscripcionformaejecu", newfile._name)
                    inscrito.archivo = newfile
                inscrito.save(request)
                log(u"Agregó observacion al inscrito: %s - %s"%(inscrito,inscrito.id),request,'change')
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'generar_rubro':
            try:
                id = encrypt(request.POST['id'])
                form = GenerarRubrosForm(request.POST)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                cuota = form.cleaned_data['cuota']
                if not cuota>=0:
                    raise NameError("El numero de cuota no debe ser negativo")
                inscribir = CapaEventoInscritoFormaEjecutiva.objects.get(status=True,id=int(id))
                if not inscribir.capeventoperiodo.tiporubro and inscribir.capeventoperiodo.generarrubro:
                    raise NameError(u"No existe Rubro en curso.")
                tiprubroarancel = inscribir.capeventoperiodo.tiporubro
                personalunemi = False
                if inscribir.participante.distributivopersona_set.filter(estadopuesto_id=1, status=True).exists():
                    costo_total_curso = inscribir.capeventoperiodo.costo
                    personalunemi = True
                else:
                    if inscribir.participante.inscripcion_set.filter(status=True).exclude(coordinacion_id=9):
                        verificainsripcion = inscribir.participante.inscripcion_set.values_list('id').filter(status=True).exclude(coordinacion_id=9)
                        if Matricula.objects.filter(inscripcion_id__in=verificainsripcion, status=True):
                            costo_total_curso = inscribir.capeventoperiodo.costo
                            personalunemi = True
                        else:
                            if RecordAcademico.objects.filter(inscripcion_id__in=verificainsripcion, status=True):
                                costo_total_curso = inscribir.capeventoperiodo.costo
                                personalunemi = True
                            else:
                                costo_total_curso = inscribir.capeventoperiodo.costoexterno
                    else:
                        costo_total_curso = inscribir.capeventoperiodo.costoexterno
                if inscribir.capeventoperiodo.generarrubro:
                    inscribir.personalunemi = personalunemi
                    inscribir.save(request)
                    if cuota > 1:
                        costo_total_curso = float(costo_total_curso // cuota)
                        for c in range(cuota):
                            fecha_pago = inscribir.capeventoperiodo.fechamaxpago + timedelta(days=1+(c*31))
                            if not Rubro.objects.filter(persona=inscribir.participante,
                                                        capeventoperiodoformejecu=inscribir.capeventoperiodo,
                                                        status=True,cuota=c+1).exists():
                                rubro = Rubro(tipo=tiprubroarancel,
                                              persona=inscribir.participante,
                                              relacionados=None,
                                              nombre=tiprubroarancel.nombre + ' - ' + inscribir.capeventoperiodo.capevento.nombre,
                                              cuota=c+1,
                                              fecha=datetime.now().date(),
                                              fechavence=fecha_pago,
                                              valor=costo_total_curso,
                                              iva_id=1,
                                              valortotal=costo_total_curso,
                                              capeventoperiodoformejecu=inscribir.capeventoperiodo,
                                              saldo=costo_total_curso,
                                              epunemi=True,
                                              cancelado=False)
                                rubro.save(request)
                                log(u'Adiciono un inscrito en Evento en Capacitacion Formacion Ejecutiva: %s [%s]' % (
                                inscribir, inscribir.participante.id), request, "add")
                                resultado_migracion = migrar_crear_rubro_deunemi_aepunemi(request, [rubro],
                                                                                          action='generar_rubro')
                                if resultado_migracion['result'] == 'ok':
                                    res_js = {"result": False}
                                    messages.success(request, "Se creó  el rubro y se migró exitosamente a EPUNEMI.")
                                else:
                                    raise NameError(resultado_migracion['mensaje'])
                    else:
                        if not Rubro.objects.filter(persona=inscribir.participante,capeventoperiodoformejecu=inscribir.capeventoperiodo, status=True).exists():
                            rubro = Rubro(tipo=tiprubroarancel,
                                          persona=inscribir.participante,
                                          relacionados=None,
                                          nombre=tiprubroarancel.nombre + ' - ' + inscribir.capeventoperiodo.capevento.nombre,
                                          cuota=1,
                                          fecha=datetime.now().date(),
                                          fechavence=inscribir.capeventoperiodo.fechamaxpago + timedelta(days=1),
                                          valor=costo_total_curso,
                                          iva_id=1,
                                          valortotal=costo_total_curso,
                                          capeventoperiodoformejecu=inscribir.capeventoperiodo,
                                          saldo=costo_total_curso,
                                          epunemi=True,
                                          cancelado=False)
                            rubro.save(request)
                            log(u'Adiciono un inscrito en Evento en Capacitacion Formacion Ejecutiva: %s [%s]'%(inscribir, inscribir.participante.id),request, "add")
                            resultado_migracion = migrar_crear_rubro_deunemi_aepunemi(request, [rubro], action='generar_rubro')
                            if resultado_migracion['result'] == 'ok':
                                res_js = {"result": False}
                                messages.success(request, "Se creó  el rubro y se migró exitosamente a EPUNEMI.")
                            else:
                                raise NameError(resultado_migracion['mensaje'])
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'mensaje': msg_err}
            return JsonResponse(res_js,safe=False)

        elif action == 'borrar_rubro':
            try:
                inscribir = CapaEventoInscritoFormaEjecutiva.objects.get(id=request.POST['id'])
                id_evento = inscribir.capeventoperiodo.id
                id_participante = inscribir.participante_id
                rubro = Rubro.objects.filter(status=True, capeventoperiodoformejecu_id=id_evento, persona_id=id_participante,cancelado=False)
                # Eliminar rubro unemi y migrar rubros a epunemi
                result_migrar = eliminar_y_migrar_rubro_deunemi_aepunemi_formacionejecutiva(request, rubro, action='borrar_rubro')
                if result_migrar['result'] == "ok":
                    mensajemigrar = result_migrar['mensaje']
                    result_rubrosunemi = mensajemigrar['total_rubrosunemi']
                    result_rubrosepunemi = mensajemigrar['total_rubrosepunemi']
                    resultrubpagados_noeli = mensajemigrar['rubrospagados_noeliminados']
                    if result_rubrosunemi == 0 and result_rubrosepunemi == 0:
                        if resultrubpagados_noeli:
                            mensajeeliminados = f'No se eliminó ningún rubro. Por los siguientes motivos: {resultrubpagados_noeli}.'
                        else:
                            mensajeeliminados = f'No se eliminó ningún rubro.'
                    else:
                        if resultrubpagados_noeli:
                            mensajeeliminados = f"Se han eliminado {result_rubrosunemi} rubros y se han migrado (eliminado) {result_rubrosepunemi} rubros a EPUNEMI exitosamente. No se eliminaron o migraron: {resultrubpagados_noeli}."
                            # mensajeeliminados = f"Se han migrado (eliminado) {result_rubrosepunemi} rubros exitosamente a EPUNEMI."
                        else:
                            mensajeeliminados = f"Se han eliminado {result_rubrosunemi} rubros y se han migrado (eliminado) {result_rubrosepunemi} rubros a EPUNEMI exitosamente."
                    res_js = {"error": False, "message": mensajeeliminados}
                    messages.success(request, mensajeeliminados)
                else:
                    raise NameError(result_migrar['mensaje'])
                # Eliminar rubro unemi y migrar rubros a epunemi
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'message': msg_err}
            return JsonResponse(res_js, safe=False)

        elif action == 'generarrubromasivo':
            try:
                evento = CapacitaEventoFormacionEjecutiva.objects.get(pk=int(encrypt(request.POST['id'])))
                form = GenerarRubrosForm(request.POST)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                cuota = form.cleaned_data['cuota']
                if not cuota >= 0:
                    raise NameError("El numero de cuota no debe ser negativo")

                # Si el evento no tiene costo no podrá generar rubros.
                if evento.costo == 0 and evento.costoexterno == 0:
                    raise NameError(u"Éste evento no tiene costo, por lo tanto no se permite generar rubros a los inscritos.")

                # Si el evento genera rubros=true debe tener tipo rubro
                if not evento.tiporubro and evento.generarrubro:
                    raise NameError(u"No existe rubro en éste evento, por lo tanto no puede generar rubros a los inscritos.")

                # Inscritos que NO se hayan desactivado y que NO tengan rubro creado
                inscritos = CapaEventoInscritoFormaEjecutiva.objects.filter(status=True, capeventoperiodo=evento, desactivado=False)
                if not inscritos:
                    raise NameError(u"No hay inscritos pendientes de generación de rubro.")

                totalrubros, listarubrosunemi = 0, []

                for inscribir in inscritos:

                    if not inscribir.existerubrocurso():
                        tiprubroarancel = inscribir.capeventoperiodo.tiporubro
                        personalunemi = False
                        if inscribir.participante.distributivopersona_set.filter(estadopuesto_id=1, status=True).exists():
                            costo_total_curso = inscribir.capeventoperiodo.costo
                            personalunemi = True
                        else:
                            if inscribir.participante.inscripcion_set.filter(status=True).exclude(coordinacion_id=9):
                                verificainsripcion = inscribir.participante.inscripcion_set.values_list('id').filter(
                                    status=True).exclude(coordinacion_id=9)
                                if Matricula.objects.filter(inscripcion_id__in=verificainsripcion, status=True):
                                    costo_total_curso = inscribir.capeventoperiodo.costo
                                    personalunemi = True
                                else:
                                    if RecordAcademico.objects.filter(inscripcion_id__in=verificainsripcion, status=True):
                                        costo_total_curso = inscribir.capeventoperiodo.costo
                                        personalunemi = True
                                    else:
                                        costo_total_curso = inscribir.capeventoperiodo.costoexterno
                            else:
                                costo_total_curso = inscribir.capeventoperiodo.costoexterno

                        if inscribir.capeventoperiodo.generarrubro:
                            inscribir.personalunemi = personalunemi
                            inscribir.save(request)
                            if cuota > 1:
                                costo_total_curso = float(costo_total_curso // cuota)
                                for c in range(cuota):
                                    fecha_pago = inscribir.capeventoperiodo.fechamaxpago + timedelta(days=1 + (c * 31))
                                    if not Rubro.objects.filter(persona=inscribir.participante,
                                                                capeventoperiodoformejecu=inscribir.capeventoperiodo,
                                                                status=True, cuota=c + 1).exists():
                                        rubro = Rubro(tipo=tiprubroarancel,
                                                      persona=inscribir.participante,
                                                      relacionados=None,
                                                      nombre=tiprubroarancel.nombre + ' - ' + inscribir.capeventoperiodo.capevento.nombre,
                                                      cuota=c + 1,
                                                      fecha=datetime.now().date(),
                                                      fechavence=fecha_pago,
                                                      valor=costo_total_curso,
                                                      iva_id=1,
                                                      valortotal=costo_total_curso,
                                                      capeventoperiodoformejecu=inscribir.capeventoperiodo,
                                                      saldo=costo_total_curso,
                                                      epunemi=True,
                                                      cancelado=False)
                                        rubro.save(request)
                                        totalrubros += 1
                                        # Listado de rubros a migrar
                                        listarubrosunemi.append(rubro)
                            else:
                                if not Rubro.objects.filter(persona=inscribir.participante,
                                                            capeventoperiodoformejecu=inscribir.capeventoperiodo,
                                                            status=True).exists():
                                    rubro = Rubro(tipo=tiprubroarancel,
                                                  persona=inscribir.participante,
                                                  relacionados=None,
                                                  nombre=tiprubroarancel.nombre + ' - ' + inscribir.capeventoperiodo.capevento.nombre,
                                                  cuota=1,
                                                  fecha=datetime.now().date(),
                                                  fechavence=inscribir.capeventoperiodo.fechamaxpago + timedelta(days=1),
                                                  valor=costo_total_curso,
                                                  iva_id=1,
                                                  valortotal=costo_total_curso,
                                                  capeventoperiodoformejecu=inscribir.capeventoperiodo,
                                                  saldo=costo_total_curso,
                                                  epunemi=True,
                                                  cancelado=False)
                                    rubro.save(request)
                                    totalrubros += 1
                                    # Listado de rubros a migrar
                                    listarubrosunemi.append(rubro)
                if totalrubros > 0:
                    # Migrar rubros
                    resultado_migraciones = migrar_crear_rubro_deunemi_aepunemi(request, listarubrosunemi, action='generarrubromasivo')
                    if resultado_migraciones['result'] == 'ok':
                        resultado_funcion = resultado_migraciones['mensaje']
                        log(u'Generó rubros masivo a los inscritos en evento IPEC: %s [%s]' % (inscritos, inscribir.capeventoperiodo.id), request, "add")
                        messages.success(request, f"Se creó {totalrubros} rubros y se migró {resultado_funcion['total']} rubros exitosamente a EPUNEMI.")
                        res_js = {"result": False}
                    else:
                        raise NameError(resultado_migraciones['mensaje'])
                    # Migrar rubros
                else:
                    res_js = {'result': False, "message": u"No hay inscritos pendientes de generación de rubro."}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'mensaje': msg_err}
            return JsonResponse(res_js, safe=False)

        elif action == 'borrarrubromasivo':
            try:
                evento = CapacitaEventoFormacionEjecutiva.objects.get(pk=int(encrypt(request.POST['id'])))
                inscritos = CapaEventoInscritoFormaEjecutiva.objects.filter(capeventoperiodo=evento, status=True)
                totaleliminado, idrubrosunemieliminar = 0, []
                for inscrito in inscritos:
                    nota = inscrito.nota_total_evento(evento)

                    if not nota:
                        if not inscrito.rutapdf:
                            excluir_persona = None
                            if Rubro.objects.filter(cancelado=True, status=True, persona=inscrito.participante,
                                                    capeventoperiodoformejecu=evento).exists():
                                excluir_persona = Q(persona=inscrito.participante)
                            if excluir_persona:
                                if Rubro.objects.filter(cancelado=False, status=True, persona=inscrito.participante,
                                                    capeventoperiodoformejecu=evento).exclude(excluir_persona).exists():
                                    rubro = Rubro.objects.filter(cancelado=False, status=True, persona=inscrito.participante,
                                                              capeventoperiodoformejecu=evento).exclude(excluir_persona)
                                    for rub in rubro:
                                        idrubrosunemieliminar.append(rub.id)
                            else:
                                if Rubro.objects.filter(cancelado=False, status=True, persona=inscrito.participante,
                                                    capeventoperiodoformejecu=evento).exists():
                                    rubro = Rubro.objects.filter(cancelado=False, status=True, persona=inscrito.participante,
                                                              capeventoperiodoformejecu=evento)
                                    for rub in rubro:
                                        idrubrosunemieliminar.append(rub.id)
                rubrosunemi_aeliminar = Rubro.objects.filter(id__in=idrubrosunemieliminar)
                # Eliminar y migrar a epunemi
                result_migrar = eliminar_y_migrar_rubro_deunemi_aepunemi_formacionejecutiva(request, rubrosunemi_aeliminar, action='borrar_rubro', procesomasivo=True)
                if result_migrar['result'] == "ok":
                    mensajemigrar = result_migrar['mensaje']
                    result_rubrosunemi = mensajemigrar['total_rubrosunemi']
                    result_rubrosepunemi = mensajemigrar['total_rubrosepunemi']
                    resultrubpagados_noeli = mensajemigrar['rubrospagados_noeliminados']
                    if result_rubrosunemi == 0 and result_rubrosepunemi == 0:
                        if resultrubpagados_noeli:
                            mensajeeliminados = f'No se eliminó ningún rubro. Por los siguientes motivos: {resultrubpagados_noeli}.'
                        else:
                            mensajeeliminados = f'No se eliminó ningún rubro.'
                    else:
                        if resultrubpagados_noeli:
                            mensajeeliminados = f"Se han eliminado {result_rubrosunemi} rubros y se han migrado(eliminado) {result_rubrosepunemi} rubros a EPUNEMI exitosamente. No se eliminaron o migraron: {resultrubpagados_noeli}."
                            # mensajeeliminados = f"Se han migrado (eliminado) {result_rubrosepunemi} rubros exitosamente a EPUNEMI."
                        else:
                            mensajeeliminados = f"Se han eliminado {result_rubrosunemi} rubros y se han migrado(eliminado) {result_rubrosepunemi} rubros a EPUNEMI exitosamente."
                    res_js = {"error": False, "message": mensajeeliminados}
                    messages.success(request, mensajeeliminados)

                else:
                    raise NameError(result_migrar['mensaje'])
                # Eliminar y migrar a epunemi
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'message': msg_err}
            return JsonResponse(res_js, safe=False)

        elif action == 'addgeneralmodel':
            try:
                form = ModeloEvaluativoGeneralFormEjecutiva(request.POST)
                if CapModeloEvaluativoGeneralFormaEjecutiva.objects.values('id').filter(status=True,modelo_id=int(request.POST['modelo'])):
                    raise NameError("Modelo Evaluativo ya existe.")
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                filtro = CapModeloEvaluativoGeneralFormaEjecutiva(
                    modelo=form.cleaned_data['modelo'],
                    orden=form.cleaned_data['orden']
                )
                filtro.save(request)
                log(u'Adiciono Modelo Evaluativo a la configuración fromacion ejecutiva: %s' % filtro, request, "add")
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'editgeneralmodel':
            try:
                id = encrypt(request.POST['id'])
                filtro = CapModeloEvaluativoGeneralFormaEjecutiva.objects.get(status=True, id=int(id))
                form = ModeloEvaluativoGeneralFormEjecutiva(request.POST)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                filtro.orden = form.cleaned_data['orden']
                filtro.save(request)
                log(u'Modificó Modelo Evaluativo de la configuración formación ejecutiva: %s' % filtro, request, "edit")
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'delgeneralmodel':
            try:
                id = encrypt(request.POST['id'])
                evento = CapModeloEvaluativoGeneralFormaEjecutiva.objects.get(status=True, id=int(id))
                evento.status = False
                evento.save(request)
                log(u"Eliminó Modelo Evaluativo de la configuración formación ejecutiva: %s"%(evento.__str__()),request,'del')
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'createcoursemoodle':
            try:
                instructor = InstructorFormaEjecutiva.objects.get(pk=int(encrypt(request.POST['id'])))
                modeloNotas = instructor.capnotaformaejecutiva_set.values('id').filter(status=True).count()
                if modeloNotas > 0:
                    curso = instructor.capeventoperiodo
                    if curso.costo:
                        listadocodigo = curso.list_inscritos_costo().values_list('participante__idusermoodleposgrado', flat=True)
                    else:
                        listadocodigo = curso.list_inscritos_sin_costo().values_list('participante__idusermoodleposgrado', flat=True)


                    cursorpos = connections['moodle_pos'].cursor()
                    sql = """SELECT DISTINCT  ARRAY_TO_STRING(array_agg(us1.id),',')                                      
                             FROM mooc_role_assignments asi
                            INNER JOIN MOOC_CONTEXT CON ON asi.CONTEXTID=CON.ID
                            INNER JOIN mooc_user us1 ON us1.id=asi.userid
                            AND ASI.ROLEID=%s
                            AND CON.INSTANCEID=%s
                            AND us1.id in %s""" % (10, instructor.idcursomoodle, tuple(listadocodigo) if not len(listadocodigo) ==1 else f'({listadocodigo.first()})')
                    cursorpos.execute(sql)
                    listadosmoodle = []
                    row = cursorpos.fetchall()
                    if instructor.idcursomoodle:
                        if row[0][0]:
                            listadosmoodle = row[0][0].split(",")
                    listac = None
                    if curso.costo:
                        listacurso = curso.list_inscritos_costo()
                    else:
                        listacurso = curso.list_inscritos_sin_costo()

                    listac = listacurso.values('id', 'participante__id',
                                                               'participante__apellido1',
                                                               'participante__apellido2',
                                                               'participante__nombres').filter(
                    participante__status=True, status=True).exclude(
                    participante__idusermoodleposgrado__in=listadosmoodle).order_by(
                    'participante__apellido1',
                    'participante__apellido2',
                    'participante__nombres')
                    cursorpos.close()
                    res_js = {"error": False, "cantidad": len(listac),"listacurso": list(listac)}
                else:
                    raise NameError("Asigne un modelo evaluativo al evento")
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'message': msg_err}
            return JsonResponse(res_js)

        elif action == 'confimodelogeneral':
            try:
                filtro = CapModeloEvaluativoGeneralFormaEjecutiva.objects.filter(status=True).order_by('orden')
                instructor = InstructorFormaEjecutiva.objects.get(pk=int(request.POST['id']))
                for f in filtro:
                    if not CapNotaFormaEjecutiva.objects.filter(status=True, modelo=f.modelo,instructor_id=instructor.pk).exists():
                        modelonota = CapNotaFormaEjecutiva(modelo=f.modelo,
                                                 fecha=datetime.now().date(),
                                                 instructor_id=instructor.pk)
                        modelonota.save(request)
                        log(u'Adiciono Modelo Evaluativo Instructor Formación Ejecutiva: %s' % modelonota, request, "add")
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'delmodelonota':
            try:
                id = encrypt(request.POST['id'])
                modelonota = CapNotaFormaEjecutiva.objects.get(pk=int(id))
                log(u'Elimino modelo en nota de Capacitación Formación Ejecutiva: %s - [%s]' % (modelonota, modelonota.id), request,
                    "del")
                modelonota.status=False
                modelonota.save(request)
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'calificar':
            try:
                id = encrypt(request.POST['id'])
                tarea = CapNotaFormaEjecutiva.objects.get(pk=int(id), status=True)
                if not tarea.instructor.capeventoperiodo.exiten_inscritos():
                    raise NameError("No puede continuar, porque no existen inscritos.")
                for inscrito in tarea.instructor.capeventoperiodo.inscritos():
                    if not inscrito.capdetallenotaformaejecutiva_set.values('id').filter(status=True, cabeceranota=tarea,
                                                                  inscrito=inscrito).exists():
                        detalle = CapDetalleNotaFormaEjecutiva(cabeceranota=tarea, inscrito=inscrito)
                        detalle.save(request)
                        log(u'Adicionado inscrito para calificar tarea de capacitación Formación Ejecutiva: %s - [%s]' % (
                            detalle, detalle.id), request, "add")
                res_js = {'result': True}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': False, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'updatenota':
            try:
                id = encrypt(request.POST['id'])
                detalle = CapDetalleNotaFormaEjecutiva.objects.get(pk=int(id))
                nota = float(request.POST['vc'])
                cupoanterior = detalle.nota
                detalle.nota = nota
                detalle.save(request)
                log(u'Actualizo nota en tarea de capacitacion Formación Ejecutiva: %s cupo anterior: %s cupo actual: %s' % (
                    detalle, str(cupoanterior), str(detalle.nota)), request, "edit")
                if 'idl' in request.POST:
                    idl = encrypt(request.POST['idl'])
                    capinscritoipec = CapaEventoInscritoFormaEjecutiva.objects.get(pk=int(idl))
                    nofinal = capinscritoipec.nota_total_evento_porinstructor(
                        detalle.cabeceranota.instructor.capeventoperiodo.id, detalle.cabeceranota.instructor.pk)
                    res_js = {'result': True, 'valor': detalle.nota, 'nofinal': nofinal}
                else:
                    res_js = {'result': True, 'valor': detalle.nota}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': False, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'observacion':
            try:
                id = encrypt(request.POST['id'])
                detalle = CapDetalleNotaFormaEjecutiva.objects.get(pk=int(id))
                detalle.observacion = request.POST['valor']
                detalle.save(request)
                log(u'Actualizo observacion en tarea de capacitacion Formación Ejecutiva: %s ' % detalle.observacion, request, "edit")
                res_js = {'result': True}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': False, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'observacioninscrito':
            try:
                id = encrypt(request.POST['id'])
                detalle = CapaEventoInscritoFormaEjecutiva.objects.get(pk=int(id))
                detalle.observacion = request.POST['valor']
                detalle.save(request)
                log(u'Actualizo observacion en tarea de capacitacion Formación Ejecutiva: %s ' % detalle.observacion, request, "edit")
                res_js = {'result': True}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': False, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'calificageneral':
            try:
                id = encrypt(request.POST['id'])
                instructor = InstructorFormaEjecutiva.objects.get(pk=int(id), status=True)
                if not instructor.capeventoperiodo.exiten_inscritos():
                    raise NameError("No puede continuar, porque no existen inscritos.")
                for inscrito in instructor.capeventoperiodo.inscritos():
                    for tarea in instructor.capnotaformaejecutiva_set.filter(status=True):
                        if not inscrito.capdetallenotaformaejecutiva_set.values('id').filter(status=True, cabeceranota=tarea,
                                                                      inscrito=inscrito).exists():
                            detalle = CapDetalleNotaFormaEjecutiva(cabeceranota=tarea, inscrito=inscrito)
                            detalle.save(request)
                            log(u'Adicionado inscrito para calificar tarea de capacitación Formación Ejecutiva: %s - [%s]' % (
                            detalle, detalle.id), request, "add")
                res_js = {'result': True}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': False, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'exportarinscrito':
            try:
                contador = int(request.POST['contador'])
                inscrito = request.POST['inscrito']
                instructor = InstructorFormaEjecutiva.objects.get(status=True, pk=encrypt(request.POST['idinstructor']))
                grupo = instructor.capeventoperiodo
                codigointegrante = grupo.capaeventoinscritoformaejecutiva_set.get(pk=inscrito, status=True)
                codigointegrante.encursomoodle = True
                codigointegrante.save(request)
                instructor.crear_curso_moodle(inscrito, contador, formeje=True)
                time.sleep(3)
                res_js = {'result': True}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': False, 'message': msg_err}
            return JsonResponse(res_js)

        elif action == 'actualizar_modelo_moodle_pos':
            try:
                id = encrypt(request.POST['id'])
                instructor = InstructorFormaEjecutiva.objects.get(pk=int(id), status=True)
                modeloNotas = instructor.capnotaformaejecutiva_set.filter(status=True).count()
                if modeloNotas > 0:
                    if instructor.idcursomoodle != 0:
                        modelo = instructor.crear_actualizar_categoria_notas_curso()
                        if modelo:
                            res_js = {'result': True}
                        else:
                            raise NameError(u"Modelo evaluativo no actualizado")
                    else:
                        raise NameError(u"Instructor no cuenta con curso moodle")
                else:
                    raise NameError(u"Por favor, asigne un modelo evaluativo al evento")
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': False, 'message': msg_err}
            return JsonResponse(res_js)

        elif action == 'recordpayment':
            try:
                id = encrypt(request.POST['id'])
                data['filtro'] = filtro = CapaEventoInscritoFormaEjecutiva.objects.get(status=True, id=int(id))
                form = PagoFormacionEjecutivaForm(request.POST,request.FILES)
                if not form.is_valid():
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")
                archivo = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if not newfile._name.split('.')[-1] in ['pdf','png','jpg','jpeg']:
                        raise NameError(f"Suba un formato de archivo valido (pdf,png,jpg,jpeg)")
                    if newfile.size > 10485760:
                        raise NameError(u"El tamaño del fichero excede los 10MB")
                    newfile._name = generar_nombre("comprobante_pago", newfile._name)
                    archivo=newfile
                if filtro.regpago():
                    pago = filtro.regpago().first()
                    pago.observacion = form.cleaned_data['observacion']
                    pago.inscripcionevento=filtro
                    pago.valor = form.cleaned_data['valor']
                    pago.fpago = form.cleaned_data['fpago']
                    pago.banco = form.cleaned_data['banco']
                    pago.tipocomprobante = form.cleaned_data['tipocomprobante']
                    pago.save(request)
                    log(u"Editó pago al inscrito. %s - %s"%(filtro.__str__(),pago.__str__()),request,'add')
                else:
                    pago = PagoFormacionEjecutiva(
                        inscripcionevento=filtro,
                        observacion=form.cleaned_data['observacion'],
                        valor=form.cleaned_data['valor'],
                        fpago=form.cleaned_data['fpago'],
                        banco=form.cleaned_data['banco'],
                        tipocomprobante=form.cleaned_data['tipocomprobante'],
                    )
                    pago.save(request)
                    log(u"Agrego pago al inscrito. %s - %s"%(filtro.__str__(),pago.__str__()),request,'add')
                if archivo:
                    pago.archivo=archivo
                    pago.save(request)
                # log(u'Actualizo observacion en tarea de capacitacion Formación Ejecutiva: %s ' % detalle.observacion, request, "edit")
                res_js = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': True, 'message': msg_err}
            return JsonResponse(res_js)

        elif action == 'gencertificadmasivoasistencia':
            try:
                id = request.POST.get('id', None)
                template_asistencia_pdf = "adm_ejecuform/certificadoasistencia_pdf_2.html"
                capevento = CapacitaEventoFormacionEjecutiva.objects.get(status=True,id=int(encrypt(id)))
                inscritos = CapaEventoInscritoFormaEjecutiva.objects.filter(status=True,capeventoperiodo=capevento).order_by('-id')
                data['elabora_persona'] = persona
                for ins in inscritos:
                    data['evento'] = evento = ins.capeventoperiodo
                    data['logoaval'] = ins.capeventoperiodo.archivo
                    data['inscrito'] = ins
                    mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                    data['fecha'] = u"Milagro, %s de %s del %s" % (datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
                    data['listado_contenido'] = listado = evento.contenido.split("\n") if evento.contenido else []
                    qrname = 'qr_certificado_' + str(ins.id)
                    result = generar_certificado_porinscripcion_save(ins=ins, data=data, evento=capevento,
                                                                     qrname=qrname, listado=listado,
                                                                     template_asistencia=template_asistencia_pdf)

                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err_ = f'{ex} ({sys.exc_info()[-1].tb_lineno})'
                res_js = {'error':True, 'message':err_}
            return JsonResponse(res_js)

        elif action == 'generarcertificadoasistencia':
            try:
                id = request.POST.get('id', None)
                template_asistencia_pdf = "adm_ejecuform/certificadoasistencia_pdf_2.html"
                ins = CapaEventoInscritoFormaEjecutiva.objects.get(status=True,id=int(encrypt(id)))
                capevento = ins.capeventoperiodo
                data['elabora_persona'] = persona
                data['evento'] = evento = ins.capeventoperiodo
                data['logoaval'] = ins.capeventoperiodo.archivo
                data['inscrito'] = ins
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                       "octubre", "noviembre", "diciembre"]
                data['fecha'] = u"Milagro, %s de %s del %s" % (
                datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
                data['listado_contenido'] = listado = evento.contenido.split("\n") if evento.contenido else []
                qrname = 'qr_certificado_' + str(ins.id)
                result = generar_certificado_porinscripcion_save(ins=ins, data=data, evento=capevento,
                                                                         qrname=qrname, listado=listado,
                                                                         template_asistencia=template_asistencia_pdf)
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err_ = f'{ex} ({sys.exc_info()[-1].tb_lineno})'
                res_js = {'error': True, 'message': err_}
            return JsonResponse(res_js)

        elif action == 'notificarporemail':
            try:
                id = request.POST.get('id', None)
                capevento = CapacitaEventoFormacionEjecutiva.objects.get(status=True, id=int(encrypt(id)))
                inscritos = CapaEventoInscritoFormaEjecutiva.objects.filter(status=True, capeventoperiodo=capevento, rutapdf__isnull=False).exclude(rutapdf='').order_by('-id')
                for ins in inscritos:
                    correoinscrito = ins.participante.emailpersonal()
                    asunto = u"CERTIFICADO - " + ins.capeventoperiodo.capevento.nombre
                    send_html_mail(asunto, "emails/notificar_certificado_formacion.html",
                                   {'sistema': request.session['nombresistema'],'titulos_name':'Formación Ejecutiva', 'inscrito': ins,},
                                   correoinscrito,
                                   [], [ins.rutapdf],
                                   cuenta=CUENTAS_CORREOS[0][1])
                    ins.emailnotificado = True
                    ins.save(request)
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err_ = f'{ex} ({sys.exc_info()[-1].tb_lineno})'
                res_js = {'error': True, 'message': err_}
            return JsonResponse(res_js)

        elif action == 'notificarporemailind':
            try:
                id = request.POST.get('id', None)
                inscritos = CapaEventoInscritoFormaEjecutiva.objects.get(status=True,id=int(encrypt(id)))
                capevento = inscritos.capeventoperiodo
                correoinscrito = inscritos.participante.emailpersonal()
                asunto = u"CERTIFICADO - " + inscritos.capeventoperiodo.capevento.nombre
                send_html_mail(asunto, "emails/notificar_certificado_formacion.html",
                               {'sistema': request.session['nombresistema'],'titulos_name':'Formación Ejecutiva', 'inscrito': inscritos,},
                               correoinscrito,
                               [], [inscritos.rutapdf],
                               cuenta=CUENTAS_CORREOS[0][1])
                inscritos.emailnotificado = True
                inscritos.save(request)
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err_ = f'{ex} ({sys.exc_info()[-1].tb_lineno})'
                res_js = {'error': True, 'message': err_}
            return JsonResponse(res_js)

        elif action == 'notasmoodle':
            try:
                instructor = InstructorFormaEjecutiva.objects.get(pk=request.POST['id'], status=True)
                evento = instructor.capeventoperiodo
                for alumno in evento.list_inscritos_sin_costo():
                    # Extraer datos de moodle
                    for notasmooc in instructor.notas_de_moodle(alumno.participante):
                        if type(notasmooc[0]) is Decimal:
                            if CapNotaFormaEjecutiva.objects.filter(status=True, instructor=instructor,
                                                                    modelo__nombre=notasmooc[1].upper()).exists():
                                modeloevaluativo = CapNotaFormaEjecutiva.objects.filter(status=True,
                                                                                        instructor=instructor,
                                                                                        modelo__nombre=notasmooc[
                                                                                            1].upper())
                                notaanterior = 0
                                if CapDetalleNotaFormaEjecutiva.objects.filter(status=True, cabeceranota__status=True,
                                                                               cabeceranota_id=modeloevaluativo[0],
                                                                               inscrito=alumno,
                                                                               cabeceranota__instructor__capeventoperiodo=instructor.capeventoperiodo,
                                                                               cabeceranota__instructor=instructor).exists():
                                    detalle = CapDetalleNotaFormaEjecutiva.objects.filter(status=True,
                                                                                          cabeceranota__status=True,
                                                                                          cabeceranota_id=
                                                                                          modeloevaluativo[0],
                                                                                          inscrito=alumno,
                                                                                          cabeceranota__instructor__capeventoperiodo=instructor.capeventoperiodo,
                                                                                          cabeceranota__instructor=instructor).order_by(
                                        '-id').first()
                                    notaanterior = detalle.nota
                                    detalle.nota = float(notasmooc[0])
                                else:
                                    detalle = CapDetalleNotaFormaEjecutiva(cabeceranota=modeloevaluativo[0],
                                                                           inscrito=alumno,
                                                                           observacion="IMPORTACIÓN AUTOMÁTICA",
                                                                           nota=float(notasmooc[0]))
                                detalle.save()
                                log(u'Actualizo nota en tarea de capacitacion IPEC: %s nota anterior: %s nota actualizada: %s del modelo de evaluativo %s' % (
                                detalle, str(notaanterior), str(detalle.nota), detalle.cabeceranota.modelo), request,
                                    "edit")
                                alumno.nofinal = detalle.inscrito.nota_total_evento_porinstructor(
                                    instructor.capeventoperiodo.id, instructor.pk)
            except Exception as ex:
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': False, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'extraernotasmoodle':
            try:
                instructor = InstructorFormaEjecutiva.objects.get(pk=request.POST['id'], status=True)
                evento = instructor.capeventoperiodo
                for alumno in evento.list_inscritos_sin_costo():
                    # Extraer datos de moodle
                    for notasmooc in instructor.notas_de_moodle(alumno.participante):
                        if type(notasmooc[0]) is Decimal:
                            if CapNotaFormaEjecutiva.objects.filter(status=True, instructor=instructor,
                                                                    modelo__nombre=notasmooc[1].upper()).exists():
                                modeloevaluativo = CapNotaFormaEjecutiva.objects.filter(status=True,
                                                                                        instructor=instructor,
                                                                                        modelo__nombre=notasmooc[
                                                                                            1].upper())
                                notaanterior = 0
                                if CapDetalleNotaFormaEjecutiva.objects.filter(status=True, cabeceranota__status=True,
                                                                               cabeceranota_id=modeloevaluativo[0],
                                                                               inscrito=alumno,
                                                                               cabeceranota__instructor__capeventoperiodo=instructor.capeventoperiodo,
                                                                               cabeceranota__instructor=instructor).exists():
                                    detalle = CapDetalleNotaFormaEjecutiva.objects.filter(status=True,
                                                                                cabeceranota__status=True,
                                                                                cabeceranota_id=modeloevaluativo[0],
                                                                                inscrito=alumno,
                                                                                cabeceranota__instructor__capeventoperiodo=instructor.capeventoperiodo,
                                                                                cabeceranota__instructor=instructor).order_by(
                                        '-id').first()
                                    notaanterior = detalle.nota
                                    detalle.nota = float(notasmooc[0])
                                else:
                                    detalle = CapDetalleNotaFormaEjecutiva(cabeceranota=modeloevaluativo[0],
                                                                           inscrito=alumno,
                                                                           observacion="IMPORTACIÓN AUTOMÁTICA",
                                                                           nota=float(notasmooc[0]))
                                detalle.save()
                                log(u'Actualizo nota en tarea de cursos posgrados: %s nota anterior: %s nota actualizada: %s del modelo de evaluativo %s' % (
                                detalle, str(notaanterior), str(detalle.nota), detalle.cabeceranota.modelo), request,
                                    "edit")
                                alumno.nofinal = detalle.inscrito.nota_total_evento_porinstructor(
                                    instructor.capeventoperiodo.id, instructor.pk)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': False, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'resetearusu':
            try:
                from moodle.models import UserAuth
                inscripcion = CapaEventoInscritoFormaEjecutiva.objects.get(pk=request.POST['id'])
                pers = inscripcion.participante
                usuario = pers.usuario
                password = pers.identificacion()
                usuario.set_password(password)
                usuario.save()
                pers.clave_cambiada()

                if not UserAuth.objects.filter(usuario=usuario).exists():
                    usermoodle = UserAuth(usuario=usuario)
                    usermoodle.set_data()
                    usermoodle.set_password(password)
                    usermoodle.save()
                else:
                    usermoodle = UserAuth.objects.filter(usuario=usuario)[0]
                    usermoodle.set_data()
                    usermoodle.set_password(password)
                    usermoodle.save()
                log(u'Reseteo clave de inscrito: %s' % inscripcion, request, "add")
            except Exception as ex:
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': False, 'mensaje': msg_err}
            return JsonResponse(res_js)


        return HttpResponseRedirect('/adm_formejecuperiodo')
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            validaciones(data, persona)
            if action == 'addperiodo':
                try:
                    data['title'] = u'Agregar periodo'
                    form = PeriodoFormaEjecutivaForm()
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result':True,'data':template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result':False,'mensaje':msg_err}
                return JsonResponse(res_js)

            elif action == 'inscritoaplicagratuidad':
                try:
                    idinscrito = request.GET['idinscrito']
                    ideventoperiodo = request.GET['ideventoperiodo']
                    estadogratuidad = str(request.GET['estadogratuidad'])
                    identificadorgratuidad = 0
                    actualizar_aplicagratuidad = CapaEventoInscritoFormaEjecutiva.objects.get(id=idinscrito,
                                                                                              capeventoperiodo_id=ideventoperiodo)
                    if estadogratuidad == 'true':
                        actualizar_aplicagratuidad.aplicagratuidad = 1
                        identificadorgratuidad = 1
                    if estadogratuidad == 'false':
                        actualizar_aplicagratuidad.aplicagratuidad = 2
                    actualizar_aplicagratuidad.save(request)
                    log(u'Actualiza aplica gratuidad %s - %s' % (persona, actualizar_aplicagratuidad), request, "edit")
                    return JsonResponse({"result": True, "identificadorgratuidad": identificadorgratuidad})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u'Error al momento de actualizar'})

            elif action == 'busquedaconcargo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 2:
                        distributivo = Persona.objects.filter(
                            Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1]), status=True).distinct()[:20]
                    else:
                        distributivo = Persona.objects.filter(
                            Q(nombres__contains=q) | Q(apellido1__contains=q) | Q(
                                apellido2__contains=q) | Q(cedula__contains=q)).filter(status=True)[:20]
                    data = {"result": "ok", "results": [{"id": x.id, "name": (u'%s - %s' % (
                        x.cedula, x.nombre_completo_inverso()))} for x in
                                                        distributivo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'planificacion':
                try:
                    id = encrypt(request.GET['id'])
                    request.session['viewactive'] = 1
                    data['title'] = u'Planificación de eventos Formación Ejecutiva'
                    data['perd'] = perd = PeriodoFormaEjecutiva.objects.get(status=True,id=int(id))
                    filtro, search, url_vars = Q(status=True), request.GET.get('s', None), f'&action={action}&id={request.GET["id"]}'

                    if search:
                        url_vars += '&s=' + search
                        filtro = filtro & Q(Q(nombre__icontains=search))
                        data['search'] = search
                    query = CapacitaEventoFormacionEjecutiva.objects.filter(filtro).filter(periodo=perd)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['meses'] = MESES_CHOICES
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    return render(request, "adm_ejecuform/viewperiodo.html", data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    print(msg_err)
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?info={msg_err}')

            elif action == 'addeventocapacitacion':
                try:
                    id = encrypt(request.GET['id'])
                    data['title'] = u"Agregar Evento"
                    data['periodoevento']=periodoevento = PeriodoFormaEjecutiva.objects.get(status=True, id=int(id))
                    configuracion = ConfiguracionFormaEjecutiva.objects.all()
                    form = CapaEventoFormaEjecutivaForm(initial={
                        'periodo': periodoevento,
                        'minasistencia': configuracion[
                            0].minasistencia if configuracion.exists() else 0,
                        'minnota': configuracion[
                            0].minnota if configuracion.exists() else 0,
                        'aprobado2': (u'%s - %s - %s' % (
                            configuracion[0].aprobado2.cedula,
                            configuracion[0].aprobado2.nombre_completo_inverso(),
                            configuracion[
                                0].denominacionaprobado2)) if configuracion.exists() else '',
                        'aprobado3': (u'%s - %s - %s' % (
                            configuracion[0].aprobado3.cedula,
                            configuracion[0].aprobado3.nombre_completo_inverso(),
                            configuracion[
                                0].denominacionaprobado3)) if configuracion.exists() else ''

                    })
                    form.editar_grupo()
                    # form.edit_persona_firma_certificado_1(26497,'DIRECTOR DE POSGRADO')
                    # form.edit_persona_firma_certificado_2(37789,'VICERRECTOR DE INVESTIGACION Y POSGRADO')

                    data['form'] = form
                    return render(request,"adm_ejecuform/formcapacievento.html",data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    print(msg_err)
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?info={msg_err}')

            elif action == 'editeventocapacitacion':
                try:
                    id = encrypt(request.GET['id'])
                    data['title'] = u'Editar Evento'
                    data['eventocap'] = evento = CapacitaEventoFormacionEjecutiva.objects.get(pk=int(id))
                    data['periodoevento'] = evento.periodo
                    if evento.tiporubro_id in [None, '', 0]:
                        data['idtipootrorubro'] = idtipootrorubro = 0
                    else:
                        data['idtipootrorubro'] = idtipootrorubro = evento.tiporubro_id
                    responsable = Administrativo.objects.get(persona=evento.responsable)
                    form = CapaEventoFormaEjecutivaForm(initial={'periodo': evento.periodo,
                                                                 'capevento': evento.capevento,
                                                                 'tipootrorubro': idtipootrorubro,
                                                                 'horas': evento.horas,
                                                                 'costo': evento.costo,
                                                                 'costoexterno': evento.costoexterno,
                                                                 'objetivo': evento.objetivo,
                                                                 'observacion': evento.observacion,
                                                                 'minasistencia': evento.minasistencia,
                                                                 'minnota': evento.minnota,
                                                                 'fechainicio': evento.fechainicio,
                                                                 'fechafin': evento.fechafin,
                                                                 'fechainiinscripcion': evento.fechainicioinscripcion,
                                                                 'fechafininscripcion': evento.fechafininscripcion,
                                                                 'tipoparticipacion': evento.tipoparticipacion,
                                                                 'contextocapacitacion': evento.contextocapacitacion,
                                                                 'modalidad': evento.modalidad,
                                                                 'tipocertificacion': evento.tipocertificacion,
                                                                 'tipocapacitacion': evento.tipocapacitacion,
                                                                 'visualizar': evento.visualizar,
                                                                 'publicarinscripcion': evento.publicarinscripcion,
                                                                 'enfoque': evento.enfoque,
                                                                 'cupo': evento.cupo,
                                                                 'contenido': evento.contenido,
                                                                 'modeloevaludativoindividual': evento.modeloevaludativoindividual,
                                                                 'mes': evento.mes,
                                                                 'responsable': responsable.id,
                                                                 'fechacertificado': evento.fechacertificado,
                                                                 'fechamaxpago': evento.fechamaxpago,
                                                                 'areaconocimiento': evento.areaconocimiento,
                                                                 'aprobado2': (
                                                                         u'%s - %s - %s' % (evento.aprobado2.cedula,
                                                                                            evento.aprobado2.nombre_completo_inverso(),
                                                                                            evento.denominacionaprobado2)) if evento.aprobado2 else '',
                                                                 'aprobado3': (
                                                                         u'%s - %s - %s' % (evento.aprobado3.cedula,
                                                                                            evento.aprobado3.nombre_completo_inverso(),
                                                                                            evento.denominacionaprobado3)) if evento.aprobado3 else '',
                                                                 'aula': evento.aula,
                                                                 'envionotaemail': evento.envionotaemail,
                                                                 'rubroepunemi':evento.rubroepunemi})
                    form.editar_grupo()
                    form.editar_responsable(responsable)
                    # form.edit_persona_firma_certificado_1(evento.firma_certificado_1.id if evento.firma_certificado_1 else None,evento.cargo_firma_certificado_1 if evento.cargo_firma_certificado_1 else None)
                    # form.edit_persona_firma_certificado_2(evento.firma_certificado_1.id if evento.firma_certificado_1 else None,evento.cargo_firma_certificado_1  if evento.cargo_firma_certificado_1 else None)

                    data['form'] = form
                    data['logoaval'] = evento.archivo
                    data['banner'] = evento.banner
                    return render(request, "adm_ejecuform/formcapacievento.html", data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    print(msg_err)
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?info={msg_err}')

            elif action == 'configuracion':
                try:
                    data['title'] = u'Configuración'
                    configuracion = ConfiguracionFormaEjecutiva.objects.filter()
                    if configuracion.exists():
                        data['filtro'] = configuracion[0]
                        try:
                            data['aprobado2']=aprobado2 = DistributivoPersona.objects.filter(persona=configuracion[0].aprobado2,
                                                                           denominacionpuesto=configuracion[
                                                                               0].denominacionaprobado2)
                            data['aprobado3']=aprobado3 = DistributivoPersona.objects.filter(persona=configuracion[0].aprobado3,
                                                                           denominacionpuesto=configuracion[
                                                                               0].denominacionaprobado3)
                            form = ConfiguracionFormaEjecutivaForm(initial={'minasistencia': configuracion[0].minasistencia,
                                                                     'minnota': configuracion[0].minnota,
                                                                     'aprobado2': aprobado2[
                                                                         0].id if aprobado2.exists() else 0,
                                                                     'aprobado3': aprobado3[
                                                                         0].id if aprobado3.exists() else 0})
                            form.editar(aprobado2, aprobado3)
                        except Exception as ex:
                            form = ConfiguracionFormaEjecutivaForm(initial={'minasistencia': configuracion[0].minasistencia,
                                                                     'minnota': configuracion[0].minnota})
                    else:
                        form = ConfiguracionFormaEjecutivaForm()
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result': True, 'data': template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'mensaje': msg_err}
                return JsonResponse(res_js)

            elif action == 'editperiodo':
                try:
                    id = encrypt(request.GET['id'])
                    data['filtro']=filtro=PeriodoFormaEjecutiva.objects.get(status=True,id=int(id))
                    data['title'] = u'Editar periodo'
                    form = PeriodoFormaEjecutivaForm(initial=model_to_dict(filtro))
                    form.editar()
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result':True,'data':template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result':False,'mensaje':msg_err}
                return JsonResponse(res_js)

            elif action == 'eventos':
                try:
                    request.session['viewactive'] = 2
                    data['title'] = u'Eventos Formación Ejecutiva'
                    filtro, search, url_vars = Q(status=True), request.GET.get('s', None), f'&action={action}'

                    if search:
                        url_vars += '&s=' + search
                        filtro = filtro & Q(Q(nombre__icontains=search))
                        data['search'] = search
                    query = EventoFormaEjecutiva.objects.filter(filtro)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    return render(request, "adm_ejecuform/vieweventos.html", data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    print(msg_err)
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?info={msg_err}')

            elif action == 'addevento':
                try:
                    data['title'] = u'Agregar evento'
                    form = EventoFormaEjecutivaForm()
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result':True,'data':template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result':False,'mensaje':msg_err}
                return JsonResponse(res_js)

            elif action == 'editevento':
                try:
                    id = encrypt(request.GET['id'])
                    data['filtro']=filtro=EventoFormaEjecutiva.objects.get(status=True,id=int(id))
                    data['title'] = u'Editar Evento'
                    form = EventoFormaEjecutivaForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result':True,'data':template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result':False,'mensaje':msg_err}
                return JsonResponse(res_js)

            elif action == 'enfoques':
                try:
                    request.session['viewactive'] = 3
                    data['title'] = u'Enfoque Formación Ejecutiva'
                    filtro, search, url_vars = Q(status=True), request.GET.get('s', None), f'&action={action}'

                    if search:
                        url_vars += '&s=' + search
                        filtro = filtro & Q(Q(nombre__icontains=search))
                        data['search'] = search
                    query = EnfoqueFormaEjecutiva.objects.filter(filtro)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    return render(request, "adm_ejecuform/viewenfoques.html", data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    print(msg_err)
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?info={msg_err}')

            elif action == 'addenfoque':
                try:
                    data['title'] = u'Agregar enfoque'
                    form = EnfoqueFormaEjecutivaForm()
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result':True,'data':template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result':False,'mensaje':msg_err}
                return JsonResponse(res_js)

            elif action == 'editenfoque':
                try:
                    id = encrypt(request.GET['id'])
                    data['filtro']=filtro=EnfoqueFormaEjecutiva.objects.get(status=True,id=int(id))
                    data['title'] = u'Editar Evento'
                    form = EnfoqueFormaEjecutivaForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result':True,'data':template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result':False,'mensaje':msg_err}
                return JsonResponse(res_js)

            elif action == 'turnos':
                try:
                    request.session['viewactive'] = 4
                    data['title'] = u'Turnos Formación Ejecutiva'
                    filtro, search, url_vars = Q(status=True), request.GET.get('s', None), f'&action={action}'

                    if search:
                        url_vars += '&s=' + search
                        filtro = filtro & Q(Q(nombre__icontains=search))
                        data['search'] = search
                    query = TurnoFormaEjecutiva.objects.filter(filtro)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    return render(request, "adm_ejecuform/viewturnos.html", data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    print(msg_err)
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?info={msg_err}')

            elif action == 'addturno':
                try:
                    data['title'] = u'Agregar enfoque'
                    form = TurnoFormaEjecutivaForm(
                        initial={
                            'turno':int((TurnoFormaEjecutiva.objects.filter(status=True).aggregate(
                        Max('turno'))['turno__max']) + 1) if TurnoFormaEjecutiva.objects.filter(status=True).exists() else 1
                        }
                    )
                    data['form'] = form
                    form.editar_horas()
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result':True,'data':template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result':False,'mensaje':msg_err}
                return JsonResponse(res_js)

            elif action == 'editturno':
                try:
                    id = encrypt(request.GET['id'])
                    data['filtro']=filtro=TurnoFormaEjecutiva.objects.get(status=True,id=int(id))
                    data['title'] = u'Editar Evento'
                    form = TurnoFormaEjecutivaForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    form.editar()
                    form.editar_horas()
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result':True,'data':template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result':False,'mensaje':msg_err}
                return JsonResponse(res_js)

            elif action == 'modelo':
                try:
                    request.session['viewactive'] = 5
                    data['title'] = u'Modelo Evaluativo Formación Ejecutiva'
                    filtro, search, url_vars = Q(status=True), request.GET.get('s', None), f'&action={action}'

                    if search:
                        url_vars += '&s=' + search
                        filtro = filtro & Q(Q(nombre__icontains=search))
                        data['search'] = search
                    query = ModeloEvaluativoFormaEjecutiva.objects.filter(filtro)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    return render(request, "adm_ejecuform/viewmodelo.html", data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    print(msg_err)
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?info={msg_err}')

            elif action == 'addmodelo':
                try:
                    data['title'] = u'Agregar Modelo'
                    form = ModeloEvaluativoFormaEjecutivaForm()
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result':True,'data':template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result':False,'mensaje':msg_err}
                return JsonResponse(res_js)

            elif action == 'editmodelo':
                try:
                    id = encrypt(request.GET['id'])
                    data['filtro']=filtro=ModeloEvaluativoFormaEjecutiva.objects.get(status=True,id=int(id))
                    data['title'] = u'Editar Modelo'
                    form = ModeloEvaluativoFormaEjecutivaForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result':True,'data':template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result':False,'mensaje':msg_err}
                return JsonResponse(res_js)
            # INSTRUCTOR
            elif action == 'busquedainstructor':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 2:
                        persona = Persona.objects.filter(apellido1__icontains=s[0], apellido2__icontains=s[1],
                                                         real=True).exclude(pk__in=lista).distinct()[:15]
                    else:
                        persona = Persona.objects.filter(Q(real=True) & (
                                Q(nombres__contains=s[0]) | Q(apellido1__contains=s[0]) | Q(
                            apellido2__contains=s[0]) | Q(cedula__contains=s[0]))).exclude(pk__in=lista).distinct()[
                                  :15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr()} for x in persona]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'inscritos':
                try:
                    id = encrypt(request.GET['id'])
                    request.session['viewactive'] = 1
                    data['title'] = u'Inscritos - Formación Ejecutiva'
                    data['capa'] = capa = CapacitaEventoFormacionEjecutiva.objects.get(status=True, id=int(id))
                    data['perd'] = perd = capa.periodo
                    filtro, search, url_vars = Q(status=True,capeventoperiodo=capa), request.GET.get('s',None), f'&action={action}&id={request.GET["id"]}'
                    if search:
                        url_vars += '&s=' + search
                        search = request.GET['s'].strip()
                        url_vars += f'&s={search}'
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(participante__nombres__icontains=search) |
                                               Q(participante__apellido1__icontains=search) |
                                               Q(participante__apellido2__icontains=search) |
                                               Q(participante__cedula__icontains=search) |
                                               Q(participante__pasaporte__icontains=search) |
                                               Q(participante__usuario__username__icontains=search))
                        else:
                            filtro = filtro & (Q(participante__apellido1__icontains=ss[0]) &
                                               Q(participante__apellido2__icontains=ss[1]))
                        data['s'] = search
                    query = CapaEventoInscritoFormaEjecutiva.objects.filter(filtro)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list

                    data['costoext'] = capa.costoexterno
                    data['costoint'] = capa.costo
                    return render(request,"adm_ejecuform/viewinscritos.html",data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'mensaje': msg_err}
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?action=planificacion&id={encrypt(perd.id)}')

            elif action == 'buscarinscritos':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    querybase = Persona.objects.filter(status=True).order_by('apellido1')
                    if len(s) == 1:
                        querybase = querybase.filter((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) |  Q(apellido2__icontains=q) | Q(cedula__contains=q)), Q(status=True)).distinct()[:15]
                    elif len(s) == 2:
                        querybase = querybase.filter((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                                       (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                                       (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1]))).filter(status=True).distinct()[:15]
                    else:
                        querybase = querybase.filter((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) |
                                                       (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).filter(status=True).distinct()[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {} | {}".format(x.cedula, x.nombre_completo(), x.nombres)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'addinscrito':
                try:
                    data['title'] = u'Agregar Inscripción'
                    data['id'] = id = encrypt(request.GET['id'])
                    data['filtro'] = filtro = CapacitaEventoFormacionEjecutiva.objects.get(pk=id)
                    form = CapaEventoInscritoFormaEjecutivaForm()
                    form.fields['participante'].queryset = Persona.objects.none()
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result': True, 'data': template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'mensaje': msg_err}
                return JsonResponse(res_js)

            elif action == 'addregistrar':
                try:
                    data['title'] = u'Registrar datos de la inscripción'
                    data['eventoperiodo'] = CapacitaEventoFormacionEjecutiva.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = CapaEventoInscritoFormaEjecutivaManualForm()
                    return render(request, "adm_ejecuform/formparticipantemanual.html", data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?info={msg_err}')
            #
            # elif action == 'addinscribir':
            #     try:
            #         data['title'] = u'Inscribir'
            #         data['form'] = CapInscribirIpecForm()
            #         data['eventoperiodo'] = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
            #         return render(request, "adm_capacitacioneventoperiodoipec/addinscribir.html", data)
            #     except Exception as ex:
            #         pass
            elif action == 'instructores':
                try:
                    request.session['viewactive'] = 6
                    data['title'] = u'Instructores - Formación Ejecutiva'
                    filtro, search, url_vars = Q(status=True), request.GET.get('s',None), f'&action={action}'
                    if search:
                        url_vars += '&s=' + search
                        filtro = filtro & Q(Q(instructor__nombres__icontains=search)|Q(instructor__apellido1__icontains=search)|Q(instructor__apellido2__icontains=search))
                        data['search'] = search
                    query = InstructorFormaEjecutiva.objects.filter(filtro)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    return render(request,"adm_ejecuform/viewinstructores.html",data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'mensaje': msg_err}
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?info={msg_err}')

            elif action == 'instructor':
                try:
                    id = encrypt(request.GET['id'])
                    request.session['viewactive'] = 1
                    data['capa'] = capa = CapacitaEventoFormacionEjecutiva.objects.get(status=True, id=int(id))
                    data['perd'] = perd = capa.periodo
                    data['title'] = u'Instructores de Evento - Formación Ejecutiva'
                    filtro, search, url_vars = Q(status=True,capeventoperiodo=capa), request.GET.get('s', None), f'&action={action}'
                    if search:
                        url_vars += '&s=' + search
                        filtro = filtro & Q(
                            Q(instructor__nombres__icontains=search) | Q(instructor__apellido1__icontains=search) | Q(
                                instructor__apellido2__icontains=search))
                        data['search'] = search
                    query = InstructorFormaEjecutiva.objects.filter(filtro)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    return render(request, "adm_ejecuform/viewinstructor.html", data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'mensaje': msg_err}
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?info={msg_err}')

            elif action == 'addinstructor':
                try:
                    data['eventoperiodo'] = request.GET['id']
                    form = InstructorFormaEjecutivaForm()
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result': True, 'data': template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'mensaje': msg_err}
                return JsonResponse(res_js)

            elif action == 'editinstructor':
                try:
                    id = encrypt(request.GET['id'])
                    data['filtro']=filtro = InstructorFormaEjecutiva.objects.get(status=True,id=int(id))
                    form = InstructorFormaEjecutivaForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result': True, 'data': template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'mensaje': msg_err}
                return JsonResponse(res_js)

            elif action == 'rubros':
                try:
                    request.session['viewactive'] = 7
                    data['title'] = u'Rubros - Formación Ejecutiva'
                    filtro, search, url_vars = Q(tiporubro=8, status=True), request.GET.get('s', None), f'&action={action}'
                    if search:
                        url_vars += '&s=' + search
                        filtro = filtro & Q(
                            Q(instructor__nombres__icontains=search) | Q(instructor__apellido1__icontains=search) | Q(
                                instructor__apellido2__icontains=search))
                        data['search'] = search

                    query = TipoOtroRubro.objects.filter(filtro)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    return render(request, "adm_ejecuform/viewrubros.html", data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'mensaje': msg_err}
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?info={msg_err}')

            elif action == 'addtiporubro':
                try:
                    form = TipoOtroRubroEjecutivaForm()
                    form.addtiporubro()
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result': True, 'data': template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False,'mensaje': msg_err}
                return JsonResponse(res_js)

            elif action == 'edittiporubro':
                try:
                    id = encrypt(request.GET['id'])
                    data['filtro'] = tipootrorubro = TipoOtroRubro.objects.get(status=True,id=int(id))
                    form = TipoOtroRubroEjecutivaForm(initial={'nombre': tipootrorubro.nombre,
                                                          'partida': tipootrorubro.partida,
                                                          'unidad_organizacional': tipootrorubro.unidad_organizacional,
                                                          'programa': tipootrorubro.programa,
                                                          'ivaaplicado': tipootrorubro.ivaaplicado,
                                                          'valor': tipootrorubro.valor,
                                                          'tipo': tipootrorubro.tiporubro})
                    form.addtiporubro()
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result': True, 'data': template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False,'mensaje': msg_err}
                return JsonResponse(res_js)

            elif action == 'addobservacion':
                try:
                    id = encrypt(request.GET['id'])
                    data['filtro'] = inscrito = CapaEventoInscritoFormaEjecutiva.objects.get(pk=int(id))
                    data['title'] = u'Observación de %s' % inscrito.participante.nombre_completo_inverso()
                    initial = model_to_dict(inscrito)
                    form = ObservacionInscritoEventoFormaEjecutivaForm(initial=initial)
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result': True, 'data': template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'mensaje': msg_err}
                return JsonResponse(res_js)

            elif action == 'verobservacioninscripcion':
                try:
                    id = encrypt(request.GET['id'])
                    data['inscrito'] = inscrito = CapaEventoInscritoFormaEjecutiva.objects.get(pk=int(id))
                    data['title'] = u'Observación'
                    template = get_template("adm_ejecuform/modal/verobservacioninscripcion.html")
                    json_content = template.render(data)
                    res_js = {'result': True, 'data': template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'mensaje': msg_err}
                return JsonResponse(res_js)

            elif action == 'consultapagoepunemi':
                try:
                    rubro = Rubro.objects.values_list('id','idrubroepunemi').filter(persona=int(request.GET['id']),
                                                 capeventoperiodoformejecu=int(request.GET['capeventoperiodo']),
                                                 status=True).exclude(pago__factura__valida=False)
                    idrubrounemi = tuple([idrubrounemi[1] for idrubrounemi in rubro])
                    idrubro = tuple([idrubrounemi[0] for idrubrounemi in rubro])

                    data['nombre'] = request.GET['nombre']
                    data['pago'] = pago = int(request.GET['pago'])
                    data['costo'] = costo = int(request.GET['costo'])
                    data['saldoUnemi'] = costo - pago
                    data['saldoEpunemi'] = 0
                    data['pagoEpunemi'] = 0
                    data['costoEpunemi'] = 0
                    data['canceladoEpunemi'] = 'NO'
                    data['canceladoUnemi'] = 'NO'
                    canceladoUnemi = request.GET['rubro']
                    data['estado'] = False
                    if canceladoUnemi:
                        data['canceladoUnemi'] = 'SI'
                    cursor = connections['epunemi'].cursor()
                    queryest = """
                            SELECT valortotal, cancelado FROM sagest_rubro WHERE status=true and id in %s AND idrubrounemi in %s
                            """ % (idrubrounemi if len(idrubrounemi)>1 else str(idrubrounemi).replace(",",""), idrubro if len(idrubrounemi)>1 else str(idrubro).replace(",",""))
                    cursor.execute(queryest)
                    rowest = cursor.fetchall()
                    if rowest:
                        valorsuma = 0
                        for rowsuma in rowest:
                            valorsuma += rowsuma[0]
                        data['costoEpunemi'] = costoEpunemi = valorsuma
                        data['canceladoEpunemi'] = rowest[0][1]
                        data['estado'] = True
                    queryest = """
                            SELECT SUM(valortotal) FROM sagest_pago WHERE status=true and rubro_id in %s
                            """ % (str(idrubrounemi if len(idrubrounemi)>1 else str(idrubrounemi).replace(",","")))
                    cursor.execute(queryest)
                    rowest = cursor.fetchall()
                    if rowest:
                        valorsuma = 0
                        for rowsuma in rowest:
                            if rowsuma[0] != None:
                                valorsuma += rowsuma[0]
                        if rowest[0][0] != None:
                            data['pagoEpunemi'] = rowest[0][0]
                            costoEpunemi = costoEpunemi - valorsuma
                            data['saldoEpunemi'] = costoEpunemi
                    template = get_template('adm_ejecuform/modal/pagoepunemi.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    return JsonResponse({"result": False, 'mensaje': msg_err})

            elif action == 'verdetalleevento':
                try:
                    id = encrypt(request.GET['id'])
                    data['evento'] = inscrito = CapacitaEventoFormacionEjecutiva.objects.get(pk=int(id))
                    template = get_template("adm_ejecuform/modal/detalleevento.html")
                    res_js = {'result': True, 'data': template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'mensaje': msg_err}
                return JsonResponse(res_js)

            elif action == 'modelevaluageneral':
                try:
                    request.session['viewactive'] = 8
                    data['title'] = u'Rubros - Formación Ejecutiva'
                    filtro, search, url_vars = Q(status=True), request.GET.get('s',None), f'&action={action}'
                    if search:
                        url_vars += '&s=' + search
                        filtro = filtro & Q(
                            Q(instructor__nombres__icontains=search) | Q(instructor__apellido1__icontains=search) | Q(
                                instructor__apellido2__icontains=search))
                        data['search'] = search
                    query = CapModeloEvaluativoGeneralFormaEjecutiva.objects.filter(filtro).order_by('orden')
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    return render(request, "adm_ejecuform/viewgeneralmodel.html", data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?info={msg_err}')

            elif action == 'addgeneralmodel':
                try:
                    filtro = CapModeloEvaluativoGeneralFormaEjecutiva.objects.filter(status=True)
                    data['title'] = u'Agregar modelo evaluativo general'
                    form = ModeloEvaluativoGeneralFormEjecutiva()
                    form.fields['modelo'].queryset = ModeloEvaluativoFormaEjecutiva.objects.filter(status=True).exclude(
                        id__in=filtro.values_list('modelo__id', flat=True)).order_by('nombre')
                    form.fields['orden'].initial = filtro.count() + 1
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result':True,'data':template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result':False,'message':msg_err}
                return JsonResponse(res_js)

            elif action == 'editgeneralmodel':
                try:
                    id = encrypt(request.GET['id'])
                    data['filtro']=filtro=CapModeloEvaluativoGeneralFormaEjecutiva.objects.get(status=True,id=int(id))
                    data['title'] = u'Editar modelo evaluativo general'
                    form = ModeloEvaluativoGeneralFormEjecutiva(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result':True,'data':template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result':False,'message':msg_err}
                return JsonResponse(res_js)

            elif action == 'notas':
                try:
                    data['title'] = u'Notas'
                    id = encrypt(request.GET['id'])
                    data['evento'] = evento = CapacitaEventoFormacionEjecutiva.objects.get(status=True,id=int(id))
                    data['perd'] = perd = evento.periodo
                    data['instructores'] = evento.instructorformaejecutiva_set.filter(status=True,instructorprincipal=True).order_by('instructor__apellido1', 'instructor__apellido2', 'instructor__nombres')
                    if not evento.modeloevaludativoindividual:
                        data['modeloevaluativogeneral'] = CapModeloEvaluativoGeneralFormaEjecutiva.objects.filter(status=True).order_by('orden')
                    return render(request, "adm_ejecuform/viewnotas.html", data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?info={msg_err}')

            elif action == 'confimodelogeneral':
                try:
                    data['id'] = encrypt(request.GET['id'])
                    data['modeloevaluativo'] = modelos = CapModeloEvaluativoGeneralFormaEjecutiva.objects.filter(
                        status=True).order_by('orden')
                    data['instructor'] = instructor = InstructorFormaEjecutiva.objects.get(pk=int(encrypt(request.GET['id'])))
                    if instructor.capnotaformaejecutiva_set.filter(status=True).count() >= modelos.count():
                        return JsonResponse({"result": False, 'message': 'Instructor ya cuenta con modelo evaluativo'})
                    data['instructorname'] = instructor.instructor.nombre_completo_inverso()
                    template = get_template("adm_ejecuform/modal/confirmarmodelo.html")
                    res_js = {'result': True, 'data': template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'message': msg_err}
                return JsonResponse(res_js)

            elif action == 'calificar':
                try:
                    data['title'] = u'Notas'
                    id = encrypt(request.GET['id'])
                    data['tarea'] = tarea = CapNotaFormaEjecutiva.objects.get(pk=int(id))
                    data['listadoinscritos'] = tarea.capdetallenotaformaejecutiva_set.filter(status=True)
                    return render(request, "adm_ejecuform/viewcalificaciones.html", data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?info={msg_err}')

            elif action == 'calificageneral':
                try:
                    data['title'] = u'Calificación General'
                    id = encrypt(request.GET['id'])
                    data['instructor'] = instructor = InstructorFormaEjecutiva.objects.get(pk=int(id))
                    data['tareas'] = CapNotaFormaEjecutiva.objects.filter(status=True,instructor=instructor)
                    data['listadoinscritos'] = instructor.capeventoperiodo.inscritos()
                    return render(request, "adm_ejecuform/viewcalificacionesgeneral.html", data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?info={msg_err}')

            elif action == 'generar_rubro':
                try:
                    id = encrypt(request.GET['id'])
                    data['filtro'] = filtro = CapaEventoInscritoFormaEjecutiva.objects.get(status=True,id=int(id))
                    data['title'] = u'Generar rubros'
                    form = GenerarRubrosForm()
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result': True, 'data': template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'message': msg_err}
                return JsonResponse(res_js)

            elif action == 'generarrubromasivo':
                try:
                    id = encrypt(request.GET['id'])
                    data['filtro'] = filtro = CapacitaEventoFormacionEjecutiva.objects.get(pk=int(id))
                    data['title'] = u'Generar rubros masivo'
                    form = GenerarRubrosForm()
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result': True, 'data': template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'message': msg_err}
                return JsonResponse(res_js)

            elif action == 'recordpayment':
                try:
                    id = encrypt(request.GET['id'])
                    data['filtro'] = filtro = CapaEventoInscritoFormaEjecutiva.objects.get(status=True,id=int(id))
                    data['title'] = u'Ingresar pagos'
                    if filtro.regpago():
                        pago = filtro.regpago().first()
                        form = PagoFormacionEjecutivaForm(initial=model_to_dict(pago))
                    else:
                        form = PagoFormacionEjecutivaForm()
                    data['form'] = form
                    template = get_template("adm_ejecuform/modal/formmodal.html")
                    res_js = {'result': True, 'data': template.render(data)}
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'message': msg_err}
                return JsonResponse(res_js)

            elif action == 'exportinscritospay':
                try:
                    id = encrypt(request.GET['id'])
                    evento = CapacitaEventoFormacionEjecutiva.objects.get(status=True,id=int(id))
                    inscritos = evento.inscritos()
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('reporte')
                    formatoceldagris = workbook.add_format({'align': 'center', 'border': 1, 'text_wrap': True, 'fg_color': '#B6BFC0'})
                    formatocelda = workbook.add_format({'align': 'left', 'border': 1, 'text_wrap': True})
                    formmoney = workbook.add_format({'align': 'left', 'border': 1, 'text_wrap': True,'num_format': '$#,##0.00'})
                    ws.write(0, 0, 'EVENTO')
                    ws.merge_range('B1:F1', str(evento))
                    row_num = 1
                    column = (
                        ('F.Registro',10),
                        ('Nombres',40),
                        ('Cedula',10),
                        ('Descripción',60),
                        ('Pago',10),
                        ('Tipo Pago',20),
                        ('F.Pago',10),
                    )
                    for col in range(len(column)):
                        ws.write(row_num, col,column[col][0],formatoceldagris)
                        ws.set_column(col,col,column[col][1])
                    row_num += 1
                    for ins in inscritos:
                        pago=ins.regpago()
                        ws.write(row_num,0,str(ins.fecha_creacion.strftime('%d/%m/%Y')),formatocelda)
                        ws.write(row_num,1,ins.participante.nombre_completo(),formatocelda)
                        ws.write(row_num,2,ins.participante.cedula,formatocelda)
                        if pago:
                            pago = pago.first()
                            ws.write(row_num,3,pago.observacion,formatocelda)
                            ws.write(row_num,4,pago.valor,formmoney)
                            ws.write(row_num,5,pago.get_tipocomprobante_display(),formatocelda)
                            ws.write(row_num,6,pago.fpago.strftime('%d/%m/%Y'),formatocelda)
                        else:
                            ws.write(row_num, 3, '-', formatocelda)
                            ws.write(row_num, 4, 0.00, formmoney)
                            ws.write(row_num, 5, '-', formatocelda)
                            ws.write(row_num, 6, '-', formatocelda)
                        row_num +=1
                    workbook.close()
                    output.seek(0)
                    filename = 'reporte_inscritos.xlsx'
                    response = HttpResponse(output,content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?action=planificacion&id={encrypt(evento.periodo.id)}&info={msg_err}')

            elif action == 'exportinscritospayperiodo':
                try:
                    id = encrypt(request.GET['id'])
                    periodo = PeriodoFormaEjecutiva.objects.get(status=True,id=int(id))
                    evntos = periodo.capacitaeventoformacionejecutiva_set.filter(status=True)
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('reporte')
                    formatoceldagris = workbook.add_format({'align': 'center', 'border': 1, 'text_wrap': True, 'fg_color': '#B6BFC0'})
                    formatocelda = workbook.add_format({'align': 'left', 'border': 1, 'text_wrap': True})
                    formmoney = workbook.add_format({'align': 'left', 'border': 1, 'text_wrap': True, 'num_format': '$#,##0.00'})
                    row_num = 1
                    column = (
                        ('F.Registro', 10),
                        ('Evento', 40),
                        ('Nombres', 40),
                        ('Cedula', 10),
                        ('Descripción', 60),
                        ('Pago', 10),
                        ('Tipo Pago', 20),
                        ('F.Pago', 10),
                    )
                    for col in range(len(column)):
                        ws.write(row_num, col, column[col][0], formatoceldagris)
                        ws.set_column(col, col, column[col][1])
                    row_num += 1
                    for evento in evntos:
                        inscritos = evento.inscritos()

                        for ins in inscritos:
                            pago=ins.regpago()
                            ws.write(row_num,0,str(ins.fecha_creacion.strftime('%d/%m/%Y')),formatocelda)
                            ws.write(row_num, 1, evento.capevento.nombre, formatocelda)
                            ws.write(row_num,2,ins.participante.nombre_completo(),formatocelda)
                            ws.write(row_num,3,ins.participante.cedula,formatocelda)
                            if pago:
                                pago = pago.first()
                                ws.write(row_num,4,pago.observacion,formatocelda)
                                ws.write(row_num,5,pago.valor,formmoney)
                                ws.write(row_num,6,pago.get_tipocomprobante_display(),formatocelda)
                                ws.write(row_num,7,pago.fpago.strftime('%d/%m/%Y'),formatocelda)
                            else:
                                ws.write(row_num, 4, '-', formatocelda)
                                ws.write(row_num, 5, 0.00, formmoney)
                                ws.write(row_num, 6, '-', formatocelda)
                                ws.write(row_num, 7, '-', formatocelda)
                            row_num +=1
                    workbook.close()
                    output.seek(0)
                    filename = 'reporte_inscritos_periodo.xlsx'
                    response = HttpResponse(output,content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?action=planificacion&id={encrypt(evento.periodo.id)}&info={msg_err}')

            elif action == 'alumnos':
                try:
                    request.session['viewactive'] = 9
                    if 'idi' in request.GET and 'ide' in request.GET:
                        data['title'] = u'Alumnos inscritos'
                        instructor = InstructorFormaEjecutiva.objects.get(pk=int(request.GET['idi']), capeventoperiodo_id=int(request.GET['ide']))
                        data['evento'] = instructor.capeventoperiodo
                        data['instructor'] = instructor
                        data['tareas'] = CapNotaFormaEjecutiva.objects.filter(status=True, instructor=instructor)
                        data['listadoinscritos'] = instructor.capeventoperiodo.inscritos()
                        return render(request, "adm_ejecuform/instructor/alumno/view.html", data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'mensaje': msg_err}
                    return HttpResponseRedirect(f'/?info={msg_err}')

            elif action == 'notasmoodle':
                try:
                    request.session['viewactive'] = 9
                    data['title'] = u'Alumnos inscritos'
                    search = None
                    data['instructor'] = intructor = InstructorFormaEjecutiva.objects.get(pk=int(encrypt(request.GET['idi'])),capeventoperiodo_id=int(encrypt(request.GET['ide'])))
                    data['evento'] = intructor.capeventoperiodo
                    data['modelosencabesados'] = intructor.modelo_calificacion_abreviado(intructor.capeventoperiodo)
                    inscritos = intructor.capeventoperiodo.list_inscritos_sin_costo()
                    data['inscritos'] = inscritos
                    return render(request, "adm_ejecuform/instructor/notas/view.html", data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'mensaje': msg_err}
                    return HttpResponseRedirect(f'/?info={msg_err}')

            elif action == 'cursosinstructor':
                try:
                    request.session['viewactive'] = 9
                    data['title'] = u'Mis cursos - Formación Ejecutiva'
                    data['title'] = u'Mis Cursos Asigandos'
                    data['cursos'] = InstructorFormaEjecutiva.objects.filter(status=True, instructorprincipal=True, instructor=persona).order_by('-capeventoperiodo__fechainicio')
                    data['instructor'] = persona

                    return render(request, "adm_ejecuform/instructor/view.html", data)
                except Exception as ex:
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'mensaje': msg_err}
                    return HttpResponseRedirect(f'/?info={msg_err}')

            elif action == 'extraernotasmoodle':
                try:
                    data['title'] = u'Importar calificaciones de moodle'
                    data['instructor'] = instructor = InstructorFormaEjecutiva.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_ejecuform/instructor/extraernotasmoodle.html", data)
                except Exception as ex:
                    pass

            elif action == 'resetearusu':
                try:
                    data['title'] = u'Resetear clave del usuario'
                    data['inscrito'] = inscripcion = CapaEventoInscritoFormaEjecutiva.objects.get(pk=request.GET['id'])
                    return render(request, "adm_ejecuform/modal/resetear.html", data)
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

            elif action == 'consultar_cargo_persona':
                try:
                    from sagest.models import Departamento
                    cargo = ''
                    id = int(request.GET['persona_id'])
                    eDepartamento = Departamento.objects.filter(status=True,id__in=[215,247,163],responsable_id = id)
                    if eDepartamento.exists():
                        if eDepartamento.first().id == 215: #escuela eduacion
                            cargo = 'Director(a) de la Escuela de Educación'
                        elif eDepartamento.first().id == 247: #escuela salud
                            cargo = 'Director(a) de la Escuela de Ciencias de la Salud'
                        elif eDepartamento.first().id == 163: #escuela negocio
                            cargo = 'Director(a) de la Escuela de Negocios'
                        else:
                            cargo = ''
                    return JsonResponse({"result": True, "cargo": cargo})
                except Exception as ex:
                    return JsonResponse({"result": True, "cargo": cargo})

            return HttpResponseRedirect('/adm_formejecuperiodo')
        else:
            try:
                validaciones(data, persona)
                request.session['viewactive'] = 1
                data['title'] = u'Periodos Formación Ejecutiva'
                filtro,search,url_vars = Q(status=True), request.GET.get('s',None),''

                if search:
                    url_vars += '&s='+search
                    filtro = filtro & Q(Q(nombre__icontains=search)|Q(descripcion__icontains=search))
                    data['search'] = search

                query = PeriodoFormaEjecutiva.objects.filter(filtro)
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
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data["url_params"] = url_vars
                data["url_vars"] = url_vars
                data["listado"] = page.object_list
                if not data['es_administrador'] and data['es_instructor']  and not persona.usuario.is_superuser:
                    request.session['viewactive'] = 9
                    return HttpResponseRedirect(f'/adm_formejecuperiodo?action=cursosinstructor')
                else:
                    return render(request,"adm_ejecuform/view.html",data)
            except Exception as ex:
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                print(msg_err)
                return HttpResponseRedirect(f'/?info={msg_err}')

def buscarPedidoOnlineRubroEpunemi(idpersona, idrubro):
    cursor = connections['epunemi'].cursor()
    sql = """SELECT detped.id FROM crm_detallepedidoonline detped 
                INNER JOIN crm_pedidoonline ped on detped.pedido_id=ped.id
                WHERE detped.status=TRUE and detped.rubro_id=%s and ped.persona_id='%s'; """ % (idrubro, idpersona)
    cursor.execute(sql)
    rubrotienecomprobanteepunemi = cursor.fetchone()
    cursor.close()
    return rubrotienecomprobanteepunemi

# Elimina rubros unemi y migra cambios a EPUNEMI
def eliminar_y_migrar_rubro_deunemi_aepunemi_formacionejecutiva(request, rubrosunemi, action='MIGRADO_UNEMI', procesomasivo = False):
    with transaction.atomic():
        try:
            rubrospagados_noeliminados, total_rubrosunemi, total_rubrosepunemi = [], 0, 0
            for r in rubrosunemi:
                # consultar rubro epunemi
                cursor = connections['epunemi'].cursor()
                sql = """SELECT id, valor, totalunemi, cancelado, nombre, persona_id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE; """ % (
                    r.id)
                cursor.execute(sql)
                rubroepunemi = cursor.fetchone()
                inscrito = CapaEventoInscritoFormaEjecutiva.objects.filter(status=True, capeventoperiodo_id=r.capeventoperiodoformejecu.id, participante=r.persona).first()
                if rubroepunemi:
                    # consultar pago de rubro epunemi
                    tienepagosepunemi = buscarPagosEpunemiRubroUnemi(rubroepunemi[0])
                    tienepagosepunemi_min = Rubro.objects.values_list('idrubroepunemi',flat=True).filter(capeventoperiodoformejecu=r.capeventoperiodoformejecu, persona=r.persona,status=True)
                    for tpago in tienepagosepunemi_min:
                        tienepagosepunemi = buscarPagosEpunemiRubroUnemi(tpago)
                        if tienepagosepunemi:
                            break
                    # Valido que sólo elimine cuando no haya pago, no este cancelado y el valor de los rubros sean iguales en unemi y epunemi
                    if not r.tiene_pagos() and r.cancelado == False and not tienepagosepunemi and rubroepunemi[3] == False and r.valor == rubroepunemi[1] and r.valor == rubroepunemi[2]:
                        # Verificar que no tenga pendiente registro de pago, es decir que no tenga comprobante alumno epunemi
                        rubroepunemitienecomprobante =  buscarPedidoOnlineRubroEpunemi(rubroepunemi[5], rubroepunemi[0])
                        if not rubroepunemitienecomprobante:
                            # Elimino el rubro en UNEMI y llamo funcion eliminar en EPUNEMI
                            r.status = False
                            r.save(request)
                            if procesomasivo:
                                # Desactivar el inscrito
                                inscrito.desactivado = True
                                inscrito.save(request)
                                # Desactivar el inscrito
                            total_rubrosunemi += 1

                            # Consulto * rubro epunemi a eliminar (antes de cambiar el status)
                            sql = """SELECT row_to_json(r) FROM (SELECT * FROM sagest_rubro WHERE status=TRUE AND id=%s) r;"""
                            cursor.execute(sql, [rubroepunemi[0]])
                            rubroepunemi_dic = cursor.fetchone()
                            rubroepunemi_dic = rubroepunemi_dic[0]

                            # Elimino logicamente el rubro en Epunemi
                            sql = """UPDATE sagest_rubro SET status=false WHERE status=TRUE AND id=%s; """ % (rubroepunemi[0])
                            cursor.execute(sql)
                            total_rubrosepunemi += 1

                            # guardar auditoría en UNEMI el log del rubro unemi eliminado
                            qs_nuevo = [vars(r)]
                            salvaRubros(request, r, action, qs_nuevo=qs_nuevo)

                            # guardar auditoría en EPUNEMI el log del rubro epunemi eliminado desde UNEMI
                            qs_nuevoepunemi = [rubroepunemi_dic]
                            salvaRubrosEpunemiEdcon(rubroepunemi_dic, action, qs_nuevo=qs_nuevoepunemi)
                        else:
                            rubrospagados_noeliminados.append(f'{r.persona.cedula} [{r.id}] porque el rubro posee un comprobante de pago')
                    else:
                        rubrospagados_noeliminados.append(f'{r.persona.cedula} [{r.id}] porque el rubro posee pagos o su valor difiere con el rubro EPUNEMI')
                else:
                    # Elimino el rubro que sólo existe en UNEMI
                    # guardar auditoría en UNEMI el log del rubro elimminado en unemi
                    qs_nuevo = [vars(r)]
                    salvaRubros(request, r, action, qs_nuevo=qs_nuevo)
                    r.status = False
                    r.save(request)
                    if procesomasivo:
                        # Desactivar el inscrito
                        inscrito.desactivado = True
                        inscrito.save(request)
                        # Desactivar el inscrito
                    log(u'Se elimino un rubro a inscrito : %s [%s]' % (inscrito, r), request, "del")
                    total_rubrosunemi += total_rubrosunemi
                    rubrospagados_noeliminados.append(f'{r.persona.cedula} [{r.id}] porque el rubro no ha sido migrado a EPUNEMI')
                cursor.close()
            # concatenar rubrospagados_noeliminados
            textorubrosnoeliminado = rubrospagados_noeliminados[0] if rubrospagados_noeliminados else None
            for error in rubrospagados_noeliminados[1:]:
                textorubrosnoeliminado += f", {error}"
            return {"result": "ok", "mensaje": {"total_rubrosunemi": total_rubrosunemi, "total_rubrosepunemi": total_rubrosepunemi, "rubrospagados_noeliminados": textorubrosnoeliminado}}
        except Exception as ex:
            transaction.set_rollback(True)
            print(f"Error {str(ex)} on line {sys.exc_info()[-1].tb_lineno}")
            return {"result": "bad", "mensaje": f"Error {str(ex)} on line {sys.exc_info()[-1].tb_lineno}"}

def generar_certificado_porinscripcion_save(**kwargs):
    try:
        firmacertificado = None
        persona_cargo_tercernivel = None
        cargo = None
        tamano = 0
        request = kwargs.get('request', None)
        _var = lambda x: request.session.get(x, None) if not x in kwargs else kwargs.get(x, None)
        ins = _var('ins')
        qrname = _var('qrname')
        template_asistencia_pdf = _var('template_asistencia')
        listado = _var('listado')
        evento = _var('evento')
        data = _var('data')
        data["DOMINIO_DEL_SISTEMA"] = dominio_sistema = 'https://sga.unemi.edu.ec' if not DEBUG else 'http://127.0.0.1:8000'

        if ins.capeventoperiodo.firma_certificado_1 and ins.capeventoperiodo.firma_certificado_2:
            data['firma_por_integrante'] = True
            data['persona_1'] = ins.capeventoperiodo.firma_certificado_1
            data['firma_1'] = FirmaPersona.objects.filter(status=True, persona=ins.capeventoperiodo.firma_certificado_1).last()
            data['cargo_persona_1'] = ins.capeventoperiodo.cargo_firma_certificado_1
            data['persona_2'] = ins.capeventoperiodo.firma_certificado_2
            data['firma_2'] = FirmaPersona.objects.filter(status=True,persona=ins.capeventoperiodo.firma_certificado_2).last()
            data['cargo_persona_2'] =ins.capeventoperiodo.cargo_firma_certificado_2
        else:
            data['firma_por_integrante'] = False
            if PersonaDepartamentoFirmas.objects.filter(status=True, departamento=158).exists(): firmacertificado = PersonaDepartamentoFirmas.objects.filter(status=True,departamento=158).order_by('-id').first()
            if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                firmaizquierda = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                                                                       tipopersonadepartamento_id=2,
                                                                       departamentofirma_id=1)
            if PersonaDepartamentoFirmas.objects.values('id').filter(status=True,
                                                                     fechafin__gte=evento.fechafin,
                                                                     fechainicio__lte=evento.fechafin,
                                                                     tipopersonadepartamento_id=2,
                                                                     departamentofirma_id=1).exists():
                firmaizquierda = PersonaDepartamentoFirmas.objects.get(status=True,
                                                                       fechafin__gte=evento.fechafin,
                                                                       fechainicio__lte=evento.fechafin,
                                                                       tipopersonadepartamento_id=2,
                                                                       departamentofirma_id=1)
            data['firmacertificado'] = firmacertificado
            data['firmaimg'] = FirmaPersona.objects.filter(status=True, persona=firmacertificado.personadepartamento).last()
            data['firmaizquierda'] = firmaizquierda
            data['firmaimgizq'] = FirmaPersona.objects.filter(status=True, persona=firmaizquierda.personadepartamento).last()
        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'formacionejecutiva', 'qrcode', 'certificados'))
        try:
            os.stat(folder)
        except:
            os.mkdir(folder)
        if evento.objetivo.__len__() < 290:
            if listado.__len__() < 21:
                tamano = 120
            elif listado.__len__() < 35:
                tamano = 100
            elif listado.__len__() < 41:
                tamano = 70
        data['ruta_arch'] = f'{dominio_sistema}/media/formacionejecutiva/qrcode/certificados/{qrname}.png'
        data['ruta_arch_pdf'] = f'{dominio_sistema}/media/formacionejecutiva/qrcode/certificados/{qrname}.pdf'
        ruta_arch = folder + os.sep + qrname + '.png'
        ruta_archpdf = folder + os.sep + qrname + '.pdf'
        if os.path.isfile(ruta_arch):
            os.remove(ruta_arch)
        if os.path.isfile(ruta_archpdf):
            os.remove(ruta_archpdf)

        if not ins.namehtmlinsignia:
            htmlname = "%s%s" % (uuid.uuid4().hex, '.html')
        else:
            htmlname = ins.namehtmlinsignia
        urlname = "/media/formacionejecutiva/qrcode/insignia/%s" % htmlname
        rutahtml = SITE_STORAGE + urlname
        if os.path.isfile(rutahtml):
            os.remove(rutahtml)

        url = pyqrcode.create(f'https://sga.unemi.edu.ec/media/formacionejecutiva/qrcode/insignia/{htmlname}')
        imageqr = url.png(ruta_arch, 16, '#000000')
        data['controlar_bajada_logo'] = tamano
        data['urlhtmlinsignia'] = dominio_sistema + urlname
        valida = conviert_html_to_pdf_name_bitacora(template_asistencia_pdf, {'pagesize': 'A4', 'data': data}, qrname + '.pdf')
        if valida[0]:
            valida[1].seek(0)
            fil_content = valida[1].read()
            resp = ContentFile(fil_content)
            if ins.rutapdf:
                pass
            ins.rutapdf.save(qrname + '.pdf', resp)
            data['rutapdf'] = dominio_sistema + urlname
            a = render_to_string("adm_ejecuform/certificadovalido.html",
                       {"data": data, 'institucion': 'UNIVERSIDAD ESTATAL DE MILAGRO',
                        "remotenameaddr": 'sga.unemi.edu.ec'},request)
            temp_file = ContentFile(a.encode('utf-8'))
            ins.htmlinsignia.save(htmlname, temp_file)

        else:
            res_js = valida[1]
            raise NameError(valida[1]['mensaje'])
    except Exception as ex:
        err_ = f'{ex}({sys.exc_info()[-1].tb_lineno})'
        raise NameError(err_)
