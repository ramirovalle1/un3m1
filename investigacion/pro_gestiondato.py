# -*- coding: UTF-8 -*-
import io
import json
import os
import calendar
from math import ceil
from core.firmar_documentos_ec import JavaFirmaEc

import PyPDF2
from datetime import time, datetime, timedelta, date
from decimal import Decimal
from calendar import monthrange

import requests
import xlsxwriter
import zipfile
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
from decorators import secure_module
from investigacion.forms import SolicitudBaseInstitucionalForm, HorarioServicioForm
from investigacion.funciones import FORMATOS_CELDAS_EXCEL, notificar_docente_invitado, iniciales_nombres_apellidos, vicerrector_investigacion_posgrado, getmonthname, decano_investigacion, analista_verifica_informe_docente_invitado, isvalidurl, director_escuela_investigacion, \
    reemplazar_fuente_para_informe, guardar_recorrido_informe_docente_invitado, secuencia_informe_docente_invitado, coordinacion_carrera_distributivo_docente, secuencia_asesoria, secuencia_solicitud_base_institucional, notificar_gestion_dato, periodo_vigente_distributivo_docente_investigacion, \
    secuencia_acuerdo_confidencialidad, guardar_recorrido_solicitud_base_institucional, es_director_carrera, tiene_horas_docencia, secuencia_acta_reunion_solicitud_base, extension_archivo
from investigacion.models import SolicitudBaseInstitucional, DocenteInvitado, FuncionDocenteInvitado, HorarioDocenteInvitado, DetalleHorarioDocenteInvitado, ESTADO_CUMPLIMIENTO_ACTIVIDAD, InformeDocenteInvitado, AnexoInformeDocenteInvitado, ActividadInformeDocenteInvitado, ActividadCriterioDocenteInvitado, \
    ConclusionRecomendacionInformeDocenteInvitado, TIPO_ANEXO, RecorridoInformeDocenteInvitado, BaseInstitucional, TurnoCita, RecorridoSolicitudBaseInstitucional, DetalleSolicitudBaseInstitucional, \
    TipoTrabajoBaseInstitucional
from sagest.commonviews import obtener_estado_solicitud, obtener_estados_solicitud
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, generar_nombre, email_valido, \
    validar_archivo, null_to_decimal, cuenta_email_disponible_para_envio, fechaletra_corta, fecha_letra_rango, dia_semana_enletras_fecha, remover_atributo_style_html, \
    elimina_tildes, remover_caracteres_especiales_unicode, remover_caracteres
from sga.funcionesxhtml2pdf import convert_html_to_pdf
from sga.models import CUENTAS_CORREOS, Persona, MESES_CHOICES, Profesor, Modalidad, Turno, AsesoramientoSEE, AsesoramientoSEETipoTrabajo
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
    es_profesor = perfilprincipal.es_profesor()

    if not es_profesor:
        return HttpResponseRedirect("/?info=El Módulo está disponible para docentes.")

    periodo = request.session['periodo']
    profesor = persona.profesor()

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitud':
            try:
                f = SolicitudBaseInstitucionalForm(request.POST)

                if f.is_valid():
                    # Obtener los valores del formulario
                    tipotrabajo = f.cleaned_data['tipotrabajo']
                    baseinstitucional = f.cleaned_data['baseinstitucional']
                    fecha = datetime.strptime(request.POST['fecha'], '%Y-%m-%d').date()
                    idturno = request.POST['idturno']
                    motivo = request.POST['motivo'].strip()
                    idarchivobase = request.POST['archivoselecc']

                    # Consultar turno
                    turnocita = TurnoCita.objects.get(pk=idturno)

                    # Obtener fecha en letras
                    dialetras = dia_semana_enletras_fecha(fecha)
                    fechadialetras = dialetras + " " + str(fecha.day) + " de " + MESES_CHOICES[fecha.month - 1][1].capitalize() + " del " + str(fecha.year)
                    mensajehorario = "<b>" + fechadialetras + "</b> en horario de <b>" + turnocita.comienza.strftime('%H:%M') + " a " + turnocita.termina.strftime('%H:%M') + "</b>"

                    # Validar si aún existe el turno disponible
                    if not AsesoramientoSEE.objects.values("id").filter(status=True, fechaatencion=fecha, horaatencion=turnocita.comienza).exists():
                        # Consulto el tipo de trabajo SOLICITUD BASE INSTITUCIONAL
                        tipotrabajoase = AsesoramientoSEETipoTrabajo.objects.filter(status=True, tipo=2)[0]

                        # Obtener periodo vigente del distributivo del profesor
                        periodovigente = periodo_vigente_distributivo_docente_investigacion(profesor)

                        # Consulto la coordinacion y carrera vigente
                        reg = coordinacion_carrera_distributivo_docente(profesor)

                        # Guardar el asesoramiento
                        asesoramiento = AsesoramientoSEE(
                            periodo=periodovigente,
                            persona=persona,
                            titulo= f'Solicitud de Base Institucional: {baseinstitucional.titulo}',
                            tipotrabajo=tipotrabajoase,
                            descripcion=motivo,
                            coordinacion_id=reg["idcoordinacion"],
                            carrera_id=reg["idcarrera"],
                            fechaatencion=fecha,
                            horaatencion=turnocita.comienza
                        )
                        asesoramiento.save(request)

                        # Obtengo estado SOLICITADO
                        estado = obtener_estado_solicitud(24, 1)

                        # Obtener secuencia de la solicitud
                        secuencia = secuencia_solicitud_base_institucional()

                        # Guardar la solicitud
                        solicitudbase = SolicitudBaseInstitucional(
                            secuencia=secuencia,
                            numero=str(secuencia).zfill(5),
                            fecha=datetime.now().date(),
                            solicita=persona,
                            periodo=periodovigente,
                            coordinacion=asesoramiento.coordinacion,
                            carrera=asesoramiento.carrera,
                            tipotrabajo=tipotrabajo,
                            baseinstitucional=baseinstitucional,
                            motivo=motivo,
                            fechacita=fecha,
                            iniciocita=turnocita.comienza,
                            fincita=turnocita.termina,
                            citaasesoria=asesoramiento,
                            estado=estado
                        )
                        solicitudbase.save(request)

                        # Guardar el detalle de la solicitud
                        detallesolicitud = DetalleSolicitudBaseInstitucional(
                            solicitud=solicitudbase,
                            archivobase_id=idarchivobase
                        )
                        detallesolicitud.save(request)

                        # Guardar el recorrido
                        guardar_recorrido_solicitud_base_institucional(solicitudbase, estado, '', request)

                        # Notificar por e-mail al responsable
                        notificar_gestion_dato(solicitudbase, "REGSOL", request)

                        # Notificar por e-mail al solicitante
                        notificar_gestion_dato(solicitudbase, "REGSOLPRO", request)

                        log(f'{persona} agregó solicitud de asesoramiento del centro de estudios estadísticos {asesoramiento}', request, "add")
                        log(f'{persona} agregó solicitud de base institucional {solicitudbase}', request, "add")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito. <br><br>Usted agendó una cita con el Centro de Estudios Estadísticos para el asesoramiento y revisión de su solicitud para el {}".format(mensajehorario), "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El turno para el día {} ya no está disponible".format(mensajehorario), "showSwal": "True", "swalType": "warning"})
                else:
                    for k, v in f.errors.items():
                        raise NameError( k + ', ' + v[0])
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editsolicitud':
            try:
                f = SolicitudBaseInstitucionalForm(request.POST)

                if f.is_valid():
                    # Consultar la solicitud y cita de asesormiento
                    solicitudbase = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(request.POST['id'])))
                    asesoramiento = solicitudbase.citaasesoria

                    # Verifico que se pueda editar
                    if not solicitudbase.puede_editar_docente():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido revisado por otra instancia", "showSwal": "True", "swalType": "warning"})

                    # Obtener los valores del formulario
                    tipotrabajo = f.cleaned_data['tipotrabajo']
                    baseinstitucional = f.cleaned_data['baseinstitucional']
                    motivo = request.POST['motivo'].strip()
                    idarchivobase = request.POST['archivoselecc']

                    # Actualizar la solicitud
                    solicitudbase.tipotrabajo = tipotrabajo
                    solicitudbase.baseinstitucional = baseinstitucional
                    solicitudbase.motivo = motivo
                    solicitudbase.save(request)

                    # Actualizar el detalle de la solicitud
                    detallesolicitud = DetalleSolicitudBaseInstitucional.objects.filter(status=True, solicitud=solicitudbase)[0]
                    detallesolicitud.archivobase_id = idarchivobase
                    detallesolicitud.save(request)

                    # Actualizar el asesoramiento
                    asesoramiento.titulo = f'Solicitud de Base Institucional: {baseinstitucional.titulo}'
                    asesoramiento.descripcion = motivo
                    asesoramiento.save(request)

                    log(f'{persona} editó solicitud de asesoramiento del centro de estudios estadísticos {asesoramiento}', request, "edit")
                    log(f'{persona} editó solicitud de base institucional {solicitudbase}', request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito.", "showSwal": True})
                else:
                    for k, v in f.errors.items():
                        raise NameError( k + ', ' + v[0])
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'reagendarcita':
            try:
                f = SolicitudBaseInstitucionalForm(request.POST)

                if f.is_valid():
                    # Consultar la solicitud y cita de asesormiento
                    solicitudbase = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(request.POST['id'])))
                    asesoramiento = solicitudbase.citaasesoria

                    # Verifico que se pueda editar
                    if not solicitudbase.puede_editar_docente():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido revisado por otra instancia", "showSwal": "True", "swalType": "warning"})

                    # Obtener los valores del formulario
                    fecha = datetime.strptime(request.POST['fecha'], '%Y-%m-%d').date()
                    idturno = request.POST['idturno']

                    # Consultar turno
                    turnocita = TurnoCita.objects.get(pk=idturno)

                    # Obtener fecha en letras
                    dialetras = dia_semana_enletras_fecha(fecha)
                    fechadialetras = dialetras + " " + str(fecha.day) + " de " + MESES_CHOICES[fecha.month - 1][1].capitalize() + " del " + str(fecha.year)
                    mensajehorario = "<b>" + fechadialetras + "</b> en horario de <b>" + turnocita.comienza.strftime('%H:%M') + " a " + turnocita.termina.strftime('%H:%M') + "</b>"

                    # Validar si aún existe el turno disponible
                    if not AsesoramientoSEE.objects.values("id").filter(status=True, fechaatencion=fecha, horaatencion=turnocita.comienza).exists():
                        # Actualizar la solicitud
                        solicitudbase.fechacita = fecha
                        solicitudbase.iniciocita = turnocita.comienza
                        solicitudbase.fincita = turnocita.termina
                        solicitudbase.save(request)

                        # Actualizar el asesoramiento
                        asesoramiento.fechaatencion = fecha
                        asesoramiento.horaatencion = turnocita.comienza
                        asesoramiento.save(request)

                        # Notificar por e-mail al responsable
                        notificar_gestion_dato(solicitudbase, "REASOL", request)

                        # Notificar por e-mail al solicitante
                        notificar_gestion_dato(solicitudbase, "REASOLPRO", request)

                        log(f'{persona} re-agendó cita con el centro de estudios estadísticos {solicitudbase}', request, "edit")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito. <br><br>Usted re-agendó una cita con el Centro de Estudios Estadísticos para el asesoramiento y revisión de su solicitud para el {}".format(mensajehorario), "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El turno para el día {} ya no está disponible".format(mensajehorario), "showSwal": "True", "swalType": "warning"})
                else:
                    for k, v in f.errors.items():
                        raise NameError( k + ', ' + v[0])
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'cancelarsolicitud':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar la solicitud y cita de asesormiento
                solicitudbase = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(request.POST['id'])))
                asesoramiento = solicitudbase.citaasesoria

                # Verifico que se pueda cancelar
                if not solicitudbase.puede_editar_docente():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede cancelar la solicitud", "showSwal": "True", "swalType": "warning"})

                # Obtengo estado CANCELADO
                estado = obtener_estado_solicitud(24, 2)

                # Obtengo los valores del formulario
                observacion = request.POST['observacion'].strip()

                # Actualizar el registro de la solicitud
                solicitudbase.observacion = observacion
                solicitudbase.estado = estado
                solicitudbase.save(request)

                # Guardar el recorrido
                guardar_recorrido_solicitud_base_institucional(solicitudbase, estado, observacion.upper(), request)

                # Eliminar la cita de asesoramiento
                asesoramiento.status = False
                asesoramiento.save(request)

                # Notificar por e-mail al responsable
                notificar_gestion_dato(solicitudbase, "CANSOL", request)

                # Notificar por e-mail al solicitante
                notificar_gestion_dato(solicitudbase, "CANSOLPRO", request)

                log(f'{persona} canceló solicitud de base institucional {solicitudbase}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'actareunionpdf':
            try:
                data = {}

                solicitudbase = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(request.POST['id'])))

                if not solicitudbase.actaimpresa:
                    data['solicitudbase'] = solicitudbase
                    data['nombrearchivo'] = solicitudbase.detalles()[0].archivobase.descripcion
                    data['titulosnivel3'] = persona.mis_titulaciones().filter(verificado=True, titulo__nivel__nivel=3).order_by('-fechaobtencion')
                    data['titulosnivel4'] = persona.mis_titulaciones().filter(verificado=True, titulo__nivel__nivel=4, titulo__grado_id=2).order_by('-fechaobtencion')
                    data['titulosphd'] = persona.mis_titulaciones().filter(verificado=True, titulo__nivel__nivel=4, titulo__grado_id=1).order_by('-fechaobtencion')

                    # Generar el número del acuerdo
                    # anio = datetime.now().date().year
                    secuencia = secuencia_acta_reunion_solicitud_base()
                    # numero = f'{str(secuencia).zfill(3)}-EFI-FI-REP-AE-{anio}'
                    numero = str(secuencia).zfill(5)

                    # Obtengo estado ACTA G
                    estadoregistro = obtener_estado_solicitud(24, 5)

                    # Actualizar el registro
                    solicitudbase.secuenciaacta = secuencia
                    solicitudbase.numeroacta = numero
                    solicitudbase.fechaacta = datetime.now()
                    solicitudbase.estado = estadoregistro
                    solicitudbase.save(request)

                    # Creacion de los archivos por separado
                    directorio = SITE_STORAGE + '/media/proyectoinvestigacion/informes'
                    try:
                        os.stat(directorio)
                    except:
                        os.mkdir(directorio)

                    # Archivo de la parte 1 del informe
                    nombrearchivo = 'actareunionparte1_' + str(solicitudbase.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                    valida = convert_html_to_pdf(
                        'pro_gestiondato/actareunionpdf.html',
                        {'pagesize': 'A4', 'data': data},
                        nombrearchivo,
                        directorio
                    )

                    if not valida:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento de la parte 1 del acta de reunión."})

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
                    nombrearchivoresultado = generar_nombre('actareunion', 'actareunion.pdf')
                    pdfOutputFile = open(directorio + "/" + nombrearchivoresultado, "wb")
                    pdfWriter.write(pdfOutputFile)

                    # Borro los documento individuales creados a exepción del archivo del proyecto cargado por el docente
                    os.remove(archivo1)

                    pdfOutputFile.close()

                    # archivo = SITE_STORAGE + '/media/certificadoedocente/' + nombrearchivoresultado
                    archivo = directorio + "/" + nombrearchivoresultado

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
                    solicitudbase.actaimpresa = True
                    solicitudbase.archivoacta = archivocopiado
                    solicitudbase.save(request)

                    # Guardar el recorrido
                    guardar_recorrido_solicitud_base_institucional(solicitudbase, estadoregistro, '', request)

                    # Borro el acta creada de manera general, no la del registro
                    os.remove(archivo)

                    log(f'{persona} generó acta de reunión de la solicitud de base institucional {solicitudbase}', request, "edit")
                return JsonResponse({"result": "ok", "idacta": encrypt(solicitudbase.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento del acta de reunión. [%s]" % msg})

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

                # Obtengo estado ACTA FD.
                estadoregistro = obtener_estado_solicitud(24, 6)

                # Obtengo el archivo del acta
                archivoacta = solicitudbase.archivoacta
                rutapdfarchivo = SITE_STORAGE + archivoacta.url
                textoabuscar = solicitudbase.solicita.nombre_completo().title()
                textofirma = 'Docente:'
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
                    y = 5000 - int(valor[3]) - 4125
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
                solicitudbase.actafirmaelabora = True
                solicitudbase.estado = estadoregistro
                solicitudbase.save(request)

                # Guardar el recorrido
                guardar_recorrido_solicitud_base_institucional(solicitudbase, estadoregistro, '', request)

                # Notificar por e-mail al responsable
                notificar_gestion_dato(solicitudbase, "FIRACT", request)

                # Notificar por e-mail al solicitante
                notificar_gestion_dato(solicitudbase, "FIRACTPRO", request)

                log(f'{persona} firmó acta de reunión de la solicitud de base institucional {solicitudbase}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True, "idacta": encrypt(solicitudbase.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'acuerdopdf':
            try:
                data = {}

                solicitudbase = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(request.POST['id'])))

                if not solicitudbase.impreso:
                    # Generar el número del acuerdo
                    anio = datetime.now().date().year
                    fecha = datetime.now().date()
                    secuencia = secuencia_acuerdo_confidencialidad()
                    # numero = f'{str(secuencia).zfill(3)}-EFI-FI-REP-AE-{anio}'
                    numero = str(secuencia).zfill(5)

                    # Obtengo estado ACUERDO G.
                    estadoregistro = obtener_estado_solicitud(24, 8)

                    # Actualizar el registro
                    solicitudbase.secuenciaacuerdo = secuencia
                    solicitudbase.numeroacuerdo = numero
                    solicitudbase.fechaacuerdo = datetime.now()
                    solicitudbase.estado = estadoregistro
                    solicitudbase.save(request)

                    data['solicitudbase'] = solicitudbase
                    data['tipostrabajo'] = TipoTrabajoBaseInstitucional.objects.filter(status=True, vigente=True).order_by('descripcion')
                    data['fechaletras'] = f'{str(fecha.day).zfill(2)} de {getmonthname(fecha)} de {anio}'
                    data['nombrearchivo'] = solicitudbase.detalles()[0].archivobase.descripcion

                    # Creacion de los archivos por separado
                    directorio = SITE_STORAGE + '/media/proyectoinvestigacion/informes'
                    try:
                        os.stat(directorio)
                    except:
                        os.mkdir(directorio)

                    # Archivo de la parte 1 del informe
                    nombrearchivo = 'acuerdoparte1_' + str(solicitudbase.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                    valida = convert_html_to_pdf(
                        'pro_gestiondato/acuerdoconfidencialidadpdf.html',
                        {'pagesize': 'A4', 'data': data},
                        nombrearchivo,
                        directorio
                    )

                    if not valida:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento de la parte 1 del acuerdo."})

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
                    nombrearchivoresultado = generar_nombre('acuerdo', 'acuerdo.pdf')
                    pdfOutputFile = open(directorio + "/" + nombrearchivoresultado, "wb")
                    pdfWriter.write(pdfOutputFile)

                    # Borro los documento individuales creados a exepción del archivo del proyecto cargado por el docente
                    os.remove(archivo1)

                    pdfOutputFile.close()

                    # archivo = SITE_STORAGE + '/media/certificadoedocente/' + nombrearchivoresultado
                    archivo = directorio + "/" + nombrearchivoresultado

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
                    solicitudbase.impreso = True
                    solicitudbase.archivo = archivocopiado
                    solicitudbase.save(request)

                    # Guardar el recorrido
                    guardar_recorrido_solicitud_base_institucional(solicitudbase, estadoregistro, '', request)

                    # Borro el acuerdo creado de manera general, no la del registro
                    os.remove(archivo)

                    log(f'{persona} generó acuerdo de confidencialidad de la solicitud de base institucional {solicitudbase}', request, "edit")
                return JsonResponse({"result": "ok", "ida": encrypt(solicitudbase.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento del acuerdo. [%s]" % msg})

        elif action == 'firmaracuerdo':
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

                # Obtengo estado ACUERDO F
                estadoregistro = obtener_estado_solicitud(24, 9)

                # Obtengo el archivo del acuerdo
                archivoacuerdo = solicitudbase.archivo
                rutapdfarchivo = SITE_STORAGE + archivoacuerdo.url
                textoabuscar = solicitudbase.solicita.nombre_completo().title()
                textofirma = textoabuscar
                ocurrencia = 1

                vecesencontrado = 0
                # ocurrencia = 5

                # Obtener coordenadas para ubicar al firma dependiendo de donde se encuentra ubicado el nombre de la persona
                documento = fitz.open(rutapdfarchivo)
                numpaginafirma = int(documento.page_count) - 1

                # # Busca la página donde se encuentran ubicados los textos: Elaboraro por, Verificado por y Aprobado por
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
                #         if textofirma in linea:
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
                    y = 5000 - int(valor[3]) - 4047
                else:
                    y = 0

                x = 70  # izq
                # x = 230  # cent
                # x = 350  # der

                # Si no existe el nombre de la persona en el documento
                if y == 0:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"No se encuentra el nombre del firmante en el documento", "showSwal": "True", "swalType": "warning"})

                # Obtener extensión y leer archivo de la firma
                extfirma = os.path.splitext(archivofirma.name)[1][1:]
                bytesfirma = archivofirma.read()

                # Firma del documento
                datau = JavaFirmaEc(
                    archivo_a_firmar=archivoacuerdo,
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

                nombre = "acuerdofirmado"

                nombrearchivofirmado = generar_nombre(nombre, nombre + '.pdf')
                objarchivo = DjangoFile(generar_archivo_firmado, nombrearchivofirmado)

                solicitudbase.archivofirmado = objarchivo
                solicitudbase.firmaelabora = True
                solicitudbase.estado = estadoregistro
                solicitudbase.save(request)

                # Guardar el recorrido
                guardar_recorrido_solicitud_base_institucional(solicitudbase, estadoregistro, '', request)

                # Crear una carpeta comprimida con los archivos de la base institucional
                directorio = os.path.join(os.path.join(SITE_STORAGE, 'media', 'zipav'))
                nombre_archivo = f'solicitudbase{solicitudbase.numero.replace("-", "_")}'
                nombre_archivo = generar_nombre(f'{nombre_archivo}_', f'{nombre_archivo}_.zip')
                filename = os.path.join(directorio, nombre_archivo)
                fantasy_zip = zipfile.ZipFile(filename, 'w')
                subcarpeta = ""
                caracteres_a_quitar = "!\"\#$%&()=?¡'¿{}[],.-+*/|°^~:;"

                # Agregar los archivos de la base institucional
                for detalle in solicitudbase.detalles():
                    nombreanexo = remover_caracteres(detalle.archivobase.descripcion, caracteres_a_quitar)
                    ext = extension_archivo(detalle.archivobase.archivo.name)

                    if os.path.exists(SITE_STORAGE + detalle.archivobase.archivo.url):
                        fantasy_zip.write(SITE_STORAGE + detalle.archivobase.archivo.url, subcarpeta + "/" + nombreanexo + ext.lower())

                fantasy_zip.close()

                archivo = directorio + "/" + nombre_archivo

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
                archivocopiado.name = nombre_archivo

                # Actualizo la solicitud
                solicitudbase.archivobase = archivocopiado
                solicitudbase.totaldescarga = 0
                solicitudbase.save(request)

                # Borro el archivo creado de manera general, no la del registro
                os.remove(archivo)

                log(f'{persona} firmó acuerdo de confidencialidad de la solicitud de base institucional {solicitudbase}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True, "ida": encrypt(solicitudbase.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'descargarbase':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar la solicitud
                solicitudbase = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico si aún puede descargar
                if solicitudbase.totaldescarga > 3 or not solicitudbase.baseinstitucional.visible:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La descarga de la base institucional no se encuentra disponible", "showSwal": "True", "swalType": "warning"})

                # Actualizar el contador
                solicitudbase.totaldescarga = solicitudbase.totaldescarga + 1
                solicitudbase.save(request)

                log(f'{persona} descargó base institucional correspondiente a la solicitud {solicitudbase}', request, "edit")
                return JsonResponse({"result": "ok", "documento": solicitudbase.archivobase.url})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al intentar descargar la base. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Solicitud incorrecta.", "showSwal": "True", "swalType": "error"})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addsolicitud':
                try:
                    data['title'] = u'Agregar Solicitud de Base Institucional para Artículos Científicos'
                    form = SolicitudBaseInstitucionalForm()
                    data['form'] = form
                    data['anio'] = datetime.now().date().year
                    data['mes'] = datetime.now().date().month

                    return render(request, "pro_gestiondato/addsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'cargarcalendario':
                try:
                    # Consulta el servicio de la gestión
                    baseinstitucional = BaseInstitucional.objects.get(pk=int(request.GET['idserv']))
                    contexto = baseinstitucional.contexto
                    detalles = [{"id": detalle.id, "descripcion": detalle.descripcion, "icono": detalle.icono_archivo()} for detalle in baseinstitucional.archivos()]
                    fechaactual = datetime.now().date()
                    horaactual = datetime.now().time()

                    # Formar el calendario según mes y año
                    anio = int(request.GET['anio'])
                    mes = int(request.GET['mes'])

                    if request.GET['mov'] != '':
                        tipomovimiento = request.GET['mov']
                        if tipomovimiento == 'ant':
                            mes = mes - 1
                            if mes < 1:
                                anio = anio - 1
                                mes = 12
                        else:
                            mes = mes + 1
                            if mes > 12:
                                anio = anio + 1
                                mes = 1

                    totalturnos = TurnoCita.objects.values("id").filter(status=True, tipo=2, vigente=True).count()
                    listadias = []
                    calendario = calendar.TextCalendar()

                    for dia in calendario.itermonthdays(anio, mes):
                        if dia > 0:
                            # Consultar si existen turnos disponibles en ese día
                            fechacal = date(anio, mes, dia)

                            # Si es día laborable o la fecha no es anterior
                            if fechacal.weekday() + 1 <= 5 and fechacal >= fechaactual:
                                if fechacal > fechaactual:
                                    if not AsesoramientoSEE.objects.values("id").filter(status=True, fechaatencion=fechacal).count() == totalturnos:
                                        listadias.append({"dia": dia, "status": "TDI"})
                                    else:
                                        listadias.append({"dia": dia, "status": "OCU"})
                                else:
                                    turnos = TurnoCita.objects.filter(status=True, tipo=2).distinct().order_by('orden')
                                    disponibles = False
                                    for turno in turnos:
                                        if turno.comienza >= horaactual:
                                            if not AsesoramientoSEE.objects.values("id").filter(status=True, fechaatencion=fechacal, horaatencion=turno.comienza).exists():
                                                disponibles = True
                                                break

                                    if disponibles:
                                        listadias.append({"dia": dia, "status": "TDI"})
                                    else:
                                        listadias.append({"dia": dia, "status": "OCU"})
                            else:
                                listadias.append({"dia": dia, "status": "STU"})
                        else:
                            listadias.append({"dia": dia, "status": "STU"})

                    data['idserv'] = request.GET['idserv']
                    data['anio'] = anio
                    data['mes'] = mes
                    data['titulomes'] = MESES_CHOICES[mes - 1][1] + " " + str(anio)
                    data['listadias'] = listadias

                    template = get_template("pro_gestiondato/calendario.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'contexto': contexto, 'detalles': detalles})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargarturnosservicio':
                try:
                    # servicio = ServicioGestion.objects.get(pk=int(request.GET['idserv']))
                    baseinstitucional = BaseInstitucional.objects.get(pk=int(request.GET['idserv']))

                    anio = int(request.GET['anio'])
                    mes = int(request.GET['mes'])
                    dia = int(request.GET['dia'])

                    fechacal = date(anio, mes, dia)
                    fechaactual = datetime.now().date()
                    horaactual = datetime.now().time()

                    # Obtener fecha en letras
                    dialetras = dia_semana_enletras_fecha(fechacal)
                    fechadialetras = dialetras + " " + str(fechacal.day) + " de " + MESES_CHOICES[fechacal.month - 1][1].capitalize() + " del " + str(fechacal.year)

                    data['idserv'] = request.GET['idserv']
                    data['fecha'] = fechacal
                    data['anio'] = anio
                    data['mes'] = mes
                    data['fechadialetras'] = fechadialetras

                    turnos = TurnoCita.objects.filter(status=True, tipo=2).distinct().order_by('orden')

                    listaturnos = []

                    for turno in turnos:
                        citas = AsesoramientoSEE.objects.values("id").filter(status=True, fechaatencion=fechacal, horaatencion=turno.comienza).exists()
                        if not citas:
                            if fechacal == fechaactual:
                                if turno.comienza >= horaactual:
                                    listaturnos.append({"id": turno.id, "comienza": turno.comienza.strftime('%H:%M'), "termina": turno.termina.strftime('%H:%M')})
                            else:
                                listaturnos.append({"id": turno.id, "comienza": turno.comienza.strftime('%H:%M'), "termina": turno.termina.strftime('%H:%M')})

                    data['turnos'] = listaturnos

                    template = get_template("pro_gestiondato/turno.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editsolicitud':
                try:
                    data['title'] = u'Editar Solicitud de Base Institucional para Artículos Científicos'
                    data['solicitudbase'] = solicitudbase = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(request.GET['id'])))

                    form = SolicitudBaseInstitucionalForm(initial={
                        "tipotrabajo": solicitudbase.tipotrabajo,
                        "baseinstitucional": solicitudbase.baseinstitucional,
                        "contexto": solicitudbase.baseinstitucional.contexto
                    })
                    data['form'] = form
                    data['idarchivosolicitado'] = solicitudbase.detalles()[0].archivobase.id

                    fechacita = solicitudbase.fechacita
                    dialetras = dia_semana_enletras_fecha(fechacita)
                    fechadialetras = dialetras + " " + str(fechacita.day) + " de " + MESES_CHOICES[fechacita.month - 1][1].capitalize() + " del " + str(fechacita.year)
                    mensajehorario = fechadialetras + " en horario de " + solicitudbase.iniciocita.strftime('%H:%M') + " a " + solicitudbase.fincita.strftime('%H:%M')
                    data['mensajehorario'] = mensajehorario

                    return render(request, "pro_gestiondato/editsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'informacionbase':
                try:
                    # Consulta el servicio de la gestión
                    baseinstitucional = BaseInstitucional.objects.get(pk=int(request.GET['id']))
                    contexto = baseinstitucional.contexto
                    detalles = [{"id": detalle.id, "descripcion": detalle.descripcion, "icono": detalle.icono_archivo()} for detalle in baseinstitucional.archivos()]
                    return JsonResponse({"result": "ok", 'contexto': contexto, 'detalles': detalles})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

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

            elif action == 'reagendarcita':
                try:
                    data['title'] = u'Re-Agendar Cita para Asesoría con el Centro de Estudios Estadísticos'
                    data['solicitudbase'] = solicitudbase = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(request.GET['id'])))

                    form = SolicitudBaseInstitucionalForm(initial={
                        "tipotrabajo": solicitudbase.tipotrabajo,
                        "baseinstitucional": solicitudbase.baseinstitucional,
                        "contexto": solicitudbase.baseinstitucional.contexto
                    })
                    data['form'] = form
                    data['anio'] = datetime.now().date().year
                    data['mes'] = datetime.now().date().month

                    fechacita = solicitudbase.fechacita
                    dialetras = dia_semana_enletras_fecha(fechacita)
                    fechadialetras = dialetras + " " + str(fechacita.day) + " de " + MESES_CHOICES[fechacita.month - 1][1].capitalize() + " del " + str(fechacita.year)
                    mensajehorario = fechadialetras + " en horario de " + solicitudbase.iniciocita.strftime('%H:%M') + " a " + solicitudbase.fincita.strftime('%H:%M')
                    data['mensajehorario'] = mensajehorario

                    return render(request, "pro_gestiondato/reagendarcita.html", data)
                except Exception as ex:
                    pass

            elif action == 'cancelarsolicitud':
                try:
                    data['title'] = u'Cancelar Solicitud de Base Institucional para Artículos Científicos'
                    data['solicitudbase'] = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(request.GET['id'])))

                    template = get_template("pro_gestiondato/modal/cancelarsolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'firmaractareunion':
                try:
                    data['title'] = u'Firmar Acta de Reunión'

                    solicitudbase = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['solicitud'] = solicitudbase
                    data['iddoc'] = solicitudbase.id  # ID del documento a firmar
                    data['idper'] = solicitudbase.solicita.id  # ID de la persona que firma
                    data['tipofirma'] = 'ELA'

                    data['mensaje'] = f"Firma del Acta de Reunión N° <b>{solicitudbase.numeroacta}</b> del docente <b>{solicitudbase.solicita.nombre_completo_inverso()}</b>"
                    data['accionfirma'] = action

                    template = get_template("pro_becadocente/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'firmaracuerdo':
                try:
                    data['title'] = u'Firmar Acuerdo de Confidencialidad'

                    solicitudbase = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['solicitud'] = solicitudbase
                    data['iddoc'] = solicitudbase.id  # ID del documento a firmar
                    data['idper'] = solicitudbase.solicita.id  # ID de la persona que firma
                    data['tipofirma'] = 'ELA'

                    data['mensaje'] = f"Firma del Acuerdo de Confidencialidad N° <b>{solicitudbase.numeroacuerdo}</b> del docente <b>{solicitudbase.solicita.nombre_completo_inverso()}</b>"
                    data['accionfirma'] = action

                    template = get_template("pro_becadocente/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            try:
                ida, idacta = request.GET.get('ida', ''), request.GET.get('idacta', '')
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, solicita=persona), ''

                solicitudes = SolicitudBaseInstitucional.objects.filter(filtro).order_by('-id')

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

                # Verifico que sea director de carrera o tenga horas de docencia en el periodo vigente
                if not es_director_carrera(profesor) and not tiene_horas_docencia(profesor):
                    data["mensaje"] = "Estimado docente para poder registrar una solicitud usted debe tener asignadas horas de clase o ser director de carrera"

                if ida:
                    solicitudbase = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(ida)))
                    data['acuerdo'] = solicitudbase.archivofirmado.url if solicitudbase.archivofirmado else solicitudbase.archivo.url
                    data['tipoacuerdo'] = 'Acuerdo de Confidencialidad Firmado' if solicitudbase.archivofirmado else 'Acuerdo de Confidencialidad'

                if idacta:
                    solicitudbase = SolicitudBaseInstitucional.objects.get(pk=int(encrypt(idacta)))
                    data['actareunion'] = solicitudbase.archivoctafirmada.url if solicitudbase.archivoctafirmada else solicitudbase.archivoacta.url
                    data['tipoacta'] = 'Acta de Reunión Firmada' if solicitudbase.archivoctafirmada else 'Acta de Reunión'

                data['title'] = u'Mis Solicitudes de Bases Institucionales para Artículos Científicos'

                return render(request, "pro_gestiondato/view.html", data)
            except Exception as ex:
                msg = ex.__str__()
                return HttpResponseRedirect(f"/?info=Error al obtener los datos. {msg}")
