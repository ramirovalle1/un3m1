# -*- coding: UTF-8 -*-
import io
import json
import os
import calendar
import shutil
from math import ceil
from calendar import monthrange
import PyPDF2
from datetime import time, datetime, timedelta, date
from decimal import Decimal

import requests
import xlsxwriter
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q, ExpressionWrapper, F, DurationField
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import time as pausaparaemail
from django.core.files import File as DjangoFile
from fitz import fitz
from xlwt import easyxf, XFStyle, Workbook
import random

from core.firmar_documentos_ec import JavaFirmaEc
from decorators import secure_module
from investigacion.forms import BaseInstitucionalForm, HorarioServicioForm
from investigacion.funciones import FORMATOS_CELDAS_EXCEL, notificar_docente_invitado, analista_uath_valida_asistencia, decano_investigacion, analista_verifica_informe_docente_invitado, director_escuela_investigacion, guardar_recorrido_informe_docente_invitado, secuencia_reporte_validacion_asistencia, secuencia_solicitud_validacion_asistencia, experto_uath_revisa_asistencia, director_uath, getmonthname, vicerrector_investigacion_posgrado, \
    elemento_repetido_lista, notificar_gestion_dato, guardar_recorrido_solicitud_base_institucional, extension_archivo, asistente_direccion_cee
from investigacion.models import BaseInstitucional, DocenteInvitado, FuncionDocenteInvitado, CriterioDocenteInvitado, HorarioDocenteInvitado, ESTADO_HORARIO_DOCENTE, ActividadCriterioDocenteInvitado, InformeDocenteInvitado, ActividadInformeDocenteInvitado, AnexoInformeDocenteInvitado, AsistenciaDocenteInvitado, VALOR_AVANCE_ACTIVIDAD, DetalleAsistenciaDocenteInvitado, ConclusionRecomendacionInformeDocenteInvitado, ArchivoBaseInstitucional, SolicitudBaseInstitucional, RecorridoSolicitudBaseInstitucional
from sagest.commonviews import obtener_estado_solicitud, obtener_estados_solicitud
from settings import SITE_STORAGE, MEDIA_ROOT
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, generar_nombre, email_valido, \
    validar_archivo, null_to_decimal, cuenta_email_disponible_para_envio, fechaletra_corta, fecha_letra_rango, dia_semana_enletras_fecha, elimina_tildes, remover_caracteres_especiales_unicode, \
    remover_caracteres
from sga.funcionesxhtml2pdf import convert_html_to_pdf
from sga.models import CUENTAS_CORREOS, Persona, MESES_CHOICES, Profesor, Modalidad, Turno
from django.template import Context
from django.template.loader import get_template

import time as ET
import collections
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

    es_vicerrector = persona.es_vicerrector_investigacion()
    es_tecnico_inv = persona.es_tecnico_investigacion()
    es_asistente_cee = persona == asistente_direccion_cee()
    otro = True

    if not es_vicerrector and not es_tecnico_inv and not otro:
    # if not es_vicerrector and not es_tecnico_investigacion:
        return HttpResponseRedirect("/?info=Usted no tiene permitido el acceso al módulo.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addbase':
            try:
                f = BaseInstitucionalForm(request.POST)

                if f.is_valid():
                    # Obtener los valores del formulario
                    titulo = f.cleaned_data['titulo'].strip()
                    contexto = f.cleaned_data['contexto'].strip()

                    # Validar que no esté repetido el título
                    if BaseInstitucional.objects.values('id').filter(titulo__icontains=titulo, status=True).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El Título de la base institucional ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    # Archivos
                    nfilas_ca_archivo = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else []  # Números de filas que tienen lleno el campo archivo en detalle de anexos
                    nfilas_archivo = request.POST.getlist('nfila_archivo[]')  # Todos los número de filas del detalle de archivos
                    descripciones_archivo = request.POST.getlist('descripcion_archivo[]')  # Todas las descripciones detalle de archivos
                    archivos_base = request.FILES.getlist('archivo_base[]')  # Todos los archivos del detalle

                    # Valido los archivos cargados de detalle de anexos
                    for nfila, archivo in zip(nfilas_ca_archivo, archivos_base):
                        descripcionarchivo = 'Archivos'
                        resp = validar_archivo(descripcionarchivo, archivo, variable_valor("TIPOS_ANEXOS_ASESORIAS_INV"), variable_valor("TAMANIO_ANEXOS_ASESORIAS_INV"))
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"{resp['mensaje']} en la fila # {nfila['cfila']}", "showSwal": "True", "swalType": "warning"})

                    # Validar que las descripciones no estén repetidas
                    repetido = elemento_repetido_lista(descripciones_archivo)
                    if repetido:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"La descripción <b>{repetido[0]}</b> en el detalle de archivos está repetida", "showSwal": "True", "swalType": "warning"})

                    # Guardar la base institucional
                    baseinstitucional = BaseInstitucional(
                        titulo=titulo,
                        contexto=contexto,
                        visible=True
                    )
                    baseinstitucional.save(request)

                    # Guardar los archivos de la base
                    for nfila, descripcion in zip(nfilas_archivo, descripciones_archivo):
                        archivobase = ArchivoBaseInstitucional(
                            baseinstitucional=baseinstitucional,
                            descripcion=descripcion.strip(),
                            visible=True
                        )
                        archivobase.save(request)

                        # Guardo el archivo del detalle
                        for nfilaarchi, archivo in zip(nfilas_ca_archivo, archivos_base):
                            # Si la fila de la descripcion es igual a la fila que contiene archivo
                            if int(nfilaarchi['nfila']) == int(nfila):
                                # actualizo campo archivo del registro creado
                                archivoreg = archivo
                                archivoreg._name = generar_nombre("archivo_", archivoreg._name)
                                archivobase.archivo = archivoreg
                                archivobase.save(request)
                                break

                    log(f'{persona} agregó base institucional para artículos científicos {baseinstitucional}', request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito.", "showSwal": True})
                else:
                    for k, v in f.errors.items():
                        raise NameError( k + ', ' + v[0])
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editbase':
            try:
                f = BaseInstitucionalForm(request.POST)

                if f.is_valid():
                    # Obtener los valores del formulario
                    titulo = f.cleaned_data['titulo'].strip()
                    contexto = f.cleaned_data['contexto'].strip()

                    # Validar que no esté repetido el título
                    if BaseInstitucional.objects.values('id').filter(titulo__icontains=titulo, status=True).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El Título de la base institucional ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    # Archivos
                    nfilas_ca_archivo = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else []  # Números de filas que tienen lleno el campo archivo en detalle de anexos
                    nfilas_archivo = request.POST.getlist('nfila_archivo[]')  # Todos los número de filas del detalle de archivos
                    idsreg_archivo = request.POST.getlist('idregarchivo[]')  # Todos los ids de detalle de archivos
                    descripciones_archivo = request.POST.getlist('descripcion_archivo[]')  # Todas las descripciones detalle de archivos
                    archivos_base = request.FILES.getlist('archivo_base[]')  # Todos los archivos del detalle

                    # Valido los archivos cargados de detalle de anexos
                    for nfila, archivo in zip(nfilas_ca_archivo, archivos_base):
                        descripcionarchivo = 'Archivos'
                        resp = validar_archivo(descripcionarchivo, archivo, variable_valor("TIPOS_ANEXOS_ASESORIAS_INV"), variable_valor("TAMANIO_ANEXOS_ASESORIAS_INV"))
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"{resp['mensaje']} en la fila # {nfila['cfila']}", "showSwal": "True", "swalType": "warning"})

                    # Validar que las descripciones no estén repetidas
                    repetido = elemento_repetido_lista(descripciones_archivo)
                    if repetido:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"La descripción <b>{repetido[0]}</b> en el detalle de archivos está repetida", "showSwal": "True", "swalType": "warning"})

                    # Consultar la base institucional
                    baseinstitucional = BaseInstitucional.objects.get(pk=int(encrypt(request.POST['id'])))

                    # Actualizar la base institucional
                    baseinstitucional.titulo = titulo
                    baseinstitucional.contexto = contexto
                    baseinstitucional.save(request)

                    # Guardar los archivos de la base
                    for idreg, nfila, descripcion in zip(idsreg_archivo, nfilas_archivo, descripciones_archivo):
                        # Si es registro nuevo
                        if int(idreg) == 0:
                            archivobase = ArchivoBaseInstitucional(
                                baseinstitucional=baseinstitucional,
                                descripcion=descripcion.strip(),
                                visible=True
                            )
                        else:
                            archivobase = ArchivoBaseInstitucional.objects.get(pk=idreg)
                            archivobase.descripcion = descripcion.strip()

                        archivobase.save(request)

                        # Guardo el archivo del detalle
                        for nfilaarchi, archivo in zip(nfilas_ca_archivo, archivos_base):
                            # Si la fila de la descripcion es igual a la fila que contiene archivo
                            if int(nfilaarchi['nfila']) == int(nfila):
                                # actualizo campo archivo del registro creado
                                archivoreg = archivo
                                archivoreg._name = generar_nombre("archivo_", archivoreg._name)
                                archivobase.archivo = archivoreg
                                archivobase.save(request)
                                break

                    log(f'{persona} editó base institucional para artículos científicos {baseinstitucional}', request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito.", "showSwal": True})
                else:
                    for k, v in f.errors.items():
                        raise NameError( k + ', ' + v[0])
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'asignarvisible':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar la base institucional
                baseinstitucional = BaseInstitucional.objects.get(pk=int(encrypt(request.POST['id'])))
                visible = request.POST['valor'] == 'S'

                # Actualizar el registro
                baseinstitucional.visible = visible
                baseinstitucional.save(request)

                log(f'{persona} asignó estado {"visible" if visible else "no visible"} para la base institucional {baseinstitucional}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'gestionarsolicitud':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar la solicitud y cita de asesormiento
                solicitudbase = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(request.POST['id'])))
                asesoramiento = solicitudbase.citaasesoria

                # Verifico que se pueda gestionar
                if not solicitudbase.puede_gestionar():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede gestionar la solicitud", "showSwal": "True", "swalType": "warning"})

                # Obtengo los valores del formulario
                asistio = 'asistio' in request.POST
                inicioasesoria = finasesoria = None
                if asistio:
                    inicioasesoria = datetime.strptime(request.POST['inicioasesoria'], '%H:%M').time()
                    finasesoria = datetime.strptime(request.POST['finasesoria'], '%H:%M').time()

                observacion = request.POST['observacion'].strip()
                estadogestion = request.POST['estadogestion']

                # Validar las horas
                if asistio:
                    if datetime.combine(solicitudbase.fechacita, finasesoria) < datetime.combine(solicitudbase.fechacita, inicioasesoria):
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La hora de fin de asesoría debe ser mayor a la hora de inicio", "showSwal": "True", "swalType": "warning"})

                # Obtengo estado VALIDADO o NEGADO
                estado = obtener_estado_solicitud(24, estadogestion)

                # Actualizar la solicitud
                solicitudbase.inicioasesoria = inicioasesoria
                solicitudbase.finasesoria = finasesoria
                solicitudbase.asistio = asistio
                solicitudbase.fechavalida = datetime.now()
                solicitudbase.valida = persona
                solicitudbase.cargovalida = persona.mi_cargo_actual().denominacionpuesto
                solicitudbase.observacion = observacion
                solicitudbase.estado = estado
                solicitudbase.save(request)

                # Guardar el recorrido
                guardar_recorrido_solicitud_base_institucional(solicitudbase, estado, observacion, request)

                # Obtener estado y actualizar el asesoramiento
                if asistio:
                    estadoasesoria = 2 if estado.valor == 3 else 4
                    estadolog = "validado"
                else:
                    estadoasesoria = 4
                    estadolog = "negado"

                asesoramiento.horaculminacion = finasesoria
                asesoramiento.funcionarioasesortecnico = persona
                asesoramiento.observacion = observacion
                asesoramiento.estado = estadoasesoria
                asesoramiento.save(request)

                # Notificar por e-mail al responsable
                notificar_gestion_dato(solicitudbase, "VALSOL" if estado.valor == 3 else "NEGSOL", request)

                # Notificar por e-mail al solicitante
                notificar_gestion_dato(solicitudbase, "VALSOLPRO" if estado.valor == 3 else "NEGSOLPRO", request)

                log(f'{persona} asignó estado {estadolog} a solicitud de base institucional {solicitudbase}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'firmaractareunion':
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

                # Consulto la solicitud
                solicitudbase = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(request.POST['iddoc'])))

                # Obtengo estado ACTA FA.
                estadoregistro = obtener_estado_solicitud(24, 7)

                # Obtengo el archivo del acta de reunión
                archivoacta = solicitudbase.archivoctafirmada
                rutapdfarchivo = SITE_STORAGE + archivoacta.url
                textoabuscar = solicitudbase.valida.nombre_completo().title()
                textofirma = 'Funcionario Asesor:'
                ocurrencia = 1

                vecesencontrado = 0
                # ocurrencia = 5

                # Obtener coordenadas para ubicar al firma dependiendo de donde se encuentra ubicado el nombre de la persona
                documento = fitz.open(rutapdfarchivo)
                # numpaginafirma = int(documento.page_count) - 1

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
                        break

                valor = None
                for cadena in words_dict[0]:
                    linea = cadena[4].replace("\n", " ")
                    if linea:
                        linea = linea.strip()

                    if textoabuscar in linea:
                        valor = cadena

                        vecesencontrado += 1
                        if vecesencontrado == ocurrencia:
                            break

                if valor:
                    y = 5000 - int(valor[3]) - 4115
                else:
                    y = 0

                # x = 127  # izq
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
                    archivo_a_firmar=archivoacta,
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

                nombre = "actareunionfirmada"

                nombrearchivofirmado = generar_nombre(nombre, nombre + '.pdf')
                objarchivo = DjangoFile(generar_archivo_firmado, nombrearchivofirmado)

                solicitudbase.archivoctafirmada = objarchivo
                solicitudbase.actafirmaasesor = True
                solicitudbase.estado = estadoregistro
                solicitudbase.save(request)

                # Guardar el recorrido
                guardar_recorrido_solicitud_base_institucional(solicitudbase, estadoregistro, '', request)

                # Notificar por e-mail al responsable
                notificar_gestion_dato(solicitudbase, "FIRASEACT", request)

                # Notificar por e-mail al solicitante
                notificar_gestion_dato(solicitudbase, "FIRASEACTPRO", request)

                log(f'{persona} firmó acta de reunión de la solicitud de base institucional {solicitudbase}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True, "ida": encrypt(solicitudbase.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        # elif action == 'enviarwhatsapp':
        #     try:
        #         import pywhatkit
        #         phone_numer = '+593996734649'
        #         group_id = ''
        #         message = 'Hola que tal :) ...'
        #         time_hour = 11
        #         time_minute = 59
        #
        #         waiting_time_to_send = 15
        #         close_tab = True
        #         waiting_time_to_close = 2
        #
        #         mode = "contact"
        #
        #         print("Enviando jajja....")
        #         # pywhatkit.sendwhatmsg(phone_numer, message, time_hour, time_minute, waiting_time_to_send, close_tab, waiting_time_to_close)
        #         pywhatkit.sendwhatmsg_instantly(phone_numer, message, waiting_time_to_send, close_tab, waiting_time_to_close)
        #
        #         return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
        #     except Exception as ex:
        #         msg = ex.__str__()
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Solicitud incorrecta.", "showSwal": "True", "swalType": "error"})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'addbase':
                try:
                    data['title'] = u'Agregar Base Institucional para Artículos Científicos'
                    form = BaseInstitucionalForm()
                    data['form'] = form
                    data['tipoanexos'] = ", ".join(variable_valor("TIPOS_ANEXOS_ASESORIAS_INV"))
                    data['tamanio'] = variable_valor("TAMANIO_ANEXOS_ASESORIAS_INV")

                    return render(request, "adm_gestiondato/addbase.html", data)
                except Exception as ex:
                    pass

            elif action == 'editbase':
                try:
                    data['title'] = u'Editar Base Institucional para Artículos Científicos'
                    data['baseinstitucional'] = baseinstitucional = BaseInstitucional.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = BaseInstitucionalForm(initial={
                        "titulo": baseinstitucional.titulo,
                        "contexto": baseinstitucional.contexto
                    })
                    data['form'] = form
                    data['detalles'] = baseinstitucional.archivos()
                    data['tipoanexos'] = ", ".join(variable_valor("TIPOS_ANEXOS_ASESORIAS_INV"))
                    data['tamanio'] = variable_valor("TAMANIO_ANEXOS_ASESORIAS_INV")

                    return render(request, "adm_gestiondato/editbase.html", data)
                except Exception as ex:
                    pass

            elif action == 'solicitudes':
                try:
                    ida = request.GET.get('ida', '')
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                    desde, hasta, estadoid = request.GET.get('desde', ''), request.GET.get('hasta', ''), int(request.GET.get('estadoid', '0'))

                    if search:
                        data['s'] = search
                        ss = search.split(" ")
                        if len(ss) == 1:
                            filtro = filtro & (Q(solicita__nombres__icontains=search) |
                                               Q(solicita__apellido1__icontains=search) |
                                               Q(solicita__apellido2__icontains=search))
                        else:
                            filtro = filtro & (Q(solicita__apellido1__contains=ss[0]) &
                                               Q(solicita__apellido2__contains=ss[1]))

                        url_vars += f'&s={search}'

                    if desde:
                        data['desde'] = datetime.strptime(desde, '%Y-%m-%d').date()
                        filtro = filtro & Q(fecha__gte=desde)
                        url_vars += f'&desde={desde}'

                    if hasta:
                        data['hasta'] = datetime.strptime(hasta, '%Y-%m-%d').date()
                        filtro = filtro & Q(fecha__lte=hasta)
                        url_vars += f'&hasta={hasta}'

                    data['estadoid'] = estadoid
                    if estadoid:
                        filtro = filtro & Q(estado__valor=estadoid)
                        url_vars += f'&estadoid={estadoid}'

                    solicitudes = SolicitudBaseInstitucional.objects.filter(filtro).order_by('-secuencia')

                    paging = MiPaginador(solicitudes, 25)
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
                    data['solicitudes'] = page.object_list
                    data['estados'] = obtener_estados_solicitud(24, [1, 2, 3, 4, 5, 6, 7])
                    data['fechadesde'] = datetime.now().date()
                    data['fechahasta'] = datetime.now().date()
                    data['esasistente'] = es_asistente_cee
                    data['title'] = u'Solicitudes de Bases Institucionales para Artículos Científicos'

                    if ida:
                        solicitudbase = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(ida)))
                        data['acuerdo'] = solicitudbase.archivoctafirmada.url
                        data['tipoacuerdo'] = 'Acta de Reunión Firmada'

                    return render(request, "adm_gestiondato/solicitudbase.html", data)
                except Exception as ex:
                    pass

            elif action == 'informacionsolicitud':
                try:
                    title = u'Información de la Solicitud de Base Institucional para Artículos Científicos'
                    solicitudbase = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitudbase'] = solicitudbase
                    template = get_template("pro_gestiondato/modal/informacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'gestionarsolicitud':
                try:
                    data['title'] = u'Gestionar Solicitud de Base Institucional para Artículos Científicos'
                    data['solicitudbase'] = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(request.GET['id'])))

                    template = get_template("adm_gestiondato/modal/gestionarsolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'firmaractareunion':
                try:
                    solicitudbase = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = f'Firmar Acta de Reunión. Funcionario Asesor: {solicitudbase.valida.nombre_completo_inverso()[:30]}'
                    data['solicitud'] = solicitudbase
                    data['iddoc'] = solicitudbase.id  # ID del documento a firmar
                    data['idper'] = solicitudbase.valida.id  # ID de la persona que firma
                    data['tipofirma'] = 'ASE'

                    data['mensaje'] = f"Firma del Acta de Reunión N° <b>{solicitudbase.numeroacta}</b> del docente <b>{solicitudbase.solicita.nombre_completo_inverso()}</b>"
                    data['accionfirma'] = action

                    template = get_template("pro_becadocente/firmardocumento.html")
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
                    filtro = filtro & (Q(titulo__icontains=search))
                    url_vars += '&s=' + search

                docentes = BaseInstitucional.objects.filter(filtro).order_by('fecha_creacion')

                paging = MiPaginador(docentes, 5) # 25
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
                data['basesinstitucionales'] = page.object_list
                data['estecnico'] = es_tecnico_inv
                data['title'] = u'Bases Institucionales para Artículos Científicos'

                return render(request, "adm_gestiondato/view.html", data)
            except Exception as ex:
                msg = ex.__str__()
                return HttpResponseRedirect(f"/?info=Error al obtener los datos. {msg}")
