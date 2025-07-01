# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from django.db.models import Q, Sum
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from decorators import last_access, secure_module
from inno.funciones import enviar_notificacion_aceptar_rechazar_solicitud_asistencia_pro
from inno.models import ProgramaPac
from sagest.models import Rubro, Departamento, PersonaDepartamentoFirmas, DistributivoPersona, AnioEjercicio
from secretaria.models import Solicitud, Servicio, HistorialSolicitud, CategoriaServicio, FormatoCertificado, SolicitudAsignatura, \
    InformeHomologacionPosgrado, HistorialInformeHomologacion, IntegrantesInformeHomologacion, SecuenciaInformeHomologacion, \
    HistorialInformeHomologacion, AsignaturaCompatibleHomologacion, IntegrantesCronogramaTituEx
from settings import SOLICITUD_PREPROYECTO_ESTADO_APROBADO_ID, \
    SOLICITUD_PREPROYECTO_ESTADO_RECHAZADO_ID, MEDIA_ROOT, MEDIA_URL, SITE_STORAGE
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre, notificacion2, notificacion4, null_to_decimal
from sga.models import SolicitudAperturaClase, Carrera, Profesor, ESTADOS_PREPROYECTO
from sga.templatetags.sga_extras import encrypt
from django.template.loader import get_template
from secretaria.forms import EntregaCertificadoForm, SubirCertificadoPersonalizadoForm, SubirFormatoCertificadoForm, \
    AprobarRechazarInformePertinenciaForm, AdicionarActividadCronogramaForm, ActividadCronogramaTitulacionForm, \
    SubirInformeTecnicoPertinenciaForm, SubirCronogramaTitulacionForm, NotificarCronogramaTitulacionForm, \
    CarreraHomologableForm, IntegrantesTitulacionForm
from sga.tasks import send_html_mail
from sga.models import CUENTAS_CORREOS, PerfilAccesoUsuario, Persona, FirmaCertificadoSecretaria, InscripcionMalla, AsignaturaMalla, \
    RecordAcademico, Inscripcion, Malla, Administrativo
from django.forms import model_to_dict
from sga.funciones import notificacion3, remover_caracteres_tildes_unicode, remover_caracteres_especiales_unicode, generar_nombre, \
    notificacion, fechaletra_corta2, fechaletra_corta3
from pdip.models import ContratoDip, ContratoCarrera
from posgrado.models import ActividadCronogramaTitulacion, DetalleActividadCronogramaTitulacion, CohorteMaestria, InscripcionCohorte
from sga.funciones_templatepdf import cronogramatituex
from sga.funciones import variable_valor
import os
from core.firmar_documentos import firmar, firmarmasivo, obtener_posicion_y, obtener_posicion_x_y
from core.firmar_documentos_ec import JavaFirmaEc
import io
import time
import xlsxwriter
from django.core.files import File as DjangoFile
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdfsavecontratomae
import shutil
from sagest.funciones import encrypt_id
from core.firmar_documentos_ec_descentralizada import qrImgFirma
import random
from sagest.funciones import dominio_sistema_base
from decimal import Decimal
from typing import Any, Hashable, Iterable, Optional
import json
from secretaria.models import ESTADO_SOLICITUD
from PyPDF2 import PdfFileReader, PdfFileWriter
from django.core.files.base import ContentFile
from pdfminer.high_level import extract_text

def nombre_carrera_pos(carrera):
    nombre = f'{carrera.nombre} MODALIDAD {carrera.get_modalidad_display()}'
    if carrera.mencion:
        nombre = f'{carrera.nombre} CON MENCIÓN EN {carrera.mencion} MODALIDAD {carrera.get_modalidad_display()}'
    return nombre

def nombre_carrera_pos2(carrera):
    nombre = f'{carrera.nombre}'
    if carrera.mencion:
        nombre = f'{carrera.nombre} CON MENCIÓN EN {carrera.mencion}'
    return nombre

def generar_codigo(secuenciai, alias):
    secuenciai.secuencia += 1
    secuenciai.save()

    id = secuenciai.secuencia
    if len(str(id)) == 1:
        id = f"0{id}"
    codigo = f"{id}-{alias}-{secuenciai.anioejercicio}"
    return codigo

def secuencia_informehomologacion(request, anio):
    anioe = AnioEjercicio.objects.get(anioejercicio=anio)
    if not SecuenciaInformeHomologacion.objects.filter(anioejercicio=anioe).exists():
        secuencia = SecuenciaInformeHomologacion(anioejercicio=anioe)
        secuencia.save(request)
        return secuencia
    else:
        return SecuenciaInformeHomologacion.objects.filter(anioejercicio=anioe)[0]

def buscar_dicc(it: Iterable[dict], clave: Hashable, valor: Any) -> Optional[dict]:
    for dicc in it:
        if dicc[clave] == valor:
            return dicc
    return None

def is_blank_page(page, pdf_file, page_number):
    try:
        """
        Verifica si una página es en blanco comparando el contenido de texto.
        """
        pdf_buffer = io.BytesIO()
        writer = PdfFileWriter()
        writer.addPage(page)
        writer.write(pdf_buffer)
        pdf_buffer.seek(0)

        # Extraer el texto de la página en formato de string
        text = extract_text(pdf_buffer, page_numbers=[page_number])

        return text.strip() == ""
    except Exception as ex:
        pass

def remove_last_blank_page(input_pdf):
    try:
        # Leer el PDF
        reader = PdfFileReader(input_pdf)
        writer = PdfFileWriter()

        # Iterar sobre todas las páginas excepto la última si es en blanco
        total_pages = len(reader.pages)
        for i in range(total_pages):
            page = reader.pages[i]
            if i == total_pages - 1 and is_blank_page(page, input_pdf, i):
                continue  # Saltar la última página si está en blanco
            writer.addPage(page)

        # Guardar el nuevo PDF en un buffer
        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        output_buffer.seek(0)

        return output_buffer
    except Exception as ex:
        pass

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    miscarreras = persona.mis_carreras()
    data['DOMINIO_DEL_SISTEMA'] = dominio_sistema = dominio_sistema_base(request)

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'delete':
            try:
                eSolicitud = delete = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))
                if not eSolicitud.puede_eliminar():
                    raise NameError(u"Solicitud se esta utilizando")
                eRubros = Rubro.objects.filter(solicitud=eSolicitud, status=True)
                historial = False
                observacion = ''
                if eRubros.values("id").exists():
                    eRubro = eRubros.first()
                    if not eRubro.tiene_pagos():
                        #eSolicitud.delete()
                        #eSolicitud.anular_solicitud()
                        eRubro.delete()
                        observacion = u'Elimino solicitud'
                        historial = True
                        log(u'Eliminó solicitud de secretaría: %s' % delete, request, "del")
                    else:
                        observacion= u'Solicitud cuenta con pagos realizados'
                        historial = True

                if historial:
                    eSolicitud.estado = 8
                    eSolicitud.en_proceso = False
                    eSolicitud.save(request)
                    log(u'Eliminó solicitud de secretaría: %s' % delete, request, "del")
                    eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                             observacion=observacion,
                                                             fecha=datetime.now().date(),
                                                             hora=datetime.now().time(),
                                                             estado=eSolicitud.estado,
                                                             responsable=eSolicitud.perfil.persona,
                                                             )
                    eHistorialSolicitud.save(request)
                return JsonResponse({"result": 'ok', "mensaje": u"Solicitud eliminada correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        if action == 'validarfirmaec':
            try:
                eSolicitud = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))

                eSolicitud.firmadoec = True
                eSolicitud.save(request)
                observacion = 'Archivo de solicitud de homologación interna validado correctamente.'
                log(u'Validó archivo de solicitud de homologación: %s' % eSolicitud, request, "del")

                eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                         observacion=observacion,
                                                         fecha=datetime.now().date(),
                                                         hora=datetime.now().time(),
                                                         estado=eSolicitud.estado,
                                                         archivo=eSolicitud.archivo_respuesta,
                                                         responsable=persona
                                                         )
                eHistorialSolicitud.save(request)

                titulo = "SOLICITUD DE HOMOLOGACIÓN INTERNA VALIDADA"

                cuerpo = f"Se informa al coordinador del programa de {eSolicitud.inscripcioncohorte.cohortes.maestriaadmision.carrera} que el archivo de solicitude homologación interna del solicitante {eSolicitud.perfil.persona} ha sido validado por la encargada de Admisión Posgrado. Por favor, realizar el proceso respectivo (Informe, Ficha de homologación)."

                notificacion2(titulo, cuerpo, eSolicitud.inscripcioncohorte.cohortes.coordinador, None,
                              '/adm_secretaria?action=versolicitudes&id=' + str(eSolicitud.servicio.categoria.id) + '&ids=0&s=' + str(eSolicitud.codigo),
                              eSolicitud.inscripcioncohorte.cohortes.coordinador.pk, 1, 'sga',
                              eSolicitud.inscripcioncohorte.cohortes.coordinador)

                titulo = 'ARCHIVO DE HOMOLOGACIÓN VALIDADO'
                cuerpo2 = f"Saludos cordiales, se comunica al solicitante {eSolicitud.perfil.persona} que su archivo de solicitud de homologación interna ha validado por el personal de Admisión Posgrado."

                notificacion4(titulo, cuerpo2, eSolicitud.perfil.persona, None, '/alu_secretaria/service/asignaturashomologa', eSolicitud.pk, 1, 'SIE', eSolicitud, eSolicitud.perfil)

                return JsonResponse({"result": 'ok', "mensaje": u"Archivo de solicitud de homologación interna validado correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        if action == 'rechazarfirmaec':
            try:
                eSolicitud = Solicitud.objects.get(pk=int(request.POST['id']))

                observacionf = request.POST['observacion']

                eSolicitud.firmadoec = False
                eSolicitud.estado = 7
                eSolicitud.save(request)
                observacion = f'Su archivo de solicitud de homologación ha sido rechazado. - {observacionf}.'

                log(u'Rechazó archivo de solicitud de homologación: %s' % eSolicitud, request, "edit")

                if not HistorialSolicitud.objects.filter(status=True, solicitud=eSolicitud, estado=7):
                    eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                             observacion=observacion,
                                                             fecha=datetime.now().date(),
                                                             hora=datetime.now().time(),
                                                             estado=eSolicitud.estado,
                                                             archivo=eSolicitud.archivo_respuesta,
                                                             responsable=persona)
                    eHistorialSolicitud.save(request)

                    titulo = 'ARCHIVO DE HOMOLOGACIÓN RECHAZADO'
                    cuerpo2 = f"Saludos cordiales, se comunica al solicitante {eSolicitud.perfil.persona} que su archivo de solicitud homologación interna ha sido rechazado con la siguiente observación {observacionf}. Por favor, subir nuevamente el archivo o en su defecto firmarlo desde el sistema."

                    notificacion4(titulo, cuerpo2, eSolicitud.perfil.persona, None, '/alu_secretaria/service/asignaturashomologa', eSolicitud.pk, 1, 'SIE', eSolicitud, eSolicitud.perfil)
                else:
                    histo = HistorialSolicitud.objects.filter(status=True, solicitud=eSolicitud, estado=7).first()
                    histo.fecha = datetime.now().date()
                    histo.hora = datetime.now().time()
                    histo.observacion = observacion
                    histo.archivo = eSolicitud.archivo_respuesta
                    histo.save(request)

                return JsonResponse({"result": False, 'mensaje': 'Solicitud Rechazada'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        if action == 'seleccionarcarreraho':
            try:
                eSolicitud = Solicitud.objects.get(pk=int(request.POST['id']))
                carrera = Carrera.objects.get(pk=int(request.POST['carrera']))

                nombre_carrera = carrera.nombre
                if carrera.mencion:
                    nombre_carrera = f'{carrera.nombre} CON MENCIÓN EN {carrera.mencion}'

                eSolicitud.carrera_homologada = carrera
                eSolicitud.save(request)

                eSolicitudAsignaturas = SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud).distinct()

                for eSolicitudAsignatura in eSolicitudAsignaturas:
                    if eSolicitud.solicitud_asignatura_record(eSolicitudAsignatura.asignaturamalla) is not None:
                        eSolicitudAsignatura.record = eSolicitud.solicitud_asignatura_record(eSolicitudAsignatura.asignaturamalla)
                        eSolicitudAsignatura.save()

                inscrito = Inscripcion.objects.filter(status=True, carrera=eSolicitud.perfil.inscripcion.carrera, persona=eSolicitud.perfil.persona).first()
                malla = InscripcionMalla.objects.filter(status=True, inscripcion=inscrito).first().malla
                # eNoseleccionadas = AsignaturaMalla.objects.filter(status=True, malla=malla).values_list('asignatura__id', flat=True).exclude(id__in=eSolicitudAsignaturas.values_list('asignaturamalla__id', flat=True))
                eNoseleccionadas = AsignaturaMalla.objects.filter(status=True, malla=malla).exclude(id__in=eSolicitudAsignaturas.values_list('asignaturamalla__id', flat=True))

                for eAsignaturamalla in eNoseleccionadas:
                    if eSolicitud.solicitud_asignatura_record(eAsignaturamalla) is not None:
                        if not SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud, asignaturamalla=eAsignaturamalla):
                            soli = SolicitudAsignatura(solicitud=eSolicitud,
                                                       asignaturamalla=eAsignaturamalla,
                                                       estado=4,
                                                       record=eSolicitud.solicitud_asignatura_record(eAsignaturamalla))
                            soli.save(request)

                log(u'Seleccionó carrera comparativa: %s' % eSolicitud, request, "edit")

                eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                         observacion=f'Seleccionó como carrera comparativa: {nombre_carrera}',
                                                         fecha=datetime.now().date(),
                                                         hora=datetime.now().time(),
                                                         estado=eSolicitud.estado,
                                                         # archivo=eSolicitud.archivo_respuesta,
                                                         responsable=persona)
                eHistorialSolicitud.save(request)
                return JsonResponse({"result": False, 'mensaje': 'Solicitud Rechazada'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        if action == 'deleteformat':
            try:
                eFormat = FormatoCertificado.objects.get(pk=int(request.POST['id']))
                eFormat.status = False
                eFormat.save(request)
                log(u'Eliminó el formato de certificado: %s' % eFormat, request, "del")
                return JsonResponse({"result": 'ok', "mensaje": u"Solicitud eliminada correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        if action == 'deleteactividad':
            try:
                eActividad = ActividadCronogramaTitulacion.objects.get(pk=int(request.POST['id']))
                eActividad.status = False
                eActividad.save(request)
                log(u'Eliminó el actividad de cronograma de titulación: %s' % eActividad, request, "del")
                return JsonResponse({"result": 'ok', "mensaje": u"Solicitud eliminada correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        if action == 'deleteactividaddetalle':
            try:
                eActividad = DetalleActividadCronogramaTitulacion.objects.get(pk=int(request.POST['id']))
                eActividad.status = False
                eActividad.save(request)
                log(u'Eliminó el actividad de cronograma de titulación del maestrante: %s' % eActividad.solicitud, request, "del")
                return JsonResponse({"result": 'ok', "mensaje": u"Solicitud eliminada correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        if action == 'procesarCertificado':
            try:
                eSolicitud = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))
                eSolicitud = eSolicitud.generar_certificado(persona)
                return JsonResponse({"result": 'ok', "mensaje": u"Certificado generaddo correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al generar certificado: {ex.__str__()}"})

        if action == 'limpiarhojascertificado':
            try:
                eSolicitud = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))

                pdf_buffer = remove_last_blank_page(eSolicitud.archivo_respuesta.path)

                # Crear un archivo Django ContentFile
                pdf_file = ContentFile(pdf_buffer.read(), 'nuevo_documento.pdf')

                # Asignar el archivo al campo en el modelo y guardar la instancia
                eSolicitud.archivo_respuesta.save('nuevo_documento.pdf', pdf_file)
                eSolicitud.estado = 22
                eSolicitud.save()
                return JsonResponse({"result": 'ok', "mensaje": u"Certificado actualizado correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al generar certificado: {ex.__str__()}"})

        elif action == 'addentrega':
            try:
                f = EntregaCertificadoForm(request.POST)
                if f.is_valid():
                    solicitud = Solicitud.objects.get(pk=int(request.POST['id']))
                    solicitud.estado = 2
                    solicitud.save(request)

                    eHistorialSolicitud = HistorialSolicitud(solicitud=solicitud,
                                                             observacion=f.cleaned_data['observacion'],
                                                             fecha=datetime.now().date(),
                                                             hora=datetime.now().time(),
                                                             estado=solicitud.estado,
                                                             responsable=persona)
                    eHistorialSolicitud.save(request)
                    log(u'Entregó certificado físico: %s' % solicitud, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'marcaratendido':
            try:
                solicitud = Solicitud.objects.get(status=True, pk=int(encrypt(request.POST['id'])))
                # solicitud.atendido = True
                # solicitud.save(request)

                fechaasi = datetime.now().date()
                horaasi = str(datetime.now().time().strftime('%H:%M'))

                eHistorialSolicitud = HistorialSolicitud(solicitud=solicitud,
                                                         observacion= f"Está siendo atendido por {persona}",
                                                         fecha=fechaasi,
                                                         hora=horaasi,
                                                         estado=solicitud.estado,
                                                         responsable=persona,
                                                         atendido=True)
                eHistorialSolicitud.save(request)
                log(u'Atendió las solicitud del maestrante: %s' % solicitud.perfil.persona, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'aprobarrechazar':
            try:
                solicitud = Solicitud.objects.get(status=True, pk=int(request.POST['id']))
                director = ''

                if 'DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                    director = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN'
                if 'DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                    director = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD'
                if 'DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                    director = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO'

                f = AprobarRechazarInformePertinenciaForm(request.POST)
                if f.is_valid():
                    if int(f.cleaned_data['estado']) == 1:
                        solicitud.estado = 12
                        solicitud.save(request)
                    else:
                        solicitud.estado = 13
                        solicitud.save(request)

                    fechaasi = datetime.now().date()
                    horaasi = str(datetime.now().time().strftime('%H:%M'))

                    eHistorialSolicitud = HistorialSolicitud(solicitud=solicitud,
                                                             observacion=f.cleaned_data['observacion'],
                                                             fecha=fechaasi,
                                                             hora=horaasi,
                                                             estado=solicitud.estado,
                                                             responsable=persona,
                                                             archivo = solicitud.respaldo if solicitud.respaldo else '',
                                                             atendido=True)
                    eHistorialSolicitud.save(request)

                    secretarias = Persona.objects.filter(id__in=variable_valor('PERSONAL_SECRETARIA'), status=True)

                    coordinadores = ContratoDip.objects.filter(status=True, cargo__nombre__icontains='COORDINADOR', contratocarrera__carrera=solicitud.perfil.inscripcion.carrera, fechainicio__lte=datetime.now().date(), fechafin__gte=datetime.now().date()).exclude(persona=persona)

                    if 'clave' in request.POST and request.POST['clave'] == 'homolog':
                        if int(f.cleaned_data['estado']) == 1:
                            titulo = 'INFORME TÉCNICO DE PERTINENCIA APROBADO'
                            cuerpo = f'Saludos cordiales, se comunica al solicitante {solicitud.perfil.persona} que su informe técnico de pertinencia ha sido APROBADO por el {director}. Se le comunicará en estos días las asignaturas favorables para el proceso de homologación junto con la opción pra confirmar la generación del rubro.'

                            notificacion4(titulo, cuerpo, solicitud.perfil.persona, None, '/alu_secretaria/service/asignaturashomologa', solicitud.pk, 1, 'SIE', solicitud, solicitud.perfil)

                        if int(f.cleaned_data['estado']) == 1:
                            titulo = "INFORME TÉCNICO DE PERTINENCIA APROBADO"
                            cuerpo = f'Se informa al coordinador del programa de {solicitud.perfil.inscripcion.carrera} que el informe técnico de pertinencia del solicitante {solicitud.perfil.persona}  ha sido aprobado por el {director}.'
                        else:
                            titulo = "INFORME TÉCNICO DE PERTINENCIA RECHAZADO"
                            cuerpo = f'Se informa al coordinador del programa de {solicitud.perfil.inscripcion.carrera} que el informe técnico de pertinencia del solicitante {solicitud.perfil.persona}  ha sido rechazado por el {director}.'

                        coordinador = solicitud.inscripcioncohorte.cohortes.coordinador
                        notificacion2(titulo, cuerpo, coordinador, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.codigo), coordinador.id, 1, 'sga', coordinador)
                    else:
                        if int(f.cleaned_data['estado']) == 1:
                            titulo = 'INFORME TÉCNICO DE PERTINENCIA APROBADO'
                            cuerpo = 'Saludos cordiales, se comunica al maestrante ' + str(solicitud.perfil.persona) + ' que su informe técnico de pertinencia ha sido APROBADO por el ' + director +', por esta razón se ha habilitado la opción en la ventana de Mis pedidos representada mediante un ícono de dólar, la cual confirmará la creación del rubro para ingresar al proceso de titulación extraordinaria.'

                            notificacion4(titulo, cuerpo, solicitud.perfil.persona, None, '/alu_secretaria/mis_pedidos', solicitud.pk, 1, 'SIE', solicitud, solicitud.perfil)
                        else:
                            titulo = 'INFORME TÉCNICO DE PERTINENCIA RECHAZADO'
                            cuerpo = 'Saludos cordiales, se comunica al maestrante ' + str(solicitud.perfil.persona) + ' que su informe técnico de pertinencia ha sido RECHAZADO por el ' + director + '. Agradecemos su compresión.'

                            notificacion4(titulo, cuerpo, solicitud.perfil.persona, None, '/alu_secretaria/mis_pedidos', solicitud.pk, 1, 'SIE',
                                          solicitud, solicitud.perfil)

                        for secretaria in secretarias:
                            if int(f.cleaned_data['estado']) == 1:
                                titulo = "INFORME TÉCNICO DE PERTINENCIA APROBADO"
                                cuerpo = 'Se informa a todo el personal de Secretaría Técnica Posgrado que el informe técnico de pertinencia del maestrante ' + str(solicitud.perfil.persona) + ' ha sido aprobado por el ' + director +'.'
                            else:
                                titulo = "INFORME TÉCNICO DE PERTINENCIA RECHAZADO"
                                cuerpo = 'Se informa a todo el personal de Secretaría Técnica Posgrado que el informe técnico de pertinencia del maestrante ' + str(solicitud.perfil.persona) + ' ha sido rechazado por el ' + director +'.'

                            notificacion2(titulo,
                                          cuerpo, secretaria, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.codigo),
                                          secretaria.pk, 1, 'sga', secretaria)

                        for coordinador in coordinadores:
                            if int(f.cleaned_data['estado']) == 1:
                                titulo = "INFORME TÉCNICO DE PERTINENCIA APROBADO"
                                cuerpo = 'Se informa a todo el personal de Secretaría Técnica Posgrado que el informe técnico de pertinencia del maestrante ' + str(solicitud.perfil.persona) + ' ha sido aprobado por el ' + director +'.'
                            else:
                                titulo = "INFORME TÉCNICO DE PERTINENCIA RECHAZADO"
                                cuerpo = 'Se informa a todo el personal de Secretaría Técnica Posgrado que el informe técnico de pertinencia del maestrante ' + str(solicitud.perfil.persona) + ' ha sido rechzado por el ' + director +'.'

                            notificacion2(titulo,
                                          cuerpo, coordinador.persona, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.codigo),
                                          coordinador.persona.pk, 1, 'sga', coordinador.persona)

                    log(u'Aprobó el informe técnico de pertinencia del maestrante: %s' % solicitud.perfil.persona, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Aprobación Existosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'revisarinforme':
            try:
                solicitud = Solicitud.objects.get(status=True, pk=int(request.POST['id']))

                f = AprobarRechazarInformePertinenciaForm(request.POST)
                if f.is_valid():
                    if int(f.cleaned_data['estado']) == 1:
                        solicitud.estado = 17
                        solicitud.save(request)
                    else:
                        solicitud.estado = 13
                        solicitud.save(request)

                    fechaasi = datetime.now().date()
                    horaasi = str(datetime.now().time().strftime('%H:%M'))

                    eHistorialSolicitud = HistorialSolicitud(solicitud=solicitud,
                                                             observacion=f.cleaned_data['observacion'],
                                                             fecha=fechaasi,
                                                             hora=horaasi,
                                                             estado=solicitud.estado,
                                                             responsable=persona)
                    eHistorialSolicitud.save(request)

                    secretarias = Persona.objects.filter(id__in=variable_valor('PERSONAL_SECRETARIA'), status=True)

                    coordinadores = ContratoDip.objects.filter(status=True, cargo__nombre__icontains='COORDINADOR', contratocarrera__carrera=solicitud.perfil.inscripcion.carrera, fechainicio__lte=datetime.now().date(), fechafin__gte=datetime.now().date()).exclude(persona=persona)

                    if int(f.cleaned_data['estado']) == 1:
                        if solicitud.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN').values_list('carrera_id', flat=True):
                            cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN'
                            dir = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
                            titulo = "REVISIÓN DE INFORME TÉCNICO DE PERTINENCIA"
                            cuerpo = 'Se informa a ' + str(dir) + ' que la experta de Secretaría Técnica de Posgrado ha aprobado el informe técnico de pertinencia del maestrante ' + str(solicitud.perfil.inscripcion.persona) + '. Por favor, realizar la respectiva revisión y la posterior aprobación o rechazo para continuar con el proceso.'

                            notificacion2(titulo, cuerpo, dir, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.codigo),
                                          dir.pk, 1, 'sga', dir)
                        elif solicitud.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD').values_list('carrera_id', flat=True):
                            cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD'
                            dir = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
                            titulo = "REVISIÓN DE INFORME TÉCNICO DE PERTINENCIA"
                            cuerpo = 'Se informa a ' + str(dir) + ' que la experta de Secretaría Técnica de Posgrado ha aprobado el informe técnico de pertinencia del maestrante ' + str(solicitud.perfil.inscripcion.persona) + '. Por favor, realizar la respectiva revisión y la posterior aprobación o rechazo para continuar con el proceso.'

                            notificacion2(titulo, cuerpo, dir, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.codigo),
                                          dir.pk, 1, 'sga', dir)
                        elif solicitud.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO').values_list('carrera_id', flat=True):
                            cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO'
                            dir = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
                            titulo = "REVISIÓN DE INFORME TÉCNICO DE PERTINENCIA"
                            cuerpo = 'Se informa a ' + str(dir) + ' que la experta de Secretaría Técnica de Posgrado ha aprobado el informe técnico de pertinencia del maestrante ' + str(solicitud.perfil.inscripcion.persona) + '. Por favor, realizar la respectiva revisión y la posterior aprobación o rechazo para continuar con el proceso.'

                            notificacion2(titulo, cuerpo, dir, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.codigo),
                                          dir.pk, 1, 'sga', dir)

                    for secretaria in secretarias:
                        if int(f.cleaned_data['estado']) == 1:
                            titulo = "INFORME TÉCNICO DE PERTINENCIA APROBADO"
                            cuerpo = 'Se informa a todo el personal de Secretaría Técnica Posgrado que el informe técnico de pertinencia del maestrante ' + str(solicitud.perfil.persona) + ' ha sido aprobado por la EXPERTA de Secretaría Técnica de Posgrado'
                        else:
                            titulo = "INFORME TÉCNICO DE PERTINENCIA RECHAZADO"
                            cuerpo = 'Se informa a todo el personal de Secretaría Técnica Posgrado que el informe técnico de pertinencia del maestrante ' + str(solicitud.perfil.persona) + ' ha sido rechazado por la EXPERTA de Secretaría Técnica de Posgrado'

                        notificacion2(titulo,
                                      cuerpo, secretaria, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.perfil.persona.cedula),
                                      secretaria.pk, 1, 'sga', secretaria)

                    for coordinador in coordinadores:
                        if int(f.cleaned_data['estado']) == 1:
                            titulo = "INFORME TÉCNICO DE PERTINENCIA APROBADO"
                            cuerpo = 'Se informa a todo el personal de Secretaría Técnica Posgrado que el informe técnico de pertinencia del maestrante ' + str(solicitud.perfil.persona) + ' ha sido aprobado por la EXPERTA de Secretaría Técnica de Posgrado'
                        else:
                            titulo = "INFORME TÉCNICO DE PERTINENCIA RECHAZADO"
                            cuerpo = 'Se informa a todo el personal de Secretaría Técnica Posgrado que el informe técnico de pertinencia del maestrante ' + str(solicitud.perfil.persona) + ' ha sido rechazado por la EXPERTA de Secretaría Técnica de Posgrado'

                        notificacion2(titulo,
                                      cuerpo, coordinador.persona, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.perfil.persona.cedula),
                                      coordinador.persona.pk, 1, 'sga', coordinador.persona)

                    log(u'Revisó el informe técnico de pertinencia del maestrante: %s' % solicitud.perfil.persona, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Aprobación Existosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'revisarcronograma':
            try:
                solicitud = Solicitud.objects.get(status=True, pk=int(request.POST['id']))

                f = AprobarRechazarInformePertinenciaForm(request.POST)
                if f.is_valid():
                    if int(f.cleaned_data['estado']) == 1:
                        solicitud.estado = 18
                        solicitud.save(request)
                    else:
                        solicitud.estado = 21
                        solicitud.save(request)

                    fechaasi = datetime.now().date()
                    horaasi = str(datetime.now().time().strftime('%H:%M'))

                    eHistorialSolicitud = HistorialSolicitud(solicitud=solicitud,
                                                             observacion=f.cleaned_data['observacion'],
                                                             fecha=fechaasi,
                                                             hora=horaasi,
                                                             estado=solicitud.estado,
                                                             responsable=persona)
                    eHistorialSolicitud.save(request)

                    secretarias = Persona.objects.filter(id__in=variable_valor('PERSONAL_SECRETARIA'), status=True)

                    if int(f.cleaned_data['estado']) == 1:
                        if solicitud.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN').values_list('carrera_id', flat=True):
                            cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN'
                            dir = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
                            titulo = "REVISIÓN DE CRONOGRAMA DE TITULACIÓN EXTRAORDINARIA"
                            cuerpo = 'Se informa a ' + str(dir) + ' que la experta de Secretaría Técnica de Posgrado ha aprobado el cronograma de titulación extraordinaria del maestrante ' + str(solicitud.perfil.inscripcion.persona) + '. Por favor, realizar la respectiva revisión y la posterior aprobación o rechazo para continuar con el proceso.'

                            notificacion2(titulo, cuerpo, dir, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.codigo),
                                          dir.pk, 1, 'sga', dir)
                        elif solicitud.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD').values_list('carrera_id', flat=True):
                            cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD'
                            dir = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
                            titulo = "REVISIÓN DE CRONOGRAMA DE TITULACIÓN EXTRAORDINARIA"
                            cuerpo = 'Se informa a ' + str(dir) + ' que la experta de Secretaría Técnica de Posgrado ha aprobado el cronograma de titulación extraordinaria del maestrante ' + str(solicitud.perfil.inscripcion.persona) + '. Por favor, realizar la respectiva revisión y la posterior aprobación o rechazo para continuar con el proceso.'

                            notificacion2(titulo, cuerpo, dir, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.codigo),
                                          dir.pk, 1, 'sga', dir)
                        elif solicitud.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO').values_list('carrera_id', flat=True):
                            cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO'
                            dir = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
                            titulo = "REVISIÓN DE CRONOGRAMA DE TITULACIÓN EXTRAORDINARIA"
                            cuerpo = 'Se informa a ' + str(dir) + ' que la experta de Secretaría Técnica de Posgrado ha aprobado el cronograma de titulación extraordinaria del maestrante ' + str(solicitud.perfil.inscripcion.persona) + '. Por favor, realizar la respectiva revisión y la posterior aprobación o rechazo para continuar con el proceso.'

                            notificacion2(titulo, cuerpo, dir, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.codigo),
                                          dir.pk, 1, 'sga', dir)

                    for secretaria in secretarias:
                        if int(f.cleaned_data['estado']) == 1:
                            titulo = "CRONOGRAMA DE TITULACIÓN EX. APROBADO"
                            cuerpo = 'Se informa a todo el personal de Secretaría Técnica Posgrado que el cronograma de titulación extraordinaria del maestrante ' + str(solicitud.perfil.persona) + ' ha sido aprobado por la EXPERTA de Secretaría Técnica de Posgrado'
                        else:
                            titulo = "CRONOGRAMA DE TITULACIÓN EX. RECHAZADO"
                            cuerpo = 'Se informa a todo el personal de Secretaría Técnica Posgrado que el cronograma de titulación extraordinaria del maestrante ' + str(solicitud.perfil.persona) + ' ha sido rechazado por la EXPERTA de Secretaría Técnica de Posgrado'

                        notificacion2(titulo,
                                      cuerpo, secretaria, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.codigo),
                                      secretaria.pk, 1, 'sga', secretaria)

                    log(u'Revisó el cronograma de titulación extraordinaria del maestrante: %s' % solicitud.perfil.persona, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Aprobación Existosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'aprobarrechazarcronograma':
            try:
                solicitud = Solicitud.objects.get(status=True, pk=int(request.POST['id']))

                f = AprobarRechazarInformePertinenciaForm(request.POST)
                if f.is_valid():
                    if int(f.cleaned_data['estado']) == 1:
                        solicitud.estado = 20
                        solicitud.save(request)
                    else:
                        solicitud.estado = 21
                        solicitud.save(request)

                    fechaasi = datetime.now().date()
                    horaasi = str(datetime.now().time().strftime('%H:%M'))

                    eHistorialSolicitud = HistorialSolicitud(solicitud=solicitud,
                                                             observacion=f.cleaned_data['observacion'],
                                                             fecha=fechaasi,
                                                             hora=horaasi,
                                                             estado=solicitud.estado,
                                                             responsable=persona)
                    eHistorialSolicitud.save(request)

                    secretarias = Persona.objects.filter(id__in=variable_valor('PERSONAL_SECRETARIA'), status=True)

                    for secretaria in secretarias:
                        if int(f.cleaned_data['estado']) == 1:
                            titulo = "CRONOGRAMA DE TITULACIÓN EX. APROBADO"
                            cuerpo = 'Se informa a todo el personal de Secretaría Técnica Posgrado que el cronograma de titulación extraordinaria del maestrante ' + str(solicitud.perfil.persona) + ' ha sido aprobado por el Director de Escuela'
                        else:
                            titulo = "CRONOGRAMA DE TITULACIÓN EX. RECHAZADO"
                            cuerpo = 'Se informa a todo el personal de Secretaría Técnica Posgrado que el cronograma de titulación extraordinaria del maestrante ' + str(solicitud.perfil.persona) + ' ha sido rechazado por el Director de Escuela'

                        notificacion2(titulo,
                                      cuerpo, secretaria, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.codigo),
                                      secretaria.pk, 1, 'sga', secretaria)

                    log(u'Aprobó o rechazó el cronograma de titulación extraordinaria del maestrante: %s' % solicitud.perfil.persona, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Aprobación Existosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'subircertificado':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})

                f = SubirCertificadoPersonalizadoForm(request.POST, request.FILES)
                if f.is_valid():
                    solicitud = Solicitud.objects.get(pk=int(request.POST['id']))
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("resultado", newfile._name)
                        solicitud.archivo_respuesta = newfile
                        solicitud.estado = 2
                        solicitud.save(request)

                        eHistorialSolicitud = HistorialSolicitud(solicitud=solicitud,
                                                                 observacion=f.cleaned_data['observacion'],
                                                                 fecha=datetime.now().date(),
                                                                 hora=datetime.now().time(),
                                                                 estado=solicitud.estado,
                                                                 responsable=persona)
                        eHistorialSolicitud.save(request)

                        if solicitud.servicio.categoria.roles == '3':
                            send_html_mail(u"Certificado personalizado habilitado para descarga, Secretaría Técnica Posgrado.",
                                "emails/entrega_certificado_posgrado.html",
                                {'sistema': u'SGA', 'fecha': solicitud.fecha_retiro,
                                 'hora': solicitud.hora_retiro, 'solicitud': solicitud,
                                 'persona': solicitud.perfil.persona, 'lugar': solicitud.lugar_retiro},
                                solicitud.perfil.persona.lista_emails_envio(), [], [], cuenta=CUENTAS_CORREOS[34][1])
                        else:
                            send_html_mail(u"Certificado personalizado habilitado para descarga, Secretaría General.",
                                "emails/entrega_certificado_posgrado.html",
                                {'sistema': u'SGA', 'fecha': solicitud.fecha_retiro,
                                 'hora': solicitud.hora_retiro, 'solicitud': solicitud,
                                 'persona': solicitud.perfil.persona, 'lugar': solicitud.lugar_retiro},
                                solicitud.perfil.persona.lista_emails_envio(), [], [], cuenta=CUENTAS_CORREOS[35][1])
                        log(u'Subió certificado personalizado: %s' % solicitud, request, "edit")
                        return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'subirinformetecnico':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() in ['.pdf', '.doc', '.docx']:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .doc o .docx"})

                clave = None
                f = SubirInformeTecnicoPertinenciaForm(request.POST, request.FILES)
                f.sin_carrera()
                if f.is_valid():
                    solicitud = Solicitud.objects.get(pk=int(request.POST['id']))
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("informe_tecnico_pertinencia", newfile._name)

                        if request.POST['clave'] == '':
                            solicitud.archivo_respuesta = newfile
                            solicitud.estado = 11
                            solicitud.save(request)

                            eHistorialSolicitud = HistorialSolicitud(solicitud=solicitud,
                                                                     observacion=f.cleaned_data['observacion'],
                                                                     fecha=datetime.now().date(),
                                                                     hora=datetime.now().time(),
                                                                     estado=solicitud.estado,
                                                                     responsable=persona,
                                                                     archivo=solicitud.archivo_respuesta)
                            eHistorialSolicitud.save(request)
                        else:
                            solicitud.respaldo = newfile
                            solicitud.estado = 11
                            solicitud.save(request)

                            eHistorialSolicitud = HistorialSolicitud(solicitud=solicitud,
                                                                     observacion=f.cleaned_data['observacion'],
                                                                     fecha=datetime.now().date(),
                                                                     hora=datetime.now().time(),
                                                                     estado=solicitud.estado,
                                                                     responsable=persona,
                                                                     archivo=solicitud.respaldo)
                            eHistorialSolicitud.save(request)

                        if 'clave' in request.POST and request.POST['clave'] == 'homolog':
                            solicitud.notificar_escuela()
                        log(u'Subió informe técnico de pertinencia: %s' % solicitud, request, "edit")
                        return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'subircronograma':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf"})

                f = SubirCronogramaTitulacionForm(request.POST, request.FILES)
                if f.is_valid():
                    solicitud = Solicitud.objects.get(pk=int(request.POST['id']))
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("cronograma_titulacion", newfile._name)
                        solicitud.archivo_solicitud = newfile
                        solicitud.estado = 19
                        solicitud.save(request)

                        eHistorialSolicitud = HistorialSolicitud(solicitud=solicitud,
                                                                 observacion=f.cleaned_data['observacion'],
                                                                 fecha=datetime.now().date(),
                                                                 hora=datetime.now().time(),
                                                                 estado=solicitud.estado,
                                                                 responsable=persona,
                                                                 archivo=solicitud.archivo_solicitud)
                        eHistorialSolicitud.save(request)

                        experta = Persona.objects.get(status=True, pk=int(variable_valor('EXPERTA_SECRETARÍA')))

                        titulo = "REVISIÓN DE CRONOGRAMA DE TITULACIÓN EX."
                        cuerpo = 'Se informa a ' + str(experta) + ' que el personal administrativo ha subido el cronograma de titulación extraordinaria del maestrante ' + str(solicitud.perfil.inscripcion.persona) + '. Por favor, realizar la respectiva revisión y la posterior aprobación o rechazo.'

                        notificacion2(titulo, cuerpo, experta, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.codigo),
                                      experta.pk, 1, 'sga', experta)

                        # if 'notificar' in request.POST:
                        #     titulo = 'CRONOGRAMA ENTREGADO'
                        #     cuerpo = 'Saludos cordiales, se comunica al maestrante ' + str(solicitud.perfil.persona) + ' que su cronograma de titulación ha sido enviado vía correo electrónico. Al dar clic en esta notificación será redirigido al módulo de Proceso de Titulación.'
                        #
                        #     notificacion4(titulo, cuerpo, solicitud.perfil.persona, None, '/alu_secretaria/mis_pedidos', solicitud.pk, 1, 'SIE', solicitud, solicitud.perfil)
                        #
                        #     send_html_mail(
                        #         u"Cronograma de Titulación Extraordinaria, Secretaría Técnica Posgrado.",
                        #         "emails/entrega_cronograma_tit_ex.html",
                        #         {'sistema': u'SGA', 'fecha': datetime.now().date(),
                        #          'hora': datetime.now().time(), 'solicitud': solicitud,
                        #          'persona': solicitud.perfil.persona},
                        #         solicitud.perfil.persona.lista_emails_envio(), [], [solicitud.archivo_solicitud], cuenta=CUENTAS_CORREOS[34][1])
                        #
                        #     if solicitud.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN').values_list('carrera_id', flat=True):
                        #         cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN'
                        #         dir = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
                        #         titulo = "CRONOGRAMA ENTREGADO"
                        #         cuerpo = 'Se informa a ' + str(dir) + ' que el cronograma de titulación extraordinaria del maestrante ' + str(solicitud.perfil.inscripcion.persona) + ' ha sido entregado.'
                        #
                        #         notificacion2(titulo, cuerpo, dir, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.perfil.inscripcion.persona.cedula),
                        #                       dir.pk, 1, 'sga', dir)
                        #     elif solicitud.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD').values_list('carrera_id', flat=True):
                        #         cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD'
                        #         dir = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
                        #         titulo = "CRONOGRAMA ENTREGADO"
                        #         cuerpo = 'Se informa a ' + str(dir) + ' que el cronograma de titulación extraordinaria del maestrante ' + str(solicitud.perfil.inscripcion.persona) + ' ha sido entregado.'
                        #
                        #         notificacion2(titulo, cuerpo, dir, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.perfil.inscripcion.persona.cedula),
                        #                       dir.pk, 1, 'sga', dir)
                        #     elif solicitud.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO').values_list('carrera_id', flat=True):
                        #         cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO'
                        #         dir = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
                        #         titulo = "CRONOGRAMA ENTREGADO"
                        #         cuerpo = 'Se informa a ' + str(dir) + ' que el cronograma de titulación extraordinaria del maestrante ' + str(solicitud.perfil.inscripcion.persona) + ' ha sido entregado.'
                        #
                        #         notificacion2(titulo, cuerpo, dir, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.perfil.inscripcion.persona.cedula),
                        #                       dir.pk, 1, 'sga', dir)
                        log(u'Subió informe técnico de pertinencia: %s' % solicitud, request, "edit")
                        return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'notificarcronograma':
            try:
                f = NotificarCronogramaTitulacionForm(request.POST)
                if f.is_valid():
                    solicitud = Solicitud.objects.get(pk=int(request.POST['id']))
                    solicitud.estado = 16
                    solicitud.save(request)

                    eHistorialSolicitud = HistorialSolicitud(solicitud=solicitud,
                                                             observacion=f.cleaned_data['observacion'],
                                                             fecha=datetime.now().date(),
                                                             hora=datetime.now().time(),
                                                             estado=solicitud.estado,
                                                             responsable=persona,
                                                             archivo=solicitud.archivo_solicitud,
                                                             urldrive=f.cleaned_data['url'])
                    eHistorialSolicitud.save(request)

                    titulo = 'CRONOGRAMA ENTREGADO'
                    cuerpo = 'Saludos cordiales, se comunica al maestrante ' + str(solicitud.perfil.persona) + ' que su cronograma de titulación extraordinaria ha sido subido al SGA en el módulo Servicios de secretaría en la ventana de Mis pediddos, y también ha sido enviado vía correo electrónico. Al dar clic en esta notificación será redirigido al módulo de Proceso de Titulación.'

                    notificacion4(titulo, cuerpo, solicitud.perfil.persona, None, '/alu_tematitulacionposgrado', solicitud.pk, 1, 'SIE', solicitud, solicitud.perfil)

                    send_html_mail(
                        u"Cronograma de Titulación Extraordinaria, Secretaría Técnica Posgrado.",
                        "emails/entrega_cronograma_tit_ex.html",
                        {'sistema': u'SGA', 'fecha': datetime.now().date(),
                         'hora': datetime.now().time(), 'solicitud': solicitud,
                         'persona': solicitud.perfil.persona, 'observacion': f.cleaned_data['observacion'],
                         'url':f.cleaned_data['url']},
                        solicitud.perfil.persona.lista_emails_envio(), [], [solicitud.archivo_solicitud], cuenta=CUENTAS_CORREOS[34][1])

                    if solicitud.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN').values_list('carrera_id', flat=True):
                        cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN'
                        dir = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
                        titulo = "CRONOGRAMA ENTREGADO"
                        cuerpo = 'Se informa a ' + str(dir) + ' que el cronograma de titulación extraordinaria del maestrante ' + str(solicitud.perfil.inscripcion.persona) + ' ha sido entregado.'

                        notificacion2(titulo, cuerpo, dir, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.perfil.inscripcion.persona.cedula),
                                      dir.pk, 1, 'sga', dir)
                    elif solicitud.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD').values_list('carrera_id', flat=True):
                        cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD'
                        dir = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
                        titulo = "CRONOGRAMA ENTREGADO"
                        cuerpo = 'Se informa a ' + str(dir) + ' que el cronograma de titulación extraordinaria del maestrante ' + str(solicitud.perfil.inscripcion.persona) + ' ha sido entregado.'

                        notificacion2(titulo, cuerpo, dir, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.perfil.inscripcion.persona.cedula),
                                      dir.pk, 1, 'sga', dir)
                    elif solicitud.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO').values_list('carrera_id', flat=True):
                        cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO'
                        dir = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
                        titulo = "CRONOGRAMA ENTREGADO"
                        cuerpo = 'Se informa a ' + str(dir) + ' que el cronograma de titulación extraordinaria del maestrante ' + str(solicitud.perfil.inscripcion.persona) + ' ha sido entregado.'

                        notificacion2(titulo, cuerpo, dir, None, '/adm_secretaria?action=versolicitudes&id=' + str(solicitud.servicio.categoria.id) + '&ids=0&s=' + str(solicitud.perfil.inscripcion.persona.cedula),
                                      dir.pk, 1, 'sga', dir)
                    log(u'Notificó el cronograma de titulación extraordinaria del maestrante: %s' % solicitud, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addformato':
            try:
                lista = ''
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() in ['.doc', '.docx']:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .doc o .docx"})

                if request.POST['idc'] == '1':
                    lista = '3'
                elif request.POST['idc'] == '4':
                    lista = '2'
                elif request.POST['idc'] == '5':
                    lista = '1'

                f = SubirFormatoCertificadoForm(request.POST, request.FILES)
                if f.is_valid():
                    formato = FormatoCertificado(certificacion=f.cleaned_data['certificacion'],
                                                 tipo_origen=f.cleaned_data['tipo'],
                                                 roles=lista)
                    formato.save(request)

                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("resultado", newfile._name)
                        formato.formato = newfile
                        formato.save(request)

                        log(u'Adicionó formato de certificado: %s' % formato, request, "add")
                        return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addactividad':
            try:
                f = AdicionarActividadCronogramaForm(request.POST)
                if f.is_valid():
                    actividad = ActividadCronogramaTitulacion(nombre=f.cleaned_data['nombre'],
                                                            descripcion=f.cleaned_data['descripcion'])
                    actividad.save(request)
                    log(u'Adicionó actividad de cronograma de titulación: %s' % actividad, request, "add")
                    return JsonResponse({"result": False, 'mensaje': 'Adición Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addactividadtituex':
            try:
                solicitante = Solicitud.objects.get(status=True, pk=int(request.GET['id']))
                f = ActividadCronogramaTitulacionForm(request.POST)
                if f.is_valid():
                    if not DetalleActividadCronogramaTitulacion.objects.filter(status=True, solicitud=solicitante, actividad=f.cleaned_data['actividad']).exists():
                        if f.cleaned_data['inicio'] <= f.cleaned_data['fin']:
                            deta = DetalleActividadCronogramaTitulacion(solicitud=solicitante,
                                                                       periodo=f.cleaned_data['periodo'],
                                                                       actividad=f.cleaned_data['actividad'],
                                                                       inicio=f.cleaned_data['inicio'],
                                                                       fin=f.cleaned_data['fin'],
                                                                       observacion=f.cleaned_data['observacion'])
                            deta.save(request)
                            log(u'Adicionó actividad de cronograma de titulación del maestrante: %s' % deta.solicitud, request, "add")
                            return JsonResponse({"result": False, 'mensaje': 'Adición Exitosa'})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio debe ser menor o igual a la de fin"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Esta actividad ya ha sido ingresada"})
                        # raise NameError(u"Esta actividad ya ha sido ingresada")
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'configurarintegrantestitu':
            try:
                solicitante = Solicitud.objects.get(status=True, pk=int(request.GET['id']))
                f = IntegrantesTitulacionForm(request.POST)

                if solicitante.director_titu():
                    f.edit_director(int(request.POST['director']))

                if solicitante.coordinador_titu():
                    f.edit_coordinador(int(request.POST['coordinador']))

                if f.is_valid():
                    if not IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=solicitante, tipo=1):
                        eIntegrante = IntegrantesCronogramaTituEx(solicitud=solicitante,
                                                                  tipo=1,
                                                                  administrativo=f.cleaned_data['director'],
                                                                  cargo=f.cleaned_data['cargodir'],
                                                                  responsabilidad='Aprobado por')
                        eIntegrante.save()
                        log(u'Adicionó director de titulación extraordinaria: %s' % eIntegrante, request, "add")
                    else:
                        eIntegrante = IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=solicitante, tipo=1).first()
                        eIntegrante.administrativo = f.cleaned_data['director']
                        eIntegrante.cargo = f.cleaned_data['cargodir']
                        eIntegrante.save()
                        log(u'Actualizó director de titulación extraordinaria: %s' % eIntegrante, request, "edit")

                    if not IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=solicitante, tipo=2):
                        eIntegrante = IntegrantesCronogramaTituEx(solicitud=solicitante,
                                                                  tipo=2,
                                                                  administrativo=f.cleaned_data['coordinador'],
                                                                  cargo=f.cleaned_data['cargocor'],
                                                                  responsabilidad='Revisado por')
                        eIntegrante.save()
                        log(u'Adicionó coordinador o administrativo de titulación extraordinaria: %s' % eIntegrante, request, "add")
                    else:
                        eIntegrante = IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=solicitante, tipo=2).first()
                        eIntegrante.administrativo = f.cleaned_data['coordinador']
                        eIntegrante.cargo = f.cleaned_data['cargocor']
                        eIntegrante.save()
                        log(u'Actualizó coordinador o administrativo de titulación extraordinaria: %s' % eIntegrante, request,"edit")
                    return JsonResponse({"result": False, 'mensaje': 'Adición Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editactividad':
            try:
                actividad = ActividadCronogramaTitulacion.objects.get(pk=int(request.POST['id']))
                f = AdicionarActividadCronogramaForm(request.POST, request.FILES)
                if f.is_valid():
                    actividad.nombre = f.cleaned_data['nombre']
                    actividad.descripcion = f.cleaned_data['descripcion']
                    actividad.save(request)
                    log(u'Editó actividad de cronograma de titulación: %s' % actividad, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editactividadtituex':
            try:
                detalle = DetalleActividadCronogramaTitulacion.objects.get(pk=int(request.POST['id']))
                f = ActividadCronogramaTitulacionForm(request.POST)
                if f.is_valid():
                    if not DetalleActividadCronogramaTitulacion.objects.filter(status=True, solicitud=detalle.solicitud, actividad=f.cleaned_data['actividad']).exclude(pk=detalle.id).exists():
                        detalle.periodo = f.cleaned_data['periodo']
                        detalle.actividad = f.cleaned_data['actividad']
                        detalle.inicio = f.cleaned_data['inicio']
                        detalle.fin = f.cleaned_data['fin']
                        detalle.observacion = f.cleaned_data['observacion']
                        detalle.save(request)
                        log(u'Editó actividad de cronograma de titulación del maestrante: %s' % detalle.solicitud.perfil.inscripcion.persona, request, "edit")
                        return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Esta actividad ya ha sido ingresada"})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'pdfcronogramatituex':
            try:
                result = cronogramatituex(request.POST['id'])
                return JsonResponse({"result": "ok", 'url': result})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'firmarcertificadomasivo':
            try:
                firma = request.FILES["firma"]
                passfirma = request.POST['palabraclave']
                certificadoselect = request.POST['ids'].split(',')
                bandera = False
                p12 = None
                certificado = None
                listainscripcion = []
                nombresmae = ''
                conterrornombre = 0
                conteoerror = 0
                bytes_certificado = firma.read()
                extension_certificado = os.path.splitext(firma.name)[1][1:]
                palabras = FirmaCertificadoSecretaria.objects.get(status=True, activo=True).nombrefirma
                # palabras = 'Abg. Stefania Velasco Neira, Mgtr.'

                secretaria = Persona.objects.get(pk=variable_valor('SECRETARIA_G'))
                for certi in certificadoselect:
                    certificado = Solicitud.objects.get(pk=certi)
                    if not certificado.respaldo:
                        certificado.respaldo = certificado.archivo_respuesta
                        certificado.save(request)
                    documento_a_firmar = certificado.archivo_respuesta
                    # obtener la posicion xy de la firma del doctor en el pdf
                    y, numpaginafirma = obtener_posicion_y(documento_a_firmar.url, palabras)
                    # FIN obtener la posicion y
                    if y:
                        datau = JavaFirmaEc(
                            archivo_a_firmar=documento_a_firmar, archivo_certificado=bytes_certificado,
                            extension_certificado=extension_certificado,
                            password_certificado=passfirma,
                            page=numpaginafirma, reason='Certificado firmado', lx=260, ly=y)
                        if datau:
                            if datau.datos_del_certificado['cedula'] == secretaria.cedula:
                                generar_archivo_firmado = io.BytesIO()
                                generar_archivo_firmado.write(datau.sign_and_get_content_bytes())
                                generar_archivo_firmado.seek(0)
                                extension = documento_a_firmar.name.split('.')
                                tam = len(extension)
                                exte = extension[tam - 1]
                                nombrefile_ = remover_caracteres_tildes_unicode(
                                    remover_caracteres_especiales_unicode(documento_a_firmar.name)).replace('-', '_').replace('.pdf', '')
                                _name = 'rpt_certificado' + str(certificado.id)
                                file_obj = DjangoFile(generar_archivo_firmado, name=f"{remover_caracteres_especiales_unicode(_name)}_firmado.pdf")
                                certificado.archivo_respuesta = file_obj
                                certificado.certificadofirmado = True
                                certificado.estado = 2
                                certificado.save(request)
                                detalleevidencia = HistorialSolicitud(solicitud_id=certificado.id)
                                detalleevidencia.save(request)
                                detalleevidencia.observacion = 'Certificado firmado'
                                detalleevidencia.responsable = persona
                                detalleevidencia.estado = 2
                                detalleevidencia.fecha = datetime.now().date()
                                detalleevidencia.hora = datetime.now().time()
                                detalleevidencia.save(request)
                                log(u'Masivo Firmó Documento: {}'.format(nombrefile_), request, "add")
                                listainscripcion.append(certificado.perfil.inscripcion.id)
                                nombresmae += '%s, ' % certificado.perfil.inscripcion.persona

                                integrante = Persona.objects.get(status=True, pk=certificado.perfil.inscripcion.persona.id)

                                asunto = u"CERTIFICADO FIRMADO"
                                cuerpo = f'Se le comunica que su certificado ha sido firmado y entregado correctamente. Clic aqu[i, para ser redirigido a la venta mis pedidos.'

                                notificacion3(asunto,
                                              cuerpo, certificado.perfil.persona, None,
                                              '/alu_secretaria/mis_pedidos',
                                              certificado.pk, 1, 'SIE', certificado, certificado.perfil, request)
                            else:
                                return JsonResponse({"result": "bad", "mensaje": f"La firma ingresada no pertenece a la Secretaria General {secretaria} con número de cédula {secretaria.cedula}."})
                        else:
                            conteoerror += 1
                            if certificado.certificadofirmado:
                                certificado.certificadofirmado = False
                            certificado.estado = 7
                            certificado.save(request)

                            detalleevidencia = HistorialSolicitud(solicitud_id=certificado.id)
                            detalleevidencia.save(request)
                            detalleevidencia.observacion = 'Certificado con inconsistencia en la firma'
                            detalleevidencia.responsable = persona
                            detalleevidencia.estado = 7
                            detalleevidencia.fecha = datetime.now().date()
                            detalleevidencia.hora = datetime.now().time()
                            detalleevidencia.save(request)
                    else:
                        conteoerror += 1
                        conterrornombre += 1
                        if certificado.certificadofirmado:
                            certificado.certificadofirmado = False
                        certificado.estado = 7
                        certificado.save(request)

                        detalleevidencia = HistorialSolicitud(solicitud_id=certificado.id)
                        detalleevidencia.save(request)
                        detalleevidencia.observacion = 'El nombre de la secretaria general en la firma no es el correcto.'
                        detalleevidencia.responsable = persona
                        detalleevidencia.estado = 7
                        detalleevidencia.fecha = datetime.now().date()
                        detalleevidencia.hora = datetime.now().time()
                        detalleevidencia.save(request)
                    time.sleep(2)
                if listainscripcion:
                    cuerpo = ('Documentos firmados con éxito: %s' % nombresmae)
                    notificacion('Firma electrónica SGA', cuerpo, persona, None,
                                 '/adm_secretaria?action=listadoafirmar&id=1', None, 1, 'sga', certificado,
                                 request)
                    if conteoerror > 0:
                        messages.success(request, f'Documentos firmados con éxito. %s' % (
                            'Existieron %s contratos con inconsistencia que no fueron firmados. Enviados a comercialización: %s' % (
                            conteoerror, conterrornombre) if conterrornombre > 0 else ''))
                    else:
                        messages.success(request, f'Documentos firmados con éxito')
                else:
                    if conteoerror > 0:
                        messages.warning(request, f'%s' % (
                            'Existieron %s certificados(s) con inconsistencia que no fueron firmados.' % conteoerror if conteoerror > 0 else ''))
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % ex})

        elif action == 'firmarcertificadoindividual':
            try:
                firma = request.FILES["firma"]
                passfirma = request.POST['palabraclave']
                bandera = False
                p12 = None
                certificado = None
                listainscripcion = []
                nombresmae = ''
                conterrornombre = 0
                conteoerror = 0
                bytes_certificado = firma.read()
                extension_certificado = os.path.splitext(firma.name)[1][1:]
                palabras = FirmaCertificadoSecretaria.objects.get(status=True, activo=True).nombrefirma
                # palabras = 'Abg. Stefania Velasco Neira, Mgtr.'

                secretaria = Persona.objects.get(pk=variable_valor('SECRETARIA_G'))
                certificado = Solicitud.objects.get(pk=int(request.POST['id']))
                if not certificado.respaldo:
                    certificado.respaldo = certificado.archivo_respuesta
                    certificado.save(request)
                documento_a_firmar = certificado.archivo_respuesta
                # obtener la posicion xy de la firma del doctor en el pdf
                y, numpaginafirma = obtener_posicion_y(documento_a_firmar.url, palabras)
                # FIN obtener la posicion y
                if y:
                    datau = JavaFirmaEc(
                        archivo_a_firmar=documento_a_firmar, archivo_certificado=bytes_certificado,
                        extension_certificado=extension_certificado,
                        password_certificado=passfirma,
                        page=numpaginafirma, reason='Certificado firmado', lx=260, ly=y)
                    if datau:
                        if datau.datos_del_certificado['cedula'] == secretaria.cedula:
                            generar_archivo_firmado = io.BytesIO()
                            generar_archivo_firmado.write(datau.sign_and_get_content_bytes())
                            generar_archivo_firmado.seek(0)
                            extension = documento_a_firmar.name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            nombrefile_ = remover_caracteres_tildes_unicode(
                                remover_caracteres_especiales_unicode(documento_a_firmar.name)).replace('-', '_').replace('.pdf', '')
                            _name = 'rpt_certificado' + str(certificado.id)
                            file_obj = DjangoFile(generar_archivo_firmado, name=f"{remover_caracteres_especiales_unicode(_name)}_firmado.pdf")
                            certificado.archivo_respuesta = file_obj
                            certificado.certificadofirmado = True
                            certificado.estado = 2
                            certificado.save(request)
                            detalleevidencia = HistorialSolicitud(solicitud_id=certificado.id)
                            detalleevidencia.save(request)
                            detalleevidencia.observacion = 'Certificado firmado'
                            detalleevidencia.responsable = persona
                            detalleevidencia.estado = 2
                            detalleevidencia.fecha = datetime.now().date()
                            detalleevidencia.hora = datetime.now().time()
                            detalleevidencia.save(request)
                            log(u'Masivo Firmó Documento: {}'.format(nombrefile_), request, "add")
                            listainscripcion.append(certificado.perfil.inscripcion.id)
                            nombresmae += '%s, ' % certificado.perfil.inscripcion.persona

                            integrante = Persona.objects.get(status=True, pk=certificado.perfil.inscripcion.persona.id)

                            asunto = u"CERTIFICADO FIRMADO"
                            cuerpo = f'Se le comunica que su certificado ha sido firmado y entregado correctamente. Clic aqu[i, para ser redirigido a la venta mis pedidos.'

                            notificacion3(asunto,
                                          cuerpo, certificado.perfil.persona, None,
                                          '/alu_secretaria/mis_pedidos',
                                          certificado.pk, 1, 'SIE', certificado, certificado.perfil, request)
                        else:
                            return JsonResponse({"result": "bad", "mensaje": f"La firma ingresada no pertenece a la Secretaria General {secretaria} con número de cédula {secretaria.cedula}."})
                    else:
                        conteoerror += 1
                        if certificado.certificadofirmado:
                            certificado.certificadofirmado = False
                        certificado.estado = 7
                        certificado.save(request)

                        detalleevidencia = HistorialSolicitud(solicitud_id=certificado.id)
                        detalleevidencia.save(request)
                        detalleevidencia.observacion = 'Certificado con inconsistencia en la firma'
                        detalleevidencia.responsable = persona
                        detalleevidencia.estado = 7
                        detalleevidencia.fecha = datetime.now().date()
                        detalleevidencia.hora = datetime.now().time()
                        detalleevidencia.save(request)
                else:
                    conteoerror += 1
                    conterrornombre += 1
                    if certificado.certificadofirmado:
                        certificado.certificadofirmado = False
                    certificado.estado = 7
                    certificado.save(request)

                    detalleevidencia = HistorialSolicitud(solicitud_id=certificado.id)
                    detalleevidencia.save(request)
                    detalleevidencia.observacion = 'El nombre de la secretaria general en la firma no es el correcto.'
                    detalleevidencia.responsable = persona
                    detalleevidencia.estado = 7
                    detalleevidencia.fecha = datetime.now().date()
                    detalleevidencia.hora = datetime.now().time()
                    detalleevidencia.save(request)
                    time.sleep(2)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % ex})

        elif action == 'informarasignaturas':
            try:
                eSolicitud = Solicitud.objects.get(pk=int(request.POST['id']))

                eSolicitudAsignaturas = SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud)

                idam = request.POST['ids'].split(',')

                lisid = []
                for id in idam:
                    if int(id) in eSolicitudAsignaturas.values_list('asignaturamalla__id', flat=True):
                        soli = SolicitudAsignatura.objects.filter(status=True, asignaturamalla__id=id, solicitud=eSolicitud).first()
                        soli.estado = 2
                        soli.nota = eSolicitud.solicitud_asignatura_record(soli.asignaturamalla).nota
                        soli.horas = eSolicitud.solicitud_asignatura_record(soli.asignaturamalla).horas
                        soli.creditos = eSolicitud.solicitud_asignatura_record(soli.asignaturamalla).creditos
                        soli.save(request)

                        lisid.append(soli.id)

                        log(u'Marcó como favorable la asignatura: %s' % SolicitudAsignatura, request, "edit")
                    else:
                        asigma = AsignaturaMalla.objects.get(pk=id)
                        soli = SolicitudAsignatura(solicitud=eSolicitud,
                                                   asignaturamalla=asigma,
                                                   estado=2)
                        soli.save(request)

                        soli.nota = eSolicitud.solicitud_asignatura_record(soli.asignaturamalla).nota
                        soli.horas = eSolicitud.solicitud_asignatura_record(soli.asignaturamalla).horas
                        soli.creditos = eSolicitud.solicitud_asignatura_record(soli.asignaturamalla).creditos
                        soli.save(request)

                        lisid.append(soli.id)

                        log(u'Marcó como favorable la asignatura: %s' % SolicitudAsignatura, request, "add")

                for eSoli in eSolicitudAsignaturas.exclude(id__in=lisid):
                    eSoli.estado = 3
                    eSoli.save(request)

                    log(u'Marcó como NO favorable la asignatura: %s' % SolicitudAsignatura, request, "edit")

                eSolicitud.descargar_ficha()
                obs = f'Ha marcadado como favorables las asignaturas: {eSolicitud.lista_asignaturas_favorables()} y como NO favorable las asignaturas: {eSolicitud.lista_asignaturas_no_favorables()}'
                if not HistorialSolicitud.objects.filter(status=True, solicitud=eSolicitud, estado=24):
                    eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                             observacion=obs,
                                                             fecha=datetime.now().date(),
                                                             hora=datetime.now().time(),
                                                             estado=24,
                                                             responsable=persona,
                                                             archivo=eSolicitud.ficha)
                    eHistorialSolicitud.save(request)
                else:
                    histo = HistorialSolicitud.objects.filter(status=True, solicitud=eSolicitud).first()
                    histo.fecha = datetime.now().date()
                    histo.hora = datetime.now().time()
                    histo.observacion = obs
                    histo.archivo = eSolicitud.archivo_solicitud
                    histo.save(request)

                eSolicitud.estado = 24
                eSolicitud.visible = True
                eSolicitud.save(request)

                titulo = 'RESULTADOS DE SU SOLICITUD DE HOMOLOGACIÓN INTERNA POSGRADO'
                notificacion4(titulo, obs, eSolicitud.perfil.persona, None, '/alu_secretaria/service/asignaturashomologa', eSolicitud.pk, 1, 'SIE', eSolicitud, eSolicitud.perfil)
                return JsonResponse({"result": 'ok', "mensaje": u"Asignaturas procesadas"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        elif action == 'aplicarhomologacion':
            try:
                eSolicitud = Solicitud.objects.get(pk=int(request.POST['id']))

                eSolicitudAsignaturas = SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud, estado=2)

                for eSolicitudAsignatura in eSolicitudAsignaturas:

                    record = RecordAcademico(inscripcion=eSolicitud.perfil.inscripcion,
                                             asignatura=eSolicitudAsignatura.asignaturamalla.asignatura,
                                             asignaturamalla=eSolicitudAsignatura.asignaturamalla,
                                             nota=eSolicitudAsignatura.nota,
                                             asistencia=100,
                                             fecha=datetime.now().date(),
                                             aprobada=True,
                                             convalidacion=True,
                                             pendiente=False,
                                             creditos=eSolicitudAsignatura.creditos,
                                             horas=eSolicitudAsignatura.horas,
                                             homologada=True,
                                             valida=True,
                                             validapromedio=True,
                                             observaciones=f'ASIGNATURA HOMOLOGADA POR PROCESO DE HOMOLOGACIÓN INTERNA POSGRAD CON CÓDIGO DE SOLICITUD {eSolicitudAsignatura.solicitud.codigo}',
                                             solicitudho=eSolicitudAsignatura)
                    record.save(request)
                    record.actualizar()

                log(u'Homologó la asignatura: %s' % SolicitudAsignatura, request, "edit")

                obs = f'Se ha HOMOLOGADO las siguientes asignaturas favorables: {eSolicitud.lista_asignaturas_favorables()}.'
                if not HistorialSolicitud.objects.filter(status=True, solicitud=eSolicitud, estado=27):
                    eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                             observacion=obs,
                                                             fecha=datetime.now().date(),
                                                             hora=datetime.now().time(),
                                                             estado=27,
                                                             responsable=persona,
                                                             archivo=eSolicitud.ficha)
                    eHistorialSolicitud.save(request)
                else:
                    histo = HistorialSolicitud.objects.filter(status=True, solicitud=eSolicitud, estado=27).first()
                    histo.fecha = datetime.now().date()
                    histo.hora = datetime.now().time()
                    histo.observacion = obs
                    # histo.archivo = eSolicitud.archivo_solicitud
                    histo.save(request)

                eSolicitud.estado = 27
                eSolicitud.visible = True
                eSolicitud.save(request)

                titulo = 'HOMOLOGACIÓN INTERNA EXITOSA'
                notificacion4(titulo, f'{obs} Por favor, revise su récord académico.', eSolicitud.perfil.persona, None, '/alu_notas', eSolicitud.pk, 1, 'SIE', eSolicitud, eSolicitud.perfil)
                return JsonResponse({"result": 'ok', "mensaje": u"Homologación ejecutada"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})


        elif action == 'changeesfavorable':
            try:
                eSolicitudAsignatura = SolicitudAsignatura.objects.get(status=True, pk=request.POST['idreq'])
                eSolicitud = eSolicitudAsignatura.solicitud

                if eSolicitudAsignatura.estado == 2:
                    eSolicitudAsignatura.estado = 3
                    log(u'Marcó como NO favorable la asignatura: %s' % eSolicitudAsignatura, request, "edit")
                else:
                    eSolicitudAsignatura.estado = 2
                    eSolicitudAsignatura.nota = eSolicitud.solicitud_asignatura_record(eSolicitudAsignatura.asignaturamalla).nota
                    eSolicitudAsignatura.horas = eSolicitud.solicitud_asignatura_record(eSolicitudAsignatura.asignaturamalla).horas
                    eSolicitudAsignatura.creditos = eSolicitud.solicitud_asignatura_record(eSolicitudAsignatura.asignaturamalla).creditos

                    log(u'Marcó como favorable la asignatura: %s' % eSolicitudAsignatura, request, "edit")

                eSolicitudAsignatura.save(request)
                eSolicitudAsignatura.solicitud.visible = True
                eSolicitudAsignatura.solicitud.save(request)
                return JsonResponse({'result': 'ok', 'valor': eSolicitudAsignatura.estado})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'firmarinformehomologacion':
            try:
                idinforme = int(encrypt(request.POST['id_objeto']))
                eInforme = InformeHomologacionPosgrado.objects.get(status=True, pk=idinforme)
                eSolicitud = eInforme.solicitud

                if not IntegrantesInformeHomologacion.objects.filter(status=True, informe=eInforme,
                                                                     persona=persona).exists():
                    return JsonResponse({"result": "bad",
                                         "mensaje": u"Usted no forma parte de los integrantes que firman el documento"})

                eIntegrante = IntegrantesInformeHomologacion.objects.filter(status=True, informe=eInforme, persona=persona).first()

                if eIntegrante.firmado:
                    return JsonResponse({"result": "bad",
                                         "mensaje": u"Usted ya ha firmado el documento"})

                ultimo = IntegrantesInformeHomologacion.objects.filter(status=True, informe=eInforme, firmado=True).order_by('-id').first()

                if ultimo is None:
                    if not IntegrantesInformeHomologacion.objects.filter(status=True, informe=eInforme, persona=persona, orden=1).exists():
                        inte = IntegrantesInformeHomologacion.objects.filter(status=True, informe=eInforme, orden=1).order_by('-id').first()
                        return JsonResponse({"result": "bad",
                                             "mensaje": f"No es su turno de firmar el documento, es el turno de {inte.persona}"})
                else:
                    if ultimo.orden == 1:
                        if not eIntegrante.orden == 2:
                            inte = IntegrantesInformeHomologacion.objects.filter(status=True, informe=eInforme,
                                                                                 orden=2).order_by('-id').first()
                            return JsonResponse({"result": "bad",
                                                 "mensaje": f"No es su turno de firmar el documento, es el turno de {inte.persona}"})
                    elif ultimo.orden == 2:
                        if not eIntegrante.orden == 3:
                            inte = IntegrantesInformeHomologacion.objects.filter(status=True, informe=eInforme,
                                                                                 orden=3).order_by('-id').first()
                            return JsonResponse({"result": "bad",
                                                 "mensaje": f"No es su turno de firmar el documento, es el turno de {inte.persona}"})

                certificado = request.FILES["firma"]
                contrasenaCertificado = request.POST['palabraclave']
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()
                palabras = f'{eIntegrante.responsabilidad}'

                documento_a_firmar = eInforme.archivo_actual_2()
                y, numpaginafirma = obtener_posicion_y(documento_a_firmar.url, palabras)

                if y:
                    datau = JavaFirmaEc(
                        archivo_a_firmar=documento_a_firmar, archivo_certificado=bytes_certificado,
                        extension_certificado=extension_certificado,
                        password_certificado=contrasenaCertificado,
                        page=numpaginafirma, reason='Informe homologacion interna firmado', lx=360, ly=y-55)
                    if datau:
                        generar_archivo_firmado = io.BytesIO()
                        generar_archivo_firmado.write(datau.sign_and_get_content_bytes())
                        generar_archivo_firmado.seek(0)
                        extension = documento_a_firmar.name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        nombrefile_ = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(documento_a_firmar.name)).replace('-', '_').replace('.pdf', '')
                        _name = f'informehomologacion_{eInforme.codigo}'

                        file_obj = DjangoFile(generar_archivo_firmado,
                                              name=f"{remover_caracteres_especiales_unicode(_name)}_firmado.pdf")

                        # eSolicitud.archivocontrato = file_obj

                        eIntegrante.firmado = True
                        eIntegrante.save(request)
                        log(u'Firmó Informe de homologacion: {}'.format(eIntegrante), request, "add")

                        detalleevidencia = HistorialInformeHomologacion(informe=eInforme)
                        detalleevidencia.save(request)
                        detalleevidencia.observacion = f'Archivo firmado por {eIntegrante.persona}.'
                        detalleevidencia.archivo = file_obj
                        detalleevidencia.persona = persona
                        if eInforme.get_cantidad_de_integrantes_que_han_firmado() == 3:
                            detalleevidencia.estadorevision = 3
                            eInforme.estadorevision = 3
                            eInforme.save(request)
                        else:
                            detalleevidencia.estadorevision = 2
                        detalleevidencia.fecha = datetime.now().date()
                        detalleevidencia.hora = datetime.now().now()
                        detalleevidencia.save(request)
                        log(u'Firmó Documento: {}'.format(nombrefile_), request, "add")

                        if eIntegrante.orden == 1:
                            eIntegranteNoti = IntegrantesInformeHomologacion.objects.get(status=True, informe=eInforme, orden=2)
                            asunto = u"INFORME DE HOMOLOGACION I. FIRMADO"
                            observacion = f'Se le comunica que el Msc. {eIntegrante.persona} ha generado y firmado el Informe de Homologacion Interna del solicitante {eSolicitud.perfil.persona}. Por favor, revise el documento y fírmelo en caso de ser correcto.'
                            para = eIntegranteNoti.persona
                            perfiu = eIntegranteNoti.persona.perfilusuario_administrativo()

                            notificacion3(asunto, observacion, para, None,
                                          f'/adm_secretaria?action=versolicitudes&id={eSolicitud.servicio.categoria.id}&ids=0&s={eSolicitud.codigo}',
                                          para.pk, 1,
                                          'sga', Persona, perfiu, request)
                        elif eIntegrante.orden == 2:
                            eIntegranteNoti =  IntegrantesInformeHomologacion.objects.get(status=True, informe=eInforme, orden=3)
                            asunto = u"INFORME DE HOMOLOGACION I. FIRMADO"
                            observacion = f'Se le comunica que la encargada de Secretaría Técnica de Posgrado {eIntegrante.persona} ha revisado y firmado el Informe de Homologación Interna del solicitante {eSolicitud.perfil.persona}. Por favor, revise el documento y fírmelo para aprobar la homologación de dichas asignaturas.'
                            para = eIntegranteNoti.persona
                            perfiu = eIntegranteNoti.persona.perfilusuario_administrativo()

                            notificacion3(asunto, observacion, para, None,
                                          f'/adm_secretaria?action=versolicitudes&id={eSolicitud.servicio.categoria.id}&ids=0&s={eSolicitud.codigo}',
                                          para.pk, 1,
                                          'sga', Persona, perfiu, request)

                        elif eIntegrante.orden == 3:
                            asunto = u"INFORME DE HOMOLOGACION I. APROBADO"
                            observacion = f'Se le comunica a las autoriades que el director de la {eSolicitud.perfil.inscripcion.carrera.escuelaposgrado} ha revisado y aprobado el Informe de Homologación Interna del solicitante {eSolicitud.perfil.persona}. Por favor, continuar con el proceso.'
                            for integrante in eInforme.get_integrantes_notifican():
                                para = integrante.persona
                                perfiu = integrante.persona.perfilusuario_administrativo()

                                notificacion3(asunto, observacion, para, None,
                                              f'/adm_secretaria?action=versolicitudes&id={eSolicitud.servicio.categoria.id}&ids=0&s={eSolicitud.codigo}',
                                              para.pk, 1,
                                              'sga', Persona, perfiu, request)

                        if eInforme.get_cantidad_de_integrantes_que_han_firmado() == 3:
                            eSolicitud.estado = 12
                            eSolicitud.save(request)

                            eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                                     observacion=f'El documento ha sido legalizado por todos los integrantes.',
                                                                     fecha=datetime.now().date(),
                                                                     hora=datetime.now().time(),
                                                                     estado=eSolicitud.estado,
                                                                     responsable=persona,
                                                                     archivo=detalleevidencia.archivo)
                            eHistorialSolicitud.save(request)
                    else:
                        return JsonResponse({"result": "bad",
                                             "mensaje": f"Error al firmar el archivo"})
                return JsonResponse({"result": False, 'mensaje':'Archivo firmado correctamente', 'url':eInforme.archivo_actual()})
            except Exception as ex:
                messages.error(request, f'{ex}')

        elif action == 'listarasignaturas':
            try:
                if 'id' in request.POST:
                    lista = []
                    idmallas = Malla.objects.filter(status=True, carrera__id=int(request.POST['id'])).values_list('id', flat=True).order_by('id').distinct()
                    eAsignaturas = AsignaturaMalla.objects.filter(status=True, malla__id__in=idmallas)
                    for eAsignatura in eAsignaturas:
                        lista.append([eAsignatura.id, f'{eAsignatura.id} - {eAsignatura.asignatura.nombre}'])
                    return JsonResponse({"result": "ok", 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        elif action == 'consultadatosasi':
            try:
                eAsignaturaMalla = AsignaturaMalla.objects.get(status=True, pk=int(request.POST['id']))

                return JsonResponse({"result": "ok", "creditos": eAsignaturaMalla.creditos, "horas": eAsignaturaMalla.horas})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s"%(ex)})

        elif action == 'addasignaturashomologables':
            try:
                with transaction.atomic():
                    form = CarreraHomologableForm(request.POST)
                    if not 'lista_items1' in request.POST:
                        raise NameError('Debe adicionar un asignatura homologable')
                    for registro in json.loads(request.POST['lista_items1']):
                        eAsignaturaHom = AsignaturaMalla.objects.get(pk=int(request.POST['asignatura']))
                        eAsignaturaCom = AsignaturaMalla.objects.get(pk=int(registro['asignaturaco']))

                        if AsignaturaCompatibleHomologacion.objects.filter(status=True, asignaturach=eAsignaturaHom, asignaturama=eAsignaturaCom).exists():
                            return JsonResponse({'error': True,
                                                 "mensaje": f'La asignatura {eAsignaturaCom} del programa de {eAsignaturaCom.malla.carrera} ya ha sido configurada como homologable para la asignatura {eAsignaturaHom} del programa de {eAsignaturaHom.malla.carrera}'},
                                                safe=False)
                        else:
                            eAsignaturaHomologable = AsignaturaCompatibleHomologacion(asignaturach=eAsignaturaHom,
                                                                                      asignaturama=eAsignaturaCom)
                            eAsignaturaHomologable.save(request)
                            log(u'Adicionó asignaturas homologable: %s' % eAsignaturaHomologable, request, "add")

                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. Detalle: %s"%(ex.__str__())}, safe=False)

        elif action == 'editasignaturashomologables':
            try:
                with transaction.atomic():
                    form = CarreraHomologableForm(request.POST)
                    id = int(request.POST['id'])

                    eAsi = AsignaturaMalla.objects.get(pk=id)
                    if not 'lista_items1' in request.POST:
                        raise NameError('Debe adicionar un asignatura homologable')

                    dicc = json.loads(request.POST['lista_items1'])
                    asignaturaco_list = [int(item['asignaturaco']) for item in dicc]

                    ids = AsignaturaCompatibleHomologacion.objects.filter(status=True, asignaturach=eAsi).values_list('asignaturama__id', flat=True).distinct()

                    list_remove = []
                    for id in ids:
                        if id not in asignaturaco_list:
                            list_remove.append(id)

                    list_add = []
                    for id in asignaturaco_list:
                        if id not in ids:
                            list_remove.append(id)


                    for registro in list_add:
                        eAsignaturaHom = AsignaturaMalla.objects.get(pk=eAsi.id)
                        eAsignaturaCom = AsignaturaMalla.objects.get(pk=int(registro))

                        if not AsignaturaCompatibleHomologacion.objects.filter(status=True, asignaturach=eAsignaturaHom, asignaturama=eAsignaturaCom).exists():
                            eAsignaturaHomologable = AsignaturaCompatibleHomologacion(asignaturach=eAsignaturaHom,
                                                                                      asignaturama=eAsignaturaCom)
                            eAsignaturaHomologable.save(request)
                            log(u'Adicionó asignaturas homologable: %s' % eAsignaturaHomologable, request, "add")

                    for registro in list_remove:
                        eAsignaturaHom = AsignaturaMalla.objects.get(pk=eAsi.id)
                        eAsignaturaCom = AsignaturaMalla.objects.get(pk=int(registro))

                        if AsignaturaCompatibleHomologacion.objects.filter(status=True, asignaturach=eAsignaturaHom, asignaturama=eAsignaturaCom).exists():
                            eAsignaturaHomologable = AsignaturaCompatibleHomologacion.objects.filter(status=True, asignaturach=eAsignaturaHom, asignaturama=eAsignaturaCom).first()
                            eAsignaturaHomologable.status = False
                            eAsignaturaHomologable.save(request)
                            log(u'Adicionó asignaturas homologable: %s' % eAsignaturaHomologable, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. Detalle: %s"%(ex.__str__())}, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'versolicitudes':
                try:
                    data['title'] = u'Gestión de solicitudes'
                    es_director = False
                    es_coordi = False
                    es_secretaria = False
                    es_experta = False

                    filtros = Q(pk__gte=0)

                    experta = Persona.objects.get(status=True, pk=int(variable_valor('EXPERTA_SECRETARÍA')))

                    if persona.id == experta.id:
                        es_experta = True

                    cate = CategoriaServicio.objects.get(status=True, id=int(request.GET['id']))

                    if persona.id in Persona.objects.filter(id__in=variable_valor('PERSONAL_SECRETARIA'), status=True).values_list('id', flat=True):
                        es_secretaria = True

                    if 'SOLO_TITULACION_EX' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                        if CohorteMaestria.objects.filter(status=True, coordinador=persona).exists():
                            idcarreras = CohorteMaestria.objects.filter(status=True, coordinador=persona).values_list('maestriaadmision__carrera__id', flat=True).order_by('maestriaadmision__carrera__id').distinct()
                            filtros = Q(pk__gte=0, servicio__categoria__id=int(request.GET['id']), perfil__inscripcion__carrera__id__in=idcarreras)
                            es_coordi = True
                            data['eCarreras'] = Carrera.objects.filter(status=True, id__in=idcarreras)
                    elif 'SOLICITUDES_ALL' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                        if cate.roles == '1':
                            carreras = Carrera.objects.filter(status=True, coordinacionvalida__id__in=[1, 2, 3, 4, 5])
                        elif cate.roles == '2':
                            carreras = Carrera.objects.filter(status=True, coordinacion__id__in=[1, 2, 3, 4, 5])
                        elif cate.roles == '3':
                            carreras = Carrera.objects.filter(status=True, coordinacion__id=7)
                        else:
                            carreras = Carrera.objects.filter(status=True)

                        filtros = Q(pk__gte=0, servicio__categoria__id=int(request.GET['id']), perfil__inscripcion__carrera__id__in=carreras.values_list('id', flat=True))
                        data['eCarreras'] = carreras
                    elif 'DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                        es_director = True
                        idcarreras = PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN').values_list('carrera_id', flat=True)
                        filtros = Q(pk__gte=0, servicio__categoria__id=int(request.GET['id']),
                                    perfil__inscripcion__carrera__id__in=idcarreras, estado__in=[11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 24, 25, 26, 27])
                        data['eCarreras'] = Carrera.objects.filter(status=True, id__in=idcarreras)
                    elif 'DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                        es_director = True
                        idcarreras = PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD').values_list('carrera_id', flat=True)
                        filtros = Q(pk__gte=0, servicio__categoria__id=int(request.GET['id']),
                                    perfil__inscripcion__carrera__id__in=idcarreras, estado__in=[11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 24, 25, 26, 27])
                        data['eCarreras'] = Carrera.objects.filter(status=True, id__in=idcarreras)
                    elif 'DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                        es_director = True
                        idcarreras = PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO').values_list('carrera_id', flat=True)
                        filtros = Q(pk__gte=0, servicio__categoria__id=int(request.GET['id']),
                                    perfil__inscripcion__carrera__id__in=idcarreras, estado__in=[11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 24, 25, 26, 27])
                        data['eCarreras'] = Carrera.objects.filter(status=True, id__in=idcarreras)
                    elif 'SOLICITUDES_FACI' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                        if cate.roles == '1':
                            carreras = Carrera.objects.filter(status=True, coordinacionvalida__id=4)
                        else:
                          carreras = Carrera.objects.filter(status=True, coordinacion__id=4)
                        filtros = Q(pk__gte=0, servicio__categoria__id=int(request.GET['id']), perfil__inscripcion__carrera__id__in=carreras.values_list('id', flat=True))
                        data['eCarreras'] = carreras
                    elif 'SOLICITUDES_FASO' in persona.usuario.groups.all().distinct().values_list('name', flat=True) and 'SOLICITUDES_FACAC' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                        carreras = None
                        if cate.roles == '1':
                            carreras = Carrera.objects.filter(status=True, coordinacionvalida__id__in=[3, 2])
                        else:
                            if 'SOLICITUDES_ASISTENTE_1' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                                carreras = Carrera.objects.filter(status=True, id__in=[134, 138, 244, 7, 130, 160, 246, 89, 190, 161, 6, 162,
                                                                    92, 141, 95, 225, 140, 61])
                            if 'SOLICITUDES_ASISTENTE_2' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                                carreras = Carrera.objects.filter(status=True, id__in=[188, 9, 145, 91, 164, 8, 43, 165, 11, 128, 158, 245,
                                                                    248, 10, 88, 144, 16, 12, 126, 242, 163, 93])
                            if 'SOLICITUDES_ASISTENTE_3' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                                carreras = Carrera.objects.filter(status=True, id__in=[132, 136, 243, 18, 137, 58, 152, 5, 159, 15, 131, 143,
                                                                    247, 80])
                        filtros = Q(pk__gte=0, servicio__categoria__id=int(request.GET['id']), perfil__inscripcion__carrera__id__in=carreras.values_list('id', flat=True))
                        data['eCarreras'] = carreras
                    elif 'SOLICITUDES_FACE' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                        if cate.roles == '1':
                            carreras = Carrera.objects.filter(status=True, coordinacionvalida__id=5)
                        else:
                            carreras = Carrera.objects.filter(status=True, coordinacion__id=5)
                        filtros = Q(pk__gte=0, servicio__categoria__id=int(request.GET['id']), perfil__inscripcion__carrera__id__in=carreras.values_list('id', flat=True))
                        data['eCarreras'] = carreras
                    elif 'SOLICITUDES_FACS' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                        if cate.roles == '1':
                            carreras = Carrera.objects.filter(status=True, coordinacionvalida__id=1)
                        else:
                            carreras = Carrera.objects.filter(status=True, coordinacion__id=1)
                        filtros = Q(pk__gte=0, servicio__categoria__id=int(request.GET['id']), perfil__inscripcion__carrera__id__in=carreras.values_list('id', flat=True))
                        data['eCarreras'] = carreras
                    else:
                        filtros = Q(pk__gte=0, servicio__categoria__id=int(request.GET['id']))
                        if cate.roles == '3':
                            data['eCarreras'] = Carrera.objects.filter(status=True, coordinacion__id=7).order_by('-id').distinct()
                        elif cate.roles == '1':
                            data['eCarreras'] = Carrera.objects.filter(status=True, coordinacion__id=9).order_by('-id').distinct()
                        else:
                            data['eCarreras'] = Carrera.objects.filter(status=True).exclude(coordinacion__id=7).order_by('-id').distinct()

                    s = request.GET.get('s', '')
                    ids = request.GET.get('ids', '0')
                    idc = request.GET.get('idc', '0')
                    ide = request.GET.get('ide', '0')
                    url_vars = '&action=versolicitudes&id=' + request.GET['id']

                    if s:
                        filtros = filtros & (Q(servicio__nombre__icontains=s) | Q(perfil__persona__nombres__contains=s) | Q(perfil__persona__apellido1__contains=s) | Q(perfil__persona__apellido2__contains=s) | Q(perfil__persona__cedula__contains=s) | Q(perfil__persona__pasaporte__contains=s) | Q(codigo__contains=s))
                        ss = s.split(" ")
                        if ss.__len__() == 2:
                            filtros = filtros & (Q(perfil__persona__apellido1__contains=ss[0]) & Q(perfil__persona__apellido2__contains=ss[1]))
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"

                    if int(ids):
                        filtros = filtros & (Q(servicio_id=ids))
                        data['ids'] = f"{ids}"
                        url_vars += f"&ids={ids}"

                    if int(idc):
                        filtros = filtros & (Q(perfil__inscripcion__carrera__id=idc))
                        data['idc'] = f"{idc}"
                        url_vars += f"&idc={idc}"

                    if int(ide):
                        if int(ide) == 30:
                            filtros = filtros & (Q(firmadoec=False))
                            data['ide'] = f"{ide}"
                            url_vars += f"&ide={ide}"
                        if int(ide) == 31:
                            filtros = filtros & (Q(carrera_homologada__isnull=True))
                            data['ide'] = f"{ide}"
                            url_vars += f"&ide={ide}"
                        if int(ide) == 32:
                            filtros = filtros & (Q(carrera_homologada__isnull=False))
                            data['ide'] = f"{ide}"
                            url_vars += f"&ide={ide}"
                        else:
                            filtros = filtros & (Q(estado=ide))
                            data['ide'] = f"{ide}"
                            url_vars += f"&ide={ide}"

                    eSolicitudes = Solicitud.objects.filter(filtros).order_by('-fecha', '-hora')
                    paging = MiPaginador(eSolicitudes, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['eSolicitudes'] = page.object_list
                    data['url_vars'] = url_vars
                    data['eServicios'] = Servicio.objects.values_list('id', 'nombre').filter(status=True, categoria__id=int(request.GET['id'])).distinct()
                    data['id'] = int(request.GET['id'])
                    data['eTotal'] = eSolicitudes.count()
                    data['eSolicitados'] = eSolicitudes.filter(estado=1).count()
                    data['eEntregados'] = eSolicitudes.filter(estado=2).count()
                    data['ePendientes'] = eSolicitudes.filter(estado=3).count()
                    data['ePagados'] = eSolicitudes.filter(estado=4).count()
                    data['eReasignados'] = eSolicitudes.filter(estado=5).count()
                    data['eAsignados'] = eSolicitudes.filter(estado=6).count()
                    data['eRechazados'] = eSolicitudes.filter(estado=7).count()
                    data['eVencidos'] = eSolicitudes.filter(estado=9).count()
                    data['eEliminados'] = eSolicitudes.filter(estado=8).count()
                    data['cate'] = cate
                    data['es_director'] = es_director
                    data['es_coordinador'] = es_coordi
                    data['es_secretaria'] = es_secretaria
                    data['es_experta'] = es_experta

                    if cate.id == 7:
                        return render(request, "adm_secretaria/solicitudeshomoi.html", data)
                    else:
                        return render(request, "adm_secretaria/versolicitudes.html", data)
                except Exception as ex:
                    pass

            elif action == 'verformatoscertificados':
                try:
                    data['title'] = u'Formatos de certificados'
                    if int(request.GET['id']) == 1:
                        filtros = Q(status=True, roles=3)
                    elif int(request.GET['id']) == 4:
                        filtros = Q(status=True, roles=2)
                    elif int(request.GET['id']) == 5:
                        filtros = Q(status=True, roles=1)
                    else:
                        filtros = Q(status=True)

                    s = request.GET.get('s', '')
                    idt = request.GET.get('idt', '0')
                    url_vars = '&action=verformatoscertificados&id=' + request.GET['id']

                    if s:
                        filtros = filtros & (Q(certificacion__icontains=s))
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"

                    if int(idt):
                        filtros = filtros & (Q(tipo_origen=idt))
                        data['idt'] = f"{idt}"
                        url_vars += f"&idt={idt}"

                    eFormatos = FormatoCertificado.objects.filter(filtros).order_by('-id')
                    paging = MiPaginador(eFormatos, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['eFormatos'] = page.object_list
                    data['url_vars'] = url_vars
                    data['id'] = int(request.GET['id'])
                    return render(request, "adm_secretaria/verformatoscertificados.html", data)
                except Exception as ex:
                    pass

            elif action == 'configurarhomologacion':
                try:
                    data['title'] = u'Asignaturas homologables'
                    idasi = AsignaturaCompatibleHomologacion.objects.filter(status=True).values_list('asignaturach__id', flat=True).distinct()
                    filtros = Q(status=True, id__in=idasi)

                    id = request.GET['id']
                    url_vars = f'?action=configurarhomologacion&id={id}'

                    search = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtros = filtros & (Q(asignatura__nombre__icontains=search) | Q(asignatura__nombre__icontains=search))
                        url_vars += f"&s={search}"

                    eAsignaturas = AsignaturaMalla.objects.filter(filtros).order_by('-id')
                    paging = MiPaginador(eAsignaturas, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['eAsignaturas'] = page.object_list
                    data['url_vars'] = url_vars
                    data['s'] = search if search else ""
                    data['id'] = int(id)
                    return render(request, "adm_secretaria/configuracionho.html", data)
                except Exception as ex:
                    pass

            elif action == 'addasignaturashomologables':
                try:
                    data['title'] = u'Adicionar configuración de homologación de asignaturas'
                    form = CarreraHomologableForm()
                    data['form'] = form
                    form.fields['carrera'].queryset = Carrera.objects.filter(status=True, coordinacion__id=7).order_by('-id')
                    form.fields['carreraco'].queryset = Carrera.objects.filter(status=True, coordinacion__id=7).order_by('-id')
                    data['id'] = int(request.GET['id'])
                    return render(request, "adm_secretaria/addasignaturashomologables.html", data)
                except Exception as ex:
                    pass

            elif action == 'editasignaturashomologables':
                try:
                    data['title'] = u'Editar configuración de homologación de asignaturas'
                    data['eAsignaturaHo'] = eAsignaturaHo = AsignaturaMalla.objects.get(status=True, pk=int(request.GET['id']))
                    data['eAsignaturasCo'] = AsignaturaCompatibleHomologacion.objects.filter(status=True, asignaturach=eAsignaturaHo).order_by('-id')
                    form = CarreraHomologableForm(initial={'carrera':eAsignaturaHo.malla.carrera,
                                                           'asignatura': eAsignaturaHo,
                                                           'creditos': eAsignaturaHo.creditos,
                                                           'horas': eAsignaturaHo.horas})
                    data['form'] = form
                    form.editar()
                    form.fields['carrera'].queryset = Carrera.objects.filter(status=True, coordinacion__id=7).order_by('-id')
                    form.fields['asignatura'].queryset = AsignaturaMalla.objects.filter(status=True, malla__carrera__coordinacion__id=7).order_by('-id')
                    form.fields['carreraco'].queryset = Carrera.objects.filter(status=True, coordinacion__id=7).order_by('-id')
                    data['id'] = int(request.GET['id'])
                    data['idc'] = int(request.GET['idc'])
                    return render(request, "adm_secretaria/editasignaturashomologables.html", data)
                except Exception as ex:
                    pass

            elif action == 'validarasignaturasagregadas':
                try:
                    eAsignaturaah = AsignaturaMalla.objects.get(status=True, pk=int(request.GET['asignaturaah_id']))
                    eAsignaturaco = AsignaturaMalla.objects.get(status=True, pk=int(request.GET['asignaturaco_id']))

                    if AsignaturaCompatibleHomologacion.objects.filter(status=True, asignaturach=eAsignaturaah, asignaturama=eAsignaturaco).exists():
                        return JsonResponse({'result': False,
                                             "mensaje": f'La asignatura {eAsignaturaco.asignatura.nombre} ya ha sido configurada como asignatura homologable para la asignatura {eAsignaturaah.asignatura.nombre} de la carrera {eAsignaturaah.malla.carrera}.'},
                                            safe=False)

                    res_js = {"result": True}
                except Exception as ex:
                    import sys
                    line_error = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    print(line_error)
                    res_js = {"result":False,"mensaje":"Ocurrio un error!. Detalle: %s"% ex.__str__(),"line_erro":line_error}
                return JsonResponse(res_js)

            elif action == 'listadoafirmar':
                try:
                    data['title'] = u'Certificaciones a firmar'

                    search = request.GET.get('s', None)
                    ide = request.GET.get('ide', '0')
                    idt = request.GET.get('idt', '0')
                    url_vars = '&action=listadoafirmar'

                    filtro = Q(status=True, estado__in=[22, 7]) | Q(status=True, certificadofirmado=True)
                    # filtro = Q(status=True, servicio__categoria__id=int(request.GET['id']), estado__in=[22, 7]) | Q(status=True, servicio__categoria__id=int(request.GET['id']), certificadofirmado=True)

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(perfil__inscripcion__persona__apellido1__icontains=search) |
                                                     Q(perfil__inscripcion__persona__apellido2__icontains=search) |
                                                     Q(perfil__inscripcion__persona__nombres__icontains=search) |
                                                     Q(perfil__inscripcion__persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(perfil__inscripcion__persona__apellido1__icontains=ss[0]) &
                                                     Q(perfil__inscripcion__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(perfil__inscripcion__persona__apellido1__icontains=ss[0]) &
                                                Q(perfil__inscripcion__persona__apellido2__icontains=ss[1]) &
                                               Q(perfil__inscripcion__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)

                    if int(ide):
                        if int(ide) == 1:
                            filtro = filtro & (Q(certificadofirmado=True))
                            data['ide'] = f"{ide}"
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 2:
                            filtro = filtro & (Q(certificadofirmado=False))
                            data['ide'] = f"{ide}"
                            url_vars += f"&ide={ide}"

                    if int(idt):
                        cor = [1, 2, 3, 4, 5, 7]
                        if int(idt) == 1:
                            cor = [7]
                        elif int(idt) == 2:
                            cor = [1, 2, 3, 4, 5]
                        filtro = filtro & (Q(perfil__inscripcion__carrera__coordinacion__in=cor))
                        data['idt'] = f"{idt}"
                        url_vars += f"&idt={idt}"

                    eSolicitudes = Solicitud.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(eSolicitudes, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['eSolicitudes'] = page.object_list
                    data['url_vars'] = url_vars
                    # data['id'] = int(request.GET['id'])
                    data['Total'] = eSolicitudes.count()
                    data['Firmados'] = eSolicitudes.filter(certificadofirmado=True).count()
                    data['Nofirmados'] = eSolicitudes.filter(certificadofirmado=False).count()
                    return render(request, "adm_secretaria/listadoafirmar.html", data)
                except Exception as ex:
                    pass

            elif action == 'cronogramatitulacion':
                try:
                    data['title'] = u'Actividades de cronograma de titulación extraordinaria'
                    filtros = Q(status=True)

                    s = request.GET.get('s', '')
                    idt = request.GET.get('idt', '0')
                    url_vars = '&action=cronogramatitulacion'

                    if s:
                        filtros = filtros & (Q(nombre__icontains=s) | Q(descripcion__icontains=s))
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"

                    eActividades = ActividadCronogramaTitulacion.objects.filter(filtros).order_by('-id')
                    paging = MiPaginador(eActividades, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['eActividades'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "adm_secretaria/cronogramatitulacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'vercronogramatitulacion':
                try:
                    id = request.GET.get('id', '0')
                    eSolicitud = Solicitud.objects.get(status=True, pk=int(id))
                    data['title'] = u'Cronograma de titulación extraordinaria de ' + str(eSolicitud.perfil.inscripcion.persona)

                    eActividades = DetalleActividadCronogramaTitulacion.objects.filter(status=True, solicitud=eSolicitud).order_by('inicio')
                    paging = MiPaginador(eActividades, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['eActividades'] = page.object_list
                    data['solicitante'] = eSolicitud
                    return render(request, "adm_secretaria/vercronogramaex.html", data)
                except Exception as ex:
                    pass

            elif action == 'infoservicios':
                try:
                    id= int(request.GET['id'])
                    data['categoria'] = categoria = CategoriaServicio.objects.get(pk=id, status=True)
                    data['servicios'] = Servicio.objects.filter(status=True, categoria=categoria).order_by('id')
                    template=get_template('adm_secretaria/modales/infoservicios.html')
                    return JsonResponse({'result':'ok','data':template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'infoobservacion':
                try:
                    id= int(encrypt(request.GET['id']))
                    solicitud = Solicitud.objects.get(pk=id)
                    data['historiales'] = HistorialSolicitud.objects.filter(status=True, solicitud=solicitud).order_by('id')
                    data['solicitante'] = solicitud
                    template=get_template('adm_secretaria/modales/infoobservacion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'historialfirmas':
                try:
                    id= int(encrypt(request.GET['id']))
                    informe = InformeHomologacionPosgrado.objects.get(pk=id)
                    data['historiales'] = HistorialInformeHomologacion.objects.filter(status=True, informe=informe).order_by('id')
                    data['solicitante'] = informe.solicitud
                    template=get_template('adm_secretaria/modales/historialfirma.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addentrega':
                try:
                    data['title'] = u'Asignar horario de retiro'
                    data['action'] = request.GET['action']
                    data['id'] = id = int(request.GET['id'])
                    solicitud = Solicitud.objects.get(pk=id)
                    form = EntregaCertificadoForm(initial={'postulante': solicitud.perfil.persona.nombre_completo_inverso(),
                                                      'maestria': solicitud.perfil.inscripcion.carrera,
                                                      'periodo': solicitud.perfil.inscripcion.matricula_posgrado(),
                                                      'observacion': 'Ninguna'})
                    data['form'] = form
                    template = get_template("adm_secretaria/modales/addhorarioretiro.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'addformato':
                try:
                    data['title'] = u'Adicionar formato de certificado'
                    data['action'] = request.GET['action']
                    data['idc'] = request.GET['idc']
                    form = SubirFormatoCertificadoForm()
                    data['form2'] = form
                    template = get_template("adm_secretaria/modales/addformato.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'addactividad':
                try:
                    data['title'] = u'Adicionar actividad de cronograma'
                    data['action'] = request.GET['action']
                    form = AdicionarActividadCronogramaForm()
                    data['form2'] = form
                    template = get_template("adm_secretaria/modales/addactividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'addactividadtituex':
                try:
                    data['title'] = u'Adicionar actividad de cronograma de titulación'
                    data['action'] = request.GET['action']
                    solicitante = Solicitud.objects.get(status=True, pk=int(request.GET['id']))
                    detalle = DetalleActividadCronogramaTitulacion.objects.filter(status=True, solicitud=solicitante)
                    if detalle:
                        form = ActividadCronogramaTitulacionForm(initial={'solicitante':solicitante.perfil.inscripcion.persona,
                                                                          'periodo':detalle[0].periodo})
                    else:
                        form = ActividadCronogramaTitulacionForm(initial={'solicitante':solicitante.perfil.inscripcion.persona})
                    data['form2'] = form
                    data['id'] = solicitante.id
                    template = get_template("adm_secretaria/modales/addactividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'configurarintegrantestitu':
                try:
                    data['action'] = 'configurarintegrantestitu'
                    solicitante = Solicitud.objects.get(status=True, pk=int(request.GET['id']))
                    eDirector = eCoordinador = None
                    if IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=solicitante, tipo=1).exists():
                        eDirector = IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=solicitante, tipo=1).first()

                    if IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=solicitante, tipo=2).exists():
                        eCoordinador = IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=solicitante, tipo=2).first()

                    form = IntegrantesTitulacionForm(initial={'solicitante':solicitante.perfil.inscripcion.persona,
                                                               # 'director': eDirector,
                                                               'cargodir': eDirector.cargo if eDirector else None,
                                                              # 'coordinador': eCoordinador,
                                                              'cargocor': eCoordinador.cargo if eCoordinador else None})

                    if eDirector:
                        form.edit_director(eDirector.administrativo.id)

                    if eCoordinador:
                        form.edit_coordinador(eCoordinador.administrativo.id)

                    data['form2'] = form
                    data['id'] = solicitante.id
                    template = get_template("adm_secretaria/modales/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'buscaradministrativo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Administrativo.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                      | Q(persona__apellido2__icontains=s[0])
                                                      | Q(persona__cedula__icontains=s[0])
                                                      | Q(persona__pasaporte__icontains=s[0])
                                                      | Q(persona__ruc__icontains=s[0]),
                                                      status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        personas = Administrativo.objects.filter(Q(persona__apellido1__icontains=s[0]) & Q(persona__apellido2__icontains=s[1]),
                                                           status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso())} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editformato':
                try:
                    data['title'] = u'Adicionar formato de certificado'
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = FormatoCertificado.objects.get(status=True, pk=int(request.GET['id']))
                    data['action'] = request.GET['action']
                    form = SubirFormatoCertificadoForm(initial=model_to_dict(filtro))
                    data['form2'] = form
                    template = get_template("adm_secretaria/modales/addformato.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editactividad':
                try:
                    data['title'] = u'Adicionar formato de certificado'
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ActividadCronogramaTitulacion.objects.get(status=True, pk=int(request.GET['id']))
                    data['action'] = request.GET['action']
                    form = AdicionarActividadCronogramaForm(initial=model_to_dict(filtro))
                    data['form2'] = form
                    template = get_template("adm_secretaria/modales/addactividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editactividadtituex':
                try:
                    data['title'] = u'Adicionar formato de certificado'
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = DetalleActividadCronogramaTitulacion.objects.get(status=True, pk=int(request.GET['id']))
                    data['action'] = request.GET['action']
                    form = ActividadCronogramaTitulacionForm(initial={'solicitante': filtro.solicitud.perfil.inscripcion.persona,
                                                                      'periodo':filtro.periodo,
                                                                      'actividad':filtro.actividad,
                                                                      'inicio':filtro.inicio,
                                                                      'fin':filtro.fin,
                                                                      'observacion':filtro.observacion})
                    data['form2'] = form
                    template = get_template("adm_secretaria/modales/addactividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'subircertificado':
                try:
                    data['title'] = u'Subir archivo de certificado personalizado'
                    data['action'] = 'subircertificado'
                    data['id'] = id = int(request.GET['id'])
                    form = SubirCertificadoPersonalizadoForm()
                    data['form2'] = form
                    template = get_template("adm_secretaria/modales/subircertificado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'subirinformetecnico':
                try:
                    data['title'] = u'Subir archivo de certificado personalizado'
                    data['action'] = 'subirinformetecnico'
                    data['id'] = id = int(request.GET['id'])

                    if 'clave' in request.GET:
                        data['clave'] = request.GET['clave']

                    form = SubirInformeTecnicoPertinenciaForm()
                    data['form2'] = form
                    form.sin_carrera()
                    template = get_template("adm_secretaria/modales/subircertificado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'rechazarfirmaec':
                try:
                    data['title'] = u'Subir archivo de certificado personalizado'
                    data['action'] = 'rechazarfirmaec'
                    data['id'] = id = int(request.GET['id'])
                    data['eSolicitud'] = Solicitud.objects.get(pk=id)

                    form = SubirInformeTecnicoPertinenciaForm()
                    data['form2'] = form

                    if 'clave' in request.GET and request.GET['clave'] == 'rechazo':
                        data['clave'] = request.GET['clave']
                        form.sin_archivo()
                        form.sin_carrera()

                    template = get_template("adm_secretaria/modales/subircertificado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'seleccionarcarreraho':
                try:
                    data['title'] = u'Subir archivo de certificado personalizado'
                    data['action'] = 'seleccionarcarreraho'
                    data['id'] = id = int(request.GET['id'])
                    data['eSolicitud'] = eSolicitud =Solicitud.objects.get(pk=id)

                    form = SubirInformeTecnicoPertinenciaForm()
                    data['form2'] = form

                    if 'clave' in request.GET and request.GET['clave'] == 'selectcarreraho':
                        data['clave'] = request.GET['clave']
                        form.solo_carrera()

                    idcarreras = RecordAcademico.objects.filter(status=True, inscripcion__carrera__coordinacion__id=7,
                                                       inscripcion__persona=eSolicitud.perfil.inscripcion.persona, asignaturamalla__isnull=False).values_list('inscripcion__carrera__id', flat=True).order_by('inscripcion__carrera__id').distinct()

                    form.fields['carrera'].queryset = Carrera.objects.filter(id__in=idcarreras).exclude(id=eSolicitud.perfil.inscripcion.carrera.id)
                    template = get_template("adm_secretaria/modales/subircertificado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'subircronograma':
                try:
                    data['title'] = u'Subir archivo de certificado personalizado'
                    data['action'] = 'subircronograma'
                    data['id'] = id = int(request.GET['id'])
                    form = SubirCronogramaTitulacionForm()
                    data['form2'] = form
                    template = get_template("adm_secretaria/modales/subircertificado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'aprobarrechazar':
                try:
                    data['title'] = u'Aprobar/Rechazar informe técnico de pertinecia'
                    data['action'] = 'aprobarrechazar'
                    data['id'] = id = int(request.GET['id'])
                    data['eSolicitud'] = Solicitud.objects.get(status=True, pk=id)
                    es_director = False
                    if 'clave' in request.GET and request.GET['clave'] == 'homolog':
                        data['clave'] = request.GET['clave']

                        if 'DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                            es_director = True
                        elif 'DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                            es_director = True
                        elif 'DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                            es_director = True
                    data['es_director'] = es_director
                    form = AprobarRechazarInformePertinenciaForm()
                    data['form2'] = form
                    template = get_template("adm_secretaria/modales/subircertificado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'revisarinforme':
                try:
                    data['title'] = u'Aprobar/Rechazar informe técnico de pertinecia'
                    data['action'] = 'revisarinforme'
                    data['id'] = id = int(request.GET['id'])
                    form = AprobarRechazarInformePertinenciaForm()
                    data['form2'] = form
                    template = get_template("adm_secretaria/modales/subircertificado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'revisarcronograma':
                try:
                    data['title'] = u'Aprobar/Rechazar cronograma de titulación'
                    data['action'] = 'revisarcronograma'
                    data['id'] = id = int(request.GET['id'])
                    form = AprobarRechazarInformePertinenciaForm()
                    data['form2'] = form
                    template = get_template("adm_secretaria/modales/subircertificado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'aprobarrechazarcronograma':
                try:
                    data['title'] = u'Aprobar/Rechazar cronograma de titulación'
                    data['action'] = 'aprobarrechazarcronograma'
                    data['id'] = id = int(request.GET['id'])
                    form = AprobarRechazarInformePertinenciaForm()
                    data['form2'] = form
                    template = get_template("adm_secretaria/modales/subircertificado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'notificarcronograma':
                try:
                    data['title'] = u'Aprobar/Rechazar informe técnico de pertinecia'
                    data['action'] = 'notificarcronograma'
                    data['id'] = id = int(request.GET['id'])
                    form = NotificarCronogramaTitulacionForm()
                    data['form2'] = form
                    template = get_template("adm_secretaria/modales/subircertificado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'firmarcertificadomasivo':
                try:
                    ids = None

                    if 'ids' in request.GET:
                        ids = request.GET['ids']

                    leadsselect = ids
                    data['listadoseleccion'] = leadsselect

                    template = get_template("adm_secretaria/firmarcertificados.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    mensaje = 'Intentelo más tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            elif action == 'firmarcertificadoindividual':
                try:
                    id = None
                    if 'id' in request.GET:
                        id = int(request.GET['id'])
                    data['eSolicitud'] = Solicitud.objects.get(status=True, pk=id)
                    data['valor'] = 1
                    template = get_template("adm_secretaria/firmarcertificados.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    mensaje = 'Intentelo más tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            elif action == 'fichahomologacion':
                try:
                    data['title'] = u'Ficha de homologación interna Posgrado'
                    eSolicitud = Solicitud.objects.get(pk=int(request.GET['ids']))

                    data['s'] = request.GET.get('s', '')
                    data['idc'] = request.GET.get('idc', '0')
                    data['ide'] = request.GET.get('ide', '0')

                    if HistorialSolicitud.objects.filter(status=True, solicitud=eSolicitud, estado=12).exists():
                        tieneinformeaprobado = 'SI'
                    else:
                        tieneinformeaprobado = 'NO'
                    eInscripcionHo = Inscripcion.objects.get(status=True, carrera=eSolicitud.carrera_homologada, persona=eSolicitud.perfil.persona)
                    eInscripcionMallaHo = InscripcionMalla.objects.get(status=True, inscripcion=eInscripcionHo)
                    eAsignaturasMallaHo = AsignaturaMalla.objects.filter(status=True, malla=eInscripcionMallaHo.malla)

                    eInscripcionNew = Inscripcion.objects.get(status=True, carrera=eSolicitud.perfil.inscripcion.carrera, persona=eSolicitud.perfil.persona)
                    eInscripcionMallaNew = InscripcionMalla.objects.get(status=True, inscripcion=eInscripcionNew)
                    eAsignaturasMallaNew = AsignaturaMalla.objects.filter(status=True, malla=eInscripcionMallaNew.malla)

                    eSolicitudesAsignatura = SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud, record__isnull=False)
                    eRecordsLi = []
                    c = id = 0
                    eSolicitudA = eSolicitudB = eSolicitudC = None
                    tienefavorable = 0
                    for eAsignaturaHo in eAsignaturasMallaHo:
                        eRecord = eSolicitud.record_academia(eAsignaturaHo)

                        eRecordsLi.append({
                            "id": eAsignaturaHo.id,
                            "asignatura": eRecord.asignaturamalla.asignatura.nombre if eRecord is not None else eAsignaturaHo.asignatura.nombre,
                            "nota": eRecord.nota if eRecord is not None else 0,
                            "horas": eRecord.horas if eRecord is not None else eAsignaturaHo.horas,
                            "creditos": eRecord.creditos if eRecord is not None else eAsignaturaHo.creditos,
                            "asignatura2": '',
                            "nota2": 0,
                            "horas2": 0,
                            "creditos2": 0,
                            "color": '',
                            "porcentaje": 0,
                            "color2": '',
                            "colorfont": '',
                            "nos": '',
                            "orden": 0,
                            "solasi": None,
                            "idasih": 0
                        })

                    for eSolicitudAsignatura in eSolicitudesAsignatura:
                        for eRecordLi in eRecordsLi:
                            if eRecordLi['id'] == eSolicitudAsignatura.record.asignaturamalla.id:
                                eRecordLi['asignatura2'] = eSolicitudAsignatura.asignaturamalla.asignatura.nombre
                                eRecordLi['nota2'] = eSolicitudAsignatura.record.nota
                                eRecordLi['horas2'] = eSolicitudAsignatura.record.horas
                                eRecordLi['creditos2'] = eSolicitudAsignatura.record.creditos
                                eRecordLi['porcentaje'] = 100
                                eRecordLi['orden'] = 3
                                eRecordLi['idasih'] = eSolicitudAsignatura.asignaturamalla.id
                                eRecordLi['solasi'] = eSolicitudAsignatura
                                if eSolicitudAsignatura.estado == 4:
                                    eRecordLi['color'] = '#FE9900'
                                    eRecordLi['color2'] = '#FE9900'
                                    eRecordLi['colorfont'] = 'white'
                                    eRecordLi['nos'] = 'no'
                                    tienefavorable = 1
                                else:
                                    eRecordLi['color'] = '#198754'
                                    eRecordLi['color2'] = '#124076'
                                    eRecordLi['colorfont'] = 'white'
                                    tienefavorable = 1

                    valores_id_sin_cero = [diccionario["idasih"] for diccionario in eRecordsLi if diccionario["idasih"] != 0]

                    diccionarios_con_id_cero = [diccionario for diccionario in eRecordsLi if diccionario["idasih"] == 0]

                    c = 0
                    for eRecordLi in diccionarios_con_id_cero:
                        if c <= eAsignaturasMallaNew.exclude(id__in=valores_id_sin_cero).distinct().count() - 1:
                            eSolicitudAsignatura2 = eAsignaturasMallaNew.exclude(id__in=valores_id_sin_cero)[c]
                            eRecordLi['asignatura2'] = eSolicitudAsignatura2.asignatura.nombre
                            eRecordLi['nota2'] = 0
                            eRecordLi['horas2'] = eSolicitudAsignatura2.horas
                            eRecordLi['creditos2'] = eSolicitudAsignatura2.creditos
                            eRecordLi['porcentaje'] = 0
                            eRecordLi['orden'] = 0
                            eRecordLi['idasih'] = eSolicitudAsignatura2.id
                            if eSolicitud.solicitud_asignatura(eSolicitudAsignatura2.asignatura):
                                eRecordLi['color'] = '#124076'
                                eRecordLi['color2'] = '#124076'
                                eRecordLi['colorfont'] = 'white'
                                eRecordLi['orden'] = 1

                            c += 1

                    valores_id_sin_cero2 = [diccionario["idasih"] for diccionario in eRecordsLi if diccionario["idasih"] != 0]

                    if eAsignaturasMallaNew.exclude(id__in=valores_id_sin_cero2).distinct().count() > 0:
                        for eAsignatura3 in eAsignaturasMallaNew.exclude(id__in=valores_id_sin_cero2).distinct():
                            eRecordsLi.append({
                                "id": '',
                                "asignatura": '',
                                "nota": '',
                                "horas": '',
                                "creditos": '',
                                "asignatura2": eAsignatura3.asignatura.nombre,
                                "nota2": 0,
                                "horas2": eAsignatura3.horas,
                                "creditos2": eAsignatura3.creditos,
                                "color": '',
                                "porcentaje": 0,
                                "color2": '',
                                "colorfont": '',
                                "nos": '',
                                "orden": 0,
                                "solasi": None,
                                "idasih": 0
                            })

                    eRecordsLi_ordenada = sorted(eRecordsLi, key=lambda x: x["orden"], reverse=True)
                    data['eRecords'] = eRecordsLi_ordenada
                    data['eSolicitud'] = eSolicitud
                    data['tienefavorable'] = tienefavorable
                    subjects = None
                    favorables = SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud, estado=2)
                    if favorables.exists():
                        subjects = '<ul>'
                        for favorable in favorables:
                            subjects += f'<li>{favorable.asignaturamalla.asignatura.nombre}</li>'
                        subjects = subjects + '</ul>'
                    data['subjects'] = subjects

                    data['eTotalasignaturaspa'] = SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud).distinct().count()
                    data['eTotalasignaturasap'] = SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud, estado=2).distinct().count()

                    data['eTotalhoraspa'] = null_to_decimal(SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud).distinct().aggregate(horas=Sum('asignaturamalla__horas'))['horas'], 0)
                    data['eTotalhorasap'] = null_to_decimal(SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud, estado=2).distinct().aggregate(horas=Sum('horas'))['horas'], 0)

                    data['eTotalcreditospa'] = null_to_decimal(SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud).distinct().aggregate(creditos=Sum('asignaturamalla__creditos'))['creditos'], 0)
                    data['eTotalcreditosap'] = null_to_decimal(SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud, estado=2).distinct().aggregate(creditos=Sum('creditos'))['creditos'], 0)
                    data['tieneinformeaprobado'] = tieneinformeaprobado
                    return render(request, "adm_secretaria/fichahomologacion.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'descargarfichahomologacion':
                try:
                    __author__ = 'Unemi'

                    eSolicitud = Solicitud.objects.get(status=True, id=int(request.GET['id']))
                    ruta = f'{SITE_STORAGE}/static/logos/logo_posgrado_mailing.png'
                    ruta = ruta.replace('\\', '/')

                    directory = os.path.join(MEDIA_ROOT, 'reportes', 'fichas_homologacion')
                    try:
                        os.stat(directory)
                    except:
                        os.mkdir(directory)
                    nombre_archivo = f'Ficha_homologacion_{eSolicitud.codigo}.xlsx'
                    directory = os.path.join(MEDIA_ROOT, 'reportes', 'fichas_homologacion', nombre_archivo)

                    workbook = xlsxwriter.Workbook(directory)
                    ws = workbook.add_worksheet('fichas')
                    ws.set_column(0, 0, 5)
                    ws.set_row(20, 30)
                    ws.set_row(21, 50)

                    ws.set_row(22, 50)
                    ws.set_row(23, 50)
                    ws.set_row(24, 50)
                    ws.set_row(25, 50)
                    ws.set_row(26, 50)
                    ws.set_row(27, 50)
                    ws.set_row(28, 50)
                    ws.set_row(29, 50)
                    ws.set_row(30, 50)
                    ws.set_row(31, 50)

                    ws.set_column(1, 1, 17)
                    ws.set_column(2, 2, 14)
                    ws.set_column(3, 3, 10)
                    ws.set_column(4, 4, 12)
                    ws.set_column(5, 5, 5)
                    ws.set_column(6, 6, 17)
                    ws.set_column(7, 7, 14)
                    ws.set_column(8, 8, 10)
                    ws.set_column(9, 9, 12)
                    ws.set_column(10, 10, 10)
                    ws.set_column(11, 11, 7)
                    ws.set_column(12, 12, 7)
                    ws.set_column(13, 13, 10)

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#A6A6A6', 'font_color': 'black', 'font_size': 6, 'font_name': 'Times New Roman', 'valign': 'vcenter'})

                    formatoceldacab4 = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'text_wrap': True, 'font_color': 'black', 'font_size': 11, 'font_name': 'Times New Roman', 'valign': 'vcenter'})

                    formatoceldacab5 = workbook.add_format(
                        {'align': 'right', 'bold': 1, 'text_wrap': True, 'font_color': 'black', 'font_size': 11, 'font_name': 'Times New Roman', 'valign': 'vcenter'})

                    formatoceldacab6 = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 2, 'text_wrap': True, 'font_color': 'black', 'font_size': 11, 'font_name': 'Times New Roman', 'valign': 'vcenter'})

                    formatoceldacab7 = workbook.add_format(
                        {'align': 'left', 'bold': 1, 'text_wrap': True, 'font_color': 'black', 'font_size': 11, 'font_name': 'Times New Roman', 'valign': 'vcenter'})

                    formatoceldacab8 = workbook.add_format(
                        {'align': 'left', 'text_wrap': True, 'font_color': 'black', 'font_size': 11, 'font_name': 'Times New Roman', 'valign': 'vcenter'})

                    formatoceldacab9 = workbook.add_format(
                        {'align': 'left', 'bold': 1, 'text_wrap': True, 'font_color': 'black', 'font_size': 10, 'font_name': 'Times New Roman', 'valign': 'vcenter'})

                    formatoceldacab10 = workbook.add_format(
                        {'align': 'left', 'text_wrap': True, 'font_color': 'black', 'font_size': 10, 'font_name': 'Times New Roman', 'valign': 'vcenter'})

                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 6, 'font_name': 'Times New Roman'})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'font_size': 6, 'font_name': 'Times New Roman'})

                    formatoceldaleft2 = workbook.add_format(
                        {'text_wrap': True, 'bold': 1, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 6, 'font_name': 'Times New Roman', 'fg_color': '#A6A6A6'})

                    ws.insert_image('A1', ruta, {'x_scale': 25 / 100, 'y_scale': 25 / 100})

                    ws.merge_range('A5:N5', 'UNIVERSIDAD ESTATAL DE MILAGRO', formatoceldacab4)
                    ws.merge_range('A6:N6', 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADO', formatoceldacab4)
                    ws.merge_range('A7:N7', 'DIRECCIÓN DE POSGRADO', formatoceldacab4)
                    ws.merge_range('A8:N8', 'RECONOCIMIENTO U HOMOLOGACIÓN DE ESTUDIOS', formatoceldacab4)
                    ws.merge_range('A9:N9', 'FICHA COMPARATIVA INTERNA', formatoceldacab4)

                    ws.merge_range('K10:M10', f'CÓDIGO', formatoceldacab5)
                    ws.write('N10', eSolicitud.id, formatoceldacab6)

                    ws.merge_range('A12:C12', f'NOMBRE DEL ESTUDIANTE: ', formatoceldacab7)
                    ws.merge_range('D12:N12', f'{eSolicitud.perfil.persona}', formatoceldacab8)
                    ws.merge_range('A13:B13', f'CÉDULA: ', formatoceldacab7)
                    ws.merge_range('C13:N13', f'{eSolicitud.perfil.persona.cedula}', formatoceldacab8)
                    ws.merge_range('A14:F14', f'PROGRAMA DE MAESTRÍA/UNIVERSIDAD DE PROCEDENCIA: ', formatoceldacab7)
                    ws.merge_range('G14:N14', f'{nombre_carrera_pos(eSolicitud.carrera_homologada)}/ UNEMI', formatoceldacab8)
                    ws.merge_range('A15:D15', f'PLAN DE ESTUDIO DE PROCEDENCIA: ', formatoceldacab7)
                    ws.merge_range('E15:N15', f'{nombre_carrera_pos(eSolicitud.carrera_homologada)}', formatoceldacab8)
                    ws.merge_range('A16:D16', f'PLAN DE ESTUDIO A HOMOLOGAR: ', formatoceldacab7)
                    ws.merge_range('E16:N16', f'{nombre_carrera_pos(eSolicitud.perfil.inscripcion.carrera)}', formatoceldacab8)
                    ws.merge_range('A17:B17', f'MODALIDAD: ', formatoceldacab7)
                    ws.merge_range('C17:N17', f'{eSolicitud.perfil.inscripcion.carrera.get_modalidad_display()}', formatoceldacab8)

                    ws.merge_range('H19:N19', f'FECHA DE RECEPCIÓN: {eSolicitud.fecha_recepcion()}', formatoceldacab7)

                    ws.merge_range('A21:A22', 'No.', formatoceldacab)
                    ws.merge_range('B21:E21', f'{nombre_carrera_pos(eSolicitud.carrera_homologada)}', formatoceldacab)
                    ws.write('B22', 'ASIGNATURAS', formatoceldacab)
                    ws.write('C22', 'CALIFICACIÓN', formatoceldacab)
                    ws.write('D22', 'HORAS', formatoceldacab)
                    ws.write('E22', 'CRÉDITOS', formatoceldacab)
                    ws.merge_range('F21:F22', 'No.', formatoceldacab)
                    ws.merge_range('G21:J21', f'{nombre_carrera_pos(eSolicitud.perfil.inscripcion.carrera)}', formatoceldacab)
                    ws.write('G22', 'ASIGNATURAS', formatoceldacab)
                    ws.write('H22', 'CALIFICACIÓN', formatoceldacab)
                    ws.write('I22', 'HORAS', formatoceldacab)
                    ws.write('J22', 'CRÉDITOS', formatoceldacab)
                    ws.merge_range('K21:K22', '% COMPARATIVO DE CONTENIDOS (SIMILITUD)', formatoceldacab)
                    ws.merge_range('L21:M21', '% SE ACEPTA ASIGNATURA', formatoceldacab)
                    ws.write('L22', 'SI', formatoceldacab)
                    ws.write('M22', 'NO', formatoceldacab)
                    ws.merge_range('N21:N22', '% ABREVIACIÓN HOM', formatoceldacab)

                    filas_recorridas = 23
                    cont = 1

                    eTotalasignaturaspa = SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud).distinct().count()
                    eTotalasignaturasap = SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud, estado=2).distinct().count()

                    eTotalhoraspa = null_to_decimal(SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud).distinct().aggregate(horas=Sum('asignaturamalla__horas'))['horas'], 0)
                    eTotalhorasap = null_to_decimal(SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud, estado=2).distinct().aggregate(horas=Sum('horas'))['horas'], 0)

                    eTotalcreditospa = null_to_decimal(SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud).distinct().aggregate(creditos=Sum('asignaturamalla__creditos'))['creditos'], 0)
                    eTotalcreditosap = null_to_decimal(SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud, estado=2).distinct().aggregate(creditos=Sum('creditos'))['creditos'], 0)

                    for eRecord in eSolicitud.ficha_homologacion():
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft2)
                        ws.write('B%s' % filas_recorridas, str(eRecord['asignatura']), formatoceldaleft3)
                        ws.write('C%s' % filas_recorridas, str(eRecord['nota']), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(eRecord['horas']), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(eRecord['creditos']), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(cont), formatoceldaleft2)
                        ws.write('G%s' % filas_recorridas, str(eRecord['asignatura2']), formatoceldaleft3)
                        ws.write('H%s' % filas_recorridas, str(eRecord['nota2']), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(eRecord['horas2']), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(eRecord['creditos2']), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str(eRecord['porcentaje'])+ '%', formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, str('X' if eRecord['porcentaje'] == 100 else ''), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str('X' if eRecord['porcentaje'] == 0 else ''), formatoceldaleft)
                        ws.write('N%s' % filas_recorridas, str('HOM'), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1

                    ws.merge_range(f'B{filas_recorridas + 1}:E{filas_recorridas + 1}', 'No. DE ASIGNATURAS POR APROBAR: ', formatoceldacab9)
                    ws.write(f'F{filas_recorridas + 1}', eTotalasignaturaspa, formatoceldacab10)
                    ws.merge_range(f'B{filas_recorridas + 2}:E{filas_recorridas + 2}', 'TOTAL HORAS POR HOMOLOGAR: ', formatoceldacab9)
                    ws.write(f'F{filas_recorridas + 2}', eTotalhoraspa, formatoceldacab10)
                    ws.merge_range(f'B{filas_recorridas + 3}:E{filas_recorridas + 3}', 'TOTAL CRÉDITOS POR HOMOLOGAR: ', formatoceldacab9)
                    ws.write(f'F{filas_recorridas + 3}', eTotalcreditospa, formatoceldacab10)

                    ws.merge_range(f'G{filas_recorridas + 1}:J{filas_recorridas + 1}', 'No. DE ASIGNATURAS APROBADAS: ', formatoceldacab9)
                    ws.write(f'K{filas_recorridas + 1}', eTotalasignaturasap, formatoceldacab10)
                    ws.merge_range(f'G{filas_recorridas + 2}:J{filas_recorridas + 2}', 'TOTAL HORAS HOMOLOGADAS: ', formatoceldacab9)
                    ws.write(f'K{filas_recorridas + 2}', eTotalhorasap, formatoceldacab10)
                    ws.merge_range(f'G{filas_recorridas + 3}:J{filas_recorridas + 3}', 'TOTAL CRÉDITOS HOMOLOGADOS: ', formatoceldacab9)
                    ws.write(f'K{filas_recorridas + 3}', eTotalcreditosap, formatoceldacab10)

                    ws.merge_range(f'A{filas_recorridas + 4}:B{filas_recorridas + 4}', 'OBSERVACIÓN: ', formatoceldacab9)

                    ws.merge_range(f'H{filas_recorridas + 11}:N{filas_recorridas + 11}', f'FECHA DE REVISIÓN: {eSolicitud.fecha_revision()}', formatoceldacab9)

                    ws.merge_range(f'A{filas_recorridas + 13}:B{filas_recorridas + 13}', 'REALIZADA POR: ', formatoceldacab9)
                    ws.merge_range(f'C{filas_recorridas + 13}:F{filas_recorridas + 13}', eSolicitud.inscripcioncohorte.cohortes.coordinador.__str__(), formatoceldacab10)
                    ws.merge_range(f'A{filas_recorridas + 14}:B{filas_recorridas + 14}', 'APROBADA POR: ', formatoceldacab9)
                    ws.merge_range(f'C{filas_recorridas + 14}:F{filas_recorridas + 14}', eSolicitud.director_escuela(), formatoceldacab10)

                    workbook.close()
                    ruta = "{}reportes/fichas_homologacion/{}".format(MEDIA_URL, nombre_archivo)
                    if not eSolicitud.ficha:
                        eSolicitud.ficha = ruta
                        eSolicitud.save(request)
                    return JsonResponse({"result": 'ok', "mensaje": u"Ficha generada", "url": ruta})
                except Exception as ex:
                    pass

            elif action == 'firmarinformehomologacion':
                try:
                    eSolicitud = Solicitud.objects.get(status=True, pk=int(encrypt_id(request.GET['id'])))

                    ePrograma = ProgramaPac.objects.get(status=True, carrera=eSolicitud.perfil.inscripcion.carrera)

                    if eSolicitud.carrera_homologada is None:
                        return JsonResponse({"result": "no",
                                             "mensaje": f"Por favor, seleccione la carrera comparativa del solicitante {eSolicitud.perfil.persona} para poder proceder con la generación del informe."})

                    if not eSolicitud.firmadoec:
                        return JsonResponse({"result": "no",
                                             "mensaje": f"Por favor, indicar a Secretaría técnica que realice la validación de la firma del archivo de solicitud del solicitante {eSolicitud.perfil.persona} para poder proceder con la generación del informe."})

                    if eSolicitud.tiene_informe():
                        if IntegrantesInformeHomologacion.objects.filter(status=True, informe=eSolicitud.tiene_informe(), persona=persona, firmado=True):
                            return JsonResponse({"result": "no",
                                                 "mensaje": f"Usted  ya ha firmado este informe de homologación."})


                    if not eSolicitud.tiene_informe_firmado():
                        nombredir = nombrecor = nombreasi = ''
                        cargodir = cargocor = cargoasi = ''
                        para = ''
                        cargopara = ''
                        objdir = objcor = objasi = objpara = None
                        if Departamento.objects.filter(status=True, pk=162).exists():
                            idper = Departamento.objects.get(status=True, pk=162).responsable
                            cargopara = DistributivoPersona.objects.get(status=True,
                                                                        persona=idper).denominacionpuesto.descripcion
                            para = idper.__str__()
                            objpara = idper

                        if eSolicitud.perfil.inscripcion.carrera.escuelaposgrado.id == 1:
                            if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                                dirsal = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                                                                               tipopersonadepartamento_id=10,
                                                                               departamento_id=216)
                                nombredir = dirsal.personadepartamento.__str__()
                                cargodir = dirsal.tipopersonadepartamento
                                objdir = dirsal.personadepartamento

                        elif eSolicitud.perfil.inscripcion.carrera.escuelaposgrado.id == 2:
                            if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                                diredu = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                                                                               tipopersonadepartamento_id=9,
                                                                               departamento_id=215)

                                nombredir = diredu.personadepartamento.__str__()
                                cargodir = diredu.tipopersonadepartamento
                                objdir = diredu.personadepartamento

                        elif eSolicitud.perfil.inscripcion.carrera.escuelaposgrado.id == 3:
                            if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                                dirneg = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                                                                               tipopersonadepartamento_id=11,
                                                                               departamento_id=163)
                                nombredir = dirneg.personadepartamento.__str__()
                                cargodir = dirneg.tipopersonadepartamento
                                objdir = dirneg.personadepartamento

                        nombrecor = eSolicitud.inscripcioncohorte.cohortes.coordinador.__str__()
                        cargocor = f'Coordinador del Programa de {eSolicitud.inscripcioncohorte.cohortes.maestriaadmision.carrera.nombre}'
                        objcor = eSolicitud.inscripcioncohorte.cohortes.coordinador

                        # if DistributivoPersona.objects.filter(status=True, persona=persona).exists():
                        #     cargoasi = DistributivoPersona.objects.get(status=True,
                        #                                                persona=persona).denominacionpuesto.descripcion
                        #     nombreasi = persona.__str__()
                        #     objasi = persona
                        if ContratoDip.objects.filter(status=True, persona=Persona.objects.get(id=variable_valor('ENCARGADA_ADMISION'), status=True),
                                                        fechainicio__lte=datetime.now().date(),
                                                        fechafin__gte=datetime.now().date()).exists():
                            cargoasi = ContratoDip.objects.filter(status=True, persona=Persona.objects.get(id=variable_valor('ENCARGADA_ADMISION'), status=True),
                                                                  fechainicio__lte=datetime.now().date(),
                                                                  fechafin__gte=datetime.now().date()).first().cargo.nombre
                            objasi = Persona.objects.get(id=variable_valor('ENCARGADA_ADMISION'), status=True)
                            nombreasi = objasi.__str__()
                        else:
                            cargoasi = ContratoDip.objects.filter(status=True, persona=persona).last().cargo.nombre
                            objasi = Persona.objects.get(id=variable_valor('ENCARGADA_ADMISION'), status=True)
                            nombreasi = objasi.__str__()

                        if not InformeHomologacionPosgrado.objects.filter(status=True, solicitud=eSolicitud).exists():
                            secuencia = secuencia_informehomologacion(request, datetime.now().date().year)
                            codigo = generar_codigo(secuencia, eSolicitud.perfil.inscripcion.carrera.alias)
                            informe = InformeHomologacionPosgrado(codigo=codigo,
                                                                  fechaemision=datetime.now().date(),
                                                                  para=objpara,
                                                                  de=objdir,
                                                                  solicitud=eSolicitud,
                                                                  estadorevision=1)
                            informe.save(request)
                            log(u'Generó informe de homologación interna : %s' % informe, request, "add")

                            integrante1 = IntegrantesInformeHomologacion(informe=informe,
                                                                         orden=1,
                                                                         persona=objcor,
                                                                         firmado=False,
                                                                         cargo=cargocor,
                                                                         responsabilidad='Elaborado por')

                            integrante1.save(request)
                            log(u'Adicionó coordinador para firma de informe de homologación interna: %s' % integrante1, request, "add")

                            integrante2 = IntegrantesInformeHomologacion(informe=informe,
                                                                         orden=2,
                                                                         persona=objasi,
                                                                         firmado=False,
                                                                         cargo=cargoasi,
                                                                         responsabilidad='Revisado por')
                            integrante2.save(request)
                            log(u'Adicionó asistente para firma de informe de homologación interna: %s' % integrante2, request, "add")

                            integrante3 = IntegrantesInformeHomologacion(informe=informe,
                                                                         orden=3,
                                                                         persona=objdir,
                                                                         firmado=False,
                                                                         cargo=cargodir.nombre,
                                                                         responsabilidad='Aprobado por')
                            integrante3.save(request)
                            log(u'Adicionó director para firma de informe de homologación interna: %s' % integrante3,
                                request, "add")
                        else:
                            informe = InformeHomologacionPosgrado.objects.get(status=True, solicitud=eSolicitud)
                            integrantes = IntegrantesInformeHomologacion.objects.filter(status=True,
                                                                                        informe=informe).order_by('orden')

                            for integrante in integrantes:
                                if integrante.orden == 1:
                                    integrante.persona = objcor
                                    integrante.cargo = cargocor
                                    integrante.responsabilidad = 'Elaborado por'
                                    log(u'Editó coordinador para firma de informe de homologación interna: %s' % integrante,
                                        request, "edit")
                                elif integrante.orden == 2:
                                    integrante.persona = objasi
                                    integrante.cargo = cargoasi
                                    integrante.responsabilidad = 'Revisado por'
                                    log(u'Editó asistente para firma de informe de homologación interna: %s' % integrante,
                                        request, "edit")
                                elif integrante.orden == 3:
                                    integrante.persona = objdir
                                    integrante.cargo = cargodir.nombre
                                    integrante.responsabilidad = 'Aprobado por'
                                    log(u'Editó director para firma de informe de homologación interna: %s' % integrante,
                                        request, "edit")
                                integrante.save(request)

                        eInscripcionHo = Inscripcion.objects.get(status=True, carrera=eSolicitud.perfil.inscripcion.carrera,
                                                                 persona=eSolicitud.perfil.persona)
                        eInscripcionMallaHo = InscripcionMalla.objects.get(status=True, inscripcion=eInscripcionHo)
                        eAsignaturasMallaHo = AsignaturaMalla.objects.filter(status=True, malla=eInscripcionMallaHo.malla)

                        idasif = []
                        for eAsignaturaHo in eAsignaturasMallaHo:
                            eRecord = eSolicitud.record_academia(eAsignaturaHo)
                            if eRecord is not None:
                                idasif.append(eAsignaturaHo.id)
                        data['eAsignaturasMalla'] = AsignaturaMalla.objects.filter(status=True, id__in=idasif)
                        data['eInforme'] = informe
                        data['nombredir'] = nombredir
                        data['nombrecor'] = nombrecor
                        data['nombreasi'] = nombreasi
                        data['cargodir'] = cargodir
                        data['cargocor'] = cargocor
                        data['cargoasi'] = cargoasi
                        data['para'] = para
                        data['cargopara'] = cargopara
                        data['objdir'] = objdir
                        data['objcor'] = objcor
                        data['objasi'] = objasi
                        data['objpara'] = objpara
                        data['carreragraduado'] = nombre_carrera_pos2(eSolicitud.carrera_homologada)
                        data['carreraahomologar'] = nombre_carrera_pos2(eSolicitud.perfil.inscripcion.carrera)
                        data['ePrograma'] = ePrograma

                        data['fechaOcas'] = fechaletra_corta2(ePrograma.fechaaprobacion)
                        data['fechaCes'] = fechaletra_corta3(ePrograma.fechaaprobacioncaces)
                        qrname = f'{eSolicitud.servicio.alias}_informehomologacion_{eSolicitud.id}'
                        directory = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'informetecnicohomologacion')
                        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'informetecnicohomologacion',
                                                           eSolicitud.servicio.alias))

                        try:
                            os.stat(directory)
                        except:
                            os.mkdir(directory)

                        rutapdf = folder + qrname + '.pdf'
                        if os.path.isfile(rutapdf):
                            os.remove(rutapdf)

                        imagenqr = 'qr' + qrname

                        conviert_html_to_pdfsavecontratomae(
                            'adm_secretaria/informehomoi.html',
                            {
                                'pagesize': 'A4',
                                'data': data,
                                'imprimeqr': True,
                                'qrname': imagenqr
                            }, qrname + '.pdf', 'informetecnicohomologacion'
                        )

                        qrresult = '/media/qrcode/informetecnicohomologacion/' + qrname + '.pdf'

                        url_archivo = (SITE_STORAGE + qrresult).replace('\\', '/')
                        url_archivo = (url_archivo).replace('//', '/')
                        _name = generar_nombre(f'informehomologacion_{informe.codigo}_', 'descargado')
                        folder = os.path.join(SITE_STORAGE, 'media', 'archivohomologaciondescargado', '')
                        if not os.path.exists(folder):
                            os.makedirs(folder)
                        folder_save = os.path.join('archivohomologaciondescargado', '').replace('\\', '/')
                        url_file_generado = f'{folder_save}{_name}.pdf'
                        ruta_creacion = SITE_STORAGE
                        ruta_creacion = ruta_creacion.replace('\\', '/')
                        shutil.copy(url_archivo, ruta_creacion + '/media/' + url_file_generado)

                        archivoho = url_file_generado

                        if not HistorialInformeHomologacion.objects.filter(status=True, informe=informe).exists():
                            history = HistorialInformeHomologacion(informe=informe,
                                                                   persona=persona,
                                                                   fecha=datetime.now().date(),
                                                                   hora=datetime.now().time(),
                                                                   observacion=f'Generó el informe de homologación interna de posgrado - solicitud {eSolicitud.codigo}',
                                                                   estadorevision=1,
                                                                   archivo=archivoho)
                            history.save(request)
                            log(u'Guardó historial informe de homologación interna descargado: %s' % informe, request, "add")

                            eSolicitud.estado = 11
                            eSolicitud.save(request)

                            historysoli = HistorialSolicitud(solicitud=eSolicitud,
                                                             observacion='Informe generado correctamente',
                                                             fecha=datetime.now().date(),
                                                             hora=datetime.now().time(),
                                                             estado=eSolicitud.estado,
                                                             responsable=persona,
                                                             archivo=archivoho)
                            historysoli.save(request)
                            log(u'Guardó historial general de la solicitud: %s' % historysoli, request, "add")

                            random_number = random.randint(1, 1000000)
                            data['id_objeto'] = informe.id
                            data['archivo'] = history.archivo.url
                            archivo = f"{history.archivo.url}?cache={random_number}"
                            data['url_archivo'] = '{}{}'.format(dominio_sistema, archivo)
                            data['action_firma'] = 'firmarinformehomologacion'
                        else:
                            informe = InformeHomologacionPosgrado.objects.get(status=True, solicitud=eSolicitud)

                            history = HistorialInformeHomologacion.objects.filter(status=True, informe=informe).last()
                            history.fecha = datetime.now().date()
                            history.hora = datetime.now().time()
                            history.responsable = persona
                            history.observacion = f'Generó el informe de homologación interna de posgrado - solicitud {eSolicitud.codigo}',
                            history.archivo = archivoho
                            history.save(request)
                            log(u'Guardó historial informe de homologación interna descargado: %s' % informe, request, "edit")

                            historysoli = HistorialSolicitud.objects.filter(status=True, solicitud=eSolicitud, estado=11).last()
                            historysoli.fecha = datetime.now().date()
                            historysoli.hora = datetime.now().time()
                            historysoli.responsable = persona
                            historysoli.observacion = f'Generó el informe de homologación interna de posgrado - solicitud {eSolicitud.codigo}',
                            historysoli.archivo = archivoho
                            historysoli.save(request)
                            log(u'Guardó historial de la solicitud: %s' % historysoli, request, "edit")

                            random_number = random.randint(1, 1000000)
                            data['id_objeto'] = informe.id
                            data['archivo'] = history.archivo.url
                            archivo = f"{history.archivo.url}?cache={random_number}"
                            data['url_archivo'] = '{}{}'.format(dominio_sistema, archivo)
                            data['action_firma'] = 'firmarinformehomologacion'
                    else:
                        informe = eSolicitud.tiene_informe()

                        random_number = random.randint(1, 1000000)
                        data['id_objeto'] = informe.id
                        data['archivo'] = informe.archivo_actual()
                        archivo = f"{informe.archivo_actual()}?cache={random_number}"
                        data['url_archivo'] = '{}{}'.format(dominio_sistema, archivo)
                        data['action_firma'] = 'firmarinformehomologacion'

                    template = get_template("formfirmaelectronica_posgrado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'reporteseguimientosolicitud':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)                    
                    ws = workbook.add_worksheet('seguimiento solicitudes')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 25)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 40)
                    ws.set_column(5, 5, 25)
                    ws.set_column(6, 6, 40)
                    ws.set_column(7, 7, 15)
                    ws.set_column(8, 8, 15)
                    ws.set_column(9, 9, 15)
                    ws.set_column(10, 10, 15)
                    ws.set_column(11, 11, 20)
                    ws.set_column(12, 12, 15)
                    ws.set_column(13, 13, 20)
                    ws.set_column(14, 14, 15)
                    ws.set_column(15, 15, 40)
                    ws.set_column(16, 16, 40)
                    ws.set_column(17, 17, 40)
                    ws.set_column(18, 18, 20)
                    ws.set_column(19, 19, 20)
                    ws.set_column(20, 20, 20)
                    ws.set_column(21, 21, 20)
                    ws.set_column(22, 22, 20)
                    ws.set_column(23, 23, 20)
                    ws.set_column(24, 24, 20)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    decimalformat2 = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    asesor = cohorte = 0
                    desde = hasta = ''
                    
                    eCategoria = CategoriaServicio.objects.get(pk=int(request.GET['id']))
                    
                    ws.merge_range('A1:Y1', f'Reporte seguimiento solicitudes de {eCategoria}', formatotitulo_filtros)

                    ws.write(2, 0, 'N°', formatoceldacab)
                    ws.write(2, 1, 'Código', formatoceldacab)
                    ws.write(2, 2, 'Servicio', formatoceldacab)
                    ws.write(2, 3, 'Cédula', formatoceldacab)
                    ws.write(2, 4, 'Solicitante', formatoceldacab)
                    ws.write(2, 5, 'Cohorte', formatoceldacab)
                    ws.write(2, 6, 'Maestría', formatoceldacab)
                    ws.write(2, 7, 'Fecha de solicitud', formatoceldacab)
                    ws.write(2, 8, '¿Rubro generado?', formatoceldacab)
                    ws.write(2, 9, 'Valor del rubro', formatoceldacab)
                    ws.write(2, 10, '¿Cancelado?', formatoceldacab)
                    ws.write(2, 11, 'Estado de la solicitud', formatoceldacab)
                    ws.write(2, 12, '¿Informe generado?', formatoceldacab)
                    ws.write(2, 13, 'Código Informe', formatoceldacab)
                    ws.write(2, 14, 'Fecha de emisión', formatoceldacab)
                    ws.write(2, 15, 'Coordinador', formatoceldacab)
                    ws.write(2, 16, 'Analista', formatoceldacab)
                    ws.write(2, 17, 'Director', formatoceldacab)
                    ws.write(2, 18, '¿Firmado por coordinador?', formatoceldacab)
                    ws.write(2, 19, 'Fecha firma coordinador', formatoceldacab)
                    ws.write(2, 20, '¿Firmado por analista?', formatoceldacab)
                    ws.write(2, 21, 'Fecha firma analista', formatoceldacab)
                    ws.write(2, 22, '¿Firmado por director?', formatoceldacab)
                    ws.write(2, 23, 'Fecha firma director', formatoceldacab)
                    ws.write(2, 24, 'Estado del informe', formatoceldacab)

                    filtros = Q(pk__gte=0, servicio__categoria__id=int(request.GET['id']))

                    if 'SOLO_TITULACION_EX' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                        if CohorteMaestria.objects.filter(status=True, coordinador=persona).exists():
                            idcarreras = CohorteMaestria.objects.filter(status=True, coordinador=persona).values_list('maestriaadmision__carrera__id', flat=True).order_by('maestriaadmision__carrera__id').distinct()
                            filtros = filtros & Q(perfil__inscripcion__carrera__id__in=idcarreras)
                    elif 'DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                        idcarreras = PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN').values_list('carrera_id', flat=True)
                        filtros = filtros & Q(perfil__inscripcion__carrera__id__in=idcarreras, estado__in=[11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 24, 25, 26, 27])
                    elif 'DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                        idcarreras = PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD').values_list('carrera_id', flat=True)
                        filtros = filtros & Q(perfil__inscripcion__carrera__id__in=idcarreras, estado__in=[11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 24, 25, 26, 27])
                    elif 'DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                        idcarreras = PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO').values_list('carrera_id', flat=True)
                        filtros = filtros & Q(perfil__inscripcion__carrera__id__in=idcarreras, estado__in=[11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 24, 25, 26, 27])

                    eSolicitudes = Solicitud.objects.filter(filtros).order_by('fecha')

                    filas_recorridas = 4
                    cont = 1
                    for eSolicitud in eSolicitudes:
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(eSolicitud.codigo), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(eSolicitud.servicio), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(eSolicitud.perfil.persona.cedula), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(eSolicitud.perfil.persona), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(eSolicitud.inscripcioncohorte.cohortes.descripcion), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(eSolicitud.inscripcioncohorte.cohortes.maestriaadmision.carrera), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(eSolicitud.fecha), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str('SI' if eSolicitud.tiene_rubro_generado() else 'NO'), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(Decimal(null_to_decimal(eSolicitud.servicio.costo)).quantize(Decimal('.01'))), decimalformat)
                        ws.write('K%s' % filas_recorridas, str('SI' if eSolicitud.tiene_rubro_generado() and eSolicitud.tiene_rubro_pagado() else 'NO'), formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, eSolicitud.get_estado_display(), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str('SI' if eSolicitud.tiene_informe() else 'NO'), formatoceldaleft)
                        ws.write('N%s' % filas_recorridas, str(eSolicitud.tiene_informe().codigo if eSolicitud.tiene_informe() else 'NO GENERADO'), formatoceldaleft)
                        ws.write('O%s' % filas_recorridas, str(eSolicitud.tiene_informe().fechaemision if eSolicitud.tiene_informe() else 'NO GENERADO'), formatoceldaleft)
                        ws.write('P%s' % filas_recorridas, str(eSolicitud.tiene_informe().coordinador().persona if eSolicitud.tiene_informe() else 'NO GENERADO'), formatoceldaleft)
                        ws.write('Q%s' % filas_recorridas, str(eSolicitud.tiene_informe().analista().persona if eSolicitud.tiene_informe() else 'NO GENERADO'), formatoceldaleft)
                        ws.write('R%s' % filas_recorridas, str(eSolicitud.tiene_informe().director().persona if eSolicitud.tiene_informe() else 'NO GENERADO'), formatoceldaleft)
                        ws.write('S%s' % filas_recorridas, str('SI' if eSolicitud.tiene_informe() and eSolicitud.tiene_informe().firmo_coordinador() else 'NO GENERADO'), formatoceldaleft)
                        ws.write('T%s' % filas_recorridas, str(eSolicitud.tiene_informe().ultima_historial_firma(1) if eSolicitud.tiene_informe() and eSolicitud.tiene_informe().firmo_coordinador() else 'NO GENERADO'), formatoceldaleft)
                        ws.write('U%s' % filas_recorridas, str('SI' if eSolicitud.tiene_informe() and eSolicitud.tiene_informe().firmo_analista() else 'NO GENERADO'), formatoceldaleft)
                        ws.write('V%s' % filas_recorridas, str(eSolicitud.tiene_informe().ultima_historial_firma(2) if eSolicitud.tiene_informe() and eSolicitud.tiene_informe().firmo_analista() else 'NO GENERADO'), formatoceldaleft)
                        ws.write('W%s' % filas_recorridas, str('SI' if eSolicitud.tiene_informe() and eSolicitud.tiene_informe().firmo_director() else 'NO GENERADO'), formatoceldaleft)
                        ws.write('X%s' % filas_recorridas, str(eSolicitud.tiene_informe().ultima_historial_firma(3) if eSolicitud.tiene_informe() and eSolicitud.tiene_informe().firmo_director() else 'NO GENERADO'), formatoceldaleft)
                        ws.write('Y%s' % filas_recorridas, str(eSolicitud.tiene_informe().get_estadorevision_display() if eSolicitud.tiene_informe() else 'NO GENERADO'), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1
                        print(f"{cont}/{eSolicitudes.count()}")
                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'Seguimiento_solicitudes_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,

                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'carga_carreras':
                try:
                    lista = []

                    eSolicitudes = Solicitud.objects.filter(status=True, servicio__categoria__id=int(request.GET['id']))
                    carreras = Carrera.objects.filter(status=True,
                                                      id__in=eSolicitudes.values_list('perfil__inscripcion__carrera__id', flat=True).order_by('perfil__inscripcion__carrera__id').distinct())

                    for carrera in carreras:
                        if not buscar_dicc(lista, 'id', carrera.id):
                            lista.append({'id': carrera.id, 'nombre': f'{carrera.__str__()}'})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'carga_estados':
                try:
                    lista = []

                    eSolicitudes = Solicitud.objects.filter(status=True, servicio__categoria__id=int(request.GET['id'])).values_list('estado', flat=True).order_by('estado').distinct()

                    for eEstado in eSolicitudes:
                        if not buscar_dicc(lista, 'id', eEstado):
                            lista.append({'id': eEstado, 'nombre': f'{dict(ESTADO_SOLICITUD)[eEstado]}'})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'reporteseguimientoceritificado':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('seguimiento_certificados')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 40)
                    ws.set_column(3, 3, 35)
                    ws.set_column(4, 4, 20)
                    ws.set_column(5, 5, 25)
                    ws.set_column(6, 6, 20)
                    ws.set_column(7, 7, 20)
                    ws.set_column(8, 8, 20)
                    ws.set_column(9, 9, 20)
                    ws.set_column(10, 10, 20)
                    ws.set_column(11, 11, 20)
                    ws.set_column(12, 12, 20)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    decimalformat2 = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    asesor = cohorte = 0
                    desde = hasta = ''

                    eCategoria = CategoriaServicio.objects.get(pk=int(request.GET['id']))

                    carrera = estado = 0
                    desde = hasta = ''

                    if 'carrera' in request.GET:
                        carrera = request.GET['carrera']

                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    if 'estado' in request.GET:
                        estado = request.GET['estado']

                    ws.merge_range('A1:M1', f'Reporte seguimiento solicitudes de {eCategoria}', formatotitulo_filtros)

                    ws.write(2, 0, 'N°', formatoceldacab)
                    ws.write(2, 1, 'Cédula', formatoceldacab)
                    ws.write(2, 2, 'Apellidos y Nombres', formatoceldacab)
                    ws.write(2, 3, 'Programa de maestría', formatoceldacab)
                    ws.write(2, 4, 'Cohorte - Año', formatoceldacab)
                    ws.write(2, 5, 'Procedimiento', formatoceldacab)
                    ws.write(2, 6, 'Fecha de solicitud', formatoceldacab)
                    ws.write(2, 7, 'Solicitud', formatoceldacab)
                    ws.write(2, 8, 'Entregado', formatoceldacab)
                    ws.write(2, 9, 'Solicitud - SGA', formatoceldacab)
                    ws.write(2, 10, 'Rubro', formatoceldacab)
                    ws.write(2, 11, 'Estado', formatoceldacab)
                    ws.write(2, 12, 'Observaciones', formatoceldacab)

                    filtro = Q(pk__gte=0, servicio__categoria__id=int(request.GET['id']))

                    if carrera != "":
                        if eval(request.GET['carrera'])[0] != "0":
                            filtro = filtro & Q(perfil__inscripcion__carrera__id__in=eval(request.GET['carrera']))

                    if estado != "":
                        estado = int(estado)
                        if estado > 0:
                            filtro = filtro & Q(estado=estado)

                    if desde and hasta:
                        filtro = filtro & Q(fecha__range=(desde, hasta))
                    elif desde:
                        filtro = filtro & Q(fecha__gte=desde)
                    elif hasta:
                        filtro = filtro & Q(fecha__lte=hasta)

                    eSolicitudes = Solicitud.objects.filter(filtro).order_by('-fecha')

                    filas_recorridas = 4
                    cont = 1
                    for eSolicitud in eSolicitudes:
                        cohorte = ''
                        eIns = InscripcionCohorte.objects.filter(status=True, inscripcion=eSolicitud.perfil.inscripcion).order_by('id').first()
                        if eIns:
                            cohorte = eIns.cohortes.descripcion

                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(eSolicitud.perfil.persona.cedula), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(eSolicitud.perfil.persona), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(eSolicitud.perfil.inscripcion.carrera), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(cohorte), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(eSolicitud.certificado_solicitado().certificacion), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, f'{eSolicitud.fecha}', formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str('RECIBIDA'), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str('ENTREGADO' if eSolicitud.estado == 2 else 'NO ENTREGADO'), decimalformat)
                        ws.write('J%s' % filas_recorridas, str('EN SISTEMA'), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str('PAGADO' if eSolicitud.tiene_rubro_pagado() else 'PENDIENTE DE PAGO'), formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, str(eSolicitud.get_estado_display()), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str(eSolicitud.primer_historial().observacion), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1
                        print(f"{cont}/{eSolicitudes.count()}")
                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'Seguimiento_certificados_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,

                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Gestión de categorías de servicios'
                search = None
                if persona.usuario.is_superuser:
                    filtros = Q(status=True, pk__gte=0)
                elif 'SOLICITUDES_ALL' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                    filtros = Q(status=True, id__in=[1, 4, 5])
                elif 'DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                    filtros = Q(status=True, id__in=[6, 7])
                elif 'DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                    filtros = Q(status=True, id__in=[6, 7])
                elif 'DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                    filtros = Q(status=True, id__in=[6, 7])
                elif persona.coordinacion_pertenece() == 7:
                    if 'SOLO_TITULACION_EX' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                        filtros = Q(status=True, id__in=[6, 7])
                    else:
                        filtros = Q(status=True, pk__gte=0, roles=3)
                elif any(y in [434, 435, 436, 437, 438] for y in persona.usuario.groups.all().distinct().values_list('id', flat=True)):
                    filtros = Q(status=True, pk=4)
                elif 'SOLICITUDES_NIVELACION' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                    filtros = Q(status=True, pk=5)
                else:
                    filtros = Q(status=True, pk__gte=0, roles__in=[1,2])

                url_vars = ' '
                ids = 0

                if 's' in request.GET:
                    search = request.GET['s']

                if 'ids' in request.GET:
                    ids = int(request.GET['ids'])

                if search:
                    data['search'] = search
                    filtros = filtros & (Q(nombre__icontains=search)| Q(descripcion__icontains=search))
                    url_vars += "&s={}".format(search)

                if ids:
                    data['ids'] = ids
                    filtros = filtros & (Q(roles=ids))
                    url_vars += "&ids={}".format(search)

                categorias = CategoriaServicio.objects.filter(filtros).order_by('nombre')

                paging = MiPaginador(categorias, 20)
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
                data['page'] = page
                data['rangospaging'] = paging.rangos_paginado(p)
                data['categorias'] = page.object_list
                data['s'] = search if search else ""
                data['url_vars'] = url_vars
                return render(request, "adm_secretaria/view.html", data)
            except Exception as ex:
                HttpResponseRedirect(f"/?info={ex.__str__()}")
