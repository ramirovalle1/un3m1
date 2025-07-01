# -*- coding: UTF-8 -*-
import io
import json
import os
from math import ceil

import PyPDF2
from datetime import time, datetime
from decimal import Decimal

import requests
import xlsxwriter
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import time as pausaparaemail
from xlwt import easyxf, XFStyle, Workbook
import random
from decorators import secure_module
from investigacion.forms import GrupoInvestigacionForm, FinanciamientoPonenciaForm, ConvocatoriaFinanciamientoPonenciaForm
from investigacion.funciones import FORMATOS_CELDAS_EXCEL
from investigacion.models import GrupoInvestigacion, FUNCION_INTEGRANTE_GRUPO_INVESTIGACION, GrupoInvestigacionIntegrante
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.forms import PlanificarPonenciasForm
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, generar_nombre, email_valido, \
    validar_archivo, null_to_decimal, cuenta_email_disponible_para_envio, fechaletra_corta, fecha_letra_rango
from sga.funcionesxhtml2pdf import convert_html_to_pdf
from sga.models import CUENTAS_CORREOS, Persona, PlanificarPonencias, ConvocatoriaPonencia, CriterioPonencia, PlanificarPonenciasCriterio, PlanificarPonenciasRecorrido, MESES_CHOICES, Matricula
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
    es_administrativo = perfilprincipal.es_administrativo()

    if not es_administrativo:
        return HttpResponseRedirect("/?info=El Módulo está disponible para administrativos.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addconvocatoria':
            try:
                f = ConvocatoriaFinanciamientoPonenciaForm(request.POST, request.FILES)

                # Validar los archivos
                if 'archivopolitica' in request.FILES:
                    archivo = request.FILES['archivopolitica']
                    descripcionarchivo = 'Políticas'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivobase' in request.FILES:
                    archivo = request.FILES['archivobase']
                    descripcionarchivo = 'Bases Convocatoria'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    if not ConvocatoriaPonencia.objects.filter(status=True, descripcion=f.cleaned_data['descripcion'].strip().upper()).exists():
                        if f.cleaned_data['finpos'] <= f.cleaned_data['iniciopos']:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de postulación debe ser mayor a la fecha de inicio de postulación ", "showSwal": "True", "swalType": "warning"})

                        # Guardo la convocatoria
                        convocatoria = ConvocatoriaPonencia(
                            descripcion=f.cleaned_data['descripcion'].strip().upper(),
                            iniciopos=f.cleaned_data['iniciopos'],
                            finpos=f.cleaned_data['finpos'],
                            publicada=f.cleaned_data['publicada']
                        )
                        convocatoria.save(request)

                        if 'archivopolitica' in request.FILES:
                            newfile = request.FILES['archivopolitica']
                            newfile._name = generar_nombre("politica", newfile._name)
                            convocatoria.archivopolitica = newfile

                        if 'archivobase' in request.FILES:
                            newfile = request.FILES['archivobase']
                            newfile._name = generar_nombre("baseconvocatoria", newfile._name)
                            convocatoria.archivobase = newfile

                        convocatoria.save(request)

                        log(u'%s agregó convocatoria para financiamiento a ponencias: %s' % (persona, convocatoria), request, "add")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La convocatoria para financiamiento a ponencias ya ha sido ingresada", "showSwal": "True", "swalType": "warning"})
                else:
                    for k, v in f.errors.items():
                        raise NameError( k + ', ' + v[0])
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editconvocatoria':
            try:
                f = ConvocatoriaFinanciamientoPonenciaForm(request.POST, request.FILES)

                # Validar los archivos
                if 'archivopolitica' in request.FILES:
                    archivo = request.FILES['archivopolitica']
                    descripcionarchivo = 'Políticas'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivobase' in request.FILES:
                    archivo = request.FILES['archivobase']
                    descripcionarchivo = 'Bases Convocatoria'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    if not ConvocatoriaPonencia.objects.filter(status=True, descripcion=f.cleaned_data['descripcion'].strip().upper()).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        # Consultar la convocatoria
                        convocatoria = ConvocatoriaPonencia.objects.get(pk=int(encrypt(request.POST['id'])))

                        if f.cleaned_data['finpos'] <= f.cleaned_data['iniciopos']:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de postulación debe ser mayor a la fecha de inicio de postulación ", "showSwal": "True", "swalType": "warning"})

                        # Actualizo la convocatoria
                        convocatoria.descripcion = f.cleaned_data['descripcion'].strip().upper()
                        convocatoria.iniciopos = f.cleaned_data['iniciopos']
                        convocatoria.finpos = f.cleaned_data['finpos']
                        convocatoria.publicada = f.cleaned_data['publicada']

                        if 'archivopolitica' in request.FILES:
                            newfile = request.FILES['archivopolitica']
                            newfile._name = generar_nombre("politica", newfile._name)
                            convocatoria.archivopolitica = newfile

                        if 'archivobase' in request.FILES:
                            newfile = request.FILES['archivobase']
                            newfile._name = generar_nombre("baseconvocatoria", newfile._name)
                            convocatoria.archivobase = newfile

                        convocatoria.save(request)

                        log(u'%s editó convocatoria para financiamiento a ponencias: %s' % (persona, convocatoria), request, "edit")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La convocatoria para financiamiento a ponencias ya ha sido ingresada", "showSwal": "True", "swalType": "warning"})
                else:
                    for k, v in f.errors.items():
                        raise NameError( k + ', ' + v[0])
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'anularsolicitud':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivo = request.FILES['archivorespaldo']
                descripcionarchivo = 'Archivo Respaldo para anulación'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto la solicitud de financiamiento de ponencia
                solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.POST['id'])))

                archivo._name = generar_nombre("panulacion", archivo._name)

                # Actualiza la solicitud
                solicitud.archivoanulacion = archivo
                solicitud.observacion = request.POST['observacion'].strip().upper()
                solicitud.estado = 9
                solicitud.save(request)

                # Guardo el recorrido
                recorrido = PlanificarPonenciasRecorrido(planificarponencias=solicitud,
                                                         observacion=solicitud.observacion,
                                                         estado=9,
                                                         fecha=datetime.now().date(),
                                                         persona=persona)
                recorrido.save(request)

                # Notificar por e-mail
                notificar_revision_solicitud(solicitud)

                log(u'%s anuló solicitud de financiamiento a ponencias: %s' % (persona, solicitud), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'validarsolicitud':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                estado = int(request.POST['estadosolicitud'])
                observacion = request.POST['observacion'].strip().upper()

                # Consulto la solicitud de financiamiento de ponencia
                solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.POST['id'])))

                # Actualiza la solicitud
                solicitud.estado = estado
                solicitud.observacion = observacion
                solicitud.save(request)

                # Guardo el recorrido
                recorrido = PlanificarPonenciasRecorrido(planificarponencias=solicitud,
                                                         observacion=solicitud.observacion,
                                                         estado=estado,
                                                         fecha=datetime.now().date(),
                                                         persona=persona)
                recorrido.save(request)

                # Notificar por e-mail
                notificar_revision_solicitud(solicitud)

                log(u'%s revisó solicitud de financiamiento a ponencias: %s' % (persona, solicitud), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'aprobarsolicitud':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                resultado = int(request.POST['resultado'])
                observacion = request.POST['observacion'].strip().upper()
                archivocomision = request.FILES['archivocomision']
                descripcionarchivo = 'Archivo Resolución de Comisión'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivocomision, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                archivoocas = request.FILES['archivoocas']
                descripcionarchivo = 'Archivo Resolución de OCAS'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivoocas, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto la solicitud de financiamiento de ponencia
                solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.POST['id'])))

                archivocomision._name = generar_nombre("presolucioncga", archivocomision._name)
                archivoocas._name = generar_nombre("presolucionocas", archivoocas._name)

                # Actualiza la solicitud
                solicitud.archivocomision = archivocomision
                solicitud.archivoocas =archivoocas
                solicitud.estado = resultado
                solicitud.observacion = observacion if observacion else 'APROBADO POR OCAS'

                solicitud.save(request)

                # Guardo el recorrido
                recorrido = PlanificarPonenciasRecorrido(planificarponencias=solicitud,
                                                         observacion=solicitud.observacion,
                                                         estado=resultado,
                                                         fecha=datetime.now().date(),
                                                         persona=persona)
                recorrido.save(request)

                # Notificar por e-mail
                notificar_revision_solicitud(solicitud)

                if int(resultado) == 3:
                    log(u'%s registró aprobación ocas de la solicitud de financiamiento a ponencias: %s' % (persona, solicitud), request, "edit")
                else:
                    log(u'%s registró rechazo ocas de la solicitud de financiamiento a ponencias: %s' % (persona, solicitud), request, "edit")

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'fichasolicitudpdf':
            try:
                data = {}

                # Consulto la solicitud de financiamiento de ponencia
                solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.POST['id'])))

                data['solicitud'] = solicitud

                documentos = []
                if solicitud.archivoabstract:
                    documento = {"id": 1, "descripcion": "Abstract(Resumen)", "archivo": solicitud.archivoabstract}
                    documentos.append(documento)

                if solicitud.archivocartaaceptacion:
                    documento = {"id": 2, "descripcion": "Carta de aceptación", "archivo": solicitud.archivocartaaceptacion}
                    documentos.append(documento)

                if solicitud.archivocronograma:
                    documento = {"id": 3, "descripcion": "Cronograma de actividades", "archivo": solicitud.archivocronograma}
                    documentos.append(documento)

                if solicitud.archivocomite:
                    documento = {"id": 4, "descripcion": "Comité científico", "archivo": solicitud.archivocomite}
                    documentos.append(documento)

                if solicitud.archivocartacompromiso:
                    documento = {"id": 5, "descripcion": "Carta de compromiso", "archivo": solicitud.archivocartacompromiso}
                    documentos.append(documento)

                if solicitud.archivojustifica:
                    documento = {"id": 6, "descripcion": "Planificación Justificar Horas docencia", "archivo": solicitud.archivojustifica}
                    documentos.append(documento)

                if solicitud.archivoindexacion:
                    documento = {"id": 7, "descripcion": "Evidencia de Indexación en Scopus/WoS", "archivo": solicitud.archivoindexacion}
                    documentos.append(documento)

                data['documentos'] = documentos

                # Creacion del archivo
                directorio = SITE_STORAGE + '/media/ponencias/fichasolicitud'
                try:
                    os.stat(directorio)
                except:
                    os.mkdir(directorio)

                # Archivo de la solicitud de beca
                nombrearchivo = generar_nombre('fichasolicitudponencia', 'fichasolicitudponencia.pdf')

                valida = convert_html_to_pdf(
                    'adm_financiamientoponencia/fichasolicitudpdf.html',
                    {'pagesize': 'A4', 'data': data},
                    nombrearchivo,
                    directorio
                )

                if not valida:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el documento de la carta de compromiso.", "showSwal": "True", "swalType": "error"})

                # archivo = 'media/ponencias/cartacompromiso/' + nombrearchivo
                # archivo = SITE_STORAGE + '/media/ponencias/fichasolicitud/' + nombrearchivo
                archivo = '/media/ponencias/fichasolicitud/' + nombrearchivo

                return JsonResponse({"result": "ok", "documento": archivo})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"ERROR al generar la carta de compromiso de la solicitud. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Solicitud incorrecta.", "showSwal": "True", "swalType": "error"})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'solicitudes':
                try:
                    search, idc, filtro, url_vars = request.GET.get('s', ''), request.GET.get('idc', ''), Q(status=True), '&action=' + action

                    convocatoria = ConvocatoriaPonencia.objects.get(pk=int(encrypt(idc)))

                    filtro = filtro & Q(convocatoria=convocatoria)

                    url_vars += '&idc=' + idc

                    if search:
                        data['s'] = search
                        s = search.split(" ")
                        if len(s) == 1:
                            filtro = filtro & (Q(tema__unaccent__icontains=search) | Q(profesor__persona__apellido1__icontains=search) | Q(profesor__persona__apellido2__icontains=search) | Q(profesor__persona__nombres__icontains=search))
                        else:
                            filtro = filtro & (Q(profesor__persona__apellido1__icontains=s[0]) & Q(profesor__persona__apellido2__icontains=s[1]))

                        url_vars += '&s=' + search

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
                    data['title'] = u'Solicitudes de Financiamiento a Ponencias'
                    data['convocatoria'] = convocatoria
                    data['enlaceatras'] = "/adm_financiamientoponencia"

                    return render(request, "adm_financiamientoponencia/solicitudes.html", data)
                except Exception as ex:
                    pass

            elif action == 'addconvocatoria':
                try:
                    data['title'] = u'Agregar Convocatoria para Financiamiento a Ponencias'
                    form = ConvocatoriaFinanciamientoPonenciaForm()
                    data['form'] = form
                    data['criteriosnac'] = CriterioPonencia.objects.filter(status=True, tipoponencia=1, vigente=True).order_by('orden')
                    data['criteriosint'] = CriterioPonencia.objects.filter(status=True, tipoponencia=2, vigente=True).order_by('orden')
                    return render(request, "adm_financiamientoponencia/addconvocatoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'editconvocatoria':
                try:
                    data['title'] = u'Editar Convocatoria para Financiamiento a Ponencias'
                    convocatoria = ConvocatoriaPonencia.objects.get(pk=int(encrypt(request.GET['idc'])))

                    form = ConvocatoriaFinanciamientoPonenciaForm(
                        initial={
                            'descripcion': convocatoria.descripcion,
                            'iniciopos': convocatoria.iniciopos,
                            'finpos': convocatoria.finpos,
                            'publicada': convocatoria.publicada
                        }
                    )

                    data['form'] = form
                    data['convocatoria'] = convocatoria
                    data['criteriosnac'] = CriterioPonencia.objects.filter(status=True, tipoponencia=1, vigente=True).order_by('orden')
                    data['criteriosint'] = CriterioPonencia.objects.filter(status=True, tipoponencia=2, vigente=True).order_by('orden')

                    return render(request, "adm_financiamientoponencia/editconvocatoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'mostrarrecorrido':
                try:
                    title = u'Recorrido de la Solicitud de Financiamiento'
                    solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitud'] = solicitud
                    data['recorrido'] = solicitud.planificarponenciasrecorrido_set.filter(status=True).order_by('id')
                    template = get_template("pro_financiamientoponencia/recorridosolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'anularsolicitud':
                try:
                    data['title'] = u'Anular Solicitud de Financiamiento a Ponencia'
                    data['solicitud'] = PlanificarPonencias.objects.get(pk=int(encrypt(request.GET['id'])))

                    template = get_template("adm_financiamientoponencia/anularsolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'validarsolicitud':
                try:
                    data['title'] = u'Revisar y Validar Solicitud de Financiamiento a Ponencia'
                    solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitud'] = solicitud
                    data['convocatoria'] = solicitud.convocatoria

                    documentos = []
                    if solicitud.archivoabstract:
                        documento = {"id": 1, "descripcion": "Abstract(Resumen)", "archivo": solicitud.archivoabstract}
                        documentos.append(documento)

                    if solicitud.archivocartaaceptacion:
                        documento = {"id": 2, "descripcion": "Carta de aceptación", "archivo": solicitud.archivocartaaceptacion}
                        documentos.append(documento)

                    if solicitud.archivocronograma:
                        documento = {"id": 3, "descripcion": "Cronograma de actividades", "archivo": solicitud.archivocronograma}
                        documentos.append(documento)

                    if solicitud.archivocomite:
                        documento = {"id": 4, "descripcion": "Comité científico", "archivo": solicitud.archivocomite}
                        documentos.append(documento)

                    if solicitud.archivocartacompromiso:
                        documento = {"id": 5, "descripcion": "Carta de compromiso", "archivo": solicitud.archivocartacompromiso}
                        documentos.append(documento)

                    if solicitud.archivojustifica:
                        documento = {"id": 6, "descripcion": "Planificación Justificar Horas docencia", "archivo": solicitud.archivojustifica}
                        documentos.append(documento)

                    if solicitud.archivoindexacion:
                        documento = {"id": 7, "descripcion": "Evidencia de Indexación en Scopus/WoS", "archivo": solicitud.archivoindexacion}
                        documentos.append(documento)

                    data['documentos'] = documentos
                    data['primerdocumento'] = documentos[0]

                    estadosvalidacion = [
                        {"id": 2, "descripcion": "PRESELECCIONADO"},
                        {"id": 4, "descripcion": "RECHAZADO"},
                        {"id": 7, "descripcion": "NOVEDAD"}
                    ]
                    data['estadosvalidacion'] = estadosvalidacion

                    return render(request, "adm_financiamientoponencia/validarsolicitud.html", data)
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. [%s]" % msg})

            elif action == 'mostrarinformacion':
                try:
                    data['title'] = u'Información de la Solicitud de Financiamiento a Ponencia'
                    solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitud'] = solicitud
                    data['convocatoria'] = solicitud.convocatoria

                    documentos = []
                    if solicitud.archivoabstract:
                        documento = {"id": 1, "descripcion": "Abstract(Resumen)", "archivo": solicitud.archivoabstract}
                        documentos.append(documento)

                    if solicitud.archivocartaaceptacion:
                        documento = {"id": 2, "descripcion": "Carta de aceptación", "archivo": solicitud.archivocartaaceptacion}
                        documentos.append(documento)

                    if solicitud.archivocronograma:
                        documento = {"id": 3, "descripcion": "Cronograma de actividades", "archivo": solicitud.archivocronograma}
                        documentos.append(documento)

                    if solicitud.archivocomite:
                        documento = {"id": 4, "descripcion": "Comité científico", "archivo": solicitud.archivocomite}
                        documentos.append(documento)

                    if solicitud.archivocartacompromiso:
                        documento = {"id": 5, "descripcion": "Carta de compromiso", "archivo": solicitud.archivocartacompromiso}
                        documentos.append(documento)

                    if solicitud.archivojustifica:
                        documento = {"id": 6, "descripcion": "Planificación Justificar Horas docencia", "archivo": solicitud.archivojustifica}
                        documentos.append(documento)

                    if solicitud.archivoindexacion:
                        documento = {"id": 7, "descripcion": "Evidencia de Indexación en Scopus/WoS", "archivo": solicitud.archivoindexacion}
                        documentos.append(documento)

                    data['documentos'] = documentos
                    data['primerdocumento'] = documentos[0]

                    estadosvalidacion = [
                        {"id": 2, "descripcion": "PRESELECCIONADO"},
                        {"id": 4, "descripcion": "RECHAZADO"},
                        {"id": 7, "descripcion": "NOVEDAD"}
                    ]
                    data['estadosvalidacion'] = estadosvalidacion

                    return render(request, "adm_financiamientoponencia/informacionsolicitud.html", data)
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. [%s]" % msg})

            elif action == 'reportegeneral':
                try:
                    convocatoria = ConvocatoriaPonencia.objects.get(pk=int(encrypt(request.GET['idc'])))
                    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'postgrado'))

                    nombrearchivo = "SOLICITUDES_FINANCIAMIENTO_PONENCIAS_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xlsx"

                    # Create un nuevo archivo de excel y le agrega una hoja
                    workbook = xlsxwriter.Workbook(output_folder + '/' + nombrearchivo)
                    ws = workbook.add_worksheet("Listado")

                    fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
                    fceldageneral = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneral"])
                    ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
                    fceldafecha = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdafecha"])
                    fceldamoneda = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamoneda"])

                    ws.merge_range(0, 0, 0, 11, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
                    ws.merge_range(1, 0, 1, 11, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADO', ftitulo1)
                    ws.merge_range(2, 0, 2, 11, 'COORDINACIÓN DE INVESTIGACIÓN', ftitulo1)
                    ws.merge_range(3, 0, 3, 11, 'LISTADO GENERAL DE SOLICITUDES DE FINANCIAMIENTO A PONENCIAS', ftitulo1)
                    ws.merge_range(4, 0, 4, 11, 'CONVOCATORIA: ' + convocatoria.descripcion, ftitulo1)

                    columns = [
                        (u"FECHA", 12),
                        (u"NÚMERO", 10),
                        (u"PROFESOR", 40),
                        (u"CONGRESO", 40),
                        (u"TEMA", 40),
                        (u"PAÍS", 20),
                        (u"MODALIDAD", 20),
                        (u"FECHA INICIO", 12),
                        (u"FECHA FIN", 12),
                        (u"COSTO", 15),
                        (u"ESTADO", 20)
                    ]

                    row_num = 6
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                        ws.set_column(col_num, col_num, columns[col_num][1])

                    row_num = 7

                    solicitudes = PlanificarPonencias.objects.filter(status=True, convocatoria=convocatoria).order_by('-id')

                    for solicitud in solicitudes:
                        ws.write(row_num, 0, solicitud.fecha_creacion, fceldafecha)
                        ws.write(row_num, 1, str(solicitud.id).zfill(6), fceldageneral)
                        ws.write(row_num, 2, solicitud.profesor.persona.nombre_completo_inverso(), fceldageneral)
                        ws.write(row_num, 3, solicitud.nombre, fceldageneral)
                        ws.write(row_num, 4, solicitud.tema, fceldageneral)
                        ws.write(row_num, 5, solicitud.pais.nombre, fceldageneral)
                        ws.write(row_num, 6, solicitud.modalidad.nombre if solicitud.modalidad else '', fceldageneral)
                        ws.write(row_num, 7, solicitud.fecha_inicio, fceldafecha)
                        ws.write(row_num, 8, solicitud.fecha_fin, fceldafecha)
                        ws.write(row_num, 9, solicitud.costo, fceldamoneda)
                        ws.write(row_num, 10, solicitud.get_estado_display(), fceldageneral)

                        row_num += 1


                    workbook.close()

                    ruta = "media/postgrado/" + nombrearchivo
                    return JsonResponse({'result': 'ok', 'archivo': ruta})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el reporte. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            elif action == 'aprobarsolicitud':
                try:
                    data['title'] = u'Aprobar Solicitud de Financiamiento a Ponencia'
                    data['solicitud'] = PlanificarPonencias.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("adm_financiamientoponencia/aprobarsolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al obtener los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            elif action == 'geolocalizacion':
                try:
                    data['title'] = u'GeoLocalización'

                    return render(request, "adm_financiamientoponencia/geolocalizacion.html", data)
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. [%s]" % msg})

            return HttpResponseRedirect(request.path)
        else:
            try:
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''

                convocatorias = ConvocatoriaPonencia.objects.filter(filtro).order_by('-iniciopos', '-finpos')

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
                data['convocatorias'] = page.object_list
                data['title'] = u'Convocatorias para Financiamiento de Ponencias'
                data['enlaceatras'] = "/ges_investigacion?action=convocatorias"

                return render(request, "adm_financiamientoponencia/view.html", data)
            except Exception as ex:
                pass


def notificar_revision_solicitud(solicitud):
    # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
    listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

    # E-mail del destinatario
    lista_email_envio = solicitud.profesor.persona.lista_emails_envio()
    # lista_email_envio = ['isaltosm@unemi.edu.ec']
    lista_email_cco = ['ivan_saltos_medina@hotmail.com']
    lista_adjuntos = []

    fechaenvio = datetime.now().date()
    horaenvio = datetime.now().time()
    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

    if solicitud.estado == 2:
        tituloemail = "Solicitud de Financiamiento a Ponencia Pre-Seleccionada"
        tiponotificacion = "PRESELSOL"
        estadoasignado = "PRE-SELECCIONÓ"
    elif solicitud.estado == 4:
        tituloemail = "Solicitud de Financiamiento a Ponencia Rechazada"
        tiponotificacion = "RECHSOL"
        estadoasignado = "RECHAZÓ"
    elif solicitud.estado == 7:
        tituloemail = "Novedades con Solicitud de Financiamiento a Ponencia"
        tiponotificacion = "NOVSOL"
        estadoasignado = "NOVEDAD"
    elif solicitud.estado == 9:
        tituloemail = "Anulación de Solicitud de Financiamiento a Ponencia"
        tiponotificacion = "ANUSOL"
        estadoasignado = "ANULADO"
    elif solicitud.estado == 3:
        tituloemail = "Solicitud de Financiamiento a Ponencia Aprobada"
        tiponotificacion = "APRSOL"
        estadoasignado = "APROBADO"
    else:
        tituloemail = "Solicitud de Financiamiento a Ponencia Rechazada"  # RECHAZADA POR OCS
        tiponotificacion = "RECHSOLOCAS"
        estadoasignado = "RECHAZÓ"

    titulo = "Postulación y Financiamiento de Ponencias"

    send_html_mail(tituloemail,
                   "emails/financiamientoponencia.html",
                   {'sistema': u'SGA - UNEMI',
                    'titulo': titulo,
                    'fecha': fechaenvio,
                    'hora': horaenvio,
                    'tiponotificacion': tiponotificacion,
                    'saludo': 'Estimada' if solicitud.profesor.persona.sexo_id == 1 else 'Estimado',
                    'nombrepersona': solicitud.profesor.persona.nombre_completo_inverso(),
                    'solicitud': solicitud,
                    'estadoasignado': estadoasignado,
                    'observacion': solicitud.observacion
                    },
                   lista_email_envio,
                   lista_email_cco,
                   lista_adjuntos,
                   cuenta=CUENTAS_CORREOS[cuenta][1]
                   )
