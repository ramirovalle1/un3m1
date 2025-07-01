# -*- coding: UTF-8 -*-
import io
import json
import os
import zipfile
from datetime import datetime

import PyPDF2
import time as ET
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from fitz import fitz
from xlwt import easyxf, XFStyle, Workbook
from django.core.files import File as DjangoFile
import random
from core.firmar_documentos_ec import JavaFirmaEc
from becadocente.forms import ConvocatoriaBecaForm
from core.firmar_documentos import firmar
from decorators import secure_module
from investigacion.funciones import coordinador_investigacion, vicerrector_investigacion_posgrado, rector_institucion, analista_investigacion, experto_investigacion, secuencia_informe_factibilidad, director_juridico, experto_juridico, secuencia_resolucion_comite, salto_linea_nombre_firma_encontrado, secuencia_solicitud_certificacion, experto_becas_docentes, decano_investigacion
from sagest.commonviews import obtener_estado_solicitud, obtener_estados_solicitud, obtener_estado_solicitud_por_id
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from django.template import Context
from django.template.loader import get_template

from decimal import Decimal

from sga.funciones import MiPaginador, log, validar_archivo, generar_nombre, cuenta_email_disponible_para_envio, fechaletra_corta, remover_atributo_style_html, moneda_a_letras, remover_caracteres, elimina_tildes, remover_caracteres_tildes_unicode, remover_caracteres_especiales_unicode, null_to_decimal, variable_valor

from becadocente.models import Convocatoria, Requisito, RequisitoConvocatoria, RecorridoRegistro, FormatoConvocatoria, Rubro, RubroConvocatoria, Solicitud, SolicitudRequisito, \
    SolicitudDocumento, InformeFactibilidad, DocumentoConvocatoria, InformeFactibilidadAnexo, Documento, ResolucionComite, SolicitudPresupuesto, SolicitudPresupuestoRubroDetalle, SolicitudPresupuestoRubro, CertificacionPresupuestaria, CertificacionPresupuestariaDetalle
from sga.funcionesxhtml2pdf import convert_html_to_pdf
from sga.models import CUENTAS_CORREOS
from sga.tasks import send_html_mail

from sga.templatetags.sga_extras import encrypt

@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    es_administrativo = perfilprincipal.es_administrativo()

    if not es_administrativo:
        return HttpResponseRedirect("/?info=El Módulo está disponible para administrativos.")

    es_expertobecas = persona.tiene_cargo_especifico(variable_valor('ID_CARGO_EXPERTO_BECAS'))
    es_decano = persona.tiene_cargo_especifico(variable_valor('ID_PERSONA_DECINV'))
    es_vicerrector = persona.tiene_cargo_especifico(variable_valor('ID_CARGO_VICERRECTOR_INV'))
    es_tecnico = persona.tiene_cargo_especifico(variable_valor('ID_CARGO_TECNICO_INV'))

    if not es_expertobecas and not es_decano and not es_vicerrector and not es_tecnico:
        return HttpResponseRedirect("/?info=Usted no tiene permitido el acceso al módulo.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addconvocatoria':
            try:
                f = ConvocatoriaBecaForm(request.POST, request.FILES)

                archivoresolucion = request.FILES['archivoresolucion']
                archivoconvocatoria = request.FILES['archivoconvocatoria']

                descripcionarchivo = 'Archivo Resolución OCS'
                resp = validar_archivo(descripcionarchivo, archivoresolucion, ['pdf'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                descripcionarchivo = 'Archivo Convocatoria'
                resp = validar_archivo(descripcionarchivo, archivoconvocatoria, ['pdf'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto los rubros de presupuesto
                rubros = Rubro.objects.filter(status=True, vigente=True).order_by('tipo')

                if not rubros:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No existen rubros de presupuesto para la convocatoria", "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    # Validaciones
                    if Convocatoria.objects.filter(status=True, descripcion__icontains=f.cleaned_data['descripcion'].strip()).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La convocatoria para becas ya ha sido ingresada", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['finpos'] <= f.cleaned_data['iniciopos']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de postulación debe ser mayor a la fecha de inicio de postulación ", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['inicioveri'] <= f.cleaned_data['iniciopos']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de inicio de verificación de requisitos debe ser mayor a la fecha de inicio de postulación", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['finveri'] <= f.cleaned_data['inicioveri']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de verificación de requisitos debe ser mayor a la fecha de inicio de verificación de requisitos", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['iniciosel'] <= f.cleaned_data['iniciopos']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de inicio de calificacion y selección debe ser mayor a la fecha de inicio de postulación", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['finsel'] <= f.cleaned_data['iniciosel']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de calificacion y selección debe ser mayor a la fecha de inicio de de calificacion y selección", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['inicioadj'] <= f.cleaned_data['iniciopos']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de inicio de adjudicación debe ser mayor a la fecha de inicio de postulación", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['finadj'] <= f.cleaned_data['inicioadj']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de adjudicación debe ser mayor a la fecha de inicio de adjudicación", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['inicionoti'] <= f.cleaned_data['iniciopos']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de inicio de notificación debe ser mayor a la fecha de inicio de postulación", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['finnoti'] <= f.cleaned_data['inicionoti']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de notificación debe ser mayor a la fecha de inicio de notificación", "showSwal": "True", "swalType": "warning"})

                    requisitos = json.loads(request.POST['lista_items1'])

                    archivoresolucion._name = generar_nombre("resolucionocs", archivoresolucion._name)
                    archivoconvocatoria._name = generar_nombre("convocatoria", archivoconvocatoria._name)

                    # Obtengo estado PUBLICADO
                    estado = obtener_estado_solicitud(9, 10)

                    # Guardo la convocatoria
                    convocatoria = Convocatoria(
                        descripcion=f.cleaned_data['descripcion'].strip().upper(),
                        iniciopos=f.cleaned_data['iniciopos'],
                        finpos=f.cleaned_data['finpos'],
                        # mensajepos=f.cleaned_data['mensajepos'],
                        inicioveri=f.cleaned_data['inicioveri'],
                        finveri=f.cleaned_data['finveri'],
                        # mensajeveri=f.cleaned_data['mensajeveri'],
                        iniciosel=f.cleaned_data['iniciosel'],
                        finsel=f.cleaned_data['finsel'],
                        # mensajesel=f.cleaned_data['mensajesel'],
                        inicioadj=f.cleaned_data['inicioadj'],
                        finadj=f.cleaned_data['finadj'],
                        # mensajeadj=f.cleaned_data['mensajeadj'],
                        inicionoti=f.cleaned_data['inicionoti'],
                        finnoti=f.cleaned_data['finnoti'],
                        # mensajenoti=f.cleaned_data['mensajenoti'],
                        vigente=True,
                        archivoresolucion=archivoresolucion,
                        archivoconvocatoria=archivoconvocatoria,
                        estado=estado
                    )
                    convocatoria.save(request)

                    # Guardo los requisitos para la convocatoria
                    secuencia = 1
                    for requisito in requisitos:
                        requisitoconvocatoria = RequisitoConvocatoria(
                            convocatoria=convocatoria,
                            requisito_id=requisito['id'],
                            requierearchivo=requisito['valor'],
                            secuencia=secuencia
                        )
                        requisitoconvocatoria.save(request)
                        secuencia += 1

                    # Guardo los rubros de la convocatoria
                    secuencia = 1
                    for rubro in rubros:
                        rubroconvocatoria = RubroConvocatoria(
                            convocatoria=convocatoria,
                            rubro=rubro,
                            secuencia=secuencia
                        )
                        rubroconvocatoria.save(request)
                        secuencia += 1

                    # Guardo los documentos asociados a la convocatoria
                    for documento in Documento.objects.filter(status=True, vigente=True).order_by('id'):
                        documentoconvocatoria = DocumentoConvocatoria(
                            convocatoria=convocatoria,
                            documento=documento
                        )
                        documentoconvocatoria.save(request)

                    # Guardo el recorrido
                    recorrido = RecorridoRegistro(
                        tiporegistro=1,
                        registroid=convocatoria.id,
                        fecha=datetime.now().date(),
                        departamento=persona.mi_cargo_actual().unidadorganica,
                        persona=persona,
                        observacion=estado.observacion,
                        estado=estado
                    )
                    recorrido.save(request)

                    log(f'{persona} convocatoria de becas para docentes {convocatoria}', request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    for k, v in f.errors.items():
                        raise NameError(k + ', ' + v[0])
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editconvocatoria':
            try:
                f = ConvocatoriaBecaForm(request.POST, request.FILES)

                archivoresolucion = archivoconvocatoria = None

                if 'archivoresolucion' in request.FILES:
                    archivoresolucion = request.FILES['archivoresolucion']
                    descripcionarchivo = 'Archivo Resolución OCS'
                    resp = validar_archivo(descripcionarchivo, archivoresolucion, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivoconvocatoria' in request.FILES:
                    archivoconvocatoria = request.FILES['archivoconvocatoria']
                    descripcionarchivo = 'Archivo Convocatoria'
                    resp = validar_archivo(descripcionarchivo, archivoconvocatoria, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    if Convocatoria.objects.filter(status=True, descripcion__icontains=f.cleaned_data['descripcion'].strip()).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La convocatoria para becas ya ha sido ingresada", "showSwal": "True", "swalType": "warning"})

                    # Consultar la convocatoria
                    convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.POST['id'])))

                    # Validaciones
                    if f.cleaned_data['finpos'] <= f.cleaned_data['iniciopos']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de postulación debe ser mayor a la fecha de inicio de postulación ", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['finveri'] <= f.cleaned_data['inicioveri']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de verificación de requisitos debe ser mayor a la fecha de inicio de verificación de requisitos", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['iniciosel'] <= f.cleaned_data['iniciopos']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de inicio de calificacion y selección debe ser mayor a la fecha de inicio de postulación", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['finsel'] <= f.cleaned_data['iniciosel']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de calificacion y selección debe ser mayor a la fecha de inicio de de calificacion y selección", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['inicioadj'] <= f.cleaned_data['iniciopos']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de inicio de adjudicación debe ser mayor a la fecha de inicio de postulación", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['finadj'] <= f.cleaned_data['inicioadj']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de adjudicación debe ser mayor a la fecha de inicio de adjudicación", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['inicionoti'] <= f.cleaned_data['iniciopos']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de inicio de notificación debe ser mayor a la fecha de inicio de postulación", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['finnoti'] <= f.cleaned_data['inicionoti']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de notificación debe ser mayor a la fecha de inicio de notificación", "showSwal": "True", "swalType": "warning"})

                    requisitos = json.loads(request.POST['lista_items1'])

                    # Actualizar el registro
                    convocatoria.descripcion = f.cleaned_data['descripcion'].strip().upper()
                    convocatoria.iniciopos = f.cleaned_data['iniciopos']
                    convocatoria.finpos = f.cleaned_data['finpos']
                    # convocatoria.mensajepos = f.cleaned_data['mensajepos']
                    convocatoria.inicioveri = f.cleaned_data['inicioveri']
                    convocatoria.finveri = f.cleaned_data['finveri']
                    # convocatoria.mensajeveri = f.cleaned_data['mensajeveri']
                    convocatoria.iniciosel = f.cleaned_data['iniciosel']
                    convocatoria.finsel = f.cleaned_data['finsel']
                    # convocatoria.mensajesel = f.cleaned_data['mensajesel']
                    convocatoria.inicioadj = f.cleaned_data['inicioadj']
                    convocatoria.finadj = f.cleaned_data['finadj']
                    # convocatoria.mensajeadj = f.cleaned_data['mensajeadj']
                    convocatoria.inicionoti = f.cleaned_data['inicionoti']
                    convocatoria.finnoti = f.cleaned_data['finnoti']
                    # convocatoria.mensajenoti = f.cleaned_data['mensajenoti']

                    if archivoresolucion:
                        archivoresolucion._name = generar_nombre("resolucionocs", archivoresolucion._name)
                        convocatoria.archivoresolucion = archivoresolucion

                    if archivoconvocatoria:
                        archivoconvocatoria._name = generar_nombre("convocatoria", archivoconvocatoria._name)
                        convocatoria.archivoconvocatoria = archivoconvocatoria

                    convocatoria.save(request)

                    # Actualizo los requisitos para la convocatoria
                    for requisito in requisitos:
                        requisitoconvocatoria = RequisitoConvocatoria.objects.get(convocatoria=convocatoria, requisito_id=requisito['id'])
                        requisitoconvocatoria.requierearchivo = requisito['valor']
                        requisitoconvocatoria.save(request)

                    log(f'{persona} editó de becas para docentes {convocatoria}', request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    for k, v in f.errors.items():
                        raise NameError(k + ', ' + v[0])
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'asignarvigente':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el requisito
                requisito = Requisito.objects.get(pk=int(encrypt(request.POST['id'])))
                vigente = request.POST['valor'] == 'S'

                # Actualizar el registro
                requisito.vigente = vigente
                requisito.save(request)

                log(f'{persona} asignó estado {"vigente" if vigente else "no vigente"} al requisito {requisito}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addrequisito':
            try:
                if 'descripcion' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                numero = request.POST['numero'].strip()
                descripcion = request.POST['descripcion'].strip()

                # Validaciones
                if Requisito.objects.values("id").filter(status=True, descripcion__icontains=descripcion, vigente=True).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El requisito para beca está repetido", "showSwal": "True", "swalType": "warning"})

                # Guardar el registro
                requisitobeca = Requisito(
                    tipo=1,
                    numero=numero,
                    descripcion=descripcion,
                    vigente=True
                )
                requisitobeca.save(request)

                log(f'{persona} agregó requisito de becas para docentes {requisitobeca}', request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editrequisito':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                numero = request.POST['numeroe'].strip()
                descripcion = request.POST['descripcione'].strip()

                # Validaciones
                if Requisito.objects.values("id").filter(status=True, descripcion__icontains=descripcion, vigente=True).exclude(pk=int(encrypt(request.POST['id']))).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El requisito para beca está repetido", "showSwal": "True", "swalType": "warning"})

                # Consultar el requisito
                requisitobeca = Requisito.objects.get(pk=int(encrypt(request.POST['id'])))

                # Actualizar el registro
                requisitobeca.numero = numero
                requisitobeca.descripcion = descripcion
                requisitobeca.save(request)

                log(f'{persona} editó requisito de becas para docentes {requisitobeca}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'verificarconvocatoria':
            try:
                if not 'idconvocatoria' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                # Consultar convocatoria
                convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.POST['idconvocatoria'])))

                estadooriginal = request.POST['estadooriginal']
                estadoasignado = request.POST['estado']
                observacion = request.POST['observacion'].strip()

                # Verificar que el estado actual de la convocatoria sea el mismo de la pantalla
                if convocatoria.estado.id != int(estadooriginal):
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede guardar debido a que el estado actual ha sido actualizado por otro usuario", "showSwal": "True", "swalType": "warning"})

                # Obtengo el estado a asignar
                estado = obtener_estado_solicitud_por_id(estadoasignado)

                # Actualizo el estado de la convocatoria
                convocatoria.estado = estado
                if estado.valor == 10:
                    convocatoria.publicada = True

                convocatoria.save(request)

                if estado.valor in [2, 4, 6, 8, 10] and not observacion:
                    observacion = estado.observacion

                # Guardo el recorrido
                recorrido = RecorridoRegistro(
                    tiporegistro=1,
                    registroid=convocatoria.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=observacion,
                    estado=estado
                )
                recorrido.save(request)

                valorestado = estado.valor
                if valorestado in [3, 8]:  # Rechazo Experto o Autorizado Rector
                    personadestinatario = analista_investigacion()
                elif valorestado == 5:  # Rechazo Coordinador
                    personadestinatario = experto_investigacion()
                elif valorestado in [2, 7]:  # Revisado Experto o Rechazado Vicerrector
                    personadestinatario = coordinador_investigacion()
                elif valorestado in [4, 9]:  # Validado Coord. Inv o Rechazado Rector
                    personadestinatario = vicerrector_investigacion_posgrado()
                elif valorestado == 6:  # Aprobado Vicerrector
                    personadestinatario = rector_institucion()

                if valorestado == 2:
                    estadoconv = 'REVISADO'
                    textoestado = 'validación'
                elif valorestado == 4:
                    estadoconv = 'VALIDADO'
                    textoestado = 'aprobación'
                elif valorestado == 6:
                    estadoconv = 'APROBADO'
                    textoestado = 'autorización'
                elif valorestado == 8:
                    estadoconv = 'AUTORIZADO'
                    textoestado = 'publicación'
                elif valorestado != 10:
                    estadoconv = 'RECHAZADO'
                    textoestado = 'verificación y corrección'

                if valorestado != 10:  # Si no es publicado
                    # Envío de e-mail de notificación al usuario que debe asignar el siguiente estado
                    listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                    # E-mail del destinatario

                    # lista_email_envio = personadestinatario.lista_emails_envio()
                    lista_email_envio = ['ivan_saltos_medina@hotmail.com']
                    lista_email_cco = ['isaltosm@unemi.edu.ec']
                    lista_archivos_adjuntos = []

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                    asuntoemail = "Actualización de estado en Convocatoria Becas de Docentes"
                    titulo = "Convocatoria Beca Docente"

                    # send_html_mail(asuntoemail,
                    #                "emails/convocatoriabecadocente.html",
                    #                {'sistema': u'SGA - UNEMI',
                    #                 'titulo': titulo,
                    #                 'fecha': fechaenvio,
                    #                 'hora': horaenvio,
                    #                 'saludo': 'Estimada' if personadestinatario.sexo_id == 1 else 'Estimado',
                    #                 'nombrepersona': personadestinatario.nombre_completo_inverso(),
                    #                 'nombreconvocatoria': convocatoria.descripcion,
                    #                 'estado': estadoconv,
                    #                 'estadosiguiente': textoestado,
                    #                 'observaciones': observacion,
                    #                 },
                    #                lista_email_envio,
                    #                lista_email_cco,
                    #                lista_archivos_adjuntos,
                    #                cuenta=CUENTAS_CORREOS[cuenta][1]
                    #                )

                log(u'%s asignó estado %s a convocatoria de becas para docentes: %s' % (persona, estado.descripcion, convocatoria), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'habilitaredicion':
            try:
                # Consulto la postulación
                postulacion = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que tenga estado SOLICITADO
                if not postulacion.estado.valor == 2:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el Registro porque no tiene estado SOLICITADO", "showSwal": "True", "swalType": "warning"})

                # Obtengo estado EN EDICIÓN
                estado = obtener_estado_solicitud(13, 1)

                # Actualizo la postulación
                postulacion.estado = estado
                postulacion.observacion = ""
                postulacion.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion='SOLICITUD EN EDICIÓN',
                    estado=estado
                )
                recorrido.save(request)

                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                # E-mail del destinatario
                lista_email_envio = postulacion.profesor.persona.lista_emails_envio()
                # lista_email_envio = ['isaltosm@unemi.edu.ec']
                lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                lista_archivos_adjuntos = []

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                asuntoemail = "Habilitación Edición Registro de Postulación a Beca Docente"
                titulo = "Postulación Beca Docente"
                tiponotificacion = "HABEDI"

                send_html_mail(asuntoemail,
                               "emails/postulacionbecadocente.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimada' if postulacion.profesor.persona.sexo_id == 1 else 'Estimado',
                                'nombrepersona': postulacion.profesor.persona.nombre_completo_inverso(),
                                'postulacion': postulacion
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_archivos_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s habilitó edición de postulación para beca docente: %s' % (persona, postulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'revisarpostulacion':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                # Consulto la postulación
                postulacion = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que el estado actual no sea EN EDICIÓN
                if postulacion.estado.valor == 1:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"No se puede guardar debido a que la postulación se encuentra EN EDICIÓN por parte del docente", "showSwal": "True", "swalType": "warning"})

                # Obtengo los valores de los campos del formulario
                estadosolicitud = request.POST['estadosolicitud']
                criteriojuridico = True if 'criteriojuridico' in request.POST else False
                observacionsol = request.POST['observacion'] if 'observacion' in request.POST else ''

                # Obtengo los valores de los switch de requisitos y otros documentos
                requisitos = json.loads(request.POST['lista_items1'])
                otrosdocumentos = json.loads(request.POST['lista_items2'])

                # Obtiene los valores de los arreglos
                iddetallesreq = request.POST.getlist('iddetallereq[]')  # IDs detalles de requisitos
                observacionesreq = request.POST.getlist('observacionreq[]')  # Observaciones detalles de requisitos
                iddocumentos = request.POST.getlist('iddetalledoc[]')  # IDs detalles de otros documentos
                observacionesdoc = request.POST.getlist('observacionotrodoc[]')  # Observaciones detalles de otros documentos

                # Obtengo estado para el registro
                estado = obtener_estado_solicitud(13, estadosolicitud)

                # Actualizar la solicitud
                postulacion.validada = True
                if estado.valor == 3:
                    postulacion.estadovalidacion = 1
                elif estado.valor == 4:
                    postulacion.estadovalidacion = 2
                else:
                    postulacion.estadovalidacion = 3

                postulacion.observacion = observacionsol
                postulacion.criteriojuridico = criteriojuridico
                postulacion.estado = estado
                postulacion.save(request)

                # Actualizar estados de los requisitos
                for iddetalle, requisito, observacion in zip(iddetallesreq, requisitos, observacionesreq):
                    # Consulto el detalle de requisito
                    solicitudrequisito = SolicitudRequisito.objects.get(pk=iddetalle)

                    # Actualizo el detalle
                    solicitudrequisito.personarevisa = persona
                    solicitudrequisito.fecharevisa = datetime.now()
                    solicitudrequisito.observacion = observacion
                    solicitudrequisito.estado = 2 if requisito['valor'] is True else 4
                    solicitudrequisito.save(request)

                # Actualizar estados de los otros documentos
                for iddetalle, documento, observacion in zip(iddocumentos, otrosdocumentos, observacionesdoc):
                    # Consulto el detalle del documento
                    solicituddocumento = SolicitudDocumento.objects.get(pk=iddetalle)

                    # Actualizo el detalle
                    solicituddocumento.personarevisa = persona
                    solicituddocumento.fecharevisa = datetime.now()
                    solicituddocumento.observacion = observacion
                    solicituddocumento.estado = 2 if documento['valor'] is True else 4
                    solicituddocumento.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=observacionsol if observacionsol else estado.observacion,
                    estado=estado
                )
                recorrido.save(request)

                tiponotificacion = ""
                # Si es rechazado o presenta novedades se debe notificar al solicitante
                if estado.valor in [4, 6]:
                    tiponotificacion = "NOVEDAD"
                else:
                    # Si no requiere criterio jurídico
                    if not criteriojuridico:
                        # Obtengo estado INFORME FACTIBILIDAD PENDIENTE DE GENERAR POR ANALISTA DE INVESTIGACIÓN
                        estado = obtener_estado_solicitud(13, 11)

                        # Actualizo la postulación
                        postulacion.observacion = estado.observacion
                        postulacion.estado = estado
                        postulacion.save(request)

                        # Guardo el recorrido de la solicitud
                        recorrido = RecorridoRegistro(
                            tiporegistro=2,
                            registroid=postulacion.id,
                            fecha=datetime.now().date(),
                            departamento=persona.mi_cargo_actual().unidadorganica,
                            persona=persona,
                            observacion=estado.observacion,
                            estado=estado
                        )
                        recorrido.save(request)
                    else:
                        # Obtengo estado INFORME JURÍDICO PENDIENTE DE REGISTRAR
                        estado = obtener_estado_solicitud(13, 7)

                        # Actualizo la postulación
                        postulacion.observacion = estado.observacion
                        postulacion.estado = estado
                        postulacion.save(request)

                        # Guardo el recorrido de la solicitud
                        recorrido = RecorridoRegistro(
                            tiporegistro=2,
                            registroid=postulacion.id,
                            fecha=datetime.now().date(),
                            departamento=persona.mi_cargo_actual().unidadorganica,
                            persona=persona,
                            observacion=estado.observacion,
                            estado=estado
                        )
                        recorrido.save(request)

                # Consultos los detalles de requisitos y otros documentos de la postulación para enviar en el correo
                requisitos = postulacion.requisitos()
                documentos = postulacion.documentos()

                # Notificar por e-mail
                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                # E-mail del destinatario solicitante
                # lista_email_envio = postulacion.profesor.persona.lista_emails_envio()
                lista_email_envio = ['isaltosm@unemi.edu.ec']
                lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                lista_archivos_adjuntos = []

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                # Si se asignó estado de RECHAZO o NOVEDAD solo se notifica al solicitante
                if tiponotificacion == 'NOVEDAD':
                    asuntoemail = "Postulación a Beca Docente Rechazada" if estado.valor == 6 else "Novedades con Postulación a Beca Docente"
                    titulo = "Postulación Beca Docente"
                    tiponotificacion = "RECHSOL" if estado.valor == 6 else "NOVSOL"

                    send_html_mail(asuntoemail,
                                   "emails/postulacionbecadocente.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'tiponotificacion': tiponotificacion,
                                    'saludo': 'Estimada' if postulacion.profesor.persona.sexo_id == 1 else 'Estimado',
                                    'nombrepersona': postulacion.profesor.persona.nombre_completo_inverso(),
                                    'postulacion': postulacion,
                                    'requisitos': requisitos,
                                    'documentos': documentos
                                    },
                                   lista_email_envio,
                                   lista_email_cco,
                                   lista_archivos_adjuntos,
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                else:
                    asuntoemail = "Postulación a Beca Docente Aceptada"
                    titulo = "Postulación Beca Docente"
                    tiponotificacion = "ACEPTADA"

                    send_html_mail(asuntoemail,
                                   "emails/postulacionbecadocente.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'tiponotificacion': tiponotificacion,
                                    'saludo': 'Estimada' if postulacion.profesor.persona.sexo_id == 1 else 'Estimado',
                                    'nombrepersona': postulacion.profesor.persona.nombre_completo_inverso(),
                                    'postulacion': postulacion,
                                    'requisitos': requisitos,
                                    'documentos': documentos
                                    },
                                   lista_email_envio,
                                   lista_email_cco,
                                   lista_archivos_adjuntos,
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                    # Si requiere criterio jurídico se debe notificar a la Dirección Jurídica
                    if criteriojuridico:
                        # E-mail de la dirección jurídica
                        # lista_email_envio = ['correo12345@unemi.edu.ec']
                        lista_email_envio = ['isaltosm@unemi.edu.ec']

                        asuntoemail = "Requerimiento de Informe Jurídico para Postulación a Beca Docente"
                        titulo = "Postulación Beca Docente"
                        tiponotificacion = "REQJUR"

                        send_html_mail(asuntoemail,
                                       "emails/postulacionbecadocente.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'titulo': titulo,
                                        'fecha': fechaenvio,
                                        'hora': horaenvio,
                                        'tiponotificacion': tiponotificacion,
                                        # 'saludo': 'Estimada' if postulacion.profesor.persona.sexo_id == 1 else 'Estimado',
                                        'saludo': 'Estimados',
                                        'genpersona': 'de la docente' if postulacion.profesor.persona.sexo_id == 1 else 'del docente',
                                        'nombrepersona': postulacion.profesor.persona.nombre_completo_inverso(),
                                        'postulacion': postulacion,
                                        'requisitos': requisitos,
                                        'documentos': documentos
                                        },
                                       lista_email_envio,
                                       lista_email_cco,
                                       lista_archivos_adjuntos,
                                       cuenta=CUENTAS_CORREOS[cuenta][1]
                                       )

                log(u'%s asignó estado %s a postulación de beca: %s' % (persona, estado.descripcion, postulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addinformeotorgamiento':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                # Consulto la postulación
                postulacion = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))

                # Obtengo los valores de los campos del formulario
                if postulacion.profesor.persona.sexo.id == 1:
                    objeto = "Informe sobre la revisión de los requisitos para postulación a beca docente " + postulacion.convocatoria.descripcion + " de la profesora " + postulacion.profesor.persona.nombre_completo_inverso() + "."
                else:
                    objeto = "Informe sobre la revisión de los requisitos para postulación a beca docente " + postulacion.convocatoria.descripcion + " del profesor " + postulacion.profesor.persona.nombre_completo_inverso() + "."

                antecedente = remover_atributo_style_html(request.POST['antecedente'])
                conclusion = remover_atributo_style_html(request.POST['conclusion'])
                recomendacion = remover_atributo_style_html(request.POST['recomendacion'])

                # Obtengo los valores del detalle de anexos
                nfilas_ca_evi = json.loads(request.POST['lista_items1'])  # Números de filas que tienen lleno el campo archivo en detalle de evidencias
                nfilas = request.POST.getlist('nfila_evidencia[]')  # Todos los número de filas del detalle de anexos
                descripciones = request.POST.getlist('descripcion_evidencia[]')  # Todas las descripciones
                archivos = request.FILES.getlist('archivo_evidencia[]')  # Todos los archivos
                fechasgenera = request.POST.getlist('fecha_genera[]')  # Todas las fechas de generación

                # Valido los archivos cargados en el detalle de anexos
                for nfila, archivo in zip(nfilas_ca_evi, archivos):
                    descripcionarchivo = 'Anexo'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                # Obtengo estado INFORME DE FACTIBILIDAD GENERADO Y PENDIENTE DE CARGAR FIRMADO
                estado = obtener_estado_solicitud(13, 12)

                # Datos de personas que intervienen en el informe
                destinatario = vicerrector_investigacion_posgrado()
                cargodestinatario = destinatario.mi_cargo_actual_docente().denominacionpuesto if destinatario.mi_cargo_actual_docente() else None
                remitente = coordinador_investigacion()
                cargoremitente = remitente.mi_cargo_actual().denominacionpuesto
                elabora = persona
                cargoelabora = persona.mi_cargo_actual().denominacionpuesto
                verifica = experto_becas_docentes()
                cargoverifica = verifica.mi_cargo_actual().denominacionpuesto
                aprueba = remitente
                cargoaprueba = cargoremitente

                # Actualizar la solicitud
                postulacion.informeogen = True
                postulacion.estado = estado
                postulacion.save(request)

                # Obtener secuencia del informe
                secuencia = secuencia_informe_factibilidad(1)
                numero = "ITI-CI–CB-" + str(secuencia).zfill(3) + "-" + str(datetime.now().year)

                # Crear el registro del informe
                informe = InformeFactibilidad(
                    solicitud=postulacion,
                    tipo=1,
                    secuencia=secuencia,
                    fecha=datetime.now().date(),
                    numero=numero,
                    remitente=remitente,
                    cargoremitente=cargoremitente,
                    destinatario=destinatario,
                    cargodestinatario=cargodestinatario,
                    objeto=objeto,
                    antecedente=antecedente,
                    motivaciontecnica='',
                    conclusion=conclusion,
                    recomendacion=recomendacion,
                    elabora=elabora,
                    cargoelabora=cargoelabora,
                    verifica=verifica,
                    cargoverifica=cargoverifica,
                    aprueba=aprueba,
                    cargoaprueba=cargoaprueba,
                    vigente=True,
                    estado=1
                )
                informe.save(request)

                # Guardo los anexos del informe
                for descripcion, archivo, fechagenera in zip(descripciones, archivos, fechasgenera):
                    fecha = datetime.strptime(fechagenera, '%Y-%m-%d').date()
                    pdf2ReaderEvi = PyPDF2.PdfFileReader(archivo)

                    archivoreg = archivo
                    archivoreg._name = generar_nombre("anexoinformeotorgamiento", archivoreg._name)

                    anexoinforme = InformeFactibilidadAnexo(
                        informe=informe,
                        descripcion=descripcion.strip(),
                        fecha=fecha,
                        archivo=archivoreg,
                        numeropagina=pdf2ReaderEvi.numPages
                    )
                    anexoinforme.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=estado.observacion,
                    estado=estado
                )
                recorrido.save(request)

                log(u'%s agregó informe de factibilidad de otorgamiento %s a postulación de beca: %s' % (persona, informe.numero, postulacion), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True, "id": request.POST['id']})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editinformeotorgamiento':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                # Consulto el informe
                informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.POST['id'])))
                postulacion = informe.solicitud

                # Obtengo los valores de los campos del formulario
                antecedente = remover_atributo_style_html(request.POST['antecedente'])
                conclusion = remover_atributo_style_html(request.POST['conclusion'])
                recomendacion = remover_atributo_style_html(request.POST['recomendacion'])

                # Obtengo los valores del detalle de anexos
                nfilas_ca_evi = json.loads(request.POST['lista_items1'])  # Números de filas que tienen lleno el campo archivo en detalle de evidencias
                nfilas = request.POST.getlist('nfila_evidencia[]')  # Todos los número de filas del detalle de anexos
                idsanexos = request.POST.getlist('idregistro[]')  # Todos los ids de detalle de anexos
                descripciones = request.POST.getlist('descripcion_evidencia[]')  # Todas las descripciones
                archivos = request.FILES.getlist('archivo_evidencia[]')  # Todos los archivos
                fechasgenera = request.POST.getlist('fecha_genera[]')  # Todas las fechas de generación
                anexosseliminados = json.loads(request.POST['lista_items2']) if 'lista_items2' in request.POST else []

                # Valido los archivos cargados en el detalle de anexos
                for nfila, archivo in zip(nfilas_ca_evi, archivos):
                    descripcionarchivo = 'Anexo'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                # En caso que el estado sea POR REVISAR, NOVEDAD o CARGADO, se debe actualizar los estados de la postulacion
                # actualizarpostulacion = informe.estado in [1, 2, 4, 5]
                actualizarpostulacion = informe.estado in [2, 5, 6]

                if actualizarpostulacion:
                    # Obtengo estado INFORME DE FACTIBILIDAD GENERADO Y PENDIENTE DE CARGAR FIRMADO
                    estado = obtener_estado_solicitud(13, 12)

                    # Actualizar la solicitud
                    postulacion.estadoinformeo = None
                    postulacion.estado = estado
                    postulacion.save(request)

                # Actualizo el registro del informe
                informe.antecedente = antecedente
                informe.conclusion = conclusion
                informe.recomendacion = recomendacion
                informe.archivo = None
                informe.archivofirmado = None
                informe.impreso = False
                informe.firmaelabora = False
                informe.firmaverifica = False
                informe.firmaaprueba = False
                informe.estado = 1
                informe.save(request)

                # Guardo los anexos del informe
                for idanexo, nfila, descripcion, fechagenera in zip(idsanexos, nfilas, descripciones, fechasgenera):
                    fecha = datetime.strptime(fechagenera, '%Y-%m-%d').date()
                    # Si es registro nuevo
                    if int(idanexo) == 0:
                        anexoinforme = InformeFactibilidadAnexo(
                            informe=informe,
                            descripcion=descripcion.strip(),
                            fecha=fecha
                        )
                    else:
                        anexoinforme = InformeFactibilidadAnexo.objects.get(pk=idanexo)
                        anexoinforme.descripcion = descripcion.strip()
                        anexoinforme.fecha = fecha

                    anexoinforme.save(request)

                    # Guardo el archivo del anexo
                    for nfilaarchi, archivo in zip(nfilas_ca_evi, archivos):
                        # Si la fila de la descripcion es igual a la fila que contiene archivo
                        if int(nfilaarchi['nfila']) == int(nfila):
                            pdf2ReaderEvi = PyPDF2.PdfFileReader(archivo)

                            archivoreg = archivo
                            archivoreg._name = generar_nombre("anexoinformeotorgamiento", archivoreg._name)

                            # actualizo campo archivo del registro creado
                            anexoinforme.archivo = archivoreg
                            anexoinforme.numeropagina = pdf2ReaderEvi.numPages
                            anexoinforme.save(request)
                            break

                # Elimino los anexos que se borraron del detalle
                if anexosseliminados:
                    for anexo in anexosseliminados:
                        anexoinforme = InformeFactibilidadAnexo.objects.get(pk=anexo['idreg'])
                        anexoinforme.status = False
                        anexoinforme.save(request)

                if actualizarpostulacion:
                    # Guardo el recorrido de la solicitud
                    recorrido = RecorridoRegistro(
                        tiporegistro=2,
                        registroid=postulacion.id,
                        fecha=datetime.now().date(),
                        departamento=persona.mi_cargo_actual().unidadorganica,
                        persona=persona,
                        observacion=estado.observacion,
                        estado=estado
                    )
                    recorrido.save(request)

                log(u'%s editó informe de factibilidad de otorgamiento %s a postulación de beca: %s' % (persona, informe.numero, postulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True, "id": request.POST['id']})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'informeotorgamientopdf':
            try:
                data = {}

                informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.POST['id'])))

                data['informe'] = informe
                data['postulacion'] = postulacion = informe.solicitud

                data['vicerrector'] = vicerrector_investigacion_posgrado()
                data['coordinador'] = coordinador_investigacion()
                data['analista'] = analista_investigacion()
                data['experto'] = experto_investigacion()

                data['anio1'] = anio1 = postulacion.inicio.year
                data['presupuesto1'] = postulacion.presupuesto_solicitud().total_anio(anio1)

                anexos = []
                numero = 0
                anexos_requisitos = postulacion.requisitos()
                anexos_documentos = postulacion.documentos()
                anexos_adicionales = informe.anexos()

                for anexo in anexos_requisitos:
                    numero += 1
                    anexos.append({
                        "numero": numero,
                        "descripcion": anexo.requisito.descripcion,
                        "fecha": anexo.fecha_creacion,
                        "numeropagina": anexo.numeropagina
                    })

                for anexo in anexos_documentos:
                    numero += 1
                    anexos.append({
                        "numero": numero,
                        "descripcion": anexo.documento.descripcion,
                        "fecha": anexo.fecha_creacion,
                        "numeropagina": anexo.numeropagina
                    })

                for anexo in anexos_adicionales:
                    numero += 1
                    anexos.append({
                        "numero": numero,
                        "descripcion": anexo.descripcion,
                        "fecha": anexo.fecha,
                        "numeropagina": anexo.numeropagina
                    })

                data['requisitos'] = anexos_requisitos
                data['anexos'] = anexos

                data['presupuesto'] = presupuesto = postulacion.presupuesto_solicitud()
                data['cantidadperiodos'] = cantidadperiodos = presupuesto.numeroperiodo

                listaanios = []
                anioi = postulacion.inicio.year
                aniof = postulacion.fin.year
                total = (aniof - anioi) + 1

                for n in range(total):
                    listaanios.append(anioi)
                    anioi += 1

                data['colspancab'] = (cantidadperiodos * 2) + 3
                data['anios'] = listaanios
                data['rubros'] = postulacion.rubros()

                # Creacion de los archivos por separado
                directorio = SITE_STORAGE + '/media/becadocente/informes'
                try:
                    os.stat(directorio)
                except:
                    os.mkdir(directorio)

                # Archivo de la parte 1 del informe
                nombrearchivo = 'informeparte1_' + str(informe.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                valida = convert_html_to_pdf(
                    'adm_becadocente/informeotorgamientopdf.html',
                    {'pagesize': 'A4', 'data': data},
                    nombrearchivo,
                    directorio
                )

                if not valida:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el documento de la parte 1 del informe. [%s]", "showSwal": "True", "swalType": "error"})

                archivo1 = directorio + "/" + nombrearchivo

                # Leer los archivos
                pdf1Reader = PyPDF2.PdfFileReader(archivo1)

                # Crea un nuevo objeto PdfFileWriter que representa un documento PDF en blanco
                pdfWriter = PyPDF2.PdfFileWriter()

                # Recorre todas las páginas del documento 1
                for pageNum in range(pdf1Reader.numPages):
                    pageObj = pdf1Reader.getPage(pageNum)
                    pdfWriter.addPage(pageObj)

                # Recorro el detalle de requisitos
                for evidencia in anexos_requisitos:
                    archivoevidencia = SITE_STORAGE + evidencia.archivo.url  # Archivo pdf cargado
                    pdf2ReaderEvi = PyPDF2.PdfFileReader(archivoevidencia)

                    # Recorre todas las páginas del documento de evidencia: pdf2ReaderEvi
                    for pageNum in range(pdf2ReaderEvi.numPages):
                        pageObj = pdf2ReaderEvi.getPage(pageNum)
                        pdfWriter.addPage(pageObj)

                # Recorro el detalle de documentos
                for evidencia in anexos_documentos:
                    archivoevidencia = SITE_STORAGE + evidencia.archivofirmado.url  # Archivo pdf cargado
                    pdf2ReaderEvi = PyPDF2.PdfFileReader(archivoevidencia)

                    # Recorre todas las páginas del documento de evidencia: pdf2ReaderEvi
                    for pageNum in range(pdf2ReaderEvi.numPages):
                        pageObj = pdf2ReaderEvi.getPage(pageNum)
                        pdfWriter.addPage(pageObj)

                # Recorro el detalle de anexos adicionales
                for evidencia in informe.anexos():
                    archivoevidencia = SITE_STORAGE + evidencia.archivo.url  # Archivo pdf cargado
                    pdf2ReaderEvi = PyPDF2.PdfFileReader(archivoevidencia)

                    # Recorre todas las páginas del documento de evidencia: pdf2ReaderEvi
                    for pageNum in range(pdf2ReaderEvi.numPages):
                        pageObj = pdf2ReaderEvi.getPage(pageNum)
                        pdfWriter.addPage(pageObj)

                # Luego de haberse copiado todas las paginas de todos los documentos, se las escribe en el documento en blanco
                fecha = datetime.now().date()
                hora = datetime.now().time()
                nombrearchivoresultado = generar_nombre('informeotorgamientobeca', 'informeotorgamientobeca.pdf')
                pdfOutputFile = open(directorio + "/" + nombrearchivoresultado, "wb")
                pdfWriter.write(pdfOutputFile)

                # Borro los documento individuales creados a exepción del archivo del proyecto cargado por el docente
                os.remove(archivo1)

                pdfOutputFile.close()

                # archivo = 'media/becadocente/informes/' + nombrearchivoresultado
                archivo = SITE_STORAGE + '/media/becadocente/informes/' + nombrearchivoresultado

                # Aperturo el archivo generado
                with open(archivo, 'rb') as f:
                    data = f.read()

                buffer = io.BytesIO()
                buffer.write(data)
                pdfcopia = buffer.getvalue()
                buffer.seek(0)
                buffer.close()

                # Extraigo el contenido
                archivocopiado = ContentFile(pdfcopia)
                archivocopiado.name = nombrearchivoresultado

                # Actualizo el informe
                informe.impreso = True
                informe.archivo = archivocopiado
                informe.save(request)

                # Borro el informe creado de manera general, no la del registro
                os.remove(archivo)

                return JsonResponse({"result": "ok", "documento": informe.archivo.url, "id": encrypt(postulacion.id)})
                # return JsonResponse({"result": "ok", "documento": archivo})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el documento del informe. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'subirinformeotorgamiento':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivo = request.FILES['archivoinforme']
                descripcionarchivo = 'Archivo del Informe Firmado'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '10MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                numeropagina = 0
                # Verifica que el archivo no presente problemas
                try:
                    pdf2ReaderEvi = PyPDF2.PdfFileReader(archivo)
                    numeropagina = pdf2ReaderEvi.numPages
                except Exception as ex:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El archivo presenta problemas", "showSwal": "True", "swalType": "warning"})

                # Obtengo estado INFORME DE FACTIBILIDAD CARGADO Y PENDIENTE DE REVISAR POR DOCENTE
                estado = obtener_estado_solicitud(13, 13)

                # Consulto el informe de otorgamiento de beca
                informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.POST['id'])))
                postulacion = informe.solicitud

                archivo._name = generar_nombre("informeotorgamiento", archivo._name)

                # Actualizo el estado de la postulación
                postulacion.estadoinformeo = 3
                postulacion.estado = estado
                postulacion.save(request)

                # Actualizo el informe
                informe.archivo = archivo
                informe.estado = 2
                informe.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=estado.observacion,
                    estado=estado
                )
                recorrido.save(request)

                # Notificar por e-mail
                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                # E-mail del destinatario solicitante
                # lista_email_envio = postulacion.profesor.persona.lista_emails_envio()
                lista_email_envio = ['isaltosm@unemi.edu.ec']
                lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                lista_archivos_adjuntos = [informe.archivo]

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                asuntoemail = "Revisar Informe de factibilidad de otorgamiento de Beca"
                tiponotificacion = "INFBECANL"
                titulo = "Postulación Beca Docente"

                send_html_mail(asuntoemail,
                               "emails/postulacionbecadocente.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimada' if postulacion.profesor.persona.sexo_id == 1 else 'Estimado',
                                'nombrepersona': postulacion.profesor.persona.nombre_completo_inverso(),
                                'postulacion': postulacion
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_archivos_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s subió informe de otorgamiento de beca firmada para la solicitud: %s' % (persona, postulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addinformejuridico':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                # Consulto la postulación
                postulacion = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))

                # Obtengo los valores de los campos del formulario
                objeto = remover_atributo_style_html(request.POST['objeto'])
                antecedente = remover_atributo_style_html(request.POST['antecedente'])
                conclusion = 'Con los antecedentes expuestos, y con base en el principio de legalidad, que hace referencia a la seguridad jurídica que implica que todo acto administrativo debe realizarse conforme a la ley, esta Dirección Jurídica considera que el expediente deberá remitirse al Órgano Colegiado Superior Académico a fin de que avoquen conocimiento y procedan a declarar el otorgamiento de la Beca para la Formación Académica del Docente.'
                motivaciontecnica = remover_atributo_style_html(request.POST['motivaciontecnica'])
                recomendacion = remover_atributo_style_html(request.POST['recomendacion'])

                # Obtengo los valores del detalle de anexos
                nfilas_ca_evi = json.loads(request.POST['lista_items1'])  # Números de filas que tienen lleno el campo archivo en detalle de evidencias
                nfilas = request.POST.getlist('nfila_evidencia[]')  # Todos los número de filas del detalle de anexos
                descripciones = request.POST.getlist('descripcion_evidencia[]')  # Todas las descripciones
                archivos = request.FILES.getlist('archivo_evidencia[]')  # Todos los archivos
                fechasgenera = request.POST.getlist('fecha_genera[]')  # Todas las fechas de generación

                # Valido los archivos cargados en el detalle de anexos
                for nfila, archivo in zip(nfilas_ca_evi, archivos):
                    descripcionarchivo = 'Anexo'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                # Obtengo estado INFORME JURÍDICO REGISTRADO
                estado = obtener_estado_solicitud(13, 8)

                # Datos de personas que intervienen en el informe
                destinatario = postulacion.profesor.persona
                cargodestinatario = destinatario.mi_cargo_actual_docente().denominacionpuesto if destinatario.mi_cargo_actual_docente() else None
                remitente = director_juridico()
                cargoremitente = remitente.mi_cargo_actual().denominacionpuesto
                elabora = persona
                cargoelabora = persona.mi_cargo_actual().denominacionpuesto
                verifica = experto_juridico()
                cargoverifica = verifica.mi_cargo_actual().denominacionpuesto
                aprueba = remitente
                cargoaprueba = cargoremitente

                # Actualizar la solicitud
                postulacion.informejgen = True
                postulacion.estado = estado
                postulacion.save(request)

                # Obtener secuencia del informe
                secuencia = secuencia_informe_factibilidad(2)
                numero = "ITI-AJ–CB-" + str(secuencia).zfill(3) + "-" + str(datetime.now().year)

                # Crear el registro del informe
                informe = InformeFactibilidad(
                    solicitud=postulacion,
                    tipo=2,
                    secuencia=secuencia,
                    fecha=datetime.now().date(),
                    numero=numero,
                    remitente=remitente,
                    cargoremitente=cargoremitente,
                    destinatario=destinatario,
                    cargodestinatario=cargodestinatario,
                    objeto=objeto,
                    antecedente=antecedente,
                    motivaciontecnica=motivaciontecnica,
                    conclusion=conclusion,
                    recomendacion=recomendacion,
                    elabora=elabora,
                    cargoelabora=cargoelabora,
                    verifica=verifica,
                    cargoverifica=cargoverifica,
                    aprueba=aprueba,
                    cargoaprueba=cargoaprueba,
                    vigente=True,
                    estado=1
                )
                informe.save(request)

                # Guardo los anexos del informe
                for descripcion, archivo, fechagenera in zip(descripciones, archivos, fechasgenera):
                    fecha = datetime.strptime(fechagenera, '%Y-%m-%d').date()
                    pdf2ReaderEvi = PyPDF2.PdfFileReader(archivo)

                    archivoreg = archivo
                    archivoreg._name = generar_nombre("anexoinformejuridico", archivoreg._name)

                    anexoinforme = InformeFactibilidadAnexo(
                        informe=informe,
                        descripcion=descripcion.strip(),
                        fecha=fecha,
                        archivo=archivoreg,
                        numeropagina=pdf2ReaderEvi.numPages
                    )
                    anexoinforme.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=estado.observacion,
                    estado=estado
                )
                recorrido.save(request)

                log(u'%s agregó informe jurídico de factibilidad %s a postulación de beca: %s' % (persona, informe.numero, postulacion), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True, "id": request.POST['id']})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editinformejuridico':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                # Consulto el informe
                informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.POST['id'])))
                postulacion = informe.solicitud

                # Verifico que se pueda manipular el registro
                if not postulacion.puede_manipular_informejuridico():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el registro debido que ya se registró el informe de otorgamiento en la Coordinación de investigación", "showSwal": "True", "swalType": "warning"})

                # Obtengo los valores de los campos del formulario
                objeto = remover_atributo_style_html(request.POST['objeto']).strip()
                antecedente = remover_atributo_style_html(request.POST['antecedente']).strip()
                motivaciontecnica = remover_atributo_style_html(request.POST['motivaciontecnica']).strip()
                recomendacion = remover_atributo_style_html(request.POST['recomendacion']).strip()

                # Obtengo los valores del detalle de anexos
                nfilas_ca_evi = json.loads(request.POST['lista_items1'])  # Números de filas que tienen lleno el campo archivo en detalle de evidencias
                nfilas = request.POST.getlist('nfila_evidencia[]')  # Todos los número de filas del detalle de anexos
                idsanexos = request.POST.getlist('idregistro[]')  # Todos los ids de detalle de anexos
                descripciones = request.POST.getlist('descripcion_evidencia[]')  # Todas las descripciones
                archivos = request.FILES.getlist('archivo_evidencia[]')  # Todos los archivos
                fechasgenera = request.POST.getlist('fecha_genera[]')  # Todas las fechas de generación
                anexosseliminados = json.loads(request.POST['lista_items2']) if 'lista_items2' in request.POST else []

                # Valido los archivos cargados en el detalle de anexos
                for nfila, archivo in zip(nfilas_ca_evi, archivos):
                    descripcionarchivo = 'Anexo'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                # En caso que el estado sea I.J. NOTIFICADO, I.O.PENDIENTE R, se debe actualizar los estados de la postulacion
                actualizarpostulacion = postulacion.estado.valor in [9, 11]

                if actualizarpostulacion:
                    # Obtengo estado REVISADO POR JURÍDICO
                    estado = obtener_estado_solicitud(13, 8)

                    # Actualizar la solicitud
                    postulacion.estado = estado
                    postulacion.save(request)

                # Actualizo el registro del informe
                informe.objeto = objeto
                informe.antecedente = antecedente
                informe.motivaciontecnica = motivaciontecnica
                informe.recomendacion = recomendacion
                informe.archivo = None
                informe.archivofirmado = None
                informe.impreso = False
                informe.firmaelabora = False
                informe.firmaverifica = False
                informe.firmaaprueba = False
                informe.estado = 1
                informe.save(request)

                # Guardo los anexos del informe
                for idanexo, nfila, descripcion, fechagenera in zip(idsanexos, nfilas, descripciones, fechasgenera):
                    fecha = datetime.strptime(fechagenera, '%Y-%m-%d').date()
                    # Si es registro nuevo
                    if int(idanexo) == 0:
                        anexoinforme = InformeFactibilidadAnexo(
                            informe=informe,
                            descripcion=descripcion.strip(),
                            fecha=fecha
                        )
                    else:
                        anexoinforme = InformeFactibilidadAnexo.objects.get(pk=idanexo)
                        anexoinforme.descripcion = descripcion.strip()
                        anexoinforme.fecha = fecha

                    anexoinforme.save(request)

                    # Guardo el archivo del anexo
                    for nfilaarchi, archivo in zip(nfilas_ca_evi, archivos):
                        # Si la fila de la descripcion es igual a la fila que contiene archivo
                        if int(nfilaarchi['nfila']) == int(nfila):
                            pdf2ReaderEvi = PyPDF2.PdfFileReader(archivo)

                            archivoreg = archivo
                            archivoreg._name = generar_nombre("anexoinformejuridico", archivoreg._name)

                            # actualizo campo archivo del registro creado
                            anexoinforme.archivo = archivoreg
                            anexoinforme.numeropagina = pdf2ReaderEvi.numPages
                            anexoinforme.save(request)
                            break

                # Elimino los anexos que se borraron del detalle
                if anexosseliminados:
                    for anexo in anexosseliminados:
                        anexoinforme = InformeFactibilidadAnexo.objects.get(pk=anexo['idreg'])
                        anexoinforme.status = False
                        anexoinforme.save(request)

                if actualizarpostulacion:
                    # Guardo el recorrido de la solicitud
                    recorrido = RecorridoRegistro(
                        tiporegistro=2,
                        registroid=postulacion.id,
                        fecha=datetime.now().date(),
                        departamento=persona.mi_cargo_actual().unidadorganica,
                        persona=persona,
                        observacion=estado.observacion,
                        estado=estado
                    )
                    recorrido.save(request)

                log(u'%s editó informe jurídico de factibilidad %s a postulación de beca: %s' % (persona, informe.numero, postulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True, "id": request.POST['id']})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'informejuridicopdf':
            try:
                data = {}

                informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.POST['id'])))

                data['informe'] = informe
                data['postulacion'] = postulacion = informe.solicitud

                data['vicerrector'] = vicerrector_investigacion_posgrado()
                data['coordinador'] = coordinador_investigacion()
                data['analista'] = analista_investigacion()
                data['experto'] = experto_investigacion()

                anexos = []
                numero = 0

                for anexo in informe.anexos():
                    numero += 1
                    anexos.append({
                        "numero": numero,
                        "descripcion": anexo.descripcion,
                        "fecha": anexo.fecha,
                        "numeropagina": anexo.numeropagina
                    })

                data['anexos'] = anexos

                # Creacion de los archivos por separado
                directorio = SITE_STORAGE + '/media/becadocente/informes'
                try:
                    os.stat(directorio)
                except:
                    os.mkdir(directorio)

                # Archivo de la parte 1 del informe
                nombrearchivo = 'informeparte1_' + str(informe.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                valida = convert_html_to_pdf(
                    'adm_becadocente/informejuridicopdf.html',
                    {'pagesize': 'A4', 'data': data},
                    nombrearchivo,
                    directorio
                )

                if not valida:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el documento de la parte 1 del informe. [%s]", "showSwal": "True", "swalType": "error"})

                archivo1 = directorio + "/" + nombrearchivo

                # Leer los archivos
                pdf1Reader = PyPDF2.PdfFileReader(archivo1)

                # Crea un nuevo objeto PdfFileWriter que representa un documento PDF en blanco
                pdfWriter = PyPDF2.PdfFileWriter()

                # Recorre todas las páginas del documento 1
                for pageNum in range(pdf1Reader.numPages):
                    pageObj = pdf1Reader.getPage(pageNum)
                    pdfWriter.addPage(pageObj)

                # Recorro el detalle de requisitos
                for evidencia in informe.anexos():
                    archivoevidencia = SITE_STORAGE + evidencia.archivo.url  # Archivo pdf cargado
                    pdf2ReaderEvi = PyPDF2.PdfFileReader(archivoevidencia)

                    # Recorre todas las páginas del documento de evidencia: pdf2ReaderEvi
                    for pageNum in range(pdf2ReaderEvi.numPages):
                        pageObj = pdf2ReaderEvi.getPage(pageNum)
                        pdfWriter.addPage(pageObj)

                # Luego de haberse copiado todas las paginas de todos los documentos, se las escribe en el documento en blanco
                fecha = datetime.now().date()
                hora = datetime.now().time()
                nombrearchivoresultado = generar_nombre('informejuridicobeca', 'informejuridicobeca.pdf')
                pdfOutputFile = open(directorio + "/" + nombrearchivoresultado, "wb")
                pdfWriter.write(pdfOutputFile)

                # Borro los documento individuales creados a exepción del archivo del proyecto cargado por el docente
                os.remove(archivo1)

                pdfOutputFile.close()

                # archivo = 'media/becadocente/informes/' + nombrearchivoresultado
                archivo = SITE_STORAGE + '/media/becadocente/informes/' + nombrearchivoresultado

                # Aperturo el archivo generado
                with open(archivo, 'rb') as f:
                    data = f.read()

                buffer = io.BytesIO()
                buffer.write(data)
                pdfcopia = buffer.getvalue()
                buffer.seek(0)
                buffer.close()

                # Extraigo el contenido
                archivocopiado = ContentFile(pdfcopia)
                archivocopiado.name = nombrearchivoresultado

                informe.impreso = True
                informe.archivo = archivocopiado
                informe.save(request)

                # Borro el informe creado de manera general, no la del registro
                os.remove(archivo)

                return JsonResponse({"result": "ok", "documento": informe.archivo.url, "id": encrypt(postulacion.id)})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el documento del informe. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'subirinformejuridico':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto el informe de otorgamiento de beca
                informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.POST['id'])))
                postulacion = informe.solicitud

                # Verifico que se pueda manipular el registro
                if not postulacion.puede_manipular_informejuridico():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el registro debido que ya se registró el informe de otorgamiento en la Coordinación de investigación", "showSwal": "True", "swalType": "warning"})

                archivo = request.FILES['archivoinforme']
                descripcionarchivo = 'Archivo del Informe Firmado'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '10MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                numeropagina = 0
                # Verifica que el archivo no presente problemas
                try:
                    pdf2ReaderEvi = PyPDF2.PdfFileReader(archivo)
                    numeropagina = pdf2ReaderEvi.numPages
                except Exception as ex:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El archivo presenta problemas", "showSwal": "True", "swalType": "warning"})

                # Obtengo estado NFORME JURÍDICO CARGADO
                estado = obtener_estado_solicitud(13, 9)

                archivo._name = generar_nombre("informejuridico", archivo._name)

                # Actualizo el estado de la postulación
                postulacion.estado = estado
                postulacion.save(request)

                # Actualizo el informe
                informe.archivo = archivo
                informe.estado = 5
                informe.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=estado.observacion,
                    estado=estado
                )
                recorrido.save(request)

                # Obtengo estado INFORME FACTIBILIDAD PENDIENTE DE GENERAR POR ANALISTA DE INVESTIGACIÓN
                estado = obtener_estado_solicitud(13, 11)

                # Actualizo la postulación
                postulacion.observacion = estado.observacion
                postulacion.estado = estado
                postulacion.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=estado.observacion,
                    estado=estado
                )
                recorrido.save(request)

                # Guardo o actualizo el archivo de la solicitud
                if not postulacion.solicituddocumento_set.values("id").filter(status=True, documento__tipo=2).exists():
                    # Consulto el tipo de documento
                    documento = Documento.objects.get(tipo=2)

                    # Guardo el documento de la solicitud
                    solicituddocumento = SolicitudDocumento(
                        solicitud=postulacion,
                        documento=documento,
                        archivo=archivo,
                        numeropagina=numeropagina,
                        estado=2
                    )
                else:
                    solicituddocumento = SolicitudDocumento.objects.get(solicitud=postulacion, documento__tipo=2, status=True)
                    solicituddocumento.archivo = archivo
                    solicituddocumento.numeropagina = numeropagina
                    solicituddocumento.estado = 2
                    solicituddocumento.observacion = ''

                solicituddocumento.save(request)

                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec

                # Notificar por e-mail al Analista de Investigación
                personadestinatario = analista_investigacion()
                # lista_email_envio = personadestinatario.lista_emails_envio()
                lista_email_envio = ['isaltosm@unemi.edu.ec']
                lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                lista_archivos_adjuntos = [informe.archivo]

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                asuntoemail = "Registro de Informe Jurídico de factibilidad de Beca"
                titulo = "Postulación Beca Docente"
                tiponotificacion = "INFBECJUR"

                send_html_mail(asuntoemail,
                               "emails/postulacionbecadocente.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimada' if personadestinatario.sexo_id == 1 else 'Estimado',
                                'nombrepersona': personadestinatario.nombre_completo_inverso(),
                                'genpersona': 'de la docente' if postulacion.profesor.persona.sexo_id == 1 else 'del docente',
                                'nombredocente': postulacion.profesor.persona.nombre_completo_inverso(),
                                'postulacion': postulacion
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_archivos_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s subió informe jurídico de factibilidad de beca firmada para la solicitud: %s' % (persona, postulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'notificarinformeotorgamiento':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto el informe de otorgamiento de beca
                informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.POST['id'])))
                postulacion = informe.solicitud

                # Si no se puede notificar el informe de la postulación
                if not postulacion.puede_notificar_informe_otorgamiento():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede actualizar el registro debido a que el informe ha sido revisado por el Vicerrector de Investigación y Posgrado", "showSwal": "True", "swalType": "warning"})

                estado = int(request.POST['estado'])
                observacionrevision = ''

                # Estado VALIDADO del informe
                if estado == 4:
                    # Obtengo estado INFORME DE OTORGAMIENTO NOTIFICADO AL VICERRECTOR DE INVESTIGACIÓN Y POSGRADO
                    estadosolicitud = obtener_estado_solicitud(13, 17)
                else:
                    # Obtengo estado INFORME DE OTORGAMIENTO DEL DOCENTE CON NOVEDADES
                    estadosolicitud = obtener_estado_solicitud(13, 18)
                    observacionrevision = request.POST['observacion'].strip().upper()

                # Actualizo la postulación
                postulacion.inotificadovi = estado == 4
                postulacion.estadoinformeo = 2 if estado == 4 else 1
                postulacion.estado = estadosolicitud
                postulacion.save(request)

                # Actualizo el informe
                informe.observacion = observacionrevision
                informe.estado = estado
                informe.notificadovi = estado == 4
                informe.firmavalida = estado == 4
                informe.estado = 4 if estado == 4 else 3
                informe.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=observacionrevision if observacionrevision else estadosolicitud.observacion,
                    estado=estadosolicitud
                )
                recorrido.save(request)

                # Si fue VALIDADA notifico al Vicerrector de Investigación y Posgrado
                if estado == 4:
                    personadestinatario = vicerrector_investigacion_posgrado()
                else:
                    # Notificar al Docente solicitante
                    personadestinatario = postulacion.profesor.persona

                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                # E-mail del destinatario
                # lista_email_envio = personadestinatario.lista_emails_envio()
                lista_email_envio = ['isaltosm@unemi.edu.ec']
                lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                lista_archivos_adjuntos = [informe.archivofirmado]

                if estado == 4:
                    asuntoemail = "Informe de Factibilidad de Otorgamiento de Beca Validado por el Coordinador de Investigación"
                    titulo = "Postulación Beca Docente"
                    tiponotificacion = "INFVALCOOR"

                    send_html_mail(asuntoemail,
                                   "emails/postulacionbecadocente.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'nombredocente': postulacion.profesor.persona.nombre_completo_inverso(),
                                    'genpersona': 'de la docente' if postulacion.profesor.persona.sexo_id == 1 else 'del docente',
                                    'nombrevicerrector': personadestinatario.nombre_completo_inverso(),
                                    'postulacion': postulacion,
                                    'observacionrevision': observacionrevision,
                                    'tiponotificacion': tiponotificacion,
                                    'saludo': 'Estimada' if personadestinatario.sexo_id == 1 else 'Estimado'
                                    },
                                   lista_email_envio,
                                   lista_email_cco,
                                   lista_archivos_adjuntos,
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                    log(u'%s validó informe de factibilidad de otorgamiento de beca: %s' % (persona, informe), request, "edit")
                else:
                    asuntoemail = "Novedades con Informe de Factibilidad de Otorgamiento de Beca"
                    titulo = "Postulación Beca Docente"
                    tiponotificacion = "RECHCOOR"

                    send_html_mail(asuntoemail,
                                   "emails/postulacionbecadocente.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'nombrepersona': postulacion.profesor.persona.nombre_completo_inverso(),
                                    'postulacion': postulacion,
                                    'observacionrevision': observacionrevision,
                                    'tiponotificacion': tiponotificacion,
                                    'saludo': 'Estimada' if personadestinatario.sexo_id == 1 else 'Estimado'
                                    },
                                   lista_email_envio,
                                   lista_email_cco,
                                   lista_archivos_adjuntos,
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                    log(u'%s rechazó informe de factibilidad de otorgamiento de beca: %s' % (persona, informe), request, "edit")

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'revisarinformeotorgamiento':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto el informe de otorgamiento de beca
                informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.POST['id'])))
                postulacion = informe.solicitud

                estado = int(request.POST['estado'])
                observacionrevision = ''

                # Obtengo estado INFORME DE OTORGAMIENTO REVISADO POR VICERRECTOR DE INVESTIGACIÓN Y POSGRADO
                estadosolicitud = obtener_estado_solicitud(13, 19)

                # Actualizo la postulación
                postulacion.irevisadovi = True
                postulacion.estado = estadosolicitud
                postulacion.save(request)

                # Actualizo el informe
                informe.observacion = observacionrevision
                informe.revisadovi = True
                informe.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=observacionrevision if observacionrevision else estadosolicitud.observacion,
                    estado=estadosolicitud
                )
                recorrido.save(request)

                log(u'%s revisó informe de factibilidad de otorgamiento de beca: %s' % (persona, informe), request, "edit")

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'notificarinformecomite':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto el informe de otorgamiento de beca
                informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.POST['id'])))
                postulacion = informe.solicitud

                # Verificar que exista comité de beca
                integrantescomite = postulacion.convocatoria.comite_institucional_becas()
                if not integrantescomite:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede notificar porque no existen integrantes del comité de becas registrados", "showSwal": "True", "swalType": "warning"})

                # Obtengo estado INFORME NOTIFICADO AL COMITÉ INSTITUCIONAL DE BECAS
                estadosolicitud = obtener_estado_solicitud(13, 20)

                # Actualizo la postulación
                postulacion.inotificadocb = True
                postulacion.estado = estadosolicitud
                postulacion.save(request)

                # Actualizo el informe
                informe.notificadocb = True
                informe.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=estadosolicitud.observacion,
                    estado=estadosolicitud
                )
                recorrido.save(request)

                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                lista_email_envio = []

                # E-mail del destinatario
                # for integrante in integrantescomite:
                #     lista_email_envio += integrante.persona.lista_emails_envio()

                # lista_email_envio = personadestinatario.lista_emails_envio()
                lista_email_envio = ['isaltosm@unemi.edu.ec']
                lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                lista_archivos_adjuntos = [informe.archivofirmado]

                asuntoemail = "Emitir Resolución favorable o no favorable para el Otorgamiento de becas"
                titulo = "Postulación Beca Docente"
                tiponotificacion = "INFREVVICE"

                send_html_mail(asuntoemail,
                               "emails/postulacionbecadocente.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'nombredocente': postulacion.profesor.persona.nombre_completo_inverso(),
                                'genpersona': 'de la docente' if postulacion.profesor.persona.sexo_id == 1 else 'del docente',
                                'postulacion': postulacion,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimados'
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_archivos_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s notificó informe de factibilidad de otorgamiento de beca al comité de becas: %s' % (persona, informe), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'notificarinformecomitemasivo':
            try:
                if 'idc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la convocatoria
                convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.POST['idc'])))

                # Consulto los informes de otorgamiento de beca que no han sido notificados al comité
                for informe in InformeFactibilidad.objects.filter(solicitud__convocatoria=convocatoria, status=True, vigente=True, tipo=1, revisadovi=True, notificadocb=False):
                    postulacion = informe.solicitud

                    # Verificar que exista comité de beca
                    integrantescomite = postulacion.convocatoria.comite_institucional_becas()
                    if not integrantescomite:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede notificar porque no existen integrantes del comité de becas registrados", "showSwal": "True", "swalType": "warning"})

                    # Obtengo estado INFORME NOTIFICADO AL COMITÉ INSTITUCIONAL DE BECAS
                    estadosolicitud = obtener_estado_solicitud(13, 20)

                    # Actualizo la postulación
                    postulacion.inotificadocb = True
                    postulacion.estado = estadosolicitud
                    postulacion.save(request)

                    # Actualizo el informe
                    informe.notificadocb = True
                    informe.save(request)

                    # Guardo el recorrido de la solicitud
                    recorrido = RecorridoRegistro(
                        tiporegistro=2,
                        registroid=postulacion.id,
                        fecha=datetime.now().date(),
                        departamento=persona.mi_cargo_actual().unidadorganica,
                        persona=persona,
                        observacion=estadosolicitud.observacion,
                        estado=estadosolicitud
                    )
                    recorrido.save(request)

                    # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                    listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                    lista_email_envio = []

                    # E-mail del destinatario
                    # for integrante in integrantescomite:
                    #     lista_email_envio += integrante.persona.lista_emails_envio()

                    # lista_email_envio = personadestinatario.lista_emails_envio()
                    lista_email_envio = ['isaltosm@unemi.edu.ec']
                    lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                    lista_archivos_adjuntos = [informe.archivofirmado]

                    asuntoemail = "Emitir Resolución favorable o no favorable para el Otorgamiento de becas"
                    titulo = "Postulación Beca Docente"
                    tiponotificacion = "INFREVVICE"

                    send_html_mail(asuntoemail,
                                   "emails/postulacionbecadocente.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'nombredocente': postulacion.profesor.persona.nombre_completo_inverso(),
                                    'genpersona': 'de la docente' if postulacion.profesor.persona.sexo_id == 1 else 'del docente',
                                    'postulacion': postulacion,
                                    'tiponotificacion': tiponotificacion,
                                    'saludo': 'Estimados'
                                    },
                                   lista_email_envio,
                                   lista_email_cco,
                                   lista_archivos_adjuntos,
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                    log(u'%s notificó informe de factibilidad de otorgamiento de beca al comité de becas: %s' % (persona, informe), request, "edit")
                    ET.sleep(3)

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Notificaciones realizadas con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'emitirresolucion':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                # Consulto la postulación
                postulacion = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verificar que se pueda manipular la postulacion
                if not postulacion.puede_revisar_comite():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede actualizar el Registro", "showSwal": "True", "swalType": "warning"})

                informe = postulacion.informe_otorgamiento()
                resolucion = postulacion.resolucion_comite(informe)
                guardarecorrido = resolucion is None

                # Obtengo los valores de los campos del formulario
                resultado = int(request.POST['resultado'])
                motivo = request.POST['motivo'].strip()

                # Obtengo estado para el registro POSTULACIÓN EN REVISIÓN POR COMITÉ INSTITUCIONAL DE BECAS
                # estado = obtener_estado_solicitud(13, 20) if resultado == 1 else obtener_estado_solicitud(13, 21)

                # Obtengo estado para el registro POSTULACIÓN EN REVISIÓN POR COMITÉ INSTITUCIONAL DE BECAS
                estado = obtener_estado_solicitud(13, 22)

                # Actualizar la solicitud
                postulacion.irevisadocb = True
                postulacion.resultadocb = resultado
                postulacion.estado = estado
                postulacion.save(request)

                # Actualizar el informe
                informe.revisadocb = True
                informe.save(request)

                # Si no existe la resolución la creo sino la actualizo
                if not resolucion:
                    # Obtener secuencia de la resolucion
                    secuencia = secuencia_resolucion_comite(datetime.now().year)
                    numero = "CB-SO-MES-" + str(datetime.now().year) + " N°. " + str(secuencia).zfill(3)

                    persona1 = vicerrector_investigacion_posgrado()
                    cargo1 = persona1.mi_cargo_actual().denominacionpuesto
                    persona2 = coordinador_investigacion()
                    cargo2 = persona2.mi_cargo_actual().denominacionpuesto

                    resolucion = ResolucionComite(
                        solicitud=postulacion,
                        informe=informe,
                        secuencia=secuencia,
                        fecha=datetime.now(),
                        numero=numero,
                        resultado=resultado,
                        motivo=motivo,
                        resuelve='',
                        personavice=persona1,
                        cargovice=cargo1,
                        personacoord=persona2,
                        cargocoord=cargo2,
                        vigente=True,
                        enviadoocas=False
                    )
                else:
                    resolucion.resultado = resultado
                    resolucion.motivo = motivo
                    resolucion.impreso = False
                    resolucion.archivo = None
                    resolucion.archivofirmado = None
                    resolucion.firmavice = False
                    resolucion.firmacoord = False

                resolucion.save(request)

                if guardarecorrido:
                    # Guardo el recorrido de la solicitud
                    recorrido = RecorridoRegistro(
                        tiporegistro=2,
                        registroid=postulacion.id,
                        fecha=datetime.now().date(),
                        departamento=persona.mi_cargo_actual().unidadorganica,
                        persona=persona,
                        observacion=estado.observacion,
                        estado=estado
                    )
                    recorrido.save(request)

                if guardarecorrido:
                    log(u'%s agregó resolución %s del comité de becas para la postulación de beca: %s' % (persona, resolucion.numero, postulacion), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True, "id": request.POST['id']})
                else:
                    log(u'%s editó resolución %s del comité de becas para la postulación de beca: %s' % (persona, resolucion.numero, postulacion), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True, "id": request.POST['id']})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'resolucioncomitepdf':
            try:
                data = {}
                resolucion = ResolucionComite.objects.get(pk=int(encrypt(request.POST['id'])))
                informe = resolucion.informe

                data['resolucion'] = resolucion
                data['informe'] = informe
                data['postulacion'] = postulacion = informe.solicitud
                data['fecharesolucion'] = fechaletra_corta(resolucion.fecha)
                # data['vicerrector'] = vicerrector_investigacion_posgrado()
                # data['coordinador'] = coordinador_investigacion()
                # data['analista'] = analista_investigacion()
                # data['experto'] = experto_investigacion()
                data['anio1'] = anio1 = postulacion.inicio.year
                data['presupuesto1'] = postulacion.presupuesto_solicitud().total_anio(anio1)
                data['presupuesto'] = presupuesto = postulacion.presupuesto_solicitud()
                data['cantidadperiodos'] = cantidadperiodos = presupuesto.numeroperiodo

                listaanios = []
                anioi = postulacion.inicio.year
                aniof = postulacion.fin.year
                total = (aniof - anioi) + 1

                for n in range(total):
                    listaanios.append(anioi)
                    anioi += 1

                data['colspancab'] = (cantidadperiodos * 2) + 3
                data['anios'] = listaanios
                data['rubros'] = postulacion.rubros()
                data['montobecaletras'] = moneda_a_letras(str(postulacion.presupuesto)).upper()

                # Creacion de los archivos por separado
                directorio = SITE_STORAGE + '/media/becadocente/resoluciones'
                try:
                    os.stat(directorio)
                except:
                    os.mkdir(directorio)

                # Archivo de la parte 1 del informe
                nombrearchivo = 'resolucioncomite_' + str(resolucion.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                valida = convert_html_to_pdf(
                    'adm_becadocente/resolucioncomitepdf.html',
                    {'pagesize': 'A4', 'data': data},
                    nombrearchivo,
                    directorio
                )

                if not valida:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el documento de la parte 1 del informe. [%s]", "showSwal": "True", "swalType": "error"})

                archivo1 = directorio + "/" + nombrearchivo

                # Leer los archivos
                pdf1Reader = PyPDF2.PdfFileReader(archivo1)

                # Crea un nuevo objeto PdfFileWriter que representa un documento PDF en blanco
                pdfWriter = PyPDF2.PdfFileWriter()

                # Recorre todas las páginas del documento 1
                for pageNum in range(pdf1Reader.numPages):
                    pageObj = pdf1Reader.getPage(pageNum)
                    pdfWriter.addPage(pageObj)

                # Luego de haberse copiado todas las paginas de todos los documentos, se las escribe en el documento en blanco
                fecha = datetime.now().date()
                hora = datetime.now().time()
                nombrearchivoresultado = generar_nombre('resolucioncomitebeca', 'resolucioncomitebeca.pdf')
                pdfOutputFile = open(directorio + "/" + nombrearchivoresultado, "wb")
                pdfWriter.write(pdfOutputFile)

                # Borro el documento individual creado
                os.remove(archivo1)

                pdfOutputFile.close()

                # archivo = 'media/becadocente/resoluciones/' + nombrearchivoresultado
                archivo = SITE_STORAGE + '/media/becadocente/resoluciones/' + nombrearchivoresultado

                # Aperturo el archivo generado
                with open(archivo, 'rb') as f:
                    data = f.read()

                buffer = io.BytesIO()
                buffer.write(data)
                pdfcopia = buffer.getvalue()
                buffer.seek(0)
                buffer.close()

                # Extraigo el contenido
                archivocopiado = ContentFile(pdfcopia)
                archivocopiado.name = nombrearchivoresultado

                # Borro el archivo creado de manera general, no la del registro
                os.remove(archivo)

                # Actualizo la resolución
                resolucion.archivo = archivocopiado
                resolucion.impreso = True
                resolucion.save(request)

                # return JsonResponse({"result": "ok", "documento": archivo})
                return JsonResponse({"result": "ok", "documento": resolucion.archivo.url, "id": encrypt(postulacion.id)})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el documento del informe. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'subirresolucion':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la resolucion
                resolucion = ResolucionComite.objects.get(pk=int(encrypt(request.POST['id'])))
                postulacion = resolucion.solicitud

                # Verificar que se pueda manipular la postulacion
                if not postulacion.puede_revisar_comite():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede actualizar el Registro", "showSwal": "True", "swalType": "warning"})

                archivo = request.FILES['archivoresolucion']
                descripcionarchivo = 'Archivo de la Resolución Firmada'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                numeropagina = 0
                # Verifica que el archivo no presente problemas
                try:
                    pdf2ReaderEvi = PyPDF2.PdfFileReader(archivo)
                    numeropagina = pdf2ReaderEvi.numPages
                except Exception as ex:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El archivo presenta problemas", "showSwal": "True", "swalType": "warning"})

                archivo._name = generar_nombre("resolucioncbeca", archivo._name)

                # Actualizo la resolución
                resolucion.archivo = archivo
                resolucion.save(request)

                log(u'%s subió resolución del comité de becas firmado para la solicitud: %s' % (persona, postulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'confirmarresolucion':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la resolucion
                resolucion = ResolucionComite.objects.get(pk=int(encrypt(request.POST['id'])))
                postulacion = resolucion.solicitud

                # Obtengo estado RESOLUCIÓN REGISTRADA POR COMITÉ DE BECAS
                estado = obtener_estado_solicitud(13, 23)

                # Actualizo la postulación
                postulacion.estado = estado
                postulacion.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=estado.observacion,
                    estado=estado
                )
                recorrido.save(request)

                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                # E-mail del destinatario solicitante
                # lista_email_envio = postulacion.profesor.persona.lista_emails_envio()
                lista_email_envio = ['isaltosm@unemi.edu.ec']
                lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                lista_archivos_adjuntos = [resolucion.archivofirmado]

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                asuntoemail = "Registro de Resolución por parte del Comité Institucional de Becas"
                tiponotificacion = "REGRES"
                titulo = "Postulación Beca Docente"

                send_html_mail(asuntoemail,
                               "emails/postulacionbecadocente.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimada' if postulacion.profesor.persona.sexo_id == 1 else 'Estimado',
                                'nombrepersona': postulacion.profesor.persona.nombre_completo_inverso(),
                                'postulacion': postulacion,
                                'resolucion': resolucion
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_archivos_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s registró resolución del comité de becas para la solicitud: %s' % (persona, postulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})

                # if resolucion.resultado == 1:
                #     asuntoemail = "Postulación a Beca Docente Aceptada por el Comité Institucional de Becas"
                #     tiponotificacion = "RESFAV"
                # else:
                #     asuntoemail = "Postulación a Beca Docente Rechazada por el Comité Institucional de Becas"
                #     tiponotificacion = "RESNOFAV"
                #
                # titulo = "Postulación Beca Docente"
                #
                # send_html_mail(asuntoemail,
                #                "emails/postulacionbecadocente.html",
                #                {'sistema': u'SGA - UNEMI',
                #                 'titulo': titulo,
                #                 'fecha': fechaenvio,
                #                 'hora': horaenvio,
                #                 'tiponotificacion': tiponotificacion,
                #                 'saludo': 'Estimada' if postulacion.profesor.persona.sexo_id == 1 else 'Estimado',
                #                 'nombrepersona': postulacion.profesor.persona.nombre_completo_inverso(),
                #                 'postulacion': postulacion,
                #                 'resolucion': resolucion
                #                 },
                #                lista_email_envio,
                #                lista_email_cco,
                #                lista_archivos_adjuntos,
                #                cuenta=CUENTAS_CORREOS[cuenta][1]
                #                )
                #
                # # Si la resolución es FAVORABLE se debe notificar al coordinador de investigación
                # if resolucion.resultado == 1:
                #     # Notificar por e-mail al Coordnador de Investigación
                #     personadestinatario = coordinador_investigacion()
                #
                #     # E-mail del destinatario
                #     # lista_email_envio = personadestinatario.lista_emails_envio()
                #     lista_email_envio = ['isaltosm@unemi.edu.ec']
                #
                #     asuntoemail = "Postulación a Beca Docente Aceptada por el Comité Institucional de Becas"
                #     titulo = "Postulación Beca Docente"
                #     tiponotificacion = "RESFAVCOOR"
                #
                #     send_html_mail(asuntoemail,
                #                    "emails/postulacionbecadocente.html",
                #                    {'sistema': u'SGA - UNEMI',
                #                     'titulo': titulo,
                #                     'fecha': fechaenvio,
                #                     'hora': horaenvio,
                #                     'tiponotificacion': tiponotificacion,
                #                     'saludo': 'Estimada' if personadestinatario.sexo_id == 1 else 'Estimado',
                #                     'nombrepersona': personadestinatario.nombre_completo_inverso(),
                #                     'nombredocente': postulacion.profesor.persona.nombre_completo_inverso(),
                #                     'genpersona': 'de la docente' if postulacion.profesor.persona.sexo_id == 1 else 'del docente',
                #                     'postulacion': postulacion,
                #                     'resolucion': resolucion
                #                     },
                #                    lista_email_envio,
                #                    lista_email_cco,
                #                    lista_archivos_adjuntos,
                #                    cuenta=CUENTAS_CORREOS[cuenta][1]
                #                    )
                #
                # log(u'%s confirmó resultado de la resolución del comité de becas para la solicitud: %s' % (persona, postulacion), request, "edit")
                # return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'firmarinformejuridico':
            try:
                if 'iddoc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                tipofirma = request.POST['tipofirma']
                archivofirma = request.FILES['archivofirma']
                clavefirma = request.POST['cfirma']
                descripcionarchivo = 'Archivo de la firma electrónica'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivofirma, ['P12', 'PFX'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto el informe
                informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.POST['iddoc'])))

                # Obtengo el archivo del informe
                archivoinforme = informe.archivo if not informe.archivofirmado else informe.archivofirmado
                rutapdfarchivo = SITE_STORAGE + archivoinforme.url

                if tipofirma == 'ELA':
                    textoabuscar = informe.elabora.nombre_completo_inverso()
                    textofirma = 'Elaborado por:'
                    ocurrencia = 1
                elif tipofirma == 'VER':
                    textoabuscar = informe.verifica.nombre_completo_inverso()
                    textofirma = 'Verificado por:'
                    ocurrencia = 1
                else:
                    textoabuscar = informe.aprueba.nombre_completo_inverso()
                    textofirma = 'Aprobado por:'
                    ocurrencia = 1

                vecescontrado = 0
                documento = fitz.open(rutapdfarchivo)
                numpaginafirma = int(documento.page_count) - 1

                # Busca la página donde se encuentran ubicados los textos: Elaboraro por, Verificado por y Aprobado por
                words_dict = {}
                encontrado = False
                for page_number, page in enumerate(documento):
                    words = page.get_text("blocks")
                    words_dict[0] = words

                    for cadena in words_dict[0]:
                        linea = cadena[4].replace("\n", " ")
                        if linea:
                            linea = linea.strip()

                        if textofirma in linea:
                            numpaginafirma = page_number
                            encontrado = True
                            break

                    if encontrado:
                        break

                # Obtener coordenadas para ubicar al firma dependiendo de donde se encuentra ubicado el nombre de la persona
                words_dict = {}
                for page_number, page in enumerate(documento):
                    if page_number == numpaginafirma:
                        words = page.get_text("blocks")
                        words_dict[0] = words

                valor = None
                for cadena in words_dict[0]:
                    linea = cadena[4].replace("\n", " ")
                    if linea:
                        linea = linea.strip()

                    if textoabuscar in linea:
                        valor = cadena

                        vecescontrado += 1
                        if vecescontrado == ocurrencia:
                            break

                if valor:
                    y = 5000 - int(valor[3]) - 4165  # 4110
                else:
                    y = 0

                # x = 87  # izq
                # x = 230  # cent
                x = 350  # der

                # Si no existe el nombre de la persona en el documento
                if y == 0:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"No se encuentra el nombre del firmante en el documento", "showSwal": "True", "swalType": "warning"})

                # Firma del documento
                generar_archivo_firmado = io.BytesIO()
                datau, datas = firmar(request, clavefirma, archivofirma, archivoinforme, numpaginafirma, x, y, 150, 45)
                if not datau:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % datas, "showSwal": "True", "swalType": "error"})

                generar_archivo_firmado.write(datau)
                generar_archivo_firmado.write(datas)
                generar_archivo_firmado.seek(0)

                nombrearchivofirmado = generar_nombre('informejuridicofirmado', 'informejuridicofirmado.pdf')
                objarchivo = DjangoFile(generar_archivo_firmado, nombrearchivofirmado)

                informe.archivofirmado = objarchivo

                if tipofirma == 'ELA':
                    informe.firmaelabora = True
                elif tipofirma == 'VER':
                    informe.firmaverifica = True
                else:
                    informe.firmaaprueba = True

                informe.save(request)

                log(u'%s firmó informe jurídico de solicitud de beca: %s' % (persona, informe), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True, "documento": informe.archivofirmado.url, "id": encrypt(informe.solicitud.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'notificarinformeinvestigacion':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto el informe de otorgamiento de beca
                informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.POST['id'])))
                postulacion = informe.solicitud

                # Verifico que se pueda manipular el registro
                if not postulacion.puede_manipular_informejuridico():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el registro debido que ya se registró el informe de otorgamiento en la Coordinación de investigación", "showSwal": "True", "swalType": "warning"})

                # Obtener número de páginas del informe
                rutapdfarchivo = SITE_STORAGE + informe.archivofirmado.url
                pdf2ReaderEvi = PyPDF2.PdfFileReader(rutapdfarchivo)
                numeropagina = pdf2ReaderEvi.numPages

                # Obtengo estado NFORME JURÍDICO NOTIFICADO A INVESTIGACIÓN
                estado = obtener_estado_solicitud(13, 9)

                # Actualizo el estado de la postulación
                postulacion.estado = estado
                postulacion.save(request)

                # Actualizo el informe
                informe.estado = 6
                informe.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=estado.observacion,
                    estado=estado
                )
                recorrido.save(request)

                # Obtengo estado INFORME FACTIBILIDAD PENDIENTE DE GENERAR POR ANALISTA DE INVESTIGACIÓN
                estado = obtener_estado_solicitud(13, 11)

                # Actualizo la postulación
                postulacion.observacion = estado.observacion
                postulacion.estado = estado
                postulacion.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=estado.observacion,
                    estado=estado
                )
                recorrido.save(request)

                # Aperturo el archivo
                with open(rutapdfarchivo, 'rb') as f:
                    data = f.read()

                buffer = io.BytesIO()
                buffer.write(data)
                pdfcopia = buffer.getvalue()
                buffer.seek(0)
                buffer.close()

                nombrearchivo = generar_nombre('informejuridico', 'informejuridico.pdf')

                # Extraigo el contenido
                archivocopiado = ContentFile(pdfcopia)
                archivocopiado.name = nombrearchivo

                # Guardo o actualizo el archivo de la solicitud
                if not postulacion.solicituddocumento_set.values("id").filter(status=True, documento__tipo=2).exists():
                    # Consulto el tipo de documento
                    documento = Documento.objects.get(tipo=2)

                    # Guardo el documento de la solicitud
                    solicituddocumento = SolicitudDocumento(
                        solicitud=postulacion,
                        documento=documento,
                        archivofirmado=archivocopiado,
                        numeropagina=numeropagina,
                        estado=2
                    )
                else:
                    solicituddocumento = SolicitudDocumento.objects.get(solicitud=postulacion, documento__tipo=2, status=True)
                    solicituddocumento.archivofirmado = archivocopiado
                    solicituddocumento.numeropagina = numeropagina
                    solicituddocumento.estado = 2
                    solicituddocumento.observacion = ''

                solicituddocumento.save(request)

                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec

                # Notificar por e-mail al Analista de Investigación
                personadestinatario = analista_investigacion()
                # lista_email_envio = personadestinatario.lista_emails_envio()
                lista_email_envio = ['isaltosm@unemi.edu.ec']
                lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                lista_archivos_adjuntos = [informe.archivofirmado]

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                asuntoemail = "Registro de Informe Jurídico de factibilidad de Beca Firmado"
                titulo = "Postulación Beca Docente"
                tiponotificacion = "INFBECJUR"

                send_html_mail(asuntoemail,
                               "emails/postulacionbecadocente.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimada' if personadestinatario.sexo_id == 1 else 'Estimado',
                                'nombrepersona': personadestinatario.nombre_completo_inverso(),
                                'genpersona': 'de la docente' if postulacion.profesor.persona.sexo_id == 1 else 'del docente',
                                'nombredocente': postulacion.profesor.persona.nombre_completo_inverso(),
                                'postulacion': postulacion
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_archivos_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s notificó informe jurídico de factibilidad de beca firmada para la solicitud: %s' % (persona, postulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'firmarinformeotorgamiento':
            try:
                if 'iddoc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                tipofirma = request.POST['tipofirma']
                archivofirma = request.FILES['archivofirma']
                clavefirma = request.POST['cfirma']
                descripcionarchivo = 'Archivo de la firma electrónica'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivofirma, ['P12', 'PFX'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto el informe
                informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.POST['iddoc'])))

                # Obtengo el archivo del informe
                archivoinforme = informe.archivo if not informe.archivofirmado else informe.archivofirmado
                rutapdfarchivo = SITE_STORAGE + archivoinforme.url

                if tipofirma == 'ELA':
                    textoabuscar = informe.elabora.nombre_completo_inverso()
                    textofirma = 'Elaborado por:'
                    ocurrencia = 1
                elif tipofirma == 'VER':
                    textoabuscar = informe.verifica.nombre_completo_inverso()
                    textofirma = 'Verificado por:'
                    ocurrencia = 1
                else:
                    textoabuscar = informe.aprueba.nombre_completo_inverso()
                    textofirma = 'Aprobado por:'
                    ocurrencia = 2

                vecescontrado = 0
                documento = fitz.open(rutapdfarchivo)
                numpaginafirma = int(documento.page_count) - 1

                # Busca la página donde se encuentran ubicados los textos: Elaboraro por, Verificado por y Aprobado por
                words_dict = {}
                encontrado = False
                for page_number, page in enumerate(documento):
                    words = page.get_text("blocks")
                    words_dict[0] = words

                    for cadena in words_dict[0]:
                        linea = cadena[4].replace("\n", " ")
                        if linea:
                            linea = linea.strip()

                        if textofirma in linea:
                            numpaginafirma = page_number
                            encontrado = True
                            break

                    if encontrado:
                        break

                # Obtener coordenadas para ubicar al firma dependiendo de donde se encuentra ubicado el nombre de la persona
                saltolinea = False
                words_dict = {}
                for page_number, page in enumerate(documento):
                    if page_number == numpaginafirma:
                        words = page.get_text("blocks")
                        words_dict[0] = words

                valor = None
                for cadena in words_dict[0]:
                    linea = cadena[4].replace("\n", " ")
                    if linea:
                        linea = linea.strip()

                    if textoabuscar in linea:
                        valor = cadena

                        vecescontrado += 1
                        if vecescontrado == ocurrencia:
                            break

                if valor:
                    y = 5000 - int(valor[3]) - 4125 # 4140
                else:
                    y = 0

                # x = 87  # izq
                # x = 230  # cent
                x = 350  # der

                # Si no existe el nombre de la persona en el documento
                if y == 0:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"No se encuentra el nombre del firmante en el documento", "showSwal": "True", "swalType": "warning"})

                # Obtener extensión y leer archivo de la firma
                extfirma = os.path.splitext(archivofirma.name)[1][1:]
                bytesfirma = archivofirma.read()

                # Firma del documento
                datau = JavaFirmaEc(
                    archivo_a_firmar=archivoinforme,
                    archivo_certificado=bytesfirma,
                    extension_certificado=extfirma,
                    password_certificado=clavefirma,
                    page=numpaginafirma,
                    reason='',
                    lx=x,
                    ly=y
                ).sign_and_get_content_bytes()

                generar_archivo_firmado = io.BytesIO()
                generar_archivo_firmado.write(datau)
                generar_archivo_firmado.seek(0)

                # # Firma del documento
                # generar_archivo_firmado = io.BytesIO()
                # datau, datas = firmar(request, clavefirma, archivofirma, archivoinforme, numpaginafirma, x, y, 150, 45)
                # if not datau:
                #     return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % datas, "showSwal": "True", "swalType": "error"})
                #
                # generar_archivo_firmado.write(datau)
                # generar_archivo_firmado.write(datas)
                # generar_archivo_firmado.seek(0)

                nombrearchivofirmado = generar_nombre('informeotorgamientobecafirmado', 'informeotorgamientobecafirmado.pdf')
                objarchivo = DjangoFile(generar_archivo_firmado, nombrearchivofirmado)

                informe.archivofirmado = objarchivo

                if tipofirma == 'ELA':
                    informe.firmaelabora = True
                elif tipofirma == 'VER':
                    informe.firmaverifica = True
                else:
                    informe.firmaaprueba = True

                informe.save(request)

                log(u'%s firmó informe de otorgamiento de solicitud de beca: %s' % (persona, informe), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True, "documento": informe.archivofirmado.url, "id": encrypt(informe.solicitud.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'notificarinformesolicitante':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto el informe de otorgamiento de beca
                informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.POST['id'])))
                postulacion = informe.solicitud

                # Obtengo estado INFORME DE FACTIBILIDAD NOTIFICADO AL DOCENTE
                estado = obtener_estado_solicitud(13, 13)

                # Actualizo el estado de la postulación
                postulacion.estadoinformeo = 3
                postulacion.estado = estado
                postulacion.save(request)

                # Actualizo el informe
                informe.estado = 2
                informe.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=estado.observacion,
                    estado=estado
                )
                recorrido.save(request)

                # Notificar por e-mail
                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                # E-mail del destinatario solicitante
                # lista_email_envio = postulacion.profesor.persona.lista_emails_envio()
                lista_email_envio = ['isaltosm@unemi.edu.ec']
                lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                lista_archivos_adjuntos = [informe.archivofirmado]

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                asuntoemail = "Revisar Informe de factibilidad de otorgamiento de Beca"
                tiponotificacion = "INFBECANL"
                titulo = "Postulación Beca Docente"

                send_html_mail(asuntoemail,
                               "emails/postulacionbecadocente.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimada' if postulacion.profesor.persona.sexo_id == 1 else 'Estimado',
                                'nombrepersona': postulacion.profesor.persona.nombre_completo_inverso(),
                                'postulacion': postulacion
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_archivos_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s notificó informe de otorgamiento de factibilidad de beca firmada para la solicitud: %s' % (persona, postulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editpresupuesto':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la postulación
                postulacion = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))

                # Si tiene estado I.NOTIFICADO C o REVISION C. se debe actualizar el estado de al postulación y guardar recorrido
                actualizaestado = postulacion.estado.valor in [20, 22]

                anioinicio = postulacion.inicio.year

                # Obtengo los valores de los campos del formulario
                numeroperiodo = request.POST['numero_periodo']
                total = request.POST['total_general']

                # Obtiene los valores de los arreglos
                idrubros = request.POST.getlist('idrubro[]')  # IDs de los rubros
                tiposrubros = request.POST.getlist('tiporubro[]')  # Tipos de rubros
                valoresrubros = request.POST.getlist('valorrubro[]')  # Valores unitarios de los rubros
                matcantidades = request.POST.getlist('mat_cantidad[]')  # Cantidades rubro matricula
                matsubtotales = request.POST.getlist('mat_subtotal[]')  # Subtotales rubro matricula
                psjcantidades = request.POST.getlist('psj_cantidad[]')  # Cantidades rubro pasaje
                psjsubtotales = request.POST.getlist('psj_subtotal[]')  # Subtotales rubro pasaje
                pubcantidades = request.POST.getlist('pub_cantidad[]')  # Cantidades rubro gastos por publicacion
                pubsubtotales = request.POST.getlist('pub_subtotal[]')  # Subtotales rubro gastos por publicacion
                segcantidades = request.POST.getlist('seg_cantidad[]')  # Cantidades rubro seguro de salud
                segsubtotales = request.POST.getlist('seg_subtotal[]')  # Subtotales rubro seguro de salud
                impcantidades = request.POST.getlist('imp_cantidad[]')  # Cantidades rubro impresión
                impsubtotales = request.POST.getlist('imp_subtotal[]')  # Subtotales rubro impresión
                mbicantidades = request.POST.getlist('mbi_cantidad[]')  # Cantidades rubro material biblio.
                mbisubtotales = request.POST.getlist('mbi_subtotal[]')  # Subtotales rubro material biblio.
                mancantidades = request.POST.getlist('man_cantidad[]')  # Cantidades rubro manuntención
                mansubtotales = request.POST.getlist('man_subtotal[]')  # Subtotales rubro manuntención

                # Actualizo el campo presupuesto en la solicitud
                postulacion.presupuesto = total
                postulacion.save(request)

                # Actualizo presupuesto de la postulación
                solicitudpresupuesto = SolicitudPresupuesto.objects.get(solicitud=postulacion, status=True)
                solicitudpresupuesto.total = total
                solicitudpresupuesto.save(request)

                # Actualizo los rubros del presupuesto
                for rubroid, tipo, valorunitario in zip(idrubros, tiposrubros, valoresrubros):
                    presupuestorubro = SolicitudPresupuestoRubro.objects.get(solicitudpresupuesto=solicitudpresupuesto, rubro_id=rubroid, status=True)
                    presupuestorubro.valorunitario = valorunitario
                    presupuestorubro.save(request)

                    # Actualizo el detalle de los rubros del presupuesto
                    anio = anioinicio
                    periodo = 1

                    if tipo == '1':  # Matrícula, colegiatura y derechos de grado
                        for cantidad, subtotal in zip(matcantidades, matsubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle.objects.get(presupuestorubro=presupuestorubro, periodo=periodo, anio=anio, status=True)
                            detallerubro.valorunitario = valorunitario
                            detallerubro.cantidad = cantidad
                            detallerubro.subtotal = subtotal
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    elif tipo == '2':  # Pasaje ida y retorno
                        for cantidad, subtotal in zip(psjcantidades, psjsubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle.objects.get(presupuestorubro=presupuestorubro, periodo=periodo, anio=anio, status=True)
                            detallerubro.valorunitario = valorunitario
                            detallerubro.cantidad = cantidad
                            detallerubro.subtotal = subtotal
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    elif tipo == '3':  # Gastos por publicación de artículos científicos (Q1 o Q2)
                        for cantidad, subtotal in zip(pubcantidades, pubsubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle.objects.get(presupuestorubro=presupuestorubro, periodo=periodo, anio=anio, status=True)
                            detallerubro.valorunitario = valorunitario
                            detallerubro.cantidad = cantidad
                            detallerubro.subtotal = subtotal
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    elif tipo == '4':  # Seguro de salud y de vida
                        for cantidad, subtotal in zip(segcantidades, segsubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle.objects.get(presupuestorubro=presupuestorubro, periodo=periodo, anio=anio, status=True)
                            detallerubro.valorunitario = valorunitario
                            detallerubro.cantidad = cantidad
                            detallerubro.subtotal = subtotal
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    elif tipo == '5':  # Impresión de tesis
                        for cantidad, subtotal in zip(impcantidades, impsubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle.objects.get(presupuestorubro=presupuestorubro, periodo=periodo, anio=anio, status=True)
                            detallerubro.valorunitario = valorunitario
                            detallerubro.cantidad = cantidad
                            detallerubro.subtotal = subtotal
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    elif tipo == '6':  # Material bibliográfico
                        for cantidad, subtotal in zip(mbicantidades, mbisubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle.objects.get(presupuestorubro=presupuestorubro, periodo=periodo, anio=anio, status=True)
                            detallerubro.valorunitario = valorunitario
                            detallerubro.cantidad = cantidad
                            detallerubro.subtotal = subtotal
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    else:  # Manutención: Alimentación, hospedaje y transporte interno
                        for cantidad, subtotal in zip(mancantidades, mansubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle.objects.get(presupuestorubro=presupuestorubro, periodo=periodo, anio=anio, status=True)
                            detallerubro.valorunitario = valorunitario
                            detallerubro.cantidad = cantidad
                            detallerubro.subtotal = subtotal
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1

                # Se debe actualizar el estado de al postulación y guardar recorrido en caso que tenga estado NOVEDADES
                if actualizaestado:
                    # Obtengo estado PRESUPESTO E
                    estado = obtener_estado_solicitud(13, 21)
                    postulacion.estado = estado

                    postulacion.save(request)

                    # Guardo el recorrido de la solicitud
                    recorrido = RecorridoRegistro(
                        tiporegistro=2,
                        registroid=postulacion.id,
                        fecha=datetime.now().date(),
                        departamento=persona.mi_cargo_actual().unidadorganica,
                        persona=persona,
                        observacion=estado.observacion,
                        estado=estado
                    )
                    recorrido.save(request)

                # # Consulto el documento solicitud de beca
                # documentos = postulacion.documentos()
                # if documentos:
                #     documento = documentos.filter(documento__tipo=1)[0]
                #
                #     # Actualizo los campos del documento solicitud de beca
                #     documento.archivo = None
                #     documento.archivofirmado = None
                #     documento.numeropagina = 0
                #     documento.personarevisa = None
                #     documento.fecharevisa = None
                #     documento.observacion = ''
                #     documento.estado = 6
                #     documento.save(request)

                log(u'%s editó presupuesto a postulación de becas para docentes: %s' % (persona, postulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'firmarresolucion':
            try:
                if 'iddoc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                tipofirma = request.POST['tipofirma']
                archivofirma = request.FILES['archivofirma']
                clavefirma = request.POST['cfirma']
                descripcionarchivo = 'Archivo de la firma electrónica'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivofirma, ['P12', 'PFX'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto la resolución
                resolucion = ResolucionComite.objects.get(pk=int(encrypt(request.POST['iddoc'])))

                # Obtengo el archivo de la resolución
                archivoresolucion = resolucion.archivo if not resolucion.archivofirmado else resolucion.archivofirmado
                rutapdfarchivo = SITE_STORAGE + archivoresolucion.url

                if tipofirma == 'VICE':
                    textoabuscar = resolucion.personavice.nombre_completo_inverso()
                    ocurrencia = 1
                else:
                    textoabuscar = resolucion.personacoord.nombre_completo_inverso()
                    ocurrencia = 1


                vecescontrado = 0
                documento = fitz.open(rutapdfarchivo)
                numpaginafirma = int(documento.page_count) - 1

                # # Busca la página donde se encuentran ubicados los nombres de vicerrector y coordinador de investigación
                # words_dict = {}
                # encontrado = False
                # for page_number, page in enumerate(documento):
                #     words = page.get_text("blocks")
                #     words_dict[0] = words
                #
                #     for cadena in words_dict[0]:
                #         linea = cadena[4].replace("\n", " ")
                #         if linea:
                #             linea = linea.strip()
                #
                #         if textoabuscar in linea:
                #             numpaginafirma = page_number
                #             encontrado = True
                #             break
                #
                #     if encontrado:
                #         break

                # Obtener coordenadas para ubicar al firma dependiendo de donde se encuentra ubicado el nombre de la persona
                saltolinea = False
                words_dict = {}
                for page_number, page in enumerate(documento):
                    if page_number == numpaginafirma:
                        words = page.get_text("blocks")
                        words_dict[0] = words

                valor = None
                for cadena in words_dict[0]:
                    linea = cadena[4].replace("\n", " ")
                    if linea:
                        linea = linea.strip()

                    if textoabuscar in linea:
                        valor = cadena

                        vecescontrado += 1
                        if vecescontrado == ocurrencia:
                            # saltolinea = salto_linea_nombre_firma_encontrado(cadena[4])
                            break

                # print(valor[3])

                if valor:
                    # saltolinea = False
                    # if not saltolinea:
                    #     # y = 5000 - int(valor[3]) - 4140
                    #     if tipofirma == 'VICE':
                    #         y = 5000 - int(valor[3]) - 4165
                    #     else:
                    #         y = 5000 - (int(valor[3])+ 12) - 4165
                    # else:
                    #     # y = 5000 - int(valor[3]) - 4130
                    #     if tipofirma == 'VICE':
                    #         y = 5000 - int(valor[3]) - 4130
                    #     else:
                    #         y = 5000 - (int(valor[3])+12) - 4130

                    # y = 5000 - int(valor[3]) - 4165

                    # y = 5000 - int(valor[3]) - 4130
                    # y = 5000 - int(valor[3]) - 4140


                    # y = 5000 - int(valor[3]) - 4110
                    # y = 5000 - int(valor[3]) - 4120

                    if tipofirma == 'VICE':
                        y = 5000 - int(valor[3]) - 4070
                    else:
                        y = 5000 - (int(valor[3]) + 12) - 4070
                else:
                    y = 0

                # x = 87  # izq
                # x = 230  # cent
                # x = 350  # der

                x = 87 if tipofirma == 'VICE' else 350

                # Si no existe el nombre de la persona en el documento
                if y == 0:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"No se encuentra el nombre del firmante en el documento", "showSwal": "True", "swalType": "warning"})

                # Obtener extensión y leer archivo de la firma
                extfirma = os.path.splitext(archivofirma.name)[1][1:]
                bytesfirma = archivofirma.read()

                # Firma del documento
                datau = JavaFirmaEc(
                    archivo_a_firmar=archivoresolucion,
                    archivo_certificado=bytesfirma,
                    extension_certificado=extfirma,
                    password_certificado=clavefirma,
                    page=numpaginafirma,
                    reason='',
                    lx=x,
                    ly=y
                ).sign_and_get_content_bytes()

                generar_archivo_firmado = io.BytesIO()
                generar_archivo_firmado.write(datau)
                generar_archivo_firmado.seek(0)

                # # Firma del documento
                # generar_archivo_firmado = io.BytesIO()
                # datau, datas = firmar(request, clavefirma, archivofirma, archivoresolucion, numpaginafirma, x, y, 150, 45)
                # if not datau:
                #     return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % datas, "showSwal": "True", "swalType": "error"})
                #
                # generar_archivo_firmado.write(datau)
                # generar_archivo_firmado.write(datas)
                # generar_archivo_firmado.seek(0)

                nombrearchivofirmado = generar_nombre('resolucioncomitebecafirmado', 'resolucioncomitebecafirmado.pdf')
                objarchivo = DjangoFile(generar_archivo_firmado, nombrearchivofirmado)

                resolucion.archivofirmado = objarchivo

                if tipofirma == 'VICE':
                    resolucion.firmavice = True
                else:
                    resolucion.firmacoord = True

                resolucion.save(request)

                log(u'%s firmó resolución del comité de becas: %s' % (persona, resolucion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True, "documento": resolucion.archivofirmado.url, "id": encrypt(resolucion.solicitud.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addsolicitudcertificacion':
            try:
                if 'idc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la convocatoria
                convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.POST['idc'])))

                # Obtener ids de postulaciones seleccionadas
                idspostulaciones = json.loads(request.POST['lista_items1'])

                # Verificar que las postulaciones existan y que no tengan solicitudes de certificaciones
                nbeneficiario = monto = 0
                postulaciones = []
                
                for reg in idspostulaciones:
                    postulacion = Solicitud.objects.filter(pk=int(encrypt(reg['id'])))

                    if postulacion:
                        postulacion = postulacion[0]
                        if not postulacion.cpresupuestaria:
                            nbeneficiario += 1
                            monto += postulacion.presupuesto
                            postulaciones.append(postulacion)
                        else:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La postulación del profesor %s ya tiene solicitada certificación presupuestaria" % (postulacion.profesor.persona.nombre_completo_inverso()), "showSwal": "True", "swalType": "warning"})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud. Una o más postulaciones no existen", "showSwal": "True", "swalType": "error"})

                # Obtener el número de certificacion
                numero = secuencia_solicitud_certificacion(convocatoria)

                # Guardo la solicitud de certificacion
                certificacion = CertificacionPresupuestaria(
                    convocatoria=convocatoria,
                    numero=numero,
                    fecha=datetime.now().date(),
                    persona=persona,
                    cargo=persona.mi_cargo_actual().denominacionpuesto,
                    concepto=request.POST['concepto'].strip().upper(),
                    nbeneficiario=nbeneficiario,
                    monto=monto,
                    estado=1
                )
                certificacion.save(request)

                # Obtengo estado CERTIFICACIÓN PRESUPUESTARIA SOLICITADA
                estado = obtener_estado_solicitud(13, 29)

                # Guardar detalle de la solicitud de certificacion y actualizar estados de las postulaciones
                for postulacion in postulaciones:
                    # Guardo detalle de certificacion
                    detallecertificacion = CertificacionPresupuestariaDetalle(
                        certificacion=certificacion,
                        solicitud=postulacion,
                        presupuesto=postulacion.presupuesto
                    )
                    detallecertificacion.save(request)

                    # Actualizo la postulacion
                    postulacion.cpresupuestaria = True
                    postulacion.estado = estado
                    postulacion.save(request)

                    # Guardo recorrido de la postulación
                    recorrido = RecorridoRegistro(
                        tiporegistro=2,
                        registroid=postulacion.id,
                        fecha=datetime.now().date(),
                        departamento=persona.mi_cargo_actual().unidadorganica,
                        persona=persona,
                        observacion=estado.observacion,
                        estado=estado
                    )
                    recorrido.save(request)

                # Notificar por e-mail a la Dirección Financiera
                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                lista_email_envio = ['isaltosm@unemi.edu.ec'] # aqui debe ir el e-mail de la direccion financiara
                lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                lista_archivos_adjuntos = []

                asuntoemail = "Solicitud de Emisión de Certificación Presupuestaria para Becas Docentes"
                titulo = "Postulación Beca Docente"
                tiponotificacion = "SOLCERTPRESUP"

                send_html_mail(asuntoemail,
                               "emails/postulacionbecadocente.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'certificacion': certificacion,
                                'detalles': certificacion.detalle(),
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimados'
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_archivos_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s agregó solicitud de certificación presupuestaria: %s' % (persona, certificacion), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'subircertificacion':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la solicitud de certificación
                certificacion = CertificacionPresupuestaria.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que la información de las postulaciones no haya sido consolidada
                if certificacion.postulaciones_consolidadas():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede guardar el registro debido a que la informacion de las postulaciones ya ha sido consolidada", "showSwal": "True", "swalType": "warning"})

                if 'archivocertificacion' in request.FILES:
                    archivo = request.FILES['archivocertificacion']
                    descripcionarchivo = 'Archivo de la Certificación'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                nuevoregistro = certificacion.numeromemo is None

                # Validar las fechas
                fechamemo = datetime.strptime(request.POST['fechamemo'], '%Y-%m-%d').date()
                fechaemision = datetime.strptime(request.POST['fechaemision'], '%Y-%m-%d').date()

                # Fecha de memo debe ser mayor o igual a fecha solicitud de certificación
                if fechamemo < certificacion.fecha.date():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de memorando debe ser mayor o igual a la fecha de solicitud", "showSwal": "True", "swalType": "warning"})

                # Fecha de emision debe ser mayor o igual a fecha de memo
                if fechaemision < fechamemo:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de emisión debe ser mayor o igual a la fecha de memorando", "showSwal": "True", "swalType": "warning"})

                # Actualizo la solicitud de certificacion
                certificacion.numeromemo = request.POST['numeromemo'].strip()
                certificacion.fechamemo = fechamemo
                certificacion.numerocomprobante = request.POST['numerocomprobante'].strip()
                certificacion.fechaemision = fechaemision
                certificacion.numeropartida = request.POST['numeropartida'].strip()

                if 'archivocertificacion' in request.FILES:
                    archivo._name = generar_nombre("certificacionpresupuestaria", archivo._name)
                    certificacion.archivo = archivo

                certificacion.estado = 2
                certificacion.save(request)

                if nuevoregistro:
                    # Obtengo estado CERTIFICACIÓN PRESUPUESTARIA EMITIDA POR FINANCIERO
                    estado = obtener_estado_solicitud(13, 30)

                    # Actualizo los estados de las postulaciones de la certificación
                    for detalle in certificacion.detalle():
                        postulacion = detalle.solicitud

                        # Actualizo el estado de la postulacion
                        postulacion.estado = estado
                        postulacion.save(request)

                        # Guardo el recorrido de la postulación
                        recorrido = RecorridoRegistro(
                            tiporegistro=2,
                            registroid=postulacion.id,
                            fecha=datetime.now().date(),
                            departamento=persona.mi_cargo_actual().unidadorganica,
                            persona=persona,
                            observacion=estado.observacion,
                            estado=estado
                        )
                        recorrido.save(request)

                    # Notificar al Coordinador de Investigación
                    personadestinatario = coordinador_investigacion()

                    # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                    listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                    # E-mail del destinatario
                    # lista_email_envio = personadestinatario.lista_emails_envio()
                    lista_email_envio = ['isaltosm@unemi.edu.ec']
                    lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                    lista_archivos_adjuntos = [certificacion.archivo]

                    asuntoemail = "Certificación Presupuestaria para Becas Docentes Emitida"
                    titulo = "Postulación Beca Docente"
                    tiponotificacion = "CERTPRESUPEMI"

                    send_html_mail(asuntoemail,
                                   "emails/postulacionbecadocente.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'nombrecoordinador': personadestinatario.nombre_completo_inverso(),
                                    'certificacion': certificacion,
                                    'detalles': certificacion.detalle(),
                                    'tiponotificacion': tiponotificacion,
                                    'saludo': 'Estimada' if personadestinatario.sexo_id == 1 else 'Estimado',
                                    },
                                   lista_email_envio,
                                   lista_email_cco,
                                   lista_archivos_adjuntos,
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                    log(u'%s agregó certificación presupuestaria para la solicitud de certificación: %s' % (persona, certificacion), request, "edit")
                else:
                    log(u'%s editó certificación presupuestaria para la solicitud de certificación: %s' % (persona, certificacion), request, "edit")

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'consolidarinformacion':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.POST['id'])))
                postulaciones = convocatoria.postulaciones_sin_consolidar()

                # Obtengo estado INFORMACIÓN CONSOLIDADA
                estado = obtener_estado_solicitud(13, 31)

                caracteres_a_quitar = "!\"\#$%&()=?¡'¿{}[],.-+*/|°^~:;"

                directorio = SITE_STORAGE + '/media/becadocente/consolidados'
                try:
                    os.stat(directorio)
                except:
                    os.mkdir(directorio)

                response = HttpResponse(content_type='application/zip')
                response['Content-Disposition'] = 'attachment; filename=becasdocentes_' + random.randint(1, 10000).__str__() + '.zip'

                nombrearchivoresultado = generar_nombre("becasdocentes" + str(convocatoria.iniciopos.year), "becasdocentes" + str(convocatoria.iniciopos.year) + ".zip")

                filename = os.path.join(directorio, nombrearchivoresultado)
                fantasy_zip = zipfile.ZipFile(filename, 'w')

                # Por cada postulación debo agrupar los archivos
                for postulacion in postulaciones:
                    # Creo la carpeta con los apellidos y nombres del postulante
                    nombrecarpeta = remover_caracteres(postulacion.profesor.persona.nombre_completo_inverso(), caracteres_a_quitar)
                    nombrecarpeta = nombrecarpeta.replace(" ", "_")
                    nombrecarpeta = elimina_tildes(remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(nombrecarpeta)))

                    # Informe técnico de otorgamiento de beca
                    informe = postulacion.informe_otorgamiento()
                    nombrearchivo = "INFORME_TECNICO_OTORGAMIENTO_BECA"
                    ext = informe.archivofirmado.__str__()[informe.archivofirmado.__str__().rfind("."):]
                    if os.path.exists(SITE_STORAGE + informe.archivofirmado.url):
                        fantasy_zip.write(SITE_STORAGE + informe.archivofirmado.url, nombrecarpeta + "/" + nombrearchivo + ext.lower())

                    # Resolución del comité de becas
                    resolucioncomite = postulacion.resolucion_comite(informe)
                    nombrearchivo = "RESOLUCION_COMITE_BECAS"
                    ext = resolucioncomite.archivofirmado.__str__()[resolucioncomite.archivofirmado.__str__().rfind("."):]
                    if os.path.exists(SITE_STORAGE + resolucioncomite.archivofirmado.url):
                        fantasy_zip.write(SITE_STORAGE + resolucioncomite.archivofirmado.url, nombrecarpeta + "/" + nombrearchivo + ext.lower())

                    # Certificación presupuestaria
                    certificacion = postulacion.certificacion_presupuestaria_emitida()
                    nombrearchivo = "CERTIFICACION_PRESUPUESTARIA"
                    ext = certificacion.archivo.__str__()[certificacion.archivo.__str__().rfind("."):]
                    if os.path.exists(SITE_STORAGE + certificacion.archivo.url):
                        fantasy_zip.write(SITE_STORAGE + certificacion.archivo.url, nombrecarpeta + "/" + nombrearchivo + ext.lower())

                    # Si la postulación tiene estado CERTIFICACIÓN PRESUPUESTARIA EMITIDA POR FINANCIERO
                    if postulacion.estado.valor == 30:
                        # Actualizar el estado de la postulación a CONSOLIDADO
                        postulacion.estado = estado
                        postulacion.save(request)

                        # Guardo el recorrido de la postulación
                        recorrido = RecorridoRegistro(
                            tiporegistro=2,
                            registroid=postulacion.id,
                            fecha=datetime.now().date(),
                            departamento=persona.mi_cargo_actual().unidadorganica,
                            persona=persona,
                            observacion=estado.observacion,
                            estado=estado
                        )
                        recorrido.save(request)

                fantasy_zip.close()

                archivo = SITE_STORAGE + '/media/becadocente/consolidados/' + nombrearchivoresultado
                # Aperturo el archivo generado
                with open(archivo, 'rb') as f:
                    data = f.read()

                buffer = io.BytesIO()
                buffer.write(data)
                zipcopia = buffer.getvalue()
                buffer.seek(0)
                buffer.close()

                # Extraigo el contenido
                archivocopiado = ContentFile(zipcopia)
                archivocopiado.name = nombrearchivoresultado

                # Borro el archivo creado de manera temporal
                os.remove(archivo)

                # Actualizo la convocatoria
                convocatoria.archivoconsolidado = archivocopiado
                convocatoria.save(request)

                # Notificar por e-mail al Vicerrector de Investigación
                personadestinatario = vicerrector_investigacion_posgrado()
                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                # E-mail del destinatario
                # lista_email_envio = personadestinatario.lista_emails_envio()
                lista_email_envio = ['isaltosm@unemi.edu.ec']
                lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                lista_archivos_adjuntos = []

                asuntoemail = "Información de Becas Docentes Consolidada por el Coordinador de Investigación"
                titulo = "Postulación Beca Docente"
                tiponotificacion = "INFOCONSOLIDADA"

                send_html_mail(asuntoemail,
                               "emails/postulacionbecadocente.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'nombrevicerrector': personadestinatario.nombre_completo_inverso(),
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimada' if personadestinatario.sexo_id == 1 else 'Estimado',
                                'convocatoria': convocatoria
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_archivos_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s procesó consolidación de información de las postulaciones a becas de la convocatoria: %s' % (persona, convocatoria), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Información consolidada con éxito", "showSwal": True, "documento": convocatoria.archivoconsolidado.url})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'revisarinformacionconsolidada':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.POST['id'])))
                postulaciones = convocatoria.postulaciones_consolidadas()

                # Obtengo estado POSTULACIÓN CON SOLICITUD DE TRATAMIENTO EN OCAS
                estado = obtener_estado_solicitud(13, 32)

                # Actualizo el estado y creo recorrido para cada una de las postulaciones
                for postulacion in postulaciones:
                    # Actualizar el estado de la postulación a POSTULACIÓN CON SOLICITUD DE TRATAMIENTO EN OCAS
                    postulacion.estado = estado
                    postulacion.save(request)

                    # Guardo el recorrido de la postulación
                    recorrido = RecorridoRegistro(
                        tiporegistro=2,
                        registroid=postulacion.id,
                        fecha=datetime.now().date(),
                        departamento=persona.mi_cargo_actual().unidadorganica,
                        persona=persona,
                        observacion=estado.observacion,
                        estado=estado
                    )
                    recorrido.save(request)

                log(u'%s revisó información consolidada de las postulaciones a becas de la convocatoria: %s' % (persona, convocatoria), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'notificarresultadoocas':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                resultado = int(request.POST['resultado'])
                archivo = request.FILES['archivoresolucion']
                descripcionarchivo = 'Archivo de la Resolución OCAS'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto la postulación de beca
                postulacion = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))

                # Obtengo estado APROBADO o RECHAZADO POR OCAS
                estado = obtener_estado_solicitud(13, 33) if resultado == 1 else obtener_estado_solicitud(13, 34)

                # Consulto el tipo de documento
                documento = Documento.objects.get(tipo=3)

                # Obtener número de páginas del archivo
                pdf2ReaderEvi = PyPDF2.PdfFileReader(archivo)
                numeropagina = pdf2ReaderEvi.numPages

                archivo._name = generar_nombre("resolucionocas", archivo._name)

                # Actualizo el estado de la postulación
                postulacion.estado = estado
                postulacion.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=estado.observacion,
                    estado=estado
                )
                recorrido.save(request)

                # Guardo el documento de la solicitud
                solicituddocumento = SolicitudDocumento(
                    solicitud=postulacion,
                    documento=documento,
                    archivofirmado=archivo,
                    numeropagina=numeropagina,
                    estado=2
                )
                solicituddocumento.save(request)

                # Notificar por e-mail
                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                # E-mail del destinatario solicitante
                # lista_email_envio = postulacion.profesor.persona.lista_emails_envio()
                lista_email_envio = ['isaltosm@unemi.edu.ec']
                lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                lista_archivos_adjuntos = [postulacion.archivo_resolucion_ocas().archivofirmado]

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                asuntoemail = "Postulación a Beca Docente Aprobada por OCAS" if resultado == 1 else "Postulación a Beca Docente Rechazada por OCAS"
                titulo = "Postulación Beca Docente"
                tiponotificacion = "APROOCAS" if resultado == 1 else "RECHOCAS"

                send_html_mail(asuntoemail,
                               "emails/postulacionbecadocente.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimada' if postulacion.profesor.persona.sexo_id == 1 else 'Estimado',
                                'nombrepersona': postulacion.profesor.persona.nombre_completo_inverso(),
                                'postulacion': postulacion
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_archivos_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                # En caso de ser APROBADO por OCAS se debe notificar a la Dirección Jurídica para la elaboración del contrato
                if resultado == 1:
                    # E-mail de la dirección jurídica
                    # lista_email_envio = ['correo12345@unemi.edu.ec']
                    lista_email_envio = ['isaltosm@unemi.edu.ec']

                    asuntoemail = "Requerimiento Emisión Contrato de Financiamiento para Beca Docente"
                    titulo = "Postulación Beca Docente"
                    tiponotificacion = "REQCONTRATO"

                    send_html_mail(asuntoemail,
                                   "emails/postulacionbecadocente.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'tiponotificacion': tiponotificacion,
                                    'saludo': 'Estimados',
                                    'genpersona': 'de la docente' if postulacion.profesor.persona.sexo_id == 1 else 'del docente',
                                    'nombrepersona': postulacion.profesor.persona.nombre_completo_inverso(),
                                    'postulacion': postulacion
                                    },
                                   lista_email_envio,
                                   lista_email_cco,
                                   lista_archivos_adjuntos,
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                log(u'%s notificó resultado %s de la resolución OCAS para la postulación a beca: %s' % (persona, "APROBADO" if resultado == 1 else "RECHAZADO", postulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})



        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Solicitud incorrecta.", "showSwal": "True", "swalType": "error"})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addconvocatoria':
                try:
                    data['title'] = u'Agregar Convocatoria para Becas'
                    form = ConvocatoriaBecaForm()
                    data['form'] = form
                    data['requisitos'] = Requisito.objects.filter(status=True, vigente=True).order_by('id')
                    return render(request, "adm_becadocente/addconvocatoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'editconvocatoria':
                try:
                    data['title'] = u'Editar Convocatoria para Becas'
                    convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.GET['id'])))

                    form = ConvocatoriaBecaForm(
                        initial={
                            'descripcion': convocatoria.descripcion,
                            'iniciopos': convocatoria.iniciopos,
                            'finpos': convocatoria.finpos,
                            # 'mensajepos': convocatoria.mensajepos,
                            'inicioveri': convocatoria.inicioveri,
                            'finveri': convocatoria.finveri,
                            # 'mensajeveri': convocatoria.mensajeveri,
                            'iniciosel': convocatoria.iniciosel,
                            'finsel': convocatoria.finsel,
                            # 'mensajesel': convocatoria.mensajesel,
                            'inicioadj': convocatoria.inicioadj,
                            'finadj': convocatoria.finadj,
                            # 'mensajeadj': convocatoria.mensajeadj,
                            'inicionoti': convocatoria.inicionoti,
                            'finnoti': convocatoria.finnoti,
                            # 'mensajenoti': convocatoria.mensajenoti
                        }
                    )

                    data['form'] = form
                    data['id'] = request.GET['id']
                    data['convocatoria'] = convocatoria
                    data['requisitos'] = convocatoria.requisitos()
                    # data['formatos'] = convocatoria.formatos()

                    return render(request, "adm_becadocente/editconvocatoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'requisitos':
                try:
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), f'&action={action}'

                    if search:
                        data['s'] = search
                        filtro = filtro & (Q(descripcion__icontains=search))
                        url_vars += f'&s={search}'

                    requisitos = Requisito.objects.filter(filtro).order_by('numero')

                    paging = MiPaginador(requisitos, 25)
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
                    data['url_vars'] = url_vars
                    data['requisitos'] = page.object_list
                    data['es_expertobecas'] = es_expertobecas
                    data['title'] = u'Requisitos para Becas de Docentes'

                    return render(request, "adm_becadocente/requisito.html", data)
                except Exception as ex:
                    pass

            elif action == 'addrequisito':
                try:
                    data['title'] = u'Agregar Requisito para Beca de Docentes'
                    # data['modalidades'] = Modalidad.objects.filter(status=True).order_by('id')
                    template = get_template("adm_becadocente/modal/addrequisito.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editrequisito':
                try:
                    data['title'] = u'Editar Requisito para Beca de Docentes'
                    data['requisitobeca'] = Requisito.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("adm_becadocente/modal/editrequisito.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'verificarconvocatoria':
                try:
                    data['title'] = u'%s Convocatoria para Beca de docentes' % request.GET['tipoverificacion']
                    convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.GET['idc'])))
                    tipoverificacion = request.GET['tipoverificacion'].upper()

                    if tipoverificacion == 'REVISAR':
                        estados = obtener_estados_solicitud(9, [2, 3])
                    elif tipoverificacion == 'VALIDAR':
                        estados = obtener_estados_solicitud(9, [4, 5])
                    elif tipoverificacion == 'APROBAR':
                        estados = obtener_estados_solicitud(9, [6, 7])
                    elif tipoverificacion == 'AUTORIZAR':
                        estados = obtener_estados_solicitud(9, [8, 9])
                    else:
                        estados = obtener_estados_solicitud(9, [10])

                    data['convocatoria'] = convocatoria
                    data['requisitos'] = x = convocatoria.requisitos()
                    data['estados'] = estados

                    template = get_template("adm_becadocente/verificarconvocatoria.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrarrecorrido':
                try:
                    data['title'] = u'Recorrido de la Convocatoria'
                    convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['convocatoria'] = convocatoria
                    data['recorrido'] = convocatoria.recorrido()
                    template = get_template("adm_becadocente/recorridoconvocatoria.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrartotales':
                try:
                    convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    title = u'Resumen Seguimiento Postulaciones - ' + convocatoria.descripcion
                    postulaciones = Solicitud.objects.filter(status=True, convocatoria=convocatoria).exclude(estado__valor=1).order_by('-fechasolicitud')

                    total = postulaciones.values("id").count()
                    validadas = postulaciones.values("id").filter(validada=True).count()
                    porvalidar = total - validadas
                    aceptadas = postulaciones.values("id").filter(estadovalidacion=1).count()
                    novedad = postulaciones.values("id").filter(estadovalidacion=2).count()
                    rechazadas = postulaciones.values("id").filter(estadovalidacion=3).count()

                    solicitudes = []

                    solicitudes.append({"descripcion": "Solicitudes de beca", "valor": total, "color": "inverse"})
                    solicitudes.append({"descripcion": "Solicitudes validadas", "valor": validadas, "color": "info"})
                    solicitudes.append({"descripcion": "Solicitudes pendientes de validar", "valor": porvalidar, "color": "warning"})
                    solicitudes.append({"descripcion": "Solicitudes aceptadas", "valor": aceptadas, "color": "success"})
                    solicitudes.append({"descripcion": "Solicitudes con novedades", "valor": novedad, "color": "warning"})
                    solicitudes.append({"descripcion": "Solicitudes rechazadas", "valor": rechazadas, "color": "important"})

                    informesjuridico = []
                    solicitados = postulaciones.values("id").filter(estadovalidacion=1, criteriojuridico=True).count()
                    generados = postulaciones.values("id").filter(estadovalidacion=1, criteriojuridico=True, informejgen=True).count()
                    porgenerar = postulaciones.values("id").filter(estadovalidacion=1, criteriojuridico=True, informejgen=False).count()

                    informesjuridico.append({"descripcion": "Informes jurídicos solicitados", "valor": solicitados, "color": "inverse"})
                    informesjuridico.append({"descripcion": "Informes jurídicos generados", "valor": generados, "color": "info"})
                    informesjuridico.append({"descripcion": "Informes jurídicos pendientes de generar", "valor": porgenerar, "color": "warning"})

                    informesotorgamiento = []
                    solicitados1 = postulaciones.values("id").filter(estadovalidacion=1, criteriojuridico=False).count()
                    solicitados2 = postulaciones.values("id").filter(estadovalidacion=1, criteriojuridico=True, informejgen=True).count()
                    solicitados = solicitados1 + solicitados2
                    coninforme = postulaciones.values("id").filter(estadovalidacion=1, informeogen=True).count()
                    sininforme = solicitados - coninforme

                    aceptadodoc = postulaciones.values("id").filter(estadovalidacion=1, informeogen=True, estadoinformeo=2).count()
                    pendientedoc = postulaciones.values("id").filter(estadovalidacion=1, informeogen=True, estadoinformeo=3).count()
                    novedaddoc = postulaciones.values("id").filter(estadovalidacion=1, informeogen=True, estadoinformeo=4).count()

                    informesotorgamiento.append({"descripcion": "Informes de otorgamiento solicitados", "valor": solicitados, "color": "inverse"})
                    informesotorgamiento.append({"descripcion": "Informes de otorgamiento generados", "valor": coninforme, "color": "info"})
                    informesotorgamiento.append({"descripcion": "Informes de otorgamiento pendientes de generar", "valor": sininforme, "color": "warning"})
                    informesotorgamiento.append({"descripcion": "Informes de otorgamiento aceptados por docentes", "valor": aceptadodoc, "color": "success"})
                    informesotorgamiento.append({"descripcion": "Informes de otorgamiento pendientes de revisar por docente", "valor": pendientedoc, "color": "warning"})
                    informesotorgamiento.append({"descripcion": "Informes de otorgamiento con novedad", "valor": novedaddoc, "color": "important"})

                    informescoordinador = []
                    notificar = postulaciones.values("id").filter(estadovalidacion=1, informeogen=True, estadoinformeo=2).count()
                    notificadosvi = postulaciones.values("id").filter(estadovalidacion=1, informeogen=True, estadoinformeo=2, inotificadovi=True).count()
                    pornotificarvi = postulaciones.values("id").filter(estadovalidacion=1, informeogen=True, estadoinformeo=2, inotificadovi=False).count()

                    informescoordinador.append({"descripcion": "Informes a notificar a Vicerrector de Investigación y Posgrado", "valor": notificar, "color": "inverse"})
                    informescoordinador.append({"descripcion": "Informes notificados a Vicerrector de Investigación y  Posgrado", "valor": notificadosvi, "color": "info"})
                    informescoordinador.append({"descripcion": "Informes pendientes de notificar a Vicerrector de Investigación y Posgrado", "valor": pornotificarvi, "color": "warning"})

                    informesvicerrector = []
                    revisar = postulaciones.values("id").filter(estadovalidacion=1, informeogen=True, estadoinformeo=2, inotificadovi=True).count()
                    revisadovi = postulaciones.values("id").filter(estadovalidacion=1, informeogen=True, estadoinformeo=2, inotificadovi=True, irevisadovi=True).count()
                    porrevisarvi = postulaciones.values("id").filter(estadovalidacion=1, informeogen=True, estadoinformeo=2, inotificadovi=True, irevisadovi=False).count()
                    notificadocb = postulaciones.values("id").filter(estadovalidacion=1, informeogen=True, estadoinformeo=2, inotificadovi=True, irevisadovi=True, inotificadocb=True).count()
                    pornotificarcb = postulaciones.values("id").filter(estadovalidacion=1, informeogen=True, estadoinformeo=2, inotificadovi=True, irevisadovi=True, inotificadocb=False).count()

                    informesvicerrector.append({"descripcion": "Informes a revisar", "valor": revisar, "color": "inverse"})
                    informesvicerrector.append({"descripcion": "Informes revisados", "valor": revisadovi, "color": "info"})
                    informesvicerrector.append({"descripcion": "Informes por revisar", "valor": porrevisarvi, "color": "warning"})
                    informesvicerrector.append({"descripcion": "Informes notificados al comité de becas", "valor": notificadocb, "color": "success"})
                    informesvicerrector.append({"descripcion": "Informes pendientes de notificar al comité de becas", "valor": pornotificarcb, "color": "warning"})

                    comitebeca = []
                    resolsol = postulaciones.values("id").filter(irevisadovi=True, inotificadocb=True).count()
                    resolgen = postulaciones.values("id").filter(irevisadovi=True, inotificadocb=True, irevisadocb=True).count()
                    resolpen = postulaciones.values("id").filter(irevisadovi=True, inotificadocb=True, irevisadocb=False).count()
                    resolfav = postulaciones.values("id").filter(irevisadovi=True, inotificadocb=True, irevisadocb=True, resultadocb=1).count()
                    resolnofav = postulaciones.values("id").filter(irevisadovi=True, inotificadocb=True, irevisadocb=True, resultadocb=2).count()

                    comitebeca.append({"descripcion": "Resoluciones solicitadas", "valor": resolsol, "color": "inverse"})
                    comitebeca.append({"descripcion": "Resoluciones generadas", "valor": resolgen, "color": "info"})
                    comitebeca.append({"descripcion": "Resoluciones pendientes", "valor": resolpen, "color": "warning"})
                    comitebeca.append({"descripcion": "Resoluciones favorables", "valor": resolfav, "color": "success"})
                    comitebeca.append({"descripcion": "Resoluciones no favorables", "valor": resolnofav, "color": "important"})

                    data['solicitudes'] = solicitudes
                    data['informesjuridico'] = informesjuridico
                    data['informesotorgamiento'] = informesotorgamiento
                    data['informescoordinador'] = informescoordinador
                    data['informesvicerrector'] = informesvicerrector
                    data['comitebeca'] = comitebeca

                    template = get_template("adm_becadocente/resumenpostulaciones.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            # elif action == 'convocatorias':
            #     try:
            #         search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
            #
            #         # if search:
            #         #     data['s'] = search
            #         #     filtro = filtro & (Q(nombre__unaccent__icontains=search))
            #         #     url_vars += '&s=' + search
            #         convocatorias = Convocatoria.objects.filter(filtro).order_by('-iniciopos', '-finpos')
            #         es_personaljuridico = persona.pertenece_a_departamento(122)
            #
            #         paging = MiPaginador(convocatorias, 25)
            #         p = 1
            #         try:
            #             paginasesion = 1
            #             if 'paginador' in request.session:
            #                 paginasesion = int(request.session['paginador'])
            #             if 'page' in request.GET:
            #                 p = int(request.GET['page'])
            #             else:
            #                 p = paginasesion
            #             try:
            #                 page = paging.page(p)
            #             except:
            #                 p = 1
            #             page = paging.page(p)
            #         except:
            #             page = paging.page(p)
            #         request.session['paginador'] = p
            #         data['paging'] = paging
            #         data['rangospaging'] = paging.rangos_paginado(p)
            #         data['page'] = page
            #         data['url_vars'] = url_vars
            #         data['convocatorias'] = page.object_list
            #         data['title'] = u'Convocatorias para Becas y/o Ayudas Económicas para Docentes'
            #         data['es_personaljuridico'] = es_personaljuridico
            #         data['enlaceatras'] = "/ges_investigacion?action=convocatorias"
            #
            #         return render(request, "adm_becadocente/view.html", data)
            #     except Exception as ex:
            #         pass

            elif action == 'postulaciones':
                try:
                    search, url_vars = request.GET.get('s', ''), '&action=' + action
                    idc, ids = request.GET.get('idc', ''), request.GET.get('id', '')
                    url_vars += '&idc=' + idc

                    data['convocatoria'] = convocatoria = Convocatoria.objects.get(pk=int(encrypt(idc)))

                    if ids:
                        data['ids'] = ids
                        postulaciones = Solicitud.objects.filter(pk=int(encrypt(ids)))
                        url_vars += '&id=' + ids
                    else:
                        if persona.es_coordinador_investigacion():
                            postulaciones = Solicitud.objects.filter(status=True, convocatoria=convocatoria, estadovalidacion=1, informeogen=True, estadoinformeo=2).exclude(estado__valor=1).order_by('-fechasolicitud')
                        elif persona.es_vicerrector_investigacion():
                            postulaciones = Solicitud.objects.filter(status=True, convocatoria=convocatoria, estadovalidacion=1, informeogen=True, estadoinformeo=2, inotificadovi=True).exclude(estado__valor=1).order_by('-fechasolicitud')
                        elif persona.pertenece_a_departamento(122):
                            postulaciones = Solicitud.objects.filter(status=True, convocatoria=convocatoria, criteriojuridico=True).exclude(estado__valor=1).order_by('-fechasolicitud')
                        elif persona.pertenece_a_departamento(95):
                            data['espersonalfinanciero'] = True
                            postulaciones = Solicitud.objects.filter(status=True, convocatoria=convocatoria, cpresupuestaria=True).order_by('-fechasolicitud')
                        else:
                            postulaciones = Solicitud.objects.filter(status=True, convocatoria=convocatoria).exclude(estado__valor=1).order_by('-fechasolicitud')


                    if search:
                        data['s'] = search
                        ss = search.split(" ")
                        if len(ss) == 1:
                            postulaciones = postulaciones.filter(Q(profesor__persona__nombres__icontains=search) |
                                                                 Q(profesor__persona__apellido1__icontains=search) |
                                                                 Q(profesor__persona__apellido2__icontains=search))
                        else:
                            postulaciones = postulaciones.filter(profesor__persona__apellido1__contains=ss[0],
                                                                 profesor__persona__apellido2__contains=ss[1])

                        url_vars += '&s=' + search

                    paging = MiPaginador(postulaciones, 25)
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
                    data['url_vars'] = url_vars
                    data['postulaciones'] = page.object_list
                    data['total'] = total = postulaciones.values("id").count()

                    titulo2 = ''

                    if persona.es_analista_investigacion():
                        titulo2 = ''
                    elif persona.es_analista_juridico() or persona.es_experto_juridico() or persona.es_director_juridico():
                        titulo2 = ' - Registro de Informes Jurídicos'
                        data['espersonaljuridico'] = True
                    elif persona.es_coordinador_investigacion():
                        titulo2 = ' - Revisión y Notificación de Informes al Vicerrector de Investigación y Posgrado'
                    elif persona.es_vicerrector_investigacion():
                        titulo2 = ' - Revisión y Notificación de Informes al Comité Institucional de Becas'
                        data['pornotificarcb'] = postulaciones.values("id").filter(irevisadovi=True, inotificadocb=False).count()

                    data['secretariocomite'] = secretariocomite = convocatoria.es_secretario_comite(persona)
                    # data['title'] = u'Postulaciones a Becas de Docentes (' + convocatoria.descripcion + ')' + titulo2
                    data['title'] = u'Postulaciones a Becas de Docentes (' + convocatoria.descripcion + ')'

                    return render(request, "adm_becadocente/postulaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'mostrarrecorridopostulacion':
                try:
                    title = u'Recorrido de la Postulación a Beca'
                    solicitud = Solicitud.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitud'] = solicitud
                    data['recorrido'] = solicitud.recorrido()
                    template = get_template("pro_becadocente/recorridopostulacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'revisarpostulacion':
                try:
                    data['title'] = u'Revisar y Validar Postulación a Beca'
                    postulacion = Solicitud.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['postulacion'] = postulacion
                    data['requisitos'] = requisitos = postulacion.requisitos()
                    data['primerdocumento'] = requisitos[0]
                    data['documentos'] = postulacion.documentos()
                    data['faltacarta'] = faltacarta = requisitos.filter(requisito__numero=5, estado=6).exists()
                    data['requisitocarta'] = requisitos.filter(requisito__numero=5)[0].requisito.descripcion if faltacarta else ''

                    estadosrequisito = [
                        {"id": 2, "descripcion": "VALIDADO"},
                        {"id": 4, "descripcion": "NOVEDAD"}
                    ]

                    data['estadosrequisito'] = estadosrequisito
                    data['presupuesto'] = presupuesto = postulacion.presupuesto_solicitud()
                    data['cantidadperiodos'] = cantidadperiodos = presupuesto.numeroperiodo

                    listaanios = []
                    anioi = postulacion.inicio.year
                    aniof = postulacion.fin.year
                    total = (aniof - anioi) + 1

                    for n in range(total):
                        listaanios.append(anioi)
                        anioi += 1

                    data['colspancab'] = (cantidadperiodos * 2) + 4
                    data['anios'] = listaanios
                    data['rubros'] = postulacion.rubros()

                    return render(request, "adm_becadocente/revisarrequisitos.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinformeotorgamiento':
                try:
                    data['title'] = u'Agregar Informe de Factibilidad de Otorgamiento de Beca'
                    data['postulacion'] = postulacion = Solicitud.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['coordinador'] = coordinador_investigacion()
                    data['director'] = vicerrector_investigacion_posgrado()
                    data['anio1'] = anio1 = postulacion.inicio.year
                    data['presupuesto1'] = postulacion.presupuesto_solicitud().total_anio(anio1)
                    data['requisitos'] = postulacion.requisitos()
                    data['documentos'] = postulacion.documentos()

                    data['presupuesto'] = presupuesto = postulacion.presupuesto_solicitud()
                    data['cantidadperiodos'] = cantidadperiodos = presupuesto.numeroperiodo

                    listaanios = []
                    anioi = postulacion.inicio.year
                    aniof = postulacion.fin.year
                    total = (aniof - anioi) + 1

                    for n in range(total):
                        listaanios.append(anioi)
                        anioi += 1

                    data['colspancab'] = (cantidadperiodos * 2) + 4
                    data['anios'] = listaanios
                    data['rubros'] = postulacion.rubros()
                    data['fecha'] = datetime.now().date()

                    return render(request, "adm_becadocente/addinformeotorgamiento.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinformeotorgamiento':
                try:
                    data['title'] = u'Editar Informe de Factibilidad de Otorgamiento de Beca'
                    data['informe'] = informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['postulacion'] = postulacion = informe.solicitud

                    data['coordinador'] = coordinador_investigacion()
                    data['director'] = vicerrector_investigacion_posgrado()
                    data['anio1'] = anio1 = postulacion.inicio.year
                    data['presupuesto1'] = postulacion.presupuesto_solicitud().total_anio(anio1)
                    data['requisitos'] = postulacion.requisitos()
                    data['documentos'] = postulacion.documentos()

                    data['presupuesto'] = presupuesto = postulacion.presupuesto_solicitud()
                    data['cantidadperiodos'] = cantidadperiodos = presupuesto.numeroperiodo

                    listaanios = []
                    anioi = postulacion.inicio.year
                    aniof = postulacion.fin.year
                    total = (aniof - anioi) + 1

                    for n in range(total):
                        listaanios.append(anioi)
                        anioi += 1

                    data['colspancab'] = (cantidadperiodos * 2) + 4
                    data['anios'] = listaanios
                    data['rubros'] = postulacion.rubros()
                    data['anexos'] = informe.anexos()
                    data['fecha'] = datetime.now().date()

                    return render(request, "adm_becadocente/editinformeotorgamiento.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirinformeotorgamiento':
                try:
                    data['title'] = u'Subir Informe de Otorgamiento de Beca Firmado'
                    data['informe'] = informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitud'] = informe.solicitud
                    data['accionguardar'] = 'subirinformeotorgamiento'

                    template = get_template("adm_becadocente/subirinforme.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addinformejuridico':
                try:
                    data['title'] = u'Agregar Informe Jurídico de Factibilidad de Beca'
                    data['postulacion'] = postulacion = Solicitud.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['director'] = director_juridico()

                    data['anio1'] = anio1 = postulacion.inicio.year
                    data['presupuesto1'] = postulacion.presupuesto_solicitud().total_anio(anio1)
                    data['requisitos'] = postulacion.requisitos()
                    data['documentos'] = postulacion.documentos()

                    data['presupuesto'] = presupuesto = postulacion.presupuesto_solicitud()
                    data['cantidadperiodos'] = cantidadperiodos = presupuesto.numeroperiodo

                    listaanios = []
                    anioi = postulacion.inicio.year
                    aniof = postulacion.fin.year
                    total = (aniof - anioi) + 1

                    for n in range(total):
                        listaanios.append(anioi)
                        anioi += 1

                    data['colspancab'] = (cantidadperiodos * 2) + 4
                    data['anios'] = listaanios
                    data['rubros'] = postulacion.rubros()
                    data['fecha'] = datetime.now().date()

                    return render(request, "adm_becadocente/addinformejuridico.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinformejuridico':
                try:
                    data['title'] = u'Editar Informe Jurídico de Factibilidad de Beca'
                    data['informe'] = informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['postulacion'] = postulacion = informe.solicitud

                    data['director'] = director_juridico()

                    data['anio1'] = anio1 = postulacion.inicio.year
                    data['presupuesto1'] = postulacion.presupuesto_solicitud().total_anio(anio1)
                    data['requisitos'] = postulacion.requisitos()
                    data['documentos'] = postulacion.documentos()

                    data['presupuesto'] = presupuesto = postulacion.presupuesto_solicitud()
                    data['cantidadperiodos'] = cantidadperiodos = presupuesto.numeroperiodo

                    listaanios = []
                    anioi = postulacion.inicio.year
                    aniof = postulacion.fin.year
                    total = (aniof - anioi) + 1

                    for n in range(total):
                        listaanios.append(anioi)
                        anioi += 1

                    data['colspancab'] = (cantidadperiodos * 2) + 4
                    data['anios'] = listaanios
                    data['rubros'] = postulacion.rubros()
                    data['anexos'] = informe.anexos()
                    data['fecha'] = datetime.now().date()

                    return render(request, "adm_becadocente/editinformejuridico.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirinformejuridico':
                try:
                    data['title'] = u'Subir Informe Jurídico de Factibilidad de Beca Firmado'
                    data['informe'] = informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.GET['id'])))

                    # Verifico que el tipo de documento INFORME JURÍDICO DE FACTIBILIDAD esté asignado a la convocatoria
                    if not DocumentoConvocatoria.objects.filter(status=True, convocatoria=informe.solicitud.convocatoria, documento__tipo=2).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El documento [Informe Jurídico de Factibilidad de Becas] no está asignado a la convocatoria"})

                    data['solicitud'] = informe.solicitud
                    data['accionguardar'] = 'subirinformejuridico'
                    template = get_template("adm_becadocente/subirinforme.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'notificarinformeotorgamiento':
                try:
                    data['title'] = u'Notificar Informe de Factibilidad de Otorgamiento de Beca'
                    data['informe'] = informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitud'] = informe.solicitud

                    estados = []
                    estados.append({"id": 4, "descripcion": "VALIDADO"})
                    estados.append({"id": 5, "descripcion": "NOVEDADES"})
                    data['estados'] = estados

                    template = get_template("adm_becadocente/notificarinforme.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'revisarinformeotorgamiento':
                try:
                    data['title'] = u'Revisar Informe de Factibilidad de Otorgamiento de Beca'
                    data['informe'] = informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitud'] = informe.solicitud

                    estados = []
                    estados.append({"id": 3, "descripcion": "REVISADO"})
                    data['estados'] = estados

                    template = get_template("adm_becadocente/revisarinforme.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'emitirresolucion':
                try:
                    data['title'] = u'Emitir Resolución para Postulación a Beca (Comité de Becas)'
                    postulacion = Solicitud.objects.get(pk=int(encrypt(request.GET['id'])))
                    resolucion = postulacion.resolucion_comite(postulacion.informe_otorgamiento())
                    data['resolucion'] = resolucion
                    data['postulacion'] = postulacion
                    data['requisitos'] = requisitos = postulacion.requisitos()
                    data['primerdocumento'] = requisitos[0]
                    data['documentos'] = postulacion.documentos()
                    data['faltacarta'] = faltacarta = requisitos.filter(requisito__numero=5, estado=6).exists()
                    data['requisitocarta'] = requisitos.filter(requisito__numero=5)[0].requisito.descripcion if faltacarta else ''
                    data['presupuesto'] = presupuesto = postulacion.presupuesto_solicitud()
                    data['cantidadperiodos'] = cantidadperiodos = presupuesto.numeroperiodo

                    listaanios = []
                    anioi = postulacion.inicio.year
                    aniof = postulacion.fin.year
                    total = (aniof - anioi) + 1

                    for n in range(total):
                        listaanios.append(anioi)
                        anioi += 1

                    data['colspancab'] = (cantidadperiodos * 2) + 4
                    data['anios'] = listaanios
                    data['rubros'] = postulacion.rubros()
                    data['secretariocomite'] = postulacion.convocatoria.es_secretario_comite(persona)

                    return render(request, "adm_becadocente/emitirresolucion.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirresolucion':
                try:
                    data['title'] = u'Subir Resolución Firmada'
                    data['resolucion'] = resolucion = ResolucionComite.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitud'] = resolucion.solicitud

                    template = get_template("adm_becadocente/subirresolucion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'firmarinformejuridico':
                try:
                    tipofirma = request.GET['tipofirma']
                    data['informe'] = informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['iddoc'] = informe.id
                    data['tipofirma'] = tipofirma

                    # Verifico que el tipo de documento INFORME JURÍDICO DE FACTIBILIDAD esté asignado a la convocatoria
                    if not DocumentoConvocatoria.objects.filter(status=True, convocatoria=informe.solicitud.convocatoria, documento__tipo=2).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El documento [Informe Jurídico de Factibilidad de Becas] no está asignado a la convocatoria"})

                    solicitud = informe.solicitud

                    if tipofirma == 'ELA':  # Persona que elabora
                        data['title'] = u'Firmar Informe Jurídico de Beca. Elaborado por: {}'.format(informe.elabora.nombre_completo_inverso())
                        data['idper'] = informe.elabora.id
                    elif tipofirma == 'VER':  # Persona que verifica
                        data['title'] = u'Firmar Informe Jurídico de Beca. Verificado por: {}'.format(informe.verifica.nombre_completo_inverso())
                        data['idper'] = informe.verifica.id
                    else:  # Persona que aprueba
                        data['title'] = u'Firmar Informe Jurídico de Beca. Aprobado por: {}'.format(informe.aprueba.nombre_completo_inverso())
                        data['idper'] = informe.aprueba.id

                    data['mensaje'] = "Firma de Informe Jurídico de Beca N° <b>{}</b> del docente <b>{}</b> para el programa <b>{}</b>".format(informe.numero, solicitud.profesor.persona.nombre_completo_inverso(), solicitud.programa)
                    data['accionfirma'] = "firmarinformejuridico"

                    template = get_template("pro_becadocente/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'firmarinformeotorgamiento':
                try:
                    tipofirma = request.GET['tipofirma']
                    data['informe'] = informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['iddoc'] = informe.id
                    data['tipofirma'] = tipofirma

                    # # Verifico que el tipo de documento INFORME JURÍDICO DE FACTIBILIDAD esté asignado a la convocatoria
                    # if not DocumentoConvocatoria.objects.filter(status=True, convocatoria=informe.solicitud.convocatoria, documento__tipo=2).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"El documento [Informe Jurídico de Factibilidad de Becas] no está asignado a la convocatoria"})

                    solicitud = informe.solicitud

                    if tipofirma == 'ELA':  # Persona que elabora
                        data['title'] = u'Firmar Informe Otorgamiento de Beca. Elaborado por: {}'.format(informe.elabora.nombre_completo_inverso())
                        data['idper'] = informe.elabora.id
                    elif tipofirma == 'VER':  # Persona que verifica
                        data['title'] = u'Firmar Informe Otorgamiento de Beca. Verificado por: {}'.format(informe.verifica.nombre_completo_inverso())
                        data['idper'] = informe.verifica.id
                    else:  # Persona que aprueba
                        data['title'] = u'Firmar Informe Otorgamiento de Beca. Aprobado por: {}'.format(informe.aprueba.nombre_completo_inverso())
                        data['idper'] = informe.aprueba.id

                    data['mensaje'] = "Firma de Informe de Otorgamiento de Beca N° <b>{}</b> del docente <b>{}</b> para el programa <b>{}</b>".format(informe.numero, solicitud.profesor.persona.nombre_completo_inverso(), solicitud.programa)
                    data['accionfirma'] = action

                    template = get_template("pro_becadocente/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editpresupuesto':
                try:
                    data['title'] = u'Editar Presupuesto a Postulación de Beca'
                    data['postulacion'] = postulacion = Solicitud.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['convocatoria'] = convocatoria = postulacion.convocatoria
                    data['presupuesto'] = presupuesto = postulacion.presupuesto_solicitud()
                    data['cantidadperiodos'] = cantidadperiodos = presupuesto.numeroperiodo

                    listaanios = []
                    anioi = postulacion.inicio.year
                    aniof = postulacion.fin.year
                    total = (aniof - anioi) + 1

                    for n in range(total):
                        listaanios.append(anioi)
                        anioi += 1

                    data['colspancab'] = (cantidadperiodos * 2) + 4
                    data['anios'] = listaanios
                    data['rubros'] = postulacion.rubros()

                    return render(request, "adm_becadocente/editpresupuesto.html", data)
                except Exception as ex:
                    pass

            elif action == 'firmarresolucion':
                try:
                    tipofirma = request.GET['tipofirma']
                    data['resolucion'] = resolucion = ResolucionComite.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['iddoc'] = resolucion.id
                    data['tipofirma'] = tipofirma

                    solicitud = resolucion.solicitud

                    if tipofirma == 'VICE':  # Vicerrector
                        data['title'] = u'Firmar Resolución Comité: {}'.format(resolucion.personavice.nombre_completo_inverso())
                        data['idper'] = resolucion.personavice.id
                    else:  # Coordinador
                        data['title'] = u'Firmar Resolución Comité: {}'.format(resolucion.personacoord.nombre_completo_inverso())
                        data['idper'] = resolucion.personacoord.id

                    data['mensaje'] = "Firma de Resolución de Comité Institucional de Becas <b>{}</b> del docente <b>{}</b> para el programa <b>{}</b>".format(resolucion.numero, solicitud.profesor.persona.nombre_completo_inverso(), solicitud.programa)
                    data['accionfirma'] = action

                    template = get_template("pro_becadocente/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'certificaciones':
                try:
                    search, url_vars = request.GET.get('s', ''), '&action=' + action
                    idc, ids = request.GET.get('idc', ''), request.GET.get('id', '')
                    url_vars += '&idc=' + idc

                    data['convocatoria'] = convocatoria = Convocatoria.objects.get(pk=int(encrypt(idc)))

                    if persona.pertenece_a_departamento(95):
                        data['espersonalfinanciero'] = True

                    certificaciones = CertificacionPresupuestaria.objects.filter(status=True, convocatoria=convocatoria).order_by('-id')

                    paging = MiPaginador(certificaciones, 25)
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
                    data['url_vars'] = url_vars
                    data['certificaciones'] = page.object_list
                    data['title'] = u'Solicitudes Certificaciones Presupuestarias - (' + convocatoria.descripcion + ')'
                    return render(request, "adm_becadocente/certificaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'addsolicitudcertificacion':
                try:
                    data['title'] = u'Agregar Solicitud de Certificación Presupuestaria'
                    data['convocatoria'] = convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.GET['idc'])))
                    data['postulaciones'] = convocatoria.postulaciones_sin_certificacion()
                    data['fecha'] = datetime.now().date()

                    template = get_template("adm_becadocente/addsolicitudcertificacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informacionsolicitudcertificacion':
                try:
                    title = u'Información Solicitud de Certificación Presupuestaria'
                    certificacion = CertificacionPresupuestaria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['certificacion'] = certificacion
                    data['detalles'] = certificacion.detalle()
                    template = get_template("adm_becadocente/infosolicitudcertificacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subircertificacion':
                try:
                    certificacion = CertificacionPresupuestaria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Agregar Certificación Presupuestaria' if not certificacion.numeromemo else u'Editar Certificación Presupuestaria'
                    data['certificacion'] = certificacion
                    data['fecha'] = datetime.now().date()
                    template = get_template("adm_becadocente/subircertificacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'consolidarinformacion':
                try:
                    data['title'] = u'Consolidar Información de Becas Docentes'
                    data['convocatoria'] = convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.GET['idc'])))
                    postulaciones = convocatoria.postulaciones_sin_consolidar()
                    if not postulaciones:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No existen registros de postulaciones de becas con certificaciones presupuestarias emitidas para consolidar información", "showSwal": "True", "swalType": "warning"})

                    data['postulaciones'] = postulaciones
                    data['totalpostulaciones'] = postulaciones.count()

                    total_megas_informe = 0
                    total_megas_resolucion = 0
                    total_megas_certificacion = 0

                    for postulacion in postulaciones:
                        archivoinforme = postulacion.informe_otorgamiento().archivofirmado.url
                        archivo = SITE_STORAGE + archivoinforme
                        file_size = os.path.getsize(archivo)
                        total_megas_informe += Decimal(null_to_decimal((file_size / 1024 ** 2), 2)).quantize(Decimal('.01'))

                        archivoresolucion = postulacion.resolucion_comite(postulacion.informe_otorgamiento()).archivofirmado.url
                        archivo = SITE_STORAGE + archivoresolucion
                        file_size = os.path.getsize(archivo)
                        total_megas_resolucion += Decimal(null_to_decimal((file_size / 1024 ** 2), 2)).quantize(Decimal('.01'))

                        archivocertificacion = postulacion.certificacion_presupuestaria_emitida().archivo.url
                        archivo = SITE_STORAGE + archivocertificacion
                        file_size = os.path.getsize(archivo)
                        total_megas_certificacion += Decimal(null_to_decimal((file_size / 1024 ** 2), 2)).quantize(Decimal('.01'))

                    data['tamanioinformes'] = total_megas_informe
                    data['tamanioresoluciones'] = total_megas_resolucion
                    data['tamaniocertificaciones'] = total_megas_certificacion
                    data['tamaniototal'] = total_megas_informe + total_megas_resolucion + total_megas_certificacion

                    vicerrectorposgrado = vicerrector_investigacion_posgrado()
                    data['cargo'] = vicerrectorposgrado.mi_cargo_actual().denominacionpuesto

                    template = get_template("adm_becadocente/consolidarinformacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'revisarinformacionconsolidada':
                try:
                    data['title'] = u'Revisar Información Consolidada de Becas Docentes'
                    data['convocatoria'] = convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.GET['idc'])))
                    postulaciones = convocatoria.postulaciones_consolidadas()
                    if not postulaciones:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No existe información consolidada pendiente de revisar ", "showSwal": "True", "swalType": "warning"})

                    data['postulaciones'] = postulaciones
                    data['totalpostulaciones'] = postulaciones.count()

                    total_megas_informe = 0
                    total_megas_resolucion = 0
                    total_megas_certificacion = 0

                    for postulacion in postulaciones:
                        archivoinforme = postulacion.informe_otorgamiento().archivofirmado.url
                        archivo = SITE_STORAGE + archivoinforme
                        file_size = os.path.getsize(archivo)
                        total_megas_informe += Decimal(null_to_decimal((file_size / 1024 ** 2), 2)).quantize(Decimal('.01'))

                        archivoresolucion = postulacion.resolucion_comite(postulacion.informe_otorgamiento()).archivofirmado.url
                        archivo = SITE_STORAGE + archivoresolucion
                        file_size = os.path.getsize(archivo)
                        total_megas_resolucion += Decimal(null_to_decimal((file_size / 1024 ** 2), 2)).quantize(Decimal('.01'))

                        archivocertificacion = postulacion.certificacion_presupuestaria_emitida().archivo.url
                        archivo = SITE_STORAGE + archivocertificacion
                        file_size = os.path.getsize(archivo)
                        total_megas_certificacion += Decimal(null_to_decimal((file_size / 1024 ** 2), 2)).quantize(Decimal('.01'))

                    data['tamanioinformes'] = total_megas_informe
                    data['tamanioresoluciones'] = total_megas_resolucion
                    data['tamaniocertificaciones'] = total_megas_certificacion
                    data['tamaniototal'] = total_megas_informe + total_megas_resolucion + total_megas_certificacion

                    template = get_template("adm_becadocente/revisarinformacionconsolidada.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'notificarresultadoocas':
                try:
                    data['title'] = u'Notificar Resultado de la Resolución de OCAS'
                    data['postulacion'] = postulacion = Solicitud.objects.get(pk=int(encrypt(request.GET['id'])))

                    # Verifico que el tipo de documento RESOLUCIÓN OCAS esté asignado a la convocatoria
                    if not DocumentoConvocatoria.objects.filter(status=True, convocatoria=postulacion.convocatoria, documento__tipo=3).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El documento [Resolución OCAS] no está asignado a la convocatoria ", "showSwal": "True", "swalType": "warning"})

                    template = get_template("adm_becadocente/notificarresultadoocas.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            try:
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''

                if search:
                    data['s'] = search
                    filtro = filtro & (Q(descripcion__icontains=search))
                    url_vars += '&s=' + search

                convocatorias = Convocatoria.objects.filter(filtro).order_by('-iniciopos', '-finpos')
                # es_personaljuridico = persona.pertenece_a_departamento(122)

                paging = MiPaginador(convocatorias, 25)
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
                data['url_vars'] = url_vars
                data['convocatorias'] = page.object_list
                # data['es_personaljuridico'] = es_personaljuridico
                data['es_expertobecas'] = es_expertobecas
                data['title'] = u'Convocatorias para Becas y/o Ayudas Económicas para Docentes'

                return render(request, "adm_becadocente/view.html", data)
            except Exception as ex:
                pass
