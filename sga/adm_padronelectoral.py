# -*- coding: UTF-8 -*-
import json
import os
import random
import sys
import subprocess
from datetime import datetime
from decimal import Decimal

import pyqrcode
import shutil
import uuid

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q, Count
import xlwt
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context
from django.template.loader import get_template
from xlwt import *
from django.shortcuts import render, redirect

from api.helpers.functions_helper import get_variable
from voto.models import GremioPeriodo, GremioElectoral, ListaElectoral, SubDetalleMesa, DetalleMesa, \
    ConfiguracionMesaResponsable, ListaGremio, SedesElectoralesPeriodo, PersonasSede, DignidadesElectorales, \
    RequisitosDignidadesElectorales, SolicitudDignidadesElectorales, RequisitoSolicitudDignidadesElectorales, ESTADOS_SOLICITUD_DIGNIDAD
from .formmodel import GremioPeriodoForm
from .forms import CabPadronElectoralForm, DetalleJustificativoForm, MesaPadronForm, ListaPadronForm, GremioPadronForm, \
    ConfiguracionMesaResponsableForm, PersonaEmpadronadoForm, SedeElectoralPeriodoForm, DignidadElectoralForm, \
    SolicitudDignidadForm, ValidarSolicitudesForm
from decorators import secure_module, last_access
from settings import EMAIL_DOMAIN, SITE_STORAGE, DEBUG, JR_JAVA_COMMAND, JR_RUN, DATABASES, MEDIA_ROOT, SITE_ROOT
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre, puede_realizar_accion, null_to_decimal, \
    puede_realizar_accion_afirmativo, generar_codigo, remover_caracteres_especiales_unicode, notificacion, \
    fecha_letra_formato_fecha, remover_caracteres_tildes_unicode, variable_valor, elimina_tildes
from .funcionesxhtml2pdf import conviert_html_to_pdf, download_html_to_pdf, link_callback, \
    conviert_html_to_pdf_parametros_save, conviert_html_to_pdf_name_bitacora
from .models import CabPadronElectoral, DetPersonaPadronElectoral, Administrativo, Persona, MesasPadronElectoral, \
    TIPO_PERSONA_PADRON, JustificacionPersonaPadronElectoral, HistorialJustificacionPersonaPadronElectoral, \
    Coordinacion, ESTADO_JUSTIFICACION, Canton, Provincia, Pais, Parroquia, Matricula, CUENTAS_CORREOS, \
    TipoSolicitudInformacionPadronElectoral, ESTADO_SOLICITUD_INFORMACION, SolicitudInformacionPadronElectoral, Reporte
from sagest.models import Bloque, Rubro
from django.db.models import Sum, Q, F, FloatField, IntegerField
from django.db.models.functions import Coalesce
from sga.templatetags.sga_extras import encrypt
from .reportes import transform_jasperstarter_kwargs
from .tasks import send_html_mail
from xhtml2pdf import pisa
import io as StringIO


def generar_notificacion_mesa_pdf(request, data, id, personaid, tipo):
    if not DEBUG:
        filtro = ConfiguracionMesaResponsable.objects.get(pk=id)
        personamesa = DetPersonaPadronElectoral.objects.get(pk=personaid)
        data['hoy'] = hoy = datetime.now().date()
        data['personamesa'] = personamesa
        data['info_mesa'] = personamesa.info_mesa()
        data['filtro'] = filtro
        template_pdf = 'adm_padronelectoral/pdf_notificacion_mesa.html'
        ruta1, ruta2 = 'padronelectoral', 'actas'
        directory_principal = os.path.join(SITE_STORAGE, 'media', ruta1)
        try:
            os.stat(directory_principal)
        except:
            os.mkdir(directory_principal)
        directory = os.path.join(SITE_STORAGE, 'media', ruta1, ruta2)
        try:
            os.stat(directory)
        except:
            os.mkdir(directory)
        nombrepersona = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode((personamesa.persona.__str__()).replace(' ', '_')))
        cargo = ''
        if tipo == 1:
            cargo = 'PRESIDENTE(A)'
        elif tipo == 2:
            cargo = 'SECRETARIO(A)'
        elif tipo == 3:
            cargo = 'VOCAL'
        elif tipo == 4:
            cargo = 'PRESIDENTE ALTERNO'
        elif tipo == 5:
            cargo = 'SECRETARIO(A) ALTERNO'
        elif tipo == 6:
            cargo = 'VOCAL ALTERNO'
        nombredocumento = 'NOTIFICACION_{}_{}_{}'.format(cargo, nombrepersona, random.randint(1, 100000).__str__())
        valida = conviert_html_to_pdf_parametros_save(template_pdf, {'pagesize': 'A4', 'data': data, }, nombredocumento, ruta1, ruta2)
        archivo = None
        if valida:
            if tipo == 1:
                filtro.acta_presidente = "{}/{}/{}.pdf".format(ruta1, ruta2, nombredocumento)
                filtro.fecha_notificacion_presidente = hoy
            elif tipo == 2:
                filtro.acta_secretario = "{}/{}/{}.pdf".format(ruta1, ruta2, nombredocumento)
                filtro.fecha_notificacion_secretario = hoy
            elif tipo == 3:
                filtro.acta_vocal = "{}/{}/{}.pdf".format(ruta1, ruta2, nombredocumento)
                filtro.fecha_notificacion_vocal = hoy
            elif tipo == 4:
                filtro.acta_presidente_alterno = "{}/{}/{}.pdf".format(ruta1, ruta2, nombredocumento)
                filtro.fecha_notificacion_presidente_alterno = hoy
            elif tipo == 5:
                filtro.acta_secretario_alterno = "{}/{}/{}.pdf".format(ruta1, ruta2, nombredocumento)
                filtro.fecha_notificacion_secretario_alterno = hoy
            elif tipo == 6:
                filtro.acta_vocal_alterno = "{}/{}/{}.pdf".format(ruta1, ruta2, nombredocumento)
                filtro.fecha_notificacion_vocal_alterno = hoy
            filtro.save(request)
            if tipo == 1:
                archivo = filtro.acta_presidente
            elif tipo == 2:
                archivo = filtro.acta_secretario
            elif tipo == 3:
                archivo = filtro.acta_vocal
            elif tipo == 4:
                archivo = filtro.acta_presidente_alterno
            elif tipo == 5:
                archivo = filtro.acta_secretario_alterno
            elif tipo == 6:
                archivo = filtro.acta_vocal_alterno
        return archivo
    return False


def mostrar_mesa_pdf(request, data, id, personaid, tipo):
    personas_lista = []
    filtro = ConfiguracionMesaResponsable.objects.get(pk=id)
    personamesa = DetPersonaPadronElectoral.objects.get(pk=personaid)
    # data['hoy'] = hoy = datetime(2022, 1, 11) if not personamesa.persona_id in personas_lista else datetime(2022, 1, 21)
    data['hoy'] = hoy = datetime.now().date()
    data['personamesa'] = personamesa
    data['info_mesa'] = personamesa.info_mesa()
    data['filtro'] = filtro
    template_pdf = 'adm_padronelectoral/pdf_notificacion_mesa.html'
    ruta1, ruta2 = 'padronelectoral', 'actas'
    directory_principal = os.path.join(SITE_STORAGE, 'media', ruta1)
    try:
        os.stat(directory_principal)
    except:
        os.mkdir(directory_principal)
    directory = os.path.join(SITE_STORAGE, 'media', ruta1, ruta2)
    try:
        os.stat(directory)
    except:
        os.mkdir(directory)
    nombrepersona = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode((personamesa.persona.__str__()).replace(' ', '_')))
    cargo = ''
    if tipo == 1:
        cargo = 'PRESIDENTE(A)'
    elif tipo == 2:
        cargo = 'SECRETARIO(A)'
    elif tipo == 3:
        cargo = 'VOCAL'
    elif tipo == 4:
        cargo = 'PRESIDENTE ALTERNO'
    elif tipo == 5:
        cargo = 'SECRETARIO(A) ALTERNO'
    elif tipo == 6:
        cargo = 'VOCAL ALTERNO'
    nombredocumento = 'MESA_{}_NOTIFICACION_{}_{}_{}'.format(filtro.mesa.orden, cargo, nombrepersona, random.randint(1, 100000).__str__())
    valida = conviert_html_to_pdf_parametros_save(template_pdf, {'pagesize': 'A4', 'data': data, }, nombredocumento, ruta1, ruta2)
    archivo = ''
    if valida:
        if tipo == 1:
            filtro.acta_presidente = "{}/{}/{}.pdf".format(ruta1, ruta2, nombredocumento)
            filtro.fecha_notificacion_presidente = hoy
        elif tipo == 2:
            filtro.acta_secretario = "{}/{}/{}.pdf".format(ruta1, ruta2, nombredocumento)
            filtro.fecha_notificacion_secretario = hoy
        elif tipo == 3:
            filtro.acta_vocal = "{}/{}/{}.pdf".format(ruta1, ruta2, nombredocumento)
            filtro.fecha_notificacion_vocal = hoy
        elif tipo == 4:
            filtro.acta_presidente_alterno = "{}/{}/{}.pdf".format(ruta1, ruta2, nombredocumento)
            filtro.fecha_notificacion_presidente_alterno = hoy
        elif tipo == 5:
            filtro.acta_secretario_alterno = "{}/{}/{}.pdf".format(ruta1, ruta2, nombredocumento)
            filtro.fecha_notificacion_secretario_alterno = hoy
        elif tipo == 6:
            filtro.acta_vocal_alterno = "{}/{}/{}.pdf".format(ruta1, ruta2, nombredocumento)
            filtro.fecha_notificacion_vocal_alterno = hoy
        filtro.save(request)
        if tipo == 1:
            archivo = filtro.acta_presidente
        elif tipo == 2:
            archivo = filtro.acta_secretario
        elif tipo == 3:
            archivo = filtro.acta_vocal
        elif tipo == 4:
            archivo = filtro.acta_presidente_alterno
        elif tipo == 5:
            archivo = filtro.acta_secretario_alterno
        elif tipo == 6:
            archivo = filtro.acta_vocal_alterno
    return archivo


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
# @last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    try:
        persona = request.session['persona']
        periodo = request.session['periodo']
    except Exception as ex:
        pass

    data['title'] = u'Padron Electoral'
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                with transaction.atomic():
                    form = CabPadronElectoralForm(request.POST)
                    if form.is_valid():
                        filtro = CabPadronElectoral(nombre=form.cleaned_data['nombre'].upper(), fecha=form.cleaned_data['fecha'],
                                                    activo=form.cleaned_data['activo'],
                                                    puede_justificar=form.cleaned_data['puede_justificar'],
                                                    utiliza_sede=form.cleaned_data['utiliza_sede'],
                                                    activo_ingreso_acta=form.cleaned_data['activo_ingreso_acta'],
                                                    asignacion_aleatoria=form.cleaned_data['asignacion_aleatoria'],
                                                    periodo=form.cleaned_data['periodo'],
                                                    fechalimiteconfirmacionsede=form.cleaned_data['fechalimiteconfirmacionsede'],
                                                    porcentaje_estudiantes=form.cleaned_data['porcentaje_estudiantes'],
                                                    porcentaje_administrativos=form.cleaned_data['porcentaje_administrativos'],
                                                    texto_docente=form.cleaned_data['texto_docente'],
                                                    texto_estudiantes=form.cleaned_data['texto_estudiantes'],
                                                    texto_administrativos=form.cleaned_data['texto_administrativos'],
                                                    confirmacion_sede=form.cleaned_data['confirmacion_sede'])
                        filtro.save(request)
                        log(u'Adiciono Padron Electoral: %s' % filtro, request, "add")
                        # return JsonResponse({"result": False,'to':'/nuevaurl'}, safe=False) SI DESEAS REDIRECCIONAR ADICIONARLE TO A LA RESPUESTA
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'edit':
            try:
                with transaction.atomic():
                    filtro = CabPadronElectoral.objects.get(pk=request.POST['id'])
                    f = CabPadronElectoralForm(request.POST)
                    if f.is_valid():
                        filtro.nombre = f.cleaned_data['nombre'].upper()
                        filtro.fecha = f.cleaned_data['fecha']
                        filtro.activo = f.cleaned_data['activo']
                        filtro.puede_justificar = f.cleaned_data['puede_justificar']
                        filtro.activo_ingreso_acta = f.cleaned_data['activo_ingreso_acta']
                        filtro.utiliza_sede = f.cleaned_data['utiliza_sede']
                        filtro.periodo = f.cleaned_data['periodo']
                        filtro.confirmacion_sede = f.cleaned_data['confirmacion_sede']
                        filtro.asignacion_aleatoria = f.cleaned_data['asignacion_aleatoria']
                        filtro.fechalimiteconfirmacionsede = f.cleaned_data['fechalimiteconfirmacionsede']
                        filtro.porcentaje_estudiantes = f.cleaned_data['porcentaje_estudiantes']
                        filtro.porcentaje_administrativos = f.cleaned_data['porcentaje_administrativos']
                        filtro.texto_docente = f.cleaned_data['texto_docente']
                        filtro.texto_estudiantes = f.cleaned_data['texto_estudiantes']
                        filtro.texto_administrativos = f.cleaned_data['texto_administrativos']
                        filtro.save(request)
                        log(u'Modificó Padron Electoral: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'del':
            try:
                with transaction.atomic():
                    id = request.POST['id']
                    filtro = CabPadronElectoral.objects.get(pk=id)
                    filtro.status = False
                    filtro.save(request)
                    log(u'Elimino Evento Electoral: %s' % filtro, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": str(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'importar_personas':
            try:
                with transaction.atomic():
                    cab = request.POST['cab']
                    cedula = request.POST['cedula']
                    nombres = request.POST['nombres']
                    tpersona = int(request.POST['tipo'])
                    # bloque = request.POST['bloque']
                    # mesa = request.POST['mesa']
                    # horario = request.POST['horario']
                    lugar = request.POST['lugar']
                    # mesaqs = None
                    # bloqueid = [b.pk for b in Bloque.objects.filter(status=True) if bloque in str(b.descripcion.replace('"',''))]
                    # bloqueqs = Bloque.objects.get(pk=bloqueid[0])
                    # if not MesasPadronElectoral.objects.filter(status=True, nombre=mesa).exists():
                    #     mesaqs = MesasPadronElectoral(nombre=mesa)
                    #     mesaqs.save(request)
                    # else:
                    #     mesaqs = MesasPadronElectoral.objects.filter(status=True, nombre=mesa).first()
                    if Persona.objects.filter(cedula=cedula, status=True).exists():
                        filtro_per = Persona.objects.filter(cedula=cedula, status=True).first()
                        if not DetPersonaPadronElectoral.objects.filter(cab_id=cab, persona=filtro_per, tipo=tpersona).exists():
                            # print('{}, {} - {} - {}'.format(filtro_per.__str__(), bloque, mesa, horario))
                            detalle = DetPersonaPadronElectoral(cab_id=cab, persona=filtro_per, tipo=tpersona, bloque=None, mesa=None, horario=None, lugar=lugar)
                            detalle.save(request)
                            log(u'Agrego al persona al padron electoral: %s' % detalle, request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                            filtro = DetPersonaPadronElectoral.objects.filter(cab_id=cab, persona=filtro_per, tipo=tpersona).first()
                            filtro.lugar = lugar
                            filtro.save(request)
                            return JsonResponse({"result": "ok", "mensaje": u"Registro ya existente.", "exists": True})
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Persona no existe."})
            except Exception as ex:
                print(ex)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'importar_personas_mesa':
            try:
                with transaction.atomic():
                    cab = request.POST['cab']
                    cedula = request.POST['cedula']
                    nombres = request.POST['nombres']
                    tpersona = int(request.POST['tipo'])
                    lugar = request.POST['lugar']
                    if Persona.objects.filter(cedula=cedula, status=True).exists():
                        filtro_per = Persona.objects.filter(cedula=cedula, status=True).first()
                        if DetPersonaPadronElectoral.objects.filter(cab_id=cab, persona=filtro_per, tipo=tpersona).exists():
                            detalle = DetPersonaPadronElectoral.objects.filter(cab_id=cab, persona=filtro_per, tipo=tpersona).first()
                            detalle.enmesa = True
                            detalle.lugarmesa = lugar
                            detalle.save(request)
                            log(u'Edito al personal del padron electoral, en mesa: %s' % detalle, request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": "bad", "mensaje": u"Empadronamiento de {} no existe.".format(filtro_per.__str__())})
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"{} - {} Persona no existe.".format(cedula, nombres)})
            except Exception as ex:
                print(ex)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addobservacion':
            try:
                with transaction.atomic():
                    filtro = JustificacionPersonaPadronElectoral.objects.get(pk=int(request.POST['id']))
                    form = DetalleJustificativoForm(request.POST)
                    if form.is_valid():
                        filtro.estados_justificacion = form.cleaned_data['accion']
                        if form.cleaned_data['accion'] == '1':
                            inscripcion = DetPersonaPadronElectoral.objects.get(pk=filtro.inscripcion.pk)
                            inscripcion.puede_justificar = True
                            inscripcion.save(request)
                        else:
                            inscripcion = DetPersonaPadronElectoral.objects.get(pk=filtro.inscripcion.pk)
                            inscripcion.puede_justificar = False
                            inscripcion.save(request)
                        filtro.save(request)
                        soli = HistorialJustificacionPersonaPadronElectoral(justificativo=filtro,
                                                                            detalle=form.cleaned_data['detalle'].upper(),
                                                                            accion=form.cleaned_data['accion'])
                        soli.save(request)

                        asunto = u"RESPUESTA JUSTIFICATIVO OMISIÓN DE SUFRAGIO"
                        para = soli.justificativo.inscripcion.persona
                        observacion = 'SU SOLICITUD FUE {}'.format(soli.get_accion_display())
                        notificacion(asunto, observacion, para, None, '/alu_procesoelectoral', soli.pk, 1, 'sga', HistorialJustificacionPersonaPadronElectoral, request)

                        log(u'Adiciono Observación en Justificación Omisión de Sufragio: %s' % soli, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'validarsolicitudesinformacion':
            try:
                with transaction.atomic():
                    filtro = SolicitudInformacionPadronElectoral.objects.get(pk=int(request.POST['id']))
                    form = ValidarSolicitudesForm(request.POST)
                    if form.is_valid():
                        filtro.estados = form.cleaned_data['estados']
                        filtro.respuesta = form.cleaned_data['respuesta']
                        filtro.validadopor = persona
                        filtro.fechavalidacion = datetime.now()
                        filtro.save(request)
                        url_ = '/pro_procesoelectoral'
                        if filtro.persona.es_profesor():
                            url_ = '/pro_procesoelectoral'
                        elif filtro.persona.es_administrativo():
                            url_ = '/pro_procesoelectoral'
                        else:
                            url_ = '/alu_procesoelectoral'
                        asunto = u"RESPUESTA - SOLICITUD DE INFORMACIÓN PROCESO ELECTORAL"
                        para = filtro.persona
                        observacion = 'SU SOLICITUD FUE {}'.format(filtro.get_estados_display().upper())
                        notificacion(asunto, observacion, para, None, url_, filtro.pk, 1, 'sga', HistorialJustificacionPersonaPadronElectoral, request)

                        log(u'Validar Solicitud de Información Proceso Electoral: %s' % filtro, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'addmesa':
            try:
                with transaction.atomic():
                    form = MesaPadronForm(request.POST)
                    if form.is_valid():
                        filtro = MesasPadronElectoral(periodo=form.cleaned_data['periodo'], nombre=form.cleaned_data['nombre'].upper(), orden=form.cleaned_data['orden'])
                        filtro.save(request)
                        log(u'Adiciono Mesa Padron Electoral: %s' % filtro, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editmesa':
            try:
                with transaction.atomic():
                    filtro = MesasPadronElectoral.objects.get(pk=request.POST['id'])
                    f = MesaPadronForm(request.POST)
                    if f.is_valid():
                        filtro.periodo = f.cleaned_data['periodo']
                        filtro.nombre = f.cleaned_data['nombre'].upper()
                        filtro.orden = f.cleaned_data['orden']
                        filtro.save(request)
                        log(u'Modificó Mesa Padron Electoral: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deletemesa':
            try:
                with transaction.atomic():
                    instancia = MesasPadronElectoral.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Mesa de Padron Electoral: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'deletedignidad':
            try:
                with transaction.atomic():
                    instancia = DignidadesElectorales.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Dignidad Electoral: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'deletesolicituddignidad':
            try:
                with transaction.atomic():
                    instancia = SolicitudDignidadesElectorales.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Solicitud Dignidad Electoral: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addlista':
            try:
                with transaction.atomic():
                    form = ListaPadronForm(request.POST)
                    if form.is_valid():
                        filtro = ListaElectoral(nombre=form.cleaned_data['nombre'].upper())
                        filtro.save(request)
                        log(u'Adiciono Lista Padron Electoral: %s' % filtro, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editlista':
            try:
                with transaction.atomic():
                    filtro = ListaElectoral.objects.get(pk=request.POST['id'])
                    f = ListaPadronForm(request.POST)
                    if f.is_valid():
                        filtro.nombre = f.cleaned_data['nombre'].upper()
                        filtro.save(request)
                        log(u'Modificó Lista Padron Electoral: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deletelista':
            try:
                with transaction.atomic():
                    instancia = ListaElectoral.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Lista de Padron Electoral: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addgremio':
            try:
                with transaction.atomic():
                    form = GremioPadronForm(request.POST)
                    if form.is_valid():
                        filtro = GremioElectoral(nombre=form.cleaned_data['nombre'].upper())
                        filtro.save(request)
                        log(u'Adiciono Gremio Padron Electoral: %s' % filtro, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editgremio':
            try:
                with transaction.atomic():
                    filtro = GremioElectoral.objects.get(pk=request.POST['id'])
                    f = GremioPadronForm(request.POST)
                    if f.is_valid():
                        filtro.nombre = f.cleaned_data['nombre'].upper()
                        filtro.save(request)
                        log(u'Modificó Gremio Padron Electoral: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deletegremio':
            try:
                with transaction.atomic():
                    instancia = GremioPeriodo.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Gremio de Padron Electoral: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addgremioperiodo':
            try:
                with transaction.atomic():
                    padron = CabPadronElectoral.objects.get(pk=request.POST['id'])
                    if request.POST['coordinacion']:
                        if GremioPeriodo.objects.filter(periodo=padron, coordinacion=request.POST['coordinacion'], tipo=request.POST['tipo'], gremio=request.POST['gremio'], status=True).exists():
                            transaction.set_rollback(True)
                            return JsonResponse({'error': True, "message": 'Ya existe gremio con esta configuración.'}, safe=False)
                    form = GremioPeriodoForm(request.POST)
                    if form.is_valid():
                        instance = GremioPeriodo(periodo=padron,
                                                 coordinacion=form.cleaned_data['coordinacion'],
                                                 gremio=form.cleaned_data['gremio'],
                                                 tipo=form.cleaned_data['tipo'])
                        instance.save(request)
                        for lista in request.POST.getlist('listas'):
                            listasgremios = ListaGremio(gremio_periodo=instance, lista_id=int(lista))
                            listasgremios.save(request)
                        log(u'Adiciono Gremio Periodo: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editgremioperiodo':
            try:
                with transaction.atomic():
                    filtro = GremioPeriodo.objects.get(pk=request.POST['id'])
                    f = GremioPeriodoForm(request.POST)
                    if f.is_valid():
                        filtro.gremio = f.cleaned_data['gremio']
                        filtro.coordinacion = f.cleaned_data['coordinacion']
                        filtro.tipo = f.cleaned_data['tipo']
                        filtro.save(request)
                        listids = request.POST.getlist('listas')
                        listagremios = ListaGremio.objects.filter(status=True, gremio_periodo=filtro, lista__in=listids)
                        for li in ListaGremio.objects.filter(status=True, gremio_periodo=filtro).exclude(id__in=listagremios.values_list('id', flat=True)):
                            li.status = False
                            li.save(request)
                        for lista in request.POST.getlist('listas'):
                            if not ListaGremio.objects.filter(status=True, gremio_periodo=filtro, lista_id=lista).exists():
                                listasgremios = ListaGremio(gremio_periodo=filtro, lista_id=int(lista))
                                listasgremios.save(request)
                        log(u'Modificó Gremio Periodo Padron Electoral: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deletegremio':
            try:
                with transaction.atomic():
                    instancia = GremioPeriodo.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Gremio Periodo de Padron Electoral: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addempadronado':
            try:
                with transaction.atomic():
                    padron = CabPadronElectoral.objects.get(pk=request.POST['id'])
                    if DetPersonaPadronElectoral.objects.filter(cab=padron, persona=request.POST['persona'], tipo=request.POST['tipo'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Persona ya esta empadronado.'}, safe=False)
                    form = PersonaEmpadronadoForm(request.POST)
                    if form.is_valid():
                        instance = DetPersonaPadronElectoral(cab=padron,
                                                             persona=form.cleaned_data['persona'],
                                                             mesa=form.cleaned_data['mesa'],
                                                             validado=form.cleaned_data['validado'],
                                                             lugar=form.cleaned_data['lugar'],
                                                             lugarsede=form.cleaned_data['lugarsede'],
                                                             enmesa=form.cleaned_data['enmesa'],
                                                             lugarmesa=form.cleaned_data['lugarmesa'],
                                                             excluir=form.cleaned_data['excluir'],
                                                             codigo_qr=form.cleaned_data['codigo_qr'],
                                                             puede_justificar=form.cleaned_data['puede_justificar'])
                        instance.save(request)
                        log(u'Adiciono Empadronado a Periodo Electoral: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editempadronado':
            try:
                with transaction.atomic():
                    filtro = DetPersonaPadronElectoral.objects.get(pk=request.POST['id'])
                    f = PersonaEmpadronadoForm(request.POST)
                    if f.is_valid():
                        filtro.codigo_qr = f.cleaned_data['codigo_qr']
                        filtro.validado = f.cleaned_data['validado']
                        filtro.tipo = f.cleaned_data['tipo']
                        filtro.lugar = f.cleaned_data['lugar']
                        filtro.mesa = f.cleaned_data['mesa']
                        filtro.lugarsede = f.cleaned_data['lugarsede']
                        filtro.persona = f.cleaned_data['persona']
                        filtro.puede_justificar = f.cleaned_data['puede_justificar']
                        filtro.enmesa = f.cleaned_data['enmesa']
                        filtro.lugarmesa = f.cleaned_data['lugarmesa']
                        filtro.excluir = f.cleaned_data['excluir']
                        filtro.save(request)
                        log(u'Edito Empadronado a Periodo Electoral: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deleteempadronado':
            try:
                with transaction.atomic():
                    instancia = DetPersonaPadronElectoral.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Empadronado de Padron Electoral: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addsolicituddignidad':
            try:
                with transaction.atomic():
                    newfile = None
                    if 'solicitud' in request.FILES:
                        newfile = request.FILES['solicitud']
                        if newfile:
                            if newfile.size > 10194304:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if not ext in ['.pdf', '.jpg', '.jpeg', '.png', '.jpeg', '.peg']:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf, jpg, jpeg."})
                    dignidad = DignidadesElectorales.objects.get(pk=request.POST['id'])
                    if SolicitudDignidadesElectorales.objects.filter(dignidad=dignidad, persona=request.POST['persona'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Persona ya subio documentación.'}, safe=False)
                    form = SolicitudDignidadForm(request.POST, request.FILES)
                    if form.is_valid():
                        instance = SolicitudDignidadesElectorales(dignidad=dignidad, persona=form.cleaned_data['persona'])
                        instance.save(request)
                        if 'solicitud' in request.FILES:
                            nombrepersona = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode((instance.persona.__str__()).replace(' ', '_')))
                            nombredocumento = '{}_{}'.format(nombrepersona, random.randint(1, 100000).__str__())
                            newfile._name = generar_nombre(nombredocumento, newfile._name)
                            instance.solicitud = newfile
                            instance.save(request)
                        for ins in instance.dignidad.requisitos():
                            if not RequisitoSolicitudDignidadesElectorales.objects.filter(solicitud=instance, requisito=ins, status=True):
                                req = RequisitoSolicitudDignidadesElectorales(solicitud=instance, requisito=ins)
                                req.save(request)
                        log(u'Adiciono Solicitud Dignidad: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editsolicituddignidad':
            try:
                with transaction.atomic():
                    newfile = None
                    if 'solicitud' in request.FILES:
                        newfile = request.FILES['solicitud']
                        if newfile:
                            if newfile.size > 10194304:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if not ext in ['.pdf', '.jpg', '.jpeg', '.png', '.jpeg', '.peg']:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf, jpg, jpeg."})
                    filtro = SolicitudDignidadesElectorales.objects.get(pk=request.POST['id'])
                    f = SolicitudDignidadForm(request.POST, request.FILES)
                    if f.is_valid():
                        filtro.persona = f.cleaned_data['persona']
                        filtro.save(request)
                        if 'solicitud' in request.FILES:
                            nombrepersona = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode((filtro.persona.__str__()).replace(' ', '_')))
                            nombredocumento = '{}_{}'.format(nombrepersona, random.randint(1, 100000).__str__())
                            newfile._name = generar_nombre(nombredocumento, newfile._name)
                            filtro.solicitud = newfile
                            filtro.save(request)
                        excludeids = filtro.dignidad.requisitos().values_list('pk', flat=True)
                        RequisitoSolicitudDignidadesElectorales.objects.filter(solicitud=filtro, status=True).exclude(requisito__in=excludeids).update(status=False)
                        for f in filtro.dignidad.requisitos():
                            if not RequisitoSolicitudDignidadesElectorales.objects.filter(solicitud=filtro, requisito=f, status=True):
                                req = RequisitoSolicitudDignidadesElectorales(solicitud=filtro, requisito=f)
                                req.save(request)
                        log(u'Edito Solicitud Dignidad: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Intentelo más tarde. {ex}"}, safe=False)

        elif action == 'addconfmesa':
            try:
                with transaction.atomic():
                    padron = CabPadronElectoral.objects.get(pk=request.POST['id'])
                    if ConfiguracionMesaResponsable.objects.filter(periodo=padron, tipo=request.POST['tipo'], mesa_id=request.POST['mesa'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Ya existe configuración con esta mesa y tipo.'}, safe=False)
                    form = ConfiguracionMesaResponsableForm(request.POST)
                    if form.is_valid():
                        instance = ConfiguracionMesaResponsable(periodo=padron,
                                                                mesa=form.cleaned_data['mesa'],
                                                                presidente=form.cleaned_data['presidente'],
                                                                secretario=form.cleaned_data['secretario'],
                                                                vocal=form.cleaned_data['vocal'],
                                                                presidente_alterno=form.cleaned_data['presidente_alterno'],
                                                                secretario_alterno=form.cleaned_data['secretario_alterno'],
                                                                vocal_alterno=form.cleaned_data['vocal_alterno'],
                                                                totalempadronados=form.cleaned_data['totalempadronados'],
                                                                abierta=form.cleaned_data['abierta'],
                                                                tipo=form.cleaned_data['tipo'],
                                                                sede=form.cleaned_data['sede'])
                        instance.save(request)
                        if form.cleaned_data['logistica']:
                            perLogistica = form.cleaned_data['logistica']
                            for pl in perLogistica:
                                instance.logistica.add(pl)
                        instance.save(request)
                        log(u'Adiciono Configuracion Mesa Periodo: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Intentelo más tarde. {ex}"}, safe=False)

        elif action == 'editconfmesa':
            try:
                with transaction.atomic():
                    filtro = ConfiguracionMesaResponsable.objects.get(pk=request.POST['id'])
                    f = ConfiguracionMesaResponsableForm(request.POST)
                    if f.is_valid():
                        filtro.tipo = f.cleaned_data['tipo']
                        filtro.mesa = f.cleaned_data['mesa']
                        filtro.presidente = f.cleaned_data['presidente']
                        filtro.secretario = f.cleaned_data['secretario']
                        filtro.vocal = f.cleaned_data['vocal']
                        filtro.presidente_alterno = f.cleaned_data['presidente_alterno']
                        filtro.secretario_alterno = f.cleaned_data['secretario_alterno']
                        filtro.vocal_alterno = f.cleaned_data['vocal_alterno']
                        filtro.totalempadronados = f.cleaned_data['totalempadronados']
                        filtro.abierta = f.cleaned_data['abierta']
                        filtro.sede = f.cleaned_data['sede']
                        filtro.logistica.clear()
                        if f.cleaned_data['logistica']:
                            perLogistica = f.cleaned_data['logistica']
                            for pl in perLogistica:
                                filtro.logistica.add(pl)
                        filtro.save(request)
                        log(u'Modificó Configuración de Mesa Padron Electoral: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deleterespmesa':
            try:
                with transaction.atomic():
                    instancia = ConfiguracionMesaResponsable.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Configuración de Mesa de Padron Electoral: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'editgremiosconfmesa':
            try:
                with transaction.atomic():
                    lista_items = json.loads(request.POST['lista_items1'])
                    if lista_items.__len__() == 0:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Debe asignar gremios"}, safe=False)
                    listaids = list([int(ls['id']) for ls in lista_items])
                    conf = ConfiguracionMesaResponsable.objects.get(pk=int(request.POST['id']))
                    lista_gremios = GremioPeriodo.objects.filter(status=True, pk__in=listaids)
                    listMesas = DetalleMesa.objects.filter(status=True, mesa_responsable=conf)
                    for li in listMesas.exclude(gremio_periodo__in=lista_gremios.values_list('id', flat=True)):
                        li.status = False
                        li.save(request)
                    for lista in listaids:
                        if not DetalleMesa.objects.filter(status=True, mesa_responsable=conf, gremio_periodo_id=lista).exists():
                            listasgremios = DetalleMesa(mesa_responsable=conf, gremio_periodo_id=int(lista))
                            listasgremios.save(request)
                    log(u'Adiciono Gremios a Mesa Responsable %s' % conf, request, "add")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'asignarresponsablemesa':
            try:
                with transaction.atomic():
                    presidente, secretario, vocal = request.POST.get('presidente', ''), request.POST.get('secretario', ''), request.POST.get('vocal', '')
                    conf = ConfiguracionMesaResponsable.objects.get(pk=int(request.POST['id']))
                    if presidente:
                        conf.presidente = DetPersonaPadronElectoral.objects.get(pk=presidente)
                        conf.save(request)
                        asunto = u"ASIGNACIÓN DE MIEMBRO DE MESA ELECTORAL - {}".format(conf.periodo.nombre)
                        pdf_acta = generar_notificacion_mesa_pdf(request, data, conf.id, conf.presidente.id, 1)
                        datos = {'persona': conf.presidente.persona, }
                        datos['hoy'] = hoy = datetime.now().date()
                        datos['personamesa'] = conf.presidente
                        datos['info_mesa'] = conf.presidente.info_mesa()
                        datos['filtro'] = conf
                        if variable_valor('NO_ENVIAR_CORREO_ELECCIONES2023'):
                            send_html_mail(asunto, "emails/email_miembro_mesa_elecciones.html",
                                       datos, ['rviterib1@unemi.edu.ec', 'kpalaciosz@unemi.edu.ec'], [], [pdf_acta], cuenta=CUENTAS_CORREOS[0][1])
                        else:
                            send_html_mail(asunto, "emails/email_miembro_mesa_elecciones.html",
                                       datos, [conf.presidente.persona.emailinst], [], [pdf_acta], cuenta=CUENTAS_CORREOS[0][1])
                    if secretario:
                        conf.secretario = DetPersonaPadronElectoral.objects.get(pk=secretario)
                        conf.save(request)
                        asunto = u"ASIGNACIÓN DE MIEMBRO DE MESA ELECTORAL - {}".format(conf.periodo.nombre)
                        pdf_acta = generar_notificacion_mesa_pdf(request, data, conf.id, conf.secretario.id, 2)
                        datos = {'persona': conf.secretario.persona, }
                        datos['hoy'] = hoy = datetime.now().date()
                        datos['personamesa'] = conf.secretario
                        datos['info_mesa'] = conf.secretario.info_mesa()
                        datos['filtro'] = conf
                        if variable_valor('NO_ENVIAR_CORREO_ELECCIONES2023'):
                            send_html_mail(asunto, "emails/email_miembro_mesa_elecciones.html",
                                       datos, ['rviterib1@unemi.edu.ec', 'kpalaciosz@unemi.edu.ec'], [], [pdf_acta], cuenta=CUENTAS_CORREOS[0][1])
                        else:
                            send_html_mail(asunto, "emails/email_miembro_mesa_elecciones.html",
                                       datos, [conf.secretario.persona.emailinst], [], [pdf_acta], cuenta=CUENTAS_CORREOS[0][1])
                    if vocal:
                        conf.vocal = DetPersonaPadronElectoral.objects.get(pk=vocal)
                        conf.save(request)
                        asunto = u"ASIGNACIÓN DE MIEMBRO DE MESA ELECTORAL - {}".format(conf.periodo.nombre)
                        pdf_acta = generar_notificacion_mesa_pdf(request, data, conf.id, conf.vocal.id, 3)
                        datos = {'persona': conf.vocal.persona, }
                        datos['hoy'] = hoy = datetime.now().date()
                        datos['personamesa'] = conf.vocal
                        datos['info_mesa'] = conf.vocal.info_mesa()
                        datos['filtro'] = conf
                        if variable_valor('NO_ENVIAR_CORREO_ELECCIONES2023'):
                            send_html_mail(asunto, "emails/email_miembro_mesa_elecciones.html",
                                       datos, ['rviterib1@unemi.edu.ec', 'kpalaciosz@unemi.edu.ec'], [], [pdf_acta], cuenta=CUENTAS_CORREOS[0][1])
                        else:
                            send_html_mail(asunto, "emails/email_miembro_mesa_elecciones.html",
                                       datos, [conf.vocal.persona.emailinst], [], [pdf_acta], cuenta=CUENTAS_CORREOS[0][1])
                    log(u'Adiciono Random Responsable Mesa %s' % conf, request, "add")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Intentelo más tarde. {ex}"}, safe=False)

        elif action == 'asignarresponsablemesaalterno':
            try:
                with transaction.atomic():
                    presidente, secretario, vocal = request.POST.get('presidente', ''), request.POST.get('secretario', ''), request.POST.get('vocal', '')
                    conf = ConfiguracionMesaResponsable.objects.get(pk=int(request.POST['id']))
                    if presidente:
                        conf.presidente_alterno = DetPersonaPadronElectoral.objects.get(pk=presidente)
                        conf.save(request)
                        asunto = u"ASIGNACIÓN DE MIEMBRO DE MESA ELECTORAL - {}".format(conf.periodo.nombre)
                        pdf_acta = generar_notificacion_mesa_pdf(request, data, conf.id, conf.presidente_alterno.id, 4)
                        datos = {'persona': conf.presidente_alterno.persona, }
                        datos['hoy'] = hoy = datetime.now().date()
                        datos['personamesa'] = conf.presidente_alterno
                        datos['info_mesa'] = conf.presidente_alterno.info_mesa()
                        datos['filtro'] = conf
                        if variable_valor('NO_ENVIAR_CORREO_ELECCIONES2023'):
                            send_html_mail(asunto, "emails/email_miembro_mesa_elecciones.html",
                                       datos, ['rviterib1@unemi.edu.ec', 'kpalaciosz@unemi.edu.ec'], [], [pdf_acta], cuenta=CUENTAS_CORREOS[0][1])
                        else:
                            send_html_mail(asunto, "emails/email_miembro_mesa_elecciones.html",
                                       datos, [conf.presidente_alterno.persona.emailinst], [], [pdf_acta], cuenta=CUENTAS_CORREOS[0][1])
                    if secretario:
                        conf.secretario_alterno = DetPersonaPadronElectoral.objects.get(pk=secretario)
                        conf.save(request)
                        asunto = u"ASIGNACIÓN DE MIEMBRO DE MESA ELECTORAL - {}".format(conf.periodo.nombre)
                        pdf_acta = generar_notificacion_mesa_pdf(request, data, conf.id, conf.secretario_alterno.id, 5)
                        datos = {'persona': conf.secretario_alterno.persona, }
                        datos['hoy'] = hoy = datetime.now().date()
                        datos['personamesa'] = conf.secretario_alterno
                        datos['info_mesa'] = conf.secretario_alterno.info_mesa()
                        datos['filtro'] = conf
                        if variable_valor('NO_ENVIAR_CORREO_ELECCIONES2023'):
                            send_html_mail(asunto, "emails/email_miembro_mesa_elecciones.html",
                                       datos, ['rviterib1@unemi.edu.ec', 'kpalaciosz@unemi.edu.ec'], [], [pdf_acta], cuenta=CUENTAS_CORREOS[0][1])
                        else:
                            send_html_mail(asunto, "emails/email_miembro_mesa_elecciones.html",
                                       datos, [conf.secretario_alterno.persona.emailinst], [], [pdf_acta], cuenta=CUENTAS_CORREOS[0][1])
                    if vocal:
                        conf.vocal_alterno = DetPersonaPadronElectoral.objects.get(pk=vocal)
                        conf.save(request)
                        asunto = u"ASIGNACIÓN DE MIEMBRO DE MESA ELECTORAL - {}".format(conf.periodo.nombre)
                        pdf_acta = generar_notificacion_mesa_pdf(request, data, conf.id, conf.vocal_alterno.id, 6)
                        datos = {'persona': conf.vocal_alterno.persona, }
                        datos['hoy'] = hoy = datetime.now().date()
                        datos['personamesa'] = conf.vocal_alterno
                        datos['info_mesa'] = conf.vocal_alterno.info_mesa()
                        datos['filtro'] = conf
                        if variable_valor('NO_ENVIAR_CORREO_ELECCIONES2023'):
                            send_html_mail(asunto, "emails/email_miembro_mesa_elecciones.html",
                                       datos, ['rviterib1@unemi.edu.ec', 'kpalaciosz@unemi.edu.ec'], [], [pdf_acta], cuenta=CUENTAS_CORREOS[0][1])
                        else:
                            send_html_mail(asunto, "emails/email_miembro_mesa_elecciones.html",
                                       datos, [conf.vocal_alterno.persona.emailinst], [], [pdf_acta], cuenta=CUENTAS_CORREOS[0][1])
                    log(u'Adiciono Random Responsable Mesa %s' % conf, request, "add")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                msg_ex = 'Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, str(ex))
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Intentelo más tarde. {msg_ex}"}, safe=False)

        elif action == 'addsede':
            try:
                with transaction.atomic():
                    provincias = request.POST.getlist('provincias')
                    if provincias.__len__() == 0:
                        return JsonResponse({"result": True, "mensaje": "Debe elegir al menos una provincia relacionada"}, safe=False)
                    padron = CabPadronElectoral.objects.get(pk=request.POST['id'])
                    if SedesElectoralesPeriodo.objects.filter(periodo=padron, canton=request.POST['canton'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Cantón ya se encuentra registrado como sede.'}, safe=False)
                    form = SedeElectoralPeriodoForm(request.POST)
                    if form.is_valid():
                        instance = SedesElectoralesPeriodo(periodo=padron,
                                                           canton=form.cleaned_data['canton'],
                                                           nombre=form.cleaned_data['nombre'],
                                                           latitud=form.cleaned_data['latitud'],
                                                           longitud=form.cleaned_data['longitud'],
                                                           direccion=form.cleaned_data['direccion'])
                        instance.save(request)
                        for parr in provincias:
                            provinciaget = Provincia.objects.get(pk=int(parr))
                            instance.provincias.add(provinciaget)
                            instance.save(request)
                        log(u'Adiciono Sede Electoral: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editsede':
            try:
                with transaction.atomic():
                    provincias = request.POST.getlist('provincias')
                    if provincias.__len__() == 0:
                        return JsonResponse({"result": True, "mensaje": "Debe elegir al menos una provincia relacionada"}, safe=False)
                    filtro = SedesElectoralesPeriodo.objects.get(pk=request.POST['id'])
                    f = SedeElectoralPeriodoForm(request.POST)
                    if f.is_valid():
                        filtro.canton = f.cleaned_data['canton']
                        filtro.nombre = f.cleaned_data['nombre']
                        filtro.latitud = f.cleaned_data['latitud']
                        filtro.longitud = f.cleaned_data['longitud']
                        filtro.direccion = f.cleaned_data['direccion']
                        filtro.save(request)
                        filtro.provincias.clear()
                        for parr in provincias:
                            provinciaget = Provincia.objects.get(pk=int(parr))
                            filtro.provincias.add(provinciaget)
                            filtro.save(request)
                        log(u'Modificó Sede Electoral: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deletesede':
            try:
                with transaction.atomic():
                    instancia = SedesElectoralesPeriodo.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Sede Electora: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'deletesedepersona':
            try:
                with transaction.atomic():
                    instancia = PersonasSede.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Sede Electora: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'consultatotalempadronar':
            periodoid = request.POST['idevento']
            tipo = int(request.POST['tipo'])
            total = 0
            fechaactual = datetime.now()
            evento = CabPadronElectoral.objects.get(pk=periodoid, status=True)
            if evento.periodo:
                if tipo == 1:
                    idcoordinacion = request.POST['coordinacion']
                    coordinacion = Coordinacion.objects.get(pk=int(idcoordinacion))
                    listapersona = evento.detpersonapadronelectoral_set.filter(status=True).values_list('persona__id', flat=True)
                    condeudapersonas = Rubro.objects.filter(matricula__isnull=False, matricula__inscripcion__coordinacion=coordinacion, matricula__nivelmalla__in=[3, 4, 5, 6, 7, 8, 9, 10], matricula__cerrada=False, status=True, cancelado=False, fechavence__lt=fechaactual).values_list('persona__id', flat=True)
                    matricula = Matricula.objects.select_related('inscripcion').filter(inscripcion__coordinacion=coordinacion, status=True, nivel__periodo=evento.periodo, nivelmalla__in=[3, 4, 5, 6, 7, 8, 9, 10], cerrada=False)
                    sindeudapersonas = matricula.exclude(inscripcion__persona__in=(list(condeudapersonas)))
                    listavalores = Matricula.objects.select_related('inscripcion').filter(inscripcion__coordinacion=coordinacion, status=True, nivel__periodo=evento.periodo, nivelmalla__in=[3, 4, 5, 6, 7, 8, 9, 10], cerrada=False).exclude(inscripcion__persona__in=listapersona).values_list('inscripcion__pk', 'inscripcion__persona__pk', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__carrera__nombre', 'nivelmalla').order_by('nivelmalla')
                elif tipo == 2:
                    pass
                elif tipo == 3:
                    pass
                response = JsonResponse({'result': True, 'totalempadronar': matricula.count()})
            else:
                response = JsonResponse({'result': False, 'mensaje': 'No se puede vincular, evento no cuenta con periodo academico.'})
            return HttpResponse(response.content)

        elif action == 'adddignidad':
            try:
                f = DignidadElectoralForm(request.POST)
                if f.is_valid():
                    filtro = DignidadesElectorales(nombre=f.cleaned_data['nombre'], periodo_id=request.POST['id'])
                    filtro.save(request)
                    dignidad = request.POST.getlist('detalle[]')
                    if dignidad:
                        count = 0
                        while count < len(dignidad):
                            requisito = dignidad[count]
                            marcolegal = dignidad[count + 1]
                            medioverificacion = dignidad[count + 2]
                            resp = RequisitosDignidadesElectorales(dignidad=filtro, requisito=requisito, marcolegal=marcolegal, medioverificacion=medioverificacion)
                            resp.save(request)
                            count += 3
                    log(u'Adiciono Dignidad Electoral: %s' % filtro, request, "add")
                    messages.success(request, 'Dignidad guardada con exito')
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        elif action == 'editdignidad':
            try:
                f = DignidadElectoralForm(request.POST)
                if f.is_valid():
                    filtro = DignidadesElectorales.objects.get(pk=int(request.POST['id']))
                    filtro.nombre = f.cleaned_data['nombre']
                    filtro.save(request)
                    dignidadedit = request.POST.getlist('dignidadedit[]')
                    idsrequisitos = []
                    if dignidadedit:
                        countedit = 0
                        while countedit < len(dignidadedit):
                            id = dignidadedit[countedit]
                            requisito = dignidadedit[countedit + 1]
                            marcolegal = dignidadedit[countedit + 2]
                            medioverificacion = dignidadedit[countedit + 3]
                            resp = RequisitosDignidadesElectorales.objects.get(pk=id)
                            resp.requisito = requisito
                            resp.marcolegal = marcolegal
                            resp.medioverificacion = medioverificacion
                            resp.save(request)
                            countedit += 4
                            idsrequisitos.append(id)
                    requisitosborrar = RequisitosDignidadesElectorales.objects.filter(dignidad=filtro, status=True).exclude(pk__in=idsrequisitos)
                    for respb in requisitosborrar:
                        respb.status = False
                        respb.save(request)
                    dignidad = request.POST.getlist('dignidad[]')
                    if dignidad:
                        count = 0
                        while count < len(dignidad):
                            requisito = dignidad[count]
                            marcolegal = dignidad[count + 1]
                            medioverificacion = dignidad[count + 2]
                            resp = RequisitosDignidadesElectorales(dignidad=filtro)
                            resp.requisito = requisito
                            resp.marcolegal = marcolegal
                            resp.medioverificacion = medioverificacion
                            resp.save(request)
                            count += 3
                    log(u'Editó Dignidad Electoral: %s' % filtro, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        elif action == 'validarsolicituddignidad':
            try:
                id, estado = request.POST['id'], request.POST['estado']
                solicitud = SolicitudDignidadesElectorales.objects.get(pk=id)
                solicitud.estado = estado
                solicitud.save(request)
                requisitos = RequisitoSolicitudDignidadesElectorales.objects.filter(status=True, solicitud=solicitud).order_by('pk')
                for req in requisitos:
                    fieldid = 'id_{}'.format(req.pk)
                    fieldcheck = 'check_{}'.format(req.pk)
                    fieldobs = 'obs_{}'.format(req.pk)
                    fielddoc = 'doc_{}'.format(req.pk)
                    if fieldobs in request.POST:
                        req.observacion = request.POST[fieldobs]
                    if fieldcheck in request.POST:
                        check = True if fieldcheck == 'on' else False
                        req.validado = True
                    if fielddoc in request.FILES:
                        evidencia = request.FILES[fielddoc]
                        nombredocumento = solicitud.persona.__str__()
                        nombrecompletodocumento = remover_caracteres_especiales_unicode(nombredocumento).lower().replace(' ', '_')
                        evidencia._name = generar_nombre(nombrecompletodocumento, evidencia._name)
                        req.archivo = evidencia
                    req.save(request)
                    log(u'Modifico Requisito: %s' % req, request, "edit")
                return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": ex}, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'add':
                try:
                    form = CabPadronElectoralForm()
                    data['form2'] = form
                    template = get_template("adm_padronelectoral/modal/formpadron.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = CabPadronElectoral.objects.get(pk=request.GET['id'])
                    data['form2'] = CabPadronElectoralForm(initial=model_to_dict(filtro))
                    template = get_template("adm_padronelectoral/modal/formpadron.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verobservaciones':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = JustificacionPersonaPadronElectoral.objects.get(pk=request.GET['id'])
                    data['detalle'] = detalle = filtro.historialjustificacionpersonapadronelectoral_set.all().order_by('pk')
                    template = get_template("alu_justificacionsufragio/detalleobs.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addobservacion':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = JustificacionPersonaPadronElectoral.objects.get(pk=request.GET['id'])
                    data['detalle'] = detalle = filtro.historialjustificacionpersonapadronelectoral_set.all().order_by('pk')
                    form = DetalleJustificativoForm()
                    ESTADO_JUSTIFICACION_OBS = (
                        (1, u'CORREGIR'),
                        (2, u'APROBAR'),
                        (3, u'RECHAZAR'),
                    )
                    form.fields['accion'].choices = ESTADO_JUSTIFICACION_OBS
                    data['form2'] = form
                    template = get_template("adm_padronelectoral/formobservacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'personas':
                try:
                    data['title'] = u'Personas Empadronados'
                    orderby, coordinacion, options, tipo, id, search, filtros, url_vars = request.GET.get('orderby', ''), request.GET.get('coordinacion', ''), request.GET.get('options', ''), request.GET.get('tipo', ''), request.GET.get('id', ''), request.GET.get('search', ''), Q(status=True), ''
                    data['cab'] = cab = CabPadronElectoral.objects.get(pk=id)
                    listajustificativos = JustificacionPersonaPadronElectoral.objects.filter(status=True).values_list('inscripcion__id', flat=True)
                    if id:
                        data['id'] = int(id)
                        filtros = filtros & (Q(cab_id=id))
                        url_vars += '&id={}'.format(id)
                    if tipo:
                        data['tipo'] = int(tipo)
                        filtros = filtros & (Q(tipo=int(tipo)))
                        url_vars += '&tipo=' + tipo
                    if coordinacion:
                        data['coordinacion'] = int(coordinacion)
                        filtros = filtros & (Q(inscripcion__coordinacion_id=int(coordinacion)))
                        url_vars += '&coordinacion=' + coordinacion
                    if search:
                        data['search'] = search
                        s = search.split()
                        if len(s) == 1:
                            filtros = filtros & (Q(persona__apellido2__icontains=search) | Q(persona__cedula__icontains=search) | Q(persona__apellido1__icontains=search))
                        else:
                            filtros = filtros & (Q(persona__apellido1__icontains=s[0]) & Q(persona__apellido2__icontains=s[1]))
                        url_vars += '&search={}'.format(search)
                    if options:
                        data['options'] = options = int(options)
                        if options == 1:
                            presidentesids = ConfiguracionMesaResponsable.objects.filter(periodo=cab, status=True).values_list('presidente__id', flat=True)
                            secretarioids = ConfiguracionMesaResponsable.objects.filter(periodo=cab, status=True).values_list('secretario__id', flat=True)
                            vocalesids = ConfiguracionMesaResponsable.objects.filter(periodo=cab, status=True).values_list('vocal__id', flat=True)
                            idspersonas = list(presidentesids) + list(secretarioids) + list(vocalesids)
                            filtros = filtros & (Q(pk__in=idspersonas))
                        if options == 3:
                            filtros = filtros & (Q(pk__in=listajustificativos))

                        if options == 4:
                            filtros = filtros & (Q(pdf = True))

                        if options == 5:
                            filtros = filtros & (Q(pdf__isnull=False))

                        if options == 6:
                            filtros = filtros & (Q(pdf__isnull=True))


                        url_vars += '&options={}'.format(options)
                    query = DetPersonaPadronElectoral.objects.filter(filtros).order_by('persona__apellido1')
                    if options == 2:
                        presidentesids = ConfiguracionMesaResponsable.objects.filter(periodo=cab, status=True).values_list('presidente__id', flat=True)
                        secretarioids = ConfiguracionMesaResponsable.objects.filter(periodo=cab, status=True).values_list('secretario__id', flat=True)
                        vocalesids = ConfiguracionMesaResponsable.objects.filter(periodo=cab, status=True).values_list('vocal__id', flat=True)
                        idspersonas = list(presidentesids) + list(secretarioids) + list(vocalesids)
                        query = query.exclude(pk__in=idspersonas)
                    if orderby:
                        data['orderby'] = orderby = int(orderby)
                        url_vars += '&orderby=' + str(orderby)
                        if orderby == 1:
                            query = query.order_by('persona__apellido1')
                        if orderby == 2:
                            query = query.order_by('matricula__nivelmalla')
                        if orderby == 3:
                            query = query.order_by('lugarsede__canton__nombre')
                    data['listcount'] = query.count()
                    data['totestudiantes'] = query.filter(tipo=1).count()
                    data['totdocentes'] = query.filter(tipo=2).count()
                    data['totadministrativos'] = query.filter(tipo=3).count()
                    data['totaljustificativos'] = query.filter(pk__in=listajustificativos).count()
                    url_vars += '&action={}'.format(action)
                    data["url_vars"] = url_vars
                    if 'export_to_excel' in request.GET:
                        columns = [
                            (u"PERSONA", 20000),
                            (u"CEDULA", 3000),
                            (u"SEXO", 3000),
                            (u"CELULAR", 3000),
                            (u"CONVENCIONAL", 5000),
                            (u"EMAIL", 10000),
                            (u"EMAIL INSTITUCIONAL", 10000),
                            (u"PAIS", 10000),
                            (u"PROVINCIA", 10000),
                            (u"CANTON", 10000),
                            (u"DIRECCION DOMICILIARIA", 15000),
                            (u"ESTADO SOCIOECONOMICO", 15000),
                            (u"TIENE DISCAPACIDAD", 10000),
                            (u"TIPO DISCAPACIDAD", 10000),
                            (u"¿ES PPL?", 10000),
                            (u"OBS. PPL", 10000),
                            (u"LUGAR VOTACION", 15000),
                            (u"ASISTIO A VOTACION", 10000),
                            (u"TIPO", 10000),
                            (u"FACULTAD", 10000),
                            (u"CARRERA", 10000),
                        ]
                        response = HttpResponse(content_type='application/ms-excel')
                        response['Content-Disposition'] = 'attachment; filename="reporte_empadronados.xls"'
                        wb = xlwt.Workbook(encoding='utf-8')
                        ws = wb.add_sheet('HOJA_1')
                        title = easyxf('font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                        ws.write_merge(0, 0, 0, 61, '{}'.format(cab.nombre), title)
                        fuentecabecera = easyxf('font: name Calibri, color-index black, bold on, height 200; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                        row_num = 3
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                            ws.col(col_num).width = columns[col_num][1]
                        font_style = easyxf('font: name Calibri, color-index black, height 200; borders: left thin, right thin, top thin, bottom thin')
                        date_format = font_style
                        date_format.num_format_str = 'yyyy/mm/dd'
                        row_num = 4
                        for li in query:
                            nombres = "{} {} {}".format(li.persona.apellido1, li.persona.apellido2, li.persona.nombres)
                            sexo = li.persona.sexo.nombre if li.persona.sexo else ""
                            tienediscapacidad = 'NO'
                            tipodiscapacidad = 'NINGUNA'
                            ppl = 'NO'
                            pplobs = 'NINGUNA'
                            validado = 'NO'
                            ws.write(row_num, 0, nombres, font_style)
                            ws.write(row_num, 1, li.persona.cedula, font_style)
                            ws.write(row_num, 2, sexo, font_style)
                            ws.write(row_num, 3, li.persona.telefono, font_style)
                            ws.write(row_num, 4, li.persona.telefono_conv, font_style)
                            ws.write(row_num, 5, li.persona.email, font_style)
                            ws.write(row_num, 6, li.persona.emailinst, font_style)
                            ws.write(row_num, 7, li.persona.pais.nombre if li.persona.pais else '', font_style)
                            ws.write(row_num, 8, li.persona.provincia.nombre if li.persona.provincia else '', font_style)
                            ws.write(row_num, 9, li.persona.canton.nombre if li.persona.canton else '', font_style)
                            ws.write(row_num, 10, li.persona.direccion_corta(), font_style)
                            ws.write(row_num, 11, '', font_style)
                            if li.persona.tiene_discapasidad():
                                tienediscapacidad = 'SI'
                                tipodiscapacidad = li.persona.tiene_discapasidad().first().tipodiscapacidad.nombre
                            ws.write(row_num, 12, tienediscapacidad, font_style)
                            ws.write(row_num, 13, tipodiscapacidad, font_style)
                            if li.persona.ppl:
                                ppl = 'SI'
                                pplobs = li.persona.observacionppl
                            ws.write(row_num, 14, ppl, font_style)
                            ws.write(row_num, 15, pplobs, font_style)
                            ws.write(row_num, 16, li.lugar, font_style)
                            if li.validado:
                                validado = 'SI'
                            ws.write(row_num, 17, validado, font_style)
                            ws.write(row_num, 18, li.get_tipo_display(), font_style)
                            if li.inscripcion:
                                ws.write(row_num, 19, li.inscripcion.coordinacion.alias if li.inscripcion.coordinacion else '', font_style)
                                ws.write(row_num, 20, li.inscripcion.carrera.__str__() if li.inscripcion.carrera else '', font_style)
                            row_num += 1
                        wb.save(response)
                        return response
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
                    data['tipo_persona'] = TIPO_PERSONA_PADRON
                    data['coordinaciones'] = Coordinacion.objects.filter(status=True, excluir=False, pk__in=[1, 2, 3, 4, 5]).order_by('nombre')
                    return render(request, "adm_padronelectoral/personas.html", data)
                except Exception as ex:
                    msg_ex = 'Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, str(ex))
                    return JsonResponse({"result": False, 'data': str(msg_ex)})

            elif action == 'generarqr':
                try:
                    id = request.GET['id']
                    data['person'] = person = DetPersonaPadronElectoral.objects.get(id=id)
                    data['tittle'] = 'PDF QR Electoral'
                    data['foto'] = person.persona.get_foto()
                    result = generar_qr_padronelectoral(person, detalle_id=person.id)
                    link_pdf = ''
                    if result.get('isSuccess', {}):
                        aData = result.get('data', {})
                        url_pdf = aData.get('url_pdf', None)
                        if url_pdf == None:
                            raise NameError(u"No se encontro url del documento")
                        link_pdf = f"https://sga.unemi.edu.ec/media/{url_pdf}"
                        person.pdf = url_pdf
                        person.save(request)
                        return JsonResponse({"result": True, "url_pdf": link_pdf})
                    else:
                        return JsonResponse({"result": False, "msg": result.get('message')})
                except Exception as ex:
                    print(ex)
                    # messages.success(request, f"{ex} - {sys.exc_info()[-1].tb_lineno}")
                    return JsonResponse({"result": False, "msg": f"{ex} - {sys.exc_info()[-1].tb_lineno}"})

            elif action == 'verresumen':
                try:
                    data['title'] = u'Resumen Votación'
                    data['id'] = id = request.GET.get('id', '')
                    data['cab'] = cab = CabPadronElectoral.objects.get(pk=id)
                    data['tipos_list'] = TIPO_PERSONA_PADRON
                    data['coordinaciones_list'] = Coordinacion.objects.filter(status=True).order_by('nombre')
                    data['gremios_list'] = gremios_list = GremioElectoral.objects.filter(status=True).order_by('nombre')
                    data['lista_list'] = lista_list = ListaElectoral.objects.filter(status=True).order_by('nombre')
                    url_vars, filtros, tipos, gremios, coordinaciones = '', Q(status=True), request.GET.getlist('tipos', ''), request.GET.getlist('gremios', ''), request.GET.getlist('coordinaciones', '')
                    if tipos:
                        data["tipos"] = tipos = list(map(lambda x: int(x), tipos))
                        filtros = filtros & Q(tipo__in=tipos)
                        for r in tipos:
                            url_vars += "&tipos={}".format(r)
                    if gremios:
                        data["gremios"] = gremios = list(map(lambda x: int(x), gremios))
                        filtros = filtros & Q(gremio__in=gremios)
                        for r in gremios:
                            url_vars += "&gremios={}".format(r)
                    if coordinaciones:
                        data["coordinaciones"] = coordinacion = list(map(lambda x: int(x), coordinaciones))
                        filtros = filtros & Q(coordinacion__in=coordinaciones)
                        for r in coordinaciones:
                            url_vars += "&coordinaciones={}".format(r)
                    url_vars += '&action={}&id={}'.format(action, request.GET['id'])
                    query_base = GremioPeriodo.objects.filter(periodo=cab)
                    listado = query_base.filter(filtros).order_by('gremio__nombre')
                    data['listado'] = listado
                    data["url_vars"] = url_vars
                    if 'export_to_excel' in request.GET:
                        response = HttpResponse(content_type='application/ms-excel')
                        response['Content-Disposition'] = 'attachment; filename="resumen.xls"'
                        title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                        title2 = easyxf('font: name Calibri, color-index black, bold on , height 250; alignment: horiz centre')
                        font_style = xlwt.XFStyle()
                        font_style.font.bold = True
                        fuentecabecera = easyxf('font: name Calibri, color-index black, bold on; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                        fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                        style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')

                        wb = xlwt.Workbook(encoding='utf-8')
                        ws = wb.add_sheet('detalle_mesas')
                        ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', title)
                        ws.write_merge(1, 1, 0, 8, '{}'.format(cab.nombre), title2)
                        row_num = 3
                        for det in listado:
                            gremio = det.gremio.nombre if det.gremio else ''
                            coordinacion = det.coordinacion.nombre if det.coordinacion else ''
                            ws.write_merge(row_num, row_num, 0, 5, '{} {} {}'.format(det.get_tipo_display(), gremio, coordinacion, title))
                            row_num += 1
                            columns = [
                                ('EMPADRONADOS', 10000),
                                ('VOTOS NO UTILIZADOS', 10000),
                                ('VOTOS TOTAL VALIDOS', 10000),
                                ('VOTOS NULOS', 10000),
                                ('VOTOS BLANCO', 10000),
                            ]
                            for lis in det.listas_electorales():
                                columns.append((lis.lista.nombre, 10000))
                            for col_num in range(len(columns)):
                                ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                                ws.col(col_num).width = columns[col_num][1]
                            row_num += 1
                            ws.write(row_num, 0, det.totales_votos()['empadronado'], style2)
                            ws.write(row_num, 1, det.totales_votos()['ausentismo'], style2)
                            ws.write(row_num, 2, det.totales_votos()['votovalido'], style2)
                            ws.write(row_num, 3, det.totales_votos()['votonulo'], style2)
                            ws.write(row_num, 4, det.totales_votos()['votoblanco'], style2)
                            numero = 5
                            for lis in det.listas_electorales():
                                ws.write(row_num, numero, det.tota_listas_electorales(lis.lista.pk), style2)
                                numero += 1
                            row_num += 2

                        # ws_2 = wb.add_sheet('resumen_votos')
                        # ws_2.write_merge(0, 0, 0, 3, 'RESUMEN DE VOTOS',  title)
                        # row_num = 2
                        #
                        # columns = [
                        #     ('DETALLE', 10000),
                        #     ('TOTAL VOTOS', 10000),
                        # ]
                        # for col_num in range(len(columns)):
                        #     ws_2.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        #     ws_2.col(col_num).width = columns[col_num][1]
                        #
                        # row_num += 1
                        # ws_2.write(row_num, 0, 'EMPADRONADOS', style2)
                        # ws_2.write(row_num, 1, totempadronados, style2)
                        # row_num += 1
                        # ws_2.write(row_num, 0, 'VOTOS NO UTILIZADOS', style2)
                        # ws_2.write(row_num, 1, totausentismo, style2)
                        # row_num += 1
                        # ws_2.write(row_num, 0, 'VOTOS TOTAL VALIDOS', style2)
                        # ws_2.write(row_num, 1, totvotovalido, style2)
                        # row_num += 1
                        # ws_2.write(row_num, 0, 'VOTOS NULOS', style2)
                        # ws_2.write(row_num, 1, totvotonulo, style2)
                        # row_num += 1
                        # ws_2.write(row_num, 0, 'VOTOS BLACOS', style2)
                        # ws_2.write(row_num, 1, totvotoblanco, style2)
                        # row_num += 1
                        # for lt in lista_list:
                        #     ws_2.write(row_num, 0, lt.nombre, style2)
                        #     ws_2.write(row_num, 1, lt.total_x_lista(listado, cab.id), style2)
                        #     row_num += 1
                        wb.save(response)
                        return response
                    return render(request, "adm_padronelectoral/resumen.html", data)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return redirect('{}?info={}&linea={}'.format(request.path, ex, sys.exc_info()[-1].tb_lineno))

            elif action == 'verresumenasistencia':
                try:
                    data['title'] = u'Resumen Votación'
                    data['id'] = id = request.GET.get('id', '')
                    data['cab'] = cabecera = CabPadronElectoral.objects.get(pk=id)
                    data['asistidoporcoordinacion'] = DetPersonaPadronElectoral.objects.filter(tipo=1, status=True, cab=cabecera).values('inscripcion__coordinacion__alias').annotate(totalasistido=Coalesce(Count('id', filter=Q(validado=True)), 0), totalpendiente=Coalesce(Count('id', filter=Q(validado=False)), 0)).order_by('inscripcion__coordinacion__alias')
                    data['asistidopormodalidad'] = DetPersonaPadronElectoral.objects.filter(tipo=1, status=True, cab=cabecera).values('inscripcion__carrera__modalidad').annotate(totalasistido=Coalesce(Count('id', filter=Q(validado=True)), 0), totalpendiente=Coalesce(Count('id', filter=Q(validado=False)), 0)).order_by('inscripcion__carrera__modalidad')
                    data['asistidopormesa'] = asistidopormesa = DetPersonaPadronElectoral.objects.filter(status=True, cab=cabecera).values('mesa__nombre').annotate(totalasistido=Coalesce(Count('id', filter=Q(validado=True)), 0), totalpendiente=Coalesce(Count('id', filter=Q(validado=False)), 0)).order_by('mesa__orden')
                    data['asistidoporsede'] = DetPersonaPadronElectoral.objects.filter(status=True, cab=cabecera).values('lugarsede__canton__nombre').annotate(totalasistido=Coalesce(Count('id', filter=Q(validado=True)), 0), totalpendiente=Coalesce(Count('id', filter=Q(validado=False)), 0)).order_by('lugarsede__canton__nombre')
                    data['poblacion'] = DetPersonaPadronElectoral.objects.filter(status=True, cab=cabecera).count()
                    data['totalasistidos'] = DetPersonaPadronElectoral.objects.filter(status=True, cab=cabecera, validado=True).count()
                    data['totalnoasistidos'] = DetPersonaPadronElectoral.objects.filter(status=True, cab=cabecera, validado=False).count()
                    data['poblacionest'] = DetPersonaPadronElectoral.objects.filter(tipo=1, status=True, cab=cabecera).count()
                    data['totalasistidosest'] = DetPersonaPadronElectoral.objects.filter(tipo=1, status=True, cab=cabecera, validado=True).count()
                    data['totalnoasistidosest'] = DetPersonaPadronElectoral.objects.filter(tipo=1, status=True, cab=cabecera, validado=False).count()
                    return render(request, "adm_padronelectoral/resumenasistencia.html", data)
                except Exception as ex:
                    return JsonResponse({'ex':'{}?info={}&linea={}'.format(request.path, ex, sys.exc_info()[-1].tb_lineno) })

            elif action == 'verjustificativos':
                data['filtro'] = filtro = DetPersonaPadronElectoral.objects.get(pk=int(request.GET['id']))
                data['title'] = u'Justificativos de {}'.format(filtro.persona.__str__())
                data['listado'] = JustificacionPersonaPadronElectoral.objects.filter(status=True, inscripcion=filtro).order_by('-pk')
                return render(request, "adm_padronelectoral/justificar.html", data)

            elif action == 'justificarmasivo':
                try:
                    evento = CabPadronElectoral.objects.get(pk=int(request.GET['id']))
                    totaljustificados = query = JustificacionPersonaPadronElectoral.objects.filter(status=True, inscripcion__cab=evento, estados_justificacion=0).order_by('-pk')
                    listaenviar = list(query.values('id', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres'))
                    return JsonResponse({"result": "ok", "cantidad": len(listaenviar), "inscritos": listaenviar})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'justificacionalumno':
                try:
                    filtro = JustificacionPersonaPadronElectoral.objects.get(pk=request.GET['id'])
                    filtro.estados_justificacion = 2
                    filtro.save(request)
                    empadronado = DetPersonaPadronElectoral.objects.get(pk=filtro.inscripcion.pk)
                    empadronado.puede_justificar = False
                    empadronado.save(request)
                    soli = HistorialJustificacionPersonaPadronElectoral(justificativo=filtro,
                                                                        detalle='APROBADO POR {} {} {}'.format(persona.apellido1, persona.apellido2, persona.nombres),
                                                                        accion=2)
                    soli.save(request)

                    asunto = u"RESPUESTA JUSTIFICATIVO OMISIÓN DE SUFRAGIO"
                    para = soli.justificativo.inscripcion.persona
                    observacion = 'SU SOLICITUD FUE {}'.format(soli.get_accion_display())
                    notificacion(asunto, observacion, para, None, '/alu_procesoelectoral', soli.pk, 1, 'sga',
                                 HistorialJustificacionPersonaPadronElectoral, request)

                    log(u'Adiciono Observación en Seguimiento Interesados Maestrías: %s' % soli, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'verjustificativosgeneral':
                url_vars = ''
                data['title'] = u'Justificativos de Omisión de Sufragio'

                tiposolicitud, options, estado, tipo, id, search, filtros, url_vars = request.GET.get('tiposolicitud', ''), request.GET.get('options', ''), request.GET.get('estado', ''), request.GET.get('tipo', ''), request.GET.get('id', ''), request.GET.get('search', ''), Q(status=True), ''

                listajustificativos = JustificacionPersonaPadronElectoral.objects.filter(status=True).values_list('inscripcion__id', flat=True)

                data['id'] = id = request.GET.get('id', '')
                data['cab'] = cab = CabPadronElectoral.objects.get(pk=id)

                if tipo:
                    data['tipo'] = int(tipo)
                    filtros = filtros & (Q(tipo=int(tipo)))
                    url_vars += '&tipo=' + tipo

                if estado:
                    data['estado'] = int(estado)
                    filtros = filtros & (Q(estados_justificacion=int(estado)))
                    url_vars += '&estado=' + estado

                if search:
                    data['search'] = search
                    s = search.split()
                    if len(s) == 1:
                        filtros = filtros & (Q(inscripcion__persona__apellido2__icontains=search) | Q(inscripcion__persona__cedula__icontains=search) | Q(inscripcion__persona__apellido1__icontains=search))
                    else:
                        filtros = filtros & (Q(inscripcion__persona__apellido1__icontains=s[0]) & Q(inscripcion__persona__apellido2__icontains=s[1]))
                    url_vars += '&search={}'.format(search)

                if tiposolicitud:
                    data['tiposolicitud'] = tiposolicitud = int(tiposolicitud)
                    if tiposolicitud == 1:
                        filtros = filtros & (Q(certificado_medico__isnull=False))
                    if tiposolicitud == 2:
                        filtros = filtros & (Q(certificado_upc__isnull=False))
                    if tiposolicitud == 3:
                        filtros = filtros & (Q(certificado_defuncion__isnull=False))
                    if tiposolicitud == 4:
                        filtros = filtros & (Q(certificado_licencia__isnull=False))
                    if tiposolicitud == 5:
                        filtros = filtros & (Q(certificado_alterno__isnull=False))
                    if tiposolicitud == 6:
                        filtros = filtros & (Q(documento_validador__isnull=False))

                if options:
                    data['options'] = options = int(options)
                    if options == 2:
                        filtros = filtros & (Q(estudiante_enlinea=True))
                    if options == 1:
                        filtros = filtros & (Q(estudiante_presencial=True))

                    url_vars += '&options={}'.format(options)

                url_vars += '&action={}'.format(action)
                data["url_vars"] = url_vars

                data['estado_justificacion'] = ESTADO_JUSTIFICACION
                data['tipo_persona_padron'] = TIPO_PERSONA_PADRON

                query = JustificacionPersonaPadronElectoral.objects.filter(filtros).filter(inscripcion__cab=cab).order_by('-pk')
                data['listadocount'] = query.count()
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
                data['listado'] = page.object_list
                url_vars += '&id={}'.format(id)
                url_vars += '&action={}'.format(action)
                data["url_vars"] = url_vars
                return render(request, "adm_padronelectoral/justificativos.html", data)

            elif action == 'versolicitudesinformacion':
                url_vars = ''
                data['title'] = u'Solicitudes de Información'
                data['id'] = id = request.GET.get('id', '')
                data['cab'] = cab = CabPadronElectoral.objects.get(pk=id)

                estado, tipo, search, filtros, url_vars = request.GET.get('estado', ''), request.GET.get('tipo', ''), request.GET.get('search', ''), Q(status=True), ''

                if tipo:
                    data['tipo'] = int(tipo)
                    filtros = filtros & (Q(tipo__id=int(tipo)))
                    url_vars += '&tipo=' + tipo

                if estado:
                    data['estado'] = int(estado)
                    filtros = filtros & (Q(estados=int(estado)))
                    url_vars += '&estado=' + estado

                if search:
                    data['search'] = search
                    s = search.split()
                    if len(s) == 1:
                        filtros = filtros & (Q(persona__apellido2__icontains=search) | Q(persona__cedula__icontains=search) | Q(persona__apellido1__icontains=search))
                    else:
                        filtros = filtros & (Q(persona__apellido1__icontains=s[0]) & Q(persona__apellido2__icontains=s[1]))
                    url_vars += '&search={}'.format(search)

                url_vars += '&action={}'.format(action)
                data["url_vars"] = url_vars

                data['estado_justificacion'] = ESTADO_SOLICITUD_INFORMACION
                data['tipo_solicitudes'] = TipoSolicitudInformacionPadronElectoral.objects.filter(status=True).order_by('descripcion')

                query = SolicitudInformacionPadronElectoral.objects.filter(cab=cab).filter(filtros).order_by('-pk')
                data['listadocount'] = query.count()
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
                data['listado'] = page.object_list
                url_vars += '&id={}'.format(id)
                url_vars += '&action={}'.format(action)
                data["url_vars"] = url_vars
                return render(request, "adm_padronelectoral/solicitudesinformacion/view.html", data)

            elif action == 'validarsolicitudesinformacion':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = SolicitudInformacionPadronElectoral.objects.get(pk=request.GET['id'])
                    form = ValidarSolicitudesForm()
                    data['form2'] = form
                    template = get_template("adm_padronelectoral/solicitudesinformacion/formvalidacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'certificadojustificado':
                try:
                    data['hoy'] = datetime.now()
                    data['filtro'] = filtro = JustificacionPersonaPadronElectoral.objects.get(pk=encrypt(request.GET['id']))
                    if filtro.tipo == 1:
                        template_pdf = 'adm_padronelectoral/certificado_justificacion.html'
                    else:
                        template_pdf = 'adm_padronelectoral/certificado_justificaciondoc.html'
                    return conviert_html_to_pdf(
                        template_pdf,
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'oficiomesa':
                try:
                    id, personaid, tipo = request.GET.get('id', ''), request.GET.get('personaid', ''), int(request.GET.get('tipo', ''))
                    data['hoy'] = hoy = datetime.now().date()
                    filtro = ConfiguracionMesaResponsable.objects.get(pk=id)
                    personamesa = DetPersonaPadronElectoral.objects.get(pk=personaid)
                    data['personamesa'] = personamesa
                    data['info_mesa'] = personamesa.info_mesa()
                    data['filtro'] = filtro
                    template_pdf = 'adm_padronelectoral/pdf_notificacion_mesa.html'
                    return conviert_html_to_pdf(
                        template_pdf,
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'configuraciones':
                try:
                    data['title'] = u'Configuraciones Evento Electoral'
                    data['listMesas'] = MesasPadronElectoral.objects.filter(status=True).order_by('-periodo', 'orden')
                    data['listListas'] = ListaElectoral.objects.filter(status=True).order_by('nombre')
                    data['listGremio'] = GremioElectoral.objects.filter(status=True).order_by('nombre')
                    return render(request, "adm_padronelectoral/configuraciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'reporteempadronados':
                try:
                    id = request.GET['id']
                    data['mesa'] = mesa = MesasPadronElectoral.objects.get(id=id)
                    data['total'] = mesa.detpersonas()
                    data['lista'] = mesa.lista_padron_mesa()
                    data['fechaemision'] = datetime.now().strftime('%d/%m/%Y %I.%M %p')
                    data['user'] = persona.usuario
                    #return  render(request, "adm_padronelectoral/listaempadronados_pdf.html", data)

                    return conviert_html_to_pdf(
                        'adm_padronelectoral/listaempadronados_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )

                except Exception as ex:
                    pass

            elif action == 'reporteempadronadosexcel':
                try:
                    id = request.GET['id']
                    data['mesa'] = mesa = MesasPadronElectoral.objects.get(id=id)
                    personas = mesa.lista_padron_mesa()
                    columns = [
                        (u"N°", 1500),
                        (u"NOMINA", 15000 ),
                        (u"CEDULA", 9000),
                        (u"ASISTIÓ", 7000)
                    ]
                    response = HttpResponse(content_type='application/ms-excel')
                    response['Content-Disposition'] = 'attachment; filename="reporte_empadronados.xls"'
                    wb = xlwt.Workbook(encoding='utf-8')
                    ws = wb.add_sheet('HOJA_1')
                    title = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    fuentecabecera = easyxf(
                        'font: name Calibri, color-index black, bold on, height 200; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    ws.write_merge(0, 1, 0, 4, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write(2, 1, 'Total asistidos: ' + '' + str(mesa.total_asistencia()) + ' - ' + str(mesa.total_asistencia()) + '%', fuentecabecera)

                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    font_style = easyxf(
                        'font: name Calibri, color-index black, height 200; borders: left thin, right thin, top thin, bottom thin')
                    row_num = 4
                    i = 0
                    for det in personas:
                        i+=1
                        ws.write(row_num, 0, i , font_style)
                        ws.write(row_num, 1, det.persona.__str__(), font_style)
                        ws.write(row_num, 2, det.persona.documento(), font_style)
                        ws.write(row_num, 3, 'SI' if det.validado else 'NO' , font_style)

                        row_num += 1
                    wb.save(response)
                    return response


                except Exception as ex:
                    print(ex)
                    pass

            elif action == 'addmesa':
                try:
                    data['form2'] = MesaPadronForm()
                    template = get_template("adm_padronelectoral/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editmesa':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = MesasPadronElectoral.objects.get(pk=request.GET['id'])
                    data['form2'] = MesaPadronForm(initial=model_to_dict(filtro))
                    template = get_template("adm_padronelectoral/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addlista':
                try:
                    data['form2'] = ListaPadronForm()
                    template = get_template("adm_padronelectoral/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editlista':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ListaElectoral.objects.get(pk=request.GET['id'])
                    data['form2'] = ListaPadronForm(initial=model_to_dict(filtro))
                    template = get_template("adm_padronelectoral/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addgremio':
                try:
                    data['form2'] = GremioPadronForm()
                    template = get_template("adm_padronelectoral/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editgremio':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = GremioElectoral.objects.get(pk=request.GET['id'])
                    data['form2'] = GremioPadronForm(initial=model_to_dict(filtro))
                    template = get_template("adm_padronelectoral/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'gremiosperiodo':
                try:
                    data['title'] = u'Gremios Periodos'
                    data['id'] = id = request.GET.get('id', '')
                    data['cab'] = cab = CabPadronElectoral.objects.get(pk=id)
                    data['tipos_list'] = TIPO_PERSONA_PADRON
                    data['coordinaciones_list'] = Coordinacion.objects.filter(status=True).order_by('nombre')
                    data['gremios_list'] = gremios_list = GremioElectoral.objects.filter(status=True).order_by('nombre')
                    data['lista_list'] = lista_list = ListaElectoral.objects.filter(status=True).order_by('nombre')
                    url_vars, filtros, tipos, gremios, coordinaciones = '', Q(status=True), request.GET.getlist('tipos', ''), request.GET.getlist('gremios', ''), request.GET.getlist('coordinaciones', '')
                    if tipos:
                        data["tipos"] = tipos = list(map(lambda x: int(x), tipos))
                        filtros = filtros & Q(tipo__in=tipos)
                        for r in tipos:
                            url_vars += "&tipos={}".format(r)
                    if gremios:
                        data["gremios"] = gremios = list(map(lambda x: int(x), gremios))
                        filtros = filtros & Q(gremio__in=gremios)
                        for r in gremios:
                            url_vars += "&gremios={}".format(r)
                    if coordinaciones:
                        data["coordinaciones"] = coordinacion = list(map(lambda x: int(x), coordinaciones))
                        filtros = filtros & Q(coordinacion__in=coordinaciones)
                        for r in coordinaciones:
                            url_vars += "&coordinaciones={}".format(r)
                    url_vars += '&action={}&id={}'.format(action, request.GET['id'])
                    query_base = GremioPeriodo.objects.filter(periodo=cab)
                    listado = query_base.filter(filtros).order_by('tipo')
                    data['listado'] = listado
                    data["url_vars"] = url_vars
                    return render(request, "adm_padronelectoral/gremiosperiodos.html", data)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return redirect('{}?info={}&linea={}'.format(request.path, ex, sys.exc_info()[-1].tb_lineno))

            elif action == 'addgremioperiodo':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = CabPadronElectoral.objects.get(pk=request.GET['id'])
                    data['form2'] = GremioPeriodoForm()
                    template = get_template("adm_padronelectoral/modal/formgremioperiodo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editgremioperiodo':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = GremioPeriodo.objects.get(pk=request.GET['id'])
                    data['form2'] = GremioPeriodoForm(instance=filtro)
                    template = get_template("adm_padronelectoral/modal/formgremioperiodo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'responsablemesa':
                try:
                    data['title'] = u'Configuración de Mesas'
                    data['id'] = id = request.GET.get('id', '')
                    data['cab'] = cab = CabPadronElectoral.objects.get(pk=id)
                    data['tipos_list'] = TIPO_PERSONA_PADRON
                    query_base = ConfiguracionMesaResponsable.objects.filter(periodo=cab)
                    url_vars, filtros, tipos, criterio = '', Q(status=True), request.GET.getlist('tipos', ''), request.GET.get('criterio', '')
                    if tipos:
                        data["tipos"] = tipos = list(map(lambda x: int(x), tipos))
                        filtros = filtros & Q(tipo__in=tipos)
                        for r in tipos:
                            url_vars += "&tipos={}".format(r)
                    if criterio:
                        data["criterio"] = criterio
                        filtros = filtros & Q(mesa__nombre__icontains=criterio)
                        url_vars += "&criterio={}".format(criterio)
                    listado = query_base.filter(filtros).order_by('tipo', 'mesa__orden')
                    data['listado'] = listado
                    data['listadocount'] = listado.count()
                    data["url_vars"] = url_vars
                    return render(request, "adm_padronelectoral/responsablemesa.html", data)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return redirect('{}?info={}&linea={}'.format(request.path, ex, sys.exc_info()[-1].tb_lineno))

            elif action == 'asignacionresponsablemesa':
                try:
                    data['title'] = u'Asignación de Responsables Mesas'
                    data['id'] = id = request.GET.get('id', '')
                    data['cab'] = cab = CabPadronElectoral.objects.get(pk=id)
                    data['sedes'] = sedes = SedesElectoralesPeriodo.objects.filter(periodo=cab, status=True).order_by('canton__nombre')
                    query_base = ConfiguracionMesaResponsable.objects.filter(periodo=cab, status=True).order_by('tipo', 'mesa__orden')
                    data['listado'] = query_base
                    data['listadocount'] = query_base.count()
                    return render(request, "adm_padronelectoral/asignacionmesa.html", data)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return redirect('{}?info={}&linea={}'.format(request.path, ex, sys.exc_info()[-1].tb_lineno))

            elif action == 'sedesperiodo':
                try:
                    data['title'] = u'Sedes Periodo'
                    data['id'] = id = request.GET.get('id', '')
                    data['cab'] = cab = CabPadronElectoral.objects.get(pk=id)
                    query_base = SedesElectoralesPeriodo.objects.filter(periodo=cab)
                    url_vars, filtros, criterio = '', Q(status=True), request.GET.get('criterio', '')
                    if criterio:
                        data["criterio"] = criterio
                        filtros = filtros & Q(canton__nombre__icontains=criterio) | Q(canton__provincia__nombre__icontains=criterio)
                        url_vars += "&criterio={}".format(criterio)
                    listado = query_base.filter(filtros).order_by('canton__provincia__nombre', 'canton__nombre')
                    data['listado'] = listado
                    data['listadocount'] = listado.count()
                    data["url_vars"] = url_vars
                    return render(request, "adm_padronelectoral/sedeselectorales.html", data)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return redirect('{}?info={}&linea={}'.format(request.path, ex, sys.exc_info()[-1].tb_lineno))

            elif action == 'ingresodignidades':
                try:
                    if not request.user.is_superuser:
                        return redirect(request.path)
                    data['title'] = u'Ingreso Dignidades Electorales'
                    data['id'] = id = request.GET.get('id', '')
                    data['cab'] = cab = CabPadronElectoral.objects.get(pk=id)
                    dignidades = DignidadesElectorales.objects.filter(periodo=cab).order_by('nombre')
                    data['dignidades'] = dignidades
                    query_base = SolicitudDignidadesElectorales.objects.filter(dignidad__periodo=cab).order_by('dignidad__nombre')
                    data['listado'] = query_base
                    data['listadocount'] = query_base.count()
                    return render(request, "adm_padronelectoral/dignidadessolicitudes.html", data)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return redirect('{}?info={}&linea={}'.format(request.path, ex, sys.exc_info()[-1].tb_lineno))

            elif action == 'validarrequisitos':
                try:
                    data['title'] = u'Validar Solicitud '
                    data['id'] = id = request.GET.get('id', '')
                    data['filtro'] = filtro = SolicitudDignidadesElectorales.objects.get(pk=request.GET['id'])
                    data['cabid'] = filtro.dignidad.periodo.id
                    data['estados_solicitud'] = ESTADOS_SOLICITUD_DIGNIDAD
                    excludeids = filtro.dignidad.requisitos().values_list('pk', flat=True)
                    RequisitoSolicitudDignidadesElectorales.objects.filter(solicitud=filtro, status=True).exclude(requisito__in=excludeids).update(status=False)
                    for f in filtro.dignidad.requisitos():
                        if not RequisitoSolicitudDignidadesElectorales.objects.filter(solicitud=filtro, requisito=f, status=True):
                            req = RequisitoSolicitudDignidadesElectorales(solicitud=filtro, requisito=f)
                            req.save(request)
                    data['requisitos'] = requisitos = RequisitoSolicitudDignidadesElectorales.objects.filter(solicitud=filtro, status=True).order_by('pk')
                    return render(request, "adm_padronelectoral/validarsolicitud.html", data)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return redirect('{}?info={}&linea={}'.format(request.path, ex, sys.exc_info()[-1].tb_lineno))

            elif action == 'addsolicituddignidad':
                try:
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = DignidadesElectorales.objects.get(pk=id)
                    data['cabid'] = filtro.periodo.pk
                    form = SolicitudDignidadForm()
                    form.fields['persona'].queryset = Persona.objects.none()
                    data['form2'] = form
                    template = get_template("adm_padronelectoral/modal/formsolicituddignidad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editsolicituddignidad':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = SolicitudDignidadesElectorales.objects.get(pk=request.GET['id'])
                    data['cabid'] = filtro.dignidad.periodo.id
                    form = SolicitudDignidadForm(initial=model_to_dict(filtro))
                    if filtro.persona:
                        form.fields['persona'].queryset = Persona.objects.filter(pk=filtro.persona.pk)
                    else:
                        form.fields['persona'].queryset = Persona.objects.none()
                    data['form2'] = form
                    template = get_template("adm_padronelectoral/modal/formsolicituddignidad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'dignidadesperiodo':
                try:
                    data['title'] = u'Dignidades Electorales'
                    data['id'] = id = request.GET.get('id', '')
                    data['cab'] = cab = CabPadronElectoral.objects.get(pk=id)
                    query_base = DignidadesElectorales.objects.filter(periodo=cab).order_by('nombre')
                    data['listado'] = query_base
                    data['listadocount'] = query_base.count()
                    return render(request, "adm_padronelectoral/dignidadelectoral.html", data)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return redirect('{}?info={}&linea={}'.format(request.path, ex, sys.exc_info()[-1].tb_lineno))

            elif action == 'adddignidad':
                try:
                    data['title'] = u'Adicionar Dignidad'
                    data['filtro'] = filtro = CabPadronElectoral.objects.get(id=request.GET['id'])
                    data['form'] = DignidadElectoralForm()
                    return render(request, "adm_padronelectoral/adddignidad.html", data)
                except Exception as ex:
                    pass

            elif action == 'editdignidad':
                try:
                    data['title'] = u'Editar Dignidad'
                    data['filtro'] = filtro = DignidadesElectorales.objects.get(pk=int(request.GET['id']))
                    data['form'] = DignidadElectoralForm(initial=model_to_dict(filtro))
                    return render(request, "adm_padronelectoral/editdignidad.html", data)
                except Exception as ex:
                    pass

            elif action == 'personassede':
                try:
                    data['title'] = u'Personas Sede'
                    data['id'] = id = request.GET.get('id', '')
                    data['cab'] = cab = SedesElectoralesPeriodo.objects.get(pk=id)
                    query_base = PersonasSede.objects.filter(sede=cab)
                    url_vars, filtros, criterio, search = '', Q(status=True), request.GET.get('criterio', ''), request.GET.get('search', '')
                    if criterio:
                        data["criterio"] = criterio
                        filtros = filtros & Q(canton__nombre__icontains=criterio) | Q(canton__provincia__nombre__icontains=criterio)
                        url_vars += "&criterio={}".format(criterio)
                    if search:
                        data['search'] = search
                        s = search.split()
                        if len(s) == 1:
                            filtros = filtros & (Q(persona__apellido2__icontains=search) | Q(persona__cedula__icontains=search) | Q(persona__apellido1__icontains=search))
                        else:
                            filtros = filtros & (Q(persona__apellido1__icontains=s[0]) & Q(persona__apellido2__icontains=s[1]))
                        url_vars += '&search={}'.format(search)
                    url_vars += '&action={}'.format(action)
                    url_vars += '&id={}'.format(id)
                    listado = query_base.filter(filtros).order_by('canton__provincia__nombre', 'persona__apellido1')
                    data['listadocount'] = listado.count()
                    paging = MiPaginador(listado, 25)
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
                    if 'export_to_excel' in request.GET:
                        response = HttpResponse(content_type='application/ms-excel')
                        response['Content-Disposition'] = 'attachment; filename="INSCRITOS_{}_{}.xls"'.format(cab.canton.nombre, cab.canton.provincia.nombre)
                        title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                        title2 = easyxf('font: name Calibri, color-index black, bold on , height 250; alignment: horiz centre')
                        font_style = xlwt.XFStyle()
                        font_style.font.bold = True
                        fuentecabecera = easyxf('font: name Calibri, color-index black, bold on; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                        fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                        style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                        wb = xlwt.Workbook(encoding='utf-8')
                        ws = wb.add_sheet('inscritos')
                        ws.write_merge(0, 0, 0, 8, 'INSCRITOS EN SEDE', title)
                        ws.write_merge(1, 1, 0, 8, 'Canton: {}'.format(cab.canton.nombre), title2)
                        ws.write_merge(2, 2, 0, 8, 'Provincia: {}'.format(cab.canton.provincia.nombre), title2)
                        row_num = 4
                        columns = [
                            ('CEDULA', 10000),
                            ('PERSONA', 10000),
                            ('NIVEL', 10000),
                            ('MODALIDAD', 10000),
                            ('CARRERA', 10000),
                            ('FACULTAD', 10000),
                            ('PROVINCIA', 10000),
                            ('CANTON', 10000),
                        ]
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                            ws.col(col_num).width = columns[col_num][1]
                        row_num += 1
                        for l in listado:
                            ws.write(row_num, 0, l.persona.cedula, style2)
                            ws.write(row_num, 1, l.persona.nombre_completo_inverso(), style2)
                            if l.matricula:
                                ws.write(row_num, 2, l.matricula.nivelmalla.nombre if l.matricula.nivelmalla else '', style2)
                            else:
                                ws.write(row_num, 2, '', style2)
                            if l.inscripcion:
                                ws.write(row_num, 3, l.inscripcion.modalidad.nombre if l.inscripcion.modalidad else '', style2)
                                ws.write(row_num, 4, l.inscripcion.carrera.nombre if l.inscripcion.carrera else '', style2)
                                ws.write(row_num, 5, l.inscripcion.coordinacion.alias if l.inscripcion.coordinacion else '', style2)
                            else:
                                ws.write(row_num, 3, '', style2)
                                ws.write(row_num, 4, '', style2)
                                ws.write(row_num, 5, '', style2)
                            ws.write(row_num, 6, l.canton.provincia.nombre if l.canton else '', style2)
                            ws.write(row_num, 7, l.canton.nombre if l.canton else '', style2)
                            row_num += 1
                        wb.save(response)
                        return response
                    return render(request, "adm_padronelectoral/sedespersona.html", data)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return redirect('{}?info={}&linea={}'.format(request.path, ex, sys.exc_info()[-1].tb_lineno))

            elif action == 'addsede':
                try:
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = CabPadronElectoral.objects.get(pk=id)
                    data['cabid'] = id
                    form = SedeElectoralPeriodoForm()
                    form.fields['provincia'].queryset = Provincia.objects.none()
                    form.fields['canton'].queryset = Canton.objects.none()
                    data['form2'] = form
                    template = get_template("adm_padronelectoral/modal/formsede.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editsede':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = SedesElectoralesPeriodo.objects.get(pk=request.GET['id'])
                    data['cabid'] = filtro.periodo.id
                    form = SedeElectoralPeriodoForm(initial=model_to_dict(filtro))
                    form.fields['provincia'].queryset = Provincia.objects.none()
                    form.fields['canton'].queryset = Canton.objects.none()
                    data['form2'] = form
                    template = get_template("adm_padronelectoral/modal/formsede.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addempadronado':
                try:
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = CabPadronElectoral.objects.get(pk=id)
                    data['cabid'] = id
                    form = PersonaEmpadronadoForm()
                    form.fields['persona'].queryset = Persona.objects.none()
                    form.fields['lugarsede'].queryset = SedesElectoralesPeriodo.objects.filter(status=True, periodo=filtro)
                    form.fields['mesa'].queryset = MesasPadronElectoral.objects.filter(status=True, periodo=filtro).order_by('orden')
                    data['form2'] = form
                    template = get_template("adm_padronelectoral/modal/formpersonaempadronada.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    print(ex)
                    return JsonResponse({"result": False, 'msg': ex})

            elif action == 'editempadronado':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = DetPersonaPadronElectoral.objects.get(pk=request.GET['id'])
                    data['cabid'] = filtro.cab.id
                    form = PersonaEmpadronadoForm(initial=model_to_dict(filtro))
                    form.fields['lugarsede'].queryset = SedesElectoralesPeriodo.objects.filter(status=True, periodo=filtro.cab)
                    form.fields['mesa'].queryset = MesasPadronElectoral.objects.filter(status=True, periodo=filtro.cab).order_by('orden')
                    if filtro.persona:
                        form.fields['persona'].queryset = Persona.objects.filter(pk=filtro.persona.pk)
                    else:
                        form.fields['persona'].queryset = Persona.objects.none()
                    data['form2'] = form
                    template = get_template("adm_padronelectoral/modal/formpersonaempadronada.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'buscarpersonas':
                try:
                    id = request.GET['id']
                    filtro = CabPadronElectoral.objects.get(pk=id)
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    querybase = Persona.objects.filter(status=True)
                    if len(s) == 1:
                        per = querybase.filter((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) | Q(apellido2__icontains=q) | Q(cedula__contains=q)), Q(status=True)).distinct()[:15]
                    elif len(s) == 2:
                        per = querybase.filter((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                               (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                               (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1]))).filter(status=True).distinct()[:15]
                    else:
                        per = querybase.filter((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) |
                                               (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).filter(status=True).distinct()[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.cedula, x.nombre_completo())} for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'addconfmesa':
                try:
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = CabPadronElectoral.objects.get(pk=id)
                    data['cabid'] = id
                    form = ConfiguracionMesaResponsableForm()
                    detallemesas = ConfiguracionMesaResponsable.objects.filter(periodo=filtro, status=True).values_list('mesa__id', flat=True)
                    # detallesede = ConfiguracionMesaResponsable.objects.filter(periodo=filtro, status=True).values_list('sede__id', flat=True)
                    form.fields['sede'].queryset = SedesElectoralesPeriodo.objects.filter(status=True, periodo=filtro).order_by('nombre')
                    form.fields['mesa'].queryset = MesasPadronElectoral.objects.filter(status=True, periodo=filtro).exclude(pk__in=detallemesas).order_by('orden')
                    # form.fields['sede'].queryset = SedesElectoralesPeriodo.objects.filter(status=True).exclude(pk__in=detallesede).order_by('canton__nombre')
                    form.fields['presidente'].queryset = DetPersonaPadronElectoral.objects.none()
                    form.fields['secretario'].queryset = DetPersonaPadronElectoral.objects.none()
                    form.fields['vocal'].queryset = DetPersonaPadronElectoral.objects.none()
                    form.fields['presidente_alterno'].queryset = DetPersonaPadronElectoral.objects.none()
                    form.fields['secretario_alterno'].queryset = DetPersonaPadronElectoral.objects.none()
                    form.fields['vocal_alterno'].queryset = DetPersonaPadronElectoral.objects.none()
                    form.fields['logistica'].queryset = Persona.objects.none()
                    data['form2'] = form
                    template = get_template("adm_padronelectoral/modal/formconfmesa.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editconfmesa':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ConfiguracionMesaResponsable.objects.get(pk=request.GET['id'])
                    data['cabid'] = filtro.periodo.id
                    form = ConfiguracionMesaResponsableForm(initial=model_to_dict(filtro))
                    detallemesas = ConfiguracionMesaResponsable.objects.filter(periodo=filtro.periodo.id, status=True).exclude(pk=filtro.pk).values_list('mesa__id', flat=True)
                    form.fields['mesa'].queryset = MesasPadronElectoral.objects.filter(status=True, periodo=filtro.periodo).exclude(pk__in=detallemesas).order_by('orden')
                    if filtro.presidente:
                        form.fields['presidente'].queryset = DetPersonaPadronElectoral.objects.filter(pk=filtro.presidente.pk)
                    else:
                        form.fields['presidente'].queryset = DetPersonaPadronElectoral.objects.none()
                    if filtro.secretario:
                        form.fields['secretario'].queryset = DetPersonaPadronElectoral.objects.filter(pk=filtro.secretario.pk)
                    else:
                        form.fields['secretario'].queryset = DetPersonaPadronElectoral.objects.none()
                    if filtro.vocal:
                        form.fields['vocal'].queryset = DetPersonaPadronElectoral.objects.filter(pk=filtro.vocal.pk)
                    else:
                        form.fields['vocal'].queryset = DetPersonaPadronElectoral.objects.none()
                    if filtro.presidente_alterno:
                        form.fields['presidente_alterno'].queryset = DetPersonaPadronElectoral.objects.filter(pk=filtro.presidente_alterno.pk)
                    else:
                        form.fields['presidente_alterno'].queryset = DetPersonaPadronElectoral.objects.none()
                    if filtro.secretario_alterno:
                        form.fields['secretario_alterno'].queryset = DetPersonaPadronElectoral.objects.filter(pk=filtro.secretario_alterno.pk)
                    else:
                        form.fields['secretario_alterno'].queryset = DetPersonaPadronElectoral.objects.none()
                    if filtro.vocal_alterno:
                        form.fields['vocal_alterno'].queryset = DetPersonaPadronElectoral.objects.filter(pk=filtro.vocal_alterno.pk)
                    else:
                        form.fields['vocal_alterno'].queryset = DetPersonaPadronElectoral.objects.none()
                    if filtro.logistica:
                        form.fields['logistica'].queryset = Persona.objects.filter(id__in=filtro.logistica.all().values_list('id', flat=True))
                    else:
                        form.fields['logistica'].queryset = Persona.objects.none()
                    data['form2'] = form
                    template = get_template("adm_padronelectoral/modal/formconfmesa.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'msg': str(ex)})

            elif action == 'buscarempadronados':
                try:
                    id = request.GET['id']
                    filtro = CabPadronElectoral.objects.get(pk=id)
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    querybase = DetPersonaPadronElectoral.objects.filter(status=True, cab=filtro)
                    if len(s) == 1:
                        per = querybase.filter((Q(persona__nombres__icontains=q) | Q(persona__apellido1__icontains=q) | Q(persona__cedula__icontains=q) | Q(persona__apellido2__icontains=q) | Q(persona__cedula__contains=q)), Q(status=True)).distinct()[:15]
                    elif len(s) == 2:
                        per = querybase.filter((Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1])) |
                                               (Q(persona__nombres__icontains=s[0]) & Q(persona__nombres__icontains=s[1])) |
                                               (Q(persona__nombres__icontains=s[0]) & Q(persona__apellido1__contains=s[1]))).filter(status=True).distinct()[:15]
                    else:
                        per = querybase.filter((Q(persona__nombres__contains=s[0]) & Q(persona__apellido1__contains=s[1]) & Q(persona__apellido2__contains=s[2])) |
                                               (Q(persona__nombres__contains=s[0]) & Q(persona__nombres__contains=s[1]) & Q(persona__apellido1__contains=s[2]))).filter(status=True).distinct()[:15]

                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": "{} - {}".format(x.persona.cedula, x.persona.nombre_completo())}
                                        for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'editgremiosconfmesa':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ConfiguracionMesaResponsable.objects.get(pk=request.GET['id'])
                    data['cab'] = periodo = filtro.periodo
                    data['mesas'] = mesas = DetalleMesa.objects.filter(status=True, mesa_responsable=filtro).order_by('gremio_periodo__gremio__nombre')
                    template = get_template("adm_padronelectoral/modal/formgremioconfmesa.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'asignarresponsablemesa':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ConfiguracionMesaResponsable.objects.get(pk=request.GET['id'])
                    idspresidentes = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, presidente__isnull=False).values_list('presidente__id', flat=True)
                    idssecretarios = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, secretario__isnull=False).values_list('secretario__id', flat=True)
                    idsvocales = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, vocal__isnull=False).values_list('vocal__id', flat=True)
                    idspresidentesalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, presidente_alterno__isnull=False).values_list('presidente_alterno__id', flat=True)
                    idssecretariosalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, secretario_alterno__isnull=False).values_list('secretario_alterno__id', flat=True)
                    idsvocalesalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, vocal_alterno__isnull=False).values_list('vocal_alterno__id', flat=True)
                    listaexcluir = list(idspresidentes) + list(idssecretarios) + list(idsvocales) + list(idspresidentesalternos) + list(idssecretariosalternos) + list(idsvocalesalternos)
                    data['presidente'] = presidente = DetPersonaPadronElectoral.objects.filter(cab=filtro.periodo, status=True, excluir=False, tipo=2).exclude(pk__in=listaexcluir).order_by('?').first()
                    listaexcluir.append(presidente.pk)
                    data['secretario'] = secretario = DetPersonaPadronElectoral.objects.filter(cab=filtro.periodo, status=True, excluir=False, tipo=2).exclude(pk__in=listaexcluir).order_by('?').first()
                    if filtro.tipo == 3:
                        vocal = DetPersonaPadronElectoral.objects.filter(cab=filtro.periodo, status=True, excluir=False, tipo=3).exclude(pk__in=listaexcluir).order_by('?').first()
                    else:
                        sedeinscritosids = PersonasSede.objects.filter(status=True, sede=filtro.sede).values_list('persona__id', flat=True)
                        vocal = DetPersonaPadronElectoral.objects.filter(cab=filtro.periodo, status=True, excluir=False, tipo=1, persona__in=sedeinscritosids, persona__canton=filtro.sede.canton).exclude(pk__in=listaexcluir).order_by('?').first()
                    data['vocal'] = vocal
                    template = get_template("adm_padronelectoral/modal/asignarresponsable.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'asignarresponsablemesaalterno':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ConfiguracionMesaResponsable.objects.get(pk=request.GET['id'])
                    idspresidentes = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, presidente__isnull=False).values_list('presidente__id', flat=True)
                    idssecretarios = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, secretario__isnull=False).values_list('secretario__id', flat=True)
                    idsvocales = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, vocal__isnull=False).values_list('vocal__id', flat=True)
                    idspresidentesalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, presidente_alterno__isnull=False).values_list('presidente_alterno__id', flat=True)
                    idssecretariosalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, secretario_alterno__isnull=False).values_list('secretario_alterno__id', flat=True)
                    idsvocalesalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, vocal_alterno__isnull=False).values_list('vocal_alterno__id', flat=True)
                    listaexcluir = list(idspresidentes) + list(idssecretarios) + list(idsvocales) + list(idspresidentesalternos) + list(idssecretariosalternos) + list(idsvocalesalternos)
                    data['presidente'] = presidente = DetPersonaPadronElectoral.objects.filter(cab=filtro.periodo, status=True, excluir=False, tipo=2).exclude(pk__in=listaexcluir).order_by('?').first()
                    listaexcluir.append(presidente.pk)
                    data['secretario'] = secretario = DetPersonaPadronElectoral.objects.filter(cab=filtro.periodo, status=True, excluir=False, tipo=2).exclude(pk__in=listaexcluir).order_by('?').first()
                    if filtro.tipo == 3:
                        vocal = DetPersonaPadronElectoral.objects.filter(cab=filtro.periodo, status=True, excluir=False, tipo=3).exclude(pk__in=listaexcluir).order_by('?').first()
                    else:
                        sedeinscritosids = PersonasSede.objects.filter(status=True, sede=filtro.sede).values_list('persona__id', flat=True)
                        vocal = DetPersonaPadronElectoral.objects.filter(cab=filtro.periodo, status=True, excluir=False, tipo=1, persona__in=sedeinscritosids, persona__canton=filtro.sede.canton).exclude(pk__in=listaexcluir).order_by('?').first()
                    data['vocal'] = vocal
                    template = get_template("adm_padronelectoral/modal/asignarresponsablealterno.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'asignarpresidentemesa':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ConfiguracionMesaResponsable.objects.get(pk=request.GET['id'])
                    idspresidentes = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, presidente__isnull=False).values_list('presidente__id', flat=True)
                    idssecretarios = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, secretario__isnull=False).values_list('secretario__id', flat=True)
                    idsvocales = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, vocal__isnull=False).values_list('vocal__id', flat=True)
                    idspresidentesalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, presidente_alterno__isnull=False).values_list('presidente_alterno__id', flat=True)
                    idssecretariosalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, secretario_alterno__isnull=False).values_list('secretario_alterno__id', flat=True)
                    idsvocalesalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, vocal_alterno__isnull=False).values_list('vocal_alterno__id', flat=True)
                    listaexcluir = list(idspresidentes) + list(idssecretarios) + list(idsvocales) + list(idspresidentesalternos) + list(idssecretariosalternos) + list(idsvocalesalternos)
                    data['presidente'] = presidente = DetPersonaPadronElectoral.objects.filter(cab=filtro.periodo, status=True, excluir=False, tipo=2).exclude(pk__in=listaexcluir).order_by('?').first()
                    template = get_template("adm_padronelectoral/modal/asignarresponsable.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'asignarsecretariomesa':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ConfiguracionMesaResponsable.objects.get(pk=request.GET['id'])
                    idspresidentes = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, presidente__isnull=False).values_list('presidente__id', flat=True)
                    idssecretarios = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, secretario__isnull=False).values_list('secretario__id', flat=True)
                    idsvocales = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, vocal__isnull=False).values_list('vocal__id', flat=True)
                    idspresidentesalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, presidente_alterno__isnull=False).values_list('presidente_alterno__id', flat=True)
                    idssecretariosalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, secretario_alterno__isnull=False).values_list('secretario_alterno__id', flat=True)
                    idsvocalesalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, vocal_alterno__isnull=False).values_list('vocal_alterno__id', flat=True)
                    listaexcluir = list(idspresidentes) + list(idssecretarios) + list(idsvocales) + list(idspresidentesalternos) + list(idssecretariosalternos) + list(idsvocalesalternos)
                    data['secretario'] = secretario = DetPersonaPadronElectoral.objects.filter(cab=filtro.periodo, status=True, excluir=False, tipo=2).exclude(pk__in=listaexcluir).order_by('?').first()
                    template = get_template("adm_padronelectoral/modal/asignarresponsable.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'asignarvocalmesa':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ConfiguracionMesaResponsable.objects.get(pk=request.GET['id'])
                    idspresidentes = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, presidente__isnull=False).values_list('presidente__id', flat=True)
                    idssecretarios = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, secretario__isnull=False).values_list('secretario__id', flat=True)
                    idsvocales = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, vocal__isnull=False).values_list('vocal__id', flat=True)
                    idspresidentesalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, presidente_alterno__isnull=False).values_list('presidente_alterno__id', flat=True)
                    idssecretariosalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, secretario_alterno__isnull=False).values_list('secretario_alterno__id', flat=True)
                    idsvocalesalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, vocal_alterno__isnull=False).values_list('vocal_alterno__id', flat=True)
                    listaexcluir = list(idspresidentes) + list(idssecretarios) + list(idsvocales) + list(idspresidentesalternos) + list(idssecretariosalternos) + list(idsvocalesalternos)
                    if filtro.tipo == 3:
                        vocal = DetPersonaPadronElectoral.objects.filter(cab=filtro.periodo, status=True, excluir=False, tipo=3).exclude(pk__in=listaexcluir).order_by('?').first()
                    else:
                        sedeinscritosids = PersonasSede.objects.filter(status=True, sede=filtro.sede).values_list('persona__id', flat=True)
                        vocal = DetPersonaPadronElectoral.objects.filter(cab=filtro.periodo, status=True, excluir=False, tipo=1, persona__in=sedeinscritosids).exclude(pk__in=listaexcluir).order_by('?').first()
                    data['vocal'] = vocal
                    template = get_template("adm_padronelectoral/modal/asignarresponsable.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'asignarpresidentemesaalterno':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ConfiguracionMesaResponsable.objects.get(pk=request.GET['id'])
                    idspresidentes = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, presidente__isnull=False).values_list('presidente__id', flat=True)
                    idssecretarios = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, secretario__isnull=False).values_list('secretario__id', flat=True)
                    idsvocales = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, vocal__isnull=False).values_list('vocal__id', flat=True)
                    idspresidentesalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, presidente_alterno__isnull=False).values_list('presidente_alterno__id', flat=True)
                    idssecretariosalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, secretario_alterno__isnull=False).values_list('secretario_alterno__id', flat=True)
                    idsvocalesalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, vocal_alterno__isnull=False).values_list('vocal_alterno__id', flat=True)
                    listaexcluir = list(idspresidentes) + list(idssecretarios) + list(idsvocales) + list(idspresidentesalternos) + list(idssecretariosalternos) + list(idsvocalesalternos)
                    data['presidente'] = presidente = DetPersonaPadronElectoral.objects.filter(cab=filtro.periodo, status=True, excluir=False, tipo=2).exclude(pk__in=listaexcluir).order_by('?').first()
                    template = get_template("adm_padronelectoral/modal/asignarresponsablealterno.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'asignarsecretariomesaalterno':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ConfiguracionMesaResponsable.objects.get(pk=request.GET['id'])
                    idspresidentes = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, presidente__isnull=False).values_list('presidente__id', flat=True)
                    idssecretarios = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, secretario__isnull=False).values_list('secretario__id', flat=True)
                    idsvocales = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, vocal__isnull=False).values_list('vocal__id', flat=True)
                    idspresidentesalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, presidente_alterno__isnull=False).values_list('presidente_alterno__id', flat=True)
                    idssecretariosalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, secretario_alterno__isnull=False).values_list('secretario_alterno__id', flat=True)
                    idsvocalesalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, vocal_alterno__isnull=False).values_list('vocal_alterno__id', flat=True)
                    listaexcluir = list(idspresidentes) + list(idssecretarios) + list(idsvocales) + list(idspresidentesalternos) + list(idssecretariosalternos) + list(idsvocalesalternos)
                    data['secretario'] = secretario = DetPersonaPadronElectoral.objects.filter(cab=filtro.periodo, status=True, excluir=False, tipo=2).exclude(pk__in=listaexcluir).order_by('?').first()
                    template = get_template("adm_padronelectoral/modal/asignarresponsablealterno.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'asignarvocalmesaalterno':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ConfiguracionMesaResponsable.objects.get(pk=request.GET['id'])
                    idspresidentes = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, presidente__isnull=False).values_list('presidente__id', flat=True)
                    idssecretarios = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, secretario__isnull=False).values_list('secretario__id', flat=True)
                    idsvocales = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, vocal__isnull=False).values_list('vocal__id', flat=True)
                    idspresidentesalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, presidente_alterno__isnull=False).values_list('presidente_alterno__id', flat=True)
                    idssecretariosalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, secretario_alterno__isnull=False).values_list('secretario_alterno__id', flat=True)
                    idsvocalesalternos = ConfiguracionMesaResponsable.objects.filter(status=True, periodo=filtro.periodo, vocal_alterno__isnull=False).values_list('vocal_alterno__id', flat=True)
                    listaexcluir = list(idspresidentes) + list(idssecretarios) + list(idsvocales) + list(idspresidentesalternos) + list(idssecretariosalternos) + list(idsvocalesalternos)
                    if filtro.tipo == 3:
                        vocal = DetPersonaPadronElectoral.objects.filter(cab=filtro.periodo, status=True, excluir=False, tipo=3).exclude(pk__in=listaexcluir).order_by('?').first()
                    else:
                        sedeinscritosids = PersonasSede.objects.filter(status=True, sede=filtro.sede).values_list('persona__id', flat=True)
                        vocal = DetPersonaPadronElectoral.objects.filter(cab=filtro.periodo, status=True, excluir=False, tipo=1, persona__in=sedeinscritosids).exclude(pk__in=listaexcluir).order_by('?').first()
                    data['vocal'] = vocal
                    template = get_template("adm_padronelectoral/modal/asignarresponsablealterno.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'buscarmesasgremio':
                try:
                    id, cabid = request.GET['id'], request.GET['cabid']
                    periodo = CabPadronElectoral.objects.get(pk=cabid)
                    filtro = ConfiguracionMesaResponsable.objects.get(pk=id)
                    querybase = GremioPeriodo.objects.filter(status=True, periodo=periodo, tipo=filtro.tipo)
                    if 'search' in request.GET:
                        search = request.GET['search']
                        querybase = querybase.filter(Q(gremio__nombre__icontains=search) | Q(coordinacion__nombre__icontains=search)).order_by('gremio__nombre')
                    resp = [{'id': cr.pk, 'text': cr.__str__()} for cr in querybase.distinct()]
                    return HttpResponse(json.dumps({'state': True, 'result': resp}))
                except Exception as ex:
                    pass

            elif action == 'datosgremio':
                try:
                    gremio = GremioPeriodo.objects.get(id=request.GET['valor'])
                    gremionombre = gremio.gremio.nombre if gremio.gremio else ''
                    gremionombre = f"{gremionombre} - {gremio.get_tipo_display()}"
                    coordinacionnombre = gremio.coordinacion.nombre if gremio.coordinacion else ''
                    response = JsonResponse({'resp': True, 'gremio': model_to_dict(gremio), 'id': gremio.pk, 'coordinacionnombre': coordinacionnombre, 'gremionombre': gremionombre})
                    return HttpResponse(response.content)
                except Exception as ex:
                    response = JsonResponse({'resp': False})
                    return HttpResponse(response.content)

            elif action == 'mostrarpdf':
                try:
                    presidente, secretario, vocal = request.GET.get('presidente', ''), request.GET.get('secretario', ''), request.GET.get('vocal', '')
                    presidente_alterno, secretario_alterno, vocal_alterno = request.GET.get('presidentealterno', ''), request.GET.get('secretarioalterno', ''), request.GET.get('vocalalterno', '')
                    conf = ConfiguracionMesaResponsable.objects.get(pk=int(request.GET['id']))
                    if presidente:
                        presidente = DetPersonaPadronElectoral.objects.get(pk=presidente)
                        pdf_acta = mostrar_mesa_pdf(request, data, conf.id, presidente.id, 1)
                    if secretario:
                        secretario = DetPersonaPadronElectoral.objects.get(pk=secretario)
                        pdf_acta = mostrar_mesa_pdf(request, data, conf.id, secretario.id, 2)
                    if vocal:
                        vocal = DetPersonaPadronElectoral.objects.get(pk=vocal)
                        pdf_acta = mostrar_mesa_pdf(request, data, conf.id, vocal.id, 3)
                    if presidente_alterno:
                        presidente_alterno = DetPersonaPadronElectoral.objects.get(pk=presidente_alterno)
                        pdf_acta = mostrar_mesa_pdf(request, data, conf.id, presidente_alterno.id, 4)
                    if secretario_alterno:
                        secretario_alterno = DetPersonaPadronElectoral.objects.get(pk=secretario_alterno)
                        pdf_acta = mostrar_mesa_pdf(request, data, conf.id, secretario_alterno.id, 5)
                    if vocal_alterno:
                        vocal_alterno = DetPersonaPadronElectoral.objects.get(pk=vocal_alterno)
                        pdf_acta = mostrar_mesa_pdf(request, data, conf.id, vocal_alterno.id, 6)
                    return HttpResponseRedirect('https://sga.unemi.edu.ec/media/' + str(pdf_acta))
                except Exception as e:
                    messages.error(request, str(e))

            return HttpResponseRedirect(request.path)
        else:

            if not request.user.is_superuser:
                return redirect('/')

            data['title'] = u'Evento Electoral'
            url_vars = ''
            filtro = Q(status=True)
            search = None
            ids = None

            if 's' in request.GET:
                if request.GET['s'] != '':
                    search = request.GET['s']

            if search:
                filtro = filtro & (Q(nombre__icontains=search))
                url_vars += '&s=' + search

            filtro = CabPadronElectoral.objects.filter(filtro).order_by('-fecha')
            paging = MiPaginador(filtro, 25)
            p = 1
            try:
                paginasesion = 1
                if 'paginador' in request.session:
                    paginasesion = int(request.session['paginador'])
                if 'page' in request.GET:
                    p = int(request.GET['page'])
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
            data["url_vars"] = url_vars
            data['ids'] = ids if ids else ""
            data['listado'] = page.object_list
            data['email_domain'] = EMAIL_DOMAIN
            CabPadronElectoral.objects.filter(fecha__lt=datetime.now().date()).update(activo=False)

            data['existeuno'] = CabPadronElectoral.objects.filter(activo=True, status=True).exists()
            return render(request, 'adm_padronelectoral/view.html', data)



def generar_qr_padronelectoral(person, **kwargs):
    from hashlib import md5
    from settings import  SITE_STORAGE, DEBUG

    from sga.templatetags.sga_extras import encrypt
    unicode = str
    try:
        ahora = datetime.now()
        url_path = 'http://127.0.0.1:8000'
        if not DEBUG:
            url_path = 'https://sga.unemi.edu.ec'

        try:
            eReporte = Reporte.objects.get(pk=662)
        except ObjectDoesNotExist:
            raise NameError(u"Reporte no encontrado")

        ePersona = person.persona
        eUser = ePersona.usuario
        username = eUser.username

        output_folder_pdf = os.path.join(os.path.join(SITE_STORAGE, 'media', 'mesa', ePersona.documento(), 'pdf'))
        output_folder_images = os.path.join(os.path.join(SITE_STORAGE, 'media', 'mesa', ePersona.documento(), 'images'))
        try:
            shutil.rmtree(output_folder_pdf)
        except Exception as ex:
            pass
        try:
            os.makedirs(output_folder_pdf)
        except Exception as ex:
            pass
        try:
            shutil.rmtree(output_folder_images)
        except Exception as ex:
            pass
        try:
            os.makedirs(output_folder_images)
        except Exception as ex:
            pass
        pdfname = str(uuid.uuid4())
        folder_pdf = os.path.join(
            os.path.join(SITE_STORAGE, 'media', 'mesa', ePersona.documento(),
                          'pdf', ''))
        qrname = str(uuid.uuid4())
        folder_qr = os.path.join(
            os.path.join(SITE_STORAGE, 'media', 'mesa', ePersona.documento(),
                          'images', ''))
        rutapdf = folder_pdf + pdfname + '.pdf'
        rutaqr = folder_qr + qrname + '.png'
        if os.path.isfile(rutapdf):
            os.remove(rutapdf)
        if os.path.isfile(rutaqr):
            os.remove(rutaqr)
        fecha_hora = ahora.year.__str__() + ahora.month.__str__() + ahora.day.__str__() + ahora.hour.__str__() + ahora.minute.__str__() + ahora.second.__str__()
        dataqr = md5(str(encrypt(ePersona.id) + fecha_hora + ePersona.cedula + username).encode("utf-8")).hexdigest()
        codigoqr = pyqrcode.create(dataqr)
        person.codigo_qr = dataqr
        codigoqr.png(rutaqr, scale=5)
        url_pdf = "/".join(['mesa', ePersona.documento(), 'pdf', pdfname + ".pdf"])
        url_qr = "/".join(['mesa',  ePersona.documento(), 'images', qrname + ".png"])
        runjrcommand = [JR_JAVA_COMMAND, '-jar',
                        os.path.join(JR_RUN, 'jasperstarter.jar'),
                        'pr', eReporte.archivo.file.name,
                        '--jdbc-dir', JR_RUN,
                        '-f', 'pdf',
                        '-t', 'postgres',
                        '-H', DATABASES['sga_select']['HOST'],
                        '-n', DATABASES['sga_select']['NAME'],
                        '-u', DATABASES['sga_select']['USER'],
                        '-p', f"'{DATABASES['sga_select']['PASSWORD']}'",
                        '--db-port', DATABASES['sga_select']['PORT'],
                        '-o', output_folder_pdf + os.sep + pdfname]
        parametros = eReporte.parametros()
        if kwargs:
            paramlist = [transform_jasperstarter_kwargs(p, **kwargs) for p in parametros]

        if paramlist:
            runjrcommand.append('-P')
            for parm in paramlist:
                runjrcommand.append(parm)
        else:
            runjrcommand.append('-P')
        # base_url = get_variable('SITE_URL_SGA')
        runjrcommand.append(u'MEDIA_DIR=' + str("/".join([MEDIA_ROOT, ''])))
        # static_dir = f"{url_path}/static/img/"
        static_dir = os.path.join(SITE_ROOT, 'static', 'img')
        runjrcommand.append(u'STATIC_DIR=' + str("/".join([static_dir, ''])))
        runjrcommand.append(u'QR_DIR=' + str(rutaqr))
        mens = ''
        mensaje = ''
        for m in runjrcommand:
            mens += ' ' + m
        if DEBUG:
            runjr = subprocess.run(mens, shell=True, check=True)

        else:
            runjr = subprocess.call(mens.encode("latin1"), shell=True)
        print('mens:', mens)


        person.fechageneracionpdf = ahora
        person.save()

        return {"isSuccess": True, "message": 'Se genero correctamente código QR', "data": {"url_pdf": url_pdf, "pdfname": pdfname, "url_qr": url_qr, "codigo_qr": dataqr}}

    except Exception as ex:
        error_linea = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
        print(error_linea)
        print(ex)
        return {"isSuccess": False, "message": ex.__str__()}



