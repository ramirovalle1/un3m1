# -*- coding: UTF-8 -*-
import os
import random
import json
import io
import fitz
from urllib.parse import urljoin
from dateutil.rrule import MONTHLY, rrule
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.db.models import Q, Max, Count, PROTECT, Sum, Avg, Min, F, ExpressionWrapper, TimeField, DateTimeField
from inno.models import BitacoraActividadEstudiantePpp, PracticasPreprofesionalesInscripcion, DetalleBitacoraEstudiantePpp, HistorialBitacoraActividadEstudiante, \
    ESTADO_REVISION, PersonaDatosFamiliaresExtensionSalud, HistorialDocumentosPPPSalud, PersonaDetalleMaternidadExtensionSalud, PerfilInscripcionExtensionSalud, PersonaEnfermedadExtensionSalud, \
    PersonaDetalleMaternidadExtensionSalud, PersonaDatosFamiliaresExtensionSalud, EnfermedadFamiliarSalud, ItinerarioAsignaturaSalud, RequisitoPracticappSalud
from inno.forms import validarDocumentoPPPForm, ItinerarioAsignaturaSaludForm
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, generar_nombre, log, notificacion, remover_caracteres_tildes_unicode, remover_caracteres_especiales_unicode, variable_valor, get_director_vinculacion, calcula_edad_fn_fc, fechaformatostr
from sga.models import ProfesorDistributivoHoras, AnexoEvidenciaActividad, EvidenciaActividadAudi, EvidenciaActividadDetalleDistributivo, HistorialAprobacionEvidenciaActividad, CUENTAS_CORREOS, miinstitucion, EvidenciaActividadAudi, CriterioDocenciaPeriodo, Persona, CriterioInvestigacionPeriodo, CriterioGestionPeriodo, DetalleDistributivo, Profesor, ClaseActividad, MESES_CHOICES, ItinerariosMalla, Inscripcion, \
    PersonaDatosFamiliares, PreInscripcionPracticasPP, PersonaDetalleMaternidad, PerfilInscripcion, PersonaEnfermedad, AsignaturaMalla, Malla, Carrera
import datetime
import calendar
from datetime import *
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt, nombremes
from settings import DEBUG, SITE_STORAGE
import xlwt
from xlwt import *
from core.firmar_documentos import firmar, obtener_posicion_x_y_saltolinea, verificarFirmasPDF
from django.contrib import messages
from django.core.files import File as DjangoFile
from sga.pro_cronograma import migrar_evidencia_integrante_grupo_investigacion
from sga.proyectovinculaciondocente import migrar_evidencia_proyecto_vinculacion
from core.firmar_documentos_ec import JavaFirmaEc
from django.core.files.base import ContentFile

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    # es_administrativo = perfilprincipal.es_administrativo()
    # if not perfilprincipal.es_profesor():
    #     return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    data['profesor'] = profesor = perfilprincipal.profesor
    periodo = request.session['periodo']
    # es_administrador = persona.usuario.groups.values("id").filter(id=442).exists()
    hoy = datetime.now().date()
    hoytime = datetime.now()
    dominio_sistema = 'https://sga.unemi.edu.ec'
    if DEBUG:
        dominio_sistema = 'http://localhost:8000'
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema

    # if not es_administrativo:
    #     return HttpResponseRedirect("/?info=El Módulo está disponible para administrativos.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'revisionbitacora':
            try:
                _success = json.loads(request.POST['aprobados'])
                _decline = json.loads(request.POST['rechazados'])

                bitacora = BitacoraActividadEstudiantePpp.objects.get(pk=request.POST['id'])
                DetalleBitacoraEstudiantePpp.objects.filter(pk__in=_success, bitacorapractica=bitacora).update(estadoaprobacion=2, usuario_modificacion=persona.usuario, fecha_modificacion=datetime.now())

                _values = [(x.split(';')[0], x[x.find(';') + 1:]) for x in _decline]
                for v in _values:
                    DetalleBitacoraEstudiantePpp.objects.filter(pk=v[0], bitacorapractica=bitacora).update(estadoaprobacion=3, observacion=v[1], usuario_modificacion=persona.usuario, fecha_modificacion=datetime.now())

                bitacora.estadorevision = 3
                bitacora.save(request)

                h = HistorialBitacoraActividadEstudiante(bitacora=bitacora, persona=persona, estadorevision=bitacora.estadorevision)
                h.save(request)

                log(u'Aprobo/rechazo detalle de bitacora', request, 'add')
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': f'{ex=}'})

        elif action == 'validardatos':
            try:
                preinscripcion = int(request.POST['idins'])
                tab = int(request.POST['tab'])
                estudiante = Inscripcion.objects.get(pk=request.POST['id'])
                f = validarDocumentoPPPForm(request.POST)
                tipodocumento, documento = int(request.POST.get('tipo', 0)), ''
                if f.is_valid() and tab != 0 and tipodocumento != 0:
                    if tab == 1:
                        documento = 'Discapacidad'
                        personadiscapacidad = PerfilInscripcionExtensionSalud.objects.get(status=True, pk=request.POST['ids'])
                        personadiscapacidad.fecha = hoy
                        personadiscapacidad.estadoaprobacion = f.cleaned_data['estado']
                        personadiscapacidad.observacion = f.cleaned_data['observacion']
                        personadiscapacidad.save(request)
                        h = HistorialDocumentosPPPSalud(personaperfilext=personadiscapacidad, tipo=tipodocumento, fecha=hoytime, estadoaprobacion=f.cleaned_data['estado'], persona=persona, observacion=f.cleaned_data['observacion'])
                        h.save(request)
                        h.genera_notificacion_administrativo(estudiante.persona, encrypt(estudiante.id), tab)
                    elif tab == 2:
                        documento = 'Enfermedad'
                        personaenfermedad = PersonaEnfermedadExtensionSalud.objects.get(status=True, pk=request.POST['ids'])
                        personaenfermedad.fecha = hoy
                        personaenfermedad.estadoaprobacion = f.cleaned_data['estado']
                        personaenfermedad.observacion = f.cleaned_data['observacion']
                        personaenfermedad.save(request)
                        h = HistorialDocumentosPPPSalud(personaenfermedadext=personaenfermedad, tipo=tipodocumento, fecha=hoytime, estadoaprobacion=f.cleaned_data['estado'], persona=persona, observacion=f.cleaned_data['observacion'])
                        h.save(request)
                        h.genera_notificacion_administrativo(estudiante.persona, encrypt(estudiante.id), tab)
                    elif tab == 3:
                        if tipodocumento == 31:  # Discapacidad
                            documento = 'Familiar discapacidad'
                            familiardiscapacidad = PersonaDatosFamiliaresExtensionSalud.objects.get(status=True, pk=request.POST['ids'])
                            familiardiscapacidad.fechadiscapacidad = hoy
                            familiardiscapacidad.estadoaprobaciondiscapacidad = f.cleaned_data['estado']
                            familiardiscapacidad.observaciondiscapacidad = f.cleaned_data['observacion']
                            familiardiscapacidad.save(request)
                            h = HistorialDocumentosPPPSalud(personafamiliarext=familiardiscapacidad, tipo=tipodocumento, fecha=hoytime, estadoaprobacion=f.cleaned_data['estado'], persona=persona, observacion=f.cleaned_data['observacion'])
                            h.save(request)
                            h.genera_notificacion_administrativo(estudiante.persona, encrypt(estudiante.id), tab)
                        if tipodocumento == 32:  # Enfermedad
                            documento = 'Familiar enfermedad'
                            familiarenfermedad = EnfermedadFamiliarSalud.objects.get(status=True, pk=request.POST['ids'])
                            familiarenfermedad.fecha = hoy
                            familiarenfermedad.estadoaprobacion = f.cleaned_data['estado']
                            familiarenfermedad.observacion = f.cleaned_data['observacion']
                            familiarenfermedad.save(request)
                            h = HistorialDocumentosPPPSalud(personafamiliarext=familiarenfermedad.personafamiliarext, enfermedadfamiliar=familiarenfermedad, tipo=tipodocumento, fecha=hoytime, estadoaprobacion=f.cleaned_data['estado'], persona=persona, observacion=f.cleaned_data['observacion'])
                            h.save(request)
                            h.genera_notificacion_administrativo(estudiante.persona, encrypt(estudiante.id), tab)
                    elif tab == 4:
                        documento = 'Embarazo'
                        personaembarazo = PersonaDetalleMaternidadExtensionSalud.objects.get(status=True, pk=request.POST['ids'])
                        personaembarazo.fecha = hoy
                        personaembarazo.estadoaprobacion = f.cleaned_data['estado']
                        personaembarazo.observacion = f.cleaned_data['observacion']
                        personaembarazo.save(request)
                        h = HistorialDocumentosPPPSalud(personamaternidadext=personaembarazo, tipo=tipodocumento, fecha=hoytime, estadoaprobacion=f.cleaned_data['estado'], persona=persona, observacion=f.cleaned_data['observacion'])
                        h.save(request)
                        h.genera_notificacion_administrativo(estudiante.persona, encrypt(estudiante.id), tab)
                    elif tab == 5:
                        documento = 'Niño menor a 5 años'
                        ninio = PersonaDatosFamiliaresExtensionSalud.objects.get(status=True, pk=request.POST['ids'])
                        ninio.fechaninio = hoy
                        ninio.estadoaprobacionninio = f.cleaned_data['estado']
                        ninio.observacionninio = f.cleaned_data['observacion']
                        ninio.save(request)
                        h = HistorialDocumentosPPPSalud(personafamiliarext=ninio, tipo=tipodocumento, fecha=hoytime, estadoaprobacion=f.cleaned_data['estado'], persona=persona, observacion=f.cleaned_data['observacion'])
                        h.save(request)
                        h.genera_notificacion_administrativo(estudiante.persona, encrypt(estudiante.id), tab)
                    elif tab == 6:
                        documento = 'Requisitos'
                        requisito = RequisitoPracticappSalud.objects.get(status=True, pk=request.POST['ids'])
                        requisito.fecha = hoy
                        requisito.estadoaprobacion = f.cleaned_data['estado']
                        requisito.observacion = f.cleaned_data['observacion']
                        requisito.save(request)
                        h = HistorialDocumentosPPPSalud(personarequisito=requisito, tipo=tipodocumento, fecha=hoytime, estadoaprobacion=f.cleaned_data['estado'], persona=persona, observacion=f.cleaned_data['observacion'])
                        h.save(request)
                        h.genera_notificacion_administrativo(estudiante.persona, encrypt(estudiante.id), tab)
                    log(f'Aprobo/rechazo documento verificación de {documento}', request, 'add')
                    return JsonResponse({"result": False, 'to': "{}?action=validardocumentossalud&id={}&tab={}".format(request.path, encrypt(preinscripcion), tab)}, safe=False)
                else:
                    raise NameError('Problemas al validar los datos. Intente nuevamente más tarde.')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'addasignaturaiti':
            try:
                with transaction.atomic():
                    f = ItinerarioAsignaturaSaludForm(request.POST)
                    f.iniciar(request.POST['itinerariomalla'], request.POST['asignaturamalla'])
                    if f.is_valid():
                        registro = ItinerarioAsignaturaSalud(itinerariomalla=f.cleaned_data['itinerariomalla'],
                                                            asignaturamalla=f.cleaned_data['asignaturamalla'])
                        registro.save(request)
                        log(u'Adicionó itinerario asignatura Salud: %s' % (registro), request, "add")
                        messages.success(request, 'Registro guardado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'editasignaturaiti':
            try:
                registro = ItinerarioAsignaturaSalud.objects.get(pk=int(encrypt(request.POST['id'])))
                f = ItinerarioAsignaturaSaludForm(request.POST)
                f.iniciar(request.POST['itinerariomalla'], request.POST['asignaturamalla'])
                if f.is_valid():
                    registro.itinerariomalla = f.cleaned_data['itinerariomalla']
                    registro.asignaturamalla = f.cleaned_data['asignaturamalla']
                    registro.save(request)
                    log(u'Editó itinerario asignatura Salud: %s' % (registro), request, "edit")
                    messages.success(request, 'Registro editado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'deleteformato':
            try:
                registro = ItinerarioAsignaturaSalud.objects.get(id=request.POST['id'])
                if registro:
                    registro.status = False
                    registro.save(request)
                    log(u'Eliminó itinerario asignatura Salud: %s' % (registro), request, "del")
                else:
                    raise NameError('error')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'validardocumentossalud':
                try:
                    # if not persona.usuario.has_perm('inno.puede_evaluar_videos_clases_virtuales'):
                    #     raise NameError(
                    #         f'Estimad{"a" if persona.es_mujer() else "o"} {persona.nombre_completo().split()[0].title()}, no tiene permisos para visualizar esta pantalla.')
                    search, url_vars, numerofilas, tab = request.GET.get('s', ''), '', 15, request.GET.get('tab', '')
                    filters = Q(status=True)
                    data['tab'] = tab
                    data['title'] = u'Revisión de documentos'
                    data['preinscripcion'] = preinscripcion = PreInscripcionPracticasPP.objects.get(status=True, pk=int(encrypt(request.GET['id'])))
                    preinscripciones = preinscripcion.detallepreinscripcionpracticaspp_set.filter(status=True, estado=1).order_by(
                        'inscripcion__persona__nombres', 'inscripcion__persona__apellido1')
                    data['listado'] = preinscripciones
                    return render(request, 'pro_revisionactividad_evidencia/viewdocumentossalud.html', data)
                except Exception as ex:
                    return HttpResponseRedirect(request.path + f'?info={ex=}')

            elif action == 'detalleresultados':
                try:
                    data['title'] = request.GET.get('title', 'Listado de resultados')
                    data['subtitle'] = request.GET.get('subtitle', 'Estudiantes inscritos en prácticas pre profesionales')
                    data['hoy'] = hoy = datetime.now().date()
                    data['identificador'] = identificador = int(request.GET.get('identificador', 0))
                    data['idins'] = idins = int(request.GET.get('idins', 0))
                    listado = []
                    listadoaux = []
                    resultados = []
                    bandera, idextra, fecha, estado, documento = 0, 0, '', 'PENDIENTE', ''
                    # filters = Q(status=True, estado=1)
                    filters = Q(status=True)
                    preinscripcion = PreInscripcionPracticasPP.objects.get(status=True, pk=idins)
                    exten_preinscripcion = preinscripcion.extpreinscripcionpracticaspp_set.filter(status=True).first()
                    preinscripciones = preinscripcion.detallepreinscripcionpracticaspp_set.filter(filters).order_by('inscripcion__persona__nombres', 'inscripcion__persona__apellido1').distinct('inscripcion__persona__nombres', 'inscripcion__persona__apellido1')
                    listado_estudiantes = preinscripciones.values_list('inscripcion__persona__id')

                    if preinscripciones:
                        if identificador > 0 and identificador == 1: #Discapacidad del estudiante > 30%
                            discapacidad_estudiante = PerfilInscripcionExtensionSalud.objects.filter(status=True, perfilinscripcion__persona_id__in=listado_estudiantes)
                            for d in discapacidad_estudiante.filter(perfilinscripcion__porcientodiscapacidad__gt=30):
                                listadoaux.append(d)
                                inscripcion = preinscripciones.filter(inscripcion__persona=d.perfilinscripcion.persona).first().inscripcion
                                resultados.append([inscripcion, listadoaux])
                                listadoaux, bandera = [], 0

                        elif identificador > 0 and identificador == 2: #Enfermedades catastróficas del estudiante
                            # enfermedad_estudiante = PersonaEnfermedadExtensionSalud.objects.filter(status=True, personaenfermedad__persona_id__in=listado_estudiantes, personaenfermedad__enfermedad__tipo_id__in=[5, 6])#Enfermedades Catastróficas y graves
                            enfermedad_estudiante = PersonaEnfermedadExtensionSalud.objects.filter(status=True, personaenfermedad__persona_id__in=listado_estudiantes)
                            for p in Persona.objects.filter(pk__in=enfermedad_estudiante.values_list('personaenfermedad__persona_id', flat=True)):
                                inscripcion = preinscripciones.filter(inscripcion__persona=p).first().inscripcion
                                for enfer in enfermedad_estudiante.filter(personaenfermedad__persona=p):
                                    listadoaux.append(enfer)
                                resultados.append([inscripcion, listadoaux])
                                listadoaux, bandera = [], 0

                        elif identificador > 0 and identificador == 3: #Familiar u Otro - Discapacidad/Enfermedad -- Familiar hasta el primer grado de consanguinidad y primero de afinidad (Reglamento)
                            discapacidad_familiar = PersonaDatosFamiliaresExtensionSalud.objects.filter(status=True, personafamiliar__essustituto=True, personafamiliar__fallecido=False,
                                                                                                        personafamiliar__persona_id__in=listado_estudiantes, personafamiliar__parentesco_id__in=[1, 2, 3, 11, 13, 14],
                                                                                                        personafamiliar__porcientodiscapacidad__gt=30) #Dsicapacidad mayor al 30%
                            enfermedades = EnfermedadFamiliarSalud.objects.filter(status=True, personafamiliarext__personafamiliar__essustituto=True, personafamiliarext__personafamiliar__fallecido=False,
                                                                                  personafamiliarext__personafamiliar__persona_id__in=listado_estudiantes, personafamiliarext__personafamiliar__parentesco_id__in=[1, 2, 3, 11, 13, 14])
                                                                                  # enfermedad__tipo_id__in=[5, 6]) #Enfermedades Catastróficas y graves
                            enfermedad_familiar = PersonaDatosFamiliaresExtensionSalud.objects.filter(pk__in=enfermedades.values_list('personafamiliarext_id', flat=True))
                            resultados_familiar = (discapacidad_familiar | enfermedad_familiar)
                            for p in Persona.objects.filter(pk__in=resultados_familiar.values_list('personafamiliar__persona_id', flat=True)):
                                inscripcion = preinscripciones.filter(inscripcion__persona=p).first().inscripcion
                                for resp in discapacidad_familiar.filter(personafamiliar__persona=p):
                                    listado.append(resp)
                                for resp in enfermedades.filter(personafamiliarext__personafamiliar__persona=p):
                                    listadoaux.append(resp)
                                resultados.append([inscripcion, listado, listadoaux])
                                listadoaux, listado, bandera = [], [], 0

                        elif identificador > 0 and identificador == 4: #embarazo de la estudiante
                            embarazo_estudiante = PersonaDetalleMaternidadExtensionSalud.objects.filter(status=True, personamaternidad__persona_id__in=listado_estudiantes, personamaternidad__status_gestacion=True)
                            for p in Persona.objects.filter(pk__in=embarazo_estudiante.values_list('personamaternidad__persona_id', flat=True)):
                                inscripcion = preinscripciones.filter(inscripcion__persona=p).first().inscripcion
                                for emba in embarazo_estudiante.filter(personamaternidad__persona=p):
                                    listadoaux.append(emba)
                                resultados.append([inscripcion, listadoaux])
                                listadoaux, bandera = [], 0

                        elif identificador > 0 and identificador == 5: # niños > 5 años
                            fechaninio = exten_preinscripcion.finicioconvocatoria.date() if exten_preinscripcion and exten_preinscripcion.finicioconvocatoria else hoy
                            fechalimite = fechaninio - timedelta(days=365 * 6)
                            ninio_familiar = PersonaDatosFamiliaresExtensionSalud.objects.filter(status=True, personafamiliar__fallecido=False, personafamiliar__persona_id__in=listado_estudiantes, personafamiliar__nacimiento__gte=fechalimite)
                            for p in Persona.objects.filter(pk__in=ninio_familiar.values_list('personafamiliar__persona_id', flat=True)):
                                inscripcion = preinscripciones.filter(inscripcion__persona=p).first().inscripcion
                                for resp in ninio_familiar.filter(personafamiliar__persona=p):
                                    if resp.validar_edad_ninio(fechaninio):
                                        listadoaux.append(resp)
                                if listadoaux:
                                    resultados.append([inscripcion, listadoaux])
                                listadoaux, bandera = [], 0

                        if identificador > 0 and identificador == 6: #Requisitos de practicas del estudiante
                            requisitos_estudiante = RequisitoPracticappSalud.objects.filter(status=True, persona_id__in=listado_estudiantes)
                            for r in requisitos_estudiante:
                                listadoaux.append(r)
                                inscripcion = preinscripciones.filter(inscripcion__persona=r.persona).first().inscripcion
                                resultados.append([inscripcion, listadoaux])
                                listadoaux, bandera = [], 0

                    data['listado'] = resultados
                    template = get_template('pro_revisionactividad_evidencia/detalleresultados.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': 'Problemas al obtener los datos, intente más tarde por favor.'})

            elif action == 'validardatos':
                try:
                    data['estudiante'] = estudiante = Inscripcion.objects.get(pk=request.GET['id'])
                    data['idins'] = request.GET['idins']
                    data['tab'] = tab = int(request.GET.get('identificador', 0))
                    data['tipo'] = tipo = int(request.GET['tipo']) if 'tipo' in request.GET and request.GET['tipo'] != '' else 0
                    data['idextra'] = idextra = int(request.GET['idextra']) if 'idextra' in request.GET and request.GET['idextra'] != '' else 0
                    data['ids'] = ids = request.GET['ids']
                    fecha, estado, documento, documentoextra, idestado, observacion = '', '', '', '', 0, ''

                    if tab > 0 and tab == 1: #Discapacidad Estudiante
                        resultado = PerfilInscripcionExtensionSalud.objects.get(pk=ids)
                        estado, documento = resultado.get_estadoaprobacion_display(), resultado.archivodiscapacidad.url if resultado.archivodiscapacidad else ''
                        idestado, observacion = resultado.estadoaprobacion, resultado.observacion

                    elif tab > 0 and tab == 2: #Enfermedad Estudiante
                        resultado = PersonaEnfermedadExtensionSalud.objects.get(pk=ids)
                        estado, documento = resultado.get_estadoaprobacion_display(), resultado.archivoenfermedad.url if resultado.archivoenfermedad else ''
                        idestado, observacion = resultado.estadoaprobacion, resultado.observacion

                    elif tab > 0 and tab == 3: #Familiar u otro
                        if tipo == 31: #Discapacidad
                            resultado = PersonaDatosFamiliaresExtensionSalud.objects.get(pk=ids)
                            documentoextra = resultado.personafamiliar.archivoautorizado.url if resultado.personafamiliar.archivoautorizado else ''
                            estado, documento = resultado.get_estadoaprobaciondiscapacidad_display(), resultado.personafamiliar.ceduladiscapacidad.url if resultado.personafamiliar.ceduladiscapacidad else ''
                            idestado, observacion = resultado.estadoaprobaciondiscapacidad, resultado.observaciondiscapacidad
                        if tipo == 32: #Enfermedad
                            resultado = EnfermedadFamiliarSalud.objects.get(pk=ids)
                            documentoextra = resultado.personafamiliarext.personafamiliar.archivoautorizado.url if resultado.personafamiliarext.personafamiliar.archivoautorizado else ''
                            estado, documento = resultado.get_estadoaprobacion_display(), resultado.archivoenfermedad.url if resultado.archivoenfermedad else ''
                            idestado, observacion = resultado.estadoaprobacion, resultado.observacion

                    elif tab > 0 and tab == 4: #Embarazo Estudiante
                        resultado = PersonaDetalleMaternidadExtensionSalud.objects.get(pk=ids)
                        estado, documento = resultado.get_estadoaprobacion_display(), resultado.archivoembarazo.url if resultado.archivoembarazo else ''
                        idestado, observacion = resultado.estadoaprobacion, resultado.observacion

                    elif tab > 0 and tab == 5:#Niños menores 5 años
                        resultado = PersonaDatosFamiliaresExtensionSalud.objects.get(pk=ids)
                        documentoextra = resultado.personafamiliar.archivocustodia.url if resultado.personafamiliar.archivocustodia else ''
                        estado, documento = resultado.get_estadoaprobacionninio_display(), resultado.personafamiliar.cedulaidentidad.url if resultado.personafamiliar.cedulaidentidad else ''
                        idestado, observacion = resultado.estadoaprobacionninio, resultado.observacionninio

                    if tab > 0 and tab == 6: #Requisitos prácticas Estudiante
                        resultado = RequisitoPracticappSalud.objects.get(pk=ids)
                        estado, documento = resultado.get_estadoaprobacion_display(), resultado.archivo.url if resultado.archivo else ''
                        idestado, observacion = resultado.estadoaprobacion, resultado.observacion

                    form = validarDocumentoPPPForm(initial={'estado': idestado, 'observacion': observacion})
                    # if idestado == 2: #APROBADO
                    #     form.bloqueo()
                    # else:
                    #     form = validarDocumentoPPPForm()
                    data['fecha'] = fecha
                    data['estado'] = estado
                    data['idestado'] = idestado
                    data['documentoextra'] = documentoextra
                    data['documento'] = documento
                    data['resultado'] = resultado
                    data['form'] = form
                    template = get_template('pro_revisionactividad_evidencia/modal/formvalidar.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': u"Error de conexión. %s" % ex.__str__()})

            elif action == 'historialaprobacion':
                try:
                    if 'id' in request.GET:
                        data['id'] = id = request.GET['id']
                        data['tab'] = tab = int(request.GET.get('identificador', 0))
                        data['tipo'] = tipo = int(request.GET.get('tipo', 0))
                        historial, resultado = [], None
                        if tab > 0 and tab == 1: #Discapacidad estudiante
                            resultado = PerfilInscripcionExtensionSalud.objects.get(pk=id)
                            historial = HistorialDocumentosPPPSalud.objects.filter(personaperfilext=resultado).order_by('-id')

                        if tab > 0 and tab == 2: #Enfermedad estudiante
                            resultado = PersonaEnfermedadExtensionSalud.objects.get(pk=id)
                            historial = HistorialDocumentosPPPSalud.objects.filter(personaenfermedadext=resultado).order_by('-id')

                        if tab > 0 and tab == 3:
                            if tipo == 31: #Discapacidad familiar
                                resultado = PersonaDatosFamiliaresExtensionSalud.objects.get(pk=id)
                                historial = HistorialDocumentosPPPSalud.objects.filter(personafamiliarext=resultado, tipo=31).order_by('-id')
                            if tipo == 32:  #Enfermedad familiar
                                resultado = EnfermedadFamiliarSalud.objects.get(pk=id)
                                historial = HistorialDocumentosPPPSalud.objects.filter(enfermedadfamiliar=resultado).order_by('-id')

                        if tab > 0 and tab == 4:
                            resultado = PersonaDetalleMaternidadExtensionSalud.objects.get(pk=id)
                            historial = HistorialDocumentosPPPSalud.objects.filter(personamaternidadext=resultado).order_by('-id')

                        if tab > 0 and tab == 5: #Niños <= 5 años
                            resultado = PersonaDatosFamiliaresExtensionSalud.objects.get(pk=id)
                            historial = HistorialDocumentosPPPSalud.objects.filter(personafamiliarext=resultado, tipo=5).order_by('-id')

                        if tab > 0 and tab == 6: #Requisitos
                            resultado = RequisitoPracticappSalud.objects.get(pk=id)
                            historial = HistorialDocumentosPPPSalud.objects.filter(personarequisito=resultado, tipo=6).order_by('-id')

                        data['resultado'] = resultado
                        data['historial'] = historial
                        template = get_template("pro_revisionactividad_evidencia/modal/historialaprobacion.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            # if action == 'firmadocumento':
            #     try:
            #         detalle = EvidenciaActividadDetalleDistributivo.objects.get(id=request.GET['id'])
            #         archivo = detalle.archivo.url if detalle.archivo else None
            #         if detalle.archivofirmado:
            #             archivo = detalle.archivofirmado.url
            #
            #         data['archivo'] = archivo
            #         data['url_archivo'] = '{}{}'.format(dominio_sistema, archivo)
            #         data['id_objeto'] = detalle.id
            #         data['action_firma'] = 'firmadocumento'
            #         template = get_template("formfirmaelectronica.html")
            #         return JsonResponse({"result": True, 'data': template.render(data)})
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            #

            # if action == 'updatelg':
            #     from sagest.models import LogMarcada, LogDia
            #     hoy = datetime.now().date()
            #     try:
            #         mensaje = ''
            #         persona = request.session.get('persona')
            #
            #         a = int(aio) if (aio := request.GET.get('a', hoy.year)) else hoy.year
            #         m = int(mes) if (mes := request.GET.get('m', hoy.year)) else hoy.month
            #         d = int(dia) if (dia := request.GET.get('d', hoy.year)) else hoy.day
            #         fecha = datetime(a, m, d).date()
            #
            #         dia = LogDia.objects.filter(persona=persona, fecha=fecha, status=True).first()
            #         if not dia: dia = LogDia(persona=persona, fecha=fecha, jornada_id=1)
            #
            #         if t := int(request.GET.get('t', 0)):
            #             hmm = []
            #             if t == 1: hmm = [8, 0, 3]
            #             if t == 2: hmm = [13, 0, 3]
            #             if t == 3: hmm = [13, 50, 59]
            #             if t == 4: hmm = [17, 20, 30]
            #             if hmm.__len__():
            #                 input = {'logdia': dia, 'secuencia': t, 'time': datetime(a, m, d, hmm[0], random.randint(hmm[1], hmm[2]), random.randint(0, 59), random.randint(189000, 976248))}
            #                 LogMarcada(**input).save()
            #
            #                 cantidadmarcadas = dia.logmarcada_set.filter(status=True).values('id').count()
            #                 if cantidadmarcadas in (2, 4):
            #                     dia.cantidadmarcadas = cantidadmarcadas
            #                     dia.procesado = True
            #                     dia.save()
            #         else:
            #             if lg := LogMarcada.objects.filter(logdia=dia, time__hour__gte=8, time__hour__lte=12, status=True).first():
            #                 if lg.time.time() > time(8, 6):
            #                     v = lg.time.date()
            #                     lg.time = datetime(v.year, v.month, v.day, 8, random.randint(0, 4), random.randint(0, 59), random.randint(289000, 876248))
            #                     lg.usuario_creacion_id = persona.usuario_id if not lg.usuario_creacion_id == 1 else 1
            #                     lg.save()
            #                     mensaje += f"{lg.time.__str__()}, "
            #
            #         return JsonResponse({'result': True, 'mensaje': mensaje})
            #     except Exception as ex:
            #         return JsonResponse({'result': False, 'mensaje': ex.__str__()})
            #
            # if action == 'aprobadores-sin-actividad-asociada':
            #     try:
            #         return aprobadores_sin_actividad_asociada(request)
            #     except Exception as ex:
            #         pass

            elif action == 'revisionbitacora':
                try:
                    data['title'] = u"Revisión de bitacora de actividades"
                    bitacora = BitacoraActividadEstudiantePpp.objects.get(id=request.GET['id'])
                    filters = Q(bitacorapractica=bitacora, status=True)
                    _get_horas_minutos = lambda th: (th.total_seconds() / 3600).__str__().split('.')
                    _return = ''
                    for x in request.GET.keys():
                        if not x == 'action': _return += f'&{x}={request.GET[x]}'

                    if s := request.GET.get('s', ''):
                        data['search'] = search = s.strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filters &= Q(Q(titulo__icontains=search) | Q(descripcion__icontains=search) | Q(resultado__icontains=search))
                        if len(ss) > 1:
                            filters &= Q(Q(titulo__icontains=ss[0]) & Q(titulo__icontains=ss[1])) | Q(Q(descripcion__icontains=ss[0]) & Q(descripcion__icontains=ss[1])) | Q(Q(resultado__icontains=ss[0]) & Q(resultado__icontains=ss[1]))

                    data['return'] = '?' + _return.replace(',', '%2C')
                    # data['return'] = '?action=bitacoras' + _return.replace(',', '%2C')
                    data['registrosbitacora'] = detallebitacora = DetalleBitacoraEstudiantePpp.objects.filter(filters).annotate(diferencia=ExpressionWrapper(F('horafin') - F('horainicio'), output_field=TimeField())).order_by('fecha', 'horainicio', 'horafin')

                    if th := detallebitacora.aggregate(total=Sum('diferencia'))['total']:
                        horas, minutos = _get_horas_minutos(th)
                        data['total_horas'] = float("%s.%s" % (horas, round(float('0.' + minutos) * 60)))

                    if th := detallebitacora.filter(estadoaprobacion=2).aggregate(total=Sum('diferencia'))['total']:
                        horas, minutos = _get_horas_minutos(th)
                        data['total_aprobadas'] = float("%s.%s" % (horas, round(float('0.' + minutos) * 60)))

                    if th := detallebitacora.filter(estadoaprobacion=3).aggregate(total=Sum('diferencia'))['total']:
                        horas, minutos = _get_horas_minutos(th)
                        data['total_rechazadas'] = float("%s.%s" % (horas, round(float('0.' + minutos) * 60)))

                    # diasclas = ClaseActividad.objects.filter(detalledistributivo=bitacora.criterio, detalledistributivo__distributivo__profesor=bitacora.criterio.distributivo.profesor, status=True).values_list('dia', 'turno_id').order_by('inicio', 'dia', 'turno__comienza')
                    # dt, end, step = bitacora.fechaini, bitacora.fechafin, timedelta(days=1)
                    # result = []
                    # while dt <= end:
                    #     if not periodo.dias_nolaborables(dt):
                    #         for dclase in diasclas:
                    #             if dt.isocalendar()[2] == dclase[0]:
                    #                 result.append(dt.strftime('%Y-%m-%d'))
                    #     dt += step

                    data['bitacora'] = bitacora
                    # data['total_planificadas'] = result.__len__()
                    data['revision'] = request.GET.get('r', 0)
                    data['nombre'] = persona.nombres.__str__().split()[0]
                    return render(request, "pro_revisionactividad_evidencia/revisionbitacora.html", data)
                except Exception as ex:
                    pass

            elif action == 'itinerarioasignaturamalla':
                try:
                    data['title'] = u'Relación itinerarios con la asignatura'
                    data['action'] = action
                    data['id'] = id = request.GET['id']
                    ids, iditi = None, 0
                    search, filtros, filtro_combo, url_vars = request.GET.get('s', ''), Q(status=True), Q(status=True), f'&action={action}&id={id}'
                    listado = ItinerarioAsignaturaSalud.objects.filter(filtros)

                    if 'iditi' in request.GET:
                        iditi = int(request.GET['iditi'])
                        if iditi > 0:
                            filtros = filtros & Q(itinerariomalla__in=[iditi])
                            url_vars += f"&iditi={iditi}"
                            data['iditi'] = iditi

                    if 'idcar' in request.GET:
                        idcar = int(request.GET['idcar'])
                        if idcar > 0:
                            filtro_combo = filtro_combo & Q(malla__carrera__in=[idcar])
                            filtros = filtros & Q(itinerariomalla__malla__carrera__in=[idcar])
                            url_vars += f"&idcar={idcar}"
                            data['idcar'] = idcar

                    if search:
                        s = search.split()
                        if len(s) == 1:
                            filtros = filtros & (Q(itinerariomalla__nombre__icontains=s[0]) | Q(asignaturamalla__asignatura__nombre__icontains=s[0]))
                        elif len(s) == 2:
                            filtros = filtros & ((Q(itinerariomalla__nombre__icontains=s[0]) & Q(itinerariomalla__nombre__icontains=s[1])) |
                                                 (Q(asignaturamalla__asignatura__nombre__icontains=s[0]) & Q(asignaturamalla__asignatura__nombre__icontains=s[1])))
                        else:
                            filtros = filtros & (Q(itinerariomalla__nombre__icontains=search) | Q(asignaturamalla__asignatura__nombre__icontains=search))
                        data['s'] = f"{search}"
                        url_vars += f"&s={search}"
                    data['itinerarios'] = ItinerariosMalla.objects.filter(pk__in=listado.values_list('itinerariomalla', flat=True)).filter(filtro_combo)
                    data['carreras'] = Carrera.objects.filter(pk__in=listado.values_list('itinerariomalla__malla__carrera', flat=True))
                    paging = MiPaginador(listado.filter(filtros).order_by('-id'), 15)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET: p = int(request.GET['page'])
                        else: p = paginasesion
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
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    data['ids'] = ids if ids else ""
                    return render(request, "pro_revisionactividad_evidencia/viewitinerarioasignatura.html", data)
                except Exception as ex:
                    data['msg_error'] = ex.__str__()
                    return render(request, "adm_asistenciaexamensede/error.html", data)

            elif action == 'buscaritinerario':
                try:
                    idcar = request.GET['idcar']
                    qsbase = ItinerariosMalla.objects.filter(status=True, malla__vigente=True, malla__carrera__id=idcar)
                    if 'search' in request.GET:
                        qsbase = qsbase.filter(nombre__icontains=request.GET['search'])
                    resp = [{'id': cr.pk, 'text': cr.__str__()} for cr in qsbase.order_by('nombre')]
                    return HttpResponse(json.dumps({'state': True, 'result': resp}))
                except Exception as ex:
                    pass

            elif action == 'buscarasignaturamalla':
                try:
                    itinerario_id = int(request.GET['iditi'])
                    filtro = Q(status=True)
                    if itinerario_id > 0:
                        itinerario = ItinerariosMalla.objects.get(pk=itinerario_id)
                        filtro = filtro & (Q(malla=itinerario.malla))
                    qsbase = AsignaturaMalla.objects.filter(filtro)
                    if 'search' in request.GET:
                        qsbase = qsbase.filter(asignatura__nombre__icontains=request.GET['search'])
                    resp = [{'id': cr.pk, 'text': cr.__str__()} for cr in qsbase.order_by('asignatura__nombre')[:10]]
                    return HttpResponse(json.dumps({'state': True, 'result': resp}))
                except Exception as ex:
                    pass

            elif action == 'addasignaturaiti':
                try:
                    data['action'] = request.GET['action']
                    data['title'] = u'Adicionar registro'
                    form = ItinerarioAsignaturaSaludForm()
                    data['form'] = form
                    template = get_template("pro_revisionactividad_evidencia/modal/formitinerarioasignatura.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'editasignaturaiti':
                try:
                    data['title'] = u'Editar registro'
                    data['action'] = request.GET['action']
                    if id := int(encrypt(request.GET.get('id', 0))):
                        data['id'] = id
                    if id > 0:
                        data['registro'] = registro = ItinerarioAsignaturaSalud.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                        f = ItinerarioAsignaturaSaludForm(initial={'carrera': registro.itinerariomalla.malla.carrera})
                        f.iniciar_editar(registro)
                        data['form'] = f
                        template = get_template("pro_revisionactividad_evidencia/modal/formitinerarioasignatura.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect('/alu_practicassalud?action=confpreinscripciones')
        else:
            try:
                data['title'] = u'Listado de bitacoras registradas'
                now, dias_plazo = datetime.now().date(), variable_valor('DIA_LIMITE_INFORME_MENSUAL')
                search, url_vars, numerofilas = request.GET.get('s', ''), '', 15
                # filter, url_vars = Q(supervisor=profesor, status=True), '&action=listasupervision'

                nombre_mes = lambda i: ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][i - 1]
                _get_first_col = lambda x: [i[0] for i in x]
                # filters = Q(pk=0)
                filters = Q(status=True)

                if ids := request.GET.get('id', None):
                    data['ids'] = ids
                    filters &= Q(pk=ids)
                    url_vars += f'&id={ids}'

                if practicasppinscripcion := PracticasPreprofesionalesInscripcion.objects.filter(supervisor=profesor, status=True).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres').exclude(culminada=True).distinct():
                    filters &= Q(practicasppinscripcion_id__in=practicasppinscripcion.values_list('id', flat=True))
                tipoencriptado = request.GET.get('tipo', encrypt(2))
                tipoestado = int(encrypt(tipoencriptado))

                filters &= Q(status=True)

                bitacoras = BitacoraActividadEstudiantePpp.objects.filter(filters)
                # bitacoras = BitacoraActividadDocente.objects.filter(filters).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2')
                itinerarios = [{'name': iti, 'val': iti.id} for iti in set(ItinerariosMalla.objects.filter(pk__in=bitacoras.values_list('practicasppinscripcion__itinerariomalla', flat=True)))]
                meses = [{'name': nombre_mes(m), 'val': m} for m in set(bitacoras.values_list('fechafin__month', flat=True).order_by('fechafin').distinct())]

                total = bitacoras.count()

                if tipoestado: filters &= Q(estadorevision=tipoestado)

                # if criterio := request.GET.get('criterio', '0'):
                #     if not criterio == '0':
                #         id, tipo = criterio.split(',')
                #         if tipo == 'd': filters &= Q(criterio__criteriodocenciaperiodo__criterio__id=id)
                #         if tipo == 'i': filters &= Q(criterio__criterioinvestigacionperiodo__criterio__id=id)
                #         if tipo == 'g': filters &= Q(criterio__criteriogestionperiodo__criterio__id=id)
                #         data |= {'criterio_id': id, 'tipocriterio': tipo}
                #         url_vars += f"&criterio={criterio}"

                if mes := int(request.GET.get('mes', '0')):
                    data['eMes'] = mes
                    filters &= Q(fechafin__month=mes)
                    url_vars += f"&mes={mes}"

                if iti := int(request.GET.get('itinerario', '0')):
                    data['eIti'] = iti
                    filters &= Q(practicasppinscripcion__itinerariomalla_id=iti)
                    url_vars += f"&itinerario={iti}"

                if s := request.GET.get('s', ''):
                    data['search'] = search = s.strip()
                    url_vars += f'&s={search}'
                    ss = search.split(' ')

                    if len(ss) == 1:
                        filters &= Q(Q(practicasppinscripcion__inscripcion__persona__nombres__icontains=search) | Q(practicasppinscripcion__inscripcion__persona__apellido1__icontains=search) | Q(practicasppinscripcion__inscripcion__persona__apellido2__icontains=search) | Q(practicasppinscripcion__inscripcion__persona__cedula__icontains=search) | Q(practicasppinscripcion__inscripcion__persona__pasaporte__icontains=search))
                    if len(ss) == 2:
                        filters &= Q(Q(practicasppinscripcion__inscripcion__persona__apellido1__icontains=ss[0]) & Q(practicasppinscripcion__inscripcion__persona__apellido2__icontains=ss[1]))
                    if len(ss) > 4:
                        filters &= Q(practicasppinscripcion__preinscripcion__preinscripcion__motivo__icontains=search)

                paging = MiPaginador(bitacoras.filter(filters).order_by('practicasppinscripcion__inscripcion__persona__apellido1', 'practicasppinscripcion__inscripcion__persona__persona__apellido2'), numerofilas)

                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                        if p == 1:
                            numerofilasguiente = numerofilas
                        else:
                            numerofilasguiente = numerofilas * (p - 1)
                    else:
                        p = paginasesion
                        if p == 1:
                            numerofilasguiente = numerofilas
                        else:
                            numerofilasguiente = numerofilas * (p - 1)
                    try:
                        page = paging.page(p)
                    except:
                        p = 1
                    page = paging.page(p)
                except:
                    page = paging.page(p)

                # Pasar a estado solicitado las bitacoras que esten pendientes en el día seleccionado como plazo
                # if now.day >= (dias_plazo + 1):
                #     BitacoraActividadDocente.objects.filter(estadorevision=1, fechafin__month=now.month - 1, status=True).update(estadorevision=2)

                data['tipo'] = tipoencriptado
                url_vars += f'&tipo={tipoencriptado}'
                request.session['paginador'] = p
                data['paging'] = paging
                data['numerofilasguiente'] = numerofilasguiente
                data['numeropagina'] = p
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data["url_vars"] = url_vars
                data['listaevidencias'] = page.object_list
                data['tipo_int'] = tipoestado
                # data['puede_firmar_masivo'] = not codigosdoc == None
                data['meses'] = meses
                data['itinerarios'] = itinerarios
                data['total'] = total
                return render(request, "pro_revisionactividad_evidencia/listadobitacoras.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                return render(request, "adm_horarios/error.html", data)