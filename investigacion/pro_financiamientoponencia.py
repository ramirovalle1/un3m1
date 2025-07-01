# -*- coding: UTF-8 -*-
import io
import json
import os
from math import ceil

import PyPDF2
from datetime import time, datetime
from decimal import Decimal

import requests
from dateutil import relativedelta
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.core.files import File as DjangoFile
from fitz import fitz
from xlwt import easyxf, XFStyle, Workbook
import random

from core.firmar_documentos import firmar
from core.firmar_documentos_ec import JavaFirmaEc
from decorators import secure_module
from investigacion.forms import GrupoInvestigacionForm, FinanciamientoPonenciaForm
from investigacion.funciones import salto_linea_nombre_firma_encontrado
from investigacion.models import GrupoInvestigacion, FUNCION_INTEGRANTE_GRUPO_INVESTIGACION, GrupoInvestigacionIntegrante
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.forms import PlanificarPonenciasForm
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, generar_nombre, email_valido, \
    validar_archivo, null_to_decimal, cuenta_email_disponible_para_envio, fechaletra_corta, fecha_letra_rango
from sga.funcionesxhtml2pdf import convert_html_to_pdf
from sga.models import CUENTAS_CORREOS, Persona, PlanificarPonencias, ConvocatoriaPonencia, CriterioPonencia, PlanificarPonenciasCriterio, PlanificarPonenciasRecorrido, MESES_CHOICES
from django.template import Context
from django.template.loader import get_template

import time as ET

from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt

from django.core.cache import cache


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    es_profesor = perfilprincipal.es_profesor()

    if not es_profesor:
        return HttpResponseRedirect("/?info=El Módulo está disponible para profesores.")

    data['profesor'] = profesor = perfilprincipal.profesor
    periodo = request.session['periodo']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitud':
            try:
                form = FinanciamientoPonenciaForm(request.POST, request.FILES)

                if 'archivoabstract' in request.FILES:
                    archivo = request.FILES['archivoabstract']
                    descripcionarchivo = 'Abstract(Resumen)'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocartaaceptacion' in request.FILES:
                    archivo = request.FILES['archivocartaaceptacion']
                    descripcionarchivo = 'Carta de Aceptación'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocronograma' in request.FILES:
                    archivo = request.FILES['archivocronograma']
                    descripcionarchivo = 'Cronograma de actividades'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocomite' in request.FILES:
                    archivo = request.FILES['archivocomite']
                    descripcionarchivo = 'Comité científico'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivojustifica' in request.FILES:
                    archivo = request.FILES['archivojustifica']
                    descripcionarchivo = 'Planificación justificar horas docencia'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivoindexacion' in request.FILES:
                    archivo = request.FILES['archivoindexacion']
                    descripcionarchivo = 'Evidencia de indexación en Scopus/WoS'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if form.is_valid():
                    convocatoria = ConvocatoriaPonencia.objects.get(pk=int(encrypt(request.POST['idc'])))
                    anio = convocatoria.iniciopos.year

                    if PlanificarPonencias.objects.values('id').filter(tema__icontains=form.cleaned_data['tema'], status=True).exclude(estado=9).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El Tema de la ponencia ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    if form.cleaned_data['fechainicio'].year != anio:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El año de la fecha de inicio debe ser igual a %s" % (anio), "showSwal": "True", "swalType": "warning"})

                    if relativedelta.relativedelta(form.cleaned_data['fechainicio'], datetime.now().date()).months < 1:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de inicio debe ser mayor o igual a 1 mes en relación a la fecha actual", "showSwal": "True", "swalType": "warning"})

                    if relativedelta.relativedelta(form.cleaned_data['fechalimpago'], datetime.now().date()).months < 1:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de límite de pago debe ser mayor o igual a 1 mes en relación a la fecha actual", "showSwal": "True", "swalType": "warning"})

                    if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin deber ser mayor o igual a la fecha inicio", "showSwal": "True", "swalType": "warning"})

                    lista = json.loads(request.POST['lista_items1'])
                    existecomite = False
                    for l in lista:
                        if l['obligatorio'] is True and l['valor'] is False:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El criterio [ %s ] es obligatorio de marcar" % l['criterio'], "showSwal": "True", "swalType": "warning"})

                        if form.cleaned_data['pais'].id == 1:
                            if l['orden'] == '2' and l['valor'] is True:
                                existecomite = True
                        else:
                            if l['orden'] == '3' and l['valor'] is True:
                                existecomite = True


                    nombreotrabase = ''
                    otrabase = len(request.POST['nombreotrabasenac'].strip()) > 0 or len(request.POST['nombreotrabaseint'].strip()) > 0
                    if otrabase:
                        nombreotrabase = request.POST['nombreotrabasenac'].strip().upper() if len(request.POST['nombreotrabasenac'].strip()) > 0 else request.POST['nombreotrabaseint'].strip().upper()

                    planificarponencias = PlanificarPonencias(
                        convocatoria=convocatoria,
                        periodo=periodo,
                        profesor=profesor,
                        nombre=form.cleaned_data['nombre'],
                        tema=form.cleaned_data['tema'],
                        pais=form.cleaned_data['pais'],
                        fecha_fin=form.cleaned_data['fechafin'],
                        fecha_inicio=form.cleaned_data['fechainicio'],
                        fechalimpago=form.cleaned_data['fechalimpago'],
                        costo=form.cleaned_data['costo'],
                        modalidad=form.cleaned_data['modalidad'],
                        link=form.cleaned_data['link'],
                        justificacion=form.cleaned_data['justificacion'],
                        areaconocimiento=form.cleaned_data['areaconocimiento'],
                        subareaconocimiento=form.cleaned_data['subareaconocimiento'],
                        subareaespecificaconocimiento=form.cleaned_data['subareaespecificaconocimiento'],
                        lineainvestigacion=form.cleaned_data['lineainvestigacion'],
                        sublineainvestigacion=form.cleaned_data['sublineainvestigacion'],
                        provieneproyecto=form.cleaned_data['provieneproyecto'],
                        tipoproyecto=form.cleaned_data['tipoproyecto'] if form.cleaned_data['provieneproyecto'] else None,
                        existecomite=existecomite,
                        otrabase=otrabase,
                        nombreotrabase=nombreotrabase,
                        pertenecegrupoinv=form.cleaned_data['pertenecegrupoinv'],
                        grupoinvestigacion=form.cleaned_data['grupoinvestigacion'],
                        estado=8
                    )
                    planificarponencias.save(request)

                    if form.cleaned_data['provieneproyecto']:
                        if int(form.cleaned_data['tipoproyecto']) != 3:
                            planificarponencias.proyectointerno = form.cleaned_data['proyectointerno']
                        else:
                            planificarponencias.proyectoexterno = form.cleaned_data['proyectoexterno']

                    if 'archivoabstract' in request.FILES:
                        newfile = request.FILES['archivoabstract']
                        newfile._name = generar_nombre("pabstract", newfile._name)
                        planificarponencias.archivoabstract = newfile

                    if 'archivocartaaceptacion' in request.FILES:
                        newfile = request.FILES['archivocartaaceptacion']
                        newfile._name = generar_nombre("pcartaaceptacion", newfile._name)
                        planificarponencias.archivocartaaceptacion = newfile

                    if 'archivocronograma' in request.FILES:
                        newfile = request.FILES['archivocronograma']
                        newfile._name = generar_nombre("pcronograma", newfile._name)
                        planificarponencias.archivocronograma = newfile

                    if 'archivocomite' in request.FILES:
                        newfile = request.FILES['archivocomite']
                        newfile._name = generar_nombre("pcomitecientifico", newfile._name)
                        planificarponencias.archivocomite = newfile

                    if 'archivojustifica' in request.FILES:
                        newfile = request.FILES['archivojustifica']
                        newfile._name = generar_nombre("pjustificacion", newfile._name)
                        planificarponencias.archivojustifica = newfile

                    if 'archivoindexacion' in request.FILES:
                        newfile = request.FILES['archivoindexacion']
                        newfile._name = generar_nombre("pindexacionscowos", newfile._name)
                        planificarponencias.archivoindexacion = newfile

                    planificarponencias.save(request)

                    if 'lista_items1' in request.POST:
                        lista = json.loads(request.POST['lista_items1'])
                        for l in lista:
                            detallecriterio = PlanificarPonenciasCriterio(
                                ponencia=planificarponencias,
                                criterio_id=l['id'],
                                valor=l['valor']
                            )
                            detallecriterio.save()

                    recorrido = PlanificarPonenciasRecorrido(planificarponencias=planificarponencias,
                                                             observacion='EN EDICIÓN',
                                                             estado=8,
                                                             fecha=datetime.now().date(),
                                                             persona=profesor.persona)
                    recorrido.save(request)

                    log(u'%s adicionó solicitud de financiamiento a ponencias: %s' % (persona, planificarponencias), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    for k, v in form.errors.items():
                        raise NameError( k + ', ' + v[0])
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editsolicitud':
            try:
                form = FinanciamientoPonenciaForm(request.POST, request.FILES)

                if 'archivoabstract' in request.FILES:
                    archivo = request.FILES['archivoabstract']
                    descripcionarchivo = 'Abstract(Resumen)'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocartaaceptacion' in request.FILES:
                    archivo = request.FILES['archivocartaaceptacion']
                    descripcionarchivo = 'Carta de Aceptación'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocronograma' in request.FILES:
                    archivo = request.FILES['archivocronograma']
                    descripcionarchivo = 'Cronograma de actividades'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocomite' in request.FILES:
                    archivo = request.FILES['archivocomite']
                    descripcionarchivo = 'Comité científico'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivojustifica' in request.FILES:
                    archivo = request.FILES['archivojustifica']
                    descripcionarchivo = 'Planificación justificar horas docencia'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivoindexacion' in request.FILES:
                    archivo = request.FILES['archivoindexacion']
                    descripcionarchivo = 'Evidencia de indexación en Scopus/WoS'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if form.is_valid():
                    ponencia = PlanificarPonencias.objects.get(pk=int(encrypt(request.POST['id'])))
                    convocatoria = ponencia.convocatoria
                    anio = convocatoria.iniciopos.year

                    if PlanificarPonencias.objects.values('id').filter(tema__icontains=form.cleaned_data['tema'], status=True).exclude(pk=int(encrypt(request.POST['id']))).exclude(estado=9).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El Tema de la ponencia ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    if form.cleaned_data['fechainicio'].year != anio:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El año de la fecha de inicio debe ser igual a %s" % (anio), "showSwal": "True", "swalType": "warning"})

                    if relativedelta.relativedelta(form.cleaned_data['fechainicio'], datetime.now().date()).months < 1:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de inicio debe ser mayor o igual a 1 mes en relación a la fecha actual", "showSwal": "True", "swalType": "warning"})

                    if relativedelta.relativedelta(form.cleaned_data['fechalimpago'], datetime.now().date()).months < 1:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de límite de pago debe ser mayor o igual a 1 mes en relación a la fecha actual", "showSwal": "True", "swalType": "warning"})

                    if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin deber ser mayor o igual a la fecha inicio", "showSwal": "True", "swalType": "warning"})

                    lista = json.loads(request.POST['lista_items1'])
                    existecomite = False
                    for l in lista:
                        if l['obligatorio'] is True and l['valor'] is False:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El criterio [ %s ] es obligatorio de marcar" % l['criterio'], "showSwal": "True", "swalType": "warning"})

                        if form.cleaned_data['pais'].id == 1:
                            if l['orden'] == '4' and l['valor'] is True:
                                existecomite = True
                        else:
                            if l['orden'] == '3' and l['valor'] is True:
                                existecomite = True

                    nombreotrabase = ''
                    otrabase = len(request.POST['nombreotrabasenac'].strip()) > 0 or len(request.POST['nombreotrabaseint'].strip()) > 0
                    if otrabase:
                        nombreotrabase = request.POST['nombreotrabasenac'].strip().upper() if len(request.POST['nombreotrabasenac'].strip()) > 0 else request.POST['nombreotrabaseint'].strip().upper()

                    ponencia.nombre = form.cleaned_data['nombre']
                    ponencia.tema = form.cleaned_data['tema']
                    ponencia.pais = form.cleaned_data['pais']
                    ponencia.fecha_fin = form.cleaned_data['fechafin']
                    ponencia.fecha_inicio = form.cleaned_data['fechainicio']
                    ponencia.fechalimpago = form.cleaned_data['fechalimpago']
                    ponencia.costo = form.cleaned_data['costo']
                    ponencia.modalidad = form.cleaned_data['modalidad']
                    ponencia.link = form.cleaned_data['link']
                    ponencia.justificacion = form.cleaned_data['justificacion']
                    ponencia.areaconocimiento = form.cleaned_data['areaconocimiento']
                    ponencia.subareaconocimiento = form.cleaned_data['subareaconocimiento']
                    ponencia.subareaespecificaconocimiento = form.cleaned_data['subareaespecificaconocimiento']
                    ponencia.lineainvestigacion = form.cleaned_data['lineainvestigacion']
                    ponencia.sublineainvestigacion = form.cleaned_data['sublineainvestigacion']
                    ponencia.provieneproyecto = form.cleaned_data['provieneproyecto']
                    ponencia.tipoproyecto = form.cleaned_data['tipoproyecto'] if form.cleaned_data['provieneproyecto'] else None
                    ponencia.existecomite = existecomite
                    ponencia.otrabase = otrabase
                    ponencia.nombreotrabase = nombreotrabase
                    ponencia.pertenecegrupoinv = form.cleaned_data['pertenecegrupoinv']
                    ponencia.grupoinvestigacion = form.cleaned_data['grupoinvestigacion']
                    ponencia.cartagenerada = False
                    ponencia.cartafirmada = False
                    ponencia.archivocartacompromiso = None

                    if form.cleaned_data['provieneproyecto']:
                        if int(form.cleaned_data['tipoproyecto']) != 3:
                            ponencia.proyectointerno = form.cleaned_data['proyectointerno']
                        else:
                            ponencia.proyectoexterno = form.cleaned_data['proyectoexterno']

                    if 'archivoabstract' in request.FILES:
                        newfile = request.FILES['archivoabstract']
                        newfile._name = generar_nombre("pabstract", newfile._name)
                        ponencia.archivoabstract = newfile

                    if 'archivocartaaceptacion' in request.FILES:
                        newfile = request.FILES['archivocartaaceptacion']
                        newfile._name = generar_nombre("pcartaaceptacion", newfile._name)
                        ponencia.archivocartaaceptacion = newfile

                    if 'archivocronograma' in request.FILES:
                        newfile = request.FILES['archivocronograma']
                        newfile._name = generar_nombre("pcronograma", newfile._name)
                        ponencia.archivocronograma = newfile

                    if 'archivocomite' in request.FILES:
                        newfile = request.FILES['archivocomite']
                        newfile._name = generar_nombre("pcomitecientifico", newfile._name)
                        ponencia.archivocomite = newfile

                    if 'archivojustifica' in request.FILES:
                        newfile = request.FILES['archivojustifica']
                        newfile._name = generar_nombre("pjustificacion", newfile._name)
                        ponencia.archivojustifica = newfile

                    if 'archivoindexacion' in request.FILES:
                        newfile = request.FILES['archivoindexacion']
                        newfile._name = generar_nombre("pindexacionscowos", newfile._name)
                        ponencia.archivoindexacion = newfile

                    ponencia.save(request)

                    if 'lista_items1' in request.POST:
                        lista = json.loads(request.POST['lista_items1'])

                        editar = ponencia.planificarponenciascriterio_set.filter(status=True, criterio_id=lista[0]['id']).exists()
                        if editar is False:
                            PlanificarPonenciasCriterio.objects.filter(ponencia=ponencia, status=True).update(status=False)

                        for l in lista:
                            if editar:
                                PlanificarPonenciasCriterio.objects.filter(ponencia=ponencia, status=True, criterio_id=l['id']).update(valor=l['valor'])
                            else:
                                detallecriterio = PlanificarPonenciasCriterio(
                                    ponencia=ponencia,
                                    criterio_id=l['id'],
                                    valor=l['valor']
                                )
                                detallecriterio.save()

                    # Si el estado es NOVEDAD, actualizo a EN EDICIÓN
                    if ponencia.estado == 7:
                        ponencia.estado = 8
                        ponencia.confirmada = False
                        ponencia.save(request)

                        recorrido = PlanificarPonenciasRecorrido(planificarponencias=ponencia,
                                                                 observacion='EN EDICIÓN',
                                                                 estado=8,
                                                                 fecha=datetime.now().date(),
                                                                 persona=profesor.persona)
                        recorrido.save(request)

                    log(u'%s editó solicitud de financiamiento a ponencias: %s' % (persona, ponencia), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in form.errors.items()])
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'cartacompromisoponenciapdf':
            try:
                data = {}

                # Consulto la solicitud de financiamiento de ponencia
                solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.POST['id'])))

                if not solicitud.cartagenerada:
                    solicitud.fechacarta = datetime.now().date()

                solicitud.cartagenerada = True
                solicitud.cartafirmada = False
                solicitud.save(request)

                data['solicitud'] = solicitud
                data['solicitante'] = solicitud.profesor
                data['fechasolicitud'] = str(solicitud.fechacarta.day) + " de " + MESES_CHOICES[solicitud.fechacarta.month - 1][1].capitalize() + " del " + str(solicitud.fechacarta.year)
                data['fechacongreso'] = fecha_letra_rango(solicitud.fecha_inicio, solicitud.fecha_fin)

                # Creacion del archivo
                directorio = SITE_STORAGE + '/media/ponencias/cartacompromiso'
                try:
                    os.stat(directorio)
                except:
                    os.mkdir(directorio)

                # Archivo de la solicitud de beca
                nombrearchivo = generar_nombre('cartacompromisoponencia', 'cartacompromisoponencia.pdf')

                valida = convert_html_to_pdf(
                    'pro_financiamientoponencia/cartacompromisoponenciapdf.html',
                    {'pagesize': 'A4', 'data': data},
                    nombrearchivo,
                    directorio
                )

                if not valida:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el documento de la carta de compromiso.", "showSwal": "True", "swalType": "error"})

                # archivo = 'media/ponencias/cartacompromiso/' + nombrearchivo
                archivo = SITE_STORAGE + '/media/ponencias/cartacompromiso/' + nombrearchivo

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
                archivocopiado.name = nombrearchivo

                solicitud.archivocartacompromiso = archivocopiado
                solicitud.save(request)

                ET.sleep(1)

                # Borro la solicitud creada de manera general, no la del registro
                # os.remove(archivo)

                return JsonResponse({"result": "ok", "documento": solicitud.archivocartacompromiso.url})
                # return JsonResponse({"result": "ok", "documento": archivo})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"ERROR al generar la carta de compromiso de la solicitud. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'subircartacompromiso':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivo = request.FILES['archivocarta']
                descripcionarchivo = 'Archivo Carta de compromiso de ponencia firmada'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto la solicitud de financiamiento de ponencia
                solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.POST['id'])))

                archivo._name = generar_nombre("cartacompromisoponencia", archivo._name)
                solicitud.archivocartacompromiso = archivo
                solicitud.cartafirmada = True
                solicitud.save(request)

                # Si el estado es NOVEDAD, actualizo a EN EDICIÓN
                if solicitud.estado == 7:
                    solicitud.estado = 8
                    solicitud.confirmada = False
                    solicitud.save(request)

                    recorrido = PlanificarPonenciasRecorrido(planificarponencias=solicitud,
                                                             observacion='EN EDICIÓN',
                                                             estado=8,
                                                             fecha=datetime.now().date(),
                                                             persona=profesor.persona)
                    recorrido.save(request)

                log(u'%s subió carta de compromiso firmada para la solicitud de financiamiento a ponencias: %s' % (persona, solicitud), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'firmarcartacompromiso':
            try:
                if 'iddoc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivofirma = request.FILES['archivofirma']
                clavefirma = request.POST['cfirma']
                descripcionarchivo = 'Archivo de la firma electrónica'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivofirma, ['P12', 'PFX'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto la solicitud de financiamiento a ponencia
                solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.POST['iddoc'])))

                # Obtengo el archivo de la solicitud
                archivosolicitud = solicitud.archivocartacompromiso
                rutapdfarchivo = SITE_STORAGE + archivosolicitud.url
                textoabuscar = persona.nombre_completo_inverso()

                vecescontrado = 0
                ocurrencia = 2

                # Obtener coordenadas para ubicar al firma dependiendo de donde se encuentra ubicado el nombre de la persona
                documento = fitz.open(rutapdfarchivo)
                numpaginafirma = int(documento.page_count) - 1

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
                    y = 5000 - int(valor[3]) - 4095 # 4095 0 4090
                else:
                    y = 0

                # x = 87  # izq
                x = 230  # cent
                # x = 374  # der

                # Si no existe el nombre de la persona en el documento
                if y == 0:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"No se encuentra el nombre del firmante en el documento", "showSwal": "True", "swalType": "warning"})

                # Obtener extensión y leer archivo de la firma
                extfirma = os.path.splitext(archivofirma.name)[1][1:]
                bytesfirma = archivofirma.read()

                # Firma del documento
                datau = JavaFirmaEc(
                    archivo_a_firmar=archivosolicitud,
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

                nombrearchivofirmado = generar_nombre('cartacompromisoponencia', 'cartacompromisoponencia.pdf')
                objarchivo = DjangoFile(generar_archivo_firmado, nombrearchivofirmado)

                solicitud.archivocartacompromiso = objarchivo
                solicitud.cartafirmada = True
                solicitud.save(request)

                log(u'%s firmó carta de compromiso de ponencia para la solicitud: %s' % (persona, solicitud), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True, "documento": solicitud.archivocartacompromiso.url})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'confirmarponencia':
            try:
                # Consulto la solicitud de ponencia
                solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.POST['id'])))

                # Actualizo la solicitud
                solicitud.fechasolicitud = datetime.now().date()
                solicitud.confirmada = True
                solicitud.estado = 1
                solicitud.save(request)

                # Agrego recorrido de la solicitud
                recorrido = PlanificarPonenciasRecorrido(planificarponencias=solicitud,
                                                         observacion='SOLICITADO',
                                                         estado=1,
                                                         fecha=datetime.now().date(),
                                                         persona=profesor.persona)
                recorrido.save(request)

                # # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec

                # E-mail del destinatario
                lista_email_envio = persona.lista_emails_envio()
                # lista_email_envio = ['isaltosm@unemi.edu.ec']
                lista_email_cco = []
                lista_adjuntos = [solicitud.archivocartacompromiso]

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                tituloemail = "Registro de Solicitud de Financiamiento a Ponencia"
                tiponotificacion = "REGSOL"
                titulo = "Postulación y Financiamiento de Ponencias"

                send_html_mail(tituloemail,
                               "emails/financiamientoponencia.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimada' if persona.sexo_id == 1 else 'Estimado',
                                'nombrepersona': persona.nombre_completo_inverso(),
                                'solicitud': solicitud
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                # Notificar por e-mail a la Coordinación de Investigación
                lista_email_envio = ['produccioncientifica@unemi.edu.ec']
                lista_email_cco = ['ecarrasqueror@unemi.edu.ec']
                # lista_email_envio = ['isaltosm@unemi.edu.ec', 'ivan.saltos.medina@gmail.com']

                tituloemail = "Registro de Solicitud de Financiamiento a Ponencia"
                tiponotificacion = "REGCOORDINV"

                send_html_mail(tituloemail,
                               "emails/financiamientoponencia.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimados',
                                'nombredocente': persona.nombre_completo_inverso(),
                                'saludodocente': 'la docente' if persona.sexo_id == 1 else 'el docente',
                                'solicitud': solicitud
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s confirmó solicitud de financiamiento a ponencias: %s' % (persona, solicitud), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro de solicitud confirmado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'delsolicitud':
            try:
                # Consulto la solicitud de ponencia
                solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda eliminar
                if solicitud.estado != 1:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede eliminar el Registro", "showSwal": "True", "swalType": "warning"})

                # Elimino el grupo de investigación
                solicitud.status = False
                solicitud.save(request)

                log(u'%s eliminó solicitud de financiamiento a ponencias: %s' % (persona, solicitud), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al eliminar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Solicitud incorrecta.", "showSwal": "True", "swalType": "error"})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'mostrarrecorrido':
                try:
                    title = u'Recorrido de la Solicitud de Financiamiento'
                    solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitud'] = solicitud
                    data['vistadocente'] = True
                    data['recorrido'] = solicitud.planificarponenciasrecorrido_set.filter(status=True).order_by('id')
                    template = get_template("pro_financiamientoponencia/recorridosolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addsolicitud':
                try:
                    data['title'] = u'Agregar Solicitud de Financiamiento a ponencias'
                    form = FinanciamientoPonenciaForm()
                    data['criteriosnac'] = CriterioPonencia.objects.filter(status=True, tipoponencia=1, vigente=True).order_by('orden')
                    data['criteriosint'] = CriterioPonencia.objects.filter(status=True, tipoponencia=2, vigente=True).order_by('orden')
                    data['convocatoria'] = ConvocatoriaPonencia.objects.get(pk=int(encrypt(request.GET['idc'])))
                    data['idc'] = request.GET['idc']
                    data['form'] = form
                    return render(request, "pro_financiamientoponencia/addsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'editsolicitud':
                try:
                    data['title'] = u'Editar Solicitud de Financiamiennto a ponencias'
                    ponencia = PlanificarPonencias.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['planificarponencias'] = ponencia
                    form = FinanciamientoPonenciaForm(initial={'tema': ponencia.tema,
                                                            'fechainicio': ponencia.fecha_inicio,
                                                            'fechafin': ponencia.fecha_fin,
                                                            'fechalimpago': ponencia.fechalimpago,
                                                            'justificacion': ponencia.justificacion,
                                                            'link': ponencia.link,
                                                            'nombre': ponencia.nombre,
                                                            'pais': ponencia.pais,
                                                            'sugerenciacongreso': ponencia.sugerenciacongreso,
                                                            'costo': ponencia.costo,
                                                            'modalidad': ponencia.modalidad,
                                                            'areaconocimiento': ponencia.areaconocimiento,
                                                            'subareaconocimiento': ponencia.subareaconocimiento,
                                                            'subareaespecificaconocimiento': ponencia.subareaespecificaconocimiento,
                                                            'lineainvestigacion': ponencia.lineainvestigacion,
                                                            'sublineainvestigacion': ponencia.sublineainvestigacion,
                                                            'provieneproyecto': ponencia.provieneproyecto,
                                                            'tipoproyecto': ponencia.tipoproyecto,
                                                            'proyectointerno': ponencia.proyectointerno,
                                                            'proyectoexterno': ponencia.proyectoexterno,
                                                            'pertenecegrupoinv': ponencia.pertenecegrupoinv,
                                                            'grupoinvestigacion': ponencia.grupoinvestigacion})
                    form.editar(ponencia)
                    data['form'] = form

                    data['tipoponencia'] = tipoponencia = 'N' if ponencia.pais.id == 1 else 'I'
                    data['existecomite'] = ponencia.existecomite

                    if tipoponencia == 'N':
                        data['nombreotrabasenac'] = ponencia.nombreotrabase
                    else:
                        data['nombreotrabaseint'] = ponencia.nombreotrabase

                    data['criteriosdocente'] = ponencia.planificarponenciascriterio_set.filter(status=True).order_by('criterio__orden')
                    data['criteriosnac'] = CriterioPonencia.objects.filter(status=True, tipoponencia=1, vigente=True).order_by('orden')
                    data['criteriosint'] = CriterioPonencia.objects.filter(status=True, tipoponencia=2, vigente=True).order_by('orden')
                    data['convocatoria'] = ponencia.convocatoria

                    return render(request, "pro_financiamientoponencia/editsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'subircartacompromiso':
                try:
                    data['title'] = u'Subir Carta Compromiso Firmada (App Externa)'
                    data['solicitud'] = PlanificarPonencias.objects.get(pk=int(encrypt(request.GET['id'])))

                    template = get_template("pro_financiamientoponencia/subircartacompromiso.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'firmarcartacompromiso':
                try:
                    data['title'] = u'Firmar Carta de Compromiso'

                    solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['solicitud'] = solicitud
                    data['iddoc'] = solicitud.id  # ID del documento a firmar
                    data['idper'] = solicitud.profesor.persona.id  # ID de la persona que firma
                    data['tipofirma'] = 'SOL'

                    data['mensaje'] = "Firma de Carta de Compromiso del docente <b>{}</b> para la ponencia con tema <b>{}</b>".format(solicitud.profesor.persona.nombre_completo_inverso(), solicitud.tema)
                    data['accionfirma'] = action

                    template = get_template("pro_becadocente/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrarevidencias':
                try:
                    title = u'Evidencias de la Solicitud de Financiamiento'
                    solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitud'] = solicitud
                    data['evidencias'] = solicitud.evidencias()
                    template = get_template("pro_financiamientoponencia/evidencias.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            try:
                tienedistributivo = profesor.profesordistributivohoras_set.values('id').filter(periodo=periodo, status=True).exists()

                search, filtro, url_vars = request.GET.get('s', ''), Q(profesor=profesor, status=True), ''

                # if search:
                #     data['s'] = search
                #     filtro = filtro & (Q(nombre__unaccent__icontains=search))
                #     url_vars += '&s=' + search

                ponencias = PlanificarPonencias.objects.filter(filtro).order_by('-fecha_creacion')

                paging = MiPaginador(ponencias, 25)
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
                data['ponencias'] = page.object_list

                hoy = datetime.now().date()

                convocatoria = None
                convocatorias = ConvocatoriaPonencia.objects.filter(status=True, publicada=True, iniciopos__lte=hoy, finpos__gte=hoy)
                if convocatorias:
                    convocatoria = convocatorias[0]

                data['habilitaingresoponencias'] = True if convocatoria else False
                data['tienedistributivo'] = tienedistributivo
                data['convocatoria'] = convocatoria
                data['title'] = u'Solicitudes de Financiamiento a Ponencias'
                data['enlaceatras'] = "/pro_investigacion?action=convocatorias"

                return render(request, "pro_financiamientoponencia/view.html", data)
            except Exception as ex:
                pass
