# -*- coding: UTF-8 -*-
import io
import json
import os
from math import ceil

import PyPDF2
from datetime import time, datetime
from decimal import Decimal
import time as ET

import requests
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import time as pausaparaemail

from fitz import fitz
from xlwt import easyxf, XFStyle, Workbook
from django.core.files import File as DjangoFile
import random

from core.firmar_documentos import firmar
from decorators import secure_module
from investigacion.forms import GrupoInvestigacionForm, FinanciamientoPonenciaForm, PostulacionObraRelevanciaForm, SolicitudRegArticuloPubForm, SolicitudRegPonenciaPubForm, \
    SolicitudRegLibroPubForm, SolicitudRegCapituloLibroPubForm, SolicitudRegProceedingPubForm
from investigacion.funciones import analista_investigacion, tecnico_investigacion
from investigacion.models import GrupoInvestigacion, FUNCION_INTEGRANTE_GRUPO_INVESTIGACION, GrupoInvestigacionIntegrante, ConvocatoriaObraRelevancia, ObraRelevancia, TIPO_FILIACION, ObraRelevanciaParticipante, ObraRelevanciaRecorrido, EvaluacionObraRelevancia, EvaluacionObraRelevanciaDetalle, TIPO_INTEGRANTE_PUBLICACION_F, TIPO_FILIACION_PUBLICACION_F, TIPO_PERSONA_PUBLICACION_F
from sagest.commonviews import obtener_estado_solicitud
from sagest.models import SolicitudPublicacion, ParticipanteSolicitudPublicacion
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.forms import PlanificarPonenciasForm
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, generar_nombre, email_valido, \
    validar_archivo, null_to_decimal, cuenta_email_disponible_para_envio, fechaletra_corta, fecha_letra_rango
from sga.funcionesxhtml2pdf import convert_html_to_pdf
from sga.models import CUENTAS_CORREOS, Persona, PlanificarPonencias, ConvocatoriaPonencia, CriterioPonencia, PlanificarPonenciasCriterio, PlanificarPonenciasRecorrido, MESES_CHOICES, Externo, Profesor, AreaConocimientoTitulacion, Titulacion, InstitucionEducacionSuperior, Pais, Titulo, PonenciasInvestigacion, LibroInvestigacion, CapituloLibroInvestigacion, ArticuloInvestigacion, Evidencia, Administrativo, Inscripcion
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
    es_administrativo = perfilprincipal.es_administrativo()

    if not es_profesor and not es_administrativo:
        return HttpResponseRedirect("/?info=El Módulo está disponible para profesores y administrativos.")

    data['profesor'] = profesor = perfilprincipal.profesor
    periodo = request.session['periodo']

    if request.method == 'POST':
        # Inicio POST
        action = request.POST['action']

        if action == 'addarticulo':
            try:
                f = SolicitudRegArticuloPubForm(request.POST, request.FILES)

                if 'archivoportada' in request.FILES:
                    archivo = request.FILES['archivoportada']
                    descripcionarchivo = 'Portada e Índice'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivoarticulo' in request.FILES:
                    archivo = request.FILES['archivoarticulo']
                    descripcionarchivo = 'Artículo'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocarta' in request.FILES:
                    archivo = request.FILES['archivocarta']
                    descripcionarchivo = 'Carta de aceptación'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    # Verifico si está repetida la solicitud de ese tipo con el mismo título
                    if SolicitudPublicacion.objects.filter(status=True, tiposolicitud=1, nombre=f.cleaned_data['titulo']).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El título para el tipo de publicación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    # Verifico si está repetida la solicitud de ese tipo con el mismo resumen
                    if SolicitudPublicacion.objects.filter(status=True, tiposolicitud=1, motivo=f.cleaned_data['resumen']).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El resumen para el tipo de publicación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    if int(f.cleaned_data['estadopublicacion']) == 2 and f.cleaned_data['fechatentpublicacion']:
                        if f.cleaned_data['fechatentpublicacion'] <= f.cleaned_data['fechaaceptacion']:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha tentativa de publicación debe ser mayor a la fecha de aceptación", "showSwal": "True", "swalType": "warning"})

                    # Obtengo los valores del detalle de los participates de la publicación
                    tipospersona = request.POST.getlist('tipopersona[]')  # Todas los tipos de personas (Profesor, Administrativo, Alumno)
                    idsregtipopersona = request.POST.getlist('idregtipopersona[]')  # Todas los ids de las personas (Profesor, Administrativo, Alumno)
                    idtipos = request.POST.getlist('tipo[]')  # Todas los tipos : Autor/Coautor
                    idfiliaciones = request.POST.getlist('filiacion[]')  # Todas las filiaciones: Interna/Externa

                    # Obtengo estado SOLICITADO
                    estado = obtener_estado_solicitud(8, 1)

                    # Guardo los datos de la solicitud
                    solicitudpublicacion = SolicitudPublicacion(
                        persona=persona,
                        tiposolicitud=1,
                        nombre=f.cleaned_data['titulo'],
                        motivo=f.cleaned_data['resumen'],
                        revistainvestigacion=f.cleaned_data['revista'] if f.cleaned_data['revista'] else None,
                        revista=f.cleaned_data['nombrerevista'].strip() if f.cleaned_data['nombrerevista'] else '',
                        estadopublicacion=f.cleaned_data['estadopublicacion'],
                        fechapublicacion=f.cleaned_data['fechapublicacion'] if f.cleaned_data['fechapublicacion'] else None,
                        fechaaprobacion=f.cleaned_data['fechaaceptacion'] if f.cleaned_data['fechaaceptacion'] else None,
                        fechatentpublicacion=f.cleaned_data['fechatentpublicacion'] if f.cleaned_data['fechatentpublicacion'] else None,
                        enlace=f.cleaned_data['enlace'] if f.cleaned_data['enlace'] else '',
                        volumen=f.cleaned_data['volumenrevista'] if f.cleaned_data['volumenrevista'] else '',
                        numero=f.cleaned_data['numerorevista'] if f.cleaned_data['numerorevista'] else '',
                        paginas=f.cleaned_data['paginaarticulorevista'] if f.cleaned_data['paginaarticulorevista'] else '',
                        areaconocimiento=f.cleaned_data['campoamplio'],
                        subareaconocimiento=f.cleaned_data['campoespecifico'],
                        subareaespecificaconocimiento=f.cleaned_data['campodetallado'],
                        lineainvestigacion=f.cleaned_data['lineainvestigacion'],
                        sublineainvestigacion=f.cleaned_data['sublineainvestigacion'],
                        provieneproyecto=f.cleaned_data['provieneproyecto'],
                        tipoproyecto=f.cleaned_data['tipoproyecto'] if f.cleaned_data['provieneproyecto'] else None,
                        pertenecegrupoinv=f.cleaned_data['pertenecegrupoinv'],
                        grupoinvestigacion=f.cleaned_data['grupoinvestigacion'],
                        estado=estado
                    )
                    solicitudpublicacion.save(request)

                    if f.cleaned_data['provieneproyecto']:
                        if int(f.cleaned_data['tipoproyecto']) != 3:
                            solicitudpublicacion.proyectointerno = f.cleaned_data['proyectointerno']
                        else:
                            solicitudpublicacion.proyectoexterno = f.cleaned_data['proyectoexterno']

                    if 'archivoportada' in request.FILES:
                        archivoportada = request.FILES['archivoportada']
                        archivoportada._name = generar_nombre("portada", archivoportada._name)
                        solicitudpublicacion.archivocomite = archivoportada

                    if 'archivoarticulo' in request.FILES:
                        archivoarticulo = request.FILES['archivoarticulo']
                        archivoarticulo._name = generar_nombre("articulo", archivoarticulo._name)
                        solicitudpublicacion.archivo = archivoarticulo

                    if 'archivocarta' in request.FILES:
                        archivocarta = request.FILES['archivocarta']
                        archivocarta._name = generar_nombre("cartaaceptacion", archivocarta._name)
                        solicitudpublicacion.archivocertificado = archivocarta

                    solicitudpublicacion.save(request)

                    # Guardo los participantes
                    for tipopersona, idregtipopersona, tipo, filiacion in zip(tipospersona, idsregtipopersona, idtipos, idfiliaciones):
                        participante = ParticipanteSolicitudPublicacion(
                            solicitud=solicitudpublicacion,
                            tipo=tipo,
                            profesor_id=idregtipopersona if int(tipopersona) == 1 else None,
                            administrativo_id=idregtipopersona if int(tipopersona) == 2 else None,
                            inscripcion_id=idregtipopersona if int(tipopersona) == 3 else None,
                            tipoparticipanteins=filiacion
                        )
                        participante.save(request)

                    # Notificación por e-mail
                    notificar_solicitud(solicitudpublicacion, False)

                    log(f'{persona} adicionó solicitud de registro de artículo: {solicitudpublicacion}', request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    for k, v in f.errors.items():
                        raise NameError( k + ', ' + v[0])
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editarticulo':
            try:
                # Consulto la solicitud de publicación
                solicitudpublicacion = SolicitudPublicacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda editar
                if not solicitudpublicacion.puede_editar_eliminar():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido validado por la Coordinación de Investigación", "showSwal": "True", "swalType": "warning"})

                f = SolicitudRegArticuloPubForm(request.POST, request.FILES)

                if 'archivoportada' in request.FILES:
                    archivo = request.FILES['archivoportada']
                    descripcionarchivo = 'Portada e Índice'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivoarticulo' in request.FILES:
                    archivo = request.FILES['archivoarticulo']
                    descripcionarchivo = 'Artículo'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocarta' in request.FILES:
                    archivo = request.FILES['archivocarta']
                    descripcionarchivo = 'Carta de aceptación'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    # Verifico si está repetida la solicitud de ese tipo con el mismo título
                    if SolicitudPublicacion.objects.filter(status=True, tiposolicitud=1, nombre=f.cleaned_data['titulo']).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El título para el tipo de publicación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    # Verifico si está repetida la solicitud de ese tipo con el mismo resumen
                    if SolicitudPublicacion.objects.filter(status=True, tiposolicitud=1, motivo=f.cleaned_data['resumen']).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El resumen para el tipo de publicación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    if int(f.cleaned_data['estadopublicacion']) == 2 and f.cleaned_data['fechatentpublicacion']:
                        if f.cleaned_data['fechatentpublicacion'] <= f.cleaned_data['fechaaceptacion']:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha tentativa de publicación debe ser mayor a la fecha de aceptación", "showSwal": "True", "swalType": "warning"})

                    # Obtengo los valores del detalle de los participates de la publicación
                    participanteseliminados = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else []
                    idsdetpar = request.POST.getlist('iddetpar[]')  # Todos los IDs de los detalles de participantes
                    tipospersona = request.POST.getlist('tipopersona[]')  # Todas los tipos de personas (Profesor, Administrativo, Alumno)
                    idsregtipopersona = request.POST.getlist('idregtipopersona[]')  # Todas los ids de las personas (Profesor, Administrativo, Alumno)
                    idtipos = request.POST.getlist('tipo[]')  # Todas los tipos : Autor/Coautor
                    idfiliaciones = request.POST.getlist('filiacion[]')  # Todas las filiaciones: Interna/Externa

                    estadopublicacionoriginal = solicitudpublicacion.estadopublicacion

                    # Actualizo la solicitud
                    solicitudpublicacion.nombre = f.cleaned_data['titulo']
                    solicitudpublicacion.motivo = f.cleaned_data['resumen']
                    solicitudpublicacion.revistainvestigacion = f.cleaned_data['revista'] if f.cleaned_data['revista'] else None
                    solicitudpublicacion.revista = f.cleaned_data['nombrerevista'] if f.cleaned_data['nombrerevista'] else ''
                    solicitudpublicacion.estadopublicacion = f.cleaned_data['estadopublicacion']
                    solicitudpublicacion.fechapublicacion = f.cleaned_data['fechapublicacion'] if f.cleaned_data['fechapublicacion'] else None
                    solicitudpublicacion.fechaaprobacion = f.cleaned_data['fechaaceptacion'] if f.cleaned_data['fechaaceptacion'] else None
                    solicitudpublicacion.fechatentpublicacion = f.cleaned_data['fechatentpublicacion'] if f.cleaned_data['fechatentpublicacion'] else None
                    solicitudpublicacion.enlace = f.cleaned_data['enlace'] if f.cleaned_data['enlace'] else ''
                    solicitudpublicacion.volumen = f.cleaned_data['volumenrevista'] if f.cleaned_data['volumenrevista'] else ''
                    solicitudpublicacion.numero = f.cleaned_data['numerorevista'] if f.cleaned_data['numerorevista'] else ''
                    solicitudpublicacion.paginas = f.cleaned_data['paginaarticulorevista'] if f.cleaned_data['paginaarticulorevista'] else ''
                    solicitudpublicacion.areaconocimiento = f.cleaned_data['campoamplio']
                    solicitudpublicacion.subareaconocimiento = f.cleaned_data['campoespecifico']
                    solicitudpublicacion.subareaespecificaconocimiento = f.cleaned_data['campodetallado']
                    solicitudpublicacion.lineainvestigacion = f.cleaned_data['lineainvestigacion']
                    solicitudpublicacion.sublineainvestigacion = f.cleaned_data['sublineainvestigacion']
                    solicitudpublicacion.provieneproyecto = f.cleaned_data['provieneproyecto']
                    solicitudpublicacion.tipoproyecto = f.cleaned_data['tipoproyecto'] if f.cleaned_data['provieneproyecto'] else None
                    solicitudpublicacion.proyectointerno = None
                    solicitudpublicacion.proyectoexterno = None
                    solicitudpublicacion.pertenecegrupoinv = f.cleaned_data['pertenecegrupoinv']
                    solicitudpublicacion.grupoinvestigacion = f.cleaned_data['grupoinvestigacion']

                    if f.cleaned_data['provieneproyecto']:
                        if int(f.cleaned_data['tipoproyecto']) != 3:
                            solicitudpublicacion.proyectointerno = f.cleaned_data['proyectointerno']
                        else:
                            solicitudpublicacion.proyectoexterno = f.cleaned_data['proyectoexterno']

                    if 'archivoportada' in request.FILES:
                        archivoportada = request.FILES['archivoportada']
                        archivoportada._name = generar_nombre("portada", archivoportada._name)
                        solicitudpublicacion.archivocomite = archivoportada

                    if 'archivoarticulo' in request.FILES:
                        archivoarticulo = request.FILES['archivoarticulo']
                        archivoarticulo._name = generar_nombre("articulo", archivoarticulo._name)
                        solicitudpublicacion.archivo = archivoarticulo

                    if 'archivocarta' in request.FILES:
                        archivocarta = request.FILES['archivocarta']
                        archivocarta._name = generar_nombre("cartaaceptacion", archivocarta._name)
                        solicitudpublicacion.archivocertificado = archivocarta

                    solicitudpublicacion.save(request)

                    if estadopublicacionoriginal != solicitudpublicacion.estadopublicacion:
                        if estadopublicacionoriginal == 1:
                            solicitudpublicacion.archivocomite = None
                            solicitudpublicacion.archivo = None
                        else:
                            solicitudpublicacion.archivocertificado = None

                        solicitudpublicacion.save(request)

                    # Guardo los participantes
                    for idetpar, tipopersona, idregtipopersona, tipo, filiacion in zip(idsdetpar, tipospersona, idsregtipopersona, idtipos, idfiliaciones):
                        # Nuevo
                        if int(idetpar) == 0:
                            participante = ParticipanteSolicitudPublicacion(
                                solicitud=solicitudpublicacion,
                                tipo=tipo,
                                profesor_id=idregtipopersona if int(tipopersona) == 1 else None,
                                administrativo_id=idregtipopersona if int(tipopersona) == 2 else None,
                                inscripcion_id=idregtipopersona if int(tipopersona) == 3 else None,
                                tipoparticipanteins=filiacion
                            )
                        else:
                            participante = ParticipanteSolicitudPublicacion.objects.get(pk=idetpar)
                            participante.tipo = tipo
                            participante.tipoparticipanteins = filiacion

                        participante.save(request)

                    # Elimino los que se borraron del detalle
                    if participanteseliminados:
                        for part in participanteseliminados:
                            participante = ParticipanteSolicitudPublicacion.objects.get(pk=int(part['idreg']))
                            participante.status = False
                            participante.save(request)

                    # En caso de que estado actual sea NOVEDADES se vuelve asignar SOLICITADO
                    if solicitudpublicacion.estado.valor == 3:
                        # Obtengo estado SOLICITADO
                        estado = obtener_estado_solicitud(8, 1)

                        solicitudpublicacion.estado = estado
                        solicitudpublicacion.observacion = ''
                        solicitudpublicacion.save(request)

                        notificar_solicitud(solicitudpublicacion, True)

                    log(f'{persona} editó solicitud de registro de artículo: {solicitudpublicacion}', request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    for k, v in f.errors.items():
                        raise NameError(k + ', ' + v[0])
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addproceeding':
            try:
                f = SolicitudRegProceedingPubForm(request.POST, request.FILES)

                archivo = request.FILES['archivoportada']
                descripcionarchivo = 'Portada e Índice'
                resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                archivo = request.FILES['archivoarticulo']
                descripcionarchivo = 'Artículo'
                resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocarta' in request.FILES:
                    archivo = request.FILES['archivocarta']
                    descripcionarchivo = 'Carta de aceptación'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    # Verifico si está repetida la solicitud de ese tipo con el mismo título
                    if SolicitudPublicacion.objects.filter(status=True, tiposolicitud=5, nombre=f.cleaned_data['titulo']).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El título para el tipo de publicación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    # Verifico si está repetida la solicitud de ese tipo con el mismo resumen
                    if SolicitudPublicacion.objects.filter(status=True, tiposolicitud=5, motivo=f.cleaned_data['resumen']).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El resumen para el tipo de publicación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['fechaaprobacion'] < f.cleaned_data['fecharecepcion']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de aprobación debe ser mayor o igual a la fecha de recepción", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['fechapublicacion'] < f.cleaned_data['fechaaprobacion']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de publicación debe ser mayor o igual a la fecha de aprobación", "showSwal": "True", "swalType": "warning"})

                    # Obtengo los valores del detalle de los participates de la publicación
                    tipospersona = request.POST.getlist('tipopersona[]')  # Todas los tipos de personas (Profesor, Administrativo, Alumno)
                    idsregtipopersona = request.POST.getlist('idregtipopersona[]')  # Todas los ids de las personas (Profesor, Administrativo, Alumno)
                    idtipos = request.POST.getlist('tipo[]')  # Todas los tipos : Autor/Coautor
                    idfiliaciones = request.POST.getlist('filiacion[]')  # Todas las filiaciones: Interna/Externa

                    # Obtengo estado SOLICITADO
                    estado = obtener_estado_solicitud(8, 1)

                    # Guardo los datos de la solicitud
                    solicitudpublicacion = SolicitudPublicacion(
                        persona=persona,
                        tiposolicitud=5,
                        nombre=f.cleaned_data['titulo'],
                        motivo=f.cleaned_data['resumen'],
                        revistainvestigacion=f.cleaned_data['congreso'] if f.cleaned_data['congreso'] else None,
                        revista=f.cleaned_data['nombrecongreso'].strip() if f.cleaned_data['nombrecongreso'] else '',
                        estadopublicacion=1,
                        fecharecepcion=f.cleaned_data['fecharecepcion'],
                        fechaaprobacion=f.cleaned_data['fechaaprobacion'],
                        fechapublicacion=f.cleaned_data['fechapublicacion'],
                        enlace=f.cleaned_data['enlace'],
                        volumen=f.cleaned_data['volumenmemoria'],
                        numero=f.cleaned_data['edicioncongreso'],
                        paginas=f.cleaned_data['paginaarticulomemoria'],
                        areaconocimiento=f.cleaned_data['campoamplio'],
                        subareaconocimiento=f.cleaned_data['campoespecifico'],
                        subareaespecificaconocimiento=f.cleaned_data['campodetallado'],
                        lineainvestigacion=f.cleaned_data['lineainvestigacion'],
                        sublineainvestigacion=f.cleaned_data['sublineainvestigacion'],
                        provieneproyecto=f.cleaned_data['provieneproyecto'],
                        tipoproyecto=f.cleaned_data['tipoproyecto'] if f.cleaned_data['provieneproyecto'] else None,
                        pertenecegrupoinv=f.cleaned_data['pertenecegrupoinv'],
                        grupoinvestigacion=f.cleaned_data['grupoinvestigacion'],
                        estado=estado
                    )
                    solicitudpublicacion.save(request)

                    if f.cleaned_data['provieneproyecto']:
                        if int(f.cleaned_data['tipoproyecto']) != 3:
                            solicitudpublicacion.proyectointerno = f.cleaned_data['proyectointerno']
                        else:
                            solicitudpublicacion.proyectoexterno = f.cleaned_data['proyectoexterno']

                    archivoportada = request.FILES['archivoportada']
                    archivoportada._name = generar_nombre("portada", archivoportada._name)
                    solicitudpublicacion.archivocomite = archivoportada

                    archivoarticulo = request.FILES['archivoarticulo']
                    archivoarticulo._name = generar_nombre("articulo", archivoarticulo._name)
                    solicitudpublicacion.archivo = archivoarticulo

                    if 'archivocarta' in request.FILES:
                        archivocarta = request.FILES['archivocarta']
                        archivocarta._name = generar_nombre("cartaaceptacion", archivocarta._name)
                        solicitudpublicacion.archivocertificado = archivocarta

                    solicitudpublicacion.save(request)

                    # Guardo los participantes
                    for tipopersona, idregtipopersona, tipo, filiacion in zip(tipospersona, idsregtipopersona, idtipos, idfiliaciones):
                        participante = ParticipanteSolicitudPublicacion(
                            solicitud=solicitudpublicacion,
                            tipo=tipo,
                            profesor_id=idregtipopersona if int(tipopersona) == 1 else None,
                            administrativo_id=idregtipopersona if int(tipopersona) == 2 else None,
                            inscripcion_id=idregtipopersona if int(tipopersona) == 3 else None,
                            tipoparticipanteins=filiacion
                        )
                        participante.save(request)

                    # Notificación por e-mail
                    notificar_solicitud(solicitudpublicacion, False)

                    log(u'%s adicionó solicitud de registro de proceeding (artículo de congreso) publicado: %s' % (persona, solicitudpublicacion), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editproceeding':
            try:
                # Consulto la solicitud de publicación
                solicitudpublicacion = SolicitudPublicacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda editar
                if not solicitudpublicacion.puede_editar_eliminar():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido validado por la Coordinación de Investigación", "showSwal": "True", "swalType": "warning"})

                f = SolicitudRegProceedingPubForm(request.POST, request.FILES)

                if 'archivoportada' in request.FILES:
                    archivo = request.FILES['archivoportada']
                    descripcionarchivo = 'Portada e Índice'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivoarticulo' in request.FILES:
                    archivo = request.FILES['archivoarticulo']
                    descripcionarchivo = 'Artículo'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocarta' in request.FILES:
                    archivo = request.FILES['archivocarta']
                    descripcionarchivo = 'Carta de aceptación'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    # Verifico si está repetida la solicitud de ese tipo con el mismo título
                    if SolicitudPublicacion.objects.filter(status=True, tiposolicitud=5, nombre=f.cleaned_data['titulo']).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El título para el tipo de publicación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    # Verifico si está repetida la solicitud de ese tipo con el mismo resumen
                    if SolicitudPublicacion.objects.filter(status=True, tiposolicitud=5, motivo=f.cleaned_data['resumen']).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El resumen para el tipo de publicación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['fechaaprobacion'] < f.cleaned_data['fecharecepcion']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de aprobación debe ser mayor o igual a la fecha de recepción", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['fechapublicacion'] < f.cleaned_data['fechaaprobacion']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de publicación debe ser mayor o igual a la fecha de aprobación", "showSwal": "True", "swalType": "warning"})

                    # Obtengo los valores del detalle de los participates de la publicación
                    participanteseliminados = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else []
                    idsdetpar = request.POST.getlist('iddetpar[]')  # Todos los IDs de los detalles de participantes
                    tipospersona = request.POST.getlist('tipopersona[]')  # Todas los tipos de personas (Profesor, Administrativo, Alumno)
                    idsregtipopersona = request.POST.getlist('idregtipopersona[]')  # Todas los ids de las personas (Profesor, Administrativo, Alumno)
                    idtipos = request.POST.getlist('tipo[]')  # Todas los tipos : Autor/Coautor
                    idfiliaciones = request.POST.getlist('filiacion[]')  # Todas las filiaciones: Interna/Externa

                    # Actualizo la solicitud
                    solicitudpublicacion.nombre = f.cleaned_data['titulo']
                    solicitudpublicacion.motivo = f.cleaned_data['resumen']
                    solicitudpublicacion.revistainvestigacion = f.cleaned_data['congreso'] if f.cleaned_data['congreso'] else None
                    solicitudpublicacion.revista = f.cleaned_data['nombrecongreso'] if f.cleaned_data['nombrecongreso'] else ''
                    solicitudpublicacion.fecharecepcion = f.cleaned_data['fecharecepcion']
                    solicitudpublicacion.fechaaprobacion = f.cleaned_data['fechaaprobacion']
                    solicitudpublicacion.fechapublicacion = f.cleaned_data['fechapublicacion']
                    solicitudpublicacion.enlace = f.cleaned_data['enlace']
                    solicitudpublicacion.volumen = f.cleaned_data['volumenmemoria']
                    solicitudpublicacion.numero = f.cleaned_data['edicioncongreso']
                    solicitudpublicacion.paginas = f.cleaned_data['paginaarticulomemoria']
                    solicitudpublicacion.areaconocimiento = f.cleaned_data['campoamplio']
                    solicitudpublicacion.subareaconocimiento = f.cleaned_data['campoespecifico']
                    solicitudpublicacion.subareaespecificaconocimiento = f.cleaned_data['campodetallado']
                    solicitudpublicacion.lineainvestigacion = f.cleaned_data['lineainvestigacion']
                    solicitudpublicacion.sublineainvestigacion = f.cleaned_data['sublineainvestigacion']
                    solicitudpublicacion.provieneproyecto = f.cleaned_data['provieneproyecto']
                    solicitudpublicacion.tipoproyecto = f.cleaned_data['tipoproyecto'] if f.cleaned_data['provieneproyecto'] else None
                    solicitudpublicacion.proyectointerno = None
                    solicitudpublicacion.proyectoexterno = None
                    solicitudpublicacion.pertenecegrupoinv = f.cleaned_data['pertenecegrupoinv']
                    solicitudpublicacion.grupoinvestigacion = f.cleaned_data['grupoinvestigacion']

                    if f.cleaned_data['provieneproyecto']:
                        if int(f.cleaned_data['tipoproyecto']) != 3:
                            solicitudpublicacion.proyectointerno = f.cleaned_data['proyectointerno']
                        else:
                            solicitudpublicacion.proyectoexterno = f.cleaned_data['proyectoexterno']

                    if 'archivoportada' in request.FILES:
                        archivoportada = request.FILES['archivoportada']
                        archivoportada._name = generar_nombre("portada", archivoportada._name)
                        solicitudpublicacion.archivocomite = archivoportada

                    if 'archivoarticulo' in request.FILES:
                        archivoarticulo = request.FILES['archivoarticulo']
                        archivoarticulo._name = generar_nombre("articulo", archivoarticulo._name)
                        solicitudpublicacion.archivo = archivoarticulo

                    if 'archivocarta' in request.FILES:
                        archivocarta = request.FILES['archivocarta']
                        archivocarta._name = generar_nombre("cartaaceptacion", archivocarta._name)
                        solicitudpublicacion.archivocertificado = archivocarta

                    solicitudpublicacion.save(request)

                    # Guardo los participantes
                    for idetpar, tipopersona, idregtipopersona, tipo, filiacion in zip(idsdetpar, tipospersona, idsregtipopersona, idtipos, idfiliaciones):
                        # Nuevo
                        if int(idetpar) == 0:
                            participante = ParticipanteSolicitudPublicacion(
                                solicitud=solicitudpublicacion,
                                tipo=tipo,
                                profesor_id=idregtipopersona if int(tipopersona) == 1 else None,
                                administrativo_id=idregtipopersona if int(tipopersona) == 2 else None,
                                inscripcion_id=idregtipopersona if int(tipopersona) == 3 else None,
                                tipoparticipanteins=filiacion
                            )
                        else:
                            participante = ParticipanteSolicitudPublicacion.objects.get(pk=idetpar)
                            participante.tipo = tipo
                            participante.tipoparticipanteins = filiacion

                        participante.save(request)

                    # Elimino los que se borraron del detalle
                    if participanteseliminados:
                        for part in participanteseliminados:
                            participante = ParticipanteSolicitudPublicacion.objects.get(pk=int(part['idreg']))
                            participante.status = False
                            participante.save(request)

                    # En caso de que estado actual sea NOVEDADES se vuelve asignar SOLICITADO
                    if solicitudpublicacion.estado.valor == 3:
                        # Obtengo estado SOLICITADO
                        estado = obtener_estado_solicitud(8, 1)

                        solicitudpublicacion.estado = estado
                        solicitudpublicacion.observacion = ''
                        solicitudpublicacion.save(request)

                        notificar_solicitud(solicitudpublicacion, True)

                    log(u'%s editó solicitud de registro de proceeding (artículo de congreso) publicado: %s' % (persona, solicitudpublicacion), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addponencia':
            try:
                f = SolicitudRegPonenciaPubForm(request.POST, request.FILES)

                if 'archivocongreso' in request.FILES:
                    archivo = request.FILES['archivocongreso']
                    descripcionarchivo = 'Publicación'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocarta' in request.FILES:
                    archivo = request.FILES['archivocarta']
                    descripcionarchivo = 'Carta de aceptación o invitación'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivoparticipacion' in request.FILES:
                    archivo = request.FILES['archivoparticipacion']
                    descripcionarchivo = 'Certificado participación'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocomite' in request.FILES:
                    archivo = request.FILES['archivocomite']
                    descripcionarchivo = 'Comité científico'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivoprograma' in request.FILES:
                    archivo = request.FILES['archivoprograma']
                    descripcionarchivo = 'Programa del evento'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    # Verifico si está repetida la solicitud de ese tipo con el mismo título
                    if SolicitudPublicacion.objects.filter(status=True, tiposolicitud=2, nombre=f.cleaned_data['titulo']).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El título para el tipo de publicación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    # Verifico si está repetida la solicitud de ese tipo con el mismo resumen
                    if SolicitudPublicacion.objects.filter(status=True, tiposolicitud=2, motivo=f.cleaned_data['resumen']).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El resumen para el tipo de publicación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['fechafin'] < f.cleaned_data['fechainicio']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin debe ser mayor o igual a la fecha de inicio", "showSwal": "True", "swalType": "warning"})

                    # Obtengo los valores del detalle de los participates de la publicación
                    tipospersona = request.POST.getlist('tipopersona[]')  # Todas los tipos de personas (Profesor, Administrativo, Alumno)
                    idsregtipopersona = request.POST.getlist('idregtipopersona[]')  # Todas los ids de las personas (Profesor, Administrativo, Alumno)
                    idtipos = request.POST.getlist('tipo[]')  # Todas los tipos : Autor/Coautor
                    idfiliaciones = request.POST.getlist('filiacion[]')  # Todas las filiaciones: Interna/Externa

                    # Obtengo los valores del detalle de integrantes del comité
                    integrantes = request.POST.getlist('nombre_integrante[]')  # Todas los nombres
                    instituciones = request.POST.getlist('institucion_integrante[]')  # Todas las instituciones
                    emails = request.POST.getlist('email_integrante[]')  # Todas las direcciones de e-mail

                    # Valido que se hayan ingresado mínimo 3 integrantes del comité
                    if len(integrantes) < 3:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El comité científico debe estar conformado al menos de 3 integrantes", "showSwal": "True", "swalType": "warning"})

                    # Valido que no estén repetidos los integrantes del comité
                    listado = [nombre.strip().upper() for nombre in integrantes]
                    repetido = [x for x, y in collections.Counter(listado).items() if y > 1]
                    if repetido:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El integrante <b>%s</b> del comité científico está repetido" % (listado[0]), "showSwal": "True", "swalType": "warning"})

                    # Obtengo estado SOLICITADO
                    estado = obtener_estado_solicitud(8, 1)

                    # Guardo los datos de la solicitud
                    solicitudpublicacion = SolicitudPublicacion(
                        persona=persona,
                        tiposolicitud=2,
                        nombre=f.cleaned_data['titulo'],
                        motivo=f.cleaned_data['resumen'],
                        evento=f.cleaned_data['congreso'],
                        pais=f.cleaned_data['pais'],
                        ciudad=f.cleaned_data['ciudad'],
                        fecharecepcion=f.cleaned_data['fechainicio'],
                        fechaaprobacion=f.cleaned_data['fechafin'],
                        enlace=f.cleaned_data['enlace'],
                        fechapublicacion=f.cleaned_data['fechapublicacion'],
                        estadopublicacion=1,
                        areaconocimiento=f.cleaned_data['campoamplio'],
                        subareaconocimiento=f.cleaned_data['campoespecifico'],
                        subareaespecificaconocimiento=f.cleaned_data['campodetallado'],
                        lineainvestigacion=f.cleaned_data['lineainvestigacion'],
                        sublineainvestigacion=f.cleaned_data['sublineainvestigacion'],
                        provieneproyecto=f.cleaned_data['provieneproyecto'],
                        tipoproyecto=f.cleaned_data['tipoproyecto'] if f.cleaned_data['provieneproyecto'] else None,
                        pertenecegrupoinv=f.cleaned_data['pertenecegrupoinv'],
                        grupoinvestigacion=f.cleaned_data['grupoinvestigacion'],
                        comitecientifico=True,
                        estado=estado
                    )
                    solicitudpublicacion.save(request)

                    if f.cleaned_data['provieneproyecto']:
                        if int(f.cleaned_data['tipoproyecto']) != 3:
                            solicitudpublicacion.proyectointerno = f.cleaned_data['proyectointerno']
                        else:
                            solicitudpublicacion.proyectoexterno = f.cleaned_data['proyectoexterno']

                    # Creo una lista con los integrantes
                    comiteevaluador = []
                    for integrante, institucion, email in zip(integrantes, instituciones, emails):
                        comiteevaluador.append({"nombre": integrante.upper().strip(), "institucion": institucion.upper().strip(), "email": email.lower().strip()})

                    solicitudpublicacion.integrantecomite = str(comiteevaluador)

                    archivocongreso = request.FILES['archivocongreso']
                    archivocongreso._name = generar_nombre("memoriacongreso", archivocongreso._name)
                    solicitudpublicacion.archivo = archivocongreso

                    archivocarta = request.FILES['archivocarta']
                    archivocarta._name = generar_nombre("cartaaceptacion", archivocarta._name)
                    solicitudpublicacion.archivocertificado = archivocarta

                    archivoparticipacion = request.FILES['archivoparticipacion']
                    archivoparticipacion._name = generar_nombre("certificadoparticipacion", archivoparticipacion._name)
                    solicitudpublicacion.archivoparticipacion = archivoparticipacion

                    archivocomite = request.FILES['archivocomite']
                    archivocomite._name = generar_nombre("comitecientifico", archivocomite._name)
                    solicitudpublicacion.archivocomite = archivocomite

                    archivoprograma = request.FILES['archivoprograma']
                    archivoprograma._name = generar_nombre("programaevento", archivoprograma._name)
                    solicitudpublicacion.archivoprograma = archivoprograma

                    solicitudpublicacion.save(request)

                    # Guardo los participantes
                    for tipopersona, idregtipopersona, tipo, filiacion in zip(tipospersona, idsregtipopersona, idtipos, idfiliaciones):
                        participante = ParticipanteSolicitudPublicacion(
                            solicitud=solicitudpublicacion,
                            tipo=tipo,
                            profesor_id=idregtipopersona if int(tipopersona) == 1 else None,
                            administrativo_id=idregtipopersona if int(tipopersona) == 2 else None,
                            inscripcion_id=idregtipopersona if int(tipopersona) == 3 else None,
                            tipoparticipanteins=filiacion
                        )
                        participante.save(request)

                    # Notificación por e-mail
                    notificar_solicitud(solicitudpublicacion, False)

                    log(u'%s adicionó solicitud de registro de ponencia publicada: %s' % (persona, solicitudpublicacion), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editponencia':
            try:
                # Consulto la solicitud de publicación
                solicitudpublicacion = SolicitudPublicacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda editar
                if not solicitudpublicacion.puede_editar_eliminar():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido validado por la Coordinación de Investigación", "showSwal": "True", "swalType": "warning"})

                f = SolicitudRegPonenciaPubForm(request.POST, request.FILES)

                if 'archivocongreso' in request.FILES:
                    archivo = request.FILES['archivocongreso']
                    descripcionarchivo = 'Publicación'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocarta' in request.FILES:
                    archivo = request.FILES['archivocarta']
                    descripcionarchivo = 'Carta de aceptación o invitación'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivoparticipacion' in request.FILES:
                    archivo = request.FILES['archivoparticipacion']
                    descripcionarchivo = 'Certificado participación'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocomite' in request.FILES:
                    archivo = request.FILES['archivocomite']
                    descripcionarchivo = 'Comité científico'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivoprograma' in request.FILES:
                    archivo = request.FILES['archivoprograma']
                    descripcionarchivo = 'Programa del evento'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    # Verifico si está repetida la solicitud de ese tipo con el mismo título
                    if SolicitudPublicacion.objects.filter(status=True, tiposolicitud=2, nombre=f.cleaned_data['titulo']).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El título para el tipo de publicación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    # Verifico si está repetida la solicitud de ese tipo con el mismo resumen
                    if SolicitudPublicacion.objects.filter(status=True, tiposolicitud=2, motivo=f.cleaned_data['resumen']).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El resumen para el tipo de publicación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['fechafin'] < f.cleaned_data['fechainicio']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin debe ser mayor o igual a la fecha de inicio", "showSwal": "True", "swalType": "warning"})

                    # Obtengo los valores del detalle de los participates de la publicación
                    participanteseliminados = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else []
                    idsdetpar = request.POST.getlist('iddetpar[]')  # Todos los IDs de los detalles de participantes
                    tipospersona = request.POST.getlist('tipopersona[]')  # Todas los tipos de personas (Profesor, Administrativo, Alumno)
                    idsregtipopersona = request.POST.getlist('idregtipopersona[]')  # Todas los ids de las personas (Profesor, Administrativo, Alumno)
                    idtipos = request.POST.getlist('tipo[]')  # Todas los tipos : Autor/Coautor
                    idfiliaciones = request.POST.getlist('filiacion[]')  # Todas las filiaciones: Interna/Externa

                    # Obtengo los valores del detalle de integrantes del comité
                    integrantes = request.POST.getlist('nombre_integrante[]')  # Todas los nombres
                    instituciones = request.POST.getlist('institucion_integrante[]')  # Todas las instituciones
                    emails = request.POST.getlist('email_integrante[]')  # Todas las direcciones de e-mail

                    # Valido que se hayan ingresado mínimo 3 integrantes del comité
                    if len(integrantes) < 3:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El comité científico debe estar conformado al menos de 3 integrantes", "showSwal": "True", "swalType": "warning"})

                    # Valido que no estén repetidos los integrantes del comité
                    listado = [nombre.strip().upper() for nombre in integrantes]
                    repetido = [x for x, y in collections.Counter(listado).items() if y > 1]
                    if repetido:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El integrante <b>%s</b> del comité científico está repetido" % (listado[0]), "showSwal": "True", "swalType": "warning"})

                    # Creo una lista con los integrantes
                    comiteevaluador = []
                    for integrante, institucion, email in zip(integrantes, instituciones, emails):
                        comiteevaluador.append({"nombre": integrante.upper().strip(), "institucion": institucion.upper().strip(), "email": email.lower().strip()})

                    # Actualizo la solicitud
                    solicitudpublicacion.nombre = f.cleaned_data['titulo']
                    solicitudpublicacion.motivo = f.cleaned_data['resumen']
                    solicitudpublicacion.evento = f.cleaned_data['congreso']
                    solicitudpublicacion.pais = f.cleaned_data['pais']
                    solicitudpublicacion.ciudad = f.cleaned_data['ciudad']
                    solicitudpublicacion.fecharecepcion = f.cleaned_data['fechainicio']
                    solicitudpublicacion.fechaaprobacion = f.cleaned_data['fechafin']
                    solicitudpublicacion.enlace = f.cleaned_data['enlace']
                    solicitudpublicacion.fechapublicacion = f.cleaned_data['fechapublicacion']
                    solicitudpublicacion.areaconocimiento = f.cleaned_data['campoamplio']
                    solicitudpublicacion.subareaconocimiento = f.cleaned_data['campoespecifico']
                    solicitudpublicacion.subareaespecificaconocimiento = f.cleaned_data['campodetallado']
                    solicitudpublicacion.lineainvestigacion = f.cleaned_data['lineainvestigacion']
                    solicitudpublicacion.sublineainvestigacion = f.cleaned_data['sublineainvestigacion']
                    solicitudpublicacion.provieneproyecto = f.cleaned_data['provieneproyecto']
                    solicitudpublicacion.tipoproyecto = f.cleaned_data['tipoproyecto'] if f.cleaned_data['provieneproyecto'] else None
                    solicitudpublicacion.proyectointerno = None
                    solicitudpublicacion.proyectoexterno = None
                    solicitudpublicacion.pertenecegrupoinv = f.cleaned_data['pertenecegrupoinv']
                    solicitudpublicacion.grupoinvestigacion = f.cleaned_data['grupoinvestigacion']
                    solicitudpublicacion.integrantecomite = str(comiteevaluador)

                    if f.cleaned_data['provieneproyecto']:
                        if int(f.cleaned_data['tipoproyecto']) != 3:
                            solicitudpublicacion.proyectointerno = f.cleaned_data['proyectointerno']
                        else:
                            solicitudpublicacion.proyectoexterno = f.cleaned_data['proyectoexterno']

                    if 'archivocongreso' in request.FILES:
                        archivocongreso = request.FILES['archivocongreso']
                        archivocongreso._name = generar_nombre("memoriacongreso", archivocongreso._name)
                        solicitudpublicacion.archivo = archivocongreso

                    if 'archivocarta' in request.FILES:
                        archivocarta = request.FILES['archivocarta']
                        archivocarta._name = generar_nombre("cartaaceptacion", archivocarta._name)
                        solicitudpublicacion.archivocertificado = archivocarta

                    if 'archivoparticipacion' in request.FILES:
                        archivoparticipacion = request.FILES['archivoparticipacion']
                        archivoparticipacion._name = generar_nombre("certificadoparticipacion", archivoparticipacion._name)
                        solicitudpublicacion.archivoparticipacion = archivoparticipacion

                    if 'archivocomite' in request.FILES:
                        archivocomite = request.FILES['archivocomite']
                        archivocomite._name = generar_nombre("comitecientifico", archivocomite._name)
                        solicitudpublicacion.archivocomite = archivocomite

                    if 'archivoprograma' in request.FILES:
                        archivoprograma = request.FILES['archivoprograma']
                        archivoprograma._name = generar_nombre("programaevento", archivoprograma._name)
                        solicitudpublicacion.archivoprograma = archivoprograma

                    solicitudpublicacion.save(request)

                    # Guardo los participantes
                    for idetpar, tipopersona, idregtipopersona, tipo, filiacion in zip(idsdetpar, tipospersona, idsregtipopersona, idtipos, idfiliaciones):
                        # Nuevo
                        if int(idetpar) == 0:
                            participante = ParticipanteSolicitudPublicacion(
                                solicitud=solicitudpublicacion,
                                tipo=tipo,
                                profesor_id=idregtipopersona if int(tipopersona) == 1 else None,
                                administrativo_id=idregtipopersona if int(tipopersona) == 2 else None,
                                inscripcion_id=idregtipopersona if int(tipopersona) == 3 else None,
                                tipoparticipanteins=filiacion
                            )
                        else:
                            participante = ParticipanteSolicitudPublicacion.objects.get(pk=idetpar)
                            participante.tipo = tipo
                            participante.tipoparticipanteins = filiacion

                        participante.save(request)

                    # Elimino los que se borraron del detalle
                    if participanteseliminados:
                        for part in participanteseliminados:
                            participante = ParticipanteSolicitudPublicacion.objects.get(pk=int(part['idreg']))
                            participante.status = False
                            participante.save(request)

                    # En caso de que estado actual sea NOVEDADES se vuelve asignar SOLICITADO
                    if solicitudpublicacion.estado.valor == 3:
                        # Obtengo estado SOLICITADO
                        estado = obtener_estado_solicitud(8, 1)

                        solicitudpublicacion.estado = estado
                        solicitudpublicacion.observacion = ''
                        solicitudpublicacion.save(request)

                        notificar_solicitud(solicitudpublicacion, True)

                    log(u'%s editó solicitud de registro de ponencia publicada: %s' % (persona, solicitudpublicacion), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addlibro':
            try:
                f = SolicitudRegLibroPubForm(request.POST, request.FILES)

                if 'archivolibro' in request.FILES:
                    archivo = request.FILES['archivolibro']
                    descripcionarchivo = 'Libro'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocertificado' in request.FILES:
                    archivo = request.FILES['archivocertificado']
                    descripcionarchivo = 'Certificado de publicación'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivorevision' in request.FILES:
                    archivo = request.FILES['archivorevision']
                    descripcionarchivo = 'Certificado o matriz de revsión por pares'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    # Verifico si está repetida la solicitud de ese tipo con el mismo título
                    if SolicitudPublicacion.objects.filter(status=True, tiposolicitud=3, nombre=f.cleaned_data['titulo']).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El título para el tipo de publicación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    # Obtengo los valores del detalle de los participates de la publicación
                    tipospersona = request.POST.getlist('tipopersona[]')  # Todas los tipos de personas (Profesor, Administrativo, Alumno)
                    idsregtipopersona = request.POST.getlist('idregtipopersona[]')  # Todas los ids de las personas (Profesor, Administrativo, Alumno)
                    idtipos = request.POST.getlist('tipo[]')  # Todas los tipos : Autor/Coautor
                    idfiliaciones = request.POST.getlist('filiacion[]')  # Todas las filiaciones: Interna/Externa

                    # Obtengo estado SOLICITADO
                    estado = obtener_estado_solicitud(8, 1)

                    # Guardo los datos de la solicitud
                    solicitudpublicacion = SolicitudPublicacion(
                        persona=persona,
                        tiposolicitud=3,
                        nombre=f.cleaned_data['titulo'],
                        codigoisbn=f.cleaned_data['codigoisbn'],
                        editorcompilador=f.cleaned_data['editor'],
                        fechapublicacion=f.cleaned_data['fechapublicacion'],
                        estadopublicacion=1,
                        areaconocimiento=f.cleaned_data['campoamplio'],
                        subareaconocimiento=f.cleaned_data['campoespecifico'],
                        subareaespecificaconocimiento=f.cleaned_data['campodetallado'],
                        lineainvestigacion=f.cleaned_data['lineainvestigacion'],
                        sublineainvestigacion=f.cleaned_data['sublineainvestigacion'],
                        provieneproyecto=f.cleaned_data['provieneproyecto'],
                        tipoproyecto=f.cleaned_data['tipoproyecto'] if f.cleaned_data['provieneproyecto'] else None,
                        pertenecegrupoinv=f.cleaned_data['pertenecegrupoinv'],
                        grupoinvestigacion=f.cleaned_data['grupoinvestigacion'],
                        revisadopar=f.cleaned_data['revisadopar'],
                        estado=estado
                    )
                    solicitudpublicacion.save(request)

                    if f.cleaned_data['provieneproyecto']:
                        if int(f.cleaned_data['tipoproyecto']) != 3:
                            solicitudpublicacion.proyectointerno = f.cleaned_data['proyectointerno']
                        else:
                            solicitudpublicacion.proyectoexterno = f.cleaned_data['proyectoexterno']

                    archivolibro = request.FILES['archivolibro']
                    archivolibro._name = generar_nombre("libro", archivolibro._name)
                    solicitudpublicacion.archivo = archivolibro

                    archivocertificado = request.FILES['archivocertificado']
                    archivocertificado._name = generar_nombre("certificadopublicacion", archivocertificado._name)
                    solicitudpublicacion.archivocertificado = archivocertificado

                    archivorevision = request.FILES['archivorevision']
                    archivorevision._name = generar_nombre("revisionpares", archivorevision._name)
                    solicitudpublicacion.archivocomite = archivorevision

                    solicitudpublicacion.save(request)

                    # Guardo los participantes
                    for tipopersona, idregtipopersona, tipo, filiacion in zip(tipospersona, idsregtipopersona, idtipos, idfiliaciones):
                        participante = ParticipanteSolicitudPublicacion(
                            solicitud=solicitudpublicacion,
                            tipo=tipo,
                            profesor_id=idregtipopersona if int(tipopersona) == 1 else None,
                            administrativo_id=idregtipopersona if int(tipopersona) == 2 else None,
                            inscripcion_id=idregtipopersona if int(tipopersona) == 3 else None,
                            tipoparticipanteins=filiacion
                        )
                        participante.save(request)

                    # Notificación por e-mail
                    notificar_solicitud(solicitudpublicacion, False)

                    log(u'%s adicionó solicitud de registro de libro publicado: %s' % (persona, solicitudpublicacion), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editlibro':
            try:
                # Consulto la solicitud de publicación
                solicitudpublicacion = SolicitudPublicacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda editar
                if not solicitudpublicacion.puede_editar_eliminar():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido validado por la Coordinación de Investigación", "showSwal": "True", "swalType": "warning"})

                f = SolicitudRegLibroPubForm(request.POST, request.FILES)

                if 'archivolibro' in request.FILES:
                    archivo = request.FILES['archivolibro']
                    descripcionarchivo = 'Libro'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocertificado' in request.FILES:
                    archivo = request.FILES['archivocertificado']
                    descripcionarchivo = 'Certificado de publicación'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivorevision' in request.FILES:
                    archivo = request.FILES['archivorevision']
                    descripcionarchivo = 'Certificado o matriz de revsión por pares'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    # Verifico si está repetida la solicitud de ese tipo con el mismo título
                    if SolicitudPublicacion.objects.filter(status=True, tiposolicitud=3, nombre=f.cleaned_data['titulo']).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El título para el tipo de publicación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    # Obtengo los valores del detalle de los participates de la publicación
                    participanteseliminados = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else []
                    idsdetpar = request.POST.getlist('iddetpar[]')  # Todos los IDs de los detalles de participantes
                    tipospersona = request.POST.getlist('tipopersona[]')  # Todas los tipos de personas (Profesor, Administrativo, Alumno)
                    idsregtipopersona = request.POST.getlist('idregtipopersona[]')  # Todas los ids de las personas (Profesor, Administrativo, Alumno)
                    idtipos = request.POST.getlist('tipo[]')  # Todas los tipos : Autor/Coautor
                    idfiliaciones = request.POST.getlist('filiacion[]')  # Todas las filiaciones: Interna/Externa

                    # Actualizo la solicitud
                    solicitudpublicacion.nombre = f.cleaned_data['titulo']
                    solicitudpublicacion.codigoisbn = f.cleaned_data['codigoisbn']
                    solicitudpublicacion.editorcompilador = f.cleaned_data['editor']
                    solicitudpublicacion.fechapublicacion = f.cleaned_data['fechapublicacion']
                    solicitudpublicacion.areaconocimiento = f.cleaned_data['campoamplio']
                    solicitudpublicacion.subareaconocimiento = f.cleaned_data['campoespecifico']
                    solicitudpublicacion.subareaespecificaconocimiento = f.cleaned_data['campodetallado']
                    solicitudpublicacion.lineainvestigacion = f.cleaned_data['lineainvestigacion']
                    solicitudpublicacion.sublineainvestigacion = f.cleaned_data['sublineainvestigacion']
                    solicitudpublicacion.provieneproyecto = f.cleaned_data['provieneproyecto']
                    solicitudpublicacion.tipoproyecto = f.cleaned_data['tipoproyecto'] if f.cleaned_data['provieneproyecto'] else None
                    solicitudpublicacion.proyectointerno = None
                    solicitudpublicacion.proyectoexterno = None
                    solicitudpublicacion.pertenecegrupoinv = f.cleaned_data['pertenecegrupoinv']
                    solicitudpublicacion.grupoinvestigacion = f.cleaned_data['grupoinvestigacion']
                    solicitudpublicacion.revisadopar = f.cleaned_data['revisadopar']

                    if f.cleaned_data['provieneproyecto']:
                        if int(f.cleaned_data['tipoproyecto']) != 3:
                            solicitudpublicacion.proyectointerno = f.cleaned_data['proyectointerno']
                        else:
                            solicitudpublicacion.proyectoexterno = f.cleaned_data['proyectoexterno']

                    if 'archivolibro' in request.FILES:
                        archivolibro = request.FILES['archivolibro']
                        archivolibro._name = generar_nombre("libro", archivolibro._name)
                        solicitudpublicacion.archivo = archivolibro

                    if 'archivocertificado' in request.FILES:
                        archivocertificado = request.FILES['archivocertificado']
                        archivocertificado._name = generar_nombre("certificadopublicacion", archivocertificado._name)
                        solicitudpublicacion.archivocertificado = archivocertificado

                    if 'archivorevision' in request.FILES:
                        archivorevision = request.FILES['archivorevision']
                        archivorevision._name = generar_nombre("revisionpares", archivorevision._name)
                        solicitudpublicacion.archivocomite = archivorevision

                    solicitudpublicacion.save(request)

                    # Guardo los participantes
                    for idetpar, tipopersona, idregtipopersona, tipo, filiacion in zip(idsdetpar, tipospersona, idsregtipopersona, idtipos, idfiliaciones):
                        # Nuevo
                        if int(idetpar) == 0:
                            participante = ParticipanteSolicitudPublicacion(
                                solicitud=solicitudpublicacion,
                                tipo=tipo,
                                profesor_id=idregtipopersona if int(tipopersona) == 1 else None,
                                administrativo_id=idregtipopersona if int(tipopersona) == 2 else None,
                                inscripcion_id=idregtipopersona if int(tipopersona) == 3 else None,
                                tipoparticipanteins=filiacion
                            )
                        else:
                            participante = ParticipanteSolicitudPublicacion.objects.get(pk=idetpar)
                            participante.tipo = tipo
                            participante.tipoparticipanteins = filiacion

                        participante.save(request)

                    # Elimino los que se borraron del detalle
                    if participanteseliminados:
                        for part in participanteseliminados:
                            participante = ParticipanteSolicitudPublicacion.objects.get(pk=int(part['idreg']))
                            participante.status = False
                            participante.save(request)

                    # En caso de que estado actual sea NOVEDADES se vuelve asignar SOLICITADO
                    if solicitudpublicacion.estado.valor == 3:
                        # Obtengo estado SOLICITADO
                        estado = obtener_estado_solicitud(8, 1)

                        solicitudpublicacion.estado = estado
                        solicitudpublicacion.observacion = ''
                        solicitudpublicacion.save(request)

                        notificar_solicitud(solicitudpublicacion, True)

                    log(u'%s editó solicitud de registro de libro publicado: %s' % (persona, solicitudpublicacion), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addcapitulo':
            try:
                f = SolicitudRegCapituloLibroPubForm(request.POST, request.FILES)

                if 'archivolibro' in request.FILES:
                    archivo = request.FILES['archivolibro']
                    descripcionarchivo = 'Libro'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocapitulo' in request.FILES:
                    archivo = request.FILES['archivocapitulo']
                    descripcionarchivo = 'Capítulo de Libro'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocertificado' in request.FILES:
                    archivo = request.FILES['archivocertificado']
                    descripcionarchivo = 'Certificado de publicación'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivorevision' in request.FILES:
                    archivo = request.FILES['archivorevision']
                    descripcionarchivo = 'Certificado o matriz de revsión por pares'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    # Verifico si está repetida la solicitud de ese tipo con el mismo título
                    if SolicitudPublicacion.objects.filter(status=True, tiposolicitud=4, nombre=f.cleaned_data['titulocapitulo']).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El título para el tipo de publicación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    # Obtengo los valores del detalle de los participates de la publicación
                    tipospersona = request.POST.getlist('tipopersona[]')  # Todas los tipos de personas (Profesor, Administrativo, Alumno)
                    idsregtipopersona = request.POST.getlist('idregtipopersona[]')  # Todas los ids de las personas (Profesor, Administrativo, Alumno)
                    idtipos = request.POST.getlist('tipo[]')  # Todas los tipos : Autor/Coautor
                    idfiliaciones = request.POST.getlist('filiacion[]')  # Todas las filiaciones: Interna/Externa

                    # Obtengo estado SOLICITADO
                    estado = obtener_estado_solicitud(8, 1)

                    # Guardo los datos de la solicitud
                    solicitudpublicacion = SolicitudPublicacion(
                        persona=persona,
                        tiposolicitud=4,
                        nombre=f.cleaned_data['titulocapitulo'],
                        evento=f.cleaned_data['titulolibro'],
                        codigoisbn=f.cleaned_data['codigoisbn'],
                        paginas=f.cleaned_data['pagina'],
                        editorcompilador=f.cleaned_data['editor'],
                        totalcapitulo=f.cleaned_data['totalcapitulo'],
                        fechapublicacion=f.cleaned_data['fechapublicacion'],
                        estadopublicacion=1,
                        areaconocimiento=f.cleaned_data['campoamplio'],
                        subareaconocimiento=f.cleaned_data['campoespecifico'],
                        subareaespecificaconocimiento=f.cleaned_data['campodetallado'],
                        lineainvestigacion=f.cleaned_data['lineainvestigacion'],
                        sublineainvestigacion=f.cleaned_data['sublineainvestigacion'],
                        provieneproyecto=f.cleaned_data['provieneproyecto'],
                        tipoproyecto=f.cleaned_data['tipoproyecto'] if f.cleaned_data['provieneproyecto'] else None,
                        pertenecegrupoinv=f.cleaned_data['pertenecegrupoinv'],
                        grupoinvestigacion=f.cleaned_data['grupoinvestigacion'],
                        revisadopar=f.cleaned_data['revisadopar'],
                        estado=estado
                    )
                    solicitudpublicacion.save(request)

                    if f.cleaned_data['provieneproyecto']:
                        if int(f.cleaned_data['tipoproyecto']) != 3:
                            solicitudpublicacion.proyectointerno = f.cleaned_data['proyectointerno']
                        else:
                            solicitudpublicacion.proyectoexterno = f.cleaned_data['proyectoexterno']

                    archivocapitulo = request.FILES['archivocapitulo']
                    archivocapitulo._name = generar_nombre("capitulo", archivocapitulo._name)
                    solicitudpublicacion.archivo = archivocapitulo

                    archivolibro = request.FILES['archivolibro']
                    archivolibro._name = generar_nombre("libro", archivolibro._name)
                    solicitudpublicacion.archivocertificado = archivolibro

                    archivocertificado = request.FILES['archivocertificado']
                    archivocertificado._name = generar_nombre("certificadopublicacion", archivocertificado._name)
                    solicitudpublicacion.archivoparticipacion = archivocertificado

                    archivorevision = request.FILES['archivorevision']
                    archivorevision._name = generar_nombre("revisionpares", archivorevision._name)
                    solicitudpublicacion.archivocomite = archivorevision

                    solicitudpublicacion.save(request)

                    # Guardo los participantes
                    for tipopersona, idregtipopersona, tipo, filiacion in zip(tipospersona, idsregtipopersona, idtipos, idfiliaciones):
                        participante = ParticipanteSolicitudPublicacion(
                            solicitud=solicitudpublicacion,
                            tipo=tipo,
                            profesor_id=idregtipopersona if int(tipopersona) == 1 else None,
                            administrativo_id=idregtipopersona if int(tipopersona) == 2 else None,
                            inscripcion_id=idregtipopersona if int(tipopersona) == 3 else None,
                            tipoparticipanteins=filiacion
                        )
                        participante.save(request)

                    # Notificación por e-mail
                    notificar_solicitud(solicitudpublicacion, False)

                    log(u'%s adicionó solicitud de registro de capítulo de libro publicado: %s' % (persona, solicitudpublicacion), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editcapitulo':
            try:
                # Consulto la solicitud de publicación
                solicitudpublicacion = SolicitudPublicacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda editar
                if not solicitudpublicacion.puede_editar_eliminar():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido validado por la Coordinación de Investigación", "showSwal": "True", "swalType": "warning"})

                f = SolicitudRegCapituloLibroPubForm(request.POST, request.FILES)

                if 'archivolibro' in request.FILES:
                    archivo = request.FILES['archivolibro']
                    descripcionarchivo = 'Libro'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocapitulo' in request.FILES:
                    archivo = request.FILES['archivocapitulo']
                    descripcionarchivo = 'Capítulo de Libro'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocertificado' in request.FILES:
                    archivo = request.FILES['archivocertificado']
                    descripcionarchivo = 'Certificado de publicación'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivorevision' in request.FILES:
                    archivo = request.FILES['archivorevision']
                    descripcionarchivo = 'Certificado o matriz de revsión por pares'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    # Verifico si está repetida la solicitud de ese tipo con el mismo título
                    if SolicitudPublicacion.objects.filter(status=True, tiposolicitud=4, nombre=f.cleaned_data['titulocapitulo']).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El título para el tipo de publicación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    # Obtengo los valores del detalle de los participates de la publicación
                    participanteseliminados = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else []
                    idsdetpar = request.POST.getlist('iddetpar[]')  # Todos los IDs de los detalles de participantes
                    tipospersona = request.POST.getlist('tipopersona[]')  # Todas los tipos de personas (Profesor, Administrativo, Alumno)
                    idsregtipopersona = request.POST.getlist('idregtipopersona[]')  # Todas los ids de las personas (Profesor, Administrativo, Alumno)
                    idtipos = request.POST.getlist('tipo[]')  # Todas los tipos : Autor/Coautor
                    idfiliaciones = request.POST.getlist('filiacion[]')  # Todas las filiaciones: Interna/Externa

                    # Actualizo la solicitud
                    solicitudpublicacion.nombre = f.cleaned_data['titulocapitulo']
                    solicitudpublicacion.evento = f.cleaned_data['titulolibro']
                    solicitudpublicacion.codigoisbn = f.cleaned_data['codigoisbn']
                    solicitudpublicacion.paginas = f.cleaned_data['pagina']
                    solicitudpublicacion.editorcompilador = f.cleaned_data['editor']
                    solicitudpublicacion.totalcapitulo = f.cleaned_data['totalcapitulo']
                    solicitudpublicacion.fechapublicacion = f.cleaned_data['fechapublicacion']
                    solicitudpublicacion.areaconocimiento = f.cleaned_data['campoamplio']
                    solicitudpublicacion.subareaconocimiento = f.cleaned_data['campoespecifico']
                    solicitudpublicacion.subareaespecificaconocimiento = f.cleaned_data['campodetallado']
                    solicitudpublicacion.lineainvestigacion = f.cleaned_data['lineainvestigacion']
                    solicitudpublicacion.sublineainvestigacion = f.cleaned_data['sublineainvestigacion']
                    solicitudpublicacion.provieneproyecto = f.cleaned_data['provieneproyecto']
                    solicitudpublicacion.tipoproyecto = f.cleaned_data['tipoproyecto'] if f.cleaned_data['provieneproyecto'] else None
                    solicitudpublicacion.proyectointerno = None
                    solicitudpublicacion.proyectoexterno = None
                    solicitudpublicacion.pertenecegrupoinv = f.cleaned_data['pertenecegrupoinv']
                    solicitudpublicacion.grupoinvestigacion = f.cleaned_data['grupoinvestigacion']
                    solicitudpublicacion.revisadopar = f.cleaned_data['revisadopar']

                    if f.cleaned_data['provieneproyecto']:
                        if int(f.cleaned_data['tipoproyecto']) != 3:
                            solicitudpublicacion.proyectointerno = f.cleaned_data['proyectointerno']
                        else:
                            solicitudpublicacion.proyectoexterno = f.cleaned_data['proyectoexterno']

                    if 'archivocapitulo' in request.FILES:
                        archivocapitulo = request.FILES['archivocapitulo']
                        archivocapitulo._name = generar_nombre("capitulo", archivocapitulo._name)
                        solicitudpublicacion.archivo = archivocapitulo

                    if 'archivolibro' in request.FILES:
                        archivolibro = request.FILES['archivolibro']
                        archivolibro._name = generar_nombre("libro", archivolibro._name)
                        solicitudpublicacion.archivocertificado = archivolibro

                    if 'archivocertificado' in request.FILES:
                        archivocertificado = request.FILES['archivocertificado']
                        archivocertificado._name = generar_nombre("certificadopublicacion", archivocertificado._name)
                        solicitudpublicacion.archivoparticipacion = archivocertificado

                    if 'archivorevision' in request.FILES:
                        archivorevision = request.FILES['archivorevision']
                        archivorevision._name = generar_nombre("revisionpares", archivorevision._name)
                        solicitudpublicacion.archivocomite = archivorevision

                    solicitudpublicacion.save(request)

                    # Guardo los participantes
                    for idetpar, tipopersona, idregtipopersona, tipo, filiacion in zip(idsdetpar, tipospersona, idsregtipopersona, idtipos, idfiliaciones):
                        # Nuevo
                        if int(idetpar) == 0:
                            participante = ParticipanteSolicitudPublicacion(
                                solicitud=solicitudpublicacion,
                                tipo=tipo,
                                profesor_id=idregtipopersona if int(tipopersona) == 1 else None,
                                administrativo_id=idregtipopersona if int(tipopersona) == 2 else None,
                                inscripcion_id=idregtipopersona if int(tipopersona) == 3 else None,
                                tipoparticipanteins=filiacion
                            )
                        else:
                            participante = ParticipanteSolicitudPublicacion.objects.get(pk=idetpar)
                            participante.tipo = tipo
                            participante.tipoparticipanteins = filiacion

                        participante.save(request)

                    # Elimino los que se borraron del detalle
                    if participanteseliminados:
                        for part in participanteseliminados:
                            participante = ParticipanteSolicitudPublicacion.objects.get(pk=int(part['idreg']))
                            participante.status = False
                            participante.save(request)

                    # En caso de que estado actual sea NOVEDADES se vuelve asignar SOLICITADO
                    if solicitudpublicacion.estado.valor == 3:
                        # Obtengo estado SOLICITADO
                        estado = obtener_estado_solicitud(8, 1)

                        solicitudpublicacion.estado = estado
                        solicitudpublicacion.observacion = ''
                        solicitudpublicacion.save(request)

                        notificar_solicitud(solicitudpublicacion, True)

                    log(u'%s editó solicitud de registro de capítulo de libro publicado: %s' % (persona, solicitudpublicacion), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'delsolicitud':
            try:
                # Consulto la solicitud de publicacion
                solicitudpublicacion = SolicitudPublicacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda eliminar
                if not solicitudpublicacion.puede_editar_eliminar():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede eliminar el Registro", "showSwal": "True", "swalType": "warning"})

                # Elimino lal solicitud
                solicitudpublicacion.status = False
                solicitudpublicacion.save(request)

                # Elimino el detalle de participantes
                for participante in solicitudpublicacion.participantesolicitudpublicacion_set.filter(status=True).order_by('id'):
                    participante.status = False
                    participante.save(request)

                log(u'%s eliminó solicitud de registro de publicación de %s con título: %s' % (persona, solicitudpublicacion.get_tiposolicitud_display(), solicitudpublicacion.nombre), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al eliminar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'eliminar':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la producción científica
                tipo = request.POST['tipo']
                if tipo == 'A':
                    produccioncientifica = ArticuloInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                elif tipo == 'P':
                    produccioncientifica = PonenciasInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                elif tipo == 'L':
                    produccioncientifica = LibroInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                else:
                    produccioncientifica = CapituloLibroInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Eliminar la producción científica
                produccioncientifica.observacion = request.POST['observacion'].strip().upper()
                produccioncientifica.fechaeliminadoc = datetime.now()
                produccioncientifica.eliminadoxdoc = True
                produccioncientifica.status = False
                produccioncientifica.save(request)

                log(u'%s eliminó producción científica: %s' % (persona, produccioncientifica), request, "del")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro eliminado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Solicitud incorrecta.", "showSwal": "True", "swalType": "error"})
        # Fin POST
    else:
        if 'action' in request.GET:
            # Inicio GET (action)
            action = request.GET['action']

            if action == 'solicitudespublicacion':
                try:
                    search, url_vars = request.GET.get('s', ''), '&action=' + action
                    ids = request.GET.get('id', '')

                    if ids:
                        data['ids'] = ids
                        solicitudes = SolicitudPublicacion.objects.filter(pk=int(encrypt(ids)))
                        url_vars += '&id=' + ids
                    else:
                        solicitudes = SolicitudPublicacion.objects.filter(persona=persona, status=True).order_by('-fecha_creacion')

                    if search:
                        data['s'] = search
                        solicitudes = solicitudes.filter(nombre__icontains=search)

                        url_vars += '&s=' + search

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
                    data['title'] = u'Solicitudes de Registro de Publicaciones'
                    data['enlaceatras'] = "/pro_produccioncientifica"
                    return render(request, "pro_produccioncientifica/solicitudpublicacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'evidenciasarticulo':
                try:
                    title = u'Evidencias del Artículo'

                    data['articulo'] = articulos = ArticuloInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['evidencias'] = Evidencia.objects.filter(status=True, matrizevidencia_id=3).exclude(pk=30)

                    template = get_template("th_hojavida/detallearticulo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. [%s]" % msg})

            elif action == 'evidenciasponencia':
                try:
                    title = u'Evidencias de la Ponencia'

                    data['ponencias'] = ponencias = PonenciasInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['evidencias'] = Evidencia.objects.filter(status=True, matrizevidencia_id=4)

                    template = get_template("th_hojavida/detalleponencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. [%s]" % msg})

            elif action == 'evidenciaslibro':
                try:
                    title = u'Evidencias del Libro'

                    data['libros'] = libros = LibroInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['evidencias'] = Evidencia.objects.filter(status=True, matrizevidencia_id=6)

                    template = get_template("th_hojavida/detalledetallelibro.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. [%s]" % msg})

            elif action == 'evidenciascapitulo':
                try:
                    title = u'Evidencias del Capítulo de libro'

                    data['capitulos'] = capitulos = CapituloLibroInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['evidencias'] = Evidencia.objects.filter(status=True, matrizevidencia_id=7)

                    template = get_template("th_hojavida/detallecapitulo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. [%s]" % msg})

            elif action == 'addarticulo':
                try:
                    data['title'] = u'Agregar Solicitud de Registro de Artículo'
                    form = SolicitudRegArticuloPubForm()
                    data['form'] = form
                    data['tipos'] = TIPO_INTEGRANTE_PUBLICACION_F
                    data['filiaciones'] = TIPO_FILIACION_PUBLICACION_F
                    return render(request, "pro_produccioncientifica/addarticulo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarticulo':
                try:
                    data['title'] = u'Editar Solicitud de Registro de Artículo'
                    solicitudpublicacion = SolicitudPublicacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitudpublicacion'] = solicitudpublicacion

                    form = SolicitudRegArticuloPubForm(initial={
                        'titulo': solicitudpublicacion.nombre,
                        'resumen': solicitudpublicacion.motivo,
                        'revista': solicitudpublicacion.revistainvestigacion,
                        'existerevista': True if solicitudpublicacion.revista else False,
                        'nombrerevista': solicitudpublicacion.revista,
                        'estadopublicacion': solicitudpublicacion.estadopublicacion,
                        'fechapublicacion': solicitudpublicacion.fechapublicacion,
                        'fechaaceptacion': solicitudpublicacion.fechaaprobacion,
                        'fechatentpublicacion': solicitudpublicacion.fechatentpublicacion,
                        'enlace': solicitudpublicacion.enlace,
                        'numerorevista': solicitudpublicacion.numero,
                        'volumenrevista': solicitudpublicacion.volumen,
                        'paginaarticulorevista': solicitudpublicacion.paginas,
                        'campoamplio': solicitudpublicacion.areaconocimiento,
                        'campoespecifico': solicitudpublicacion.subareaconocimiento,
                        'campodetallado': solicitudpublicacion.subareaespecificaconocimiento,
                        'lineainvestigacion': solicitudpublicacion.lineainvestigacion,
                        'sublineainvestigacion': solicitudpublicacion.sublineainvestigacion,
                        'provieneproyecto': solicitudpublicacion.provieneproyecto,
                        'tipoproyecto': solicitudpublicacion.tipoproyecto,
                        'proyectointerno': solicitudpublicacion.proyectointerno,
                        'proyectoexterno': solicitudpublicacion.proyectoexterno,
                        'pertenecegrupoinv': solicitudpublicacion.pertenecegrupoinv,
                        'grupoinvestigacion': solicitudpublicacion.grupoinvestigacion
                    })

                    form.editar(solicitudpublicacion)
                    data['participantes'] = participantes = solicitudpublicacion.participantes()
                    data['totalparticipantes'] = len(participantes)
                    data['form'] = form
                    data['tipos'] = TIPO_INTEGRANTE_PUBLICACION_F
                    data['filiaciones'] = TIPO_FILIACION_PUBLICACION_F

                    return render(request, "pro_produccioncientifica/editarticulo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addproceeding':
                try:
                    data['title'] = u'Agregar Solicitud de Registro de Proceeding (Artículo de congreso)'
                    form = SolicitudRegProceedingPubForm()
                    data['form'] = form
                    data['tipos'] = TIPO_INTEGRANTE_PUBLICACION_F
                    data['filiaciones'] = TIPO_FILIACION_PUBLICACION_F
                    return render(request, "pro_produccioncientifica/addproceeding.html", data)
                except Exception as ex:
                    pass

            elif action == 'editproceeding':
                try:
                    data['title'] = u'Editar Solicitud de Registro de Proceeding (Artículo de congreso)'
                    solicitudpublicacion = SolicitudPublicacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitudpublicacion'] = solicitudpublicacion

                    form = SolicitudRegProceedingPubForm(initial={
                        'titulo': solicitudpublicacion.nombre,
                        'resumen': solicitudpublicacion.motivo,
                        'congreso': solicitudpublicacion.revistainvestigacion,
                        'existecongreso': True if solicitudpublicacion.revista else False,
                        'nombrecongreso': solicitudpublicacion.revista,
                        'fecharecepcion': solicitudpublicacion.fecharecepcion,
                        'fechaaprobacion': solicitudpublicacion.fechaaprobacion,
                        'fechapublicacion': solicitudpublicacion.fechapublicacion,
                        'enlace': solicitudpublicacion.enlace,
                        'edicioncongreso': solicitudpublicacion.numero,
                        'volumenmemoria': solicitudpublicacion.volumen,
                        'paginaarticulomemoria': solicitudpublicacion.paginas,
                        'campoamplio': solicitudpublicacion.areaconocimiento,
                        'campoespecifico': solicitudpublicacion.subareaconocimiento,
                        'campodetallado': solicitudpublicacion.subareaespecificaconocimiento,
                        'lineainvestigacion': solicitudpublicacion.lineainvestigacion,
                        'sublineainvestigacion': solicitudpublicacion.sublineainvestigacion,
                        'provieneproyecto': solicitudpublicacion.provieneproyecto,
                        'tipoproyecto': solicitudpublicacion.tipoproyecto,
                        'proyectointerno': solicitudpublicacion.proyectointerno,
                        'proyectoexterno': solicitudpublicacion.proyectoexterno,
                        'pertenecegrupoinv': solicitudpublicacion.pertenecegrupoinv,
                        'grupoinvestigacion': solicitudpublicacion.grupoinvestigacion
                    })

                    form.editar(solicitudpublicacion)
                    data['participantes'] = participantes = solicitudpublicacion.participantes()
                    data['totalparticipantes'] = len(participantes)
                    data['form'] = form
                    data['tipos'] = TIPO_INTEGRANTE_PUBLICACION_F
                    data['filiaciones'] = TIPO_FILIACION_PUBLICACION_F

                    return render(request, "pro_produccioncientifica/editproceeding.html", data)
                except Exception as ex:
                    pass

            elif action == 'addponencia':
                try:
                    data['title'] = u'Agregar Solicitud de Registro de Ponencia Publicada'
                    form = SolicitudRegPonenciaPubForm()
                    data['form'] = form
                    data['tipos'] = TIPO_INTEGRANTE_PUBLICACION_F
                    data['filiaciones'] = TIPO_FILIACION_PUBLICACION_F
                    return render(request, "pro_produccioncientifica/addponencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'editponencia':
                try:
                    data['title'] = u'Editar Solicitud de Registro de Ponencia Publicada'
                    solicitudpublicacion = SolicitudPublicacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitudpublicacion'] = solicitudpublicacion

                    form = SolicitudRegPonenciaPubForm(initial={
                        'titulo': solicitudpublicacion.nombre,
                        'resumen': solicitudpublicacion.motivo,
                        'congreso': solicitudpublicacion.evento,
                        'pais': solicitudpublicacion.pais,
                        'ciudad': solicitudpublicacion.ciudad,
                        'fechainicio': solicitudpublicacion.fecharecepcion,
                        'fechafin': solicitudpublicacion.fechaaprobacion,
                        'enlace': solicitudpublicacion.enlace,
                        'fechapublicacion': solicitudpublicacion.fechapublicacion,
                        'campoamplio': solicitudpublicacion.areaconocimiento,
                        'campoespecifico': solicitudpublicacion.subareaconocimiento,
                        'campodetallado': solicitudpublicacion.subareaespecificaconocimiento,
                        'lineainvestigacion': solicitudpublicacion.lineainvestigacion,
                        'sublineainvestigacion': solicitudpublicacion.sublineainvestigacion,
                        'provieneproyecto': solicitudpublicacion.provieneproyecto,
                        'tipoproyecto': solicitudpublicacion.tipoproyecto,
                        'proyectointerno': solicitudpublicacion.proyectointerno,
                        'proyectoexterno': solicitudpublicacion.proyectoexterno,
                        'pertenecegrupoinv': solicitudpublicacion.pertenecegrupoinv,
                        'grupoinvestigacion': solicitudpublicacion.grupoinvestigacion
                    })

                    form.editar(solicitudpublicacion)

                    data['participantes'] = participantes = solicitudpublicacion.participantes()
                    data['totalparticipantes'] = len(participantes)
                    data['form'] = form
                    data['tipos'] = TIPO_INTEGRANTE_PUBLICACION_F
                    data['filiaciones'] = TIPO_FILIACION_PUBLICACION_F
                    data['integrantescomite'] = integrantes = solicitudpublicacion.integrantes_comite_cientifico_ponencia()
                    data['totalintegrantes'] = len(integrantes)
                    return render(request, "pro_produccioncientifica/editponencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'addlibro':
                try:
                    data['title'] = u'Agregar Solicitud de Registro de Libro Publicado'
                    form = SolicitudRegLibroPubForm()
                    data['form'] = form
                    data['tipos'] = TIPO_INTEGRANTE_PUBLICACION_F
                    data['filiaciones'] = TIPO_FILIACION_PUBLICACION_F
                    return render(request, "pro_produccioncientifica/addlibro.html", data)
                except Exception as ex:
                    pass

            elif action == 'editlibro':
                try:
                    data['title'] = u'Editar Solicitud de Registro de Libro Publicado'
                    solicitudpublicacion = SolicitudPublicacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitudpublicacion'] = solicitudpublicacion

                    form = SolicitudRegLibroPubForm(initial={
                        'titulo': solicitudpublicacion.nombre,
                        'codigoisbn': solicitudpublicacion.codigoisbn,
                        'editor': solicitudpublicacion.editorcompilador,
                        'fechapublicacion': solicitudpublicacion.fechapublicacion,
                        'campoamplio': solicitudpublicacion.areaconocimiento,
                        'campoespecifico': solicitudpublicacion.subareaconocimiento,
                        'campodetallado': solicitudpublicacion.subareaespecificaconocimiento,
                        'lineainvestigacion': solicitudpublicacion.lineainvestigacion,
                        'sublineainvestigacion': solicitudpublicacion.sublineainvestigacion,
                        'provieneproyecto': solicitudpublicacion.provieneproyecto,
                        'tipoproyecto': solicitudpublicacion.tipoproyecto,
                        'proyectointerno': solicitudpublicacion.proyectointerno,
                        'proyectoexterno': solicitudpublicacion.proyectoexterno,
                        'pertenecegrupoinv': solicitudpublicacion.pertenecegrupoinv,
                        'grupoinvestigacion': solicitudpublicacion.grupoinvestigacion,
                        'revisadopar': solicitudpublicacion.revisadopar
                    })

                    form.editar(solicitudpublicacion)

                    data['participantes'] = participantes = solicitudpublicacion.participantes()
                    data['totalparticipantes'] = len(participantes)
                    data['form'] = form
                    data['tipos'] = TIPO_INTEGRANTE_PUBLICACION_F
                    data['filiaciones'] = TIPO_FILIACION_PUBLICACION_F

                    return render(request, "pro_produccioncientifica/editlibro.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcapitulo':
                try:
                    data['title'] = u'Agregar Solicitud de Registro de Capítulo de Libro Publicado'
                    form = SolicitudRegCapituloLibroPubForm()
                    data['form'] = form
                    data['tipos'] = TIPO_INTEGRANTE_PUBLICACION_F
                    data['filiaciones'] = TIPO_FILIACION_PUBLICACION_F
                    return render(request, "pro_produccioncientifica/addcapitulo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcapitulo':
                try:
                    data['title'] = u'Editar Solicitud de Registro de Capítulo de Libro Publicado'
                    solicitudpublicacion = SolicitudPublicacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitudpublicacion'] = solicitudpublicacion

                    form = SolicitudRegCapituloLibroPubForm(initial={
                        'titulocapitulo': solicitudpublicacion.nombre,
                        'titulolibro': solicitudpublicacion.evento,
                        'codigoisbn': solicitudpublicacion.codigoisbn,
                        'pagina': solicitudpublicacion.paginas,
                        'editor': solicitudpublicacion.editorcompilador,
                        'totalcapitulo': solicitudpublicacion.totalcapitulo,
                        'fechapublicacion': solicitudpublicacion.fechapublicacion,
                        'campoamplio': solicitudpublicacion.areaconocimiento,
                        'campoespecifico': solicitudpublicacion.subareaconocimiento,
                        'campodetallado': solicitudpublicacion.subareaespecificaconocimiento,
                        'lineainvestigacion': solicitudpublicacion.lineainvestigacion,
                        'sublineainvestigacion': solicitudpublicacion.sublineainvestigacion,
                        'provieneproyecto': solicitudpublicacion.provieneproyecto,
                        'tipoproyecto': solicitudpublicacion.tipoproyecto,
                        'proyectointerno': solicitudpublicacion.proyectointerno,
                        'proyectoexterno': solicitudpublicacion.proyectoexterno,
                        'pertenecegrupoinv': solicitudpublicacion.pertenecegrupoinv,
                        'grupoinvestigacion': solicitudpublicacion.grupoinvestigacion,
                        'revisadopar': solicitudpublicacion.revisadopar
                    })

                    form.editar(solicitudpublicacion)

                    data['participantes'] = participantes = solicitudpublicacion.participantes()
                    data['totalparticipantes'] = len(participantes)
                    data['form'] = form
                    data['tipos'] = TIPO_INTEGRANTE_PUBLICACION_F
                    data['filiaciones'] = TIPO_FILIACION_PUBLICACION_F

                    return render(request, "pro_produccioncientifica/editcapitulo.html", data)
                except Exception as ex:
                    pass

            elif action == 'mostrarinformacion':
                try:
                    title = u'Información de la Solicitud de Registro de Publicación'
                    solicitudpublicacion = SolicitudPublicacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitud'] = solicitudpublicacion
                    data['evidencias'] = solicitudpublicacion.evidencias()
                    data['participantes'] = solicitudpublicacion.participantes()
                    template = get_template("pro_produccioncientifica/informacionsolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addparticipante':
                try:
                    data['title'] = u'Agregar Participante de la Publicación'
                    data['tipospersona'] = TIPO_PERSONA_PUBLICACION_F
                    data['tipos'] = TIPO_INTEGRANTE_PUBLICACION_F
                    data['filiaciones'] = TIPO_FILIACION_PUBLICACION_F
                    template = get_template("pro_produccioncientifica/addparticipante.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscarprofesor':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Profesor.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                        | Q(persona__apellido2__icontains=s[0])
                                                        | Q(persona__cedula__icontains=s[0])
                                                        | Q(persona__ruc__icontains=s[0])
                                                        | Q(persona__pasaporte__icontains=s[0]),
                                                        status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        personas = Profesor.objects.filter(persona__apellido1__icontains=s[0],
                                                           persona__apellido2__icontains=s[1],
                                                           status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso()), "identificacion": x.persona.identificacion(), "idpersona": x.persona.id, "usuario": x.persona.usuario.username if x.persona.usuario else '', "emailinst": x.persona.emailinst, "email": x.persona.email, "celular": x.persona.telefono, "telefono": x.persona.telefono_conv, "nombre": x.persona.nombre_completo_inverso() } for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscarexterno':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Externo.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                      | Q(persona__apellido2__icontains=s[0])
                                                      | Q(persona__cedula__icontains=s[0])
                                                      | Q(persona__pasaporte__icontains=s[0])
                                                      | Q(persona__ruc__icontains=s[0]),
                                                      status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        personas = Externo.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                        & Q(persona__apellido2__icontains=s[1]),
                                                           status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    # data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso())} for x in personas]}
                    if not 'opt' in request.GET:
                        data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso()), "identificacion": x.persona.identificacion(), "idpersona": x.persona.id, "usuario": x.persona.usuario.username if x.persona.usuario else '', "emailinst": x.persona.emailinst, "email": x.persona.email, "celular": x.persona.telefono, "telefono": x.persona.telefono_conv, "nombre": x.persona.nombre_completo_inverso()} for x in personas]}
                    else:
                        data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso()), "identificacion": x.persona.identificacion(), "idpersona": x.persona.id, "usuario": x.persona.usuario.username if x.persona.usuario else '', "emailinst": x.persona.emailinst, "email": x.persona.email, "celular": x.persona.telefono, "telefono": x.persona.telefono_conv, "nombre": x.persona.nombre_completo_inverso(), "cantgruposvigentes": x.persona.cantidad_grupos_investigacion_vigente()} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscaralumno':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Inscripcion.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                      | Q(persona__apellido2__icontains=s[0])
                                                      | Q(persona__cedula__icontains=s[0])
                                                      | Q(persona__pasaporte__icontains=s[0])
                                                      | Q(persona__ruc__icontains=s[0]),
                                                      status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        personas = Inscripcion.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                               & Q(persona__apellido2__icontains=s[1]),
                                                           status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    personas = personas.filter(persona__perfilusuario__visible=True, persona__perfilusuario__status=True).exclude(coordinacion_id=9).distinct()

                    if not 'opt' in request.GET:
                        data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso()) + ' - ' + x.carrera.nombre, "idpersona": x.persona.id, "nombre": x.persona.nombre_completo_inverso()} for x in personas]}
                    else:
                        data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso()) + ' - ' + x.carrera.nombre, "idpersona": x.persona.id, "nombre": x.persona.nombre_completo_inverso(), "cantgruposvigentes": x.persona.cantidad_grupos_investigacion_vigente()} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

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
                        personas = Administrativo.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                               & Q(persona__apellido2__icontains=s[1]),
                                                           status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso()), "idpersona": x.persona.id, "nombre": x.persona.nombre_completo_inverso()} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'eliminar':
                try:
                    data['title'] = u'Eliminar Producción Científica'
                    data['tipo'] = tipo = request.GET['tipo']
                    pronombre = ''

                    if tipo == 'A':
                        articulo = ArticuloInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                        data['id'] = articulo.id
                        data['titulo'] = articulo.nombre
                        data['tipoproduccion'] = articulo.get_tipoarticulo_display()
                        pronombre = 'el'
                    elif tipo == 'P':
                        ponencia = PonenciasInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                        data['id'] = ponencia.id
                        data['titulo'] = ponencia.nombre
                        data['tipoproduccion'] = "PONENCIA"
                        pronombre = 'la'
                    elif tipo == 'L':
                        libro = LibroInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                        data['id'] = libro.id
                        data['titulo'] = libro.nombrelibro
                        data['tipoproduccion'] = "LIBRO"
                        pronombre = 'el'
                    else:
                        capitulo = CapituloLibroInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                        data['id'] = capitulo.id
                        data['titulo'] = capitulo.titulocapitulo
                        data['tipoproduccion'] = "CAPITULO DE LIBRO"
                        pronombre = 'el'

                    template = get_template("pro_produccioncientifica/eliminar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title'], 'tituloproduccion': data['titulo'], 'tipoproduccion': data['tipoproduccion'], 'pronombre': pronombre})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            return HttpResponseRedirect(request.path)
            # Fin GET (action)
        else:
            try:
                data['title'] = u'Mi Producción Científica'

                # Consulta los artículos
                data['articulos'] = ArticuloInvestigacion.objects.select_related().filter((Q(
                    participantesarticulos__profesor__persona=persona) | Q(
                    participantesarticulos__administrativo__persona=persona) | Q(
                    participantesarticulos__inscripcion__persona=persona)),
                    status=True, aprobado=True,
                    participantesarticulos__status=True).order_by('-fechapublicacion')

                # Consulta las ponencias
                data['ponencias'] = PonenciasInvestigacion.objects.select_related().filter((Q(
                    participanteponencias__profesor__persona=persona) | Q(
                    participanteponencias__administrativo__persona=persona) | Q(
                    participanteponencias__inscripcion__persona=persona)),
                    status=True, participanteponencias__status=True).order_by('-fechapublicacion')

                # Consulta los libros
                data['libros'] = LibroInvestigacion.objects.select_related().filter((Q(
                    participantelibros__profesor__persona=persona) | Q(participantelibros__profesor__persona=persona)),
                    status=True, participantelibros__status=True).order_by('-fechapublicacion')

                # Consulta los capítulos de libros
                data['capitulolibro'] = CapituloLibroInvestigacion.objects.select_related().filter((Q(
                    participantecapitulolibros__profesor__persona=persona) | Q(
                    participantecapitulolibros__profesor__persona=persona)),
                    status=True, participantecapitulolibros__status=True).order_by('-fechapublicacion')

                data['enlaceatras'] = "/pro_investigacion"
                return render(request, "pro_produccioncientifica/view.html", data)
            except Exception as ex:
                pass


def notificar_solicitud(solicitudpublicacion, actualizacion):
    persona = solicitudpublicacion.persona

    # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
    listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec
    fechaenvio = datetime.now().date()
    horaenvio = datetime.now().time()

    # E-mail del destinatario
    lista_email_envio = persona.lista_emails_envio()
    # lista_email_envio = ['isaltosm@unemi.edu.ec']
    lista_email_cco = []
    lista_adjuntos = []

    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

    if not actualizacion:
        tituloemail = "Solicitud de Registro de Producción Científica"
        tiponotificacion = "REGSOL"
    else:
        tituloemail = "Actualización Solicitud de Registro de Producción Científica"
        tiponotificacion = "REGSOLACT"

    titulo = "Producción Científica"

    # Notifica al solicitante
    send_html_mail(tituloemail,
                   "emails/solicitudpublicacion.html",
                   {'sistema': u'SGA - UNEMI',
                    'titulo': titulo,
                    'fecha': fechaenvio,
                    'hora': horaenvio,
                    'tiponotificacion': tiponotificacion,
                    'saludo': 'Estimada' if persona.sexo_id == 1 else 'Estimado',
                    'nombrepersona': persona.nombre_completo_inverso(),
                    'solicitudpublicacion': solicitudpublicacion
                    },
                   lista_email_envio,
                   lista_email_cco,
                   lista_adjuntos,
                   cuenta=CUENTAS_CORREOS[cuenta][1]
                   )

    # Notifica a la Coordinación de Investigación
    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

    tiponotificacion = "REGCOORDINV" if not actualizacion else "REGCOORDINVACT"

    lista_email_envio = ['produccioncientifica@unemi.edu.ec']
    # lista_email_envio = ['isaltosm@unemi.edu.ec']

    send_html_mail(tituloemail,
                   "emails/solicitudpublicacion.html",
                   {'sistema': u'SGA - UNEMI',
                    'titulo': titulo,
                    'fecha': fechaenvio,
                    'hora': horaenvio,
                    'tiponotificacion': tiponotificacion,
                    'saludo': 'Estimados',
                    'nombresolicitante': persona.nombre_completo_inverso(),
                    'solicitudpublicacion': solicitudpublicacion
                    },
                   lista_email_envio,
                   lista_email_cco,
                   lista_adjuntos,
                   cuenta=CUENTAS_CORREOS[cuenta][1]
                   )
