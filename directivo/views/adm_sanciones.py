# -*- coding: UTF-8 -*-
#PYTHON
import sys
import json
from decorators import secure_module

#DJANGO
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.loader import get_template
from django.shortcuts import render, redirect
from django.db.models import Q
from django import forms

#OTROS
from unidecode import unidecode
from utils.filtros_genericos import filtro_persona, filtro_persona_principal

#SGA
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, log, variable_valor, MiPaginador, notificacion, validar_archivo
from sga.tasks import send_html_mail
from sga.models import Persona, CUENTAS_CORREOS
from sga.templatetags.sga_extras import encrypt

#SAGEST
from sagest.models import Departamento, Ubicacion, Bloque, MotivoAccionPersonal, BaseLegalAccionPersonal, \
    RegimenLaboral, MotivoAccionPersonalDetalle

from sagest.forms import MotivoAccionPersonalForm, BaseLegalAccionPersonalForm, MotivoAccionPersonalDetalleForm
from sagest.funciones import encrypt_id, departamentos_vigentes, get_departamento, filter_departamentos, slugs_rectorado_vicerrectorados, choice_indice, dominio_sistema_base
from core.choices.models.sagest import ESTADO_INCIDENCIA, ETAPA_INCIDENCIA,ROL_FIRMA_DOCUMENTO, ESTADO_SANCION_PERSONA, TIPO_DOCUMENTOS, ESTADO_APROBACION_ASISTENCIA, NOMBRE_FALTA_DISCIPLINARIA
from core.generic_forms import SignupForm
#DIRECTIVO
from directivo.models import (IncidenciaSancion, MotivoSancion,ResponsableFirma, AudienciaSancion, DocumentoEtapaIncidencia,
                              PersonaAudienciaSancion, DetalleAudienciaSancion, ResponsableEtapaIncidencia, RespuestaDescargo,
                              PersonaSancion, PuntoControl, EvidenciaPersonaSancion, RequisitoMotivoSancion, FaltaDisciplinaria,
                              RequisitoSancion, AnexoDocumentoIncidencia, ConsultaFirmaPersonaSancion, ReunionMediacion)
from directivo.forms import (IncidenciaSancionForm, ValidarCasoForm, GenerarDocumentoForm, AccionPersonalForm,
                             GenerarActaForm, ValidarPruebaForm, PlanificarAudienciaForm, FaltaDisciplinariaForm, MotivoSancionForm,
                             SubMotivoSancionForm, RequisitoSancionForm, RequisitoMotivoSancionForm, ResponsableFirmaForm, GenerarActaReunionForm)
from directivo.utils.funciones import (generar_codigo_incidencia, permisos_sanciones, notificacion_validacion_caso,
                                       notify_persona_sancion, notificar_personas_sancion,generar_documento_etapa, generar_acta_reunion,
                                       secciones_etapa_audiencia, secciones_etapa_analisis, generar_secuencia_doc_etapa_incidencia, generar_codigo_doc_etapa_incidencia,
                                       firmar_documento_etapa, resposables_firma_doc, obtener_tiempo_restante_seg)
from directivo.utils.actions_sanciones import (post_planificaraudiencia, post_remitir_descargo, get_planificaraudiencia, get_detalleaudiencia, get_generaracta,get_validar_audiencia, post_validar_audiencia,
                                               post_cambiarestado_audiencia, post_generar_accionpersonal,
                                               get_revisar_audiencia, get_generar_accionpersonal, post_generaracta, get_historialfirmas, notificar_audiencia_bloqueo)

from directivo.utils.strings import (Strings, get_text_campo_objeto, get_text_antecedentes_informe_echos,
                                     get_text_motivacion_tecnica_informe_echos, get_text_motivacion_tecnica_informe_sustanciacion,
                                     get_text_concluciones_informe_sustanciacion, get_text_campo_objeto_informe_sustanciacion)


@login_required(redirect_field_name='ret', login_url='/loginsagest')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['hoy'] = hoy = datetime.now()
    usuario = request.user
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    data['permisos'] = permisos = permisos_sanciones(persona)
    data['mi_departamento'] = mi_departamento = persona.mi_departamento()
    # if not mi_departamento and not permisos['revisor']:
    #     return HttpResponseRedirect('/?info=No tiene departamento asignado')

    if request.method == 'POST':
        action = request.POST['action']
        # SANCIONES
        if action == 'validarcaso':
            try:
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        raise NameError('El archivo debe pesar un maximo de 4mb.')
                    if not exte.lower() in ['pdf']:
                        raise NameError('Formato de archivo no admitido, solo se acepta pdf.')
                    arch._name = generar_nombre("incidencia_sancion", arch._name)
                idresponsable = encrypt_id(request.POST['idp'])
                personas_sancion = json.loads(request.POST['lista_items1'])
                form = ValidarCasoForm(request.POST)
                puede_guardar = False
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                incidencia = IncidenciaSancion.objects.get(pk=encrypt_id(form.cleaned_data['idincidencia']))
                incidencia.estado = int(form.cleaned_data['estado'])
                if not incidencia.motivo:
                    incidencia.motivo = form.cleaned_data['motivo']
                incidencia.archivo = arch if incidencia.estado == 4 else None
                incidencia.etapa = 2 if incidencia.estado == 3 else 1
                incidencia.save(request)
                for elemento in personas_sancion:
                    estado = int(elemento['estado'])
                    if not puede_guardar:
                        puede_guardar = estado == 1 or incidencia.estado == 4
                    persona_sancion = PersonaSancion.objects.get(id=elemento['id_personasancion'])
                    estado_anterior = persona_sancion.estado
                    persona_sancion.estado = estado if incidencia.estado != 4 else 2
                    # MOSTRAR POPUP DE NOTIFICACION
                    persona_sancion.notificacion = 1 if persona_sancion.estado == 1 else 0
                    persona_sancion.save(request)
                    # ENVIA NOTIFICACION CORREO Y SISTEMA
                    notificacion_validacion_caso(request, persona_sancion)
                    # if estado_anterior == 0:
                    #     if  persona_sancion.estado == 1:
                    #         notificacion_validacion_caso(request, persona_sancion)
                    # else:
                    #     if estado_anterior != persona_sancion.estado:
                    #         notificacion_validacion_caso(request, persona_sancion)

                if not puede_guardar:
                    raise NameError('Almenos una persona tiene que proceder para poder continuar')
                log(f'Valido caso de sanción: {incidencia}', request, 'edit')
                if idresponsable == 0:
                    responsable = ResponsableEtapaIncidencia(incidencia=incidencia,
                                                             persona=persona,
                                                             etapa=2, accion=1,
                                                             firma_doc=False, tipo_doc=1,
                                                             observacion=form.cleaned_data['observacion'])

                    responsable.save(request)
                    log(f'Guardo Responsable que valido la etapa: {responsable}', request, 'add')
                else:
                    responsable = ResponsableEtapaIncidencia.objects.get(pk=idresponsable)
                    responsable.persona = persona
                    responsable.observacion = form.cleaned_data['observacion']
                    responsable.save(request)
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, "mensaje": f"Error inesperado: {ex}"})

        elif action == 'generardocumento':
            try:
                lista_items1 = json.loads(request.POST['lista_items1'])
                documentos = request.FILES.getlist('adjuntos')
                for d in documentos:
                    items = [item for item in lista_items1 if item['archivo_anexo'] == d._name]
                    if len(items) > 1 and all(item['size'] == items[0]['size'] for item in items):
                        raise NameError(
                            f'Error, archivos duplicados {d._name}, remplace uno de los archivos duplicados.')

                    resp = validar_archivo(items[0]['archivo_anexo'], d, ['*'], '4MB')
                    if resp['estado'] != "OK":
                        raise NameError(f"{resp['mensaje']}.")

                id, tipo_doc = encrypt_id(request.POST['id']), request.POST['tipo_doc']
                documento, inicidencia = None, None
                if not tipo_doc:
                    documento = DocumentoEtapaIncidencia.objects.get(id=id)
                    tipo_doc = documento.tipo_doc
                else:
                    incidencia = IncidenciaSancion.objects.get(id=id)
                form = GenerarDocumentoForm(request.POST, instancia=documento)
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                if not documento:
                    tipo_doc = int(tipo_doc)
                    secuencia = generar_secuencia_doc_etapa_incidencia(tipo_doc)
                    codigo = generar_codigo_doc_etapa_incidencia(secuencia, persona, tipo_doc)
                    documento = DocumentoEtapaIncidencia(incidencia=incidencia,
                                                         tipo_doc = tipo_doc,
                                                         persona_elabora=persona,
                                                         persona_recepta=form.cleaned_data['persona_recepta'],
                                                         objeto=form.cleaned_data['objeto'],
                                                         antecedentes=form.cleaned_data['antecedentes'],
                                                         motivacion=form.cleaned_data['motivacion'],
                                                         conclusion=form.cleaned_data['conclusion'],
                                                         secuencia=secuencia,
                                                         codigo=codigo,
                                                         recomendacion=form.cleaned_data['recomendacion'])
                    documento.save(request)
                    log(f'Genero documento de etapa de sanción: {documento}', request, 'add')
                else:
                    documento.persona_elabora = persona
                    documento.persona_recepta = form.cleaned_data['persona_recepta']
                    documento.objeto = form.cleaned_data['objeto']
                    documento.antecedentes = form.cleaned_data['antecedentes']
                    documento.motivacion = form.cleaned_data['motivacion']
                    documento.conclusion = form.cleaned_data['conclusion']
                    documento.recomendacion = form.cleaned_data['recomendacion']
                    documento.save(request)
                    log(f'Edito documento de etapa de sanción: {documento}', request, 'edit')

                ids_excl = [int(item['id_anexo']) for item in lista_items1 if item['id_anexo']]
                for d in documentos:
                    items = [item for item in lista_items1 if item['archivo_anexo'] == d._name]
                    if not items[0]['id_anexo']:
                        d._name = generar_nombre(f"adjunto_{documento.id}_", d._name)
                        anexo = AnexoDocumentoIncidencia(documentoetapa=documento,
                                                        archivo=d,
                                                        nombre=items[0]['nombre_anexo'],
                                                        orden=items[0]['orden_anexo'],
                                                        fecha_generacion=items[0]['fecha_anexo'],
                                                        num_paginas=items[0]['paginas_anexo'],)
                        anexo.save(request)
                    else:
                        anexo = AnexoDocumentoIncidencia.objects.get(id=items[0]['id_anexo'])
                        anexo.nombre = items[0]['nombre_anexo']
                        anexo.orden = items[0]['orden_anexo']
                        anexo.fecha_generacion = items[0]['fecha_anexo']
                        anexo.num_paginas = items[0]['paginas_anexo']
                        anexo.archivo = d
                        anexo.save(request)
                    ids_excl.append(anexo.id)
                if not documentos and lista_items1:
                    for items in lista_items1:
                        if items['id_anexo']:
                            anexo = AnexoDocumentoIncidencia.objects.get(id=items['id_anexo'])
                            anexo.nombre = items['nombre_anexo']
                            anexo.orden = items['orden_anexo']
                            anexo.fecha_generacion = items['fecha_anexo']
                            anexo.num_paginas = items['paginas_anexo']
                            anexo.save(request)
                documento.get_anexos().exclude(id__in=ids_excl).update(status=False)
                generar_documento_etapa(documento, request)
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'generaractareunion':
            try:
                lista_items1 = json.loads(request.POST['lista_items1'])
                lista_anexos = obtener_lista(lista_items1, 'anexos')
                lista_convocados = obtener_lista(lista_items1, 'convocados')
                lista_planes = obtener_lista(lista_items1, 'planes')

                documentos = request.FILES.getlist('adjuntos')
                for d in documentos:
                    items = [item for item in lista_anexos if item['archivo_anexo'] == d._name]
                    if len(items) > 1 and all(item['size'] == items[0]['size'] for item in items):
                        raise NameError(
                            f'Error, archivos duplicados {d._name}, remplace uno de los archivos duplicados.')

                    resp = validar_archivo(items[0]['archivo_anexo'], d, ['*'], '4MB')
                    if resp['estado'] != "OK":
                        raise NameError(f"{resp['mensaje']}.")

                id, tipo_doc = encrypt_id(request.POST['id']), request.POST['tipo_doc']
                documento, inicidencia, reunion = None, None, None
                if not tipo_doc:
                    documento = DocumentoEtapaIncidencia.objects.get(id=id)
                    reunion = documento.reunion
                    tipo_doc = documento.tipo_doc
                else:
                    incidencia = IncidenciaSancion.objects.get(id=id)
                form = GenerarActaReunionForm(request.POST, instancia=documento)
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                if not reunion:
                    reunion = ReunionMediacion(incidencia=incidencia,
                                               conclusion=form.cleaned_data['conclusion'],
                                               desarrollo=form.cleaned_data['desarrollo'],
                                               convocador=form.cleaned_data['convocador'],
                                               organizador=form.cleaned_data['organizador'],
                                               apuntador=form.cleaned_data['apuntador'],
                                               tema=form.cleaned_data['tema'],
                                               fecha=form.cleaned_data['fecha'],
                                               horainicio=form.cleaned_data['horainicio'],
                                               horafin=form.cleaned_data['horafin'],
                                               bloque=form.cleaned_data['bloque'],
                                               ubicacion=form.cleaned_data['ubicacion'],
                                               referencia=form.cleaned_data['referencia'],)
                    reunion.save(request)
                    log(f'Genero acta de reunión: {reunion}', request, 'add')
                else:
                    reunion = ReunionMediacion.objects.get(id=reunion.id)
                    reunion.conclusion = form.cleaned_data['conclusion']
                    reunion.desarrollo = form.cleaned_data['desarrollo']
                    reunion.convocador = form.cleaned_data['convocador']
                    reunion.organizador = form.cleaned_data['organizador']
                    reunion.apuntador = form.cleaned_data['apuntador']
                    reunion.tema = form.cleaned_data['tema']
                    reunion.fecha = form.cleaned_data['fecha']
                    reunion.horainicio = form.cleaned_data['horainicio']
                    reunion.horafin = form.cleaned_data['horafin']
                    reunion.bloque = form.cleaned_data['bloque']
                    reunion.ubicacion = form.cleaned_data['ubicacion']
                    reunion.referencia = form.cleaned_data['referencia']
                    reunion.save(request)
                    log(f'Edito acta de reunión: {reunion}', request, 'edit')

                if not documento:
                    tipo_doc = int(tipo_doc)
                    secuencia = generar_secuencia_doc_etapa_incidencia(tipo_doc)
                    codigo = generar_codigo_doc_etapa_incidencia(secuencia, persona, tipo_doc)
                    documento = DocumentoEtapaIncidencia(incidencia=incidencia,
                                                         reunion=reunion,
                                                         tipo_doc = tipo_doc,
                                                         persona_elabora=persona,
                                                         secuencia=secuencia,
                                                         codigo=codigo,)
                    documento.save(request)
                    log(f'Genero acta de reunión: {documento}', request, 'add')
                else:
                    documento.persona_elabora = persona
                    documento.save(request)
                    log(f'Edito documento de etapa de sanción: {documento}', request, 'edit')

                ids_excl = [int(item['id_anexo']) for item in lista_anexos if item['id_anexo']]
                for d in documentos:
                    items = [item for item in lista_anexos if item['archivo_anexo'] == d._name]
                    if not items[0]['id_anexo']:
                        d._name = generar_nombre(f"adjunto_{documento.id}_", d._name)
                        anexo = AnexoDocumentoIncidencia(documentoetapa=documento,
                                                        archivo=d,
                                                        nombre=items[0]['nombre_anexo'],
                                                        orden=items[0]['orden_anexo'],
                                                        fecha_generacion=items[0]['fecha_anexo'],
                                                        num_paginas=items[0]['paginas_anexo'])
                        anexo.save(request)
                    else:
                        anexo = AnexoDocumentoIncidencia.objects.get(id=items[0]['id_anexo'])
                        anexo.nombre = items[0]['nombre_anexo']
                        anexo.orden = items[0]['orden_anexo']
                        anexo.fecha_generacion = items[0]['fecha_anexo']
                        anexo.num_paginas = items[0]['paginas_anexo']
                        anexo.archivo = d
                        anexo.save(request)
                    ids_excl.append(anexo.id)
                if not documentos and lista_anexos:
                    for items in lista_anexos:
                        if items['id_anexo']:
                            anexo = AnexoDocumentoIncidencia.objects.get(id=items['id_anexo'])
                            anexo.nombre = items['nombre_anexo']
                            anexo.orden = items['orden_anexo']
                            anexo.fecha_generacion = items['fecha_anexo']
                            anexo.num_paginas = items['paginas_anexo']
                            anexo.save(request)
                documento.get_anexos().exclude(id__in=ids_excl).update(status=False)
                generar_acta_reunion(documento, request, lista_convocados, lista_planes)
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'firmardocumento':
            try:
                context = {'lx': 395, 'ly_menos': 25}
                firmar_documento_etapa(request, persona, context)
                return JsonResponse({"result": False, "mensaje": "Guardado con exito", }, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % ex})

        elif action == 'validarprueba':
            try:
                form = ValidarPruebaForm(request.POST)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                respuesta = RespuestaDescargo.objects.get(pk=encrypt_id(request.POST['id']))
                respuesta.estado = int(form.cleaned_data['estado'])
                respuesta.observacion = form.cleaned_data['observacion']
                respuesta.save(request)
                log(f'Valido prueba de descargo: {respuesta}', request, 'edit')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, "mensaje": f"Error inesperado: {ex}"})

        elif action == 'finalizaretapa':
            try:
                incidencia = IncidenciaSancion.objects.get(pk=encrypt_id(request.POST['id']))
                incidencia.etapa = 3
                incidencia.estado = 6
                incidencia.save(request)
                incidencia.personas_sancion_prodecedente().update(bloqueo=False)
                log(f'Finalizo etapa analisis y paso a etapa de audiencia: {incidencia}', request, 'edit')
                return JsonResponse({'result': 'ok', 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": f"Error inesperado: {ex}"})

        elif action == 'finalizarcaso':
            try:
                incidencia = IncidenciaSancion.objects.get(pk=encrypt_id(request.POST['id']))
                incidencia.etapa = 4
                incidencia.estado = 10
                incidencia.fecha_fin = hoy
                incidencia.save(request)
                log(f'Finalizo caso: {incidencia}', request, 'edit')
                return JsonResponse({'result': 'ok', 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": f"Error inesperado: {ex}"})

        elif action == 'planificaraudiencia':
            try:
                context = post_planificaraudiencia(data, request)
                return JsonResponse(context)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, "mensaje": f"Error inesperado: {ex}"})

        elif action == 'reprogramaraudiencia':
            try:
                context = post_planificaraudiencia(data, request)
                return JsonResponse(context)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, "mensaje": f"Error inesperado: {ex}"})

        elif action == 'delplanificacion':
            try:
                audiencia = AudienciaSancion.objects.get(pk=encrypt_id(request.POST['id']))
                audiencia.status = False
                audiencia.save(request)
                log(f'Elimino planificacion de audiencia: {audiencia}', request, 'del')
                return JsonResponse({'error': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'error': True, "mensaje": f"Error inesperado: {ex}"})

        elif action == 'cambiarestadoaudiencia':
            try:
                context = post_cambiarestado_audiencia(data, request)
                return JsonResponse({'result': 'ok', 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": f"Error inesperado: {ex}"})

        elif action == 'savedetalleaudiencia':
            try:
                id = request.POST['args']
                value = request.POST['value']
                det_audiencia = DetalleAudienciaSancion.objects.get(pk=encrypt_id(id))
                det_audiencia.descripcion = value
                det_audiencia.save(request)
                log(f'Actualizo detalle de audiencia: {det_audiencia}', request, 'edit')
                return JsonResponse({'result': True, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': False, "mensaje": f"Error inesperado: {ex}"})

        elif action == 'remitirdescargo':
            try:
                context =post_remitir_descargo(data, request)
                return JsonResponse(context)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': str(ex)})

        elif action == 'generaracta':
            try:
                context = post_generaracta(data, request)
                return JsonResponse(context)
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'addmotivo':
            try:
                form = MotivoSancionForm(request.POST)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                motivo = MotivoSancion(nombre=form.cleaned_data['nombre'],
                                       descripcion=form.cleaned_data['descripcion'],
                                       falta=form.cleaned_data['falta'],
                                       principal=True)
                motivo.save(request)
                lista_items1 = json.loads(request.POST['lista_items1'])
                for item in lista_items1:
                    submotivo = MotivoSancion(nombre=item['sub_nombre'].strip().upper(), descripcion=item['sub_descripcion'], motivoref=motivo)
                    submotivo.save(request)

                log(f'Add motivo de sanción: {motivo}', request, 'add')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'editmotivo':
            try:
                id = encrypt_id(request.POST['id'])
                motivo = MotivoSancion.objects.get(id=id)
                form = MotivoSancionForm(request.POST, instancia=motivo)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                motivo.nombre = form.cleaned_data['nombre']
                motivo.descripcion = form.cleaned_data['descripcion']
                motivo.falta = form.cleaned_data['falta']
                motivo.save(request)
                lista_items1 = json.loads(request.POST['lista_items1'])
                ids_excl = [int(item['id_submotivo']) for item in lista_items1 if item['id_submotivo']]

                for item in lista_items1:
                    if item['id_submotivo']:
                        submotivo = MotivoSancion.objects.get(id=encrypt_id(item['id_submotivo']))
                        submotivo.nombre = item['sub_nombre'].strip().upper()
                        submotivo.descripcion = item['sub_descripcion']
                        submotivo.save(request)
                    else:
                        submotivo = MotivoSancion(nombre=item['sub_nombre'].strip().upper(), descripcion=item['sub_descripcion'], motivoref=motivo)
                        submotivo.save(request)
                        ids_excl.append(submotivo.id)
                MotivoSancion.objects.filter(motivoref=motivo).exclude(id__in=ids_excl).update(status=False)

                log(f'Edito motivo de sanción: {motivo}', request, 'edit')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'delmotivo':
            try:
                id = encrypt_id(request.POST['id'])
                motivo = MotivoSancion.objects.get(id=id)
                motivo.status = False
                motivo.save(request)
                log(f'Elimino motivo de sanción: {motivo}', request, 'del')
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': f'Error: {ex}'})

        elif action == 'addsubmotivo':
            try:
                form = SubMotivoSancionForm(request.POST)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                submotivo = MotivoSancion(nombre=form.cleaned_data['nombre'],
                                          descripcion=form.cleaned_data['descripcion'],
                                          motivoref=form.cleaned_data['motivoref'])
                submotivo.save(request)
                log(f'Add submotivo de sanción: {submotivo}', request, 'add')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'editsubmotivo':
            try:
                id = encrypt_id(request.POST['id'])
                submotivo = MotivoSancion.objects.get(id=id)
                form = SubMotivoSancionForm(request.POST, instancia=submotivo)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                submotivo.nombre = form.cleaned_data['nombre']
                submotivo.descripcion = form.cleaned_data['descripcion']
                submotivo.motivoref = form.cleaned_data['motivoref']
                submotivo.save(request)
                log(f'Edito submotivo de sanción: {submotivo}', request, 'edit')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'delsubmotivo':
            try:
                id = encrypt_id(request.POST['id'])
                submotivo = MotivoSancion.objects.get(id=id)
                submotivo.status = False
                submotivo.save(request)
                log(f'Elimino submotivo de sanción: {submotivo}', request, 'del')
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': f'Error: {ex}'})

        elif action == 'addrequisito':
            try:
                form = RequisitoSancionForm(request.POST)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                requisito = RequisitoSancion(nombre=form.cleaned_data['nombre'],
                                                descripcion=form.cleaned_data['descripcion'],
                                                tiporequisto=form.cleaned_data['tiporequisto'])
                requisito.save(request)
                log(f'Add requisito de sanción: {requisito}', request, 'add')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'editrequisito':
            try:
                id = encrypt_id(request.POST['id'])
                requisito = RequisitoSancion.objects.get(id=id)
                form = RequisitoSancionForm(request.POST, instancia=requisito)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                requisito.nombre = form.cleaned_data['nombre']
                requisito.descripcion = form.cleaned_data['descripcion']
                requisito.tiporequisto = form.cleaned_data['tiporequisto']
                requisito.save(request)
                log(f'Edito requisito de sanción: {requisito}', request, 'edit')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'delrequisito':
            try:
                id = encrypt_id(request.POST['id'])
                falta = RequisitoSancion.objects.get(id=id)
                falta.status = False
                falta.save(request)
                log(f'Elimino requisito de sanción: {falta}', request, 'del')
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': f'Error: {ex}'})

        elif action == 'addrequisitomotivo':
            try:
                form = RequisitoMotivoSancionForm(request.POST)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                requisito = RequisitoMotivoSancion(motivo=form.cleaned_data['motivo'],
                                                   activo=form.cleaned_data['activo'],
                                                   obligatorio=form.cleaned_data['obligatorio'],
                                                   punto_control=form.cleaned_data['punto_control'],
                                                   requisito=form.cleaned_data['requisito'])
                requisito.save(request)
                log(f'Add requisito de sanción: {requisito}', request, 'add')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'editrequisitomotivo':
            try:
                id = encrypt_id(request.POST['id'])
                requisito = RequisitoMotivoSancion.objects.get(id=id)
                form = RequisitoMotivoSancionForm(request.POST, instancia=requisito)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, 'mensaje': 'Error en el formulario'})
                requisito.motivo = form.cleaned_data['motivo']
                requisito.requisito = form.cleaned_data['requisito']
                requisito.activo = form.cleaned_data['activo']
                requisito.punto_control = form.cleaned_data['punto_control']
                requisito.obligatorio = form.cleaned_data['obligatorio']
                requisito.save(request)
                log(f'Edito requisito de sanción: {requisito}', request, 'edit')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'delrequisitomotivo':
            try:
                id = encrypt_id(request.POST['id'])
                requisito = RequisitoMotivoSancion.objects.get(id=id)
                requisito.status = False
                requisito.save(request)
                log(f'Elimino requisito de sanción: {requisito}', request, 'del')
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': f'Error: {ex}'})

        elif action == 'addfaltadisciplinaria':
            try:
                form = FaltaDisciplinariaForm(request.POST)
                id_nombre = int(request.POST.get('nombre'))
                nombre = NOMBRE_FALTA_DISCIPLINARIA[id_nombre][1]
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                falta = FaltaDisciplinaria(nombre=nombre,
                                             descripcion=form.cleaned_data['descripcion'],
                                             regimen_laboral=form.cleaned_data['regimen_laboral'],
                                             articulo=form.cleaned_data['articulo'],
                                           motivacionjuridica = form.cleaned_data['motivacionjuridica'])
                falta.save(request)
                log(f'Add falta disciplinaria: {falta}', request, 'add')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'editfaltadisciplinaria':
            try:
                id = encrypt_id(request.POST['id'])
                falta = FaltaDisciplinaria.objects.get(id=id)
                form = FaltaDisciplinariaForm(request.POST, instancia=falta)
                id_nombre = int(request.POST.get('nombre'))
                nombre = NOMBRE_FALTA_DISCIPLINARIA[id_nombre][1]
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                falta.nombre = nombre
                falta.descripcion = form.cleaned_data['descripcion']
                falta.regimen_laboral = form.cleaned_data['regimen_laboral']
                falta.articulo = form.cleaned_data['articulo']
                falta.motivacionjuridica = form.cleaned_data['motivacionjuridica']
                falta.save(request)
                log(f'Edito falta disciplinaria: {falta}', request, 'edit')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'delfaltasdisciplinarias':
            try:
                id = encrypt_id(request.POST['id'])
                falta = FaltaDisciplinaria.objects.get(id=id)
                falta.status = False
                falta.save(request)
                log(f'Elimino falta disciplinaria: {falta}', request, 'del')
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': f'Error: {ex}'})

        elif action == 'cambiarestadoreq':
            try:
                id = encrypt_id(request.POST['id'])
                requisito = RequisitoMotivoSancion.objects.get(id=id)
                requisito.activo = not requisito.activo
                requisito.save(request)
                log(f'Cambio estado de requisito de sanción: {requisito}', request, 'edit')
                return JsonResponse({'result': True, 'mensaje': 'Actualizado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

        elif action == 'cambiarobligatorioreq':
            try:
                id = encrypt_id(request.POST['id'])
                requisito = RequisitoMotivoSancion.objects.get(id=id)
                requisito.obligatorio = not requisito.obligatorio
                requisito.save(request)
                log(f'Cambio estado de requisito de sanción: {requisito}', request, 'edit')
                return JsonResponse({'result': True, 'mensaje': 'Actualizado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

        elif action == 'addresponsablefirma':
            try:
                form = ResponsableFirmaForm(request.POST)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                responsablefirma = ResponsableFirma(persona=form.cleaned_data['persona'],
                                               tipo_doc=form.cleaned_data['tipo_doc'],
                                               rol_doc=form.cleaned_data['rol_doc'],
                                               firma_doc=form.cleaned_data['firma_doc'],
                                               orden=form.cleaned_data['orden'])
                responsablefirma.save(request)
                log(f'Add responsable de firma: {responsablefirma}', request, 'add')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'editresponsablefirma':
            try:
                id = encrypt_id(request.POST['id'])
                responsablefirma = ResponsableFirma.objects.get(id=id)
                form = ResponsableFirmaForm(request.POST, instancia=responsablefirma)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, 'mensaje': 'Error en el formulario'})
                responsablefirma.persona = form.cleaned_data['persona']
                responsablefirma.tipo_doc = form.cleaned_data['tipo_doc']
                responsablefirma.rol_doc = form.cleaned_data['rol_doc']
                responsablefirma.firma_doc = form.cleaned_data['firma_doc']
                responsablefirma.orden = form.cleaned_data['orden']
                responsablefirma.save(request)
                log(f'Edito responsable de firma: {responsablefirma}', request, 'edit')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'delresponsablefirma':
            try:
                id = encrypt_id(request.POST['id'])
                responsablefirma = ResponsableFirma.objects.get(id=id)
                responsablefirma.status = False
                responsablefirma.save(request)
                log(f'Elimino responsable de firma: {responsablefirma}', request, 'del')
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': f'Error: {ex}'})

        elif action == 'generaraccionpersonal':
            try:
                context = post_generar_accionpersonal(data, request)
                return JsonResponse(context)
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'validaraudiencia':
            try:
                context = post_validar_audiencia(data, request)
                return JsonResponse(context)
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'validarasistenciaaudiencia':
            try:
                lista_items1 = json.loads(request.POST['lista_items1'])
                for item in lista_items1:
                    per_aud = PersonaAudienciaSancion.objects.get(id=item['id_persona'])
                    if per_aud.rol_firma == 7:
                        per_aud.validacion_asis = estado_val = int(item['estado_asistencia'])
                        if estado_val == 2:
                            per_aud.observacion_asis = item['observacion_asistencia']
                        else:
                            per_aud.observacion_asis = ''
                        per_aud.save(request)
                return JsonResponse({'result': False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error inesperado: {ex}'})

        elif action == 'addmotivocaso':
            try:
                form = MotivoAccionPersonalForm(request.POST)
                if form.is_valid():
                    motivo = MotivoAccionPersonal(nombre=form.cleaned_data['nombre'],
                                                  activo=form.cleaned_data['activo'],
                                                  orden=form.cleaned_data['orden'],
                                                  abreviatura=form.cleaned_data['abreviatura'])
                    motivo.save(request)
                    log(u'Registro motivo caso: %s' % motivo, request, "add")
                    return JsonResponse({'result': False})
                raise NameError('Error en el formulario')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'editmotivocaso':
            try:
                form = MotivoAccionPersonalForm(request.POST)
                filtro = MotivoAccionPersonal.objects.get(id=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    filtro.nombre = form.cleaned_data['nombre']
                    filtro.abreviatura = form.cleaned_data['abreviatura']
                    filtro.orden = form.cleaned_data['orden']
                    filtro.activo = form.cleaned_data['activo']
                    filtro.save(request)
                    log(u'Edito motivo caso: %s' % filtro, request, action)
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})


        # elif action == 'delmotivocaso':
        #     try:
        #         id = encrypt_id(request.POST['id'])
        #         motivocaso = MotivoAccionPersonal.objects.get(id=id)
        #         motivocaso.status = False
        #         motivocaso.save(request)
        #         log(f'Elimino responsable de firma: {motivocaso.nombre}', request, 'del')
        #         return JsonResponse({'result': 'ok'})
        #     except Exception as ex:
        #         return JsonResponse({'result': 'bad', 'mensaje': f'Error: {ex}'})

        elif action == 'addbaselegal':
            try:
                form = BaseLegalAccionPersonalForm(request.POST)
                if form.is_valid():
                    base = BaseLegalAccionPersonal(descripcion=form.cleaned_data['descripcion'])
                    base.save(request)
                    log(u'Registro base legal: %s' % base, request, action)
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'editbaselegal':
            try:
                form = BaseLegalAccionPersonalForm(request.POST)
                filtro = BaseLegalAccionPersonal.objects.get(id=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    filtro.descripcion = form.cleaned_data['descripcion']
                    filtro.save(request)
                    log(u'Edito base legal: %s' % filtro, request, action)
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        # elif action == 'delbaselegal':
        #     try:
        #         id = encrypt_id(request.POST['id'])
        #         baselegal = BaseLegalAccionPersonal.objects.get(id=id)
        #         baselegal.status = False
        #         baselegal.save(request)
        #         log(f'Elimino responsable de firma: {baselegal}', request, 'del')
        #         return JsonResponse({'result': 'ok'})
        #     except Exception as ex:
        #         return JsonResponse({'result': 'bad', 'mensaje': f'Error: {ex}'})

        elif action == 'addconfigurar':
            try:
                id = encrypt_id(request.POST['id'])
                motivo = MotivoAccionPersonal.objects.get(pk=id)
                form = MotivoAccionPersonalDetalleForm(request.POST)
                if form.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    if not datos:
                        return JsonResponse({'result': True, 'mensaje': f'Error: debe seleccionar al menos un regimen laboral.'})
                    for d in datos:
                        id = d['id']
                        if not (MotivoAccionPersonalDetalle.objects.filter(status=True, motivo=motivo, regimenlaboral_id=id).exists()):
                            detalle = MotivoAccionPersonalDetalle(motivo=motivo,
                                                                  baselegal=form.cleaned_data['baselegal'],
                                                                  regimenlaboral_id=id
                                                                  )
                            detalle.save()
                            log(u'aconfiguro %s en accion de personal' % motivo, request, "edit")
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'delconfigurar':
            try:
                config = MotivoAccionPersonalDetalle.objects.get(pk=encrypt(request.POST['id']), status=True)
                config.status = False
                config.save(request)
                log(u'Elimino configuracion: %s' % config, request, "del")
                return JsonResponse({'result': 'ok', 'mensaje': 'Registro eliminado correctamente'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': f'Error al eliminar el registro. {ex}'})

        elif action == 'confirmacionfirma':
            try:
                id, tipo_doc = request.POST['id'].split(',')
                id = encrypt_id(id)
                tipo_doc = int(tipo_doc)
                persna_sancion = PersonaSancion.objects.get(id=id)
                persna_sancion.bloqueo = True
                persna_sancion.notificacion = 3
                persna_sancion.save(request)
                request.session['persona_sancion_notificar'] = None
                consulta_firma = ConsultaFirmaPersonaSancion(persona_sancion=persna_sancion, tipo_doc=tipo_doc)
                consulta_firma.save(request)
                log(f'Se ha solicitado la confirmación de firma de: {persna_sancion}', request, 'add')
                return JsonResponse(
                    {'result': 'ok', 'mensaje': 'Se ha solicitado la confirmación de firma satisfactoriamente', 'showSwal': True})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': f'Error: {ex}'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        search, filtro, url_vars  = request.GET.get('s', ''), Q(status=True), ''
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            url_vars = f'&action={action}'

            # Sanciones
            if action == 'revisarincidencia':
                try:
                    template, data = get_revisar_audiencia(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'validarcaso':
                try:
                    id, observacion = encrypt_id(request.GET['id']), ''
                    if request.GET['idex']:
                        data['idp'] = idp = encrypt_id(request.GET['idex'])
                        validador = ResponsableEtapaIncidencia.objects.get(id=idp)
                        observacion = validador.observacion
                    incidencia = IncidenciaSancion.objects.get(id=id)
                    form = ValidarCasoForm(initial={'idincidencia': encrypt(incidencia.id),
                                                    'estado': incidencia.estado,
                                                    'falta': incidencia.falta,
                                                    'observacion': observacion})
                    form.fields['falta'].queryset = FaltaDisciplinaria.objects.filter(status=True,
                                                                                      regimen_laboral=incidencia.falta.regimen_laboral)
                    if not incidencia.motivo:
                        form.fields['motivoprincipal'].queryset = MotivoSancion.objects.filter(status=True, falta=incidencia.falta, principal=True)
                        # form.fields['motivo'].required = True
                        # form.fields['motivoprincipal'].required = True
                    else:
                        form.fields['motivoprincipal'].queryset = MotivoSancion.objects.none()
                        form.fields['motivoprincipal'].widget = forms.HiddenInput()
                        form.fields['motivo'].widget = forms.HiddenInput()
                    form.fields['motivo'].queryset = MotivoSancion.objects.none()
                    data['form'] = form
                    data['incidencia'] = incidencia
                    data['id'] = id
                    data['estados_persona'] = ESTADO_SANCION_PERSONA[1:3]
                    data['permisos'] = permisos = permisos_sanciones(persona)
                    template = get_template('adm_sanciones/modal/formvalidarcaso.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'generardocumento':
                try:
                    id, tipo_doc = encrypt_id(request.GET['id']), request.GET['idex']
                    data['tipo_doc'] = tipo_doc
                    if not tipo_doc:
                        documento = DocumentoEtapaIncidencia.objects.get(id=id)
                        form = GenerarDocumentoForm(initial=model_to_dict(documento))
                        form.fields['persona_recepta'].queryset = Persona.objects.filter(id=documento.persona_recepta.id)
                        data['documento'] = documento
                        data['anexos'] = documento.get_anexos()
                        tipo_doc = documento.tipo_doc
                    else:
                        data['tipo_doc'] = tipo_doc
                        lista_ids = []
                        incidencia = IncidenciaSancion.objects.get(id=id)
                        txtObjeto = get_text_campo_objeto(incidencia)
                        form = GenerarDocumentoForm(initial={'idincidencia': encrypt(incidencia.id)})
                        form.fields['persona_recepta'].queryset = Persona.objects.filter(status=True, cedula='0913716809')
                        form.fields['persona_recepta'].initial = Persona.objects.get(status=True, cedula='0913716809')
                        form.fields['persona_recepta'].widget.attrs['readonly'] = True
                        form.fields['objeto'].initial = txtObjeto
                        data['incidencia'] = incidencia
                        if tipo_doc == '1':
                            text_antecendentes = get_text_antecedentes_informe_echos(incidencia)
                            form.fields['antecedentes'].widget.attrs['ckeditor-text'] = text_antecendentes
                            text_motivacion_tec = get_text_motivacion_tecnica_informe_echos(incidencia)
                            form.fields['motivacion'].widget.attrs['ckeditor-text'] = text_motivacion_tec
                        elif tipo_doc == '4':
                            text_antecendentes = get_text_antecedentes_informe_echos(incidencia)
                            form.fields['antecedentes'].widget.attrs['ckeditor-text'] = text_antecendentes
                            text_motivacion_tec = get_text_motivacion_tecnica_informe_sustanciacion(incidencia)
                            form.fields['motivacion'].widget.attrs['ckeditor-text'] = text_motivacion_tec
                            text_conclucion = get_text_concluciones_informe_sustanciacion(incidencia)
                            form.fields['conclusion'].widget.attrs['ckeditor-text'] = text_conclucion
                            form.fields['recomendacion'].widget.attrs['ckeditor-text'] = Strings.RecomendacionesInformeSustanciacion
                            form.fields['objeto'].initial = get_text_campo_objeto_informe_sustanciacion(incidencia)


                    resp_firma = ResponsableFirma.objects.filter(status=True, persona=persona, tipo_doc=int(tipo_doc), firma_doc=True).exclude(rol_doc=1).first()
                    if resp_firma:
                        return JsonResponse({'result': False, 'mensaje': f'Usted ya se encuentra asignado para firmar el documento'
                                                         f' con el rol: "{resp_firma.get_rol_doc_display()}"'
                                                         f' por lo tanto, el documento debe ser elaborado por otro responsable.'})
                    data['responsables_firma'] = resposables_firma_doc(int(tipo_doc), [2, 3, 11])
                    data['form'] = form
                    data['id'] = id
                    data['permisos'] = permisos = permisos_sanciones(persona)
                    template = get_template('adm_sanciones/modal/formgenerardocumento.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'generaractareunion':
                try:
                    id, tipo_doc = encrypt_id(request.GET['id']), request.GET['idex']
                    data['tipo_doc'] = tipo_doc
                    convocados = []
                    personas_planes = []
                    if not tipo_doc:
                        documento = DocumentoEtapaIncidencia.objects.get(id=id)
                        reunion = documento.reunion
                        incidencia = documento.incidencia
                        form = GenerarActaReunionForm(initial=model_to_dict(reunion))
                        data['documento'] = documento
                        data['anexos'] = documento.get_anexos()
                        tipo_doc = documento.tipo_doc
                        form.fields['convocador'].queryset = Persona.objects.filter(id=reunion.convocador.id)
                        form.fields['organizador'].queryset = Persona.objects.filter(id=reunion.organizador.id)
                        form.fields['apuntador'].queryset = Persona.objects.filter(id=reunion.apuntador.id)
                        convocados = documento.responsables_legalizacion().exclude(persona_id__in=[reunion.convocador.id, reunion.organizador.id, reunion.apuntador.id])
                        data['convocados'] = [persona_firma.persona for persona_firma in convocados]
                        data['personas_planes'] = personas_planes = [persona_firma for persona_firma in convocados if persona_firma.planaccion]
                    else:
                        data['tipo_doc'] = tipo_doc
                        incidencia = IncidenciaSancion.objects.get(id=id)
                        form = GenerarActaReunionForm(initial={'idincidencia': encrypt(incidencia.id)})
                        form.fields['convocador'].queryset = Persona.objects.none()
                        form.fields['organizador'].queryset = Persona.objects.none()
                        form.fields['apuntador'].queryset = Persona.objects.none()
                        persona_sancion = incidencia.personas_sancion().first()
                        data['convocados'] = convocados = [incidencia.persona, persona_sancion.persona]

                    data['form'] = form
                    data['id'] = id
                    data['permisos'] = permisos = permisos_sanciones(persona)
                    director = incidencia.persona

                    data['numConvocado'] = len(convocados)
                    data['numPlanAccion'] = len(personas_planes)
                    template = get_template('adm_sanciones/modal/formgeneraractareunion.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'firmardocumento':
                try:
                    data['id'] = encrypt_id(request.GET['id'])
                    template = get_template("formfirmaelectronicamasiva.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'Error: {ex}'})

            elif action == 'responsables':
                try:
                    data['title'] = 'Responsables de legalización de documentos'
                    data['subtitle'] = 'Listado de responsables de legalización de documentos'
                    filtro, search, url_vars = (Q(status=True), request.GET.get('s', ''), f'&action={action}')
                    rol, tipo = request.GET.get('rol', ''), request.GET.get('tipo', '')

                    if search:
                        filtro = filtro_persona(search, filtro)
                        data['s'] = search
                        url_vars += f'&s={search}'

                    if rol:
                        rol = int(rol)
                        filtro = filtro & Q(rol_doc=rol)
                        data['rol'] = rol
                        url_vars += f'&rol={rol}'

                    if tipo:
                        tipo = int(tipo)
                        filtro = filtro & Q(tipo_doc=tipo)
                        data['tipo'] = tipo
                        url_vars += f'&tipo={tipo}'

                    listado = ResponsableFirma.objects.filter(filtro).order_by('tipo_doc', 'rol_doc', 'orden')
                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    data['tiposdocumentos'] = TIPO_DOCUMENTOS
                    data['rolesdocumentos'] = ROL_FIRMA_DOCUMENTO
                    data['viewactivo'] = {'grupo': 'configuracion', 'action': action}
                    return render(request, 'adm_sanciones/responsables_firma.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'addresponsablefirma':
                try:
                    form = ResponsableFirmaForm()
                    data['form'] = form
                    data['switchery'] = True
                    form.fields['persona'].queryset = Persona.objects.none()
                    template = get_template('adm_sanciones/modal/formresponsablefirma.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'editresponsablefirma':
                try:
                    responsable = ResponsableFirma.objects.get(id=encrypt_id(request.GET['id']))
                    form = ResponsableFirmaForm(initial=model_to_dict(responsable))
                    form.fields['persona'].queryset = Persona.objects.filter(id=responsable.persona.id)
                    data['id'] = responsable.id
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template('adm_sanciones/modal/formresponsablefirma.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'validarprueba':
                try:
                    respuesta = RespuestaDescargo.objects.get(id=encrypt_id(request.GET['id']))
                    form = ValidarPruebaForm(initial=model_to_dict(respuesta))
                    data['form'] = form
                    data['id'] = respuesta.id
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'planificaraudiencia':
                try:
                    template, data = get_planificaraudiencia(data, request)
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'editplanificacion':
                try:
                    data['audiencia'] = audiencia = AudienciaSancion.objects.get(id=encrypt_id(request.GET['id']))
                    form = PlanificarAudienciaForm(initial=model_to_dict(audiencia))
                    query = Ubicacion.objects.filter(bloque=audiencia.bloque, status=True) if audiencia.bloque else Ubicacion.objects.none()
                    form.fields['ubicacion'].queryset = query
                    form.fields['notificar'].initial = True if audiencia.estado == 1 else False
                    form.fields['id_incidencia'].initial = audiencia.incidencia.id
                    data['action'] = 'planificaraudiencia'
                    if request.GET['idex'] == 'reprogramar':
                        data['action'] = 'reprogramaraudiencia'
                    data['form'] = form
                    data['switchery'] = True
                    data['incidencia'] = incidencia = audiencia.incidencia
                    data['id'] = audiencia.id
                    data['responsables_audiencia'] = personas_firmar = audiencia.personas_audiencia_excl()
                    data['addintegrante'] = request.GET.get('idex','') == 'addintegrante'
                    data['numDetalle'] = len(personas_firmar)
                    data['roles'] = choice_indice(ROL_FIRMA_DOCUMENTO,[4,5,6,12,13])
                    template = get_template('adm_directivos/forms/formplanificar.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'detalleaudiencia':
                try:
                    template, data = get_detalleaudiencia(data, request)
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

                return HttpResponseRedirect(request.path)

            elif action == 'generaracta':
                try:

                    template, data = get_generaracta(data, request)
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'historialfirmas':
                try:
                    template, data = get_historialfirmas(data, request)
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'cargarmotivos':
                try:
                    tipo = request.GET['args']
                    if tipo == 'principal':
                        falta = FaltaDisciplinaria.objects.get(id=int(request.GET['id']))
                        motivos = falta.motivos_principales()
                    else:
                        motivo = MotivoSancion.objects.get(id=int(request.GET['id']))
                        motivos = motivo.sub_motivos()
                    motivos = [{'value': m.id, 'text': m.nombre} for m in motivos]
                    return JsonResponse({'result': True, 'data': motivos})
                except Exception as e:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'faltasdisciplinarias':
                try:
                    data['title'] = 'Faltas disciplinarias'
                    data['subtitle'] = 'Listado de faltas disciplinarias'
                    filtro, search, url_vars = (Q(status=True), request.GET.get('s', ''), f'&action={action}')
                    if search:
                        filtro = filtro & (Q(nombre__unaccent__icontains=search) | Q(descripcion__unaccent__icontains=search))
                        data['s'] = search
                        url_vars += f'&s={search}'
                    listado = FaltaDisciplinaria.objects.filter(filtro)
                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    data['viewactivo'] = {'grupo': 'configuracion', 'action': action}
                    return render(request, 'adm_sanciones/faltasdisciplinarias.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'addfaltadisciplinaria':
                try:
                    form =  FaltaDisciplinariaForm()
                    form.fields['regimen_laboral'].queryset = RegimenLaboral.objects.filter(id__in=[1])
                    form.fields['regimen_laboral'].initial = 1
                    data['form'] = form
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'verfaltadisciplinaria':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    falta = FaltaDisciplinaria.objects.get(id=id)
                    data['nombre'] = falta.nombre
                    data['descripcion'] = falta.descripcion
                    data['regimen'] = falta.regimen_laboral.descripcion
                    data['articulo'] = falta.articulo
                    data['motivacionjuridica'] = falta.motivacionjuridica
                    template = get_template('adm_sanciones/modal/viewfaltadisciplinaria.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'editfaltadisciplinaria':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    falta = FaltaDisciplinaria.objects.get(id=id)
                    # pos_nombre = [index for index, (key, value) in enumerate(NOMBRE_FALTA_DISCIPLINARIA) if value == falta.nombre][0]
                    frmfalta = FaltaDisciplinariaForm(initial=model_to_dict(falta))
                    data['form'] = frmfalta
                    # frmfalta.initial['nombre'] = pos_nombre
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'motivos':
                try:
                    data['title'] = 'Clasificación de sanción'
                    data['subtitle'] = 'Listado de clasificación de sanción'
                    filtro, search, url_vars = (Q(status=True, principal=True), request.GET.get('s', ''), f'&action={action}')
                    falta = request.GET.get('falta', '')
                    if search:
                        filtro = filtro & (Q(nombre__unaccent__icontains=search) | Q(descripcion__unaccent__icontains=search))
                        data['s'] = search
                        url_vars += f'&s={search}'
                    if falta:
                        falta = int(falta)
                        filtro = filtro & Q(falta_id=falta)
                        data['falta'] = falta
                        url_vars += f'&falta={falta}'

                    listado = MotivoSancion.objects.filter(filtro).order_by('falta', 'nombre')
                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    data['faltas'] = FaltaDisciplinaria.objects.filter(status=True)
                    data['viewactivo'] = {'grupo': 'configuracion', 'action': action}
                    return render(request, 'adm_sanciones/motivos.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'addmotivo':
                try:
                    data['form'] = MotivoSancionForm()
                    template = get_template('adm_sanciones/modal/formmotivo.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'editmotivo':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    data['motivo'] = motivo = MotivoSancion.objects.get(id=id)
                    data['form'] = MotivoSancionForm(initial=model_to_dict(motivo))
                    template = get_template('adm_sanciones/modal/formmotivo.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'submotivos':
                try:
                    data['title'] = 'Sub clasificación de sanción'
                    data['subtitle'] = 'Listado de sub clasificación de sanción'
                    filtro, search, url_vars = (Q(status=True, principal=False), request.GET.get('s', ''), f'&action={action}')
                    motivo = request.GET.get('motivo', '')
                    if search:
                        filtro = filtro & (Q(nombre__unaccent__icontains=search) | Q(descripcion__unaccent__icontains=search))
                        data['s'] = search
                        url_vars += f'&s={search}'

                    if motivo:
                        motivo = int(motivo)
                        filtro = filtro & Q(motivoref_id=motivo)
                        data['motivo'] = motivo
                        url_vars += f'&motivo={motivo}'

                    listado = MotivoSancion.objects.filter(filtro).order_by('motivoref', 'nombre')
                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    data['motivos'] = MotivoSancion.objects.filter(status=True, principal=True)
                    data['viewactivo'] = {'grupo': 'configuracion', 'action': action}
                    return render(request, 'adm_sanciones/submotivos.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'addsubmotivo':
                try:
                    data['form'] = SubMotivoSancionForm()
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'editsubmotivo':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    submotivo = MotivoSancion.objects.get(id=id)
                    data['form'] = SubMotivoSancionForm(initial=model_to_dict(submotivo))
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'motivocaso':
                try:
                    data['title'] = u'Motivos'
                    data['subtitle'] = 'Precedente de sancion'
                    filtro, search, url_vars = (Q(status=True), request.GET.get('s', ''), f'&action={action}')
                    if search:
                        filtro = filtro & (
                                    Q(nombre__unaccent__icontains=search) | Q(abreviatura__unaccent__icontains=search))
                        data['s'] = search
                        url_vars += f'&s={search}'

                    listado = MotivoAccionPersonal.objects.filter(filtro).order_by('orden')

                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    data['viewactivo'] = {'grupo': 'configuracion', 'action': action}
                    return render(request, 'adm_sanciones/motivocaso.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')


            elif action == 'addmotivocaso':
                try:
                    data['switchery'] = True
                    data['form'] = MotivoAccionPersonalForm()
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})


            elif action == 'editmotivocaso':
                try:
                    data['switchery'] = True
                    data['id'] = id = encrypt_id(request.GET['id'])
                    motivo = MotivoAccionPersonal.objects.get(id=id)
                    data['form'] = MotivoAccionPersonalForm(initial=model_to_dict(motivo))
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})


            elif action == 'baselegal':
                try:
                    data['title'] = u'Base legal'
                    data['subtitle'] = ' '
                    filtro, search, url_vars = (Q(status=True), request.GET.get('s', ''), f'&action={action}')
                    if search:
                        filtro = filtro & (
                                    Q(descripcion__unaccent__icontains=search)
                        )
                        data['s'] = search
                        url_vars += f'&s={search}'

                    listado = BaseLegalAccionPersonal.objects.filter(filtro).order_by('id')

                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    data['viewactivo'] = {'grupo': 'configuracion', 'action': action}
                    return render(request, 'adm_sanciones/baselegal.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'addbaselegal':
                try:
                    data['form'] = BaseLegalAccionPersonalForm()
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'editbaselegal':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    model = BaseLegalAccionPersonal.objects.get(id=id)
                    data['form'] = BaseLegalAccionPersonalForm(initial=model_to_dict(model))
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})


            elif action == 'requisitos':
                try:
                    data['title'] = 'Tipos de archivos'
                    data['subtitle'] = 'Rcuerde llenar todos los tipos de archivos que estaran disponibles para los distintos requisitos a solicitar'
                    filtro, search, url_vars = (Q(status=True), request.GET.get('s', ''), f'&action={action}')
                    if search:
                        filtro = filtro & (Q(nombre__unaccent__icontains=search) | Q(descripcion__unaccent__icontains=search))
                        data['s'] = search
                        url_vars += f'&s={search}'
                    listado = RequisitoSancion.objects.filter(filtro)
                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    data['viewactivo'] = {'grupo': 'configuracion', 'action': action}
                    return render(request, 'adm_sanciones/requisitos.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'addrequisito':
                try:
                    data['form'] = RequisitoSancionForm()
                    template = get_template('ajaxformmodal.html')
                    data['switchery'] = True
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'editrequisito':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    motivo = RequisitoSancion.objects.get(id=id)
                    data['form'] = RequisitoSancionForm(initial=model_to_dict(motivo))
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'requisitomotivo':
                try:
                    data['title'] = 'Requisitos de sanción'
                    data['subtitle'] = 'Listado de requisitos de sanción'
                    filtro, search, url_vars = (Q(status=True), request.GET.get('s', ''), f'&action={action}')
                    requisito = request.GET.get('requisito', '')
                    submotivo = request.GET.get('submotivo', '')
                    if requisito:
                        requisito = int(requisito)
                        filtro &= Q(requisito_id=requisito)
                        url_vars += f'&requisito={requisito}'
                        data['requisito'] = requisito

                    if submotivo:
                        submotivo = int(submotivo)
                        filtro &= Q(motivo_id=submotivo)
                        url_vars += f'&submotivo={submotivo}'
                        data['submotivo'] = submotivo
                    if search:
                        filtro = filtro & (Q(requisito__nombre__unaccent__icontains=search) | Q(requisito__descripcion__unaccent__icontains=search))
                        data['s'] = search
                        url_vars += f'&s={search}'

                    listado = RequisitoMotivoSancion.objects.filter(filtro)
                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    data['switchery'] = True
                    data['requisitos'] = RequisitoSancion.objects.filter(status=True)
                    data['submotivos'] = MotivoSancion.objects.filter(status=True, principal=False)
                    data['viewactivo'] = {'grupo': 'configuracion', 'action': action}
                    return render(request, 'adm_sanciones/requisitomotivo.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'addrequisitomotivo':
                try:
                    data['form'] = RequisitoMotivoSancionForm()
                    template = get_template('ajaxformmodal.html')
                    data['switchery'] = True
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'generaraccionpersonal':
                try:
                    template, data = get_generar_accionpersonal(data, request)
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'validaraudiencia':
                try:
                    template, data = get_validar_audiencia(data, request)
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'editrequisitomotivo':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    requisito = RequisitoMotivoSancion.objects.get(id=id)
                    data['form'] = RequisitoMotivoSancionForm(initial=model_to_dict(requisito))
                    template = get_template('ajaxformmodal.html')
                    data['switchery'] = True
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'incidenciasbiometrico':
                try:
                    data['title'] = 'Incidencias registradas por biometrico'
                    data['subtitle'] = 'Listado de incidencias registradas por biometrico'
                    estado, departamento, filtro, search, url_vars = (request.GET.get('estado', ''),
                                                                      request.GET.get('departamento', ''),
                                                                      Q(status=True, persona_id=1),
                                                                      request.GET.get('s', ''), f'')
                    if estado:
                        data['estado'] = estado = int(estado)
                        filtro &= Q(estado=estado)
                        url_vars += f'&estado={estado}'
                    if departamento:
                        data['departamento'] = departamento = int(departamento)
                        filtro &= Q(departamento_id=departamento)
                        url_vars += f'&departamento={departamento}'
                    if search:
                        filtro_ = filtro_persona(search, filtro)
                        ids_insidencias = PersonaSancion.objects.filter(filtro_).values_list('incidencia_id',
                                                                                             flat=True).order_by(
                            'incidencia_id').distinct()
                        filtro &= (Q(codigo__unaccent__icontains=search) | Q(id__in=ids_insidencias))
                        data['s'] = search
                        url_vars += f'&s={search}'
                    listado = IncidenciaSancion.objects.filter(filtro).exclude(estado__in=[0, 1]).order_by('-fecha_creacion', '-estado')
                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    data['estados'] = ESTADO_INCIDENCIA[2:]
                    ids_departamentos = IncidenciaSancion.objects.filter(status=True).values_list('departamento_id',
                                                                                                  flat=True).order_by('departamento_id').distinct()
                    data['departamentos'] = departamentos_vigentes(ids_departamentos)
                    data['viewactivo'] = {'grupo': 'general', 'action': action}
                    return render(request, 'adm_sanciones/incidenciabiometrico.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'motivoaccionpersonal':
                try:
                    data['title'] = 'Motivos de acción personal'
                    data['subtitle'] = 'Listado de motivos de acción personal'
                    filtro, search, url_vars = (Q(status=True, principal=False), request.GET.get('s', ''), f'&action={action}')
                    if search:
                        filtro = filtro & (Q(nombre__unaccent__icontains=search) | Q(descripcion__unaccent__icontains=search))
                        data['s'] = search
                        url_vars += f'&s={search}'

                    listado = MotivoSancion.objects.filter(filtro).order_by('motivoref', 'nombre')
                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    data['motivos'] = MotivoSancion.objects.filter(status=True, principal=True)
                    data['viewactivo'] = {'grupo': 'configuracion', 'action': action}
                    return render(request, 'adm_sanciones/submotivos.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'validarasistenciaaudiencia':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    audiencia = AudienciaSancion.objects.get(id=id)
                    data['personas'] = audiencia.personas_audiencia()
                    data['estadoaprovacionasis'] = ESTADO_APROBACION_ASISTENCIA
                    template = get_template("adm_sanciones/modal/formvalidarasistenciaaudiencia.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return HttpResponseRedirect(request.path)

            elif action == 'configurar':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    data['motivo'] = motivo = MotivoAccionPersonal.objects.get(pk=id)
                    data['title'] = u'Configuración de %s' % motivo.nombre
                    data['subtitle'] = u' '
                    filtro, search, url_vars = (Q(status=True), request.GET.get('s', ''), f'&action={action}')
                    if search:
                        search = request.GET['s']
                        ss = search.split(' ')

                        if len(ss) == 1:
                            bases = MotivoAccionPersonalDetalle.objects.filter(motivo=motivo,regimenlaboral__descripcion__icontains=search,status=True).distinct().order_by('pk')
                        url_vars += f"&s={search}"
                    else:
                        bases = MotivoAccionPersonalDetalle.objects.filter(motivo=motivo, status=True).order_by('pk')
                    paginator = MiPaginador(bases, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    action = 'motivocaso'
                    data['viewactivo'] = {'grupo': 'configuracion', 'action': action}
                    return render(request, 'adm_sanciones/motivocasoconf.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'addconfigurar':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    data['title'] = u'Configurar'
                    data['form'] = MotivoAccionPersonalDetalleForm()
                    data['motivo'] = MotivoAccionPersonal.objects.get(pk=id)
                    data['regimenes'] = RegimenLaboral.objects.filter(status=True)
                    data['action'] = 'addconfigurar'
                    template = get_template('adm_sanciones/modal/motivocasoaddconf.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'signup':
                try:
                    form = SignupForm()
                    data['form'] = form
                    template = get_template('core/forms/signup_externo.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": str(ex)})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['biometrico'] = biometrico = request.GET.get('biometrico', '')
                if biometrico:
                    url_vars = f'&biometrico={biometrico}'
                    data['title'] = 'Incidencias registradas por biométrico'
                    data['subtitle'] = 'Listado de incidencias registradas por biometrico'
                    filtro = Q(status=True, persona_id=1)
                    filter_excl = Q(estado__in=[0, 1])
                    data['viewactivo'] = {'grupo': 'general', 'action': 'incidenciasbiometrico'}
                else:
                    data['title'] = 'Casos de sanción registrados'
                    data['subtitle'] = 'Listado de casos de sanción registrados'
                    url_vars, filtro = '', Q(status=True)
                    filter_excl = Q(estado__in=[0, 1]) | Q(persona_id=1)
                    data['viewactivo'] = {'grupo': 'general', 'action': 'sanciones'}
                estado, departamento, search = (request.GET.get('estado', ''),
                                                                  request.GET.get('departamento', ''),
                                                                  request.GET.get('s', ''))
                if estado:
                    data['estado'] = estado = int(estado)
                    filtro &= Q(estado=estado)
                    url_vars += f'&estado={estado}'
                if departamento:
                    data['departamento'] = departamento = int(departamento)
                    filtro &= Q(departamento_id=departamento)
                    url_vars += f'&departamento={departamento}'
                if search:
                    filtro_ = filtro_persona(search, filtro)
                    ids_insidencias = PersonaSancion.objects.filter(filtro_).values_list('incidencia_id', flat=True).order_by('incidencia_id').distinct()
                    filtro &= (Q(codigo__unaccent__icontains=search) | Q(id__in=ids_insidencias))
                    data['s'] = search
                    url_vars += f'&s={search}'
                listado = IncidenciaSancion.objects.filter(filtro).exclude(filter_excl).order_by('-fecha_creacion', '-estado')
                paginator = MiPaginador(listado, 20)
                page = int(request.GET.get('page', 1))
                paginator.rangos_paginado(page)
                data['paging'] = paging = paginator.get_page(page)
                data['listado'] = paging.object_list
                data['url_vars'] = url_vars
                data['estados'] = ESTADO_INCIDENCIA[2:]
                ids_departamentos = IncidenciaSancion.objects.filter(status=True).values_list('departamento_id', flat=True).order_by('departamento_id').distinct()
                data['departamentos'] = departamentos_vigentes(ids_departamentos)
                return render(request, 'adm_sanciones/casosdelegados.html', data)
            except Exception as ex:
                return HttpResponseRedirect(f'/?info=Error inesperado {ex}')

def obtener_lista(lista_items, clave):
    return lista_items[0].get(clave, []) if lista_items else []




