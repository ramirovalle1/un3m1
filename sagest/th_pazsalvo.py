# -*- coding: latin-1 -*-
import io
import json
import os
import random
import sys
import zipfile
import pandas as pd
import pyqrcode
import xlsxwriter
from django.contrib import messages
from django.core.files import File as DjangoFile
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Max, F, Sum
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404

from core.firmar_documentos import obtener_posicion_x_y_saltolinea
from core.firmar_documentos_ec import JavaFirmaEc
from core.firmar_documentos_ec_descentralizada import qrImgFirma
from sagest.forms import ComponenteActivoForm, FormatoPazSalvoForm, DireccionFormatoPSForm, \
    DetalleDireccionFormatoPSForm, PazSalvoForm, PreguntaGeneralFormatoPSForm, RequisitoPazSalvoForm, \
    ValidarRequisitoForm, FechaInicioFinForm, ComprimidoForm, ObservacionPazSalvoForm, MatrizTramitePazySalvoForm
from sagest.models import FormatoPazSalvo, DireccionFormatoPS, DetalleDireccionFormatoPS, DistributivoPersona, DenominacionPuesto, Departamento, PazSalvo, CertificadoFirmaPS, \
    HistorialCertificadoFirmaPS, DetallePazSalvo, ResponsableFirmaPS, ActivoTecnologico, DistributivoPersonaHistorial, RequisitoPazSalvo, ESTADO_PAZ_SALVO, ESTADOS_DOCUMENTOS_PAZ_SALVO, \
    DocumentoPazSalvo, ObservacionPazSalvo, ESTADO_TRAMITE_PAGO_PAZ_SALVO
from decorators import secure_module
from settings import MEDIA_ROOT, SITE_STORAGE
from sga.commonviews import adduserdata
from sga.excelbackground import descarga_masiva_requisitos_pazsalvo_background
from sga.funciones import MiPaginador, log, generar_nombre, notificacion
from django.template.loader import get_template
from django.forms import model_to_dict

from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqr_generico
from sga.models import Notificacion, Persona, CUENTAS_CORREOS
from sagest.funciones import dominio_sistema_base, encrypt_id
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from utils.filtros_genericos import filtro_persona, filtro_persona_select
from unidecode import unidecode
unicode = str


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    cargo = persona.mi_cargo_administrativo()
    data['DOMINIO_SISTEMA'] = dominio_sistema = dominio_sistema_base(request)
    data['formato'] = formato = FormatoPazSalvo.objects.filter(status=True, activo=True).first()
    hoy = datetime.now()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'addpazsalvo':
                try:
                    form = PazSalvoForm(request.POST)
                    formato = FormatoPazSalvo.objects.filter(status=True, activo=True).last()
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    if not formato:
                        raise NameError('No existe un formato activado de paz y salvo para generar la solicitud')
                    pazsalvo = PazSalvo(formato=formato,
                                        persona=form.cleaned_data['persona'],
                                        departamento=form.cleaned_data['departamento'],
                                        cargo=form.cleaned_data['cargo'],
                                        tiporelacion=form.cleaned_data['tiporelacion'],
                                        ultimaremuneracion=form.cleaned_data['ultimaremuneracion'],
                                        fecha=form.cleaned_data['fecha'],
                                        motivosalida=form.cleaned_data['motivosalida'],
                                        estado=1,
                                        jefeinmediato=form.cleaned_data['jefeinmediato'])
                    pazsalvo.save(request)
                    sexo = 'o' if pazsalvo.jefeinmediato.sexo.id == 2 else 'a'
                    titulo = 'Certificado de paz y salvo pendiente de responder'
                    observacion = f'Estimado{sexo} {pazsalvo.jefeinmediato.nombre_completo_minus()} existe un nuevo certificado de paz y salvo de {pazsalvo.persona.nombre_completo_minus()} que necesita ser llenada y firmada por su persona.'
                    notificacion(titulo, observacion, pazsalvo.jefeinmediato, None, f'/th_pazsalvo?s={pazsalvo.persona.cedula}', pazsalvo.pk, 2, 'sga-sagest', PazSalvo, request)
                    for distributivo in formato.responsables_dp():
                        if not distributivo.persona.id == pazsalvo.jefeinmediato.id:
                            resp = distributivo.persona
                            sexo = 'o' if resp.sexo.id == 2 else 'a'
                            cuerpo = f'Estimad{sexo} {distributivo.persona.nombre_completo_minus()}  existe un nuevo certificado de paz y salvo de {pazsalvo.persona.nombre_completo_minus()} que necesita ser llenada y firmada por su persona.'
                            notificacion(titulo, cuerpo, distributivo.persona,
                                         None, f'/th_pazsalvo?s={pazsalvo.persona.cedula}', distributivo.persona.pk, 2, 'sagest',
                                         PazSalvo, request)
                    log(f'Agrego paz y salvo: {pazsalvo}', request, 'add')
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, 'mensaje': str(ex)})

            if action == 'editpazsalvo':
                try:
                    pazsalvo = PazSalvo.objects.get(id=encrypt_id(request.POST['id']))
                    form = PazSalvoForm(request.POST, instancia=pazsalvo)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    pazsalvo.persona = form.cleaned_data['persona']
                    pazsalvo.departamento = form.cleaned_data['departamento']
                    pazsalvo.cargo = form.cleaned_data['cargo']
                    pazsalvo.tiporelacion = form.cleaned_data['tiporelacion']
                    pazsalvo.jefeinmediato = form.cleaned_data['jefeinmediato']
                    pazsalvo.ultimaremuneracion = form.cleaned_data['ultimaremuneracion']
                    pazsalvo.fecha = form.cleaned_data['fecha']
                    pazsalvo.motivosalida=form.cleaned_data['motivosalida']
                    pazsalvo.save(request)
                    log(f'Edito paz y salvo: {pazsalvo}', request, 'edit')
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, 'mensaje': str(ex)})

            elif action == 'delpazsalvo':
                with transaction.atomic():
                    try:
                        instancia = PazSalvo.objects.get(pk=int(encrypt(request.POST['id'])))
                        instancia.status = False
                        instancia.save(request)
                        log(u'Elimino paz salvo: %s' % instancia, request, "del")
                        res_json = {"error": False, "mensaje": 'Registro eliminado'}
                    except Exception as ex:
                        res_json = {'error': True, "message": "Error: {}".format(ex)}
                    return JsonResponse(res_json, safe=False)

            elif action == 'addformato':
                try:
                    form = FormatoPazSalvoForm(request.POST)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    formato = FormatoPazSalvo(titulo=form.cleaned_data['titulo'],
                                              descripcion=form.cleaned_data['descripcion'],
                                              activo=form.cleaned_data['activo'])
                    formato.save(request)
                    if form.cleaned_data['activo']:
                        FormatoPazSalvo.objects.filter().exclude(id=formato.id).update(activo=False)
                    log(f'Agrego formato de paz y salvo: {formato}', request, 'add')
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, 'mensaje': str(ex)})

            elif action == 'editformato':
                try:
                    formato = FormatoPazSalvo.objects.get(id=int(encrypt(request.POST['id'])))
                    form = FormatoPazSalvoForm(request.POST, instancia=formato)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    formato.titulo = form.cleaned_data['titulo']
                    formato.descripcion = form.cleaned_data['descripcion']
                    formato.activo = form.cleaned_data['activo']
                    formato.save(request)
                    if form.cleaned_data['activo']:
                        FormatoPazSalvo.objects.filter().exclude(id=formato.id).update(activo=False)
                    log(f'Edito formato de paz y salvo: {formato}', request, 'edit')
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, 'mensaje': str(ex)})

            elif action == 'activarformato':
                try:
                    FormatoPazSalvo.objects.filter().update(activo=False)
                    formato = FormatoPazSalvo.objects.get(id=int(request.POST['id']))
                    formato.activo = eval(request.POST['val'].capitalize())
                    formato.save(request)
                    log(f'Edito formato de paz y salvo: {formato}', request, 'edit')
                    return JsonResponse({'result': True, 'mensaje': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': False, 'mensaje': str(ex)})

            elif action == 'delformato':
                try:
                    formato = FormatoPazSalvo.objects.get(id=int(encrypt(request.POST['id'])))
                    formato.status = False
                    formato.save(request)
                    log(f'Elimino formato de paz y salvo: {formato}', request, 'del')
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            elif action == 'addpreguntageneral':
                with transaction.atomic():
                    try:
                        idp = int(encrypt(request.POST['idp']))
                        formato = FormatoPazSalvo.objects.get(id=idp)
                        form = PreguntaGeneralFormatoPSForm(request.POST, instancia=formato)
                        if not form.is_valid():
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "mensaje": "Error en el formulario"})
                        detalle = DetalleDireccionFormatoPS(formato=formato,
                                                            descripcion=form.cleaned_data['descripcion'])
                        detalle.save(request)
                        diccionario = {'id': encrypt(detalle.id),
                                       'pregunta': detalle.descripcion,
                                       }
                        log(u'Agrego pregunta a formato: %s' % detalle, request, "add")
                        return JsonResponse({'result': True, 'data_return': True, 'mensaje': u'Guardado con éxito', 'data': diccionario})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

            elif action == 'editpreguntageneral':
                with transaction.atomic():
                    try:
                        id = int(encrypt(request.POST['id']))
                        detalle = DetalleDireccionFormatoPS.objects.get(id=id)
                        form = PreguntaGeneralFormatoPSForm(request.POST, instancia=detalle)
                        if not form.is_valid():
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "mensaje": "Error en el formulario"})
                        detalle.descripcion = form.cleaned_data['descripcion']
                        detalle.save(request)
                        diccionario = {'id': encrypt(detalle.id),
                                       'pregunta': detalle.descripcion,
                                       'edit': True,
                                       }
                        log(u'Edito pregunta a dirección: %s' % detalle, request, "edit")
                        return JsonResponse({'result': True, 'data_return': True, 'mensaje': u'Guardado con éxito', 'data': diccionario})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

            elif action == 'adddireccion':
                try:
                    form = DireccionFormatoPSForm(request.POST)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    direccion = DireccionFormatoPS(formato_id=int(encrypt(request.POST['idp'])),
                                                   departamento=form.cleaned_data['departamento'],
                                                   orden=form.cleaned_data['orden']
                                                   )
                    direccion.save(request)
                    log(f'Agrego direccion a formato de paz y salvo: {direccion}', request, 'add')
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, 'mensaje': str(ex)})

            elif action == 'editdireccion':
                try:
                    direccion = DireccionFormatoPS.objects.get(id=int(encrypt(request.POST['id'])))
                    form = DireccionFormatoPSForm(request.POST, instancia=direccion)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    direccion.departamento = form.cleaned_data['departamento']
                    direccion.orden = form.cleaned_data['orden']
                    direccion.save(request)
                    log(f'Edito dirección a formato de paz y salvo: {direccion}', request, 'edit')
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, 'mensaje': str(ex)})

            elif action == 'deldireccion':
                try:
                    direccion = DireccionFormatoPS.objects.get(id=int(encrypt(request.POST['id'])))
                    direccion.status = False
                    direccion.save(request)
                    direccion.preguntas().update(status=False)
                    log(f'Elimino dirección a formato de paz y salvo: {direccion}', request, 'del')
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            elif action == 'addpregunta':
                with transaction.atomic():
                    try:
                        idp = int(encrypt(request.POST['idp']))
                        direccion_f = DireccionFormatoPS.objects.get(id=idp)
                        form = DetalleDireccionFormatoPSForm(request.POST, instancia=direccion_f)
                        if not form.is_valid():
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "mensaje": "Error en el formulario"})
                        detalle = DetalleDireccionFormatoPS(direccionformato_id=direccion_f.id,
                                                            cargo=form.cleaned_data['cargo'],
                                                            descripcion=form.cleaned_data['descripcion'])
                        detalle.save(request)
                        diccionario = {'id': encrypt(detalle.id),
                                       'pregunta': detalle.descripcion,
                                       'cargo': detalle.cargo.descripcion.capitalize(),
                                       'cargo_id': detalle.cargo.id,
                                       }
                        log(u'Agrego pregunta a dirección: %s' % detalle, request, "add")
                        return JsonResponse({'result': True, 'data_return': True, 'mensaje': u'Guardado con éxito', 'data': diccionario})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

            elif action == 'editpregunta':
                with transaction.atomic():
                    try:
                        id = int(encrypt(request.POST['id']))
                        detalle = DetalleDireccionFormatoPS.objects.get(id=id)
                        form = DetalleDireccionFormatoPSForm(request.POST, instancia=detalle)
                        if not form.is_valid():
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "mensaje": "Error en el formulario"})
                        detalle.cargo = form.cleaned_data['cargo']
                        detalle.descripcion = form.cleaned_data['descripcion']
                        detalle.save(request)
                        diccionario = {'id': encrypt(detalle.id),
                                       'pregunta': detalle.descripcion,
                                       'cargo': detalle.cargo.descripcion.capitalize(),
                                       'cargo_id': detalle.cargo.id,
                                       'en_uso': detalle.en_uso(),
                                       'edit': True,
                                       }
                        log(u'Edito pregunta a dirección: %s' % detalle, request, "edit")
                        return JsonResponse({'result': True, 'data_return': True, 'mensaje': u'Guardado con éxito', 'data': diccionario})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

            elif action == 'delpregunta':
                with transaction.atomic():
                    try:
                        instancia = DetalleDireccionFormatoPS.objects.get(pk=int(encrypt(request.POST['id'])))
                        instancia.status = False
                        instancia.save(request)
                        DetallePazSalvo.objects.filter(status=True, pregunta=instancia).update(status=False)
                        log(u'Elimino pregunta de dirección: %s' % instancia, request, "del")
                        res_json = {"error": False, "mensaje": 'Registro eliminado'}
                    except Exception as ex:
                        res_json = {'error': True, "message": "Error: {}".format(ex)}
                    return JsonResponse(res_json, safe=False)

            elif action == 'responderpreguntas':
                with transaction.atomic():
                    try:
                        respuestas = json.loads(request.POST['lista_items1'])
                        pazsalvo = PazSalvo.objects.get(id=encrypt_id(request.POST['id']))
                        if 'observaciongeneral' in request.POST:
                            pazsalvo.observacion=request.POST['observaciongeneral']
                            pazsalvo.save(request)

                        for r in respuestas:
                            respuesta = encrypt_id(r['id_respuesta'])
                            if respuesta == 0:
                                detalle = DetallePazSalvo(persona=persona,
                                                          pazsalvo=pazsalvo,
                                                          pregunta_id=encrypt_id(r['id_pregunta']),
                                                          observacion=r['observacion'],
                                                          respondio=True,
                                                          marcado=r['marcado'])
                                detalle.save(request)
                                log(u'Agrego respuesta a dirección: %s' % detalle, request, "add")
                            else:
                                detalle = DetallePazSalvo.objects.get(id=respuesta)
                                if not detalle.pregunta.logicamodelo:
                                    detalle.marcado = r['marcado']
                                    detalle.observacion = r['observacion']
                                    detalle.persona = persona
                                    detalle.respondio = True
                                    detalle.save(request)
                                    log(u'Edito respuesta a dirección: %s' % detalle, request, "edit")
                        if pazsalvo.respondio_all() and pazsalvo.estado in [1, 2] and pazsalvo.puede_editar():
                            url_certificado = generar_certificado(request, pazsalvo)
                            certificado = pazsalvo.documento()
                            if not certificado:
                                certificado = CertificadoFirmaPS(pazsalvo=pazsalvo)
                            certificado.archivo = url_certificado
                            certificado.save(request)

                            # Creamos registro de responsable firma
                            crear_responsables_firma(request, certificado)

                            log(f'Agrego certificado de paz y salvo: {certificado}', request, 'add')

                            historial = HistorialCertificadoFirmaPS(certificadosalida=certificado,
                                                                    archivo=url_certificado,
                                                                    persona=persona,
                                                                    cargo=cargo,
                                                                    estado=1)
                            historial.save(request)
                            pazsalvo.estado = 2
                            pazsalvo.save(request)
                            notificar_firma_responsables(request, certificado)
                            log(f'Agrego historial de firma de paz y salvo: {historial}', request, 'add')
                        return JsonResponse({'result': False, 'mensaje': u'Guardado con éxito'})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

            elif action == 'respuestamasiva':
                with transaction.atomic():
                    try:
                        respuestas = json.loads(request.POST['lista_items1'])
                        ids_pazsalvo = request.POST.getlist('funcionario')
                        for id_p in ids_pazsalvo:
                            pazsalvo=PazSalvo.objects.get(id=int(id_p))
                            if pazsalvo.estado in [1, 2] and pazsalvo.puede_editar():
                                if 'observaciongeneral' in request.POST:
                                    pazsalvo.observacion = request.POST['observaciongeneral']
                                    pazsalvo.save(request)
                                for r in respuestas:
                                    if not r['jefe'] or pazsalvo.jefeinmediato.id == persona.id:
                                        idpregunta=encrypt_id(r['id_pregunta'])
                                        detalle = DetallePazSalvo.objects.filter(status=True, pazsalvo=pazsalvo, pregunta_id=idpregunta,respondio=True).first()
                                        if not detalle:
                                            detalle = DetallePazSalvo(persona=persona,
                                                                      pazsalvo=pazsalvo,
                                                                      pregunta_id=idpregunta,
                                                                      observacion=r['observacion'],
                                                                      respondio=True,
                                                                      marcado=r['marcado'])
                                            detalle.save(request)
                                            log(u'Agrego respuesta a dirección: %s' % detalle, request, "add")
                                        else:
                                            detalle.persona = persona
                                            detalle.marcado = r['marcado']
                                            detalle.observacion = r['observacion']
                                            detalle.save(request)
                                            log(u'Edito respuesta a dirección: %s' % detalle, request, "edit")
                                if pazsalvo.respondio_all():
                                    url_certificado = generar_certificado(request, pazsalvo)
                                    certificado = pazsalvo.documento()
                                    if not certificado:
                                        certificado = CertificadoFirmaPS(pazsalvo=pazsalvo)
                                    certificado.archivo = url_certificado
                                    certificado.save(request)

                                    # Crea el registro de responsable de firmar
                                    crear_responsables_firma(request, certificado)

                                    log(f'Agrego certificado de paz y salvo: {certificado}', request, 'add')

                                    historial = HistorialCertificadoFirmaPS(certificadosalida=certificado,
                                                                            archivo=url_certificado,
                                                                            persona=persona,
                                                                            cargo=cargo,
                                                                            estado=1)
                                    historial.save(request)
                                    pazsalvo.estado = 2
                                    pazsalvo.save(request)
                                    notificar_firma_responsables(request, certificado)
                                    log(f'Agrego historial de firma de paz y salvo: {historial}', request, 'add')
                        return JsonResponse({'result': False, 'mensaje': u'Guardado con éxito'})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

            elif action == 'generarcertificado':
                try:
                    id = encrypt_id(request.POST['id'])
                    pazsalvo = PazSalvo.objects.get(id=id)
                    url_certificado = generar_certificado(request, pazsalvo)
                    certificado = pazsalvo.documento()
                    if not certificado:
                        certificado = CertificadoFirmaPS(pazsalvo=pazsalvo)
                    certificado.archivo = url_certificado
                    certificado.save(request)
                    crear_responsables_firma(request, certificado)
                    log(f'Agrego certificado de paz y salvo: {certificado}', request, 'add')

                    historial = HistorialCertificadoFirmaPS(certificadosalida=certificado,
                                                            archivo=url_certificado,
                                                            persona=persona,
                                                            cargo=cargo,
                                                            estado=1)
                    historial.save(request)
                    pazsalvo.estado = 2
                    pazsalvo.save(request)
                    notificar_firma_responsables(request, certificado)
                    log(f'Agrego historial de firma de paz y salvo: {historial}', request, 'add')
                    res_json = {"result": "ok"}
                except Exception as ex:
                    res_json = {'error': False, "mensaje": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            elif action == 'generarcertificadomasivo':
                try:
                    cont = 0
                    for pazsalvo in formato.pazsalvos():
                        if pazsalvo.estado == 1 and pazsalvo.respondio_all():
                            url_certificado=generar_certificado(request, pazsalvo)
                            certificado=pazsalvo.documento()
                            if not certificado:
                                certificado=CertificadoFirmaPS(pazsalvo=pazsalvo)
                            certificado.archivo = url_certificado
                            certificado.save(request)
                            crear_responsables_firma(request, certificado)
                            log(f'Agrego certificado de paz y salvo: {certificado}', request, 'add')

                            historial = HistorialCertificadoFirmaPS(certificadosalida=certificado,
                                                                    archivo=url_certificado,
                                                                    persona=persona,
                                                                    estado=1)
                            historial.save(request)
                            pazsalvo.estado = 2
                            pazsalvo.save(request)
                            cont += 1
                            log(f'Agrego historial de firma de paz y salvo: {historial}', request, 'add')
                    messages.success(request, f'Se generó {cont} certificados')
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            elif action == 'firmarcertificado':
                try:
                    id = encrypt_id(request.POST['id'])
                    certificado_firma = CertificadoFirmaPS.objects.get(pk=id)
                    documento_a_firmar = certificado_firma.archivo
                    certificado = request.FILES["firma"]
                    contrasenaCertificado = request.POST['palabraclave']
                    razon = request.POST['razon'] if 'razon' in request.POST else ''
                    jsonFirmas = json.loads(request.POST['txtFirmas'])
                    name_documento_a_firmar, extension_documento_a_firmar = f'certificado_{certificado_firma.pazsalvo.persona.usuario}','.pdf'
                    extension_certificado = os.path.splitext(certificado.name)[1][1:]
                    bytes_certificado = certificado.read()
                    if not jsonFirmas:
                        raise NameError("Debe seleccionar ubicación de la firma")
                    for membrete in jsonFirmas:
                        datau = JavaFirmaEc(
                            archivo_a_firmar=documento_a_firmar, archivo_certificado=bytes_certificado, extension_certificado=extension_certificado,
                            password_certificado=contrasenaCertificado,
                            page=int(membrete["numPage"]), reason=razon, lx=membrete["x"], ly=membrete["y"]
                        ).sign_and_get_content_bytes()
                        documento_a_firmar = io.BytesIO()
                        documento_a_firmar.write(datau)
                        documento_a_firmar.seek(0)

                    _name = f"certificado_{certificado_firma.pazsalvo.persona.usuario}"
                    file_obj = DjangoFile(documento_a_firmar, name=f"{_name}.pdf")

                    certificado_firma.archivo = file_obj
                    certificado_firma.save(request)
                    historial = HistorialCertificadoFirmaPS(certificadosalida=certificado_firma,
                                                            archivo=file_obj,
                                                            persona=persona,
                                                            cargo=persona.mi_cargo_administrativo(),
                                                            cantidadfirmas=len(jsonFirmas),
                                                            estado=2)
                    historial.save(request)

                    r_firma = certificado_firma.responsable_firma(persona)
                    if r_firma:
                        r_firma.firmado = r_firma.total_firmado() >= r_firma.cantidadfirmas
                        r_firma.save(request)
                        log(u'Edito Responsable firma: {}'.format(r_firma), request, "edit")

                    if certificado_firma.firmado_all():
                        pazsalvo=certificado_firma.pazsalvo
                        pazsalvo.estado = 3
                        pazsalvo.save(request)
                        log(u'Edito paz y salvo: {}'.format(pazsalvo), request, "edit")

                    log(u'Firmo Documento: {}'.format(name_documento_a_firmar), request, "add")
                    return JsonResponse({'result': False, 'mensaje': 'Guardado correctamente'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

            elif action == 'firmarcertificadomasivo':
                try:
                    certificado = request.FILES["firma"]
                    contrasenaCertificado = request.POST['palabraclave']
                    razon = request.POST['razon'] if 'razon' in request.POST else ''
                    extension_certificado = os.path.splitext(certificado.name)[1][1:]
                    bytes_certificado = certificado.read()
                    # pazsalvos = PazSalvo.objects.filter(status=True, formato=formato, estado=2)
                    limit=int(request.POST['val_extra'])
                    responsables_firma = ResponsableFirmaPS.objects.filter(status=True, persona=persona, certificado__pazsalvo__estado=2, firmado=False)[:limit]
                    for responsable in responsables_firma:
                        try:
                            firmas = []
                            pazsalvo = responsable.certificado.pazsalvo
                            # Otra maneras de traer el certificado:
                            # certificado_firma = pazsalvo.documento()
                            # certificado_firma = pazsalvo.documento().ultimo_archivo()
                            certificado_firma = responsable.certificado
                            archivo_ = certificado_firma.archivo
                            registro = persona.titulacion_principal_senescyt_registro()
                            titulo_nombres = f'{persona}'
                            if registro and registro.titulo:
                                titulo = registro.titulo.abreviatura
                                titulo_nombres = f'{titulo} {persona}'.strip()
                            es_responsable_dir = pazsalvo.es_responsable_direccion(persona.mi_cargo_administrativo().id)
                            if pazsalvo.es_jefe(persona):
                                palabras = f'{titulo_nombres} FIRMA DE JEFE INMEDIATO'
                                x, y, numPage = obtener_posicion_x_y_saltolinea(archivo_.url, palabras, False)
                                if x and y:
                                    x = x + 53
                                    y = y + 10
                                    firmas.append({'x': x, 'y': y, 'numPage': numPage})
                            if es_responsable_dir:
                                cargo = f'RESPONSABLE DE LA {pazsalvo.direccion_persona(persona).departamento.nombre}'
                                palabras = f'{titulo_nombres} {cargo}'
                                x, y, numPage = obtener_posicion_x_y_saltolinea(archivo_.url, palabras, False)
                                if x and y:
                                    x = x + len(palabras) + 8
                                    y = y + 10
                                    firmas.append({'x': x, 'y': y, 'numPage': numPage})
                            if responsable.get_cargo().id in pazsalvo.cargos_id() and not es_responsable_dir:
                                # Nota: El punto al final es esencial para el funcionamiento de la firma masiva, es el diferenciador ubicado en el html del certificado.
                                palabras = f'{titulo_nombres}.'
                                x, y, numPage = obtener_posicion_x_y_saltolinea(archivo_.url, palabras, False)
                                if x and y:
                                    # x = x + 98
                                    x = 465
                                    y = y - 20
                                    firmas.append({'x': x, 'y': y, 'numPage': numPage})
                            for membrete in firmas:
                                datau = JavaFirmaEc(
                                    archivo_a_firmar=archivo_, archivo_certificado=bytes_certificado, extension_certificado=extension_certificado,
                                    password_certificado=contrasenaCertificado,
                                    page=int(membrete["numPage"]), reason=razon, lx=membrete["x"], ly=membrete["y"]
                                ).sign_and_get_content_bytes()
                                archivo_ = io.BytesIO()
                                archivo_.write(datau)
                                archivo_.seek(0)

                            _name = f"certificado_{certificado_firma.pazsalvo.persona.usuario}"
                            file_obj = DjangoFile(archivo_, name=f"{_name}.pdf")

                            certificado_firma.archivo = file_obj
                            certificado_firma.save(request)
                            historial = HistorialCertificadoFirmaPS(certificadosalida=certificado_firma,
                                                                    archivo=file_obj,
                                                                    persona=persona,
                                                                    cargo=responsable.get_cargo(),
                                                                    cantidadfirmas=len(firmas),
                                                                    estado=2)
                            historial.save(request)

                            r_firma = certificado_firma.responsable_firma(persona)
                            if r_firma:
                                r_firma.firmado = r_firma.total_firmado() >= r_firma.cantidadfirmas
                                r_firma.save(request)
                                log(u'Edito Responsable firma: {}'.format(r_firma), request, "edit")

                            if certificado_firma.firmado_all():
                                pazsalvo = certificado_firma.pazsalvo
                                pazsalvo.estado = 3
                                pazsalvo.save(request)

                                titulo = 'Certificado de paz y salvo firmado por responsables exitosamente.'
                                observacion = f'Estimado/a {pazsalvo.persona.nombre_completo_minus()} su certificado de paz y salvo fue firmado por todos los responsables a cargo,' \
                                              f'por favor revise su certificado y proceda a firmarlo.'
                                notificacion(titulo, observacion, pazsalvo.persona, None, '/th_hojavida?action=pazsalvo', pazsalvo.pk, 2, 'sagest', PazSalvo, request)
                                log(u'Edito paz y salvo: {}'.format(pazsalvo), request, "edit")
                        except Exception as ex:
                            if f'{ex}' == 'Certificado no es válido' or f'{ex}' == 'Invalid password or PKCS12 data':
                                raise NameError(f'{ex}')
                    return JsonResponse({"result": False, "mensaje": "Guardado con exito", }, safe=False)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % ex})

            elif action == 'firmarpazsalvo':
                try:
                    certificado = request.FILES["firma"]
                    contrasenaCertificado = request.POST['palabraclave']
                    razon = request.POST['razon'] if 'razon' in request.POST else ''
                    extension_certificado = os.path.splitext(certificado.name)[1][1:]
                    bytes_certificado = certificado.read()
                    pazsalvo = PazSalvo.objects.get(id=encrypt_id(request.POST['id']))
                    firmas = []
                    certificado_firma=pazsalvo.documento()
                    archivo_ = certificado_firma.archivo
                    registro = persona.titulacion_principal_senescyt_registro()
                    titulo_nombres = f'{persona}'
                    responsable = pazsalvo.get_responsable_firmar(persona)
                    if registro and registro.titulo:
                        titulo = registro.titulo.abreviatura
                        titulo_nombres = f'{titulo} {persona}'.strip()
                    es_responsable_dir = pazsalvo.es_responsable_direccion(persona.mi_cargo_administrativo().id)
                    if pazsalvo.es_jefe(persona):
                        palabras = f'{titulo_nombres} FIRMA DE JEFE INMEDIATO'
                        x, y, numPage = obtener_posicion_x_y_saltolinea(archivo_.url, palabras, False)
                        if x and y:
                            x = x + 53
                            y = y + 10
                            firmas.append({'x': x, 'y': y, 'numPage': numPage})
                    if es_responsable_dir:
                        cargo = f'RESPONSABLE DE LA {pazsalvo.direccion_persona(persona).departamento.nombre}'
                        palabras = f'{titulo_nombres} {cargo}'
                        x, y, numPage = obtener_posicion_x_y_saltolinea(archivo_.url, palabras, False)
                        if x and y:
                            x = x + len(palabras) + 8
                            y = y + 10
                            firmas.append({'x': x, 'y': y, 'numPage': numPage})
                    if responsable and responsable.get_cargo().id in pazsalvo.cargos_id() and not es_responsable_dir:
                        # Nota: El punto al final es esencial para el funcionamiento de la firma masiva, es el diferenciador ubicado en el html del certificado.
                        palabras = f'{titulo_nombres}.'
                        x, y, numPage = obtener_posicion_x_y_saltolinea(archivo_.url, palabras, False)
                        if x and y:
                            # x = x + 98 if x > 360 else 465
                            x = 465
                            y = y - 20
                            firmas.append({'x': x, 'y': y, 'numPage': numPage})

                    if not firmas:
                        raise NameError('No se encontraron coincidencias con su usuario')
                    for membrete in firmas:
                        datau = JavaFirmaEc(
                            archivo_a_firmar=archivo_, archivo_certificado=bytes_certificado, extension_certificado=extension_certificado,
                            password_certificado=contrasenaCertificado,
                            page=int(membrete["numPage"]), reason=razon, lx=membrete["x"], ly=membrete["y"]
                        ).sign_and_get_content_bytes()
                        archivo_ = io.BytesIO()
                        archivo_.write(datau)
                        archivo_.seek(0)

                    _name = f"certificado_{certificado_firma.pazsalvo.persona.usuario}"
                    file_obj = DjangoFile(archivo_, name=f"{_name}.pdf")

                    certificado_firma.archivo = file_obj
                    certificado_firma.save(request)
                    historial = HistorialCertificadoFirmaPS(certificadosalida=certificado_firma,
                                                            archivo=file_obj,
                                                            persona=persona,
                                                            cargo=responsable.get_cargo(),
                                                            cantidadfirmas=len(firmas),
                                                            estado=2)
                    historial.save(request)

                    r_firma = certificado_firma.responsable_firma(persona)
                    if r_firma:
                        r_firma.firmado = r_firma.total_firmado() >= r_firma.cantidadfirmas
                        r_firma.save(request)
                        log(u'Edito Responsable firma: {}'.format(r_firma), request, "edit")

                    if certificado_firma.firmado_all():
                        pazsalvo = certificado_firma.pazsalvo
                        pazsalvo.estado = 3
                        pazsalvo.save(request)
                        log(u'Edito paz y salvo: {}'.format(pazsalvo), request, "edit")
                        notificar_solicitante(request, pazsalvo)
                    return JsonResponse({"result": False, "mensaje": "Guardado con exito", }, safe=False)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % ex})

            elif action == 'revertirestado':
                with transaction.atomic():
                    try:
                        pazsalvo = PazSalvo.objects.get(pk=encrypt_id(request.POST['id']))
                        pazsalvo.estado = 1
                        pazsalvo.save(request)
                        url_certificado = generar_certificado(request, pazsalvo)
                        certificado = pazsalvo.documento()
                        certificado.archivo = url_certificado
                        certificado.save(request)
                        crear_responsables_firma(request, certificado)
                        log(u'Edito certificado de paz y salvo: %s' % pazsalvo, request, "edit")
                        res_json = {"result": 'ok'}
                    except Exception as ex:
                        res_json = {'result': False, "mensaje": "Error: {}".format(ex)}
                    return JsonResponse(res_json, safe=False)

            elif action == 'notificarcumplimiento':
                try:
                    pazsalvo = PazSalvo.objects.get(id=encrypt_id(request.POST['id']))
                    if pazsalvo.respondio_all() and pazsalvo.estado == 2:
                        certificado = pazsalvo.documento()
                        notificar_firma_responsables(request, certificado)
                        mensaje = 'legalización a responsables'
                    elif pazsalvo.estado == 3:
                        notificar_solicitante(request, pazsalvo)
                        mensaje = 'legalización a solicitante'
                    else:
                        notificar_llenado_solicitud(request, pazsalvo)
                        mensaje = 'llenado a responsables'
                    messages.success(request, f'Notificación de insistencia de {mensaje} enviada.')
                    return JsonResponse({"result": 'ok', 'mensaje': 'Notificación realizada con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": 'bad', 'mensaje': f'Error: {ex}'})

            elif action == 'cambiarobligatorio':
                with transaction.atomic():
                    try:
                        registro = DetalleDireccionFormatoPS.objects.get(pk=encrypt_id(request.POST['id']))
                        registro.obligatorio = eval(request.POST['val'].capitalize())
                        registro.save(request)
                        log(u'Cambio pregunta obligatoria : %s (%s)' % (registro, registro.obligatorio), request, "edit")
                        return JsonResponse({"result": True, 'mensaje': 'Cambios guardados'})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": False})

            elif action == 'addrequisito':
                try:
                    form = RequisitoPazSalvoForm(request.POST, request.FILES)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    requisito = RequisitoPazSalvo(nombre=form.cleaned_data['nombre'],
                                                  descripcion=form.cleaned_data['descripcion'],
                                                  link=form.cleaned_data['link'],
                                                  mostrar=form.cleaned_data['mostrar'],
                                                  opcional=form.cleaned_data['opcional'],
                                                  archivo=form.cleaned_data['archivo']
                                                  )
                    requisito.save(request)
                    log(f'Agrego requisito de paz y salvo: {requisito}', request, 'add')
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, 'mensaje': str(ex)})

            elif action == 'editrequisito':
                try:
                    instancia = RequisitoPazSalvo.objects.get(id=encrypt_id(request.POST['id']))
                    form = RequisitoPazSalvoForm(request.POST, request.FILES, instancia=instancia)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    instancia.nombre = form.cleaned_data['nombre']
                    instancia.descripcion = form.cleaned_data['descripcion']
                    instancia.link = form.cleaned_data['link']
                    instancia.mostrar = form.cleaned_data['mostrar']
                    instancia.opcional = form.cleaned_data['opcional']
                    instancia.archivo = form.cleaned_data['archivo']
                    instancia.save(request)
                    log(f'Edito formato de paz y salvo: {formato}', request, 'edit')
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, 'mensaje': str(ex)})

            elif action == 'reporteps':
                try:
                    form = FechaInicioFinForm(request.POST)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    fechainicio = form.cleaned_data['fechainicio']
                    fechafin = form.cleaned_data['fechafin']
                    instancias = PazSalvo.objects.filter(status=True, fecha__range=(fechainicio,fechafin))
                    __author__ = 'Unemi'
                    filename = 'reporte_paz_salvo.xlsx'
                    directory = os.path.join(MEDIA_ROOT, 'talento_humano', filename)
                    # output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(directory, {'constant_memory': True})
                    ws = workbook.add_worksheet('paz_salvo')
                    formatosubtitulocolumna = workbook.add_format(
                        {'align': 'left', 'valign': 'vcenter', 'bold': 1, 'font_size': 12,
                         'text_wrap': True, 'fg_color': '#ECF6FF', 'font_color': 'black'})

                    ws.set_column(0, 10, 40)
                    #Titulos
                    fila = 1
                    ws.write('A'+str(fila), 'Identificación', formatosubtitulocolumna)
                    ws.write('B'+str(fila), 'Servidor', formatosubtitulocolumna)
                    ws.write('C'+str(fila), 'Puesto', formatosubtitulocolumna)
                    ws.write('D'+str(fila), 'Unidad', formatosubtitulocolumna)
                    ws.write('E'+str(fila), 'Motivo de salida', formatosubtitulocolumna)
                    ws.write('F'+str(fila), 'Tipo de relación', formatosubtitulocolumna)
                    ws.write('G'+str(fila), 'Fecha de salida', formatosubtitulocolumna)
                    ws.write('H'+str(fila), 'Fecha de registro', formatosubtitulocolumna)
                    ws.write('I'+str(fila), 'Jefe inmediato', formatosubtitulocolumna)
                    ws.write('J'+str(fila), 'RMU', formatosubtitulocolumna)
                    ws.write('K'+str(fila), 'Estado', formatosubtitulocolumna)
                    ws.write('L'+str(fila), 'Código puesto', formatosubtitulocolumna)
                    fila +=1
                    for instancia in instancias:
                        ws.write('A'+ str(fila), str(instancia.persona.identificacion()))
                        ws.write('B'+ str(fila), str(instancia.persona.nombre_completo_minus()))
                        ws.write('C'+ str(fila), str(instancia.cargo))
                        ws.write('D'+ str(fila), str(instancia.departamento))
                        ws.write('E'+ str(fila), str(instancia.get_motivosalida_display()))
                        ws.write('F'+ str(fila), str(instancia.get_tiporelacion_display()))
                        ws.write('G'+ str(fila), str(instancia.fecha))
                        ws.write('H'+ str(fila), str(instancia.fecha_creacion.date()))
                        ws.write('I'+ str(fila), str(instancia.jefeinmediato.nombre_completo_minus()))
                        ws.write('J'+ str(fila), str(instancia.ultimaremuneracion))
                        ws.write('K'+ str(fila), str(instancia.get_estado_display()))
                        ws.write('L'+ str(fila), str(instancia.cargo.id))
                        fila+=1
                    workbook.close()
                    ruta = 'media/talento_humano/'+filename
                    return JsonResponse({'to': ruta})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, 'mensaje': str(ex)})

            elif action == 'reporterequisito':
                try:
                    form = FechaInicioFinForm(request.POST)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    fechainicio = form.cleaned_data['fechainicio']
                    fechafin = form.cleaned_data['fechafin']
                    requisitos = RequisitoPazSalvo.objects.filter(status=True).order_by('nombre')
                    instancias = PazSalvo.objects.filter(status=True, fecha__range=(fechainicio,fechafin))
                    __author__ = 'Unemi'
                    filename = 'reporte_requisito_paz_salvo.xlsx'
                    directory = os.path.join(MEDIA_ROOT, 'talento_humano', filename)
                    # output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(directory, {'constant_memory': True})
                    ws = workbook.add_worksheet('requisitos')
                    formatosubtitulocolumna = workbook.add_format(
                        {'align': 'left', 'valign': 'vcenter', 'bold': 1, 'font_size': 12,
                         'text_wrap': True, 'fg_color': '#ECF6FF', 'font_color': 'black'})

                    ws.set_column(0, 10, 40)
                    fila = 0
                    ws.write(0,0, 'Identificación', formatosubtitulocolumna)
                    ws.write(0,1, 'Servidor', formatosubtitulocolumna)
                    ws.write(0,2, 'Puesto', formatosubtitulocolumna)
                    ws.write(0,3, 'Unidad', formatosubtitulocolumna)
                    ws.write(0,4, 'Fecha de salida', formatosubtitulocolumna)
                    columna =5
                    fila=0
                    for requisito in requisitos:
                        ws.write(fila,columna, str(requisito), formatosubtitulocolumna)
                        columna+=1
                    fila +=1
                    for instancia in instancias:
                        ws.write(fila,0 , str(instancia.persona.identificacion()))
                        ws.write(fila,1, str(instancia.persona.nombre_completo_minus()))
                        ws.write(fila,2, str(instancia.cargo))
                        ws.write(fila,3, str(instancia.departamento))
                        ws.write(fila,4, str(instancia.fecha))
                        columna = 5
                        for requisito in requisitos:
                            estadoreq = 'Sin registro'
                            req = instancia.documentopazsalvo_set.filter(status=True,requisito=requisito).first()
                            if req:
                                if req.archivo:
                                    estadoreq = str(req.get_estados_display())
                            ws.write(fila, columna,estadoreq)
                            columna += 1
                        fila+=1
                    workbook.close()
                    ruta = 'media/talento_humano/'+filename
                    return JsonResponse({'to': ruta})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, 'mensaje': str(ex)})

            elif action == 'cambiarestado':
                try:
                    tipo = request.POST.get('args', '')
                    requisito = RequisitoPazSalvo.objects.get(id=encrypt_id(request.POST['id']))
                    if tipo == 'mostrar':
                        requisito.mostrar = eval(request.POST['val'].capitalize())
                        requisito.save(request)
                    elif tipo == 'opcional':
                        requisito.opcional = eval(request.POST['val'].capitalize())
                        requisito.save(request)
                    log(f'Edito requisito: {requisito}', request, 'edit')
                    return JsonResponse({'result': True, 'mensaje': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': False, 'mensaje': str(ex)})

            elif action == 'delrequisito':
                try:
                    requisito = RequisitoPazSalvo.objects.get(id=encrypt_id(request.POST['id']))
                    requisito.status = False
                    requisito.save(request)
                    log(f'Elimino formato de paz y salvo: {requisito}', request, 'del')
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            elif action == 'validar':
                with transaction.atomic():
                    try:
                        instance = DocumentoPazSalvo.objects.get(pk=int(request.POST['id']))
                        form = ValidarRequisitoForm(request.POST)
                        if not form.is_valid():
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "mensaje": "Error en el formulario"})
                        instance.estados = int(form.cleaned_data['estado'])
                        instance.observacion = form.cleaned_data['observacion']
                        instance.f_validacion = hoy
                        instance.save(request)
                        pazsalvo = instance.pazsalvo
                        documentos = DocumentoPazSalvo.objects.filter(pazsalvo=pazsalvo, status=True).exclude(id=instance.id)
                        mensaje = ''
                        if instance.estados == 1 and pazsalvo.doc_validacion() == 1 and pazsalvo.estado_requisito != 1:
                            pazsalvo.estado_requisito = 1
                            pazsalvo.save(request)
                            mensaje = f'Los documentos subidos fueron aprobados en paz y salvo de {pazsalvo.cargo}'
                        elif pazsalvo.doc_validacion() == 0 and pazsalvo.estado_requisito != 0:
                            pazsalvo.estado_requisito = 0
                            pazsalvo.save(request)
                        elif instance.estados == 2:
                            pazsalvo.estado_requisito = 2
                            pazsalvo.save(request)
                            mensaje = f'Documento {instance} pendiente de corregir.'
                        elif instance.estados == 4:
                            mensaje = f'Documento {instance} fue rechazado.'

                        if instance.estados == 1 and pazsalvo.doc_validacion() == 1 or instance.estados != 1:
                            titulo = u"Validación de documentos cargados en paz y salvo de {} - ({})".format(pazsalvo, instance.get_estados_display())
                            notificacion(titulo,
                                         mensaje, pazsalvo.persona, None, f'/th_hojavida?action=pazsalvo',
                                         instance.pk, 1, 'sga-sagest', DocumentoPazSalvo, request)

                        diccionario = {'id': instance.id, 'observacion': instance.observacion, 'estado': instance.get_estados_display(), 'idestado': instance.estados, 'color': instance.color_estado()}
                        log(u'Valido documento de paz y salvo: %s' % instance, request, "edit")
                        return JsonResponse({'result': True, 'data_return': True, 'mensaje': u'Guardado con exito', 'data': diccionario}, safe=False)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Intentelo más tarde.".format(str(ex))}, safe=False)

            elif action == 'resetearrespuestas':
                with transaction.atomic():
                    try:
                        instancia = PazSalvo.objects.get(pk=int(encrypt(request.POST['id'])))
                        instancia.estado = 1
                        instancia.save(request)
                        instancia.respuestas_all().update(status=False)
                        instancia.responsables().update(status=False)
                        log(u'Elimino respuestas de paz y salvo: %s' % instancia, request, "del")
                        res_json = {"result": 'ok', "mensaje": 'Registro eliminado'}
                    except Exception as ex:
                        res_json = {'error': True, "mensaje": "Error: {}".format(ex)}
                    return JsonResponse(res_json, safe=False)

            elif action == 'notificacionmasiva':
                try:
                    titulo = 'Certificados de Paz y Salvo pendientes de completar items y legalizar'
                    cabecera = f'Se requiere completar los items de varios certificados de paz y salvo que se encuentran a su nombre. Por favor, proceda a gestionar según sea necesario.'
                    template = "th_pazsalvo/emails/notificacion_pazsalvo.html"
                    datos_email = {'sistema': request.session['nombresistema'],
                                   'fecha': datetime.now(),
                                   'titulo': titulo,
                                   'cabecera':cabecera,
                                   'persona': '',
                                   'mensaje': '',
                                   'url': f'https://sga.unemi.edu.ec/th_pazsalvo'}
                    # lista_email = ['jguachuns@unemi.edu.ec', ]
                    jefes_id = formato.jefes_inmediatos()
                    t_jefes_notify, t_responsables_dp, t_directores, t_solicitantes = 0, 0, 0, 0
                    for id_jefe in jefes_id:
                        per = Persona.objects.get(id=id_jefe)
                        por_llenar = formato.certificados_por_llenar_jefe(id_jefe)
                        por_firmar = formato.certificados_por_firmar(id_jefe)
                        if por_llenar > 0 or por_firmar > 0:
                            datos_email['persona'] = per
                            datos_email['por_llenar'] = por_llenar if por_llenar > 0 else ''
                            datos_email['por_firmar'] = por_firmar if por_firmar > 0 else ''
                            lista_email = per.lista_emails()
                            send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])
                            t_jefes_notify += 1
                    for distributivo in formato.responsables_dp():
                        por_llenar = formato.certificados_por_llenar(distributivo)
                        por_firmar = formato.certificados_por_firmar(distributivo.persona.id)
                        if por_llenar > 0 or por_firmar > 0:
                            datos_email['persona'] = distributivo.persona
                            datos_email['por_llenar'] = por_llenar if por_llenar > 0 else ''
                            datos_email['por_firmar'] = por_firmar if por_firmar > 0 else ''
                            lista_email = distributivo.persona.lista_emails()
                            send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])
                            t_responsables_dp += 1
                    for id_director in formato.responsables_direccion():
                        por_firmar = formato.certificados_por_firmar(id_director)
                        if por_firmar > 0:
                            director = Persona.objects.get(id=id_director)
                            datos_email['persona'] = director
                            datos_email['por_llenar'] = None
                            datos_email['por_firmar'] = por_firmar if por_firmar > 0 else ''
                            lista_email = director.lista_emails()
                            send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])
                            t_directores += 1
                    pazsalvos = PazSalvo.objects.filter(status=True, estado=3)
                    for ps in pazsalvos:
                        notificar_solicitante(request, ps)
                        t_solicitantes += 1
                    mensaje = f'Se notifico a {t_jefes_notify} jefes inmediatos, {t_responsables_dp} responsables, {t_directores} directores y {t_solicitantes} solicitantes'
                    return JsonResponse({"result": 'ok', 'showSwal': True, 'Titulo': 'Notificación de insistencia realizada con éxito', 'mensaje': mensaje})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": 'bad', 'mensaje': f'Error: {ex}'})

            elif action == 'descargarcomprimidomasivo':
                with transaction.atomic():
                    try:
                        inicio, fin, estado, filtro, estado_pazsalvo = request.POST.get('fechainicio', ''), \
                                                      request.POST.get('fechafin', ''), \
                                                      request.POST.get('estado', ''), Q(status=True), request.POST.get('estado_pazsalvo','')
                        if inicio:
                            filtro = filtro & Q(fecha__gte=inicio)
                        if fin:
                            filtro = filtro & Q(fecha__lte=fin)
                        if estado:
                            filtro = filtro & Q(estado_requisito=int(estado))
                        if estado_pazsalvo:
                            filtro = filtro & Q(estado=int(estado_pazsalvo))
                        data['pazsalvos'] = pazsalvos = PazSalvo.objects.filter(filtro).exclude(documentopazsalvo__isnull=True)
                        if not pazsalvos:
                            raise NameError('No existen registros con la configuración de descarga ingresada')
                        titulo = f'Generación de archivo .zip de documentos de requisitos de paz y salvo'
                        noti = Notificacion(cuerpo='Se inicializo la compresión de documentos de requisitos de paz y salvos cargados al sistema',
                                            titulo=titulo, destinatario=persona,
                                            url='',
                                            prioridad=1, app_label='SGA-SAGEST',
                                            fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                            en_proceso=True)
                        noti.save(request)
                        descarga_masiva_requisitos_pazsalvo_background(request=request, data=data, notif=noti.pk).start()
                        return JsonResponse({"result": False, "mensaje": u"Generando archivo .zip"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": f"{ex}"})

            elif action == 'addobservacion':
                try:
                    form = ObservacionPazSalvoForm(request.POST, request.FILES)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    obs = ObservacionPazSalvo(persona=persona,
                                            pazsalvo_id=encrypt_id(request.POST['idp']),
                                            observacion=form.cleaned_data['observacion'])
                    obs.save(request)
                    log(f'Agrego requisito de paz y salvo: {obs}', request, 'add')
                    context = {'id': obs.id,
                               'foto': persona.get_foto(),
                               'nombres': persona.nombre_completo_minus(),
                               'observacion': obs.observacion,
                               'fecha_creacion': obs.fecha_creacion.strftime('%d-%m-%Y | %H:%M:%S')}
                    return JsonResponse({'result': 'ok', 'data_return': True, 'data': context, 'mensaje': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, 'mensaje': str(ex)})

            elif action == 'editobservacion':
                try:
                    id=encrypt_id(request.POST['id'])
                    obs=ObservacionPazSalvo.objects.get(id=id)
                    form = ObservacionPazSalvoForm(request.POST, request.FILES)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    obs.persona=persona
                    obs.observacion=form.cleaned_data['observacion']
                    obs.save(request)
                    log(f'Edito observacion de paz y salvo: {obs}', request, 'edit')
                    context={'id':obs.id,'foto':persona.get_foto(),'observacion':obs.observacion,'fecha_creacion':obs.fecha_creacion.strftime('%d-%m-%Y %H:%M:%S')}
                    return JsonResponse({'result': False,'data_return':context, 'mensaje': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, 'mensaje': str(ex)})

            elif action == 'delobservacion':
                with transaction.atomic():
                    try:
                        instancia = ObservacionPazSalvo.objects.get(pk=encrypt_id(request.POST['id']))
                        instancia.status = False
                        instancia.save(request)
                        log(u'Elimino pregunta de dirección: %s' % instancia, request, "del")
                        res_json = {"error": False, "refresh": instancia.id, "mensaje": 'Registro eliminado'}
                    except Exception as ex:
                        res_json = {'error': True, "message": "Error: {}".format(ex)}
                    return JsonResponse(res_json, safe=False)

            if action == 'importarremitidospago':
                try:
                    list_errors = []
                    cont_actualizados = 0
                    form = MatrizTramitePazySalvoForm(request.POST, request.FILES)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                    archivo = request.FILES['archivo']
                    df = pd.read_excel(archivo)
                    if not 'CEDULA' in df.columns:
                        raise NameError('Formato de archivo erróneo, columna CEDULA faltante.')

                    if not 'CODIGO PUESTO' in df.columns:
                        raise NameError('Formato de archivo erróneo, columna CODIGO PUESTO faltante.')

                    if not 'FECHA SALIDA' in df.columns:
                        raise NameError('Formato de archivo erróneo, columna FECHA SALIDA faltante.')

                    for index, row in df.iterrows():
                        cedula = str(int(row['CEDULA'])).strip()
                        cedula = cedula if len(cedula) == 10 else f'0{cedula}'
                        codigo_puesto = str(row.get('CODIGO PUESTO', '')).strip()
                        fecha = str(row.get('FECHA SALIDA', '')).strip()

                        if not fecha:
                            list_errors.append({'fecha': fecha, 'error': 'Fecha no ingresada'})
                            continue

                        if not codigo_puesto:
                            list_errors.append({'cedula': cedula, 'error': 'No se ingresó código de puesto'})
                            continue

                        try:
                            codigo_puesto = int(float(codigo_puesto))
                        except ValueError:
                            list_errors.append({'cedula': cedula, 'error': 'Código de puesto no es un número válido'})
                            continue

                        puesto = DenominacionPuesto.objects.filter(id=int(codigo_puesto), status=True).first()
                        if not puesto:
                            list_errors.append({'cedula': cedula, 'error': 'Código de puesto no encontrado'})
                            continue

                        pers = Persona.objects.filter(cedula=cedula).first()
                        if not pers:
                            list_errors.append({'cedula': cedula, 'error': 'Cédula no encontrada'})
                            continue

                        servidor = PazSalvo.objects.filter(status=True, persona=pers, cargo=puesto, fecha=fecha).first()
                        if not servidor:
                            list_errors.append({'cedula': cedula, 'error': 'Servidor no encontrado'})
                            continue

                        servidor.estado_tramite = 2
                        servidor.save(request)
                        cont_actualizados += 1
                        log(f'Edito servidor Paz y Salvo remitido de pago: {servidor}', request, 'edit')

                    if list_errors:
                        return JsonResponse({'result': True, 'data_return': True, 'mensaje': f'Actualizados: {cont_actualizados}, no actualizados: {list_errors.__len__()}', 'data': list_errors})

                    return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, 'mensaje': str(ex)})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addpazsalvo':
                try:
                    form = PazSalvoForm()
                    # ids_departamentos = DistributivoPersona.objects.filter(status=True).values_list('unidadorganica_id', flat=True).distinct()
                    form.fields['persona'].queryset = Persona.objects.none()
                    form.fields['jefeinmediato'].queryset = Persona.objects.none()
                    form.fields['cargo'].queryset = DenominacionPuesto.objects.none()
                    form.fields['departamento'].queryset = Departamento.objects.none()
                    data['form'] = form
                    template = get_template('th_pazsalvo/modal/formpazsalvo.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editpazsalvo':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    pazsalvo=PazSalvo.objects.get(id=id)
                    form = PazSalvoForm(model_to_dict(pazsalvo))
                    ids_departamentos = DistributivoPersona.objects.filter(status=True).values_list('unidadorganica_id', flat=True).distinct()
                    form.fields['persona'].queryset = Persona.objects.filter(id=pazsalvo.persona.id)
                    form.fields['jefeinmediato'].queryset = Persona.objects.filter(id=pazsalvo.jefeinmediato.id)
                    form.fields['cargo'].queryset = DenominacionPuesto.objects.filter(id=pazsalvo.cargo.id)
                    form.fields['departamento'].queryset = Departamento.objects.filter(id__in=ids_departamentos)
                    data['form'] = form
                    template = get_template('th_pazsalvo/modal/formpazsalvo.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'formatos':
                try:
                    data['title'] = u'Formatos de paz y salvo'
                    data['subtitle'] = u'Listado de formatos de paz y salvo'
                    iter, search, url_vars, filtro = False, request.GET.get('s', ''), f'&action={action}', Q(status=True)
                    if search:
                        data['s'] = search
                        filtro = filtro & Q(titulo__icontains=search)
                        url_vars += f'&s={search}'
                        iter = True
                    formatos = FormatoPazSalvo.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(formatos, 20)
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
                    data['iter'] = iter
                    data['url_vars'] = url_vars
                    data['listado'] = page.object_list
                    request.session['viewactivo'] = 2
                    return render(request, "th_pazsalvo/formatos_view.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'addformato':
                try:
                    form = FormatoPazSalvoForm()
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editformato':
                try:
                    instancia = FormatoPazSalvo.objects.get(id=int(encrypt(request.GET['id'])))
                    form = FormatoPazSalvoForm(initial=model_to_dict(instancia))
                    data['id'] = instancia.id
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'preguntasgenerales':
                try:
                    form = PreguntaGeneralFormatoPSForm()
                    data['idp'] = idp = int(encrypt(request.GET['idp']))
                    data['formato'] = FormatoPazSalvo.objects.get(id=idp)
                    data['filtro'] = DetalleDireccionFormatoPS.objects.filter(formato_id=idp, status=True).order_by('cargo_id')
                    data['form'] = form
                    data['action'] = 'addpreguntageneral'
                    template = get_template('th_pazsalvo/modal/formpreguntaformato.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'direcciones':
                try:
                    data['title'] = u'Direcciones de formato '
                    id = request.GET['formato']
                    formato = FormatoPazSalvo.objects.get(id=int(encrypt(id)))
                    iter, search, url_vars, filtro = False, request.GET.get('s', ''), f'&action={action}&id={id}', Q(status=True, formato=formato)
                    if search:
                        data['s'] = search
                        filtro = filtro & Q(departamento__nombre__icontains=search)
                        url_vars += f'&s={search}'
                        iter = True
                    formmatos = DireccionFormatoPS.objects.filter(filtro).order_by('orden')
                    paging = MiPaginador(formmatos, 20)
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
                    data['formato'] = formato
                    data['iter'] = iter
                    data['url_vars'] = url_vars
                    data['listado'] = page.object_list
                    request.session['viewactivo'] = 2
                    return render(request, "th_pazsalvo/direcciones_view.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'adddireccion':
                try:
                    form = DireccionFormatoPSForm()
                    ids_departamentos = DistributivoPersona.objects.filter(status=True).values_list('unidadorganica_id', flat=True).distinct()
                    form.fields['departamento'].queryset = Departamento.objects.filter(id__in=ids_departamentos, tipo=1)
                    data['idp'] = id = int(encrypt(request.GET['idp']))
                    form.cargar_orden_siguiente(id)
                    form.fields['idformato'].initial = id
                    data['form'] = form
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editdireccion':
                try:
                    instancia = DireccionFormatoPS.objects.get(id=int(encrypt(request.GET['id'])))
                    form = DireccionFormatoPSForm(initial=model_to_dict(instancia))
                    form.fields['idformato'].initial = instancia.formato.id
                    data['id'] = instancia.id
                    data['form'] = form
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'preguntasdireccion':
                try:
                    form = DetalleDireccionFormatoPSForm()

                    data['idp'] = idp = int(encrypt(request.GET['idp']))
                    direccion = DireccionFormatoPS.objects.get(id=idp)
                    ids_cargo = DistributivoPersona.objects.filter(status=True, unidadorganica=direccion.departamento).values_list('denominacionpuesto_id', flat=True).distinct()
                    form.fields['cargo'].queryset = DenominacionPuesto.objects.filter(id__in=ids_cargo)
                    data['filtro'] = DetalleDireccionFormatoPS.objects.filter(direccionformato_id=idp, status=True).order_by('cargo_id')
                    data['form'] = form
                    data['action'] = 'addpregunta'
                    template = get_template('th_pazsalvo/modal/formpreguntas.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'buscarpersonas':
                try:
                    resp = filtro_persona_select(request)
                    return HttpResponse(json.dumps({'status': True, 'results': resp}))
                except Exception as ex:
                    pass

            elif action == 'cargarcargos':
                try:
                    id = request.GET.get('id', '')
                    idp = request.GET.get('args', 0)
                    ids_p = DistributivoPersona.objects.filter(status=True, unidadorganica_id=id, persona_id=idp).values_list('denominacionpuesto_id', flat=True).distinct()
                    ids_ph = DistributivoPersonaHistorial.objects.filter(status=True, persona_id=idp, unidadorganica_id=id).values_list('denominacionpuesto_id', flat=True).distinct()
                    ids_cargo = list(ids_p) + list(ids_ph)
                    cargos = DenominacionPuesto.objects.filter(id__in=ids_cargo)
                    resp = [{'value': c.pk, 'text': f"{c.descripcion}"} for c in cargos]
                    return JsonResponse({'result': True, 'data': resp})
                except Exception as ex:
                    pass

            elif action == 'cargardirecciones':
                try:
                    id = request.GET.get('id', '')
                    ids_p = DistributivoPersona.objects.filter(status=True, persona_id=id).values_list('unidadorganica_id', flat=True).distinct()
                    ids_ph = DistributivoPersonaHistorial.objects.filter(status=True, persona_id=id).values_list('unidadorganica_id', flat=True).distinct()
                    ids_departamentos = list(ids_p) + list(ids_ph)
                    departamentos = Departamento.objects.filter(id__in=ids_departamentos)
                    resp = [{'value': c.pk, 'text': f"{c.nombre}"} for c in departamentos]
                    return JsonResponse({'result': True, 'data': resp})
                except Exception as ex:
                    pass

            elif action == 'cargarrmu':
                try:
                    idcargo = request.GET.get('value', '')
                    id = request.GET.get('args', 0)
                    cargo = DenominacionPuesto.objects.get(id=idcargo)
                    distributivo = DistributivoPersona.objects.filter(status=True, denominacionpuesto=cargo, persona_id=id).order_by('-fecha_creacion').first()
                    if not distributivo:
                        distributivo = DistributivoPersonaHistorial.objects.filter(status=True, denominacionpuesto=cargo, persona_id=id).order_by('-fechahistorial').first()
                    rmu = distributivo.rmupuesto if distributivo else 0
                    return JsonResponse({'result': True, 'rmu': rmu})
                except Exception as ex:
                    pass

            elif action == 'firmarcertificadomasivo':
                try:
                    idscertificado = ResponsableFirmaPS.objects.filter(status=True, persona=persona, certificado__pazsalvo__estado=2, certificado__pazsalvo__status=True, firmado=False).values_list('certificado_id', flat=True)
                    total = len(idscertificado)
                    if total == 0:
                        raise NameError('No dispone de certificados por firmar.')
                    data['info_mensaje'] = f'Nota: Tiene {total} certificados de paz y salvo pendientes de firmar.<br> ' \
                                           f'Se habilitó la opción de firma por lotes debido a la itermitencia de FIRMA EC'
                    data['extra_buttons'] = True
                    data['total']=total
                    template = get_template("formfirmaelectronicamasiva.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'{ex}'})

            elif action == 'responderpreguntas':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    data['pazsalvo'] = pazsalvo = PazSalvo.objects.get(id=id)
                    data['preguntas'] = preguntas =pazsalvo.preguntas(persona.mi_cargo_administrativo().id)
                    if persona.id == pazsalvo.jefeinmediato.id:
                        data['preguntas_jefe'] = pazsalvo.preguntas(persona.mi_cargo_administrativo().id, True, True)
                    for pregunta in preguntas:
                        if pregunta.logicamodelo:
                            pregunta_check = validar_pregunta(request, pregunta, pazsalvo)
                            respuesta = pregunta.respuesta(pazsalvo)
                            if not respuesta:
                                respuesta = DetallePazSalvo(persona=persona,
                                                          pazsalvo=pazsalvo,
                                                          pregunta=pregunta,
                                                          respondio=True,
                                                          marcado=pregunta_check)
                                respuesta.save(request)
                                log(u'Agrego respuesta a dirección: %s' % respuesta, request, "add")
                            else:
                                respuesta = DetallePazSalvo.objects.get(id=respuesta.id)
                                respuesta.marcado = pregunta_check
                                respuesta.persona = persona
                                respuesta.save(request)
                                log(u'Edito respuesta a dirección: %s' % respuesta, request, "edit")
                    template = get_template('th_pazsalvo/modal/formresponderpreguntas.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'respuestamasiva':
                try:
                    context = []
                    if not persona.mi_cargo_administrativo():
                        return JsonResponse({"result": False, 'mensaje': 'Su perfil no cuenta con un cargo asignado'})
                    if persona.id in formato.jefes_inmediatos():
                        data['preguntas_jefe'] = formato.preguntas_jefe()
                    pazsalvos = formato.pazsalvos().filter(estado=1)
                    for ps in pazsalvos:
                        es_jefe = persona.id == ps.jefeinmediato.id
                        preguntas = ps.preguntas(persona.mi_cargo_administrativo().id, es_jefe).exclude(logicamodelo='')
                        pregunta_check = True
                        for p in preguntas:
                            pregunta_check = validar_pregunta(request, p, ps)
                            if not pregunta_check:
                                break
                        if not ps.cumplimiento(cargo.id, es_jefe)['respondio'] and pregunta_check:
                            if es_jefe or cargo.id in ps.cargos_id():
                                diccionario = {'id': ps.id,
                                               'text': ps.persona.nombre_completo_inverso()}
                                context.append(diccionario)
                    data['pazsalvos'] = context
                    data['preguntas'] = formato.preguntas_cargo(persona.mi_cargo_administrativo().id)

                    template = get_template('th_pazsalvo/modal/formrespuestamasiva.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'buscarpazsalvo':
                try:
                    context = []
                    filtro = filtro_persona(request.GET['q'], Q(status=True, estado__in=[1, 2]))
                    pazsalvos = formato.pazsalvos().filter(filtro)
                    for ps in pazsalvos:
                        es_jefe = persona.id == ps.jefeinmediato.id
                        preguntas = ps.preguntas(persona.mi_cargo_administrativo().id, es_jefe).exclude(logicamodelo='')
                        pregunta_check = True
                        for p in preguntas:
                            pregunta_check = validar_pregunta(request, p, ps)
                            if not pregunta_check:
                                break
                        if ps.puede_editar() and ps.estado in [1, 2] and pregunta_check:
                            if es_jefe or cargo.id in ps.cargos_id():
                                diccionario = {'id': ps.pk, 'text': f"{ps.persona.nombre_completo_inverso()}",
                                               'documento': ps.persona.documento(),
                                               'departamento': ps.persona.departamentopersona() if not ps.persona.departamentopersona() == 'Ninguno' else '',
                                               'foto': ps.persona.get_foto()}
                                context.append(diccionario)
                    return HttpResponse(json.dumps({'status': True, 'results': context}))
                except Exception as ex:
                    pass

            elif action == 'firmarcertificado':
                try:
                    pazsalvo = PazSalvo.objects.get(id=encrypt_id(request.GET['id']))
                    certificado = pazsalvo.documento()
                    data['archivo_url'] = certificado.archivo.url
                    data['id'] = certificado.id
                    qr = qrImgFirma(request, persona, "png", paraMostrar=True)
                    data["qrBase64"] = qr[0]
                    template = get_template("formfirmaelectronica_v2.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')
                    return HttpResponseRedirect(request.path)

            elif action == 'firmarpazsalvo':
                try:
                    data['id'] = encrypt_id(request.GET['id'])
                    data['info_mensaje'] = f'Nota: Se firmaran todos los campos que se requieran firmar a su nombre en el certificado de paz y salvo'
                    template = get_template("formfirmaelectronicamasiva.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')
                    return HttpResponseRedirect(request.path)

            elif action == 'historialfirmas':
                try:
                    data['certificado'] = certificado = CertificadoFirmaPS.objects.get(id=encrypt_id(request.GET['id']))
                    data['historial'] = certificado.historial_firmas_all().order_by('-fecha_creacion')
                    template = get_template('th_pazsalvo/modal/historialfirmas.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'requisitos':
                try:
                    data['title'] = u'Requisitos'
                    data['subtitle'] = u'Listado de requisitos solicitados'
                    iter, search, url_vars, filtro = False, request.GET.get('s', ''), f'&action={action}', Q(status=True)
                    if search:
                        data['s'] = search
                        filtro = filtro & Q(nombre__unaccent__icontains=search)
                        url_vars += f'&s={search}'
                        iter = True
                    formatos = RequisitoPazSalvo.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(formatos, 10)
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
                    data['iter'] = iter
                    data['url_vars'] = url_vars
                    data['listado'] = page.object_list
                    return render(request, "th_pazsalvo/requisitos.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'addrequisito':
                try:
                    form = RequisitoPazSalvoForm()
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editrequisito':
                try:
                    instancia = RequisitoPazSalvo.objects.get(id=encrypt_id(request.GET['id']))
                    form = RequisitoPazSalvoForm(initial=model_to_dict(instancia))
                    data['id'] = instancia.id
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'validar':
                try:
                    form = ValidarRequisitoForm()
                    data['form'] = form
                    data['pazsalvo'] = PazSalvo.objects.get(pk=request.GET['id'])
                    template = get_template("th_pazsalvo/modal/formvalidar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'reporteps':
                try:
                    form = FechaInicioFinForm()
                    data['form'] = form
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'reporterequisito':
                try:
                    form = FechaInicioFinForm()
                    data['form'] = form
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'descargarcomprimido':
                with transaction.atomic():
                    try:
                        pazsalvo = PazSalvo.objects.get(id=encrypt_id(request.GET['id']))
                        return descargar_comprimido_requisitos(request, pazsalvo)
                    except Exception as ex:
                        messages.error(request, f"Error: {ex}")

            elif action == 'descargarcomprimidomasivo':
                with transaction.atomic():
                    try:
                        data['form']=ComprimidoForm()
                        template = get_template('th_pazsalvo/modal/formcomprimido.html')
                        return JsonResponse({'result':True, 'data':template.render(data)})
                    except Exception as ex:
                        return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

            elif action == 'observaciones':
                try:
                    data['idp'] = id = encrypt_id(request.GET['id'])
                    data['pazsalvo'] = PazSalvo.objects.get(id=id)
                    data['form'] = ObservacionPazSalvoForm()
                    data['action'] = 'addobservacion'
                    data['seccionado'] = True
                    template = get_template('th_pazsalvo/modal/formobservaciones.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'importarremitidospago':
                try:
                    form = MatrizTramitePazySalvoForm()
                    data['form'] = form
                    template = get_template('th_pazsalvo/modal/formimportarmatriz.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')


            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Paz y salvo'
                iter, search, url_vars, filtro, f_formato, estado = False, \
                                                            request.GET.get('s', ''), \
                                                            f'', Q(status=True), \
                                                            request.GET.get('f_formato', ''), request.GET.get('estado', '')
                tramite = request.GET.get('tramite', '')
                if search:
                    data['s'] = search
                    filtro = filtro_persona(search, filtro)
                    url_vars += f'&s={search}'
                    iter = True
                if f_formato:
                    data['f_formato'] = id_f = int(f_formato)
                    filtro = filtro & Q(formato_id=id_f)
                    url_vars += f'&f_formato={f_formato}'
                    iter = True
                if estado:
                    data['estado'] = estado = int(estado)
                    filtro = filtro & Q(estado=estado)
                    url_vars += f'&estado={estado}'
                    iter = True
                if tramite:
                    data['tramite'] = int(tramite)
                    filtro = filtro & Q(estado_tramite=tramite)
                    url_vars += f'&tramite={tramite}'
                    iter = True
                pazsalvos = PazSalvo.objects.filter(filtro).order_by('-id')
                paging = MiPaginador(pazsalvos, 10)
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
                data['iter'] = iter
                data['formatos'] = FormatoPazSalvo.objects.filter(status=True)
                data['url_vars'] = url_vars
                cargo = cargo if cargo else persona.mi_cargo()
                if cargo and formato:
                    es_jefe = persona.id in formato.jefes_inmediatos()
                    data['es_responsable'] = cargo.id in formato.cargos_preguntas() or es_jefe
                    # data['pendientes_llenar'] = formato.pendiente_llenar_persona(cargo, es_jefe)
                    data['pendientes_firmar'] = len(ResponsableFirmaPS.objects.filter(status=True, persona=persona, certificado__pazsalvo__estado=2, firmado=False).values_list('certificado_id'))
                pazsalvo_values = PazSalvo.objects.filter(status=True).values('id', 'estado', 'estado_tramite')
                data['total'] = len(pazsalvo_values)
                data['t_pendientes'] = len(pazsalvo_values.filter(estado=1))
                data['t_generados'] = len(pazsalvo_values.filter(estado=2))
                data['t_firmados'] = len(pazsalvo_values.filter(estado=3))
                data['t_finalizados'] = len(pazsalvo_values.filter(estado=4))
                data['tramite_pendiente'] = len(pazsalvo_values.filter(estado_tramite=1))
                data['tramite_remitido'] = len(pazsalvo_values.filter(estado_tramite=2))
                data['listado'] = page.object_list
                data['estados'] = ESTADO_PAZ_SALVO
                data['tramites'] = ESTADO_TRAMITE_PAGO_PAZ_SALVO
                request.session['viewactivo'] = 1
                return render(request, "th_pazsalvo/view.html", data)
            except Exception as ex:
                messages.error(request, f'{ex}')
            return HttpResponseRedirect(request.path)


def generar_certificado(request, pazsalvo):
    data = {}
    directory_p = os.path.join(MEDIA_ROOT, 'talento_humano')
    try:
        os.stat(directory_p)
    except:
        os.mkdir(directory_p)

    directory = os.path.join(MEDIA_ROOT, 'talento_humano', 'certificado_firma')
    nombre_archivo = generar_nombre(f'pazsalvo_{pazsalvo.id}_{pazsalvo.persona.usuario.username}', 'generado') + '.pdf'
    try:
        os.stat(directory)
    except:
        os.mkdir(directory)
    data['pazsalvo'] = pazsalvo
    context = {'pagesize': 'A4 landscape', 'data': data}
    valido = conviert_html_to_pdfsaveqr_generico(request,
                                                 'th_pazsalvo/certificadopdf.html',
                                                 context,
                                                 directory, nombre_archivo)
    if not valido[0]:
        raise NameError('Error al generar el informe')
    url_archivo = f'talento_humano/certificado_firma/{nombre_archivo}'
    return url_archivo

def crear_responsables_firma(request, certificado):
    try:
        pazsalvo = certificado.pazsalvo
        formato = pazsalvo.formato
        jefeinmediato = pazsalvo.jefeinmediato
        ResponsableFirmaPS.objects.filter(status=True, certificado=certificado).update(status=False)
        for d_pazsalvo in pazsalvo.respuestas_all().order_by('persona_id').distinct('persona_id'):
            cantidad = 0
            persona = d_pazsalvo.persona
            idcargo = persona.mi_cargo_administrativo().id
            if pazsalvo.preguntas(idcargo, False):
                cantidad += 1
            if persona.id == jefeinmediato.id and pazsalvo.preguntas(jefeinmediato.mi_cargo_administrativo().id, True):
                cantidad += 1
            responsable = ResponsableFirmaPS(certificado=certificado,
                                             persona=persona,
                                             cargo=persona.mi_cargo_administrativo() if persona.mi_cargo_administrativo() else None,
                                             cantidadfirmas=cantidad)
            responsable.save(request)
            log(f'Agrego responsable de firmar certificado: {responsable}', request, 'add')
        for direccion in formato.direcciones():
            persona = direccion.departamento.responsable
            cantidad = 1
            r_firma = ResponsableFirmaPS.objects.filter(status=True, persona=persona, certificado=certificado).first()
            if not pazsalvo.cargo_director_unico(direccion):
                if not r_firma:
                    r_firma = ResponsableFirmaPS(certificado=certificado,
                                                 persona=persona,
                                                 cargo=persona.mi_cargo_administrativo(),
                                                 cantidadfirmas=cantidad)
                    r_firma.save(request)
                    log(f'Agrego responsable de firmar certificado: {r_firma}', request, 'add')
                else:
                    r_firma.cantidadfirmas = cantidad + r_firma.cantidadfirmas
                    r_firma.save(request)
                    log(f'Edito responsable de firmar certificado: {r_firma}', request, 'edit')
    except Exception as ex:
        raise NameError(f'Error: {ex}')

def validar_pregunta(request, pregunta, pazsalvo):
    if not pregunta or not pazsalvo.persona:
        return False
    d = locals()
    exec(pregunta.logicamodelo, globals(), d)
    return d['verificar_pregunta'](pazsalvo)

def notificar_firma_responsables(request, certificado, correo=False):
    try:
        pazsalvo = certificado.pazsalvo
        cedula = pazsalvo.persona.cedula
        responsables = ResponsableFirmaPS.objects.filter(status=True, certificado=certificado)
        titulo = 'Pendiente de legalización: Certificado de Paz y Salvo.'
        template = "th_pazsalvo/emails/notificacion_pazsalvo.html"
        datos_email = {'sistema': request.session['nombresistema'],
                       'fecha': datetime.now(),
                       'titulo': titulo,
                       'cabecera': '',
                       'persona': '',
                       'url': f'https://sga.unemi.edu.ec/th_pazsalvo?&s={cedula}'}
        # lista_email = ['jguachuns@unemi.edu.ec', ]
        for d in responsables:
            if not d.firmado:
                sexo = 'o' if d.persona.sexo.id == 2 else 'a'
                saludo = f'Estimado{sexo} {d.persona.nombre_completo_minus()}'
                observacion = f'Existe un nuevo certificado de paz y salvo de {pazsalvo.persona.nombre_completo_minus()} que necesita ser legalizado por su parte.'
                notificacion(titulo, f'{saludo}, {observacion}', d.persona, None, f'/th_pazsalvo?s={cedula}', d.persona.pk, 2, 'sga-sagest', ResponsableFirmaPS, request)
                datos_email['persona'] = d.persona
                datos_email['cabecera'] = observacion
                lista_email = d.persona.lista_emails()
                if correo:
                    send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])
    except Exception as ex:
        raise NameError(f'Error {ex}')

def notificar_llenado_solicitud(request, pazsalvo):
    try:
        formato = pazsalvo.formato
        cedula = pazsalvo.persona.cedula
        cumplimiento = pazsalvo.cumplimiento(pazsalvo.jefeinmediato.mi_cargo_administrativo())
        titulo = 'Pendiente de completar: Certificado de Paz y Salvo.'
        template = "th_pazsalvo/emails/notificacion_pazsalvo.html"
        datos_email = {'sistema': request.session['nombresistema'],
                       'fecha': datetime.now(),
                       'titulo': titulo,
                       'cabecera': '',
                       'persona': '',
                       'url': f'https://sga.unemi.edu.ec/th_pazsalvo?&s={cedula}'}
        # lista_email = ['jguachuns@unemi.edu.ec', ]
        if not cumplimiento['respondio']:
            sexo = 'o' if pazsalvo.jefeinmediato.sexo.id == 2 else 'a'
            saludo = f'Estimado{sexo} {pazsalvo.jefeinmediato.nombre_completo_minus()}'
            observacion = f'Se ha emitido un nuevo certificado de paz y salvo de {pazsalvo.persona.nombre_completo_minus()} el cual requiere ser completado y legalizado por su parte.. Por favor, proceda a gestionar este documento según sea necesario.'
            notificacion(titulo, f'{saludo}, {observacion}', pazsalvo.jefeinmediato, None, f'/th_pazsalvo?s={pazsalvo.persona.cedula}', pazsalvo.pk, 2, 'sga-sagest', PazSalvo, request)
            datos_email['persona']=pazsalvo.jefeinmediato
            datos_email['cabecera']=observacion
            lista_email = pazsalvo.jefeinmediato.lista_emails()
            send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])

        for distributivo in formato.responsables_dp():
            if not distributivo.persona.id == pazsalvo.jefeinmediato.id:
                resp = distributivo.persona
                cumplimiento = pazsalvo.cumplimiento(resp.mi_cargo_administrativo())
                if not cumplimiento['respondio']:
                    sexo = 'o' if resp.sexo.id == 2 else 'a'
                    saludo = f'Estimad{sexo} {distributivo.persona.nombre_completo_minus()}'
                    cuerpo = f'Se ha emitido un nuevo certificado de paz y salvo de {pazsalvo.persona.nombre_completo_minus()} el cual requiere ser completado y legalizado por su parte. Por favor, proceda a gestionar este documento según sea necesario.'
                    notificacion(titulo, f'{saludo}, {cuerpo}', distributivo.persona,
                                 None, f'/th_pazsalvo?s={cedula}', distributivo.persona.pk, 2, 'sga-sagest',
                                 PazSalvo, request)
                    lista_email = distributivo.persona.persona.lista_emails()
                    datos_email['persona'] = distributivo.persona
                    datos_email['cabecera'] = cuerpo
                    send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])
    except Exception as ex:
        raise NameError(f'Error {ex}')

def notificar_solicitante(request, pazsalvo):
    titulo = 'Certificado de Paz y Salvo legalizado con éxito.'
    sexo = 'o' if pazsalvo.persona.sexo.id == 2 else 'a'
    saludo = f'Estimad{sexo} {pazsalvo.persona.nombre_completo_minus()}'
    observacion = f'Su certificado de paz y salvo ha sido legalizado por todas las partes responsables.' \
                  f'Le instamos a revisar el documento y proceder con la firma correspondiente.'
    notificacion(titulo, f'{saludo}, {observacion}', pazsalvo.persona, None, '/th_hojavida?action=pazsalvo', pazsalvo.pk, 2, 'sga-sagest', PazSalvo, request)
    template = "th_pazsalvo/emails/notificacion_pazsalvo.html"
    datos_email = {'sistema': request.session['nombresistema'],
                   'fecha': datetime.now(),
                   'titulo': titulo,
                   'cabecera': observacion,
                   'persona': pazsalvo.persona,
                   'url': f'https://sga.unemi.edu.ec/th_hojavida?action=pazsalvo'}
    lista_email = pazsalvo.persona.lista_emails()
    # lista_email = ['jguachuns@unemi.edu.ec', ]
    send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])

def descargar_comprimido_requisitos(request, pazsalvo):
    # Crear directorios recursivamente
    directory_p = os.path.join(MEDIA_ROOT, 'talento_humano')
    directory = os.path.join(directory_p, 'docs_comprimidos')
    os.makedirs(directory_p, exist_ok=True)
    os.makedirs(directory, exist_ok=True)
    name_folder = f'{unidecode(pazsalvo.persona.nombre_completo_minus())} (Requisitos de Paz y Salvo)'
    name_zip = f'{name_folder}.zip'
    url_zip = os.path.join(SITE_STORAGE, 'media', 'talento_humano', 'docs_comprimidos', name_zip)
    fantasy_zip = zipfile.ZipFile(url_zip, 'w')
    for idx, r in enumerate(pazsalvo.documentos_subidos()):
        url_file = r.archivo.url
        name_file = unidecode(r.requisito.nombre.replace(" ", "_"))
        ext = url_file[url_file.rfind("."):].lower()
        ruta_archivo_zip = os.path.join(name_folder, f'{name_file}{ext}')
        fantasy_zip.write(r.archivo.path, ruta_archivo_zip)
    fantasy_zip.close()
    response = HttpResponse(open(url_zip, 'rb'), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename={name_zip}'
    return response