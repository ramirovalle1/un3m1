# -*- coding: UTF-8 -*-
import io
import json
import sys
import pyqrcode
import os

from datetime import time, timedelta, date
import requests
import xlwt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from http_ece import decrypt
from unidecode import unidecode
from xlwt import easyxf, XFStyle, Workbook
import random

from core.firmar_documentos import verificarFirmasPDF
from core.firmar_documentos_ec import JavaFirmaEc
from core.firmar_documentos_ec_descentralizada import qrImgFirma
from settings import SITE_STORAGE
from decorators import secure_module
from sagest.models import datetime, Banco
from sga.commonviews import adduserdata
from sga.forms import RequisitoActividadConvalidacionForm,RecomendacionActividadPPVForm, ActividadConvalidacionVoluntariadoForm,ActividadConvalidacionForm, AsignacionProfesorActividadForm, InscripcionManualActividadExtracurricularForm
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, generar_nombre, \
    remover_caracteres_especiales_unicode, convertirfecha2, convertir_fecha_invertida
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqrinformepractividadextra
from sga.models import Persona, \
    BecaSolicitudRecorrido, BecaSolicitud, miinstitucion, SolicitudDevolucionDinero, \
    RecomendacionesActividadConvalidacionPPV, SolicitudDevolucionDineroRecorrido, \
    CUENTAS_CORREOS, ActividadConvalidacionPPV, DetalleActividadConvalidacionPPV, InscripcionActividadConvalidacionPPV, \
    PracticasPreprofesionalesInscripcion, ParticipantesMatrices, DetalleEvidenciasPracticasPro, Inscripcion, Carrera, \
    ESTADO_ACTIVIDAD_CONVALIDACION, Matricula, Profesor, Notificacion, Periodo, RequisitosActividadConvalidacionPPV, \
    InscripcionRequisitosActividadConvalidacionPPV, CoordinadorCarrera, ItinerariosMalla
from django.template import Context
from django.template.loader import get_template, render_to_string

import time as ET

from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    # data['periodo'] = periodo = request.session['periodo']
    periodo = request.session['periodo']
    data['perfilprincipal'] = perfilprincipal = request.session['perfilprincipal']
    hayrequisito = False
    opcion = 0
    listo = None
    id2 = 1
    cargosactuales = persona.mis_cargos_actuales().values_list('id', flat=True)
    miscarreras = persona.mis_carreras_tercer_nivel()
    es_director_carr = True if miscarreras else False
    es_docente = persona.es_profesor() and perfilprincipal.profesor
    #es_analista_vincu = perfilprincipal.administrativo and 554 in cargosactuales

    es_director_vincu = persona.departamentodireccionvinculacion() and perfilprincipal.administrativo
    eModulosGrupos = data["grupos_usuarios"].filter(id__in=variable_valor('VALIDACION_GRUPO_EXTRACURRICULAR')).exists()
    serviciocomunitario_carreras = variable_valor('VARIOS_SERVICIOCOMUNITARIO_CARRERAS')
    practica_carreras = variable_valor('VARIOS_PRACTICA_CARRERAS')

    if not es_director_carr and not es_docente and not es_director_vincu and not eModulosGrupos:
        return HttpResponseRedirect("/?info=El Módulo está disponible para personal autorizado.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'actualizarformatoactividades':
            try:
                listadoids, id = request.POST.getlist('idslistados[]'), request.POST['id']
                actividad = ActividadConvalidacionPPV.objects.get(pk=id)
                if listadoids:
                    for iddetalle in listadoids:
                        detalle = DetalleActividadConvalidacionPPV.objects.get(pk=int(iddetalle))
                        if 'formato{}'.format(iddetalle) in request.FILES:
                            formato = request.FILES['formato{}'.format(iddetalle)]
                            nombredocumento = actividad.titulo
                            nombrecompletodocumento = remover_caracteres_especiales_unicode(nombredocumento).lower().replace(' ', '_')
                            formato._name = generar_nombre(nombrecompletodocumento, formato._name)
                            if formato.size > 10485760:
                                return JsonResponse({"result": True, "mensaje": "Error, archivo mayor a 10 Mb."}, safe=False)
                            detalle.formato = formato
                        detalle.save(request)
                        log(u'Edito Formato de Actividad Extracurrricular: %s' % actividad, request, "edit")
                return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": ex}, safe=False)
            
        elif action == 'addinscritomanual':
            try:
                idestudiante, id = request.POST['idestudiante'], request.POST['id']
                idinscripcion = Inscripcion.objects.get(pk=idestudiante)
                actividad = ActividadConvalidacionPPV.objects.get(pk=id)
                permite_varios_servicio = str(idinscripcion.carrera.id) in serviciocomunitario_carreras if serviciocomunitario_carreras else False
                permite_varios_practica = str(idinscripcion.carrera.id) in practica_carreras if practica_carreras else False
                if actividad.tipoactividad == 1: selecciona_varios = permite_varios_practica
                else: selecciona_varios = permite_varios_servicio
                if not idinscripcion.perfil_inscripcion():
                    return JsonResponse(
                        {"result": False, "mensaje": u"La inscripción no se encuentra activa"})

                # if not actividad.en_fecha_inscripcion():
                #     return JsonResponse({"result": False, "mensaje": u"El periodo de inscripción ha finalizado"})
                #
                # # if actividad.alumno_inscrito_actividad(idinscripcion):
                #     return JsonResponse(
                #         {"result": False, "mensaje": u"Usted ya está inscrito en la actividad seleccionada"})

                if not selecciona_varios and actividad.validacion_inscritos(idinscripcion, periodo):
                    return JsonResponse(
                        {"result": False, "mensaje": u"Estudiante ya se ha inscrito en otra actividad"})

                if actividad.validacion_nivel_actv(idinscripcion):
                    return JsonResponse(
                        {"result": False, "mensaje": u"Estudiante no pertenece al nivel de la actividad"})

                if actividad.total_cupo_disponible() < 1:
                    return JsonResponse({"result": False,
                                         "mensaje": u"No existen cupos disponibles para inscribirse en la actividad seleccionada"})


                if InscripcionActividadConvalidacionPPV.objects.filter(actividad=actividad, inscripcion=idinscripcion, status=True, estado=1).exists():
                    return JsonResponse({"result": False,
                                         "mensaje": u"El estudiante ya se encuentra pre-inscrito en esta actividad"})

                elif InscripcionActividadConvalidacionPPV.objects.filter(actividad=actividad, inscripcion=idinscripcion, status=True, estado=2).exists():
                    return JsonResponse({"result": False,
                                         "mensaje": u"El estudiante ya se encuentra inscrito en esta actividad"})
                else:
                    inscripcion = InscripcionActividadConvalidacionPPV(actividad=actividad, inscripcion=idinscripcion,
                                                                       status=True, estado=1)
                    inscripcion.save(request)
                    log(u'%s agregó inscripción en la actividad de convalidación PPV: %s' % (persona, actividad), request, "add")

                    # Envío de correo al estudiante
                    cuenta = cuenta_email_disponible()
                    tituloemail = "Inscripción Actividad Extracurricular"
                    estudiante = idinscripcion.persona
                    saludo = 'Estimado(a)'
                    if estudiante.sexo:
                        saludo = 'Estimada' if estudiante.sexo.id == 1 else 'Estimado'

                    send_html_mail(tituloemail,
                                   "emails/inscripcionactividadppv.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'accion': 'INSCRIPCION',
                                    'fecha': datetime.now().date(),
                                    'hora': datetime.now().time(),
                                    'saludo': saludo,
                                    'estudiante': estudiante,
                                    'actividad': actividad.titulo,
                                    'periodo': actividad.periodo.nombre,
                                    't': miinstitucion()
                                    },
                                   estudiante.lista_emails_envio(),
                                   [],
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )
                    # Envío de correo al profesor líder para que acepte o rechace la inscripción
                    cuenta = cuenta_email_disponible()
                    tituloemail = "Inscripción de Estudiante a Actividad Extracurricular"
                    docente = actividad.profesor.persona

                    if docente.sexo:
                        saludo = 'Estimada' if docente.sexo.id == 1 else 'Estimado'

                    send_html_mail(tituloemail,
                                   "emails/inscripcionactividadppv.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'accion': 'NOTIFICADOCENTE',
                                    'fecha': datetime.now().date(),
                                    'hora': datetime.now().time(),
                                    'saludo': saludo,
                                    'docente': docente,
                                    'estudiante': estudiante,
                                    'actividad': actividad.titulo,
                                    'periodo': actividad.periodo.nombre,
                                    't': miinstitucion()
                                    },
                                   docente.lista_emails_envio(),
                                   [],
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )
                    return JsonResponse({"result": True})
            except Exception as ex:
                return JsonResponse({"result": False, 'mensaje': str(ex)})

        elif action == 'addactividad':
            try:
                if es_director_vincu:
                    f = ActividadConvalidacionVoluntariadoForm(request.POST, request.FILES)
                else:
                    f = ActividadConvalidacionForm(request.POST, request.FILES)

                if 'archivoresolucion' in request.FILES:
                    arch = request.FILES['archivoresolucion']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. [Resolución Consejo Directivo]"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf [Resolución Consejo Directivo]"})

                if 'archivoproyecto' in request.FILES:
                    arch = request.FILES['archivoproyecto']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. [Proyecto Actividad ExtraCurricular]"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf [Proyecto Actividad ExtraCurricular]"})

                if f.is_valid():
                    if ActividadConvalidacionPPV.objects.filter(status=True, titulo=f.cleaned_data['titulo']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El título para la actividad ya existe."})

                    if f.cleaned_data['inicioinscripcion'] >= f.cleaned_data['fininscripcion']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha de fin de inscripciones debe ser mayor a la fecha de inicio."})

                    # if f.cleaned_data['fininscripcion'] >= f.cleaned_data['fechainicio']:
                    #     return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio de la actividad debe ser mayor a la fecha de fin de inscripción"})

                    if f.cleaned_data['fechainicio'] >= f.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha de fin de la actividad debe ser mayor a la fecha de inicio."})

                    archivoresolucion = request.FILES['archivoresolucion']
                    archivoresolucion._name = generar_nombre("resolucion", archivoresolucion._name)
                    archivoproyecto = request.FILES['archivoproyecto']
                    archivoproyecto._name = generar_nombre("proyecto", archivoproyecto._name)
                    # volun_estado = False
                    # if es_director_vincu:
                    #     volun_estado = True


                    actividadconvalidacion = ActividadConvalidacionPPV(periodo=periodo,
                                                                       director=persona,
                                                                       titulo=f.cleaned_data['titulo'],
                                                                       tipoactividad=f.cleaned_data[
                                                                           'tipoactividad'],
                                                                       fechainicio=f.cleaned_data['fechainicio'],
                                                                       fechafin=f.cleaned_data['fechafin'],
                                                                       horas=f.cleaned_data['horas'],
                                                                       profesor=f.cleaned_data['profesor'],
                                                                       inicioinscripcion=f.cleaned_data[
                                                                           'inicioinscripcion'],
                                                                       fininscripcion=f.cleaned_data[
                                                                           'fininscripcion'],
                                                                       cupo=f.cleaned_data['cupo'],
                                                                       archivoresolucion=archivoresolucion,
                                                                       archivoproyecto=archivoproyecto,
                                                                       nivelminimo=f.cleaned_data['nivelminimo'] if
                                                                       f.cleaned_data['nivelminimo'] else None,
                                                                       voluntariado=f.cleaned_data['voluntariado'],
                                                                       itinerariomalla=f.cleaned_data['itinerario'],)
                    actividadconvalidacion.save(request)
                    actividadconvalidacion.carrera.clear()
                    #PRACTICAS PREPROFESIONALES
                    if int(actividadconvalidacion.tipoactividad) == 1:
                        if f.cleaned_data['carrera']:
                            actividadconvalidacion.carrera.add(f.cleaned_data['carrera'])
                    #PROYECTOS DE VINCULACION
                    elif int(actividadconvalidacion.tipoactividad) == 2:
                        for data in f.cleaned_data['carreramultiple']:
                            actividadconvalidacion.carrera.add(data)
                    actividadconvalidacion.save(request)

                    # Envío de correo
                    cuenta = cuenta_email_disponible()
                    tituloemail = "Asignación como profesor líder de Actividad Extracurricular"
                    docente = actividadconvalidacion.profesor.persona

                    send_html_mail(tituloemail,
                                   "emails/ingresoactividadppv.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'fecha': datetime.now().date(),
                                    'hora': datetime.now().time(),
                                    'saludo': 'Estimada' if docente.sexo.id == 1 else 'Estimado',
                                    'docente': docente,
                                    'actividad': actividadconvalidacion.titulo,
                                    'periodo': actividadconvalidacion.periodo.nombre,
                                    't': miinstitucion()
                                    },
                                   docente.lista_emails_envio(),
                                   [],
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                    # Temporizador para evitar que se bloquee el servicion de gmail
                    ET.sleep(5)

                    log(u'Adicionó actividad extracurricular de convalidación PPV: %s' % actividadconvalidacion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'addactividadvoluntariado':
            try:
                f = ActividadConvalidacionVoluntariadoForm(request.POST, request.FILES)

                if 'archivoresolucion' in request.FILES:
                    arch = request.FILES['archivoresolucion']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad",
                                             "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. [Resolución Consejo Directivo]"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad",
                                             "mensaje": u"Solo se permiten archivos .pdf [Resolución Consejo Directivo]"})

                if 'archivoproyecto' in request.FILES:
                    arch = request.FILES['archivoproyecto']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad",
                                             "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. [Proyecto Actividad ExtraCurricular]"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad",
                                             "mensaje": u"Solo se permiten archivos .pdf [Proyecto Actividad ExtraCurricular]"})

                if f.is_valid():
                    if ActividadConvalidacionPPV.objects.filter(status=True, titulo=f.cleaned_data['titulo']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El título para la actividad ya existe."})

                    if f.cleaned_data['inicioinscripcion'] >= f.cleaned_data['fininscripcion']:
                        return JsonResponse({"result": "bad",
                                             "mensaje": u"La fecha de fin de inscripciones debe ser mayor a la fecha de inicio."})

                    # if f.cleaned_data['fininscripcion'] >= f.cleaned_data['fechainicio']:
                    #     return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio de la actividad debe ser mayor a la fecha de fin de inscripción"})

                    if f.cleaned_data['fechainicio'] >= f.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad",
                                             "mensaje": u"La fecha de fin de la actividad debe ser mayor a la fecha de inicio."})

                    archivoresolucion = request.FILES['archivoresolucion']
                    archivoresolucion._name = generar_nombre("resolucion", archivoresolucion._name)
                    archivoproyecto = request.FILES['archivoproyecto']
                    archivoproyecto._name = generar_nombre("proyecto", archivoproyecto._name)

                    actividadconvalidacion = ActividadConvalidacionPPV(periodo=periodo,
                                                                       director=persona,
                                                                       titulo=f.cleaned_data['titulo'],
                                                                       tipoactividad=f.cleaned_data[
                                                                           'tipoactividad'],
                                                                       fechainicio=f.cleaned_data['fechainicio'],
                                                                       fechafin=f.cleaned_data['fechafin'],
                                                                       horas=f.cleaned_data['horas'],
                                                                       profesor=f.cleaned_data['profesor'],
                                                                       inicioinscripcion=f.cleaned_data[
                                                                           'inicioinscripcion'],
                                                                       fininscripcion=f.cleaned_data[
                                                                           'fininscripcion'],
                                                                       cupo=f.cleaned_data['cupo'],
                                                                       archivoresolucion=archivoresolucion,
                                                                       archivoproyecto=archivoproyecto,
                                                                       nivelminimo=f.cleaned_data['nivelminimo'] if
                                                                       f.cleaned_data['nivelminimo'] else None,
                                                                       voluntariado=True)
                    actividadconvalidacion.save(request)
                    actividadconvalidacion.carrera.clear()

                    # PRACTICAS PREPROFESIONALES
                    if int(actividadconvalidacion.tipoactividad) == 1:
                        if f.cleaned_data['carrera']:
                            actividadconvalidacion.carrera.add(f.cleaned_data['carrera'])
                    # PROYECTOS DE VINCULACION
                    elif int(actividadconvalidacion.tipoactividad) == 2:
                        for data in f.cleaned_data['carreramultiple']:
                            actividadconvalidacion.carrera.add(data)
                    actividadconvalidacion.save(request)

                    # for data in f.cleaned_data['carrera']:
                    #     actividadconvalidacion.carrera.add(data)
                    # actividadconvalidacion.save(request)

                    # Envío de correo
                    cuenta = cuenta_email_disponible()
                    tituloemail = "Asignación como profesor líder de Actividad Extracurricular"
                    docente = actividadconvalidacion.profesor.persona

                    send_html_mail(tituloemail,
                                   "emails/ingresoactividadppv.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'fecha': datetime.now().date(),
                                    'hora': datetime.now().time(),
                                    'saludo': 'Estimada' if docente.sexo.id == 1 else 'Estimado',
                                    'docente': docente,
                                    'actividad': actividadconvalidacion.titulo,
                                    'periodo': actividadconvalidacion.periodo.nombre,
                                    't': miinstitucion()
                                    },
                                   docente.lista_emails_envio(),
                                   [],
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                    # Temporizador para evitar que se bloquee el servicion de gmail
                    ET.sleep(5)

                    log(u'Adicionó actividad extracurricular de voluntariado PPV: %s' % actividadconvalidacion,
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'editactividad':
            try:
                f = ActividadConvalidacionForm(request.POST, request.FILES)
                enviarcorreo=False
                if 'archivoresolucion' in request.FILES:
                    arch = request.FILES['archivoresolucion']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. [Resolución Consejo Directivo]"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf [Resolución Consejo Directivo]"})

                if 'archivoproyecto' in request.FILES:
                    arch = request.FILES['archivoproyecto']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. [Proyecto Actividad ExtraCurricular]"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf [Proyecto Actividad ExtraCurricular]"})

                actividad = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.POST['id'])))

                if f.is_valid():
                    # if ActividadConvalidacionPPV.objects.filter(status=True, titulo=f.cleaned_data['titulo']).exclude(pk=actividad.id).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"El título para la actividad ya existe."})

                    if f.cleaned_data['inicioinscripcion'] >= f.cleaned_data['fininscripcion']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha de fin de inscripciones debe ser mayor a la fecha de inicio."})

                    # if f.cleaned_data['fininscripcion'] >= f.cleaned_data['fechainicio']:
                    #     return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio de la actividad debe ser mayor a la fecha de fin de inscripción"})

                    if f.cleaned_data['fechainicio'] >= f.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha de fin de la actividad debe ser mayor a la fecha de inicio."})

                    # carreras_original = [c.id for c in actividad.carrera.all()]
                    # carreras_formulario = [carrera.id for carrera in f.cleaned_data['carrera']]
                    # excluidas = [c for c in carreras_original if c not in carreras_formulario]
                    #
                    # if len(excluidas) > 0:
                    #     for c in excluidas:
                    #         if InscripcionActividadConvalidacionPPV.objects.values('id').filter(status=True, inscripcion__carrera_id=c).exists():
                    #             nombrecarrera = Carrera.objects.get(pk=c).nombre
                    #             return JsonResponse({"result": "bad", "mensaje": "No se puede excluir la carrera %s del listado de carreras." % (nombrecarrera)})
                    if not actividad.profesor:
                        enviarcorreo=True
                    actividad.titulo = f.cleaned_data['titulo']
                    actividad.fechainicio = f.cleaned_data['fechainicio']
                    actividad.fechafin = f.cleaned_data['fechafin']
                    actividad.horas = f.cleaned_data['horas']
                    actividad.fininscripcion = f.cleaned_data['fininscripcion']
                    actividad.cupo = f.cleaned_data['cupo']
                    actividad.profesor = f.cleaned_data['profesor']

                    if actividad.estado == 0:
                        actividad.estado = 1

                    actualiza_otros_campos = True
                    if actividad.total_alumnos_inscritos() > 0 or actividad.total_alumnos_preinscritos() > 0 or actividad.total_detalle_actividades_profesor() > 0:
                        actualiza_otros_campos = False

                    if actualiza_otros_campos:
                        actividad.tipoactividad = f.cleaned_data['tipoactividad']
                        actividad.inicioinscripcion = f.cleaned_data['inicioinscripcion']
                        actividad.nivelminimo = f.cleaned_data['nivelminimo'] if f.cleaned_data['nivelminimo'] else None

                    if 'archivoresolucion' in request.FILES:
                        archivoresolucion = request.FILES['archivoresolucion']
                        archivoresolucion._name = generar_nombre("resolucion", archivoresolucion._name)
                        actividad.archivoresolucion = archivoresolucion

                    if 'archivoproyecto' in request.FILES:
                        archivoproyecto = request.FILES['archivoproyecto']
                        archivoproyecto._name = generar_nombre("proyecto", archivoproyecto._name)
                        actividad.archivoproyecto = archivoproyecto

                    actividad.itinerariomalla = None
                    if int(actividad.tipoactividad) == 1:
                        actividad.itinerariomalla = f.cleaned_data['itinerario']
                    actividad.save(request)

                    actividad.carrera.clear()
                    # PRACTICAS PREPROFESIONALES
                    if int(actividad.tipoactividad) == 1:
                        if f.cleaned_data['carrera']:
                            actividad.carrera.add(f.cleaned_data['carrera'])
                    # PROYECTOS DE VINCULACION
                    elif int(actividad.tipoactividad) == 2:
                        for data in f.cleaned_data['carreramultiple']:
                            actividad.carrera.add(data)
                    actividad.save(request)

                    if enviarcorreo:
                        # Envío de correo
                        cuenta = cuenta_email_disponible()
                        tituloemail = "Asignación como profesor líder de Actividad Extracurricular"
                        docente = actividad.profesor.persona

                        send_html_mail(tituloemail,
                                       "emails/ingresoactividadppv.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        'saludo': 'Estimada' if docente.sexo.id == 1 else 'Estimado',
                                        'docente': docente,
                                        'actividad': actividad.titulo,
                                        'periodo': actividad.periodo.nombre,
                                        't': miinstitucion()
                                        },
                                       docente.lista_emails_envio(),
                                       [],
                                       cuenta=CUENTAS_CORREOS[cuenta][1]
                                       )

                        # Temporizador para evitar que se bloquee el servicion de gmail
                        ET.sleep(5)
                    log(u'Editó actividad extracurricular de convalidación PPV: %s' % actividad, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'dupliactividad':
            try:
                actividad = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.POST['id'])))
                # archivoresolucion = actividad.archivoresolucion
                # archivoresolucion._name = generar_nombre("resolucion", archivoresolucion._name)
                # archivoproyecto = actividad.archivoproyecto
                # archivoproyecto._name = generar_nombre("proyecto", archivoproyecto._name)

                actividadconvalidacion = ActividadConvalidacionPPV(periodo=actividad.periodo,
                                                                   director=actividad.director,
                                                                   titulo=actividad.titulo,
                                                                   tipoactividad=actividad.tipoactividad,
                                                                   fechainicio=actividad.fechainicio,
                                                                   fechafin=actividad.fechafin,
                                                                   horas=actividad.horas,
                                                                   estado=0,
                                                                   inicioinscripcion=actividad.inicioinscripcion,
                                                                   fininscripcion=actividad.fininscripcion,
                                                                   cupo=actividad.cupo,
                                                                   archivoresolucion=actividad.archivoresolucion,
                                                                   archivoproyecto=actividad.archivoproyecto,
                                                                   nivelminimo=actividad.nivelminimo,
                                                                   voluntariado=actividad.voluntariado, )
                actividadconvalidacion.save(request)


                log(u'Duplicó actividad extracurricular de convalidación PPV: %s' % actividadconvalidacion,
                    request, "dupliactividad")
                return JsonResponse({"result": False})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'eliminarecomendacion':
            try:
                recomendaciones = RecomendacionesActividadConvalidacionPPV.objects.get(id=int(request.POST['id']))
                recomendaciones.status = False
                recomendaciones.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "no"})

        elif action == 'editactividadvoluntariado':
            try:
                f = ActividadConvalidacionVoluntariadoForm(request.POST, request.FILES)

                if 'archivoresolucion' in request.FILES:
                    arch = request.FILES['archivoresolucion']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. [Resolución Consejo Directivo]"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf [Resolución Consejo Directivo]"})

                if 'archivoproyecto' in request.FILES:
                    arch = request.FILES['archivoproyecto']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. [Proyecto Actividad ExtraCurricular]"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf [Proyecto Actividad ExtraCurricular]"})

                actividad = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.POST['id'])))

                if f.is_valid():
                    # if ActividadConvalidacionPPV.objects.filter(status=True, titulo=f.cleaned_data['titulo']).exclude(pk=actividad.id).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"El título para la actividad ya existe."})

                    if f.cleaned_data['inicioinscripcion'] >= f.cleaned_data['fininscripcion']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha de fin de inscripciones debe ser mayor a la fecha de inicio."})

                    # if f.cleaned_data['fininscripcion'] >= f.cleaned_data['fechainicio']:
                    #     return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio de la actividad debe ser mayor a la fecha de fin de inscripción"})

                    if f.cleaned_data['fechainicio'] >= f.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha de fin de la actividad debe ser mayor a la fecha de inicio."})

                    # carreras_original = [c.id for c in actividad.carrera.all()]
                    # carr = []
                    # carr.append(f.cleaned_data['carrera'])
                    # carreras_formulario = [carrera.id for carrera in carr]
                    # excluidas = [c for c in carreras_original if c not in carreras_formulario]
                    #
                    # if len(excluidas) > 0:
                    #     for c in excluidas:
                    #         if InscripcionActividadConvalidacionPPV.objects.values('id').filter(status=True, inscripcion__carrera_id=c).exists():
                    #             nombrecarrera = Carrera.objects.get(pk=c).nombre
                    #             return JsonResponse({"result": "bad", "mensaje": "No se puede excluir la carrera %s del listado de carreras." % (nombrecarrera)})

                    actividad.titulo = f.cleaned_data['titulo']
                    actividad.fechainicio = f.cleaned_data['fechainicio']
                    actividad.fechafin = f.cleaned_data['fechafin']
                    actividad.horas = f.cleaned_data['horas']
                    actividad.fininscripcion = f.cleaned_data['fininscripcion']
                    actividad.cupo = f.cleaned_data['cupo']
                    actividad.profesor = f.cleaned_data['profesor']

                    actualiza_otros_campos = True
                    if actividad.total_alumnos_inscritos() > 0 or actividad.total_alumnos_preinscritos() > 0 or actividad.total_detalle_actividades_profesor() > 0:
                        actualiza_otros_campos = False

                    if actualiza_otros_campos:
                        actividad.tipoactividad = f.cleaned_data['tipoactividad']
                        actividad.inicioinscripcion = f.cleaned_data['inicioinscripcion']
                        actividad.nivelminimo = f.cleaned_data['nivelminimo'] if f.cleaned_data['nivelminimo'] else None

                    if 'archivoresolucion' in request.FILES:
                        archivoresolucion = request.FILES['archivoresolucion']
                        archivoresolucion._name = generar_nombre("resolucion", archivoresolucion._name)
                        actividad.archivoresolucion = archivoresolucion

                    if 'archivoproyecto' in request.FILES:
                        archivoproyecto = request.FILES['archivoproyecto']
                        archivoproyecto._name = generar_nombre("proyecto", archivoproyecto._name)
                        actividad.archivoproyecto = archivoproyecto
                    actividad.itinerariomalla = None
                    if int(actividad.tipoactividad) == 1:
                        actividad.itinerariomalla = f.cleaned_data['itinerario']
                    actividad.save(request)

                    actividad.carrera.clear()
                    # PRACTICAS PREPROFESIONALES
                    if int(actividad.tipoactividad) == 1:
                        if f.cleaned_data['carrera']:
                            actividad.carrera.add(f.cleaned_data['carrera'])
                    # PROYECTOS DE VINCULACION
                    elif int(actividad.tipoactividad) == 2:
                        for data in f.cleaned_data['carreramultiple']:
                            actividad.carrera.add(data)
                    actividad.save(request)

                    log(u'Editó actividad extracurricular de convalidación PPV: %s' % actividad, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'delactividad':
            try:
                actividad = ActividadConvalidacionPPV.objects.get(pk=request.POST['id'])

                if actividad.total_alumnos_inscritos() > 0:
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar la actividad debido a que existen estudiantes inscritos."})

                # if actividad.total_detalle_actividades_profesor() > 0:
                #     return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar la actividad debido a que el profesor asignado registró detalle de actividades."})

                actividad.status = False
                actividad.save(request)

                # Elimino los alumnos pre-inscritos en caso de existir
                if actividad.total_alumnos_preinscritos() > 0:
                    preinscritos = actividad.alumnos_preinscritos()
                    for preinscrito in preinscritos:
                        preinscrito.status = False
                        preinscrito.observacion = 'ELIMINADO POR DIRECTOR DE CARRERA'
                        preinscrito.save(request)


                log(u'Eliminó actividad extracurricular convalidación PPV: %s [%s]' % (actividad, actividad.id), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos. [%s]" % msg})

        elif action == 'anulactividad':
            try:
                actividad = ActividadConvalidacionPPV.objects.get(pk=request.POST['id'])
                obser = str(request.POST['observacion'])
                if actividad.total_alumnos_preinscritos() > 0:
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar la actividad debido a que existen estudiantes pre-inscritos."})

                if obser == '':
                    obser = 'SUSPENDIDA POR DIRECTOR DE CARRERA'

                actividad.estado = 5
                actividad.save(request)


                # Elimino los alumnos inscritos en caso de existir
                preinscritos = actividad.alumnos_inscritos()
                for preinscrito in preinscritos:
                    preinscrito.estado = 8
                    preinscrito.observacion = obser
                    preinscrito.save(request)

                log(u'Anulo la actividad extracurricular convalidación PPV: %s - %s [%s]' % (persona, actividad, actividad.id), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos. [%s]" % msg})

        elif action == 'reactivaract':
            try:
                id = encrypt(request.POST['id'])
                obser = str(request.POST['observacion'])
                actividad = ActividadConvalidacionPPV.objects.get(pk=int(id))
                if obser == '':
                    obser = 'SUSPENDIDA POR DIRECTOR DE CARRERA'
                actividad.estado = 1
                actividad.save(request)
                preinscritos = actividad.alumnos_inscritos()
                for preinscrito in preinscritos:
                    preinscrito.estado = 2
                    preinscrito.observacion = obser
                    preinscrito.save(request)
                log(u'Reactivo la actividad extracurricular convalidación PPV: %s - %s [%s]' % (persona, actividad, actividad.id), request, "edit")
                return JsonResponse({"error": False})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Error al eliminar los datos. [%s]" % msg})

        elif action == 'delactividadvoluntariado':
            try:
                actividad = ActividadConvalidacionPPV.objects.get(pk=request.POST['id'])

                if actividad.total_alumnos_inscritos() > 0:
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar la actividad debido a que existen estudiantes inscritos."})

                # if actividad.total_detalle_actividades_profesor() > 0:
                #     return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar la actividad debido a que el profesor asignado registró detalle de actividades."})

                actividad.status = False
                actividad.save(request)

                # Elimino los alumnos pre-inscritos en caso de existir
                if actividad.total_alumnos_preinscritos() > 0:
                    preinscritos = actividad.alumnos_preinscritos()
                    for preinscrito in preinscritos:
                        preinscrito.status = False
                        preinscrito.observacion = 'ELIMINADO POR DIRECTOR DE VINCULACION'
                        preinscrito.save(request)


                log(u'Eliminó actividad extracurricular convalidación PPV: %s [%s]' % (actividad, actividad.id), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos. [%s]" % msg})

        elif action == 'quitaraprobadodirector':
            try:
                actividad = ActividadConvalidacionPPV.objects.get(pk=request.POST['id'])
                # Si la actividad fue aprobada o reprobada por dirección de vinculación
                if actividad.estado == 9:
                    perfilrevisa = "la Dirección de Vinculación"
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede actualizar el Registro porque ya consta en revisión por parte de %s" % (perfilrevisa)})

                actividad.estado = 7
                actividad.save(request)

                inscritos = actividad.alumnos_inscritos()
                for inscrito in inscritos:
                    inscrito.estadodirectorcarrera = None
                    inscrito.fechaestadodirector = None
                    inscrito.observaciondirector = None
                    inscrito.save(request)

                log(u'Quitó estado APROBADO por director de carrera a la actividad: %s' % actividad, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos. [%s]" % msg})

        elif action == 'ingresardetalle':
            try:
                if not 'idactividad' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                actividad = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.POST['idactividad'])))
                actividades = request.POST.getlist('actividad[]')
                horas = request.POST.getlist('horaactividad[]')
                observaciones = request.POST.getlist('observacion[]')
                idsdetalle = request.POST.getlist('iddetalle[]')

                acciondetalles = "I"
                detalles = actividad.detalle_actividades_profesor()
                if detalles:
                    if detalles.count() == len(actividades):
                        acciondetalles = "U"
                    else:
                        DetalleActividadConvalidacionPPV.objects.filter(actividad=actividad, status=True).update(status=False, fecha_modificacion=datetime.now(), usuario_modificacion_id=persona.usuario.id)

                if acciondetalles == "I":
                    for detalle, hora, observacion in zip(actividades, horas, observaciones):
                        detalleactividad = DetalleActividadConvalidacionPPV(actividad=actividad,
                                                                            detalle=detalle,
                                                                            horas=hora,
                                                                            observacion=observacion
                                                                            )
                        detalleactividad.save(request)
                else:
                    for iddetalle, detalle, hora, observacion in zip(idsdetalle, actividades, horas, observaciones):
                        DetalleActividadConvalidacionPPV.objects.filter(pk=iddetalle).update(detalle=detalle, horas=hora, observacion=observacion, fecha_modificacion=datetime.now(), usuario_modificacion_id=persona.usuario.id)

                if acciondetalles == "I":
                    log(u'Agregó detalles de la actividad extracurricular convalidación PPV: %s' % (actividad), request, "add")
                else:
                    log(u'Editó detalles de la actividad extracurricular convalidación PPV: %s' % (actividad), request, "edit")

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'aggrecomendacion_actividad':
            try:

                requisito = RequisitosActividadConvalidacionPPV.objects.get(id=request.POST['id'])
                requisito.status = False
                requisito.save(request)
                return JsonResponse({"error": True, 'mensaje': 'No puede eliminar esta requisito'}, safe=False)
            except Exception as e:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, 'mensaje': str(e)}, safe=False)

        elif action == 'aceptarinscripcion':
            try:
                if not 'idactividad' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                actividad = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.POST['idactividad'])))

                id2 = int(request.POST['id2'])

                idinscripciones = request.POST.getlist('idinscripcion[]')
                estados = request.POST.getlist('estadopreinscripcion[]')
                observaciones = request.POST.getlist('observacionpreins[]')

                inscripciones = []

                if id2 == 2:
                    for id, estado, observacion in zip(idinscripciones, estados, observaciones):
                        if int(estado) == 3:
                            inscripcion_ae = InscripcionActividadConvalidacionPPV.objects.get(pk=int(id))
                            inscripcion_ae.fechaaceptarechaza = datetime.now()
                            inscripcion_ae.observacion = observacion
                            inscripcion_ae.estado = estado
                            inscripcion_ae.save(request)
                            ins = {'id': id}
                            inscripciones.append(ins)

                else:
                    for id, estado, observacion in zip(idinscripciones, estados, observaciones):
                        if int(estado) != 1:
                            inscripcion_ae = InscripcionActividadConvalidacionPPV.objects.get(pk=int(id))
                            eInscripcion = inscripcion_ae.inscripcion
                            permite_varios_servicio = str(eInscripcion.carrera.id) in serviciocomunitario_carreras if serviciocomunitario_carreras else False
                            permite_varios_practica = str(eInscripcion.carrera.id) in practica_carreras if practica_carreras else False
                            if actividad.tipoactividad == 1: selecciona_varios = permite_varios_practica
                            else: selecciona_varios = permite_varios_servicio

                            if int(estado) != 3 :
                                if not selecciona_varios and actividad.validacion_inscritos_adicionar_manual(inscripcion_ae.inscripcion.id, periodo):
                                    return JsonResponse({"result": "no", "mensaje": u"Estudiante ya se ha inscrito en otra actividad: [%s]" % inscripcion_ae.inscripcion.persona})

                            inscripcion_ae.fechaaceptarechaza = datetime.now()
                            inscripcion_ae.observacion = observacion
                            inscripcion_ae.estado = estado
                            inscripcion_ae.save(request)

                            ins = {'id': id}
                            inscripciones.append(ins)

                log(u'Actualizó estados de inscripciones de alumnos a la actividad extracurricular convalidación PPV: %s' % (actividad), request, "edit")
                if id2 == 1:
                    return JsonResponse({"result": "ok", "cantidad": len(inscripciones), "inscripciones": inscripciones})
                else:
                    return JsonResponse({"result": "no", "mensaje": u"DATOS GUARDADOS"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'enviaremailestadoinscripcion':
            try:
                inscripcion_ae = InscripcionActividadConvalidacionPPV.objects.get(pk=int(request.POST['id']))
                inscripcion_ae.notificado = True
                inscripcion_ae.save(request)

                # Envío de correo al estudiante
                cuenta = cuenta_email_disponible()
                estadoinscripcion = "ACEPTADA" if inscripcion_ae.estado == 2 else "RECHAZADA"
                tituloemail = "Inscripción Actividad Extracurricular - " + estadoinscripcion
                estudiante = inscripcion_ae.inscripcion.persona

                send_html_mail(tituloemail,
                               "emails/inscripcionactividadppv.html",
                               {'sistema': u'SGA - UNEMI',
                                'accion': 'CAMBIOESTADO',
                                'fecha': datetime.now().date(),
                                'hora': datetime.now().time(),
                                'saludo': 'Estimada' if estudiante.sexo.id == 1 else 'Estimado',
                                'estudiante': estudiante,
                                'actividad': inscripcion_ae.actividad.titulo,
                                'periodo': inscripcion_ae.actividad.periodo.nombre,
                                'estado': estadoinscripcion,
                                'observacion': inscripcion_ae.observacion,
                                't': miinstitucion()
                                },
                               estudiante.lista_emails_envio(),
                               [],
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                # Temporizador para evitar que se bloquee el servicion de gmail
                ET.sleep(5)

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al enviar el e-mail."})

        elif action == 'registrocumplimiento':
            try:
                if not 'idactividad' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                if 'informetecnico' in request.FILES:
                    arch = request.FILES['informetecnico']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:

                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                    arch._name = generar_nombre("informeactividad", arch._name)

                actividad = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.POST['idactividad'])))

                if actividad.total_recomendaciones() == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"DEBE INGRESAR LAS RECOMENDACIONES"})

                # if actividad.estado >= 7:
                #     return JsonResponse({"result": "bad", "mensaje": u"YA SE FINALIZÓ LA ACTIVIDAD"})

                idinscripciones = request.POST.getlist('idinscripcion[]')
                estados = request.POST.getlist('estadoregistro[]')
                observaciones = request.POST.getlist('observacionreg[]')
                horascumplidas = request.POST.getlist('horacumplida[]')

                if actividad.tipoactividad == 1:
                    institucion = request.POST.getlist('institucion[]')
                    for e, inst2 in zip(estados, institucion):
                        if int(e) == 6:
                            if inst2 == '':
                                return JsonResponse({"result": "bad", "mensaje": u"INGRESE LA INSTITUCIÓN EN TODOS LOS REGISTROS"})


                # Se valida que el total de horas cumplidas no exceda el total de horas pendientes
                # Se omite validación por pedido de Jadira Yunga 15-01-2021
                # for id, estado, hora in zip(idinscripciones, estados, horascumplidas):
                #     inscripcion_ae = InscripcionActividadConvalidacionPPV.objects.get(pk=int(id))
                #     insalumno = inscripcion_ae.inscripcion
                #     nombrealumno = insalumno.persona.nombre_completo_inverso()
                #     ella = "la" if insalumno.persona.sexo.id == 1 else "el"
                #     if actividad.tipoactividad == 1:
                #         horaspendientes = insalumno.total_horas_practicas_pendiente()
                #         if int(hora) > horaspendientes:
                #             return JsonResponse({"result": "bad", "mensaje": u"El total de horas cumplidas para %s estudiante %s debe ser menor o igual a %s " % (ella, nombrealumno, horaspendientes)})
                #     else:
                #         horaspendientes = insalumno.total_horas_proyecto_vinculacion_pendiente()
                #         if int(hora) > horaspendientes:
                #             return JsonResponse({"result": "bad", "mensaje": u"El total de horas cumplidas para %s estudiante %s debe ser menor o igual a %s " % (ella, nombrealumno, horaspendientes)})

                # Si la actividad fue aprobada o reprobada por director de carrera o dirección de vinculación
                if actividad.estado == 8 or actividad.estado == 9:
                    perfilrevisa = "el Director de Carrera" if actividad.estado == 8 else "la Dirección de Vinculación"
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede actualizar el Registro porque ya consta en revisión por parte de %s" % (perfilrevisa)})

                if not actividad.archivoinforme:
                    actividad.fechainforme = datetime.now().date()

                # if 'informetecnico' in request.FILES:
                #     if not actividad.archivoinforme:
                #         actividad.fechainforme = datetime.now().date()
                #     actividad.archivoinforme = arch
                #     actividad.estado = 7

                data['fechafin'] = fecfin = datetime.now().date()

                f2 = convertir_fecha_invertida(str(fecfin))

                an2 = fecfin.year

                data['actividad'] = actividad


                # cargoactual_act = dire.mi_cargo_actual()
                #
                # data['cargoactual_act'] = cargoactual_act

                inscripciones = []

                if actividad.tipoactividad == 1:
                    # institucion = request.POST.getlist('institucion[]')
                    for id, estado, observacion, hora, inst in zip(idinscripciones, estados, observaciones, horascumplidas, institucion):
                        inscripcion_ae = InscripcionActividadConvalidacionPPV.objects.get(pk=int(id))
                        maximo = inscripcion_ae.maximohoras() if inscripcion_ae.maximohoras() > 0 else int(hora) + 1
                        if int(hora) > maximo:
                            raise NameError("Ha ingresado un numero mayor a las horas maximas de esta actividad del participante {}".format(inscripcion_ae.inscripcion.persona))
                        inscripcion_ae.horascumplidas = hora
                        inscripcion_ae.institucion_actividad = inst
                        inscripcion_ae.estadoprofesor = 1 if int(estado) == 6 else 2
                        inscripcion_ae.fechaestadoprofesor = datetime.now().date()
                        inscripcion_ae.observacionprofesor = observacion
                        if int(estado) == 7:
                            inscripcion_ae.estado = estado
                        else:
                            inscripcion_ae.estado = 4

                        inscripcion_ae.save(request)

                        log(u'Actualizó registro de cumplimiento en la actividad %s del estudiante %s' % (inscripcion_ae.actividad, inscripcion_ae.inscripcion.persona), request, "edit")

                        # ins = {'id': id}
                        # inscripciones.append(ins)
                else:
                    # institucion = ''
                    for id, estado, observacion, hora in zip(idinscripciones, estados, observaciones, horascumplidas):
                        inscripcion_ae = InscripcionActividadConvalidacionPPV.objects.get(pk=int(id))
                        maximo = inscripcion_ae.maximohoras() if inscripcion_ae.maximohoras() > 0 else int(hora) + 1
                        if int(hora) > maximo:
                            raise NameError("Ha ingresado un numero mayor a las horas maximas de esta actividad del participante {}".format(inscripcion_ae.inscripcion.persona))
                        inscripcion_ae.horascumplidas = hora
                        inscripcion_ae.estadoprofesor = 1 if int(estado) == 6 else 2
                        inscripcion_ae.fechaestadoprofesor = datetime.now().date()
                        inscripcion_ae.observacionprofesor = observacion
                        if int(estado) == 7:
                            inscripcion_ae.estado = estado
                        else:
                            inscripcion_ae.estado = 4

                        inscripcion_ae.save(request)

                        log(u'Actualizó registro de cumplimiento en la actividad %s del estudiante %s' % (inscripcion_ae.actividad, inscripcion_ae.inscripcion.persona), request, "edit")

                        # ins = {'id': id}
                        # inscripciones.append(ins)

                # for id, estado, observacion, hora in zip(idinscripciones, estados, observaciones, horascumplidas):
                #     inscripcion_ae = InscripcionActividadConvalidacionPPV.objects.get(pk=int(id))
                #     inscripcion_ae.horascumplidas = hora
                #     inscripcion_ae.estadoprofesor = 1 if int(estado) == 6 else 2
                #     inscripcion_ae.fechaestadoprofesor = datetime.now().date()
                #     inscripcion_ae.observacionprofesor = observacion
                #     if int(estado) == 7:
                #         inscripcion_ae.estado = estado
                #     else:
                #         inscripcion_ae.estado = 4
                #
                #     inscripcion_ae.save(request)
                #
                #     log(u'Actualizó registro de cumplimiento en la actividad %s del estudiante %s' % (inscripcion_ae.actividad, inscripcion_ae.inscripcion.persona), request, "edit")
                #
                #     # ins = {'id': id}
                #     # inscripciones.append(ins)

                data['inscritos'] = actividad.alumnos_inscritos()
                data['horaactual'] = datetime.now().time()

                data['careras_Actividad'] = ca = actividad.carrera.all()
                cargoactual = actividad.director.mi_cargo_actual()
                # Modulo para directores de carrera, docentes y analista de vinculación
                if cargoactual == 227000:
                    data['director_ac'] = actividad.director
                    data['cargoactual_act'] = 'DIRECTOR(A) DE VINCULACIÓN'

                else:
                    for c in ca:
                        if CoordinadorCarrera.objects.filter(carrera=c, periodo=periodo, tipo=3, status=True).exists():
                            coo = CoordinadorCarrera.objects.filter(carrera=c, periodo=periodo, tipo=3, status=True).first()
                            data['director_ac'] = coo.persona
                            data['director_carrera'] = coo.carrera
                            cargoactual_act = coo.persona.mi_cargo_actual()
                            data['cargoactual_act'] = 'DIRECTOR(A) DE CARRERA'

                data['numero_carrera'] = ca.count()
                data['detalle'] = actividad.detalle_actividades_profesor()
                nombresinciales = ''
                nombre = persona.nombres.split()
                if len(nombre) > 1:
                    nombresiniciales = '{}{}'.format(nombre[0][0], nombre[1][0])
                else:
                    nombresiniciales = '{}'.format(nombre[0][0])
                if persona.apellido2:
                    inicialespersona = '{}{}{}'.format(nombresiniciales, persona.apellido1[0], persona.apellido2[0])
                else:
                    inicialespersona = '{}{}'.format(nombresiniciales, persona.apellido1[0])


                data['recomendaciones'] = RecomendacionesActividadConvalidacionPPV.objects.filter(actividad_id=int(encrypt(request.POST['idactividad'])), status=True)

                cant_Actv = ActividadConvalidacionPPV.objects.filter(periodo=actividad.periodo, status=True, profesor__persona_id=persona.id).order_by('id')
                num = 0
                for ac in cant_Actv:
                    num += 1
                    if ac == actividad:
                        canti = num

                data['numinforme'] = '{}-ACTEX-{}-{}'.format(canti, inicialespersona, an2)

                # qrname='Informe_ActividadExtra_{}'.format(random.randint(1, 100000).__str__())

                directory = os.path.join(SITE_STORAGE, 'media', 'convalidacionppv', 'informesactv/')
                try:
                    os.stat(directory)
                except:
                    os.mkdir(directory)
                qrname = 'INFORME_FINAL_DE_ACTIVIDADES_EXTRACURRICULARES_{}'.format(random.randint(1, 100000).__str__())

                rutaimg = '{}/{}.png'.format(directory, qrname)

                if os.path.isfile(rutaimg):
                    os.remove(rutaimg)
                p = persona.id
                if persona.mis_cargos().exists():
                    url = pyqrcode.create('DOCENTE: {}\nCARGO: {}'.format(persona.__str__(), persona.mis_cargos()[0]))
                else:
                    url = pyqrcode.create('DOCENTE: {}\nCARGO: {}'.format(persona.__str__(), 'NO TIENE CARGO'))

                imageqr = url.png('{}{}.png'.format(directory, qrname), 16, '#000000')

                data['qrname'] = qrname

                valida = conviert_html_to_pdfsaveqrinformepractividadextra(
                    'adm_convalidacionpractica/informe/informeactividad.html',
                    {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                )

                actividad.archivoinforme = 'convalidacionppv/informesactv/' + qrname + '.pdf'

                actividad.estado = 7
                actividad.save(request)

                log(u'Actualizó registro de cumplimiento de los estudiantes a la actividad extracurricular convalidación PPV: %s' % (actividad), request, "edit")

                # return redirect('/media/{}'.format(actividad.archivoinforme))

                # return JsonResponse({"result": "ok", "cantidad": len(inscripciones), "inscripciones": inscripciones})
                messages.success(request, 'Actividades culminadas con exito')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                print(sys.exc_info()[-1].tb_lineno)
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'actualizar_informe':
            try:
                fecfin = datetime.now().date()
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                actividad = ActividadConvalidacionPPV.objects.get(pk=int(request.POST['id']))

                data['fechafin'] = fecfin

                f2 = convertir_fecha_invertida(str(fecfin))

                an2 = fecfin.year

                data['actividad'] = actividad

                data['inscritos'] = actividad.alumnos_inscritos()
                data['horaactual'] = datetime.now().time()

                data['careras_Actividad'] = ca = actividad.carrera.all()
                cargoactual = actividad.director.mi_cargo_actual()
                # Modulo para directores de carrera, docentes y analista de vinculación
                if cargoactual == 227000:
                    data['director_ac'] = actividad.director
                    data['cargoactual_act'] = 'DIRECTOR(A) DE VINCULACIÓN'

                else:
                    for c in ca:
                        if CoordinadorCarrera.objects.filter(carrera=c, periodo=periodo, tipo=3, status=True).exists():
                            coo = CoordinadorCarrera.objects.filter(carrera=c, periodo=periodo, tipo=3, status=True).first()
                            data['director_ac'] = coo.persona
                            data['director_carrera'] = coo.carrera
                            cargoactual_act = coo.persona.mi_cargo_actual()
                            data['cargoactual_act'] = 'DIRECTOR(A) DE CARRERA'

                data['numero_carrera'] = ca.count()
                data['detalle'] = actividad.detalle_actividades_profesor()
                nombresinciales = ''
                nombre = actividad.profesor.persona.nombres.split()
                if len(nombre) > 1:
                    nombresiniciales = '{}{}'.format(nombre[0][0], nombre[1][0])
                else:
                    nombresiniciales = '{}'.format(nombre[0][0])
                if actividad.profesor.persona.apellido2:
                    inicialespersona = '{}{}{}'.format(nombresiniciales, actividad.profesor.persona.apellido1[0], actividad.profesor.persona.apellido2[0])
                else:
                    inicialespersona = '{}{}'.format(nombresiniciales, actividad.profesor.persona.apellido1[0])

                data['recomendaciones'] = RecomendacionesActividadConvalidacionPPV.objects.filter(actividad_id=int(request.POST['id']), status=True)

                cant_Actv = ActividadConvalidacionPPV.objects.filter(periodo=actividad.periodo, status=True, profesor__persona_id=actividad.profesor.persona.id).order_by('id')
                num = 0
                canti = 1
                for ac in cant_Actv:
                    num += 1
                    if ac == actividad:
                        canti = num

                data['numinforme'] = '{}-ACTEX-{}-{}'.format(canti, inicialespersona, an2)

                directory = os.path.join(SITE_STORAGE, 'media', 'convalidacionppv', 'informesactv/')
                try:
                    os.stat(directory)
                except:
                    os.mkdir(directory)
                qrname = 'INFORME_FINAL_DE_ACTIVIDADES_EXTRACURRICULARES_{}'.format(random.randint(1, 100000).__str__())
                rutaimg = '{}/{}.png'.format(directory, qrname)
                if os.path.isfile(rutaimg):
                    os.remove(rutaimg)
                p = actividad.profesor.persona.id
                if actividad.profesor.persona.mis_cargos().exists():
                    url = pyqrcode.create('DOCENTE: {}\nCARGO: {}'.format(actividad.profesor.persona.__str__(), actividad.profesor.persona.mis_cargos()[0]))
                else:
                    url = pyqrcode.create('DOCENTE: {}\nCARGO: {}'.format(actividad.profesor.persona.__str__(), 'NO TIENE CARGO'))
                imageqr = url.png('{}{}.png'.format(directory, qrname), 16, '#000000')
                data['qrname'] = qrname
                valida = conviert_html_to_pdfsaveqrinformepractividadextra(
                    'adm_convalidacionpractica/informe/informeactividad.html',
                    {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                )
                actividad.archivoinforme = 'convalidacionppv/informesactv/' + qrname + '.pdf'
                actividad.save(request)
                log(u'Actualizó registro de cumplimiento de los estudiantes a la actividad extracurricular convalidación PPV: %s' % (actividad), request, "edit")

                messages.success(request, 'Informe actualizado con exito')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                print(sys.exc_info()[-1].tb_lineno)
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})


        elif action == 'deleterequisito':
            try:
                requisito = RequisitosActividadConvalidacionPPV.objects.get(id=request.POST['id'])
                requisito.status = False
                requisito.save(request)
                return JsonResponse({"error": True, 'mensaje': 'No puede eliminar esta requisito'}, safe=False)
            except Exception as e:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, 'mensaje': str(e)}, safe=False)

        elif action == 'aprobarconvalidacion':
            try:
                if not 'idactividad' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                actividad = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.POST['idactividad'])))

                # Si la actividad fue aprobada o reprobada por dirección de vinculación
                if actividad.estado == 9:
                    perfilrevisa = "la Dirección de Vinculación"
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede actualizar el Registro porque ya consta en revisión por parte de %s" % (perfilrevisa)})

                actividad.estado = 8
                actividad.save(request)

                idinscripciones = request.POST.getlist('idinscripcion[]')
                estados = request.POST.getlist('estadoregistro[]')
                observaciones = request.POST.getlist('observacionreg[]')

                inscripciones = []

                for id, estado, observacion in zip(idinscripciones, estados, observaciones):
                    inscripcion_ae = InscripcionActividadConvalidacionPPV.objects.get(pk=int(id))
                    inscripcion_ae.estadodirectorcarrera = 1 if int(estado) == 6 else 2
                    inscripcion_ae.fechaestadodirector = datetime.now().date()
                    inscripcion_ae.observaciondirector = observacion
                    if int(estado) == 7:
                        inscripcion_ae.estado = estado
                    else:
                        inscripcion_ae.estado = 4

                    inscripcion_ae.save(request)

                    log(u'Actualizó estado de convalidación en la actividad %s del estudiante %s' % (inscripcion_ae.actividad, inscripcion_ae.inscripcion.persona), request, "edit")

                    # ins = {'id': id}
                    # inscripciones.append(ins)

                log(u'Actualizó aprobación de convalidación de los estudiantes a la actividad extracurricular convalidación PPV: %s' % (actividad), request, "edit")

                # return JsonResponse({"result": "ok", "cantidad": len(inscripciones), "inscripciones": inscripciones})
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'convalidarpractica':
            try:
                if not 'idactividad' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                actividad = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.POST['idactividad'])))

                # # Si la actividad fue aprobada o reprobada por dirección de vinculación
                # if actividad.estado == 9:
                #     perfilrevisa = "la Dirección de Vinculación"
                #     return JsonResponse({"result": "bad", "mensaje": u"No se puede actualizar el Registro porque ya consta en revisión por parte de %s" % (perfilrevisa)})

                actividad.estado = 9
                actividad.save(request)

                idinscripciones = request.POST.getlist('idinscripcion[]')
                estados = request.POST.getlist('estadoregistro[]')
                observaciones = request.POST.getlist('observacionreg[]')

                for id, estado, observacion in zip(idinscripciones, estados, observaciones):
                    inscripcion_ae = InscripcionActividadConvalidacionPPV.objects.get(pk=int(id))
                    inscripcion_ae.estadovinculacion = 1 if int(estado) == 6 else 2
                    inscripcion_ae.fechaestadovinculacion = datetime.now().date()
                    inscripcion_ae.observacionvinculacion = observacion
                    inscripcion_ae.responsablevinculacion = persona
                    inscripcion_ae.estado = estado
                    inscripcion_ae.save(request)

                    if int(estado) == 6: # APROBADO
                        # Agregar registros de practicas o vinculacion
                        if actividad.tipoactividad == 1: # PRACTICAS
                            practica = PracticasPreprofesionalesInscripcion(
                                preinscripcion=None,
                                inscripcion=inscripcion_ae.inscripcion,
                                tipo=7,
                                fechadesde=actividad.fechainicio,
                                vigente=False,#True
                                fechahasta=actividad.fechafin,
                                tutorempresa=None,
                                tutorunemi=actividad.profesor,
                                numerohora=inscripcion_ae.horascumplidas,
                                institucion=inscripcion_ae.institucion_actividad,
                                tipoinstitucion=1,
                                sectoreconomico=5,
                                tiposolicitud=2,
                                empresaempleadora=None,
                                otraempresa=False,
                                otraempresaempleadora='',
                                estadosolicitud=2,
                                archivo=None,
                                personaaprueba=persona,
                                fechaaprueba=datetime.now().date(),
                                obseaprueba='',
                                culminada=True,
                                departamento=None,
                                horahomologacion=None,
                                rotacion=None,
                                observacion=None,
                                autorizarevidencia=False,
                                fechaautorizarevidencia=None,
                                rotacionmalla=None,
                                supervisor=None,
                                fechaasigtutor=actividad.fecha_creacion,
                                fechaasigsupervisor=None,
                                validacion=None,
                                fechavalidacion=None,
                                oferta=None,
                                archivoretiro=None,
                                itinerariomalla=None,
                                periodoevidencia=None,
                                retirado=False,
                                fechahastapenalizacionretiro=None,
                                aperturapractica=None,
                                convenio=None,
                                acuerdo=None,
                                lugarpractica=None,
                                configuracionevidencia=None,
                                asignacionempresapractica=None,
                                actividad=actividad
                            )
                            practica.save(request)

                            # Evidencias
                            evidencia = DetalleEvidenciasPracticasPro(
                                evidencia=None,
                                inscripcionpracticas=practica,
                                puntaje=0,
                                descripcion='RESOLUCIÓN DE CONSEJO DIRECTIVO',
                                estadorevision=2,
                                archivo=actividad.archivoresolucion,
                                fechaarchivo=actividad.fecha_creacion,
                                personaaprueba=persona,
                                fechaaprueba=datetime.now(),
                                obseaprueba='INFORMACIÓN VALIDADA',
                                fechainicio=None,
                                fechafin=None,
                                estadotutor=0,
                                obstutor='',
                                aprobosupervisor=False
                            )
                            evidencia.save(request)

                            evidencia = DetalleEvidenciasPracticasPro(
                                evidencia=None,
                                inscripcionpracticas=practica,
                                puntaje=0,
                                descripcion='INFORME TÉCNICO DE LA ACTIVIDAD DESARROLLADA',
                                estadorevision=2,
                                archivo=actividad.archivoinforme,
                                fechaarchivo=actividad.fechainforme,
                                personaaprueba=persona,
                                fechaaprueba=datetime.now(),
                                obseaprueba='INFORMACIÓN VALIDADA',
                                fechainicio=None,
                                fechafin=None,
                                estadotutor=2,
                                obstutor='INFORME TÉCNICO CARGADO AL SISTEMA',
                                aprobosupervisor=False
                            )
                            evidencia.save(request)

                            log(u'Adicionó Registro de práctica preprofesional inscripción, por módulo actividad extracurricular: %s' % practica, request, "add")
                        else: # VINCULACION
                            vinculacion = ParticipantesMatrices(
                                matrizevidencia_id=2,
                                proyecto=None,
                                inscripcion=inscripcion_ae.inscripcion,
                                profesor=None,
                                tipoparticipante=None,
                                horas=inscripcion_ae.horascumplidas,
                                administrativo=None,
                                actividad=actividad,
                            )
                            vinculacion.save(request)

                            log(u'Adicionó Registro de Proyecto de Vinculación, por módulo actividad extracurricular: %s' % vinculacion, request, "add")

                    log(u'Actualizó estado de convalidación en la actividad %s del estudiante %s' % (inscripcion_ae.actividad, inscripcion_ae.inscripcion.persona), request, "edit")

                log(u'Actualizó convalidación de los estudiantes a la actividad extracurricular convalidación PPV: %s' % (actividad), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'validarsolicitud':
            try:
                id = int(request.POST['id'])
                estado = int(request.POST['estadosolicitud'])
                validacuenta = request.POST['validacuenta']

                solicitud = SolicitudDevolucionDinero.objects.get(pk=id)
                beneficiario = solicitud.persona

                solicitud.estado = estado
                solicitud.personarevisa = persona
                solicitud.observacion = request.POST['observacion'].strip().upper() if 'observacion' in request.POST else ''
                solicitud.fechavalida = datetime.now().date() if estado == 2 else None
                solicitud.montodevolver = request.POST['montodevolver'] if 'montodevolver' in request.POST else None
                solicitud.save(request)

                recorrido = SolicitudDevolucionDineroRecorrido(solicituddevolucion=solicitud,
                                                               fecha=datetime.now().date(),
                                                               observacion='APROBADO POR TESORERÍA' if estado == 2 else solicitud.observacion,
                                                               estado=estado
                                                               )
                recorrido.save(request)

                if validacuenta == 'S' and estado == 2:
                    cuentabancaria = beneficiario.cuentabancaria()
                    cuentabancaria.banco_id = int(request.POST['banco'])
                    cuentabancaria.tipocuentabanco_id = int(request.POST['tipocuenta'])
                    cuentabancaria.numero = request.POST['numerocuenta'].strip()
                    cuentabancaria.estadorevision = 2
                    cuentabancaria.observacion = ''
                    cuentabancaria.fechavalida = datetime.now().date()
                    cuentabancaria.save(request)

                if solicitud.estado == 2:
                    tituloemail = "Solicitud de Devolución de Dinero - APROBADA"
                    mensaje = "su solicitud de devolución de dinero fue <strong>APROBADA</strong>"
                    observaciones = ""
                else:
                    tituloemail = "Solicitud de Devolución de Dinero - RECHAZADA"
                    mensaje = "se presentaron novedades durante la revisión de su solicitud de devolución de dinero. Su solicitud fue <strong>RECHAZADA</strong>"
                    observaciones = solicitud.observacion

                cuenta = cuenta_email_disponible()

                send_html_mail(tituloemail,
                               "emails/notificarestadodevoluciondinero.html",
                               {'sistema': u'SGA - UNEMI',
                                'mensaje': mensaje,
                                'fecha': datetime.now().date(),
                                'hora': datetime.now().time(),
                                'observaciones': observaciones,
                                'saludo': 'Estimada' if solicitud.persona.sexo_id == 1 else 'Estimado',
                                'estudiante': solicitud.persona.nombre_completo_inverso(),
                                'autoridad2': '',
                                't': miinstitucion()
                                },
                               solicitud.persona.lista_emails_envio(),
                               [],
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'Revisó solicitud de devolución de dinero: %s  - %s' % (persona, solicitud), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'verificar_cuentas_validadas':
            try:
                if datetime.strptime(request.POST['desde'], '%d-%m-%Y') <= datetime.strptime(request.POST['hasta'], '%d-%m-%Y'):
                    desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)

                    if Persona.objects.filter(cuentabancariapersona__status=True,
                                              cuentabancariapersona__archivo__isnull=False,
                                              inscripcion__becasolicitud__periodo_id__in=[110, 90],
                                              inscripcion__becasolicitud__becaasignacion__status=True,
                                              cuentabancariapersona__fechavalida__range=(desde, hasta),
                                              cuentabancariapersona__archivoesigef=False).exists():
                        if Persona.objects.filter(cuentabancariapersona__status=True,
                                                  cuentabancariapersona__archivo__isnull=False,
                                                  inscripcion__becasolicitud__periodo_id__in=[110, 90],
                                                  inscripcion__becasolicitud__becaasignacion__status=True,
                                                  cuentabancariapersona__fechavalida__range=(desde, hasta),
                                                  cuentabancariapersona__archivoesigef=False,
                                                  cuentabancariapersona__banco__codigo='').exists():
                            return JsonResponse({"result": "bad", "mensaje": "No se puede generar el archivo, existen registros de bancos sin código"})
                        else:
                            return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "No existen cuentas bancarias validadas en el rango de fechas"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'verificar_cuentas_validadas_reporte':
            try:
                if datetime.strptime(request.POST['desde'], '%d-%m-%Y') <= datetime.strptime(request.POST['hasta'], '%d-%m-%Y'):
                    desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)

                    if Persona.objects.filter(cuentabancariapersona__status=True,
                                              cuentabancariapersona__archivo__isnull=False,
                                              inscripcion__becasolicitud__periodo_id__in=[110, 90],
                                              inscripcion__becasolicitud__becaasignacion__status=True,
                                              cuentabancariapersona__fechavalida__range=(desde, hasta)
                                              ).exists():
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "No existen cuentas bancarias validadas en el rango de fechas"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'verificar_cuentas_rechazadas':
            try:
                if Persona.objects.filter(cuentabancariapersona__status=True,
                                          cuentabancariapersona__archivo__isnull=False,
                                          inscripcion__becasolicitud__periodo_id__in=[110, 90],
                                          inscripcion__becasolicitud__becaasignacion__status=True,
                                          cuentabancariapersona__estadorevision=3).exists():
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "No existen cuentas bancarias rechazadas para generar el reporte"})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'verificar_cuentas_pendientes_revisar':
            try:
                if Persona.objects.filter(cuentabancariapersona__status=True,
                                          cuentabancariapersona__archivo__isnull=False,
                                          inscripcion__becasolicitud__periodo_id__in=[110, 90],
                                          inscripcion__becasolicitud__becaasignacion__status=True,
                                          cuentabancariapersona__estadorevision=1).exists():
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "No existen cuentas bancarias pendientes de revisar para generar el reporte"})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'vaciarhoras':
            try:
                with transaction.atomic():
                    actividad = ActividadConvalidacionPPV.objects.get(pk=int(request.POST['idactividad']))
                    actividad.estado = 4
                    actividad.save(request)
                    listainscritos = actividad.alumnos_inscritos()
                    for i in listainscritos:
                        i.horascumplidas = None
                        i.estadoprofesor = None
                        i.fechaestadoprofesor = None
                        i.observacionprofesor = None
                        i.estado = 4
                        i.save(request)
                    response = JsonResponse({'resp': True, 'mensaje': 'HORAS VACIADAS'})
            except Exception as ex:
                response = JsonResponse({'resp': False, 'mensaje': 'NO SE PUEDE VACIAR HORAS, INTENTELO MÁS TARDE'})
            return HttpResponse(response.content)

        elif action == 'addrequisito':
            try:
                with transaction.atomic():
                    actividad = ActividadConvalidacionPPV.objects.get(pk=request.POST['id'])
                    form = RequisitoActividadConvalidacionForm(request.POST, request.FILES)
                    if form.is_valid():
                        filtro = RequisitosActividadConvalidacionPPV(actividad=actividad,
                                                                     titulo=form.cleaned_data['titulo'].upper(),
                                                                     leyenda=form.cleaned_data['leyenda'],
                                                                     flimite=form.cleaned_data['flimite'])
                        filtro.save(request)
                        if 'formato' in request.FILES:
                            newfile = request.FILES['formato']
                            newfile._name = generar_nombre(filtro.nombre_input(), newfile._name)
                            filtro.formato = newfile
                            filtro.save(request)
                        log(u'Adiciono Requisito Actividad Extracurricular: %s' % filtro, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'addrecomendacion':
            try:
                with transaction.atomic():
                    actividad = ActividadConvalidacionPPV.objects.get(pk=request.POST['id'])
                    form = RecomendacionActividadPPVForm(request.POST, request.FILES)


                    if form.is_valid():
                        descrip = str(form.cleaned_data['descripcion'])
                        if descrip == '':
                            return JsonResponse({"result": True, "mensaje": "Llene el campo observaciones."}, safe=False)

                        filtro = RecomendacionesActividadConvalidacionPPV(actividad=actividad,
                                                                     descripcion=form.cleaned_data['descripcion'])
                        filtro.save(request)

                        log(u'Adiciono recomendación Actividad Extracurricular: %s' % filtro, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)


        elif action == 'editrequisito':
            try:
                with transaction.atomic():
                    filtro = RequisitosActividadConvalidacionPPV.objects.get(pk=request.POST['id'])
                    f = RequisitoActividadConvalidacionForm(request.POST, request.FILES)
                    if f.is_valid():
                        filtro.titulo = f.cleaned_data['titulo'].upper()
                        filtro.leyenda = f.cleaned_data['leyenda']
                        filtro.flimite = f.cleaned_data['flimite']
                        if 'formato' in request.FILES:
                            newfile = request.FILES['formato']
                            newfile._name = generar_nombre(filtro.nombre_input(), newfile._name)
                            filtro.formato = newfile
                        filtro.save(request)
                        log(u'Modificó Actividad Extracurricular: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'edittitulo':
            try:
                id = request.POST['id']
                valor = request.POST['valor']
                requisito = RequisitosActividadConvalidacionPPV.objects.get(pk=id)
                requisito.titulo = valor
                requisito.save(request)
                log(u'Modificó Titulo de Requisito Actividad Extracurricular: %s' % requisito, request, "edit")
                return JsonResponse({"result": True})
            except Exception as ex:
                return JsonResponse({'result': False, "message": str(ex)})

        # elif action == 'editobservacion':
        #     try:
        #         id = request.POST['id']
        #         valor = request.POST['valor']
        #         requisito = InscripcionRequisitosActividadConvalidacionPPV.objects.get(pk=id)
        #         requisito.titulo = valor
        #         requisito.save(request)
        #         log(u'Modificó Observación de Archivo de Actividad Extracurricular: %s' % requisito, request, "edit")
        #         return JsonResponse({"result": True})
        #     except Exception as ex:
        #         return JsonResponse({'result': False, "message": str(ex)})

        # elif action == 'validararchivo':
        #     try:
        #         archivos = InscripcionRequisitosActividadConvalidacionPPV.objects.get(id=int(request.POST['id']))
        #         archivos.estado = request.POST['est']
        #         archivos.observacion = request.POST['obs']
        #         dias = archivos.requisito.diascorreccion
        #         # estadoarchivo = InscripcionRequisitosActividadConvalidacionPPV.objects.get(pk=archivos.estado)
        #         if int(request.POST['est']) == 0:
        #             archivos.estado = 3
        #             estado_p = 'CORREGIR'
        #             notificacion = Notificacion(titulo="Evidencia revisada en el módulo Actividades Extracurriculares",
        #                                         cuerpo=f"Ha sido revisada la evidencia {archivos.requisito.titulo} de la ACTIVIDAD EXTRACURRICULAR {archivos.requisito.actividad.titulo} y se encuentra en estado {estado_p}, debe subir el archivo corregigo hasta la fecha XXXXX",
        #                                         destinatario=archivos.actividad.inscripcion.persona,
        #                                         url="/adm_convalidacionpractica",
        #                                         fecha_hora_visible=datetime.now() + timedelta(days=dias),
        #                                         content_type=None,
        #                                         object_id=None,
        #                                         prioridad=1,
        #                                         app_label='sga')
        #             notificacion.save()
        #
        #         elif int(request.POST['est']) == 1:
        #             archivos.estado = 1
        #
                    # notificacion = Notificacion(titulo="Evidencia aprobada en el módulo Actividades Extracurriculares",
                    #                             cuerpo=f"Ha sido aprobada la evidencia {archivos.requisito.titulo} de la ACTIVIDAD EXTRACURRICULAR {archivos.requisito.actividad.titulo}.",
                    #                             destinatario=archivos.actividad.inscripcion.persona,
                    #                             url="/adm_convalidacionpractica",
                    #                             fecha_hora_visible=datetime.now() + timedelta(days=dias),
                    #                             content_type=None,
                    #                             object_id=None,
                    #                             prioridad=1,
                    #                             app_label='sga')
                    # notificacion.save()
        #
        #         elif int(request.POST['est']) == 2:
        #             archivos.estado = 2
        #
                    # notificacion = Notificacion(titulo="Evidencia rechazada en el módulo Actividades Extracurriculares",
                    #                             cuerpo=f"Ha sido rechazada la evidencia {archivos.requisito.titulo} de la ACTIVIDAD EXTRACURRICULAR {archivos.requisito.actividad.titulo}.",
                    #                             destinatario=archivos.actividad.inscripcion.persona,
                    #                             url="/adm_convalidacionpractica",
                    #                             fecha_hora_visible=datetime.now() + timedelta(days=dias),
                    #                             content_type=None,
                    #                             object_id=None,
                    #                             prioridad=1,
                    #                             app_label='sga')
                    # notificacion.save()

        #         archivos.save(request)
        #         # correos = archivos.actividad.inscripcion.persona.lista_emails_envio()
        #         # send_html_mail("Proyectos de vinculación Informa!",
        #         #                "adm_convalidacionpractica/emails/notificacionvoluntariado.html",
        #         #                {'sistema': request.session['nombresistema'], 'registro': archivos,
        #         #                 'palabra_estado': estado_p,
        #         #                 't': miinstitucion(), 'dominio': EMAIL_DOMAIN}, ['jnavarretej@unemi.edu.ec'], [],
        #         #                cuenta=CUENTAS_CORREOS[0][1])
        #
        #
        #         return JsonResponse({"result": "ok"})
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})



        elif action == 'firmararchivo':

            try:
                id = int(encrypt(request.POST['id']))
                registro = InscripcionRequisitosActividadConvalidacionPPV.objects.get(pk=id)
                documento_a_firmar = archivo = registro.archivo.file
                nombre_documento = os.path.basename(registro.archivo.name)
                certificado = request.FILES["firma"]
                contrasenaCertificado = request.POST['palabraclave']
                razon = request.POST['razon'] if 'razon' in request.POST else ''
                jsonFirmas = json.loads(request.POST['txtFirmas'])
                name_documento_a_firmar, extension_documento_a_firmar = os.path.splitext(documento_a_firmar.name)
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()
                if not jsonFirmas:
                    messages.error(request, "Error: Debe seleccionar ubicación de la firma")
                    return redirect(request.path)
                for membrete in jsonFirmas:
                    datau = JavaFirmaEc(
                        archivo_a_firmar=documento_a_firmar, archivo_certificado=bytes_certificado, extension_certificado=extension_certificado,
                        password_certificado=contrasenaCertificado,
                        page=int(membrete["numPage"]), reason=razon, lx=membrete["x"], ly=membrete["y"]
                    ).sign_and_get_content_bytes()
                    documento_a_firmar = io.BytesIO()
                    documento_a_firmar.write(datau)
                    documento_a_firmar.seek(0)
                registro.archivo.save(f'{nombre_documento}', ContentFile(documento_a_firmar.read()))
                registro.estado_firma = 1
                registro.save()
                log(f"Firmo documento: {registro.archivo}", request, 'add')
                return JsonResponse({"result":"ok","idBoton":str(id)})
            except Exception as ex:
                messages.error(request, "Error: {}".format(ex))
                return redirect(request.path)       
        

        elif action == 'validararchivo':
            try:
                archivos = InscripcionRequisitosActividadConvalidacionPPV.objects.get(id=int(request.POST['id']))
                archivos.estado = request.POST['est']
                archivos.observacion = request.POST['obs']
                dias = archivos.requisito.diascorreccion
                # estadoarchivo = InscripcionRequisitosActividadConvalidacionPPV.objects.get(pk=archivos.estado)

                if int(request.POST['est']) == 0:
                    if archivos.requisito.diascorreccion:
                        archivos.estado = 3
                        data['fechaactual'] = fechaactual = datetime.now().date()
                        fno = datetime.now() + timedelta(days=dias)
                        fnueva = datetime.strptime(str(fno)[:10], "%Y-%m-%d").date()
                        archivos.fechaenviacorregir = fnueva

                        notificacion = Notificacion(
                            titulo="Evidencia revisada en el módulo Actividades Extracurriculares",
                            cuerpo=f"Se ha revisado la evidencia {archivos.requisito.titulo} de la ACTIVIDAD EXTRACURRICULAR {archivos.requisito.actividad.titulo} y se encuentra en estado CORREGIR, debe subir el archivo corregido hasta la fecha {fnueva}",
                            destinatario=archivos.actividad.inscripcion.persona,
                            url="/adm_convalidacionpractica",
                            fecha_hora_visible=datetime.now() + timedelta(days=dias),
                            content_type=None,
                            object_id=None,
                            prioridad=1,
                            app_label='sga')
                        notificacion.save()
                    else:
                        return JsonResponse({"result": "no"})

                elif int(request.POST['est']) == 1:
                    archivos.estado = 1
                    notificacion = Notificacion(titulo="Evidencia aprobada en el módulo Actividades Extracurriculares",
                                                cuerpo=f"Se ha aprobado la evidencia {archivos.requisito.titulo} de la ACTIVIDAD EXTRACURRICULAR {archivos.requisito.actividad.titulo}.",
                                                destinatario=archivos.actividad.inscripcion.persona,
                                                url="/adm_convalidacionpractica",
                                                fecha_hora_visible=datetime.now() + timedelta(days=2),
                                                content_type=None,
                                                object_id=None,
                                                prioridad=1,
                                                app_label='sga')
                    notificacion.save()
                elif int(request.POST['est']) == 2:
                    archivos.estado = 2
                    notificacion = Notificacion(titulo="Evidencia rechazada en el módulo Actividades Extracurriculares",
                                                cuerpo=f"Se ha rechazado la evidencia {archivos.requisito.titulo} de la ACTIVIDAD EXTRACURRICULAR {archivos.requisito.actividad.titulo}.",
                                                destinatario=archivos.actividad.inscripcion.persona,
                                                url="/adm_convalidacionpractica",
                                                fecha_hora_visible=datetime.now() + timedelta(days=2),
                                                content_type=None,
                                                object_id=None,
                                                prioridad=1,
                                                app_label='sga')
                    notificacion.save()

                archivos.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'guardardiascorreccion':
            try:
                archivo = RequisitosActividadConvalidacionPPV.objects.get(id=int(request.POST['id']))
                archivo.diascorreccion = request.POST['dias']
                # archivo.fechaenviacorregir = datetime.now().date()
                # print(archivo.tiempolimitecorreccion())
                archivo.save(request)
                # return JsonResponse({"result": "ok", "textofmax": archivo.textofechamaximaCorreccion(), "textotlim": archivo.textotiempolimCorreccion()})
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'guardarhorasrequisito':
            try:

                archivo = RequisitosActividadConvalidacionPPV.objects.get(status = True, id=int(request.POST['id']))
                archivo.horasrequisito = request.POST['horas']
                idactividad = archivo.actividad.id
                actividad = ActividadConvalidacionPPV.objects.get(status = True, id = int(idactividad))
                horasactividad = actividad.horas
                sumarhoras = int(request.POST['horas'])
                comprobarhoras = RequisitosActividadConvalidacionPPV.objects.filter(~Q(id=int(request.POST['id'])), status = True, actividad = int(idactividad))

                if sumarhoras > horasactividad:
                    return JsonResponse({"result": "no"})

                if comprobarhoras.exists():
                    for hor in comprobarhoras:
                        if hor.horasrequisito:
                            hora = hor.horasrequisito
                        else:
                            hora = 0
                        sumarhoras = int(hora) + sumarhoras

                    if sumarhoras > horasactividad:
                        return JsonResponse({"result": "no"})

                archivo.save(request)

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'editfecha':
            try:
                id = request.POST['id']
                valor = request.POST['valor']
                fecha_ = convertirfecha2(valor) + timedelta(days=1)
                requisito = RequisitosActividadConvalidacionPPV.objects.get(pk=id)
                requisito.flimite = fecha_
                requisito.save(request)
                log(u'Modificó Fecha Limite de Requisito Actividad Extracurricular: %s' % requisito, request, "edit")
                return JsonResponse({"result": True, "id": requisito.id, "tiempo": requisito.textoTiempo()})
            except Exception as ex:
                return JsonResponse({'result': False, "message": str(ex)})

        elif action == 'listaitinerario':
                try:
                    carrera = Carrera.objects.get(pk=int(request.POST['id']))

                    # SALUD = 1
                    listaitinerarios = []
                    puedeadicionar = False
                    existeitinerario = False
                    mensaje = ''
                    itinerarios = ItinerariosMalla.objects.filter(malla_id=carrera.malla().id, status=True)
                    if itinerarios:
                        for itinerario in itinerarios:
                            listaitinerarios.append([itinerario.id, itinerario.__str__()])
                        existeitinerario = True
                        puedeadicionar = True

                    return JsonResponse(
                        {'result': 'ok', 'puedeadicionar': puedeadicionar, 'itinerarios': listaitinerarios,
                         'mensaje': mensaje, 'existeitinerario': existeitinerario})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addactividad':
                try:
                    # carreras_director = persona.carreras_director_periodo(periodo)
                    carreras_director = persona.mis_carreras_tercer_nivel()
                    idcarreras = [c.id for c in carreras_director]
                    # profesores_director = persona.profesores_director_periodo(periodo, idcarreras)
                    profesores_director = persona.profesores_periodo_general(periodo)
                    profesores_todos = Profesor.objects.filter(status=True, activo=True)
                    carreras = Carrera.objects.filter(status=True)

                    if es_director_carr:
                        data['title'] = u'Agregar actividad extracurricular'
                        form = ActividadConvalidacionForm()
                        form.adicionar()
                        form.carreras_director(carreras_director)
                        form.profesores_director(profesores_director)
                    elif es_director_vincu:
                        data['title'] = u'Agregar actividad extracurricular'
                        form = ActividadConvalidacionVoluntariadoForm()
                        form.carreras_director(carreras)
                        form.profesores_director(profesores_todos)

                    data['form'] = form
                    return render(request, "adm_convalidacionpractica/addactividad.html", data)
                except Exception as ex:
                    pass

            if action == 'firmararchivo':
                try:

                    #   dominio_sistema = 'http://127.0.0.1:8000'
                    registro = InscripcionRequisitosActividadConvalidacionPPV.objects.get(id=int(request.GET['id']))
                    data['archivo']=archivo = registro.archivo
                    qr = qrImgFirma(request, persona, "png", paraMostrar=True)
                    data["qrBase64"] = qr[0]
                    data['archivo_url']=f"/media/{archivo}"
                    data['id']=id = request.GET['id']
                    data['title']=u'Firmar archivo de Actividad Extracurricular'
                    data['action']='firmararchivo'
                    template = get_template("formfirmaelectronica_v2.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    return JsonResponse({"result": 'bad', 'mensaje':'Ocurrio un error'})
            
            elif action == 'verificarfirmas':
                try:
                    id = int(request.GET['id'])
                    registro = InscripcionRequisitosActividadConvalidacionPPV.objects.get(pk=id)
                    archivo = registro.archivo.file
                    valido, msg, diccionario = verificarFirmasPDF(archivo)
                    if valido:
                        registro.estado_firma = 1
                        registro.save()
                        log(f"Cambio el estado de la firma de {registro.archivo}", request,
                            'add')
                    else:
                        registro.estado_firma = 2
                        registro.save()
                        log(f"Cambio el estado de la firma de  {registro.archivo}", request,
                            'add')
                    return JsonResponse({'result': True,'context':diccionario,"idState":str(id)})
                except Exception as ex:
                    return JsonResponse({'result': False, "mensaje": 'Error!: {}'.format(ex)}, safe=False)

            if action == 'addactividadvoluntariado':
                try:
                    data['title'] = u'Agregar actividad extracurricular'

                    # carreras_director = persona.carreras_director_periodo(periodo)
                    carreras_director = persona.mis_carreras_tercer_nivel()
                    carreras = Carrera.objects.filter(status=True, coordinacion__in=[1,2,3,4,5])
                    # profesores_director = persona.profesores_director_periodo(periodo, idcarreras)
                    profesores_director = persona.profesores_periodo_general(periodo)
                    form = ActividadConvalidacionVoluntariadoForm()
                    form.carreras_director(carreras)
                    form.profesores_director(profesores_director)
                    data['form'] = form
                    return render(request, "adm_convalidacionpractica/addactividadvoluntariado.html", data)
                except Exception as ex:
                    pass

            elif action == 'editactividad':
                try:
                    data['title'] = u'Editar actividad extracurricular'

                    # carreras_director = persona.carreras_director_periodo(periodo)
                    carreras_director = persona.mis_carreras_tercer_nivel()
                    idcarreras = [c.id for c in carreras_director]
                    # profesores_director = persona.profesores_director_periodo(periodo, idcarreras)
                    profesores_director = persona.profesores_periodo_general(periodo)

                    data['actividad']= actividad = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.GET['id'])))

                    form = ActividadConvalidacionForm(initial={'titulo': actividad.titulo,
                                                               'tipoactividad': actividad.tipoactividad,
                                                               'fechainicio': actividad.fechainicio,
                                                               'fechafin': actividad.fechafin,
                                                               'horas': actividad.horas,
                                                               'profesor': actividad.profesor,
                                                               'carrera': actividad.carrera.all().first(),
                                                               'carreramultiple':actividad.carrera.all(),
                                                               'inicioinscripcion': actividad.inicioinscripcion,
                                                               'fininscripcion': actividad.fininscripcion,
                                                               'cupo': actividad.cupo,
                                                               'nivelminimo': actividad.nivelminimo,
                                                               'itinerario':actividad.itinerariomalla,
                                                               })
                    if actividad.carrera.all().exists():
                        form.editar(actividad.carrera.all().first().malla())
                    else:
                        form.adicionar()
                    form.carreras_director(carreras_director)
                    form.profesores_director(profesores_director)

                    mincupos = minhoras = 1
                    if actividad.total_alumnos_inscritos() > 0 or actividad.total_alumnos_preinscritos() > 0:
                        data['inscritos'] = True
                        mincupos = actividad.total_alumnos_inscritos() + actividad.total_alumnos_preinscritos()

                    if actividad.total_detalle_actividades_profesor() > 0:
                        data['inscritos'] = True
                        minhoras = actividad.total_horas_detalle_actividades()

                    data['mincupos'] = mincupos
                    data['minhoras'] = minhoras

                    data['form'] = form
                    data['id'] = actividad.id
                    return render(request, "adm_convalidacionpractica/editactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'editactividadvoluntariado':
                try:
                    data['title'] = u'Editar actividad extracurricular'
                    # carreras_director = persona.carreras_director_periodo(periodo)
                    carreras_director = persona.mis_carreras_tercer_nivel()
                    carreras = Carrera.objects.filter(status=True, coordinacion__in=[1,2,3,4,5])
                    profesores_todos = Profesor.objects.filter(status=True, activo=True)
                    # profesores_director = persona.profesores_director_periodo(periodo, idcarreras)
                    profesores_director = persona.profesores_periodo_general(periodo)
                    data['actividad']=actividad = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = ActividadConvalidacionVoluntariadoForm(initial={'titulo': actividad.titulo,
                                                                           'tipoactividad': actividad.tipoactividad,
                                                                           'fechainicio': actividad.fechainicio,
                                                                           'fechafin': actividad.fechafin,
                                                                           'horas': actividad.horas,
                                                                           'profesor': actividad.profesor,
                                                                           'carrera': actividad.carrera.first(),
                                                                           'carreramultiple': actividad.carrera.all(),
                                                                           'inicioinscripcion': actividad.inicioinscripcion,
                                                                           'fininscripcion': actividad.fininscripcion,
                                                                           'cupo': actividad.cupo,
                                                                           'nivelminimo': actividad.nivelminimo,
                                                                           'itinerario': actividad.itinerariomalla,
                                                                           'voluntariado': True})
                    form.carreras_director(carreras)
                    form.profesores_director(profesores_todos)
                    mincupos = minhoras = 1
                    if actividad.total_alumnos_inscritos() > 0 or actividad.total_alumnos_preinscritos() > 0:
                        data['inscritos'] = True
                        mincupos = actividad.total_alumnos_inscritos() + actividad.total_alumnos_preinscritos()
                    if actividad.total_detalle_actividades_profesor() > 0:
                        data['inscritos'] = True
                        minhoras = actividad.total_horas_detalle_actividades()
                    data['mincupos'] = mincupos
                    data['minhoras'] = minhoras
                    data['form'] = form
                    data['id'] = actividad.id
                    return render(request, "adm_convalidacionpractica/editaractividadvoluntariado.html", data)
                except Exception as ex:
                    pass

            elif action == 'delactividad':
                try:
                    data['title'] = u'Eliminar actividad extracurricular'
                    data['actividad'] = actividad = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['totalpreinscritos'] = actividad.total_alumnos_preinscritos()
                    return render(request, "adm_convalidacionpractica/deleteactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'actualizar_informe':
                try:
                    data['title'] = u'Actualizar informe de actividad extracurricular'
                    data['actividad'] = actividad = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_convalidacionpractica/actualizarinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'anularactividad':
                try:
                    data['title'] = u'Suspender actividad extracurricular'
                    data['actividad'] = actividad = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['totalpreinscritos'] = actividad.total_alumnos_preinscritos()
                    return render(request, "adm_convalidacionpractica/anularactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'delactividadvoluntariado':
                try:
                    data['title'] = u'Eliminar actividad extracurricular'
                    data['actividad'] = actividad = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['totalpreinscritos'] = actividad.total_alumnos_preinscritos()
                    return render(request, "adm_convalidacionpractica/deleteactividadvoluntariado.html", data)
                except Exception as ex:
                    pass

            elif action == 'quitaraprobadodirector':
                try:
                    data['title'] = u'Quitar estado aprobado por director de carrera'
                    data['actividad'] = actividad = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_convalidacionpractica/quitaraprobadodirector.html", data)
                except Exception as ex:
                    pass

            elif action == 'mostrararchivos':
                try:
                    data['title'] = u'Archivos Soporte de la Actividad Extracurricular'
                    data['id'] = int(request.GET['id'])
                    data['actividad'] = ActividadConvalidacionPPV.objects.get(pk=int(request.GET['id']))

                    template = get_template("adm_convalidacionpractica/mostrararchivoactividad.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'mostrarinscritos':
                try:
                    data['title'] = u'Estudiantes Inscritos en la Actividad Extracurricular'
                    data['id'] = int(request.GET['id'])
                    data['actividad'] = actividad = ActividadConvalidacionPPV.objects.get(pk=int(request.GET['id']))
                    data['inscritos'] = actividad.alumnos_inscritos()

                    template = get_template("adm_convalidacionpractica/inscritos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'mostraractividad':
                try:
                    data['title'] = u'Actividad ExtraCurricular'
                    data['id'] = int(request.GET['id'])
                    data['actividad'] = actividad = ActividadConvalidacionPPV.objects.get(pk=int(request.GET['id']))

                    data['detalle'] = actividad.detalle_actividades_profesor()

                    template = get_template("adm_convalidacionpractica/mostraractividad.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'mostraractividades':
                try:
                    data['title'] = u'Actividades a Cumplirse en la Actividad Extracurricular'
                    data['id'] = int(request.GET['id'])
                    data['actividad'] = actividad = ActividadConvalidacionPPV.objects.get(pk=int(request.GET['id']))
                    data['detalle'] = actividad.detalle_actividades_profesor()

                    template = get_template("adm_convalidacionpractica/mostrardetalleactividades.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'mostrarrecomendaciones':
                try:
                    data['title'] = u'Recomendaciones sobre Actividad Extracurricular'
                    data['id'] = int(request.GET['id'])
                    data['actividad'] = actividad = ActividadConvalidacionPPV.objects.get(pk=int(request.GET['id']))

                    data['detalle'] = RecomendacionesActividadConvalidacionPPV.objects.filter(actividad_id=int(request.GET['id']), status = True)

                    template = get_template("adm_convalidacionpractica/modal/mostrardetallerecomendaciones.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'mostrarpreinscritos':
                try:
                    id2 = int(request.GET['id2'])
                    data['title'] = u'Aceptación/Rechazo de Inscripciones en la Actividad Extracurricular'
                    data['id'] = int(request.GET['id'])
                    data['id2'] = id2

                    data['actividad'] = actividad = ActividadConvalidacionPPV.objects.get(pk=int(request.GET['id']))
                    if id2 == 2:
                        data['title'] = u'Rechazo de Inscripciones en la Actividad Extracurricular'
                        data['inscritos'] = actividad.alumnos_preinscritos2()
                    else:
                        data['inscritos'] = actividad.alumnos_preinscritos()

                    template = get_template("adm_convalidacionpractica/aceptarinscripcion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass


            elif action == 'registrocumplimiento':
                try:
                    data['title'] = u'Registro de Cumplimiento de Actividades'
                    data['id'] = int(request.GET['id'])
                    data['actividad'] = actividad = ActividadConvalidacionPPV.objects.get(pk=int(request.GET['id']))
                    data['inscritos'] = inscritos = actividad.alumnos_inscritos()

                    inscripcionactividad = actividad.inscripcionactividad()

                    # inscripcionrequisito = InscripcionRequisitosActividadConvalidacionPPV.objects.filter(actividad=inscripcionactividad)

                    totalaprobado = actividad.total_alumnos_aprobados_profesor()
                    totalreprobado = actividad.total_alumnos_reprobados_profesor()
                    totalpendiente = inscritos.count() - (totalaprobado + totalreprobado)
                    data['totalpendiente'] = totalpendiente
                    data['totalaprobado'] = totalaprobado
                    data['totalreprobado'] = totalreprobado
                    data['obliginforme'] = 'S' if totalpendiente > 0 else 'N'

                    if RequisitosActividadConvalidacionPPV.objects.filter(status=True, actividad__id=int(request.GET['id'])):
                        hayrequisito = True
                    else:
                        hayrequisito = False

                    data['hayrequisito'] = hayrequisito
                    #
                    # data['requisi'] = requisi = actividad.requisitosactividad()


                    template = get_template("adm_convalidacionpractica/registrocumplimiento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'registrocumplimiento_requisitos':
                try:
                    data['title'] = u'Registro de Cumplimiento de Actividades con Requisitos'
                    data['id'] = int(request.GET['id'])
                    data['actividad'] = actividad = ActividadConvalidacionPPV.objects.get(pk=int(request.GET['id']))
                    data['inscritos'] = inscritos = actividad.alumnos_inscritos()
                    totalaprobado = actividad.total_alumnos_aprobados_profesor()
                    totalreprobado = actividad.total_alumnos_reprobados_profesor()
                    totalpendiente = inscritos.count() - (totalaprobado + totalreprobado)
                    data['totalpendiente'] = totalpendiente
                    data['totalaprobado'] = totalaprobado
                    data['totalreprobado'] = totalreprobado
                    data['obliginforme'] = 'S' if totalpendiente > 0 else 'N'

                    template = get_template("adm_convalidacionpractica/registrocumplimiento_requisitos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'aprobarconvalidacion':
                try:
                    data['title'] = u'Aprobación de Convalidación de Actividad ExtraCurricular'
                    data['id'] = int(request.GET['id'])
                    data['actividad'] = actividad = ActividadConvalidacionPPV.objects.get(pk=int(request.GET['id']))
                    data['inscritos'] = inscritos = actividad.alumnos_inscritos()

                    totalaprobadoprofesor = actividad.total_alumnos_aprobados_profesor()
                    totalreprobadoprofesor = actividad.total_alumnos_reprobados_profesor()


                    data['totalaprobadoprofesor'] = totalaprobadoprofesor
                    data['totalreprobadoprofesor'] = totalreprobadoprofesor

                    totalaprobado = actividad.total_alumnos_aprobados_director()
                    totalreprobado = actividad.total_alumnos_reprobados_director()

                    if totalreprobado == 0: totalreprobado = totalreprobadoprofesor

                    totalpendiente = inscritos.count() - (totalaprobado + totalreprobado)
                    data['totalpendiente'] = totalpendiente
                    data['totalaprobado'] = totalaprobado
                    data['totalreprobado'] = totalreprobado

                    template = get_template("adm_convalidacionpractica/aprobacionconvalidacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'convalidarpractica':
                try:
                    data['title'] = u'Convalidar Actividad ExtraCurricular (Prácticas Pre Profesionales/Proyectos Servicio Comunitario)'
                    data['id'] = int(request.GET['id'])
                    data['actividad'] = actividad = ActividadConvalidacionPPV.objects.get(pk=int(request.GET['id']))
                    data['inscritos'] = inscritos = actividad.alumnos_inscritos()

                    totalaprobadoprofesor = actividad.total_alumnos_aprobados_profesor()
                    totalreprobadoprofesor = actividad.total_alumnos_reprobados_profesor()

                    totalaprobadodirector = actividad.total_alumnos_aprobados_director()
                    totalreprobadodirector = actividad.total_alumnos_reprobados_director()


                    data['totalaprobadoprofesor'] = totalaprobadoprofesor
                    data['totalreprobadoprofesor'] = totalreprobadoprofesor

                    data['totalaprobadodirector'] = totalaprobadodirector
                    data['totalreprobadodirector'] = totalreprobadodirector

                    totalaprobado = actividad.total_alumnos_aprobados_areavinculacion()
                    totalreprobado = actividad.total_alumnos_reprobados_areavinculacion()

                    if totalreprobado == 0: totalreprobado = totalreprobadodirector

                    totalpendiente = inscritos.count() - (totalaprobado + totalreprobado)
                    data['totalpendiente'] = totalpendiente
                    data['totalaprobado'] = totalaprobado
                    data['totalreprobado'] = totalreprobado

                    template = get_template("adm_convalidacionpractica/convalidarpractica.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'ingresoactividades':
                try:
                    data['title'] = u'Ingreso de Actividades'
                    data['id'] = int(request.GET['id'])
                    data['actividad'] = actividad = ActividadConvalidacionPPV.objects.get(pk=int(request.GET['id']))

                    detalleactividades = ""
                    if actividad.detalle_actividades_profesor():
                        detalleactividades = "|".join([str(a.id) + "~" + a.detalle + "~" + str(a.horas) + "~" + a.observacion for a in actividad.detalle_actividades_profesor()])

                    data['detalle'] = detalleactividades

                    template = get_template("adm_convalidacionpractica/ingresoactividad.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'actividadasignada':
                try:
                    data['esdirectorcarr'] = es_director_carr
                    data['esdocente'] = es_docente
                    data['esdirectorvinc'] = es_director_vincu
                    #data['esanalistavinc'] = es_analista_vincu

                    lista_periodos = ActividadConvalidacionPPV.objects.filter(status=True,
                                                                              profesor__persona=persona).values_list('periodo', flat=True).distinct()

                    actividad_distinct = Periodo.objects.filter(pk__in=lista_periodos)
                    data['actividades_periodos'] = actividad_distinct

                    listo = True
                    search = None
                    ids = None

                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        peri = request.GET['periodo']
                        if peri == '0' and search == '':
                            actividades = ActividadConvalidacionPPV.objects.filter(status=True, profesor__persona=persona).order_by('-id')
                        else:
                            actividades = ActividadConvalidacionPPV.objects.filter(titulo__icontains=search, status=True, periodo=peri, profesor__persona=persona).order_by('-id')
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        actividades = ActividadConvalidacionPPV.objects.filter(id=ids).order_by('-id')
                    elif 'periodo' in request.GET:
                        peri = request.GET['periodo']
                        actividades = ActividadConvalidacionPPV.objects.filter(status=True, periodo = peri, profesor__persona=persona).order_by('-id')
                    else:
                        actividades = ActividadConvalidacionPPV.objects.filter(status=True, profesor__persona=persona).order_by('-id')

                    tipoactividad = 0
                    if 'tipoactividad' in request.GET:
                        tipoactividad = int(request.GET['tipoactividad'])
                        if tipoactividad > 0:
                            actividades = actividades.filter(tipoactividad=tipoactividad)

                    paging = MiPaginador(actividades, 25)
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
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['actividades'] = page.object_list
                    data['listo'] = listo
                    # data['actividades'] =
                    #
                    # data['totalsolicitudes'] = total = solicitudes.count()
                    # data['totalaprobadas'] = aprobadas = solicitudes.filter(estado=2).count()
                    # data['totalrechazadas'] = rechazadas = solicitudes.filter(estado=3).count()
                    # data['totalrevision'] = revision = solicitudes.filter(estado=5).count()
                    # data['totalpendiente'] = total - (aprobadas + rechazadas + revision)
                    data['tipoactividad'] = tipoactividad
                    #
                    #
                    # data['fechaactual'] = datetime.now().strftime('%d-%m-%Y')


                    data['title'] = u'Mis Actividades ExtraCurriculares de Convalidación Asignadas'
                    return render(request, "adm_convalidacionpractica/profesoractividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'excelestudiantesinscritos':
                columns = [
                    ('Cédula del Estudiante', 6000),
                    ('Estudiante', 6000),
                    ('Email Estudiante', 6000),
                    ('Carrera', 6000),
                    ('Nivel', 6000),
                    ('Horas Cumplidas', 6000),
                    ('Institución', 6000),
                    ('Actividad', 8000),
                    ('Tipo actividad', 8000),
                    ('Fehca inicio actividad', 8000),
                    ('Fecha fin actividad', 8000),
                    ('Horas actividad', 8000),
                    ('Estado asignado por el profesor', 8000),
                    ('Fecha asignación estado del profesor', 8000),
                    ('Observación del profesor', 8000),
                    ('Estado asignado por el director de carrera', 8000),
                    ('Fecha asignación estado del director de carrera', 8000),
                    ('Observación del director de carrera', 8000),
                    ('Estado asignado por la dirección de vinculación', 8000),
                    ('Fecha asignación estado de la dirección de vinculación', 8000),
                    ('Responsable de la dirección de vinculación', 8000),
                    ('Observación de la dirección de vinculación', 8000),
                    ('Fecha de aceptación o rechazo de la inscripción', 8000),
                    ('Estado de la Inscripción', 8000),
                    ('Observación de aceptación o rechazo de la inscripción', 8000),
                    ('Período', 8000),
                    ('Itinerario', 8000),

                ]
                response = HttpResponse(content_type='application/ms-excel')
                response['Content-Disposition'] = 'attachment; filename="reporte_convalidacionpractica.xls"'
                wb = xlwt.Workbook(encoding='utf-8')
                ws = wb.add_sheet('HOJA_1')
                row_num = 0
                font_style = xlwt.XFStyle()
                font_style.font.bold = True
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                font_style = xlwt.XFStyle()
                inscritos = InscripcionActividadConvalidacionPPV.objects.filter(actividad_id=int(request.GET['id']), status=True).order_by('-actividad__fechainicio')
                for det in inscritos:
                    row_num += 1
                    ws.write(row_num, 0, det.inscripcion.persona.cedula, font_style)

                    ws.write(row_num, 1, det.inscripcion.persona.__str__(), font_style)
                    ws.write(row_num, 2, det.inscripcion.persona.emailinst, font_style)
                    ws.write(row_num, 3, det.inscripcion.carrera.nombre, font_style)
                    ws.write(row_num, 4, str(det.inscripcion.mi_nivel()), font_style)
                    ws.write(row_num, 5, det.horascumplidas, font_style)
                    ws.write(row_num, 6, det.institucion_actividad, font_style)
                    ws.write(row_num, 7, det.actividad.titulo, font_style)

                    ws.write(row_num, 8, det.actividad.get_tipoactividad(), font_style)
                    ws.write(row_num, 9, str(det.actividad.fechainicio), font_style)
                    ws.write(row_num, 10, str(det.actividad.fechafin), font_style)
                    ws.write(row_num, 11, det.actividad.horas, font_style)


                    ws.write(row_num, 12, det.get_estado_profesor() if det.estadoprofesor else '', font_style)
                    ws.write(row_num, 13, str(det.fechaestadoprofesor), font_style)
                    ws.write(row_num, 14, det.observacionprofesor, font_style)

                    ws.write(row_num, 15, det.get_estado_director()if det.estadodirectorcarrera else '', font_style)
                    ws.write(row_num, 16, str(det.fechaestadodirector), font_style)
                    ws.write(row_num, 17, det.observaciondirector, font_style)

                    ws.write(row_num, 18, det.get_estado_vinculacion() if det.estadovinculacion else '', font_style)
                    ws.write(row_num, 19, str(det.fechaestadovinculacion), font_style)

                    if det.responsablevinculacion:
                        vincula = Persona.objects.get(pk = int(det.responsablevinculacion.id))
                        nombrevin = vincula.nombre_completo()
                        ws.write(row_num, 20, nombrevin, font_style)
                    else:
                        ws.write(row_num, 20, '', font_style)

                    ws.write(row_num, 21, det.observacionvinculacion, font_style)
                    ws.write(row_num, 22, str(det.fechaaceptarechaza), font_style)
                    ws.write(row_num, 23, det.get_estado_display(), font_style)
                    ws.write(row_num, 24, det.observacion, font_style)
                    ws.write(row_num, 25, str(det.actividad.periodo.nombre), font_style)
                    ws.write(row_num, 26, str(det.actividad.itinerariomalla) if det.actividad.itinerariomalla else 'NO REGISTRA', font_style)
                    # ws.write(row_num, 5, det.actividad.profesor.persona.__str__(), font_style)
                    # ws.write(row_num, 6, det.actividad.profesor.persona.emailinst, font_style)
                    # ws.write(row_num, 7, str(det.actividad.inicioinscripcion), font_style)
                    # ws.write(row_num, 8, str(det.actividad.fininscripcion), font_style)
                    # ws.write(row_num, 9, det.inscripcion.persona.cedula, font_style)
                    # ws.write(row_num, 10, det.inscripcion.persona.__str__(), font_style)
                    # ws.write(row_num, 16, det.observacion, font_style)

                wb.save(response)
                return response

            elif action == 'convalidacionpractica':
                try:
                    data['esdirectorcarr'] = es_director_carr
                    data['esdocente'] = es_docente
                    data['estados_convalidacion'] = ESTADO_ACTIVIDAD_CONVALIDACION
                    data['esdirectorvinc'] = es_director_vincu
                    #data['esanalistavinc'] = es_analista_vincu
                    desde, hasta = request.GET.get('desde',''), request.GET.get('hasta','')
                    data['desde'] = desde
                    data['hasta'] = hasta

                    search = None
                    ids = None
                    est = 0
                    actividades = ActividadConvalidacionPPV.objects.filter(status=True).order_by('-id')
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            actividades = actividades.filter(Q(titulo__icontains=search) | Q(profesor__persona__apellido1__icontains=search) | Q(profesor__persona__apellido2__icontains=search), status=True).order_by('-id')
                        else:
                            actividades = actividades.filter(Q(profesor__persona__apellido1__icontains=ss[0]) & Q(profesor__persona__apellido2__icontains=ss[1]), status=True).order_by('-id')
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        actividades = actividades.filter(id=ids).order_by('-id')
                    if 'est' in request.GET:
                        data['est'] = est = int(request.GET['est'])
                        if est > 0:
                            actividades = actividades.filter(estado=est)
                    tipoactividad = 0
                    if 'tipoactividad' in request.GET:
                        tipoactividad = int(request.GET['tipoactividad'])
                        if tipoactividad > 0:
                            actividades = actividades.filter(tipoactividad=tipoactividad)
                    if desde:
                        actividades = actividades.filter(fechainicio__gte=desde)
                    if hasta:
                        actividades = actividades.filter(fechafin__lte=hasta)

                    if 'exportar_excel' in request.GET:
                        columns = [
                            ('Actividad', 10000),
                            ('Tipo', 10000),
                            ('Fecha Inicio de la actividad', 5000),
                            ('Fecha Fin de la actividad', 5000),
                            ('Total Horas de la actividad', 6000),
                            ('Profesor Asignado', 6000),
                            ('Email de Profesor', 6000),
                            ('Carreras', 6000),
                            ('Inicio Inscripciones', 5000),
                            ('Fin Inscripciones', 5000),
                            ('Total Cupos', 6000),
                            ('Total Pre-Inscritos', 6000),
                            ('Total Inscritos', 6000),
                            ('Cupos Disponible', 6000),
                            ('Estado de la actividad', 20000),
                            ('Período actividad', 20000),
                            ('Itinerario', 6000),

                        ]
                        response = HttpResponse(content_type='application/ms-excel')
                        response['Content-Disposition'] = 'attachment; filename="reporte_convalidacionpractica.xls"'
                        wb = xlwt.Workbook(encoding='utf-8')
                        ws = wb.add_sheet('HOJA_1')
                        row_num = 0
                        font_style = xlwt.XFStyle()
                        font_style.font.bold = True
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        font_style = xlwt.XFStyle()
                        for det in actividades:
                            row_num += 1
                            ws.write(row_num, 0, det.titulo, font_style)
                            ws.write(row_num, 1, det.get_tipoactividad(), font_style)
                            ws.write(row_num, 2, str(det.fechainicio), font_style)
                            ws.write(row_num, 3, str(det.fechafin), font_style)
                            ws.write(row_num, 4, det.horas, font_style)
                            ws.write(row_num, 5, det.profesor.persona.__str__(), font_style)
                            ws.write(row_num, 6, det.profesor.persona.emailinst, font_style)
                            lista_carrera = ''
                            for carrera in det.carrera.all():
                                lista_carrera += " {},".format(carrera.nombre)
                            ws.write(row_num, 7, lista_carrera, font_style)
                            ws.write(row_num, 8, str(det.inicioinscripcion), font_style)
                            ws.write(row_num, 9, str(det.fininscripcion), font_style)
                            ws.write(row_num, 10, det.cupo, font_style)
                            ws.write(row_num, 11, det.total_alumnos_preinscritos(), font_style)
                            ws.write(row_num, 12, det.total_alumnos_inscritos(), font_style)
                            ws.write(row_num, 13, det.total_cupo_disponible(), font_style)
                            ws.write(row_num, 14, det.get_estado(), font_style)
                            ws.write(row_num, 15, str(det.periodo.nombre), font_style)
                            ws.write(row_num, 16, str(det.itinerariomalla) if det.itinerariomalla else 'NO REGISTRA', font_style)

                        wb.save(response)
                        return response

                    if 'exportar_excel_est' in request.GET:
                        columns = [
                            ('Actividad', 10000),
                            ('Tipo', 10000),
                            ('Fecha Inicio de la actividad', 5000),
                            ('Fecha Fin de la actividad', 5000),
                            ('Total Horas de la actividad', 6000),
                            ('Institución', 6000),
                            ('Profesor Asignado', 6000),
                            ('Email de Profesor', 6000),
                            ('Inicio Inscripciones', 5000),
                            ('Fin Inscripciones', 5000),
                            ('Cédula del Estudiante', 6000),
                            ('Estudiante', 6000),
                            ('Email Estudiante', 6000),
                            ('Carrera', 6000),
                            ('Nivel', 6000),
                            ('Horas Cumplidas', 6000),
                            ('Estado de la Inscripción', 6000),
                            ('Observación de aceptación o rechazo de la inscripción', 6000),
                            ('Itinerario', 6000),
                        ]
                        response = HttpResponse(content_type='application/ms-excel')
                        response['Content-Disposition'] = 'attachment; filename="reporte_convalidacionpractica.xls"'
                        wb = xlwt.Workbook(encoding='utf-8')
                        ws = wb.add_sheet('HOJA_1')
                        row_num = 0
                        font_style = xlwt.XFStyle()
                        font_style.font.bold = True
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        font_style = xlwt.XFStyle()
                        inscritos = InscripcionActividadConvalidacionPPV.objects.filter(actividad__in=actividades.values_list('id', flat=True), status=True).order_by('-actividad__fechainicio')
                        for det in inscritos:
                            row_num += 1
                            ws.write(row_num, 0, det.actividad.titulo, font_style)
                            ws.write(row_num, 1, det.actividad.get_tipoactividad(), font_style)
                            ws.write(row_num, 2, str(det.actividad.fechainicio), font_style)
                            ws.write(row_num, 3, str(det.actividad.fechafin), font_style)
                            ws.write(row_num, 4, det.actividad.horas, font_style)
                            ws.write(row_num, 5, det.institucion_actividad, font_style)
                            ws.write(row_num, 6, det.actividad.profesor.persona.__str__(), font_style)
                            ws.write(row_num, 7, det.actividad.profesor.persona.emailinst, font_style)
                            ws.write(row_num, 8, str(det.actividad.inicioinscripcion), font_style)
                            ws.write(row_num, 9, str(det.actividad.fininscripcion), font_style)
                            ws.write(row_num, 10, det.inscripcion.persona.cedula, font_style)
                            ws.write(row_num, 11, det.inscripcion.persona.__str__(), font_style)
                            ws.write(row_num, 12, det.inscripcion.persona.emailinst, font_style)
                            ws.write(row_num, 13, det.inscripcion.carrera.nombre, font_style)
                            ws.write(row_num, 14, str(det.inscripcion.mi_nivel()), font_style)
                            ws.write(row_num, 15, det.horascumplidas, font_style)
                            ws.write(row_num, 16, det.get_estado_display(), font_style)
                            ws.write(row_num, 17, det.observacion, font_style)
                            ws.write(row_num, 18, str(det.actividad.itinerariomalla) if det.actividad.itinerariomalla else 'NO REGISTRA', font_style)
                        wb.save(response)
                        return response

                    data['act_count'] = actividades.count()
                    paging = MiPaginador(actividades, 25)
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
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['actividades'] = page.object_list
                    # data['actividades'] =
                    #
                    # data['totalsolicitudes'] = total = solicitudes.count()
                    # data['totalaprobadas'] = aprobadas = solicitudes.filter(estado=2).count()
                    # data['totalrechazadas'] = rechazadas = solicitudes.filter(estado=3).count()
                    # data['totalrevision'] = revision = solicitudes.filter(estado=5).count()
                    # data['totalpendiente'] = total - (aprobadas + rechazadas + revision)
                    data['tipoactividad'] = tipoactividad
                    #
                    #
                    # data['fechaactual'] = datetime.now().strftime('%d-%m-%Y')


                    data['title'] = u'Convalidación de Prácticas Pre Profesionales y Proyectos de Servicio Comunitario'
                    return render(request, "adm_convalidacionpractica/convalidacionpractica.html", data)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'validarsolicitud':
                try:
                    data['title'] = u'Revisar/Aprobar Solicitud de Devolución'
                    data['ids'] = int(request.GET['ids'])

                    data['solicitud'] = solicitud = SolicitudDevolucionDinero.objects.get(pk=int(request.GET['ids']))

                    beneficiario = solicitud.persona
                    cuentabancaria = beneficiario.cuentabancaria()
                    data['beneficiario'] = beneficiario
                    data['cuentabancaria'] = cuentabancaria
                    data['validarcuenta'] = False if cuentabancaria.estadorevision == 2 else True
                    data['estadodocumento'] = request.GET['estadodocumento']

                    data['bancos'] = Banco.objects.filter(status=True).order_by('nombre')

                    if solicitud.personarevisa:
                        if solicitud.personarevisa != persona and solicitud.estado != 1:
                            return JsonResponse({"result": "bad", "mensaje": "La solicitud está siendo revisada por otro usuario."})
                        else:
                            if solicitud.estado != 2 and solicitud.estado != 3:
                                solicitud.personarevisa = persona
                                solicitud.estado = 5
                    else:
                        solicitud.personarevisa = persona
                        solicitud.estado = 5

                    solicitud.save(request)

                    if solicitud.estado in [2, 3]:
                        data['permite_modificar'] = False
                    else:
                        data['permite_modificar'] = True

                    template = get_template("rec_devoluciondinero/validarsolicitud.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'generarbeneficiarioscsv':
                try:
                    __author__ = 'Unemi'
                    desde = datetime.combine(convertir_fecha(request.GET['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.GET['hasta']), time.max)

                    fuentenormal = easyxf('font: name Verdana, color-index black, height 150;')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Beneficiarios')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=beneficiarios_' + random.randint(1,10000).__str__() + '.csv'

                    row_num = 0

                    for col_num in range(12):
                        ws.col(col_num).width = 5000

                    beneficiarios = Persona.objects.filter(cuentabancariapersona__status=True,
                                                           cuentabancariapersona__archivo__isnull=False,
                                                           inscripcion__becasolicitud__periodo_id__in=[110, 90],
                                                           inscripcion__becasolicitud__becaasignacion__status=True,
                                                           cuentabancariapersona__fechavalida__range=(desde, hasta),
                                                           cuentabancariapersona__archivoesigef=False).distinct().order_by('apellido1', 'apellido2', 'nombres')

                    for beneficiario in beneficiarios:
                        ws.write(row_num, 0, beneficiario.identificacion(), fuentenormal)
                        ws.write(row_num, 1, remover_caracteres_tildes_unicode(beneficiario.nombre_completo_inverso()[:100]), fuentenormal)
                        ws.write(row_num, 2, remover_caracteres_tildes_unicode(beneficiario.direccion_completa()[:300]), fuentenormal)
                        ws.write(row_num, 3, beneficiario.telefono, fuentenormal)
                        ws.write(row_num, 4, '0', fuentenormal)
                        ws.write(row_num, 5, beneficiario.emailinst, fuentenormal)
                        ws.write(row_num, 6, beneficiario.cuentabancaria().banco.codigo, fuentenormal)
                        ws.write(row_num, 7, beneficiario.cuentabancaria().tipocuentabanco.id, fuentenormal)
                        ws.write(row_num, 8, beneficiario.cuentabancaria().numero, fuentenormal)
                        ws.write(row_num, 9, 'C', fuentenormal)
                        ws.write(row_num, 10, 'N', fuentenormal)
                        row_num += 1

                        cuentabeneficiario = beneficiario.cuentabancaria()
                        cuentabeneficiario.archivoesigef = True
                        cuentabeneficiario.save(request)


                    wb.save(response)
                    return response
                except Exception as ex:
                    transaction.set_rollback(True)
                    print("Error...")
                    pass

            elif action == 'beneficiarioscuentasrechazadas':
                try:
                    __author__ = 'Unemi'

                    fuentenormal = easyxtitulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo2 = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentemoneda = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str=' "$" #,##0.00')
                    fuentefecha = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                        num_format_str='yyyy-mm-dd')
                    fuentenumerodecimal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str='#,##0.00')
                    fuentenumeroentero = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Beneficiarios')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=cuentas_rechazadas_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 15, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 15, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', titulo2)
                    ws.write_merge(2, 2, 0, 15, 'LISTADO DE BENEFICIARIOS CON CUENTAS RECHAZADAS', titulo2)

                    row_num = 4
                    columns = [
                        (u"NOMBRES COMPLETOS", 10000),
                        (u"IDENTIFICACIÓN", 5000),
                        (u"PROVINCIA", 5000),
                        (u"CANTÓN", 5000),
                        (u"PARROQUIA", 5000),
                        (u"DIRECCIÓN", 15000),
                        (u"REFERENCIA", 15000),
                        (u"SECTOR", 15000),
                        (u"# CASA", 5000),
                        (u"CORREO PERSONAL", 8000),
                        (u"CORREO UNEMI", 8000),
                        (u"TELÉFONO", 5000),
                        (u"CELULAR", 5000),
                        (u"OPERADORA", 5000),
                        (u"OBSERVACIÓN", 20000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    beneficiarios = Persona.objects.filter(cuentabancariapersona__status=True,
                                                           cuentabancariapersona__archivo__isnull=False,
                                                           inscripcion__becasolicitud__periodo_id__in=[110, 90],
                                                           inscripcion__becasolicitud__becaasignacion__status=True,
                                                           cuentabancariapersona__estadorevision=3).distinct().order_by('apellido1', 'apellido2', 'nombres')

                    for beneficiario in beneficiarios:
                        row_num += 1
                        ws.write(row_num, 0, beneficiario.nombre_completo_inverso(), fuentenormal)
                        ws.write(row_num, 1, beneficiario.identificacion(), fuentenormal)
                        ws.write(row_num, 2, str(beneficiario.provincia) if beneficiario.provincia else '', fuentenormal)
                        ws.write(row_num, 3, str(beneficiario.canton) if beneficiario.canton else '', fuentenormal)
                        ws.write(row_num, 4, str(beneficiario.parroquia) if beneficiario.parroquia else '', fuentenormal)
                        ws.write(row_num, 5, beneficiario.direccion_corta().upper(), fuentenormal)
                        ws.write(row_num, 6, beneficiario.referencia.upper(), fuentenormal)
                        ws.write(row_num, 7, beneficiario.sector.upper(), fuentenormal)
                        ws.write(row_num, 8, beneficiario.num_direccion, fuentenormal)
                        ws.write(row_num, 9, beneficiario.email, fuentenormal)
                        ws.write(row_num, 10, beneficiario.emailinst, fuentenormal)
                        ws.write(row_num, 11, beneficiario.telefono_conv, fuentenormal)
                        ws.write(row_num, 12, beneficiario.telefono, fuentenormal)
                        ws.write(row_num, 13, beneficiario.get_tipocelular_display() if beneficiario.tipocelular else '', fuentenormal)
                        cuentabeneficiario = beneficiario.cuentabancaria()
                        ws.write(row_num, 14, cuentabeneficiario.observacion, fuentenormal)

                    wb.save(response)
                    return response
                except Exception as ex:
                    print("Error...")
                    pass

            elif action == 'beneficiarioscuentasvalidadas':
                try:
                    __author__ = 'Unemi'

                    desde = datetime.combine(convertir_fecha(request.GET['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.GET['hasta']), time.max)

                    fuentenormal = easyxtitulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo2 = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentemoneda = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str=' "$" #,##0.00')
                    fuentefecha = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                        num_format_str='yyyy-mm-dd')
                    fuentenumerodecimal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str='#,##0.00')
                    fuentenumeroentero = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Beneficiarios')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=cuentas_validadas_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 15, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 15, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', titulo2)
                    ws.write_merge(2, 2, 0, 15, 'LISTADO DE BENEFICIARIOS CON CUENTAS VALIDADAS', titulo2)

                    row_num = 4
                    columns = [
                        (u"NOMBRES COMPLETOS", 10000),
                        (u"IDENTIFICACIÓN", 5000),
                        (u"PROVINCIA", 5000),
                        (u"CANTÓN", 5000),
                        (u"PARROQUIA", 5000),
                        (u"DIRECCIÓN", 15000),
                        (u"REFERENCIA", 15000),
                        (u"SECTOR", 15000),
                        (u"# CASA", 5000),
                        (u"CORREO PERSONAL", 8000),
                        (u"CORREO UNEMI", 8000),
                        (u"TELÉFONO", 5000),
                        (u"CELULAR", 5000),
                        (u"OPERADORA", 5000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    beneficiarios = Persona.objects.filter(cuentabancariapersona__status=True,
                                                           cuentabancariapersona__archivo__isnull=False,
                                                           inscripcion__becasolicitud__periodo_id__in=[110, 90],
                                                           inscripcion__becasolicitud__becaasignacion__status=True,
                                                           cuentabancariapersona__estadorevision=2,
                                                           cuentabancariapersona__fechavalida__range=(desde, hasta)).distinct().order_by('apellido1', 'apellido2', 'nombres')

                    for beneficiario in beneficiarios:
                        row_num += 1
                        ws.write(row_num, 0, beneficiario.nombre_completo_inverso(), fuentenormal)
                        ws.write(row_num, 1, beneficiario.identificacion(), fuentenormal)
                        ws.write(row_num, 2, str(beneficiario.provincia) if beneficiario.provincia else '', fuentenormal)
                        ws.write(row_num, 3, str(beneficiario.canton) if beneficiario.canton else '', fuentenormal)
                        ws.write(row_num, 4, str(beneficiario.parroquia) if beneficiario.parroquia else '', fuentenormal)
                        ws.write(row_num, 5, beneficiario.direccion_corta().upper(), fuentenormal)
                        ws.write(row_num, 6, beneficiario.referencia.upper(), fuentenormal)
                        ws.write(row_num, 7, beneficiario.sector.upper(), fuentenormal)
                        ws.write(row_num, 8, beneficiario.num_direccion, fuentenormal)
                        ws.write(row_num, 9, beneficiario.email, fuentenormal)
                        ws.write(row_num, 10, beneficiario.emailinst, fuentenormal)
                        ws.write(row_num, 11, beneficiario.telefono_conv, fuentenormal)
                        ws.write(row_num, 12, beneficiario.telefono, fuentenormal)
                        ws.write(row_num, 13, beneficiario.get_tipocelular_display() if beneficiario.tipocelular else '', fuentenormal)

                    wb.save(response)
                    return response
                except Exception as ex:
                    print("Error...")
                    pass

            elif action == 'beneficiarioscuentaspendientesrevisar':
                try:
                    __author__ = 'Unemi'

                    fuentenormal = easyxtitulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo2 = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentemoneda = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str=' "$" #,##0.00')
                    fuentefecha = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                        num_format_str='yyyy-mm-dd')
                    fuentenumerodecimal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str='#,##0.00')
                    fuentenumeroentero = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Beneficiarios')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=cuentas_pendientes_revisar_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 14, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 14, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', titulo2)
                    ws.write_merge(2, 2, 0, 14, 'LISTADO DE BENEFICIARIOS CON CUENTAS PENDIENTES DE REVISAR', titulo2)

                    row_num = 4
                    columns = [
                        (u"NOMBRES COMPLETOS", 10000),
                        (u"IDENTIFICACIÓN", 5000),
                        (u"PROVINCIA", 5000),
                        (u"CANTÓN", 5000),
                        (u"PARROQUIA", 5000),
                        (u"DIRECCIÓN", 15000),
                        (u"REFERENCIA", 15000),
                        (u"SECTOR", 15000),
                        (u"# CASA", 5000),
                        (u"CORREO PERSONAL", 8000),
                        (u"CORREO UNEMI", 8000),
                        (u"TELÉFONO", 5000),
                        (u"CELULAR", 5000),
                        (u"OPERADORA", 5000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    beneficiarios = Persona.objects.filter(cuentabancariapersona__status=True,
                                                           cuentabancariapersona__archivo__isnull=False,
                                                           inscripcion__becasolicitud__periodo_id__in=[110, 90],
                                                           inscripcion__becasolicitud__becaasignacion__status=True,
                                                           inscripcion__becasolicitud__becaasignacion__tipo=1,
                                                           inscripcion__becasolicitud__becaasignacion__cargadocumento=True,
                                                           cuentabancariapersona__estadorevision=1).distinct().order_by('apellido1', 'apellido2', 'nombres')

                    for beneficiario in beneficiarios:
                        row_num += 1
                        ws.write(row_num, 0, beneficiario.nombre_completo_inverso(), fuentenormal)
                        ws.write(row_num, 1, beneficiario.identificacion(), fuentenormal)
                        ws.write(row_num, 2, str(beneficiario.provincia) if beneficiario.provincia else '', fuentenormal)
                        ws.write(row_num, 3, str(beneficiario.canton) if beneficiario.canton else '', fuentenormal)
                        ws.write(row_num, 4, str(beneficiario.parroquia) if beneficiario.parroquia else '', fuentenormal)
                        ws.write(row_num, 5, beneficiario.direccion_corta().upper(), fuentenormal)
                        ws.write(row_num, 6, beneficiario.referencia.upper(), fuentenormal)
                        ws.write(row_num, 7, beneficiario.sector.upper(), fuentenormal)
                        ws.write(row_num, 8, beneficiario.num_direccion, fuentenormal)
                        ws.write(row_num, 9, beneficiario.email, fuentenormal)
                        ws.write(row_num, 10, beneficiario.emailinst, fuentenormal)
                        ws.write(row_num, 11, beneficiario.telefono_conv, fuentenormal)
                        ws.write(row_num, 12, beneficiario.telefono, fuentenormal)
                        ws.write(row_num, 13, beneficiario.get_tipocelular_display() if beneficiario.tipocelular else '', fuentenormal)
                        # cuentabeneficiario = beneficiario.cuentabancaria()

                    wb.save(response)
                    return response
                except Exception as ex:
                    print("Error...")
                    pass

            elif action == 'addinscritomanual':
                try:
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = ActividadConvalidacionPPV.objects.get(pk=id)
                    form = InscripcionManualActividadExtracurricularForm()
                    form.fields['persona'].queryset = Persona.objects.none()
                    data['form2'] = form
                    template = get_template("adm_convalidacionpractica/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'veractividades':
                try:
                    data['id'] = id = request.GET['id']
                    data['actividad'] = filtro = ActividadConvalidacionPPV.objects.get(pk=id)
                    data['listado_actividades'] = actividades = filtro.detalle_actividades_profesor()
                    template = get_template("adm_convalidacionpractica/modal/listadoactividades.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'buscarinscritos':
                try:
                    id = request.GET['id']
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    carrera = ""
                    actividad = ActividadConvalidacionPPV.objects.get(pk=id)
                    carreraid = actividad.carrera.all().values_list('id', flat=True)
                    querybase = Inscripcion.objects.filter(status=True, activo=True, carrera__in=carreraid).order_by('persona__apellido1')

                    if len(s) == 1:
                        querybase = querybase.filter((Q(persona__nombres__icontains=q) | Q(persona__apellido1__icontains=q) | Q(persona__cedula__icontains=q) |  Q(persona__apellido2__icontains=q) | Q(persona__cedula__contains=q)), Q(status=True, perfilusuario__status=True,
                                                                 perfilusuario__visible=True)).distinct()[:15]
                    elif len(s) == 2:
                        querybase = querybase.filter((Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1])) |
                                                       (Q(persona__nombres__icontains=s[0]) & Q(persona__nombres__icontains=s[1])) |
                                                       (Q(persona__nombres__icontains=s[0]) & Q(persona__apellido1__contains=s[1]))).filter(status=True, perfilusuario__status=True,
                                                                 perfilusuario__visible=True).distinct()[:15]
                    else:
                        querybase = querybase.filter((Q(persona__nombres__contains=s[0]) & Q(persona__apellido1__contains=s[1]) & Q(persona__apellido2__contains=s[2])) |
                                                       (Q(persona__nombres__contains=s[0]) & Q(persona__nombres__contains=s[1]) & Q(persona__apellido1__contains=s[2]))).filter(status=True, perfilusuario__status=True,
                                                                 perfilusuario__visible=True).distinct()[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {} | {} | NIVEL MALLA {}".format(x.persona.cedula, x.persona.nombre_completo(), x.carrera.nombre, x.mi_nivel().nivel.orden)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'requisitos':
                try:
                    data['title'] = u'Requisitos de Actividad Extracurricular'
                    data['id'] = id = request.GET['id']
                    data['fechaactual'] = fechaactual = datetime.now().date()
                    data['actividad'] = filtro = ActividadConvalidacionPPV.objects.get(pk=id)
                    data['requisitos'] = requisitos = RequisitosActividadConvalidacionPPV.objects.filter(status=True, actividad=filtro).order_by('titulo')

                    return render(request, 'adm_convalidacionpractica/viewrequisitos.html', data)
                except Exception as ex:
                    pass

            elif action == 'requisitos_mostrar':
                try:
                    data['title'] = u'Requisitos de Actividad Extracurricular'
                    data['id'] = id = request.GET['id']
                    data['fechaactual'] = fechaactual = datetime.now().date()
                    data['actividad'] = filtro = ActividadConvalidacionPPV.objects.get(pk=id)
                    data['requisitos'] = requisitos = RequisitosActividadConvalidacionPPV.objects.filter(status=True, actividad=filtro).order_by('titulo')

                    return render(request, 'adm_convalidacionpractica/viewrequisitos_mostrar.html', data)
                except Exception as ex:
                    pass

            elif action == 'listarinscritos':
                try:
                    search = None
                    opcion = 0
                    if request.GET['op']:
                        opcion = int(request.GET['op'])

                    data['opcion'] = opcion
                    data['title'] = u'Documentación de Estudiantes Inscritos en Actividad Extracurricular'
                    data['id'] = id = request.GET['id']
                    data['actividad'] = actividad = ActividadConvalidacionPPV.objects.get(pk=id)

                    if 's' in request.GET:
                        search = request.GET['s']
                        s = search.split(" ")
                        if len(s) == 2:
                            data['inscritos'] = actividad.inscripcionactividadconvalidacionppv_set.filter(
                                Q(inscripcion__persona__apellido1__icontains=s[0]) |
                                Q(inscripcion__persona__apellido2__icontains=s[1])).distinct().order_by(
                                'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                                'inscripcion__persona__nombres')
                        else:
                            data['inscritos'] = actividad.inscripcionactividadconvalidacionppv_set.filter(
                                Q(inscripcion__persona__apellido1__icontains=search) |
                                Q(inscripcion__persona__apellido2__icontains=search)).distinct().order_by(
                                'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                                'inscripcion__persona__nombres')
                    else:
                        data['inscritos'] = actividad.inscripcionactividadconvalidacionppv_set.filter(
                            ~Q(estado__in=[1, 3, 5]), status=True).order_by(
                            'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                            'inscripcion__persona__nombres')

                    data['search'] = search if search else ""
                    return render(request, 'adm_convalidacionpractica/viewinscritos.html', data)
                except Exception as ex:
                    pass

            elif action == 'cargararchivosinscritos':
                try:
                    opcion = 0
                    opcion = int(request.GET['op'])
                    data['opcion'] = opcion
                    data['title'] = u'Archivos de Actividad Extracurricular'
                    data['id'] = id = int(request.GET['id'])
                    data['filtro'] = filtro = InscripcionActividadConvalidacionPPV.objects.get(pk=id)
                    for req in filtro.actividad.requisitosactividad():
                        if not InscripcionRequisitosActividadConvalidacionPPV.objects.filter(status=True, actividad=filtro, requisito=req).exists():
                            requisito = InscripcionRequisitosActividadConvalidacionPPV(actividad=filtro, requisito=req)
                            requisito.save(request)
                    excluidos = InscripcionRequisitosActividadConvalidacionPPV.objects.filter(status=True, actividad=filtro).exclude(requisito__in=filtro.actividad.requisitosactividad().values_list('id',flat=True))
                    for e in excluidos:
                        e.status = False
                        e.save(request)
                    template = get_template("adm_convalidacionpractica/archivosinscritos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                    # return render(request, 'adm_convalidacionpractica/archivosinscritos.html', data)
                except Exception as ex:
                    pass

            elif action == 'addrequisito':
                try:
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = ActividadConvalidacionPPV.objects.get(pk=id)
                    data['form2'] = RequisitoActividadConvalidacionForm()
                    template = get_template("adm_convalidacionpractica/modal/formrequisito.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addrecomendacion':
                try:
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = ActividadConvalidacionPPV.objects.get(pk=id)
                    data['form2'] = RecomendacionActividadPPVForm()
                    template = get_template("adm_convalidacionpractica/modal/formmodal2.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'informeactividadpdf':
                try:
                    data['fechafin'] = fecfin = convertir_fecha_invertida(request.GET['fecfin'])
                    fecha = request.GET['fecfin']

                    an2 =fecfin.year

                    data['id'] = id = request.GET['id_actv']
                    data['actividad'] = actividad = ActividadConvalidacionPPV.objects.get(pk=int(request.GET['id_actv']))

                    data['director_ac'] = dire = actividad.director

                    cargoactual_act = dire.mi_cargo_actual()


                    data['cargoactual_act'] = cargoactual_act

                    data['inscritos'] = actividad.alumnos_inscritos()
                    data['horaactual'] = datetime.now().time()

                    data['careras_Actividad'] =  ca = actividad.carrera.all()

                    data['numero_carrera'] =  ca.count()

                    data['detalle'] = actividad.detalle_actividades_profesor()

                    nombresinciales = ''
                    nombre = persona.nombres.split()
                    if len(nombre) > 1:
                        nombresiniciales = '{}{}'.format(nombre[0][0], nombre[1][0])
                    else:
                        nombresiniciales = '{}'.format(nombre[0][0])
                    inicialespersona = '{}{}{}'.format(nombresiniciales, persona.apellido1[0], persona.apellido2[0])

                    data['recomendaciones'] = RecomendacionesActividadConvalidacionPPV.objects.filter(actividad_id=int(request.GET['id_actv']), status= True)

                    cant_Actv = ActividadConvalidacionPPV.objects.filter( periodo = periodo, status = True, profesor__persona= persona ).count()

                    data['numinforme'] = '{}-ACTEX-{}-{}'.format(cant_Actv, inicialespersona,an2)

                    # qrname='Informe_ActividadExtra_{}'.format(random.randint(1, 100000).__str__())


                    directory = os.path.join(SITE_STORAGE, 'media', 'convalidacionppv', 'informesactv')
                    try:
                        os.stat(directory)
                    except:
                        os.mkdir(directory)
                    qrname = 'Informe_ActividadExtra_{}_{}_{}_{}'.format(fecfin.month, fecfin.year, persona.pk, random.randint(1, 100000).__str__())

                    rutaimg = '{}/{}.png'.format(directory, qrname)

                    if os.path.isfile(rutaimg):
                        os.remove(rutaimg)
                    url = pyqrcode.create('DOCENTE: {}\nCARGO: {}'.format(persona.__str__(), persona.mis_cargos()[0]))

                    imageqr = url.png('{}/{}.png'.format(directory, qrname), 16, '#000000')

                    data['qrname'] = qrname

                    valida = conviert_html_to_pdfsaveqrinformepractividadextra(
                        'adm_convalidacionpractica/informe/informeactividad.html',
                        {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                    )

                    actividad.archivoinforme =  'convalidacionppv/informesactv/' + qrname + '.pdf'

                    actividad.save(request)

                    return redirect('https://sga.unemi.edu.ec/media/{}'.format(actividad.archivoinforme))
                except Exception as ex:
                    pass


            elif action == 'editrequisito':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = RequisitosActividadConvalidacionPPV.objects.get(pk=request.GET['id'])
                    data['form2'] = RequisitoActividadConvalidacionForm(initial=model_to_dict(filtro))
                    template = get_template("adm_convalidacionpractica/modal/formrequisito.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'dupliactividad':
                try:
                    data['action']=action
                    data['actividad']= actividad = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("adm_convalidacionpractica/modal/detalleduplicar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)
        else:
            data['esdirectorcarr'] = es_director_carr
            data['esdocente'] = es_docente
            data['esdirectorvinc'] = es_director_vincu
            #data['esanalistavinc'] = es_analista_vincu

            search = None
            ids = None

            #periodo_filtro = request.GET['periodo_filtro_id']

            if es_director_vincu or request.user.is_superuser:
                actividades = ActividadConvalidacionPPV.objects.filter(status=True).order_by('-id').distinct()
                lista_periodos = ActividadConvalidacionPPV.objects.filter(status=True).values_list(
                    'periodo', flat=True).distinct()
                # print(lista_periodos)

                # periodos = Periodo.objects.filter(periodo_id__in=lista_periodos)

            elif es_director_carr:
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        actividades = ActividadConvalidacionPPV.objects.filter(Q(titulo__icontains=search) | Q(profesor__persona__apellido1__icontains=search) | Q(profesor__persona__apellido2__icontains=search),Q(director=persona) | Q(carrera__in =miscarreras), status=True).order_by('-id').distinct()
                        lista_periodos = ActividadConvalidacionPPV.objects.filter(Q(director=persona) | Q(carrera__in =miscarreras),status=True).values_list(
                            'periodo', flat=True).distinct()
                    else:
                        actividades = ActividadConvalidacionPPV.objects.filter(Q(profesor__persona__apellido1__icontains=ss[0]) & Q(profesor__persona__apellido2__icontains=ss[1]),Q(director=persona) | Q(carrera__in =miscarreras), status=True).order_by('-id').distinct()
                        lista_periodos = ActividadConvalidacionPPV.objects.filter(Q(director=persona) | Q(carrera__in =miscarreras),status=True).values_list(
                            'periodo', flat=True).distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    actividades = ActividadConvalidacionPPV.objects.filter(id=ids, status=True).order_by('-id').distinct()
                    lista_periodos = ActividadConvalidacionPPV.objects.filter(id=ids, status=True).values_list(
                        'periodo', flat=True).distinct()
                else:
                    actividades = ActividadConvalidacionPPV.objects.filter(Q(director=persona) | Q(carrera__in =miscarreras),status=True).order_by('-id').distinct()
                    lista_periodos = ActividadConvalidacionPPV.objects.filter(Q(director=persona) | Q(carrera__in =miscarreras),status=True).values_list(
                        'periodo', flat=True).distinct()
                    # print(lista_periodos)

            elif es_docente:
                listo = True
                actividades = ActividadConvalidacionPPV.objects.filter(status=True, profesor__persona=persona).order_by('-id').distinct()
                lista_periodos = ActividadConvalidacionPPV.objects.filter(status=True, profesor__persona=persona).values_list('periodo', flat=True).distinct()
            else:
                actividades = ActividadConvalidacionPPV.objects.filter(status=True).order_by('-id').distinct()
                lista_periodos = ActividadConvalidacionPPV.objects.filter(status=True, profesor__persona=persona).values_list('periodo', flat=True).distinct()

            actividad_distinct = Periodo.objects.filter(pk__in=lista_periodos)

            tipoactividad = 0
            periodo = 0
            if 'tipoactividad' in request.GET:
                tipoactividad = int(request.GET['tipoactividad'])
                if tipoactividad > 0:
                    actividades = actividades.filter(tipoactividad=tipoactividad)


            if 'periodo' in request.GET:
                periodo = int(request.GET['periodo'])
                if periodo > 0:
                    actividades = actividades.filter(periodo_id=int(periodo))

            paging = MiPaginador(actividades, 25)
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
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['actividades'] = page.object_list
            data['pendientes']=len(actividades.filter(estado=0))
            data['listo'] = listo
            data['actividades_periodos'] = actividad_distinct
            # data['actividades'] =
            #
            # data['totalsolicitudes'] = total = solicitudes.count()
            # data['totalaprobadas'] = aprobadas = solicitudes.filter(estado=2).count()
            # data['totalrechazadas'] = rechazadas = solicitudes.filter(estado=3).count()
            # data['totalrevision'] = revision = solicitudes.filter(estado=5).count()
            # data['totalpendiente'] = total - (aprobadas + rechazadas + revision)
            data['tipoactividad'] = tipoactividad
            data['periodoid'] = periodo
            #
            #
            # data['fechaactual'] = datetime.now().strftime('%d-%m-%Y')

            if es_director_carr:
                data['title'] = u'Listado de actividades extracurriculares de convalidación'
                return render(request, "adm_convalidacionpractica/view.html", data)
            elif es_director_vincu:
                data['title'] = u'Mis actividades extracurriculares'
                return render(request, "adm_convalidacionpractica/voluntariado.html", data)
            elif es_docente:
                data['title'] = u'Mis actividades extracurriculares de convalidación asignadas'
                return render(request, "adm_convalidacionpractica/profesoractividad.html", data)
            else:
                data['title'] = u'Convalidación de prácticas preprofesionales y proyectos de servicio comunitario'
                return render(request, "adm_convalidacionpractica/convalidacionpractica.html", data)
